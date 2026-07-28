"""Orquestrador do Avoa.

Encadeia agentes: cada um recebe o contexto do anterior. É a base que todos os
módulos (Refina, Reunião→Backlog, etc.) compõem. Ver docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.agents.base import Agent, Contexto


@dataclass
class TraceEtapa:
    agente: str
    tarefa: str


@dataclass
class Orchestrator:
    agentes: list[Agent]
    trace: list[TraceEtapa] = field(default_factory=list)

    def run(self, contexto: Contexto) -> Contexto:
        for agente in self.agentes:
            contexto = agente.run(contexto)
            self.trace.append(TraceEtapa(agente.nome, agente.tarefa))
        return contexto

    def run_com_loop(
        self, contexto: Contexto, redator: Agent, critico: Agent, max_iter: int = 3
    ) -> Contexto:
        """Loop crítico-redator: o crítico avalia; se reprovar, o redator ajusta.

        O crítico deve gravar contexto['aprovado'] (bool) e contexto['feedback'].
        """
        contexto = redator.run(contexto)
        for _ in range(max_iter):
            contexto = critico.run(contexto)
            self.trace.append(TraceEtapa(critico.nome, critico.tarefa))
            if contexto.get("aprovado"):
                break
            contexto = redator.run(contexto)
            self.trace.append(TraceEtapa(redator.nome, redator.tarefa))
        return contexto
