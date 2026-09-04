#!/usr/bin/env bash
set -e

echo "🚀 FastRoute Logistics Data Platform — Infrastructure Initializer"
echo "------------------------------------------------------------------"

if [ ! -f .env ]; then
    echo "⚠️  .env file missing. Copying from .env.example..."
    cp .env.example .env
fi

echo "📦 Starting Docker Compose services..."
docker compose up -d --build

echo "⏳ Waiting for services to become healthy..."
sleep 5

docker compose ps

echo "✅ Infrastructure initialization complete!"
echo "👉 Streamlit Control Center: http://localhost:8501"
echo "👉 Apache Airflow UI:       http://localhost:8080 (User: airflow / Pass: airflow)"
echo "👉 MinIO S3 Console:       http://localhost:9001 (User: minioadmin / Pass: minioadmin)"
