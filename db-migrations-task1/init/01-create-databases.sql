-- Create separate databases for each migration tool / domain combination.
-- Cinema domain (Task 1 — normat)
CREATE DATABASE flyway_cinema;
CREATE DATABASE liquibase_cinema;

GRANT ALL PRIVILEGES ON DATABASE flyway_cinema TO deuser;
GRANT ALL PRIVILEGES ON DATABASE liquibase_cinema TO deuser;
