#!/usr/bin/env bash

DATE="${1:-2026-10-13}"

if [ -f "./.venv/bin/python3" ]; then
    PYTHON_BIN="./.venv/bin/python3"
elif [ -f "../1st_e2e_data_platform_project/.venv/bin/python3" ]; then
    PYTHON_BIN="../1st_e2e_data_platform_project/.venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

echo "========================================================"
echo "💥 FastRoute Logistics — Deliberate Failure Demonstration"
echo "   Logical Date: $DATE"
echo "   Switch: --fail-ingestion"
echo "========================================================"

$PYTHON_BIN -m src.orchestration.runner --date "$DATE" --fail-ingestion || {
    echo ""
    echo "========================================================"
    echo "✅ Deliberate failure observed successfully!"
    echo "   Ingestion stage threw deliberate error."
    echo "   Downstream stages were HALTED."
    echo "   Pipeline marked as FAILED with exit code 1."
    echo "========================================================"
    exit 0
}

echo "❌ Error: Pipeline was expected to fail, but succeeded!"
exit 1
