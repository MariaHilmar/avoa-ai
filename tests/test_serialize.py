"""Round-trip de serialização - cobre colisão Checklist domínio vs qualidade."""

from __future__ import annotations

import dataclasses
import types

import pytest

from core.domain.models import Checklist, Historia, Status
from core.persistence import serialize as ser
from core.quality.checklists import ChecklistAvaliacao, ItemChecklist


def test_registro_tem_checklist_de_dominio():
    assert ser._REGISTRO["Checklist"] is Checklist
    assert "ChecklistAvaliacao" not in ser._REGISTRO
    assert "ItemChecklist" not in ser._REGISTRO


def test_checklist_dominio_round_trip():
    original = Checklist(
        id="dor-padrao",
        nome="Definition of Ready",
        itens=["narrativa INVEST", "tem critério de aceite", "estimada"],
    )
    dados = ser.serialize(original)
    assert dados["__type__"] == "Checklist"
    assert dados["itens"] == original.itens

    restaurado = ser.deserialize(dados)
    assert type(restaurado) is Checklist
    assert restaurado == original


def test_historia_com_status_round_trip():
    h = Historia(id="H1", titulo="Login", status=Status.PRONTA, pontos=3, pronta=True)
    restaurado = ser.deserialize(ser.serialize(h))
    assert type(restaurado) is Historia
    assert restaurado.id == "H1"
    assert restaurado.status is Status.PRONTA
    assert restaurado.pronta is True
    assert restaurado.pontos == 3


def test_colisao_de_nome_no_registro_falha():
    """Guarda: dois dataclasses com o mesmo __name__ não podem coexistir no registro."""

    @dataclasses.dataclass
    class Checklist:  # noqa: F811 - colisão intencional com models.Checklist
        id: str

    fake = types.ModuleType("fake_colisao")
    fake.Checklist = Checklist

    with pytest.raises(RuntimeError, match="Colisão no registro"):
        ser._registrar_dataclasses(fake)


def test_checklist_avaliacao_nao_e_confundida_com_dominio():
    """Runtime com predicado não deve sobrescrever o tipo persistível."""
    avaliacao = ChecklistAvaliacao(
        "DoR",
        [ItemChecklist("ok", lambda h: True)],
    )
    assert type(avaliacao).__name__ == "ChecklistAvaliacao"
    assert ser._REGISTRO["Checklist"] is Checklist
