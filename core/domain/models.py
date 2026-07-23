"""Modelo de domínio neutro do Avoa.

Deliberadamente independente de qualquer ferramenta (GitHub/Jira/...).
Cada adaptador de integração traduz do formato da ferramenta para estas classes.
Ver docs/DATA-MODEL.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Status(str, Enum):
    RASCUNHO = "rascunho"
    PRONTA = "pronta"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"


class MetodoEstimativa(str, Enum):
    MANUAL = "manual"
    PLANNING_POKER = "planning_poker"
    AGENTE = "agente"


class ResultadoTeste(str, Enum):
    PASSOU = "passou"
    FALHOU = "falhou"
    PULADO = "pulado"


class Plano(str, Enum):
    """Plano de assinatura do usuário (freemium). Ver docs/BUSINESS.md."""
    FREE = "free"
    PRO = "pro"


class TipoVinculo(str, Enum):
    """Vínculos entre itens de trabalho (inspirado em Jira/Azure)."""
    DEPENDE_DE = "depende_de"
    BLOQUEIA = "bloqueia"
    RELACIONA = "relaciona"
    DUPLICA = "duplica"


class TipoMetrica(str, Enum):
    """Métricas ágeis clássicas (nomenclatura alinhada ao Azure Analytics)."""
    VELOCITY = "velocity"            # por pontos; alimentada pelo Planning Poker
    BURNDOWN = "burndown"
    CFD = "cfd"                      # cumulative flow diagram
    LEAD_TIME = "lead_time"
    CYCLE_TIME = "cycle_time"
    THROUGHPUT = "throughput"
    WIP = "wip"


@dataclass
class CriterioAceite:
    id: str
    descricao: str
    formato_gherkin: str | None = None  # Dado/Quando/Então


@dataclass
class Tarefa:
    id: str
    titulo: str
    status: Status = Status.RASCUNHO
    responsavel: str | None = None


@dataclass
class ExecucaoTeste:
    id: str
    data: datetime
    resultado: ResultadoTeste
    log: str = ""


@dataclass
class CasoTeste:
    id: str
    titulo: str
    passos: list[str]
    resultado_esperado: str
    tipo: str = "manual"  # manual | automatizado
    criterio_origem_id: str | None = None  # rastreabilidade
    execucoes: list[ExecucaoTeste] = field(default_factory=list)


@dataclass
class Estimativa:
    historia_id: str
    pontos: int
    metodo: MetodoEstimativa = MetodoEstimativa.MANUAL
    confianca: float | None = None


@dataclass
class VinculoPR:
    id: str
    url: str
    numero: int
    atende_criterios: bool | None = None
    analise: str = ""


@dataclass
class VinculoTrabalho:
    """Relação entre duas histórias (depende_de, bloqueia, ...)."""
    tipo: TipoVinculo
    alvo_id: str


@dataclass
class Historia:
    id: str
    titulo: str
    narrativa: str = ""  # "Como <papel>, quero <ação>, para <valor>"
    status: Status = Status.RASCUNHO
    prioridade: int | None = None
    pontos: int | None = None
    componente: str | None = None   # agrupamento (Jira Component / Azure Area Path)
    release_id: str | None = None   # versão/release (fix version)
    pronta: bool = False            # gate de Definition of Ready
    criterios_aceite: list[CriterioAceite] = field(default_factory=list)
    tarefas: list[Tarefa] = field(default_factory=list)
    casos_teste: list[CasoTeste] = field(default_factory=list)
    vinculos_pr: list[VinculoPR] = field(default_factory=list)
    vinculos: list[VinculoTrabalho] = field(default_factory=list)
    metadados: dict = field(default_factory=dict)  # origem, autor, timestamps

    def adicionar_vinculo(self, tipo: TipoVinculo, alvo_id: str) -> None:
        """Registra um vínculo (depende_de/bloqueia/...) com outra história."""
        self.vinculos.append(VinculoTrabalho(tipo=tipo, alvo_id=alvo_id))

    def alvos_por_tipo(self, tipo: TipoVinculo) -> list[str]:
        return [v.alvo_id for v in self.vinculos if v.tipo == tipo]

    def dependencias(self) -> list[str]:
        """Ids das histórias das quais esta depende."""
        return self.alvos_por_tipo(TipoVinculo.DEPENDE_DE)

    def bloqueios(self) -> list[str]:
        """Ids das histórias que esta bloqueia."""
        return self.alvos_por_tipo(TipoVinculo.BLOQUEIA)


@dataclass
class Usuario:
    """Usuário do Avoa. O `plano` deixa a cobrança plugável sem billing agora
    (ver docs/BUSINESS.md); a checagem centralizada é `core.billing.pode_usar`."""
    id: str
    email: str = ""
    plano: Plano = Plano.FREE


@dataclass
class Epico:
    id: str
    titulo: str
    descricao: str = ""
    status: Status = Status.RASCUNHO
    historias: list[Historia] = field(default_factory=list)


@dataclass
class Sprint:
    id: str
    nome: str
    inicio: datetime | None = None
    fim: datetime | None = None
    meta: str = ""
    historias: list[Historia] = field(default_factory=list)
    status: str = "planejada"  # planejada | ativa | encerrada


@dataclass
class Release:
    """Versão/release (equivalente ao 'fix version' do Jira)."""
    id: str
    nome: str
    data_alvo: datetime | None = None
    historia_ids: list[str] = field(default_factory=list)


@dataclass
class Checklist:
    """Definition of Ready / Definition of Done — aplicada pelo Crítico."""
    id: str
    nome: str  # ex.: "Definition of Ready"
    itens: list[str] = field(default_factory=list)


@dataclass
class WorkflowConfig:
    """Estados de workflow configuráveis + limites de WIP (compartilhado por
    Board/Kanban, Sprint e adaptadores). É NÚCLEO, não módulo."""
    estados: list[str] = field(
        default_factory=lambda: ["backlog", "ready", "em_andamento", "revisao", "concluido"]
    )
    wip_limits: dict[str, int] = field(default_factory=dict)  # estado -> limite

    def wip(self, historias: list["Historia"], estado_de=lambda h: h.status.value) -> dict[str, int]:
        """WIP (contagem) por coluna/estado a partir de uma lista de histórias."""
        contagem = {estado: 0 for estado in self.estados}
        for h in historias:
            estado = estado_de(h)
            contagem[estado] = contagem.get(estado, 0) + 1
        return contagem

    def colunas_excedidas(self, historias: list["Historia"], estado_de=lambda h: h.status.value) -> dict[str, int]:
        """Estados cujo WIP atual ultrapassa o limite configurado."""
        wip = self.wip(historias, estado_de)
        return {e: wip[e] for e, lim in self.wip_limits.items() if wip.get(e, 0) > lim}


@dataclass
class Metrica:
    tipo: "TipoMetrica"
    valor: float
    periodo: str
    sprint_id: str | None = None
