"""Testes do GitHubAdapter (HTTP mockado, sem rede)."""

from __future__ import annotations

import httpx
import pytest

from core.domain.models import CriterioAceite, Historia, Status
from core.integrations.github_adapter import (
    GitHubAdapter,
    IssueIdInvalidoError,
    RepoInvalidoError,
    validar_repo,
)

_BODY_F3 = """**História**
Como QA, quero testes, para validar.

**Critérios de aceite**
```gherkin
Dado critério
Quando roda
Então passa
```
"""


def _issue(
    numero: int,
    *,
    titulo: str = "Issue",
    labels: list[str] | None = None,
    pr: bool = False,
    state: str = "open",
    body: str | None = None,
) -> dict:
    item: dict = {
        "number": numero,
        "title": titulo,
        "body": body if body is not None else _BODY_F3,
        "state": state,
        "html_url": f"https://github.com/o/r/issues/{numero}",
        "labels": [{"name": lb} for lb in (labels or [])],
    }
    if pr:
        item["pull_request"] = {"url": "https://api.github.com/repos/o/r/pulls/1"}
    return item


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("GET", "https://api.github.com"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


class _FakeHTTP:
    """HTTP fake: get/post/patch com roteamento simples por path."""

    def __init__(
        self,
        *,
        paginas: dict[int, list[dict]] | None = None,
        issue_por_id: dict[str, dict] | None = None,
        search_items: list[dict] | None = None,
        post_criar: dict | None = None,
        status_por_path: dict[str, int] | None = None,
    ) -> None:
        self._paginas = paginas or {}
        self._issue_por_id = issue_por_id or {}
        self._search_items = search_items or []
        self._post_criar = post_criar or {"number": 99}
        self._status_por_path = status_por_path or {}
        self.chamadas: list[tuple[str, str, dict | None]] = []

    def _status(self, path: str) -> int:
        for prefix, code in self._status_por_path.items():
            if path.startswith(prefix) or prefix in path:
                return code
        return 200

    def get(self, path: str, params: dict | None = None):
        self.chamadas.append(("GET", path, params))
        code = self._status(path)
        if path.startswith("/search/issues"):
            return _FakeResponse({"items": self._search_items}, status_code=code)
        if "/issues/" in path and path.rstrip("/").split("/")[-1].isdigit():
            id_ = path.rstrip("/").split("/")[-1]
            return _FakeResponse(self._issue_por_id.get(id_, {}), status_code=code)
        # listagem / milestone
        pagina = (params or {}).get("page", 1)
        return _FakeResponse(self._paginas.get(pagina, []), status_code=code)

    def post(self, path: str, json: dict | None = None):
        self.chamadas.append(("POST", path, json))
        code = self._status(path)
        if path.endswith("/issues") and not path.rstrip("/").endswith("/comments"):
            return _FakeResponse(self._post_criar, status_code=code)
        return _FakeResponse({"id": 1}, status_code=code)

    def patch(self, path: str, json: dict | None = None):
        self.chamadas.append(("PATCH", path, json))
        return _FakeResponse({}, status_code=self._status(path))


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    gh = GitHubAdapter(token="test-token", repo="owner/repo")
    gh._http = _FakeHTTP()  # type: ignore[method-assign]
    return gh


def test_validar_repo_aceita_owner_repo():
    assert validar_repo("MariaHilmar/avoa-brain") == "MariaHilmar/avoa-brain"
    assert validar_repo("  org/repo-name  ") == "org/repo-name"


@pytest.mark.parametrize(
    "ruim",
    [
        "",
        "so-owner",
        "../etc/passwd",
        "a/b/c",
        "owner/repo?x=1",
        "owner/repo#frag",
        "owner/repo/../../x",
        "http://evil.com/x",
    ],
)
def test_validar_repo_rejeita_formatos_invalidos(ruim):
    with pytest.raises(RepoInvalidoError):
        validar_repo(ruim)


def test_adapter_rejeita_repo_invalido(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    with pytest.raises(RepoInvalidoError):
        GitHubAdapter(token="tok", repo="nao-e-valido")


def test_buscar_issue_rejeita_id_nao_numerico(adapter):
    with pytest.raises(IssueIdInvalidoError):
        adapter.buscar_issue("../secrets")
    with pytest.raises(IssueIdInvalidoError):
        adapter.buscar_issue("abc")


def test_buscar_issue_feliz(adapter):
    adapter._http = _FakeHTTP(  # type: ignore[method-assign]
        issue_por_id={"24": _issue(24, titulo="[F3] Rastreabilidade", labels=["fase-3"])}
    )
    h = adapter.buscar_issue("24")
    assert h.id == "24"
    assert h.titulo.startswith("[F3]")
    assert len(h.criterios_aceite) == 1
    assert h.status == Status.PRONTA


def test_criar_issue_envia_titulo_e_corpo(adapter):
    adapter._http = _FakeHTTP(post_criar={"number": 88})  # type: ignore[method-assign]
    historia = Historia(
        id="",
        titulo="Nova HU",
        narrativa="Como user, quero X, para Y.",
        criterios_aceite=[
            CriterioAceite(id="c1", descricao="", formato_gherkin="Dado a\nQuando b\nEntão c")
        ],
    )
    numero = adapter.criar_issue(historia)
    assert numero == "88"
    metodo, path, body = adapter._http.chamadas[-1]
    assert metodo == "POST"
    assert path.endswith("/issues")
    assert body["title"] == "Nova HU"
    assert "Critérios de aceite" in body["body"]
    assert "Dado a" in body["body"]


def test_atualizar_status_fecha_issue(adapter):
    adapter._http = _FakeHTTP()  # type: ignore[method-assign]
    adapter.atualizar_status("10", Status.CONCLUIDA.value)
    metodo, path, body = adapter._http.chamadas[-1]
    assert metodo == "PATCH"
    assert path.endswith("/issues/10")
    assert body == {"state": "closed"}


def test_listar_sprint_usa_milestone(adapter):
    adapter._http = _FakeHTTP(  # type: ignore[method-assign]
        paginas={1: [_issue(1, labels=["fase-3"]), _issue(2, pr=True)]}
    )
    sprint = adapter.listar_sprint("3")
    assert sprint.id == "3"
    assert len(sprint.historias) == 1
    assert sprint.historias[0].id == "1"
    assert adapter._http.chamadas[0][2]["milestone"] == "3"


def test_buscar_similares(adapter):
    adapter._http = _FakeHTTP(  # type: ignore[method-assign]
        search_items=[_issue(5, titulo="Recuperar senha")]
    )
    similares = adapter.buscar_similares("senha", limite=3)
    assert len(similares) == 1
    assert similares[0].id == "5"
    params = adapter._http.chamadas[0][2]
    assert params["per_page"] == 3
    assert "senha" in params["q"]


def test_http_erro_401_propaga(adapter):
    adapter._http = _FakeHTTP(  # type: ignore[method-assign]
        issue_por_id={"1": _issue(1)},
        status_por_path={"/repos/owner/repo/issues/1": 401},
    )
    with pytest.raises(httpx.HTTPStatusError):
        adapter.buscar_issue("1")


def test_vincular_pr_rejeita_url_fora_github(adapter):
    with pytest.raises(ValueError, match="pr_url inválida"):
        adapter.vincular_pr("1", "https://evil.example/phish")
    with pytest.raises(ValueError, match="pr_url inválida"):
        adapter.vincular_pr("1", "javascript:alert(1)")


def test_vincular_pr_aceita_url_github(adapter):
    adapter.vincular_pr("42", "https://github.com/o/r/pull/7")
    _metodo, path, body = adapter._http.chamadas[-1]
    assert path.endswith("/issues/42/comments")
    assert "github.com/o/r/pull/7" in body["body"]


def test_listar_issues_filtra_labels_or(adapter):
    adapter._http = _FakeHTTP(  # type: ignore[method-assign]
        paginas={
            1: [
                _issue(1, labels=["fase-3"]),
                _issue(2, labels=["fase-4"]),
                _issue(3, labels=["bug"]),
                _issue(4, labels=["fase-3", "tipo:agente"], pr=True),
            ],
        }
    )

    historias = adapter.listar_issues(
        state="open",
        labels=["fase-3", "fase-4"],
        labels_any=True,
    )

    assert [h.id for h in historias] == ["1", "2"]
    assert all(h.criterios_aceite for h in historias)
    assert adapter._http.chamadas[0][2]["state"] == "open"
    assert "labels" not in (adapter._http.chamadas[0][2] or {})


def test_listar_issues_labels_and_passa_parametro_api(adapter):
    adapter._http = _FakeHTTP(paginas={1: [_issue(10, labels=["fase-3"])]})  # type: ignore[method-assign]

    historias = adapter.listar_issues(
        labels=["fase-3", "tipo:agente"],
        labels_any=False,
    )

    assert len(historias) == 1
    params = adapter._http.chamadas[0][2]
    assert params["labels"] == "fase-3,tipo:agente"


def test_listar_issues_pagina_duas_paginas(adapter):
    pagina1 = [_issue(i, labels=["fase-3"]) for i in range(1, 101)]
    pagina2 = [_issue(101, labels=["fase-3"]), _issue(102, labels=["fase-4"])]

    adapter._http = _FakeHTTP(paginas={1: pagina1, 2: pagina2})  # type: ignore[method-assign]

    historias = adapter.listar_issues(labels=["fase-3"], labels_any=True)

    assert len(historias) == 101
    assert len(adapter._http.chamadas) == 2
    assert adapter._http.chamadas[1][2]["page"] == 2


def test_listar_issues_exclui_pull_requests(adapter):
    adapter._http = _FakeHTTP(  # type: ignore[method-assign]
        paginas={1: [_issue(1, labels=["fase-3"]), _issue(2, labels=["fase-3"], pr=True)]}
    )

    historias = adapter.listar_issues(labels=["fase-3"], labels_any=True)

    assert len(historias) == 1
    assert historias[0].id == "1"
