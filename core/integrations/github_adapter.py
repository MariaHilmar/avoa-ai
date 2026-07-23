"""Adaptador GitHub — implementa IssueTracker via REST API.

Traduz entre o modelo neutro do Avoa (Historia) e as issues do GitHub.
O GitHub é a fonte da verdade das issues (ver docs/PERSISTENCE.md).
Requer GITHUB_TOKEN e GITHUB_REPO (owner/repo) no ambiente.
"""

from __future__ import annotations

import os

import httpx

from core.domain.models import Historia, Sprint, Status

_API = "https://api.github.com"


class GitHubAdapter:
    def __init__(self, token: str | None = None, repo: str | None = None) -> None:
        self._token = token or os.environ["GITHUB_TOKEN"]
        self._repo = repo or os.environ["GITHUB_REPO"]  # "owner/repo"
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
        return Historia(
            id=str(issue["number"]),
            titulo=issue["title"],
            narrativa=issue.get("body") or "",
            status=estado,
            metadados={"origem": "github", "url": issue.get("html_url")},
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

    def buscar_issue(self, id_externo: str) -> Historia:
        r = self._http.get(f"/repos/{self._repo}/issues/{id_externo}")
        r.raise_for_status()
        return self._para_historia(r.json())

    def atualizar_status(self, id_externo: str, status: str) -> None:
        estado = "closed" if status == Status.CONCLUIDA.value else "open"
        r = self._http.patch(
            f"/repos/{self._repo}/issues/{id_externo}", json={"state": estado}
        )
        r.raise_for_status()

    def vincular_pr(self, id_externo: str, pr_url: str) -> None:
        r = self._http.post(
            f"/repos/{self._repo}/issues/{id_externo}/comments",
            json={"body": f"PR relacionado: {pr_url}"},
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

    def buscar_similares(self, texto: str, limite: int = 5) -> list[Historia]:
        q = f"repo:{self._repo} is:issue {texto}"
        r = self._http.get("/search/issues", params={"q": q, "per_page": limite})
        r.raise_for_status()
        return [self._para_historia(i) for i in r.json().get("items", [])]
