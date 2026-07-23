"""Observabilidade mínima: contagem de uso e traces.

Base para os KPIs de custo e para o limite do plano free (ver docs/BUSINESS.md).
Em produção, isto vira persistência via Repository; aqui é in-memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UsoLLM:
    tarefa: str
    modelo: str
    tokens_entrada: int = 0
    tokens_saida: int = 0


@dataclass
class UsageTracker:
    registros: list[UsoLLM] = field(default_factory=list)

    def registrar(self, tarefa: str, modelo: str, entrada: int, saida: int) -> None:
        self.registros.append(UsoLLM(tarefa, modelo, entrada, saida))

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_entrada + r.tokens_saida for r in self.registros)

    def por_modelo(self) -> dict[str, int]:
        agg: dict[str, int] = {}
        for r in self.registros:
            agg[r.modelo] = agg.get(r.modelo, 0) + r.tokens_entrada + r.tokens_saida
        return agg
