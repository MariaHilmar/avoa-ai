"""Testes do núcleo compartilhado complementado (issues F0 #8, #48-51, #55, #56)."""

from datetime import datetime

from core.billing import pode_usar
from core.domain.consultas import (
    agrupar_por_componente,
    agrupar_por_release,
    filtrar_por_componente,
)
from core.domain.models import (
    CriterioAceite,
    Estimativa,
    Historia,
    Plano,
    Status,
    TipoVinculo,
    Usuario,
    WorkflowConfig,
)
from core.persistence.projecao import ProjecaoIssues
from core.persistence.repository import InMemoryRepository, SQLiteRepository
from core.quality.checklists import aplicar_dor, definition_of_done


# ---- #8 flag de plano -------------------------------------------------------

def test_pode_usar_free_vs_pro():
    free = Usuario(id="u1", plano=Plano.FREE)
    pro = Usuario(id="u2", plano=Plano.PRO)
    assert pode_usar("refinar", free) is True          # feature base
    assert pode_usar("integracao_jira", free) is False  # exige pro
    assert pode_usar("integracao_jira", pro) is True
    assert pode_usar("rag_backlog_grande", Plano.FREE) is False


# ---- #48 vínculos entre histórias -------------------------------------------

def test_vinculos_depende_e_bloqueia():
    a = Historia(id="A", titulo="A")
    a.adicionar_vinculo(TipoVinculo.DEPENDE_DE, "B")
    a.adicionar_vinculo(TipoVinculo.BLOQUEIA, "C")
    assert a.dependencias() == ["B"]
    assert a.bloqueios() == ["C"]


# ---- #50 WorkflowConfig + WIP -----------------------------------------------

def test_workflow_wip_por_coluna():
    wf = WorkflowConfig(estados=["backlog", "em_andamento", "concluido"],
                        wip_limits={"em_andamento": 1})
    hs = [Historia(id=str(i), titulo="h", status=Status.EM_ANDAMENTO) for i in range(2)]
    assert wf.wip(hs)["em_andamento"] == 2
    assert wf.colunas_excedidas(hs) == {"em_andamento": 2}


# ---- #51 componente / release -----------------------------------------------

def test_agrupar_por_componente_e_release():
    hs = [
        Historia(id="1", titulo="a", componente="checkout", release_id="v1"),
        Historia(id="2", titulo="b", componente="checkout", release_id="v2"),
        Historia(id="3", titulo="c", componente="login", release_id="v1"),
    ]
    assert len(filtrar_por_componente(hs, "checkout")) == 2
    assert set(agrupar_por_componente(hs)) == {"checkout", "login"}
    assert len(agrupar_por_release(hs)["v1"]) == 2


# ---- #49 DoR / DoD ----------------------------------------------------------

def test_dor_marca_pronta():
    h = Historia(id="h", titulo="t")
    pronta, faltantes = aplicar_dor(h)
    assert pronta is False and h.pronta is False and faltantes  # crua não passa

    h.narrativa = "Como usuário, quero X, para Y"
    h.criterios_aceite = [CriterioAceite(id="c1", descricao="ok")]
    h.pontos = 3
    pronta, faltantes = aplicar_dor(h)
    assert pronta is True and h.pronta is True and faltantes == []


def test_dod_base_do_revisor():
    dod = definition_of_done()
    h = Historia(id="h", titulo="t", criterios_aceite=[CriterioAceite(id="c", descricao="x")])
    passou, faltantes = dod.avaliar(h)
    assert passou is False and "tem casos de teste vinculados" in faltantes


# ---- #55 Repository (memory + sqlite, incl. append-only) --------------------

def _round_trip(repo):
    h = Historia(id="H1", titulo="Refinada", pontos=5, status=Status.PRONTA)
    repo.salvar(h)
    achada = repo.buscar(Historia, "H1")
    assert achada is not None and achada.titulo == "Refinada"
    assert achada.status == Status.PRONTA  # enum preservado
    # upsert não duplica
    h.titulo = "Refinada v2"
    repo.salvar(h)
    assert repo.buscar(Historia, "H1").titulo == "Refinada v2"
    assert len(repo.listar(Historia)) == 1


def test_repositorio_memoria():
    _round_trip(InMemoryRepository())


def test_repositorio_sqlite():
    _round_trip(SQLiteRepository(":memory:"))


def test_append_only_nao_sobrescreve():
    for repo in (InMemoryRepository(), SQLiteRepository(":memory:")):
        m1 = Estimativa(historia_id="H1", pontos=3)
        m2 = Estimativa(historia_id="H1", pontos=5)  # mesma história, outra medição
        repo.anexar(m1)
        repo.anexar(m2)
        registros = repo.listar(Estimativa)
        assert len(registros) == 2  # histórico preservado, nada sobrescrito


# ---- #56 projeção/cache das issues ------------------------------------------

class _FakeTracker:
    """IssueTracker mínimo: o tracker é a fonte da verdade."""
    def __init__(self):
        self.dados = {"42": Historia(id="42", titulo="Do tracker")}

    def buscar_issue(self, id_externo):
        return self.dados[id_externo]


def test_projecao_le_do_tracker_sem_ser_mestra():
    tracker = _FakeTracker()
    repo = InMemoryRepository()
    proj = ProjecaoIssues(tracker, repo)
    assert proj.sincronizar(["42"]) == 1
    local = proj.ler("42")
    assert local.titulo == "Do tracker"
    assert local.metadados.get("projecao") is True  # marcada como cópia de leitura
