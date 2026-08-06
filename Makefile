.DEFAULT_GOAL := help

.PHONY: help setup test smoke-dry smoke-real pilot-private pilot-shared report

help:
	@echo "Uso rápido:"
	@echo "  make test                                      testes locais, sem chamadas"
	@echo "  make smoke-dry                                smoke simulado, sem chamadas"
	@echo "  make smoke-real                               smoke DeepSeek de 8 chamadas"
	@echo "  make pilot-private                            piloto científico private"
	@echo "  make pilot-shared CONFIRM=YES                 piloto científico shared"
	@echo "  make report RUN=data/runs/<run-id>             notebook + HTML"

setup:
	uv sync

test:
	uv run python -m unittest discover -s tests -v

smoke-dry:
	uv run python -m emergent_specialization.experiment \
		--config configs/smoke_real_private.yaml \
		--dry-run

smoke-real:
	./scripts/run-deepseek-experiment.sh \
		--config configs/smoke_real_private.yaml

pilot-private:
	./scripts/run-deepseek-experiment.sh \
		--config configs/pilot_private.yaml

pilot-shared:
	@test "$(CONFIRM)" = "YES" || \
		(echo "Para iniciar o piloto shared, use: make pilot-shared CONFIRM=YES"; exit 1)
	./scripts/run-deepseek-experiment.sh \
		--config configs/pilot_shared.yaml

report:
	@test -n "$(RUN)" || \
		(echo "Uso: make report RUN=data/runs/<run-id>"; exit 1)
	uv run --group report emergence-report --run "$(RUN)"
