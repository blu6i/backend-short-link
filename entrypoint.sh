#!/bin/sh
uv run alembic upgrade head
exec uv run --locked --no-dev uvicorn main:app --host 0.0.0.0 --port 8000