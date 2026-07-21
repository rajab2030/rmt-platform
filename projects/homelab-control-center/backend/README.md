# HomeLab Control Center Backend

## Run

Activate environment:

source .venv/bin/activate

Start API:

uvicorn app.main:app --reload

## Endpoints

GET /

Returns application information.

GET /containers

Returns Docker containers status.
