"""Cliente LLM do Avoa: roteia a tarefa para o modelo certo e chama a Anthropic.

- Usa o ModelRouter (tarefa -> tier -> modelo) para escolher o modelo barato/caro.
- Registra uso (observabilidade).
- Aceita um `transport` injetável para testes (sem chamar a API de verdade).

Ver docs/AGENTS.md.
"""

from __future__ import annotations

import os
from typing import Callable

from core.llm.router import ModelRouter
from core.observability.usage import UsageTracker

# transport: (modelo, system, user) -> (texto, tokens_entrada, tokens_saida)
Transport = Callable[[str, str, str], tuple[str, int, int]]


def _anthropic_transport(modelo: str, system: str, user: str) -> tuple[str, int, int]:
    """Transport real usando o SDK da Anthropic. Requer ANTHROPIC_API_KEY."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=modelo,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return texto, resp.usage.input_tokens, resp.usage.output_tokens


class LLMClient:
    def __init__(
        self,
        router: ModelRouter | None = None,
        transport: Transport | None = None,
        usage: UsageTracker | None = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.transport = transport or _anthropic_transport
        self.usage = usage or UsageTracker()

    def complete(self, tarefa: str, system: str, user: str) -> str:
        modelo = self.router.modelo_de(tarefa)
        texto, tin, tout = self.transport(modelo, system, user)
        self.usage.registrar(tarefa, modelo, tin, tout)
        return texto
