"""Testa orquestrador e loop crítico-redator com um LLM falso (sem API)."""

from core.agents.base import Agent
from core.agents.orchestrator import Orchestrator
from core.llm.client import LLMClient


def fake_transport(modelo, system, user):
    # devolve algo determinístico e conta tokens fake
    return (f"[{modelo}] ok", 3, 2)


def make_llm():
    return LLMClient(transport=fake_transport)


class Maiusculador(Agent):
    tarefa = "redigir_historia"
    system = "s"

    def montar_prompt(self, ctx):
        return ctx["texto"]

    def aplicar(self, ctx, resposta):
        ctx["saida"] = resposta
        return ctx


class Redator(Agent):
    tarefa = "redigir_historia"

    def montar_prompt(self, ctx):
        return ctx.get("texto", "")

    def aplicar(self, ctx, resposta):
        ctx["rascunho"] = resposta
        ctx["tentativas"] = ctx.get("tentativas", 0) + 1
        return ctx


class Critico(Agent):
    tarefa = "criticar_historia"

    def montar_prompt(self, ctx):
        return ctx.get("rascunho", "")

    def aplicar(self, ctx, resposta):
        # aprova só na 2a tentativa (exercita o loop)
        ctx["aprovado"] = ctx.get("tentativas", 0) >= 2
        return ctx


def test_orquestrador_encadeia():
    llm = make_llm()
    orq = Orchestrator([Maiusculador(llm)])
    out = orq.run({"texto": "abc"})
    assert out["saida"].endswith("ok")
    assert len(orq.trace) == 1
    assert llm.usage.total_tokens == 5


def test_loop_critico_redator():
    llm = make_llm()
    orq = Orchestrator([])
    out = orq.run_com_loop({"texto": "x"}, Redator(llm), Critico(llm), max_iter=3)
    assert out["aprovado"] is True
    assert out["tentativas"] == 2  # redator rodou 2x até o crítico aprovar
