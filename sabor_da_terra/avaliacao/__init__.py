"""Avaliação ponta a ponta (etapa 14): o gabarito da #6 contra o assistente integrado.

- `gabarito`: os casos dos YAML, turnos, relógio da sessão e requisitos funcionais;
- `execucao`: roda um caso no `Assistente`, checa funções e citações, chama o juiz;
- `juiz`: o Flash-Lite decide critério a critério (`deve_conter` / `nao_deve_conter`);
- `metricas`: agregados por desafio e por requisito e o relatório do docs/05;
- `clientes`: o cliente híbrido (replay + gravação do que falta) e o consumo da rodada.

Rodada real: `python -m scripts.avaliar_gabarito`. Regressão offline:
`pytest tests/test_gabarito.py`.
"""
