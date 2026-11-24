# FastAPI Exercises I & II

A FastAPI-based customer lookup and document management API developed as part of the EC Bootcamp exercises. The project progresses from basic API endpoints to CRUD operations, JSON-based persistence, and simple document search.

## Project Overview

This repository contains two stages of FastAPI exercises.

### FastAPI I — Customer Lookup API

The first exercise introduces the fundamentals of building REST API endpoints using FastAPI.

Features:

- Health check endpoint.
- Retrieve all customers.
- Filter customers by value tier.
- Retrieve an individual customer using their ID.
- Handle requests for unknown customer IDs.

### FastAPI II — CRUD Operations and Document Management

The second exercise extends the initial API by introducing Create, Read, Update, and Delete (CRUD) operations.

**Customer Management**

- Create a customer.
- Retrieve all customers, with optional value-tier filtering.
- Retrieve a customer by ID.
- Update customer information using PATCH.
- Delete a customer by ID.

**Document Management**

- Create and retrieve documents.
- Update document titles and text.
- Delete documents.
- Split documents into overlapping text chunks.
- Search document chunks using keyword matching.
- Return ranked search results with source document information.

## Technology Stack

- **Python** — Programming language
- **FastAPI** — Web framework for building APIs
- **Pydantic** — Request validation and data modeling
- **Uvicorn** — ASGI server
- **JSON** — Local data storage
- **pytest** — Automated testing
- **Requests** — HTTP client

## Data Storage

The project uses JSON files instead of a database.

| File             | Description                           |
| ---------------- | ------------------------------------- |
| `customers.json` | Mock customer records                 |
| `documents.json` | Sample credit card product documents  |
| `.runtime/`      | Working copies of the JSON data files |

The original JSON files serve as the initial data source. The application creates working copies inside the configured working directory and performs its operations on those copies.

Configuration is managed through environment variables:

| Variable             | Default            | Description                       |
| -------------------- | ------------------ | --------------------------------- |
| `DATABASE_LOCATION`  | `customers.json`   | Customer data source              |
| `DOCUMENTS_LOCATION` | `documents.json`   | Document data source              |
| `WORKING_DATA_DIR`   | `.runtime`         | Directory for working JSON copies |
| `ENDPOINT_URL`       | `http://localhost` | API host                          |
| `ENDPOINT_PORT`      | `8000`             | API port                          |

## Project Structure

```text
fastapi-exercise-jericko/
├── main.py              # FastAPI application and API routes
├── documents.py         # Document chunking and keyword search
├── storage.py           # JSON working-copy and persistence utilities
├── customers.json       # Mock customer records
├── documents.json       # Sample document records
├── client.py            # Example HTTP client
├── tests/
│   ├── test_api.py      # Customer API tests
│   └── test_documents.py # Document functionality tests
├── pytest.ini           # pytest configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd fastapi-exercise-jericko
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure environment variables

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Adjust the values if necessary.

### 6. Run the application

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at:

- API: [http://localhost:8000](http://localhost:8000)
- Interactive Swagger documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## API Endpoints

### Health Check

| Method | Endpoint  | Description            |
| ------ | --------- | ---------------------- |
| GET    | `/health` | Check API availability |

### Customer Endpoints

| Method | Endpoint                     | Description                    | Expected Response |
| ------ | ---------------------------- | ------------------------------ | ----------------- |
| GET    | `/customers`                 | Retrieve all customers         | 200               |
| GET    | `/customers?value_tier=High` | Filter customers by value tier | 200               |
| GET    | `/customers/{customer_id}`   | Retrieve a customer by ID      | 200 / 404         |
| POST   | `/customers`                 | Create a new customer          | 201               |
| PATCH  | `/customers/{customer_id}`   | Update an existing customer    | 200 / 404         |
| DELETE | `/customers/{customer_id}`   | Delete a customer              | 204 / 404         |

### Document Endpoints

| Method | Endpoint                              | Description                                |
| ------ | ------------------------------------- | ------------------------------------------ |
| GET    | `/documents`                          | Retrieve documents with their chunk counts |
| GET    | `/documents/search?q={query}&top_k=3` | Search document chunks                     |
| POST   | `/documents`                          | Create a document                          |
| GET    | `/documents/{document_id}`            | Retrieve a document by ID                  |
| PATCH  | `/documents/{document_id}`            | Update a document                          |
| DELETE | `/documents/{document_id}`            | Delete a document                          |

### HTTP Status Codes

| Status Code              | Meaning                                    |
| ------------------------ | ------------------------------------------ |
| 200 OK                   | Request completed successfully             |
| 201 Created              | Resource successfully created              |
| 204 No Content           | Resource successfully deleted              |
| 404 Not Found            | Requested resource does not exist          |
| 409 Conflict             | Resource conflicts with an existing record |
| 422 Unprocessable Entity | Request validation failed                  |

## Document Search

The document search functionality is a simplified implementation of the document retrieval process used in Retrieval-Augmented Generation (RAG).

The process consists of:

1. Loading documents from `documents.json`.
2. Splitting document text into overlapping chunks.
3. Tokenizing the search query and document chunks.
4. Scoring chunks based on the number of matching query words.
5. Returning the highest-ranking matching chunks.

Default chunking configuration:

- Chunk size: 500 characters
- Chunk overlap: 100 characters

**Note:** This implementation uses keyword matching rather than vector similarity. It does not generate embeddings or use a vector database.

Example:

```powershell
curl.exe "http://localhost:8000/documents/search?q=lounge"
```

## Testing

Run the automated tests from the project root with the virtual environment activated:

```bash
python -m pip install pytest httpx
python -m pytest
```

The tests use FastAPI's `TestClient`, so the application server does not need to be running separately.

## Python HTTP Client

The repository includes `client.py`, which demonstrates how to send HTTP requests to the API using the Requests library.

With the API running, execute:

```bash
python client.py
```

The example client demonstrates calls to the health, customer lookup, and document retrieval/search endpoints.

## Notes and Limitations  Customer and document records are mock data.

- JSON files are used instead of a relational database.
- Changes are written to working copies rather than the original JSON files.
- Document search uses keyword matching, not embeddings or vector search.
- The document ingestion example is separate from the customer lookup functionality.
- The API is intended for learning and exercise purposes, not production deployment.
