"""Adaptador GitHub - implementa CodeHost via REST API.

Leitura de PRs, diffs e (stubs) commits/checks. Não posta reviews
automaticamente - isso fica na camada de aplicação (Revisor).

Requer GITHUB_TOKEN e GITHUB_REPO (owner/repo), ou via args.
"""

from __future__ import annotations

import os
import re

import httpx

from core.integrations.dtos import CommitInfo, PullRequest, StatusChecks
from core.integrations.github_adapter import RepoInvalidoError, validar_repo

_API = "https://api.github.com"
_RE_PR = re.compile(r"^\d+$")
# Limite defensivo do diff em caracteres (~8k tokens ≈ 32k chars).
_DIFF_MAX_CHARS = 32_000


class PrNumeroInvalidoError(ValueError):
    """Número de PR não numérico ou fora do intervalo."""


class GitHubCodeHost:
    """CodeHost mínimo para o Revisor de PR (Fase 4)."""

    def __init__(self, token: str | None = None, repo: str | None = None) -> None:
        self._token = token or os.environ["GITHUB_TOKEN"]
        self._repo = validar_repo(repo or os.environ["GITHUB_REPO"])
        self._http = httpx.Client(
            base_url=_API,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

    @property
    def repo(self) -> str:
        return self._repo

    @staticmethod
    def _validar_pr(numero: int | str) -> int:
        raw = str(numero).strip()
        if not _RE_PR.fullmatch(raw):
            raise PrNumeroInvalidoError(
                f"número de PR inválido: {numero!r} (esperado inteiro positivo)"
            )
        n = int(raw)
        if n < 1:
            raise PrNumeroInvalidoError(
                f"número de PR inválido: {numero!r} (esperado inteiro positivo)"
            )
        return n

    def buscar_pr(self, numero: int) -> PullRequest:
        """Metadados do PR (título, body, url, state, etc.)."""
        n = self._validar_pr(numero)
        r = self._http.get(f"/repos/{self._repo}/pulls/{n}")
        r.raise_for_status()
        data = r.json()
        return PullRequest(
            numero=int(data.get("number", n)),
            titulo=data.get("title") or "",
            body=data.get("body") or "",
            url=data.get("html_url") or "",
            state=data.get("state") or "",
            merged=bool(data.get("merged")),
            head_sha=(data.get("head") or {}).get("sha") or "",
            base_ref=(data.get("base") or {}).get("ref") or "",
            user=((data.get("user") or {}).get("login") or ""),
        )

    def buscar_diff(self, pr_numero: int) -> str:
        """Unified diff do PR (truncado para caber no prompt do Crítico)."""
        n = self._validar_pr(pr_numero)
        r = self._http.get(
            f"/repos/{self._repo}/pulls/{n}",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github.diff",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        r.raise_for_status()
        texto = r.text or ""
        if len(texto) > _DIFF_MAX_CHARS:
            return (
                texto[:_DIFF_MAX_CHARS]
                + f"\n\n...[diff truncado em {_DIFF_MAX_CHARS} caracteres]...\n"
            )
        return texto

    def listar_commits(self, pr_numero: int) -> list[CommitInfo]:
        """Stub Fase 4: lista vazia (sem bloquear o marco).

        Marcado como stub até a issue de webhooks/Checks (#31) / commits reais.
        """
        self._validar_pr(pr_numero)
        return []

    def status_checks(self, pr_numero: int) -> StatusChecks:
        """Stub Fase 4: checks indisponíveis (webhook/Checks = issue #31)."""
        self._validar_pr(pr_numero)
        return StatusChecks(disponivel=False)

    def postar_comentario(self, pr_numero: int, corpo: str) -> str:
        """Comenta no PR (issue comments API). Retorna URL do comentário.

        Bônus do relatório de aderência - não faz parte da porta CodeHost,
        mas reutiliza o mesmo cliente autenticado com mínimo privilégio
        (Issues: Write no token fine-grained).
        """
        n = self._validar_pr(pr_numero)
        body = (corpo or "").strip()
        if not body:
            raise ValueError("corpo do comentário não pode ser vazio")
        if len(body) > 65_536:
            raise ValueError("corpo do comentário excede o limite do GitHub")
        r = self._http.post(
            f"/repos/{self._repo}/issues/{n}/comments",
            json={"body": body},
        )
        r.raise_for_status()
        return str((r.json() or {}).get("html_url") or "")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> GitHubCodeHost:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
