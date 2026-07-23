"""Ponto único de checagem de plano (freemium). Ver docs/BUSINESS.md.

A regra de negócio fica AQUI, num só lugar — nada de `if plano == 'pro'`
espalhado. Ligar no Stripe depois é trocar a fonte do `plano`, não a lógica.
"""

from __future__ import annotations

from core.domain.models import Plano, Usuario

#: Features que exigem plano PRO. As demais são liberadas no FREE.
FEATURES_PRO: frozenset[str] = frozenset(
    {
        "uso_ilimitado",       # sem limite mensal de refinamentos
        "multiplos_projetos",
        "integracao_jira",
        "integracao_azure",
        "kpis_historicos",
        "rag_backlog_grande",
        "processar_backlog_lote",
    }
)


def pode_usar(feature: str, plano: Plano | Usuario) -> bool:
    """True se o plano dá acesso à feature. Aceita um Plano ou um Usuario."""
    p = plano.plano if isinstance(plano, Usuario) else plano
    if feature in FEATURES_PRO:
        return p == Plano.PRO
    return True  # features base: liberadas em qualquer plano
