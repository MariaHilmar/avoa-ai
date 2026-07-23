"""Consultas sobre coleções de histórias (agrupar/filtrar).

Núcleo compartilhado: fatiar o backlog por componente (área) e por release
alimenta KPIs e roadmap sem virar módulo. Ver docs/DATA-MODEL.md.
"""

from __future__ import annotations

from collections import defaultdict

from core.domain.models import Historia


def filtrar_por_componente(historias: list[Historia], componente: str) -> list[Historia]:
    return [h for h in historias if h.componente == componente]


def filtrar_por_release(historias: list[Historia], release_id: str) -> list[Historia]:
    return [h for h in historias if h.release_id == release_id]


def agrupar_por_componente(historias: list[Historia]) -> dict[str | None, list[Historia]]:
    grupos: dict[str | None, list[Historia]] = defaultdict(list)
    for h in historias:
        grupos[h.componente].append(h)
    return dict(grupos)


def agrupar_por_release(historias: list[Historia]) -> dict[str | None, list[Historia]]:
    grupos: dict[str | None, list[Historia]] = defaultdict(list)
    for h in historias:
        grupos[h.release_id].append(h)
    return dict(grupos)
