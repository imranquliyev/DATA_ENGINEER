# db-migrations-task1 — Cinema domain (3NF + Flyway + Liquibase)
# Run all commands from this directory: cd db-migrations-task1

MODEL   ?= cinema
TOOL    ?= flyway
DOMAINS := cinema

.PHONY: help up down reset demo migrate-all clean-all \
        fw-migrate fw-validate fw-clean fw-info \
        lb-update lb-rollback lb-status lb-clean \
        psql schema-diff

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

check-docker: ## Verify Docker is installed and running
	@command -v docker >/dev/null 2>&1 || { \
		echo "Error: Docker is not installed."; \
		echo ""; \
		echo "Install on Pop!_OS / Ubuntu:"; \
		echo "  sudo apt update"; \
		echo "  sudo apt install -y docker.io docker-compose-v2"; \
		echo "  sudo systemctl enable --now docker"; \
		echo "  sudo usermod -aG docker $$USER   # then log out and back in"; \
		echo ""; \
		echo "Verify: docker compose version"; \
		exit 127; \
	}
	@docker info >/dev/null 2>&1 || { \
		if getent group docker | grep -qw "$$USER"; then \
			echo "Error: You are in the 'docker' group, but this shell has not picked it up yet."; \
			echo ""; \
			echo "Quick fix (same terminal):"; \
			echo "  newgrp docker"; \
			echo "  make demo"; \
			echo ""; \
			echo "Or open a new terminal / log out and back in."; \
		else \
			echo "Error: Docker is installed but not accessible."; \
			echo "  sudo systemctl start docker"; \
			echo "  sudo usermod -aG docker $$USER   # then log out and back in"; \
		fi; \
		exit 1; \
	}

# ── Infrastructure ────────────────────────────────────────────────────────────

up: check-docker ## Start PostgreSQL container
	docker compose up -d postgres
	@echo "Waiting for PostgreSQL..."
	@until docker compose exec postgres pg_isready -U deuser > /dev/null 2>&1; do sleep 1; done
	@echo "PostgreSQL is ready."

down: check-docker ## Stop all containers
	docker compose down

reset: check-docker ## Destroy volumes and restart fresh
	docker compose down -v
	$(MAKE) up

demo: reset migrate-all ## Full clean demo: reset DB + migrate everything
	@echo "Demo complete. Try: make psql MODEL=cinema TOOL=flyway"

# ── Flyway ────────────────────────────────────────────────────────────────────

fw-migrate: up ## Run Flyway migrate for MODEL (default: cinema)
	docker compose run --rm flyway \
		-configFiles=/flyway/conf/$(MODEL).conf migrate

fw-validate: up ## Validate Flyway migrations for MODEL
	docker compose run --rm flyway \
		-configFiles=/flyway/conf/$(MODEL).conf validate

fw-clean: up ## Flyway clean (drops all objects) for MODEL
	docker compose run --rm flyway \
		-configFiles=/flyway/conf/$(MODEL).conf clean

fw-info: up ## Show Flyway migration status for MODEL
	docker compose run --rm flyway \
		-configFiles=/flyway/conf/$(MODEL).conf info

# ── Liquibase ─────────────────────────────────────────────────────────────────

lb-update: up ## Run Liquibase update for MODEL (default: cinema)
	docker compose run --rm liquibase \
		--defaultsFile=/liquibase/conf/$(MODEL).properties update

lb-rollback: up ## Rollback last COUNT changeSets for MODEL (default COUNT=1)
	docker compose run --rm liquibase \
		--defaultsFile=/liquibase/conf/$(MODEL).properties \
		rollbackCount $(or $(COUNT),1)

lb-status: up ## Show Liquibase changelog status for MODEL
	docker compose run --rm liquibase \
		--defaultsFile=/liquibase/conf/$(MODEL).properties status

lb-clean: up ## Drop all Liquibase-tracked objects for MODEL
	docker compose run --rm liquibase \
		--defaultsFile=/liquibase/conf/$(MODEL).properties dropAll

# ── Batch operations ──────────────────────────────────────────────────────────

migrate-all: up ## Migrate all domains with both Flyway and Liquibase
	@for d in $(DOMAINS); do \
		echo "==> Flyway migrate: $$d"; \
		$(MAKE) fw-migrate MODEL=$$d; \
	done
	@for d in $(DOMAINS); do \
		echo "==> Liquibase update: $$d"; \
		$(MAKE) lb-update MODEL=$$d; \
	done
	@echo "All migrations applied."

clean-all: up ## Clean all domain databases (Flyway + Liquibase)
	@for d in $(DOMAINS); do \
		echo "==> Flyway clean: $$d"; \
		$(MAKE) fw-clean MODEL=$$d; \
	done
	@for d in $(DOMAINS); do \
		echo "==> Liquibase dropAll: $$d"; \
		$(MAKE) lb-clean MODEL=$$d; \
	done
	@echo "All databases cleaned."

# ── Inspection ──────────────────────────────────────────────────────────────────

psql: up ## Open psql shell (TOOL=flyway|liquibase, MODEL=cinema)
	docker compose exec postgres psql -U deuser -d $(TOOL)_$(MODEL)

schema-diff: up ## Compare table lists between flyway and liquibase DBs
	@echo "=== flyway_$(MODEL) tables ==="
	@docker compose exec postgres psql -U deuser -d flyway_$(MODEL) -c \
		"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
	@echo "=== liquibase_$(MODEL) tables ==="
	@docker compose exec postgres psql -U deuser -d liquibase_$(MODEL) -c \
		"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
