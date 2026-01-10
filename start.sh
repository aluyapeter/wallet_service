#!/bin/bash

celery -A app.core.celery.c_app worker --loglevel=info &

uvicorn app.main:app --host 0.0.0.0 --port $PORT