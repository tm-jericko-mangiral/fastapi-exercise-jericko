# fastapi-exercise-jericko

Gold customer lookup API built with FastAPI.

## Setup
1. python -m venv .venv
2. .venv\Scripts\Activate.ps1
3. python -m pip install -r requirements.txt
4. Copy .env.example to .env

## Run
```
uvicorn main:app --reload
```
Docs: http://localhost:8000/docs

Routes:
- GET /health
- GET /customers (optional filter: ?value_tier=High|Medium|Standard)
- GET /customers/{customer_id}

The data file path comes from DATABASE_LOCATION and defaults to customers.json. All records are mock data.

## Test
Sample curl commands added in feature/client-and-submission.