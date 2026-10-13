#!/usr/bin/env bash
set -e

echo "⏳ Waiting for PostgreSQL (5432)..."
until pg_isready -h localhost -p 5432 -U "${POSTGRES_USER:-fastroute_user}" -d "${POSTGRES_DB:-fastroute_db}" > /dev/null 2>&1; do
    sleep 2
done
echo "✅ PostgreSQL is ready."

echo "⏳ Waiting for ClickHouse (8123)..."
until curl -s http://localhost:8123/ping | grep -q "Ok"; do
    sleep 2
done
echo "✅ ClickHouse is ready."

echo "⏳ Waiting for MinIO (9000)..."
until curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    sleep 2
done
echo "✅ MinIO is ready."

echo "🎉 All infrastructure core services are UP and healthy!"
