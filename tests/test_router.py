from core.llm.router import ModelRouter


def test_tier_por_tarefa():
    r = ModelRouter()
    assert r.tier_de("extrair_itens") == "leve"
    assert r.tier_de("redigir_historia") == "medio"
    assert r.tier_de("criticar_historia") == "pesado"


def test_modelo_resolve():
    r = ModelRouter()
    assert r.modelo_de("extrair_itens") == r._tiers["leve"]


def test_tarefa_desconhecida():
    r = ModelRouter()
    try:
        r.tier_de("inexistente")
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass
