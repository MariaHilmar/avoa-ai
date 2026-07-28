"""DTOs tipados das portas de integração (CodeHost / CodingAgent).

Evita ``dict`` nas bordas do núcleo. Adaptadores mapeiam JSON externo → estes
tipos; módulos consumidores (Refina, Checks, Bridge) leem atributos estáveis.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PullRequest:
    """Metadados neutros de um pull/merge request."""

    numero: int
    titulo: str
    body: str = ""
    url: str = ""
    state: str = ""
    merged: bool = False
    head_sha: str = ""
    base_ref: str = ""
    user: str = ""


@dataclass(frozen=True)
class CommitInfo:
    """Commit associado a um PR (resumo)."""

    sha: str
    mensagem: str = ""
    autor: str = ""
    data_iso: str = ""


@dataclass(frozen=True)
class CheckRun:
    """Um check/CI individual."""

    nome: str
    status: str = ""  # queued | in_progress | completed | ...
    conclusion: str = ""  # success | failure | neutral | ...


@dataclass(frozen=True)
class StatusChecks:
    """Agregado de checks do PR.

    ``disponivel=False`` marca stub / ainda não implementado no adaptador
    (não confundir com "todos os checks passaram").
    """

    disponivel: bool = False
    state: str = ""  # success | pending | failure | error | ""
    checks: tuple[CheckRun, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResultadoCodingAgent:
    """Resposta de um agente de código ao handoff de spec."""

    referencia: str
    status: str = "pendente"  # pendente | concluido | erro
    detalhe: str = ""
    artefatos: tuple[str, ...] = field(default_factory=tuple)
