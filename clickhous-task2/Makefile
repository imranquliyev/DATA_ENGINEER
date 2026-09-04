.PHONY: all setup up generate load validate benchmark report down clean

VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

all: setup up generate load validate benchmark report

setup:
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --quiet --upgrade pip
	@$(PIP) install --quiet numpy pandas psycopg2-binary clickhouse-driver

up:
	docker compose up -d
	@echo "Waiting for databases to accept connections..."
	@sleep 5

generate:
	mkdir -p data
	$(PYTHON) scripts/generate_data.py --rows 10000000 --seed 42

load:
	$(PYTHON) scripts/load_data.py

validate:
	$(PYTHON) scripts/validate.py

benchmark:
	$(PYTHON) scripts/benchmark.py --repetitions 5 --warmup 1

report:
	@echo "Benchmark execution completed. Raw data saved to benchmark_results.json"

down:
	docker compose down -v

clean:
	rm -rf $(VENV) data/*.csv benchmark_results.json