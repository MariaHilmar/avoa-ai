"""Parse do corpo de issues GitHub no formato Avoa (INVEST + Gherkin).

Extrai narrativa e `CriterioAceite` a partir de bodies típicos do Project #9
e do que o próprio `GitHubAdapter._corpo` grava ao criar issues.

Implementação linha a linha (sem regex complexas) para evitar ReDoS em inputs
grandes ou hostis.
"""

from __future__ import annotations

from core.domain.models import CriterioAceite

_MAX_BODY_CHARS = 100_000
_GHERKIN_PREFIXES = (
    "dado ",
    "given ",
    "quando ",
    "when ",
    "então ",
    "entao ",
    "then ",
    "e ",
)


def _corpo_limitado(body: str) -> str:
    return (body or "")[:_MAX_BODY_CHARS]


def _linhas(body: str) -> list[str]:
    return _corpo_limitado(body).splitlines()


def _limpar_titulo_secao(linha: str) -> str:
    s = linha.strip()
    if s.startswith("**") and s.endswith("**"):
        s = s[2:-2]
    if s.startswith("#"):
        s = s.lstrip("#").strip()
    if s.endswith(":"):
        s = s[:-1]
    return s.strip().lower()


def _eh_cabecalho(linha: str) -> bool:
    s = linha.strip()
    return (s.startswith("**") and s.endswith("**")) or s.startswith("#")


def _eh_secao_historia(linha: str) -> bool:
    titulo = _limpar_titulo_secao(linha)
    return titulo.startswith("hist")


def _eh_secao_criterios(linha: str) -> bool:
    titulo = _limpar_titulo_secao(linha)
    return titulo.startswith("crit") and "aceite" in titulo


def _eh_secao_referencia(linha: str) -> bool:
    titulo = _limpar_titulo_secao(linha)
    return titulo.startswith("refer")


def _tem_passo_gherkin(texto: str) -> bool:
    for linha in texto.splitlines():
        s = linha.strip().lower()
        if any(s.startswith(p) for p in _GHERKIN_PREFIXES):
            return True
    return False


def _linha_inicia_cenario(linha: str) -> bool:
    s = linha.strip().lower()
    return s.startswith("dado ") or s.startswith("given ")


def _cenarios_gherkin(texto: str) -> list[str]:
    """Parte um bloco Gherkin em cenários (um por 'Dado' de topo)."""
    texto = texto.strip()
    if not texto or not _tem_passo_gherkin(texto):
        return []

    linhas = texto.splitlines()
    blocos: list[list[str]] = []
    atual: list[str] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.strip():
            j = i + 1
            while j < len(linhas) and not linhas[j].strip():
                j += 1
            if j < len(linhas) and _linha_inicia_cenario(linhas[j]) and atual:
                blocos.append(atual)
                atual = []
            i += 1
            continue
        atual.append(linha)
        i += 1
    if atual:
        blocos.append(atual)

    out = [
        "\n".join(parte).strip()
        for parte in blocos
        if _tem_passo_gherkin("\n".join(parte))
    ]
    return out or [texto]


def _blocos_fenced_gherkin(texto: str) -> list[str]:
    blocos: list[str] = []
    linhas = texto.splitlines()
    i = 0
    while i < len(linhas):
        raw = linhas[i].strip()
        if raw.startswith("```"):
            tag = raw[3:].strip().lower()
            if tag in ("", "gherkin"):
                i += 1
                buf: list[str] = []
                while i < len(linhas) and not linhas[i].strip().startswith("```"):
                    buf.append(linhas[i])
                    i += 1
                if i < len(linhas):
                    blocos.append("\n".join(buf))
            else:
                i += 1
                while i < len(linhas) and not linhas[i].strip().startswith("```"):
                    i += 1
        i += 1
    return blocos


def _texto_sem_fences(texto: str) -> str:
    out: list[str] = []
    dentro = False
    for linha in texto.splitlines():
        if linha.strip().startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            out.append(linha)
    return "\n".join(out)


def _itens_bullet(bloco: str) -> list[str]:
    """Agrupa bullets markdown (item pode ter várias linhas até o próximo `-`)."""
    itens: list[str] = []
    atual: list[str] = []
    for linha in bloco.splitlines():
        stripped = linha.lstrip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            if atual:
                itens.append("\n".join(atual).strip())
            atual = [stripped[2:]]
        elif atual:
            atual.append(linha)
    if atual:
        itens.append("\n".join(atual).strip())
    return itens


def _conteudo_secao(linhas: list[str], inicio: int) -> str:
    buf: list[str] = []
    i = inicio + 1
    while i < len(linhas):
        if _eh_cabecalho(linhas[i]):
            break
        buf.append(linhas[i])
        i += 1
    return "\n".join(buf).strip()


def _indice_secao(linhas: list[str], pred) -> int | None:
    for idx, linha in enumerate(linhas):
        if pred(linha):
            return idx
    return None


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

    texto = _corpo_limitado(body)

    for bloco in _blocos_fenced_gherkin(texto):
        for cen in _cenarios_gherkin(bloco):
            _add(cen)

    linhas = _linhas(texto)
    idx_crit = _indice_secao(linhas, _eh_secao_criterios)
    if idx_crit is not None:
        bloco = _texto_sem_fences(_conteudo_secao(linhas, idx_crit))
        for item in _itens_bullet(bloco):
            if _tem_passo_gherkin(item):
                _add(item.replace("\\n", "\n"))

    return criterios


def extrair_narrativa_do_corpo(body: str) -> str:
    """Narrativa INVEST: seção **História**, senão body sem critérios/referência."""
    if not body:
        return ""

    linhas = _linhas(body)
    idx_hist = _indice_secao(linhas, _eh_secao_historia)
    if idx_hist is not None:
        return _conteudo_secao(linhas, idx_hist)

    omitir = False
    limpas: list[str] = []
    dentro_fence = False
    for linha in linhas:
        stripped = linha.strip()
        if stripped.startswith("```"):
            dentro_fence = not dentro_fence
            continue
        if dentro_fence:
            continue
        if _eh_secao_criterios(linha) or _eh_secao_referencia(linha):
            omitir = True
            continue
        if omitir and _eh_cabecalho(linha):
            omitir = False
        if not omitir:
            limpas.append(linha)

    return "\n".join(limpas).strip()


def parse_corpo_issue(body: str) -> tuple[str, list[CriterioAceite]]:
    """Devolve (narrativa, criterios_aceite) a partir do body da issue."""
    texto = body or ""
    return extrair_narrativa_do_corpo(texto), extrair_criterios_do_corpo(texto)
