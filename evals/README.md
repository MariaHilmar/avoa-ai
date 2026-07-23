# Evals

Casos que medem se cada agente **realmente melhora** o item de trabalho
(ex.: a história refinada ganhou critérios claros? o Crítico pega ambiguidades
plantadas?). Ver docs/AGENTS.md.

Rodar tudo no tier `leve` (override em `core/llm/routing.yaml`) barateia a
execução dos evals durante o desenvolvimento.

Estrutura sugerida (a partir da Fase 1):
- `refina/casos.jsonl` — entradas + expectativas
- `refina/test_refina_eval.py` — executa e pontua
