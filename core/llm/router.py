"""Roteador de modelos do Avoa.

Resolve `tarefa -> tier -> modelo` a partir de core/llm/routing.yaml.
Permite override global (ex.: rodar tudo em 'leve' para baratear evals) e
registra a intenção de uso para observabilidade. Ver docs/AGENTS.md.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).with_name("routing.yaml")


class ModelRouter:
    def __init__(self, config_path: Path = _CONFIG_PATH) -> None:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self._tiers: dict[str, str] = data["tiers"]
        self._tarefas: dict[str, str] = data["tarefas"]
        self._force_tier: str | None = data.get("force_tier")

    def tier_de(self, tarefa: str) -> str:
        if self._force_tier:
            return self._force_tier
        try:
            return self._tarefas[tarefa]
        except KeyError as exc:
            raise ValueError(
                f"Tarefa '{tarefa}' não mapeada em routing.yaml"
            ) from exc

    def modelo_de(self, tarefa: str) -> str:
        """Retorna o model id a usar para a tarefa."""
        return self._tiers[self.tier_de(tarefa)]


if __name__ == "__main__":  # smoke test manual
    r = ModelRouter()
    for t in ("extrair_itens", "redigir_historia", "criticar_historia"):
        print(f"{t:24} -> {r.tier_de(t):7} -> {r.modelo_de(t)}")
