#!/bin/sh

# Exit immediately if any command fails
set -e

echo "🚀 [ENTRYPOINT] Initializing database tables..."
python init_db.py

echo "🔥 [ENTRYPOINT] Database verified. Starting FastAPI Gateway Server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000