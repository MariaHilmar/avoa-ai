"""Testes do parse INVEST/Gherkin do corpo de issues GitHub."""

from __future__ import annotations

import pathlib

import pytest

from core.integrations.github_adapter import GitHubAdapter
from core.integrations.github_parse import (
    extrair_criterios_do_corpo,
    extrair_narrativa_do_corpo,
    parse_corpo_issue,
)

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "github_bodies"

# Formato típico do Project #9 (avoa-brain).
_BODY_BRAIN = """**História**
Como QA, quero gerar casos de teste a partir dos critérios de aceite, para cobrir a história sem escrever tudo à mão.

**Critérios de aceite**
```gherkin
Dado um critério de aceite
Quando o GeradorDeTeste roda
Então produz casos de teste com passos e resultado esperado
E cada caso referencia o critério de origem
```

**Referência:** docs/AGENTS.md, docs/DATA-MODEL.md
"""

# Formato gravado por GitHubAdapter._corpo.
_BODY_ADAPTER = """Como usuário, quero recuperar a senha, para acessar a conta.

### Critérios de aceite
- Dado que esqueci
Quando solicito
Então recebo o link
"""


def _ler_fixture(nome: str) -> str:
    return (_FIXTURES / nome).read_text(encoding="utf-8")


def test_extrai_gherkin_fenced_do_brain():
    criterios = extrair_criterios_do_corpo(_BODY_BRAIN)
    assert len(criterios) == 1
    assert criterios[0].id == "c1"
    assert "GeradorDeTeste" in (criterios[0].formato_gherkin or "")
    assert "origem" in (criterios[0].formato_gherkin or "")
    assert "passos" in (criterios[0].formato_gherkin or "")


def test_extrai_narrativa_secao_historia():
    narrativa = extrair_narrativa_do_corpo(_BODY_BRAIN)
    assert narrativa.startswith("Como QA")
    assert "Critérios" not in narrativa
    assert "```" not in narrativa


def test_extrai_bullet_do_corpo_adapter():
    criterios = extrair_criterios_do_corpo(_BODY_ADAPTER)
    assert len(criterios) == 1
    assert "recebo o link" in (criterios[0].formato_gherkin or "")


def test_parse_corpo_issue_tupla():
    narrativa, criterios = parse_corpo_issue(_BODY_BRAIN)
    assert "Como QA" in narrativa
    assert len(criterios) == 1


def test_corpo_vazio():
    assert extrair_criterios_do_corpo("") == []
    assert extrair_narrativa_do_corpo("") == ""
    assert extrair_criterios_do_corpo("   ") == []


def test_narrativa_fallback_sem_secao_historia():
    """Body cru (sem **História**) vira narrativa após remover critérios/referência."""
    body = """Como dev, quero exportar relatório, para auditar o backlog.

**Critérios de aceite**
```gherkin
Dado backlog avaliado
Quando exporto
Então recebo PDF
```

**Referência:** docs/X.md
"""
    narrativa = extrair_narrativa_do_corpo(body)
    assert narrativa.startswith("Como dev")
    assert "gherkin" not in narrativa.lower()
    assert "Referência" not in narrativa


def test_multiplos_cenarios_no_mesmo_fence():
    body = """```gherkin
Dado usuario logado
Quando favorita
Então salva

Dado usuario anonimo
Quando favorita
Então pede login
```"""
    criterios = extrair_criterios_do_corpo(body)
    assert len(criterios) == 2
    assert criterios[0].id == "c1"
    assert criterios[1].id == "c2"
    assert "logado" in (criterios[0].formato_gherkin or "")
    assert "anonimo" in (criterios[1].formato_gherkin or "")


def test_deduplica_criterios_repetidos():
    body = """```gherkin
Dado X
Quando Y
Então Z
```

```gherkin
Dado X
Quando Y
Então Z
```"""
    assert len(extrair_criterios_do_corpo(body)) == 1


def test_body_sem_gherkin_nao_inventa_criterios():
    body = "**História**\nComo PO, quero priorizar, para entregar valor.\n"
    assert extrair_criterios_do_corpo(body) == []
    assert extrair_narrativa_do_corpo(body).startswith("Como PO")


def test_fixture_issue_24_rastreabilidade():
    body = _ler_fixture("issue_24_rastreabilidade.md")
    narrativa, criterios = parse_corpo_issue(body)
    assert narrativa.startswith("Como QA")
    assert len(criterios) == 1
    assert "CriterioAceite" in (criterios[0].formato_gherkin or "")


def test_fixture_issue_27_evals():
    body = _ler_fixture("issue_27_evals.md")
    narrativa, criterios = parse_corpo_issue(body)
    assert "evals" in narrativa.lower() or "cobertura" in narrativa.lower()
    assert len(criterios) == 1
    assert "cenários esperados" in (criterios[0].formato_gherkin or "") or (
        "cenarios esperados" in (criterios[0].formato_gherkin or "").lower()
    )


def test_fixture_sem_gherkin():
    body = _ler_fixture("issue_sem_gherkin.md")
    narrativa, criterios = parse_corpo_issue(body)
    assert narrativa.startswith("Como PO")
    assert criterios == []


def test_fence_sem_fechar_nao_quebra():
    """Fence aberto sem ``` final: não inventa critério; não levanta."""
    body = "**História**\nComo QA, quero X, para Y.\n\n```gherkin\nDado a\nQuando b\n"
    narrativa, criterios = parse_corpo_issue(body)
    assert "Como QA" in narrativa
    assert criterios == []


def test_gherkin_misturado_com_markdown_nao_quebra():
    body = """**História**
Como QA, quero X, para Y.

**Critérios de aceite**
Veja a tabela:

| passo | resultado |
| --- | --- |
| clicar | ok |

- texto solto sem Dado/Quando/Então
"""
    assert extrair_criterios_do_corpo(body) == []


def test_bullet_sem_passos_gherkin_ignorado():
    body = """### Critérios de aceite
- o sistema deve ser rápido
- UX amigável
"""
    assert extrair_criterios_do_corpo(body) == []


@pytest.mark.parametrize(
    "body",
    [
        None,
        "",
        "   \n\t  ",
        "```\n\n```",
        "**Critérios de aceite**\n```gherkin\n```\n",
        "a" * 5000,
        "<script>alert(1)</script>\n**História**\nComo X, quero Y, para Z.",
    ],
)
def test_parse_hostil_nao_quebra(body):
    """Bodies hostis/atípicos: nunca crasham; devolvem tupla estável."""
    if body is None:
        narrativa, criterios = parse_corpo_issue("")  # type: ignore[arg-type]
    else:
        narrativa, criterios = parse_corpo_issue(body)
    assert isinstance(narrativa, str)
    assert isinstance(criterios, list)


def test_para_historia_preenche_criterios():
    """_para_historia não joga o body inteiro em narrativa sem parse."""
    adapter = object.__new__(GitHubAdapter)
    issue = {
        "number": 23,
        "title": "[F3] GeradorDeTeste",
        "body": _BODY_BRAIN,
        "state": "open",
        "html_url": "https://github.com/MariaHilmar/avoa-brain/issues/23",
        "labels": [{"name": "fase-3"}, {"name": "tipo:agente"}],
    }
    h = adapter._para_historia(issue)
    assert h.id == "23"
    assert h.narrativa.startswith("Como QA")
    assert len(h.criterios_aceite) == 1
    assert h.criterios_aceite[0].formato_gherkin
    assert h.metadados["labels"] == ["fase-3", "tipo:agente"]
