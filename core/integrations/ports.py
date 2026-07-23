"""Portas (interfaces) das integrações do Avoa — Arquitetura Hexagonal.

O núcleo só conhece estas interfaces, nunca uma ferramenta concreta.
Cada ferramenta é um adaptador que as implementa. Ver docs/INTEGRATIONS.md.

Três portas:
  - IssueTracker: issues, épicos, sprints (GitHub, Jira, Azure, GitLab)
  - CodeHost:     PRs, commits, merges, diff (GitHub, GitLab, Azure)
  - CodingAgent:  entrega spec de implementação e recebe resultado (Cursor, Claude)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.domain.models import Historia, Sprint


@runtime_checkable
class IssueTracker(Protocol):
    """Gerência de itens de trabalho num rastreador externo."""

    def criar_issue(self, historia: Historia) -> str: ...
    def buscar_issue(self, id_externo: str) -> Historia: ...
    def atualizar_status(self, id_externo: str, status: str) -> None: ...
    def vincular_pr(self, id_externo: str, pr_url: str) -> None: ...
    def listar_sprint(self, sprint_id: str) -> Sprint: ...
    def buscar_similares(self, texto: str, limite: int = 5) -> list[Historia]: ...


@runtime_checkable
class CodeHost(Protocol):
    """Leitura de informações de código: PRs, commits, merges, diff, checks."""

    def buscar_pr(self, numero: int) -> dict: ...
    def listar_commits(self, pr_numero: int) -> list[dict]: ...
    def buscar_diff(self, pr_numero: int) -> str: ...
    def status_checks(self, pr_numero: int) -> dict: ...


@runtime_checkable
class CodingAgent(Protocol):
    """Handoff para um agente de código externo.

    Nível 1 (comece aqui): entrega por artefato (SPEC.md / comentário na issue).
    Nível 2 (depois): integração via SDK headless / hooks.
    O Avoa NÃO gera código — apenas entrega o contexto do requisito.
    """

    def enviar_spec(self, historia: Historia, spec: str) -> str: ...
    def receber_resultado(self, referencia: str) -> dict: ...


@runtime_checkable
class Repository(Protocol):
    """Persistência dos dados DO AVOA (rascunhos, métricas, poker, traces).

    NÃO é a fonte da verdade das issues — essa é o IssueTracker do cliente.
    Backend plugável: SQLite (dev) ou Postgres/Supabase (produção).
    Ver docs/PERSISTENCE.md.
    """

    def salvar(self, entidade: object) -> str: ...
    def buscar(self, tipo: type, id_: str) -> object | None: ...
    def listar(self, tipo: type, **filtros) -> list: ...
    def anexar(self, entidade: object) -> str: ...  # append-only (métricas, execuções)
