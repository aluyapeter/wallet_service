#!/bin/bash

echo "Running Database Migrations..."
alembic upgrade head

echo "Starting Celery Worker..."
celery -A app.core.celery.c_app worker --loglevel=info &

echo "Starting Web Server..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT