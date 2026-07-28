# Visão de arquitetura

O núcleo do Avoa é organizado em camadas. Um módulo compõe agentes; agentes usam
tools/domínio; nada fala com a infra diretamente.

```
CAMADA 4 — MÓDULOS         (casos de uso: refinar, quality gate, revisar PR, métricas...)
CAMADA 3 — AGENTES         (Analista, Redator, Crítico, Estimador... + orquestrador)
CAMADA 2 — TOOLS + DOMÍNIO (modelo neutro + Ports & Adapters + checklists + coletor)
CAMADA 1 — INFRA           (roteador de modelos, observabilidade, persistência, billing)
```

## Pacotes em `core/`

| Pacote | Papel |
|---|---|
| `domain` | Entidades neutras (`Historia`, critérios, casos de teste, sprint, vínculos) |
| `agents` | `Agent` ABC + `Orchestrator` (loop crítico-redator) |
| `llm` | Cliente + roteador tarefa → tier → modelo |
| `integrations` | Ports + adaptadores (GitHub `IssueTracker`, parse Gherkin; `CodeHost` quando disponível) |
| `persistence` | `Repository` (memória/SQLite) e projeção de issues do tracker |
| `quality` | DoR / DoD aplicadas pelo Crítico |
| `billing` | Plano + `pode_usar` (preparação freemium, sem checkout) |
| `observability` | `UsageTracker` (tokens/custo) |

## Ports & Adapters

O núcleo conhece apenas interfaces; cada ferramenta é um adaptador:

| Port | Papel | Estado no núcleo |
|---|---|---|
| `IssueTracker` | issues, épicos, sprints | Adaptador GitHub + parse de body (`github_parse`) |
| `CodeHost` | PRs, commits, merges, diff | Port + `GitHubCodeHost` (PR/diff/comentário) na Fase 4 |
| `CodingAgent` | entrega de contexto para ferramentas de código | Port definida (Copiloto / Bridge) |
| `Repository` | persistência dos dados do próprio Avoa | Memória + SQLite |

## Roteamento de modelos

`core/llm/routing.yaml` mapeia `tarefa → tier → modelo`. Isso mantém o custo baixo:
tarefas mecânicas (extração, classificação) vão para o modelo leve; raciocínio
(análise, crítica, estimativa) vai para o modelo pesado. Trocar o tier de uma
tarefa é editar configuração, não código.

Override de ambiente: `AVOA_FORCE_TIER=leve` força um tier único (útil em evals/CI).

## Orquestração

O `Orchestrator` encadeia agentes e oferece um loop crítico-redator: o redator
produz, o crítico avalia contra regras de qualidade e, se reprovar, devolve para
ajuste - até aprovar ou atingir o limite de iterações.

## Testes

Contratos do núcleo cobertos por `pytest` em `tests/` (sem rede, sem API key).
Ver a seção **Testes** no [README](../README.md).
