"""Parse do corpo de issues GitHub no formato Avoa (INVEST + Gherkin).

Extrai narrativa e `CriterioAceite` a partir de bodies típicos do Project #9
e do que o próprio `GitHubAdapter._corpo` grava ao criar issues.
"""

from __future__ import annotations

import re

from core.domain.models import CriterioAceite

# Bloco fenced ```gherkin ... ``` (ou ``` sem linguagem, seção de critérios).
_RE_FENCED_GHERKIN = re.compile(
    r"```(?:gherkin)?\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)

# Seção "Critérios de aceite" (markdown **bold** ou ### heading).
_RE_SECAO_CRITERIOS = re.compile(
    r"(?is)(?:\*\*crit[eé]rios?\s+de\s+aceite\*\*|#{1,3}\s*crit[eé]rios?\s+de\s+aceite)\s*:?\s*\n+(.*?)(?=\n\s*(?:\*\*[^*]+\*\*|#{1,3}\s+\S)|\Z)",
)

# Seção História (narrativa INVEST).
_RE_SECAO_HISTORIA = re.compile(
    r"(?is)\*\*hist[oó]ria\*\*\s*:?\s*\n+(.*?)(?=\n\s*\*\*[^*]+\*\*|\n\s*#{1,3}\s+\S|\Z)",
)

_RE_PASSOS_GHERKIN = re.compile(
    r"(?im)^\s*(dado|quando|ent[aã]o|e)\b",
)


def _cenarios_gherkin(texto: str) -> list[str]:
    """Parte um bloco Gherkin em cenários (um por 'Dado' de topo)."""
    texto = texto.strip()
    if not texto:
        return []
    # Vários cenários no mesmo fence separados por linha em branco + Dado.
    partes = re.split(r"\n\s*\n(?=(?:Dado|Given)\b)", texto, flags=re.IGNORECASE)
    out = [p.strip() for p in partes if p.strip() and _RE_PASSOS_GHERKIN.search(p)]
    return out or ([texto] if _RE_PASSOS_GHERKIN.search(texto) else [])


def _itens_bullet(bloco: str) -> list[str]:
    """Agrupa bullets markdown (item pode ter várias linhas até o próximo `-`)."""
    itens: list[str] = []
    atual: list[str] = []
    for linha in bloco.splitlines():
        if re.match(r"^\s*[-*]\s+", linha):
            if atual:
                itens.append("\n".join(atual).strip())
            atual = [re.sub(r"^\s*[-*]\s+", "", linha)]
        elif atual:
            atual.append(linha)
    if atual:
        itens.append("\n".join(atual).strip())
    return itens


def extrair_criterios_do_corpo(body: str) -> list[CriterioAceite]:
    """Extrai critérios a partir de fences Gherkin e/ou bullets da seção."""
    if not body or not body.strip():
        return []

    criterios: list[CriterioAceite] = []
    vistos: set[str] = set()

    def _add(gherkin: str) -> None:
        g = gherkin.strip()
        if not g or g in vistos:
            return
        vistos.add(g)
        n = len(criterios) + 1
        criterios.append(
            CriterioAceite(id=f"c{n}", descricao="", formato_gherkin=g)
        )

    # 1) Fences ```gherkin
    for m in _RE_FENCED_GHERKIN.finditer(body):
        for cen in _cenarios_gherkin(m.group(1)):
            _add(cen)

    # 2) Bullets na seção Critérios (formato do _corpo do adapter)
    sec = _RE_SECAO_CRITERIOS.search(body)
    if sec:
        bloco = sec.group(1)
        # Ignora o que já veio de fence dentro da seção
        sem_fence = _RE_FENCED_GHERKIN.sub("", bloco)
        for item in _itens_bullet(sem_fence):
            if _RE_PASSOS_GHERKIN.search(item):
                _add(item.replace("\\n", "\n"))

    return criterios


def extrair_narrativa_do_corpo(body: str) -> str:
    """Narrativa INVEST: seção **História**, senão body sem critérios/referência."""
    if not body:
        return ""
    m = _RE_SECAO_HISTORIA.search(body)
    if m:
        return m.group(1).strip()

    # Remove seção de critérios e referência para não poluir a narrativa.
    limpo = _RE_SECAO_CRITERIOS.sub("", body)
    limpo = _RE_FENCED_GHERKIN.sub("", limpo)
    limpo = re.sub(
        r"(?is)\*\*refer[eéê]ncia:\*\*.*|\*\*refer[eéê]ncia\*\*\s*:?.*",
        "",
        limpo,
    ).strip()
    return limpo


def parse_corpo_issue(body: str) -> tuple[str, list[CriterioAceite]]:
    """Devolve (narrativa, criterios_aceite) a partir do body da issue."""
    return extrair_narrativa_do_corpo(body or ""), extrair_criterios_do_corpo(body or "")
