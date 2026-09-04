.PHONY: up down generate load validate benchmark report ui all help

VENV_PYTHON = ./venv/bin/python

help:
	@echo "ClickHouse vs PostgreSQL Benchmark Automation Targets:"
	@echo "  make up        - Start database containers via docker compose"
	@echo "  make generate  - Generate synthetic star schema datasets (10M & 1M rows)"
	@echo "  make load      - Bulk load dataset into PostgreSQL and ClickHouse"
	@echo "  make validate  - Validate row counts and checksum parity across DBs"
	@echo "  make benchmark - Execute complete query benchmark suite & concurrency test"
	@echo "  make report    - Generate visualization charts in results/"
	@echo "  make ui        - Launch Interactive Web UI Dashboard (http://localhost:5050)"
	@echo "  make down      - Tear down containers and clean up volumes"
	@echo "  make all       - End-to-end execution of all steps in sequence"

ui:
	@echo "Launching Interactive Web Dashboard on http://127.0.0.1:5050..."
	$(VENV_PYTHON) web_ui/app.py

up:
	@echo "Starting PostgreSQL and ClickHouse containers..."
	docker compose up -d
	@echo "Waiting for containers to become healthy..."
	@until [ "$$(docker inspect --format='{{.State.Health.Status}}' benchmark_postgres 2>/dev/null)" = "healthy" ] && \
	       [ "$$(docker inspect --format='{{.State.Health.Status}}' benchmark_clickhouse 2>/dev/null)" = "healthy" ]; do \
		echo "Waiting for healthy database instances..."; \
		sleep 2; \
	done
	@echo "Database containers are up and healthy!"

generate:
	@echo "Generating synthetic dataset..."
	$(VENV_PYTHON) scripts/generate_data.py --scale both

load:
	@echo "Loading dataset into databases..."
	$(VENV_PYTHON) scripts/load_data.py --scale 10m

validate:
	@echo "Validating data parity..."
	$(VENV_PYTHON) scripts/validate_data.py

benchmark:
	@echo "Executing query benchmark suite..."
	$(VENV_PYTHON) scripts/run_benchmark.py --repetitions 5

report:
	@echo "Generating visualization charts..."
	$(VENV_PYTHON) scripts/generate_charts.py

down:
	@echo "Stopping database containers and removing volumes..."
	docker compose down -v

all: up generate load validate benchmark report
	@echo "=========================================="
	@echo "END-TO-END BENCHMARK SUITE SUCCESSFULLY EXECUTED!"
	@echo "=========================================="
