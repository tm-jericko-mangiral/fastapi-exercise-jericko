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

## Python client
With the server running, in a second terminal with `.venv` active:
```
python client.py
```
It calls `/health`, `/customers?value_tier=High`, `/customers/101` and `/customers/999`, and prints the status code and JSON for each. The base URL comes from `ENDPOINT_URL` and `ENDPOINT_PORT`, defaulting to `http://localhost` and `8000`.