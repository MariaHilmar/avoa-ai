# Avoa

> IA que faz o processo ágil decolar — do requisito ao PR.

**Avoa** (do nordestino *avoar* — alçar voo, decolar) é uma plataforma de agentes
de IA para o ciclo de desenvolvimento ágil. O diferencial não é escrever código —
é dominar o **processo**: requisitos, critérios de aceite, ritmo de time e dados de
gestão, o lado em que a IA generativa ainda erra mais.

Este repositório é o **núcleo open source** do Avoa: um pequeno framework para
construir agentes de IA sobre um domínio de trabalho ágil, com roteamento de
modelos por custo e integração via Ports & Adapters.

## O ecossistema (visão geral)

O Avoa é uma família de sistemas sobre este núcleo compartilhado:

- **Refine** — refina requisitos: história crua → INVEST + critérios em Gherkin.
- **Checks** — valida se um Pull Request atende aos critérios de aceite.
- **Metrics** — board/Kanban e indicadores de processo (lead time, cycle time...).
- **Bridge** — leva o contexto do requisito para ferramentas de código.

> Os sistemas comerciais são desenvolvidos à parte. Este repositório expõe apenas
> o framework técnico.

## O que tem aqui

| Componente | O quê |
|---|---|
| `core/domain` | Modelo de domínio neutro (História, Sprint, Critério...) |
| `core/agents` | Base de agentes + orquestrador (com loop crítico-redator) |
| `core/llm` | Roteador de modelos por tarefa (barato para tarefa simples) |
| `core/integrations` | Ports & Adapters (IssueTracker, CodeHost, CodingAgent, Repository) |
| `core/observability` | Contagem de uso (tokens/custo) |

## Ideias centrais

- **Modelo certo para a tarefa certa** — cada tarefa é roteada para um tier
  (leve/médio/pesado) via `core/llm/routing.yaml`. Extração usa modelo barato;
  raciocínio usa modelo capaz.
- **Ports & Adapters** — o núcleo fala com interfaces (`IssueTracker`, `CodeHost`...),
  não com ferramentas concretas. Trocar GitHub por Jira = um adaptador novo.
- **Orquestração multi-agente** — agentes especializados compostos por um
  orquestrador, com loop de qualidade crítico↔redator.

Visão de arquitetura: [docs/OVERVIEW.md](docs/OVERVIEW.md).

## Rodar

```bash
pip install -e .
python -m pytest tests/ -q
```

## Licença

A definir.
