"""Definition of Ready / Definition of Done — núcleo, não módulo.

Uma checklist é uma lista de itens nomeados, cada um com um predicado sobre a
história. O Crítico usa a DoR para marcar `Historia.pronta`; o Revisor de PR
(Fase 4) usa a DoD como base do "atende aos critérios?". Ver docs/AGENTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.domain.models import Historia

Predicado = Callable[[Historia], bool]


@dataclass
class ItemChecklist:
    nome: str
    predicado: Predicado


@dataclass
class Checklist:
    nome: str
    itens: list[ItemChecklist] = field(default_factory=list)

    def avaliar(self, historia: Historia) -> tuple[bool, list[str]]:
        """Devolve (passou, itens_faltantes)."""
        faltantes = [i.nome for i in self.itens if not i.predicado(historia)]
        return (not faltantes, faltantes)


# ---- Checklists padrão -------------------------------------------------------

def _tem_narrativa_invest(h: Historia) -> bool:
    n = (h.narrativa or "").lower()
    return "como" in n and "quero" in n and "para" in n


def definition_of_ready() -> Checklist:
    """DoR padrão: o que uma história precisa para entrar em desenvolvimento."""
    return Checklist(
        "Definition of Ready",
        [
            ItemChecklist("narrativa no formato INVEST", _tem_narrativa_invest),
            ItemChecklist("tem ao menos um critério de aceite", lambda h: bool(h.criterios_aceite)),
            ItemChecklist("está estimada em pontos", lambda h: h.pontos is not None),
        ],
    )


def definition_of_done() -> Checklist:
    """DoD padrão: base do 'atende?' do Revisor de PR (Fase 4)."""
    return Checklist(
        "Definition of Done",
        [
            ItemChecklist("critérios de aceite definidos", lambda h: bool(h.criterios_aceite)),
            ItemChecklist("tem casos de teste vinculados", lambda h: bool(h.casos_teste)),
        ],
    )


def aplicar_dor(historia: Historia, dor: Checklist | None = None) -> tuple[bool, list[str]]:
    """Aplica a DoR e marca `historia.pronta`. Devolve (pronta, faltantes)."""
    dor = dor or definition_of_ready()
    passou, faltantes = dor.avaliar(historia)
    historia.pronta = passou
    return passou, faltantes
