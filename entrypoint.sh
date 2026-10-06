#!/bin/sh
set -e

# Migrations run on container start by decision: one command brings up a working
# stack. A separate migrate service was considered and rejected for simplicity.
alembic upgrade head

exec uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000
