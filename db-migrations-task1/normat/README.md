# Task 1 — Normalization & Database Migrations (`normat`)

This folder documents **Task 1** of the DATA_ENGINEER project: designing a **Third Normal Form (3NF)** relational schema and implementing it with **Flyway** and **Liquibase**.

---

## Learning Objectives

| Objective | What you practice |
|-----------|-------------------|
| **Design a 3NF schema** | Split data so every column depends only on the whole primary key — no partial or transitive dependencies. |
| **Flyway versioned migrations** | Write `V1`, `V2`, `V3` SQL files with naming conventions, dependency order, seed data, and repeatable views. |
| **Liquibase YAML changelogs** | Mirror the same schema with `changeSet` IDs, explicit `rollback` blocks, and `runOnChange` views. |
| **Wire configuration** | Connect JDBC URLs, search paths, Makefile targets, and init scripts so both tools run against separate databases. |
| **Validate migrations** | Apply from scratch, re-run idempotently, compare schemas, and test rollback. |

---

## Chosen Domain: Cinema Booking Platform

Unlike the reference **hospital** (clinical care) and **e-commerce** (product sales) schemas, this task uses a **cinema booking** domain — venues, screens, movies, showtimes, and ticket reservations.

### Why this domain is in 3NF

**Third Normal Form** requires:

1. **1NF** — atomic values, no repeating groups.
2. **2NF** — every non-key column depends on the *entire* primary key (no partial dependencies).
3. **3NF** — no transitive dependencies (non-key column → non-key column).

#### Example: why `genres` is a separate table

If we stored `genre_name` directly on `movies`:

```
movies(id, title, genre_name)   -- BAD
```

Then `genre_name` depends on `genre_id` conceptually, not on `movie.id` alone — a **transitive dependency**. Extracting `genres` and linking via `movie_genres` removes it:

```
genres(id, name)
movie_genres(movie_id, genre_id)   -- composite PK, both are keys
movies(id, title, ...)
```

#### Example: why `screens` is separate from `cinemas`

A cinema has many screens. Putting `screen_number` and `capacity` on `cinemas` would create repeating groups (violates 1NF) or duplicate cinema data per screen. Normalizing to `screens(cinema_id, ...)` keeps each fact in one place.

### Entity Relationship Overview

```
cinemas ──< screens ──< showtimes >── movies
                              │              \
                              │          movie_genres >── genres
                              │
customers ──< bookings ──< booking_seats   (added in V2)
```

| Table | Role |
|-------|------|
| `cinemas` | Physical venue locations |
| `screens` | Individual auditoriums within a cinema |
| `movies` | Film catalog |
| `genres` | Normalized genre lookup |
| `movie_genres` | Many-to-many movie ↔ genre |
| `showtimes` | A movie screening on a specific screen |
| `customers` | Registered patrons |
| `bookings` | Ticket purchase for a showtime |
| `booking_seats` | *(V2)* Individual seat assignments per booking |

---

## File Map (cinema domain)

```
flyway/conf/cinema.conf
flyway/sql/cinema/V1__create_core_tables.sql
flyway/sql/cinema/V2__add_booking_seats.sql
flyway/sql/cinema/V3__seed_reference_data.sql
flyway/sql/cinema/R__upcoming_bookings_view.sql

liquibase/conf/cinema.properties
liquibase/changelog/cinema/db.changelog-master.yaml
liquibase/changelog/cinema/v1__create_core_tables.yaml
liquibase/changelog/cinema/v2__add_booking_seats.yaml
liquibase/changelog/cinema/v3__seed_reference_data.yaml
```

Databases: `flyway_cinema` and `liquibase_cinema` (created in `init/01-create-databases.sql`).

---

## How to Run

All commands run from the `db-migrations-task1/` directory:

```bash
cd db-migrations-task1
make up              # start PostgreSQL
make migrate-all     # apply Flyway + Liquibase for all domains
make fw-migrate MODEL=cinema
make fw-validate MODEL=cinema
make lb-update MODEL=cinema
make lb-rollback MODEL=cinema COUNT=1
make psql MODEL=cinema TOOL=flyway   # inspect flyway_cinema
make demo            # full clean demo from scratch
```

---

## Key Concepts Cheat Sheet

### Flyway naming

| Pattern | Purpose |
|---------|---------|
| `V1__create_core_tables.sql` | Versioned, runs once, in order |
| `V2__add_booking_seats.sql` | Schema evolution |
| `V3__seed_reference_data.sql` | Reference / demo data |
| `R__upcoming_bookings_view.sql` | Repeatable — re-applied when file changes |

### Liquibase essentials

- **changeSet `id`**: unique, e.g. `cinema-1-cinemas`
- **`author`**: consistent across all changeSets
- **`rollback`**: explicit inverse for DDL/DML that lacks auto-rollback
- **`runOnChange: true`**: re-run view definition when SQL changes

### Idempotency

- Flyway tracks applied versions in `flyway_schema_history`.
- Liquibase tracks in `databasechangelog`.
- Re-running `migrate-all` on an already-migrated DB is a no-op.
