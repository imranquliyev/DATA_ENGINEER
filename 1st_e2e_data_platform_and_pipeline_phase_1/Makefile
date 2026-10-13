.PHONY: help up down restart clean ps wait run-pipeline run-failure smoke test lint compile

help:
	@echo "FastRoute Logistics — Phase 1 Walking Skeleton Automation Commands:"
	@echo "  make up            - Launch all docker infrastructure services"
	@echo "  make down          - Stop containers (preserves volume state)"
	@echo "  make restart       - Restart containers"
	@echo "  make clean         - Tear down containers and wipe all persistent volumes"
	@echo "  make ps            - Check container health status"
	@echo "  make wait          - Wait until core services (Postgres, ClickHouse, MinIO) are ready"
	@echo "  make run-pipeline  - Execute 6-stage batch pipeline (e.g. make run-pipeline DATE=2026-10-13)"
	@echo "  make run-failure   - Trigger deliberate ingestion failure to test error propagation"
	@echo "  make smoke         - Execute automated end-to-end smoke test"
	@echo "  make test          - Run unit test suite"
	@echo "  make lint          - Run linter checks (ruff)"
	@echo "  make compile       - Check syntax of all pipeline modules"

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose down && docker compose up -d

clean:
	docker compose down -v

ps:
	docker compose ps

wait:
	./scripts/wait_for_services.sh

run-pipeline:
	./scripts/run_pipeline.sh $(DATE)

run-failure:
	./scripts/trigger_failure.sh $(DATE)

PYTHON := $(shell if [ -f "./.venv/bin/python3" ]; then echo "./.venv/bin/python3"; elif [ -f "../1st_e2e_data_platform_project/.venv/bin/python3" ]; then echo "../1st_e2e_data_platform_project/.venv/bin/python3"; else echo "python3"; fi)

smoke:
	$(PYTHON) -m pytest tests/smoke/test_smoke_pipeline.py -s -v -W ignore

test:
	$(PYTHON) -m pytest tests/unit/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/

compile:
	$(PYTHON) -m compileall src/
