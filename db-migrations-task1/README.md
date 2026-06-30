# DB Migrations — Task 1

Cinema booking platform schema in **3NF**, implemented with **Flyway** and **Liquibase**.

## Quick start

```bash
cd db-migrations-task1
make demo
```

## Project layout

```
db-migrations-task1/
├── README.md              ← you are here
├── Makefile
├── docker-compose.yml
├── init/                  ← database bootstrap
├── flyway/                ← Flyway SQL migrations (cinema)
├── liquibase/             ← Liquibase YAML changelogs (cinema)
└── normat/                ← 3NF design notes & learning guide
```

## Common commands

| Command | Description |
|---------|-------------|
| `make help` | List all targets |
| `make demo` | Reset DB + migrate everything |
| `make fw-migrate MODEL=cinema` | Flyway migrate |
| `make fw-validate MODEL=cinema` | Flyway validate |
| `make lb-update MODEL=cinema` | Liquibase update |
| `make lb-rollback MODEL=cinema COUNT=1` | Rollback last changeSet |
| `make psql MODEL=cinema TOOL=flyway` | Inspect database |

See [`normat/README.md`](normat/README.md) for the full learning guide and 3NF explanation.
