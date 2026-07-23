"""Projeção/cache local das issues do rastreador.

A fonte da verdade das issues é SEMPRE o rastreador do cliente (IssueTracker).
Esta projeção é uma **cópia de leitura** reconciliada a partir dele — para
desempenho e para relacionar com dados do Avoa — e nunca é tratada como mestra:
não há caminho de escrita da projeção de volta para o tracker aqui. Ver
docs/PERSISTENCE.md.
"""

from __future__ import annotations

from core.integrations.ports import IssueTracker, Repository


class ProjecaoIssues:
    def __init__(self, tracker: IssueTracker, repo: Repository) -> None:
        self._tracker = tracker
        self._repo = repo

    def sincronizar(self, ids_externos: list[str]) -> int:
        """Puxa cada issue do tracker e reconcilia a cópia local. Devolve o total."""
        total = 0
        for id_ext in ids_externos:
            historia = self._tracker.buscar_issue(id_ext)
            historia.metadados["projecao"] = True  # marca como cópia de leitura
            self._repo.salvar(historia)
            total += 1
        return total

    def ler(self, id_externo: str):
        """Lê da projeção local (nunca da rede). Pode estar defasada."""
        from core.domain.models import Historia

        return self._repo.buscar(Historia, id_externo)
