# fastapi-exercise-jericko

Gold customer lookup API built with FastAPI, for the EC bootcamp FastAPI lab.

## Scenario
In my data engineering capstone, customer records from Core Banking and CRM are cleaned and merged into a Gold customer table (`gold_customers`) in PostgreSQL. That project has no customer-facing API.

This lab builds the missing piece in small form: a read-only API that lets a client look up Gold customers without touching the data layer directly. A client can list customers, filter them by value tier, or fetch one customer by ID.

The lab uses GET routes only. It is not connected to the capstone pipelines.

## Data Source
The records in `customers.json` are mock data modeled on the columns of the capstone's `gold_customers` table.

- All values are fake. Emails use `example.com` and phone numbers are placeholders.
- The columns mirror the Gold table, except the internal `_loaded_at` column.
- `customer_id` is an integer here, while the Gold table stores it as text.
- `value_tier` uses the real Gold values: `High`, `Medium` and `Standard`.
- `kyc_level`, `tier`, `segment` and `status` are not constrained in Gold, so their values are invented.
- The API reads the JSON file instead of PostgreSQL. The path comes from `DATABASE_LOCATION`.

## Project Structure
```
fastapi-exercise-jericko/
├── main.py            FastAPI app with the health and customer routes
├── customers.json     Mock Gold customer records, keyed by customer_id
├── client.py          Python client that calls the API with requests
├── tests/
│   └── test_api.py    pytest tests for the routes
├── pytest.ini         pytest settings (test folder, import path)
├── requirements.txt   Pinned dependencies
├── .env.example       Template for DATABASE_LOCATION, ENDPOINT_URL, ENDPOINT_PORT
└── README.md
```
Local only, not tracked: `.env`, `.venv/` and `.pytest_cache/`.

## Setup
1. python -m venv .venv
2. .venv\Scripts\Activate.ps1
3. python -m pip install -r requirements.txt
4. Copy .env.example to .env

## Run
```
uvicorn main:app --reload --port 8000
```
Docs: http://localhost:8000/docs

Routes:
- GET /health
- GET /customers (optional filter: ?value_tier=High|Medium|Standard)
- GET /customers/{customer_id}

The data file path comes from DATABASE_LOCATION and defaults to customers.json. All records are mock data.

## Test
Start the server first. In PowerShell use `curl.exe`, because `curl` is an alias for another command.

Health check:
```
curl.exe http://localhost:8000/health
```
```
{"status":"Healthy","message":"Service is Running"}
```

List customers filtered by value tier (returns customers 101 and 102):
```
curl.exe "http://localhost:8000/customers?value_tier=High"
```

One customer by ID:
```
curl.exe http://localhost:8000/customers/101
```
```
{"customer_id":101,"source_system":"core","email":"customer101@example.com","first_name":"Ana","last_name":"Reyes","age":34,"phone":"+63-000-000-0101","city":"Quezon City","province":"Metro Manila","postal_code":"1100","country":"PH","created_at":"2014-03-12T08:30:00+08:00","tenure_years":12.7,"tenure_category":"Long Term","kyc_level":"Full","tier":"Premier","segment":"Retail","status":"Active","marketing_opt_in":true,"total_relationship_balance":2450000.5,"average_daily_balance":1980000.25,"value_tier":"High","completeness_score":100.0,"as_of_date":"2026-11-23"}
```

Missing customer:
```
curl.exe http://localhost:8000/customers/999
```
```
{"detail":"Customer not found"}
```

## Automated tests
Install the test dependencies once, then run pytest from the repo root with `.venv` active:
```
python -m pip install pytest httpx
python -m pytest
```
The tests in `tests/test_api.py` call the routes through FastAPI's `TestClient`, so the server does not need to be running. They cover the health route, the customer list and its `value_tier` filter (including case and unknown values), lookup by ID, the 404 for a missing customer and the 422 for a non-integer ID.

## Python client
With the server running, in a second terminal with `.venv` active:
```
python client.py
```
It calls `/health`, `/customers?value_tier=High`, `/customers/101` and `/customers/999`, and prints the status code and JSON for each. The base URL comes from `ENDPOINT_URL` and `ENDPOINT_PORT`, defaulting to `http://localhost` and `8000`.