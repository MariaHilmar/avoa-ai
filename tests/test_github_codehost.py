"""Testes do GitHubCodeHost (HTTP mockado, sem rede)."""

from __future__ import annotations

import httpx
import pytest

from core.integrations.dtos import PullRequest, StatusChecks
from core.integrations.github_adapter import RepoInvalidoError
from core.integrations.github_codehost import (
    GitHubCodeHost,
    PrNumeroInvalidoError,
    _DIFF_MAX_CHARS,
)


class _FakeResponse:
    def __init__(
        self,
        payload=None,
        *,
        text: str = "",
        status_code: int = 200,
    ) -> None:
        self._payload = payload
        self.text = text
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


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.get_handler = None
        self.post_handler = None

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs))
        assert self.get_handler is not None
        return self.get_handler(path, **kwargs)

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        assert self.post_handler is not None
        return self.post_handler(path, **kwargs)

    def close(self) -> None:
        pass


@pytest.fixture
def host(monkeypatch) -> GitHubCodeHost:
    monkeypatch.setenv("GITHUB_TOKEN", "tok-teste")
    monkeypatch.setenv("GITHUB_REPO", "MariaHilmar/avoa-refine")
    h = GitHubCodeHost()
    fake = _FakeClient()
    h._http = fake  # type: ignore[assignment]
    h._fake = fake  # type: ignore[attr-defined]
    return h


def test_repo_invalido():
    with pytest.raises(RepoInvalidoError):
        GitHubCodeHost(token="t", repo="nao-e-owner-repo")
    with pytest.raises(RepoInvalidoError):
        GitHubCodeHost(token="t", repo="a/b/c")
    with pytest.raises(RepoInvalidoError):
        GitHubCodeHost(token="t", repo="../evil")


def test_pr_numero_invalido(host: GitHubCodeHost):
    with pytest.raises(PrNumeroInvalidoError):
        host.buscar_pr(0)
    with pytest.raises(PrNumeroInvalidoError):
        host.buscar_pr("abc")
    with pytest.raises(PrNumeroInvalidoError):
        host.buscar_diff(-1)


def test_buscar_pr(host: GitHubCodeHost):
    fake: _FakeClient = host._fake  # type: ignore[attr-defined]

    def _get(path, **kwargs):
        assert path == "/repos/MariaHilmar/avoa-refine/pulls/11"
        return _FakeResponse(
            {
                "number": 11,
                "title": "feat(testes)",
                "body": "Fecha #27",
                "html_url": "https://github.com/MariaHilmar/avoa-refine/pull/11",
                "state": "closed",
                "merged": True,
                "head": {"sha": "abc"},
                "base": {"ref": "main"},
                "user": {"login": "MariaHilmar"},
            }
        )

    fake.get_handler = _get
    pr = host.buscar_pr(11)
    assert isinstance(pr, PullRequest)
    assert pr.numero == 11
    assert pr.titulo == "feat(testes)"
    assert "Fecha #27" in pr.body
    assert pr.merged is True


def test_buscar_diff_trunca(host: GitHubCodeHost):
    fake: _FakeClient = host._fake  # type: ignore[attr-defined]
    grande = "x" * (_DIFF_MAX_CHARS + 500)

    def _get(path, **kwargs):
        headers = kwargs.get("headers") or {}
        assert "diff" in headers.get("Accept", "")
        return _FakeResponse(text=grande)

    fake.get_handler = _get
    diff = host.buscar_diff(11)
    assert len(diff) < len(grande)
    assert "truncado" in diff


def test_stubs_commits_e_checks(host: GitHubCodeHost):
    assert host.listar_commits(11) == []
    checks = host.status_checks(11)
    assert isinstance(checks, StatusChecks)
    assert checks.disponivel is False
    assert checks.checks == ()


def test_postar_comentario(host: GitHubCodeHost):
    fake: _FakeClient = host._fake  # type: ignore[attr-defined]

    def _post(path, **kwargs):
        assert path.endswith("/issues/11/comments")
        assert kwargs["json"]["body"] == "ok"
        return _FakeResponse(
            {"html_url": "https://github.com/o/r/pull/11#issuecomment-1"}
        )

    fake.post_handler = _post
    url = host.postar_comentario(11, "ok")
    assert "issuecomment" in url


def test_postar_comentario_vazio(host: GitHubCodeHost):
    with pytest.raises(ValueError):
        host.postar_comentario(11, "   ")
