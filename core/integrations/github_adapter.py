"""Adaptador GitHub - implementa IssueTracker via REST API.

Traduz entre o modelo neutro do Avoa (Historia) e as issues do GitHub.
O GitHub é a fonte da verdade das issues (ver docs/PERSISTENCE.md).
Requer GITHUB_TOKEN e GITHUB_REPO (owner/repo) no ambiente, ou via args.
"""

from __future__ import annotations

import os
import re

import httpx

from core.domain.models import Historia, Sprint, Status
from core.integrations.github_parse import parse_corpo_issue

_API = "https://api.github.com"
# owner/repo - letras, dígitos, ponto, hífen, underscore (formato GitHub).
_RE_REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
_RE_ISSUE_ID = re.compile(r"^\d+$")


class RepoInvalidoError(ValueError):
    """GITHUB_REPO / repo fora do formato owner/repo."""


class IssueIdInvalidoError(ValueError):
    """id_externo de issue não numérico."""


def validar_repo(repo: str) -> str:
    """Valida e normaliza `owner/repo`. Rejeita path traversal e lixo."""
    repo = (repo or "").strip()
    if not _RE_REPO.fullmatch(repo):
        raise RepoInvalidoError(
            f"repo inválido: {repo!r} (esperado 'owner/repo')"
        )
    return repo


class GitHubAdapter:
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
            timeout=20,
        )

    # ---- tradução ----
    def _para_historia(self, issue: dict) -> Historia:
        estado = Status.CONCLUIDA if issue.get("state") == "closed" else Status.PRONTA
        body = issue.get("body") or ""
        narrativa, criterios = parse_corpo_issue(body)
        labels = [
            (lb.get("name") if isinstance(lb, dict) else str(lb))
            for lb in (issue.get("labels") or [])
        ]
        return Historia(
            id=str(issue["number"]),
            titulo=issue["title"],
            narrativa=narrativa,
            status=estado,
            criterios_aceite=criterios,
            metadados={
                "origem": "github",
                "url": issue.get("html_url"),
                "labels": labels,
            },
        )

    def _corpo(self, h: Historia) -> str:
        partes = [h.narrativa or ""]
        if h.criterios_aceite:
            partes.append("\n\n### Critérios de aceite")
            for c in h.criterios_aceite:
                partes.append(f"- {c.formato_gherkin or c.descricao}")
        return "\n".join(partes).strip()

    # ---- IssueTracker ----
    def criar_issue(self, historia: Historia) -> str:
        r = self._http.post(
            f"/repos/{self._repo}/issues",
            json={"title": historia.titulo, "body": self._corpo(historia)},
        )
        r.raise_for_status()
        return str(r.json()["number"])

    @staticmethod
    def _validar_issue_id(id_externo: str) -> str:
        id_ = str(id_externo).strip()
        if not _RE_ISSUE_ID.fullmatch(id_):
            raise IssueIdInvalidoError(
                f"id de issue inválido: {id_externo!r} (esperado número)"
            )
        return id_

    def buscar_issue(self, id_externo: str) -> Historia:
        id_ = self._validar_issue_id(id_externo)
        r = self._http.get(f"/repos/{self._repo}/issues/{id_}")
        r.raise_for_status()
        return self._para_historia(r.json())

    def atualizar_status(self, id_externo: str, status: str) -> None:
        id_ = self._validar_issue_id(id_externo)
        estado = "closed" if status == Status.CONCLUIDA.value else "open"
        r = self._http.patch(
            f"/repos/{self._repo}/issues/{id_}", json={"state": estado}
        )
        r.raise_for_status()

    def vincular_pr(self, id_externo: str, pr_url: str) -> None:
        id_ = self._validar_issue_id(id_externo)
        url = (pr_url or "").strip()
        if not url.startswith(("https://github.com/", "http://github.com/")):
            raise ValueError(
                f"pr_url inválida: {pr_url!r} (esperado URL https://github.com/...)"
            )
        r = self._http.post(
            f"/repos/{self._repo}/issues/{id_}/comments",
            json={"body": f"PR relacionado: {url}"},
        )
        r.raise_for_status()

    def listar_sprint(self, sprint_id: str) -> Sprint:
        # GitHub não tem sprint nativo; usamos Milestone como aproximação.
        r = self._http.get(
            f"/repos/{self._repo}/issues",
            params={"milestone": sprint_id, "state": "all"},
        )
        r.raise_for_status()
        historias = [self._para_historia(i) for i in r.json() if "pull_request" not in i]
        return Sprint(id=sprint_id, nome=f"Milestone {sprint_id}", historias=historias)

    def listar_issues(
        self,
        *,
        state: str = "open",
        labels: list[str] | None = None,
        labels_any: bool = True,
    ) -> list[Historia]:
        """Lista issues (exclui PRs).

        `labels`: filtro por nome de label.
        `labels_any=True` (padrão): OR - a issue precisa ter ao menos uma.
        `labels_any=False`: AND - a API do GitHub já filtra assim.
        """
        params: dict = {"state": state, "per_page": 100}
        if labels and not labels_any:
            params["labels"] = ",".join(labels)

        issues: list[dict] = []
        page = 1
        while True:
            params["page"] = page
            r = self._http.get(f"/repos/{self._repo}/issues", params=params)
            r.raise_for_status()
            lote = r.json()
            if not lote:
                break
            issues.extend(lote)
            if len(lote) < 100:
                break
            page += 1

        historias = [
            self._para_historia(i) for i in issues if "pull_request" not in i
        ]
        if labels and labels_any:
            alvo = {lb.lower() for lb in labels}
            historias = [
                h
                for h in historias
                if alvo & {str(x).lower() for x in (h.metadados or {}).get("labels") or []}
            ]
        return historias

    def buscar_similares(self, texto: str, limite: int = 5) -> list[Historia]:
        q = f"repo:{self._repo} is:issue {texto}"
        r = self._http.get("/search/issues", params={"q": q, "per_page": limite})
        r.raise_for_status()
        return [self._para_historia(i) for i in r.json().get("items", [])]
