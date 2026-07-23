# Visão de arquitetura

O núcleo do Avoa é organizado em camadas. Um módulo compõe agentes; agentes usam
tools/domínio; nada fala com a infra diretamente.

```
CAMADA 4 — MÓDULOS         (casos de uso: refinar, revisar PR, métricas...)
CAMADA 3 — AGENTES         (Analista, Redator, Crítico, Estimador... + orquestrador)
CAMADA 2 — TOOLS + DOMÍNIO (modelo neutro + Ports & Adapters + coletor de métricas)
CAMADA 1 — INFRA           (roteador de modelos, observabilidade, persistência)
```

## Ports & Adapters

O núcleo conhece apenas interfaces; cada ferramenta é um adaptador:

| Port | Papel |
|---|---|
| `IssueTracker` | issues, épicos, sprints (GitHub, e futuros Jira/Azure/GitLab/Linear) |
| `CodeHost` | PRs, commits, merges, diff |
| `CodingAgent` | entrega de contexto para ferramentas de código |
| `Repository` | persistência dos dados do próprio Avoa |

## Roteamento de modelos

`core/llm/routing.yaml` mapeia `tarefa → tier → modelo`. Isso mantém o custo baixo:
tarefas mecânicas (extração, classificação) vão para o modelo leve; raciocínio
(análise, crítica, estimativa) vai para o modelo pesado. Trocar o tier de uma
tarefa é editar configuração, não código.

## Orquestração

O `Orchestrator` encadeia agentes e oferece um loop crítico-redator: o redator
produz, o crítico avalia contra regras de qualidade e, se reprovar, devolve para
ajuste — até aprovar ou atingir o limite de iterações.
