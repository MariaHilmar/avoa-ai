"""Base de agentes do Avoa.

Um agente é uma capacidade reutilizável (camada 3). Ele declara a `tarefa`
(que decide o tier/modelo via roteador) e um `system` prompt, recebe um
contexto e devolve um contexto atualizado. Ver docs/AGENTS.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.llm.client import LLMClient

# Contexto tipado de forma aberta: chaves evoluem por fluxo (Refina, Reunião…).
# Módulos podem estreitar com TypedDict (ex.: avoa_refine.contexto_tipos).
Contexto = dict[str, Any]


class Agent(ABC):
    #: nome de tarefa usado pelo roteador de modelos (core/llm/routing.yaml)
    tarefa: str
    #: instrução de sistema do agente
    system: str = ""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @property
    def nome(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def montar_prompt(self, contexto: Contexto) -> str:
        """Constrói o prompt do usuário a partir do contexto."""

    @abstractmethod
    def aplicar(self, contexto: Contexto, resposta: str) -> Contexto:
        """Integra a resposta do LLM ao contexto e o devolve."""

    def run(self, contexto: Contexto) -> Contexto:
        prompt = self.montar_prompt(contexto)
        resposta = self.llm.complete(self.tarefa, self.system, prompt)
        return self.aplicar(contexto, resposta)
