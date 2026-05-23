#!/bin/bash
# Container entrypoint: seed DB at runtime (not build time), then start uvicorn
set -euo pipefail

cd /app

# Seed database on first start (if DB doesn't exist)
if [ ! -f /app/otd_erp.db ]; then
  echo "Seeding database..."
  python3 seed_data.py
fi

echo "Starting OTD ERP API..."
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8004
