#!/usr/bin/env bash
set -e

DATE="${1:-2026-10-13}"

if [ -f "./.venv/bin/python3" ]; then
    PYTHON_BIN="./.venv/bin/python3"
elif [ -f "../1st_e2e_data_platform_project/.venv/bin/python3" ]; then
    PYTHON_BIN="../1st_e2e_data_platform_project/.venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

echo "========================================================"
echo "🚚 FastRoute Logistics — Triggering Batch Pipeline"
echo "   Logical Date: $DATE"
echo "========================================================"

$PYTHON_BIN -m src.orchestration.runner --date "$DATE"
