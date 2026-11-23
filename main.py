import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from documents import (
    build_chunks,
    load_documents,
    search_chunks,
    summarize_documents,
)

CUSTOMERS_PATH = Path(os.environ.get("DATABASE_LOCATION", "customers.json"))
DOCUMENTS_PATH = Path(os.environ.get("DOCUMENTS_LOCATION", "documents.json"))
DEFAULT_TOP_K = 3

app = FastAPI()


@app.get("/health")
def get_health():
    return {
        "status": "Healthy",
        "message": "Service is Running",
    }


@app.get("/customers")
def get_customers(value_tier: str | None = None):
    customers = list(CUSTOMERS.values())
    if value_tier is None:
        return customers
    return filter_by_value_tier(customers, value_tier)


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        raise HTTPException(404, "Customer not found")
    return customer


@app.get("/documents")
def get_documents():
    return summarize_documents(DOCUMENTS, CHUNKS)


@app.get("/documents/search")
def search_documents(q: str, top_k: int = Query(DEFAULT_TOP_K, ge=1)):
    return search_chunks(CHUNKS, q, top_k)


def filter_by_value_tier(customers, value_tier):
    return [
        customer
        for customer in customers
        if customer["value_tier"].lower() == value_tier.lower()
    ]


def load_customers():
    with CUSTOMERS_PATH.open("r", encoding="utf-8") as file:
        stored_customers = json.load(file)
    return {
        int(customer_id): customer
        for customer_id, customer in stored_customers.items()
    }


CUSTOMERS = load_customers()
DOCUMENTS = load_documents(DOCUMENTS_PATH)
CHUNKS = build_chunks(DOCUMENTS)
