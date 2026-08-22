.DEFAULT_GOAL := help

.PHONY: help setup test smoke-dry smoke-real pilot-private pilot-shared direct-plan direct-doctor direct-benchmark pair-private pair-shared health report

help:
	@echo "Uso rápido:"
	@echo "  make test                                      testes locais, sem chamadas"
	@echo "  make smoke-dry                                smoke simulado, sem chamadas"
	@echo "  make smoke-real                               smoke DeepSeek de 8 chamadas"
	@echo "  make pilot-private                            piloto científico private"
	@echo "  make pilot-shared CONFIRM=YES                 piloto científico shared"
	@echo "  make direct-plan                              plano direto, sem chamadas"
	@echo "  make direct-doctor                            doctor direto offline"
	@echo "  make direct-benchmark                         plano benchmark, sem chamadas"
	@echo "  make pair-private CONFIRM=YES                par direto private (real)"
	@echo "  make pair-shared CONFIRM=YES                 par direto shared (real)"
	@echo "  make health RUN=data/runs/<run-id>            health offline"
	@echo "  make report RUN=data/runs/<run-id>             notebook + HTML"

setup:
	uv sync

test:
	uv run python -m unittest discover -s tests -v

smoke-dry:
	uv run python -m emergent_specialization.runtime.experiment \
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

direct-plan:
	uv run python -m emergent_specialization.runtime.batch \
		--config configs/research/batches/private_shared_replication_5seeds.yaml \
		--plan --only-seed 1 --json

direct-doctor:
	uv run python -m emergent_specialization.runtime.doctor

direct-benchmark:
	uv run python -m emergent_specialization.runtime.benchmark.deepseek \
		--concurrency 4,8,16,32 --jobs-per-level 32

pair-private:
	@test "$(CONFIRM)" = "YES" || \
		(echo "Para chamadas reais, use: make pair-private CONFIRM=YES"; exit 1)
	uv run python -m emergent_specialization.runtime.experiment \
		--config configs/research/replication_private.yaml \
		--seed 1 --output-dir data/runs/replication --confirm-real

pair-shared:
	@test "$(CONFIRM)" = "YES" || \
		(echo "Para chamadas reais, use: make pair-shared CONFIRM=YES"; exit 1)
	uv run python -m emergent_specialization.runtime.experiment \
		--config configs/research/replication_shared.yaml \
		--seed 1 --output-dir data/runs/replication --confirm-real

health:
	@test -n "$(RUN)" || (echo "Uso: make health RUN=data/runs/<run-id>"; exit 1)
	uv run python -m emergent_specialization.runtime.health --run "$(RUN)"

report:
	@test -n "$(RUN)" || \
		(echo "Uso: make report RUN=data/runs/<run-id>"; exit 1)
	uv run --group report emergence-report --run "$(RUN)"
