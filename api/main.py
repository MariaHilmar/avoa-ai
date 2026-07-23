"""API do Avoa (FastAPI). Fase 0: healthcheck e verificação do roteador.

Rodar: uvicorn api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from core.llm.router import ModelRouter

app = FastAPI(title="Avoa", version="0.0.1")
_router = ModelRouter()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "produto": "avoa"}


@app.get("/routing/{tarefa}")
def routing(tarefa: str) -> dict:
    """Mostra qual tier/modelo uma tarefa usa (útil para calibrar custo)."""
    return {
        "tarefa": tarefa,
        "tier": _router.tier_de(tarefa),
        "modelo": _router.modelo_de(tarefa),
    }
