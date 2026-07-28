# Evals

Casos que medem se cada agente **realmente melhora** o item de trabalho
(ex.: a história refinada ganhou critérios claros? o Crítico pega ambiguidades
plantadas?).

## Onde vivem os evals

Este diretório documenta a **convenção**. Os harnesses com casos e scorers
ficam nos módulos que possuem os agentes (prompts = IP privado):

| Módulo | Repo | Pasta típica |
|---|---|---|
| Refina | `avoa-refine` | `evals/refina/` |
| Gerador de Testes | `avoa-refine` | `evals/testes/` |
| Revisor de PR | `avoa-refine` | `evals/revisor/` (quando existir) |

O núcleo (`avoa-ai`) concentra **testes unitários** do domínio, roteador,
orquestrador e adaptadores - ver `tests/` e o [README](../README.md).

## Como baratear

- Override global: `AVOA_FORCE_TIER=leve` (env) força o tier leve em todas as tarefas.
- Ou editar temporariamente `core/llm/routing.yaml`.

## Estrutura sugerida (por módulo)

```
evals/<modulo>/
  casos.jsonl          # entradas + expectativas
  scorer.py            # rubrica
  run_eval.py          # runner
  test_<modulo>_eval.py
```
