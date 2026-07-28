# Avoa

> IA que faz o processo ágil decolar - do requisito a produção.

**Avoa** (do nordestino *avoar* - alçar voo, decolar) é uma plataforma de agentes
de IA para o ciclo de desenvolvimento ágil. O diferencial não é escrever código -
é dominar o **processo**: requisitos, critérios de aceite, ritmo de time e dados de
gestão, o lado em que a IA generativa ainda erra mais.

Este repositório é o **núcleo open source** do Avoa: um pequeno framework para
construir agentes de IA sobre um domínio de trabalho ágil, com roteamento de
modelos por custo e integração via Ports & Adapters.

## O ecossistema (visão geral)

O Avoa é uma família de sistemas sobre este núcleo compartilhado:

- **Refine** - refina requisitos: história crua → INVEST + critérios em Gherkin;
  Quality Gate ("SonarQube para requisitos"); gerador de testes.
- **Checks** - valida se um Pull Request atende aos critérios de aceite.
- **Metrics** - board/Kanban e indicadores de processo (lead time, cycle time...).
- **Bridge** - leva o contexto do requisito para ferramentas de código.

> Os sistemas comerciais são desenvolvidos à parte. Este repositório expõe apenas
> o framework técnico.

## O que tem aqui

| Componente | O quê |
|---|---|
| `core/domain` | Modelo neutro (`Historia`, `CriterioAceite`, `CasoTeste`, `Sprint`, vínculos, `casos_por_criterio`...) |
| `core/agents` | Base de agentes + orquestrador (loop crítico-redator) |
| `core/llm` | Roteador de modelos por tarefa (`routing.yaml`; override `AVOA_FORCE_TIER`) |
| `core/integrations` | Ports (`IssueTracker`, `CodeHost`, `CodingAgent`, `Repository`) + adaptadores GitHub |
| `core/integrations/github_parse.py` | Parse do body da issue (INVEST + Gherkin) → `Historia` |
| `core/persistence` | `Repository` (memória + SQLite) e projeção de issues |
| `core/quality` | Checklists DoR / DoD |
| `core/billing` | Flag de plano + `pode_usar` (sem Stripe ainda) |
| `core/observability` | Contagem de uso (tokens/custo) |
| `tests/` | Suite automatizada do núcleo (ver abaixo) |
| `evals/` | Convenção de evals de agentes (casos reais vivem nos módulos, ex. Refine) |

## Ideias centrais

- **Modelo certo para a tarefa certa** - cada tarefa é roteada para um tier
  (leve/médio/pesado) via `core/llm/routing.yaml`. Extração usa modelo barato;
  raciocínio usa modelo capaz.
- **Ports & Adapters** - o núcleo fala com interfaces (`IssueTracker`, `CodeHost`...),
  não com ferramentas concretas. Trocar GitHub por Jira = um adaptador novo.
- **Orquestração multi-agente** - agentes especializados compostos por um
  orquestrador, com loop de qualidade crítico↔redator.
- **Rastreabilidade** - caso de teste ↔ critério; RN ↔ HU; PR ↔ história
  (`VinculoPR`) - base do Quality Gate e do Revisor de PR.

Visão de arquitetura: [docs/OVERVIEW.md](docs/OVERVIEW.md).

## Instalar e rodar

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

Variáveis opcionais: copie [`.env.example`](.env.example) para `.env`
(`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPO`). Os testes unitários
**não** precisam de chave nem de rede - usam fakes.

## Testes

A suite em `tests/` cobre o contrato do núcleo. Rode antes de abrir PR:

```bash
python -m pytest tests/ -q
```

| Arquivo | O que valida |
|---|---|
| `test_nucleo.py` | Domínio (vínculos, WIP, DoR/DoD, `casos_por_criterio`), `pode_usar`, Repository, projeção |
| `test_router.py` | Roteamento tarefa → tier / modelo |
| `test_orchestrator.py` | Encadeamento de agentes + loop crítico-redator |
| `test_github_adapter.py` | `GitHubAdapter` (`IssueTracker`): CRUD, labels, listagem, validação de repo/URL |
| `test_github_parse.py` | Parse Gherkin/INVEST do body → critérios (`tests/fixtures/github_bodies/`) |
| `test_github_codehost.py` | `GitHubCodeHost` (`CodeHost`): PR, diff (com truncagem), comentário, validação |

Fixtures em `tests/fixtures/github_bodies/` usam corpos no formato das issues do
backlog Avoa (Project #9), para o parse não regressar no dogfood do Quality Gate.

> **Evals de agentes** (qualidade de saída com LLM) não ficam todos neste repo:
> o harness do Refina / Gerador de Testes / Revisor vive em `avoa-refine/evals/`.
> Aqui, `evals/` documenta a convenção; use `AVOA_FORCE_TIER=leve` para baratear
> evals reais. Detalhes: [evals/README.md](evals/README.md).

## Licença

A definir.
