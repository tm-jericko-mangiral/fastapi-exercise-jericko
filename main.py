import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status

from documents import (
    build_chunks,
    load_documents,
    search_chunks,
    summarize_documents,
)

CUSTOMERS_PATH = Path(os.environ.get("DATABASE_LOCATION", "customers.json"))
DOCUMENTS_PATH = Path(os.environ.get("DOCUMENTS_LOCATION", "documents.json"))
DEFAULT_TOP_K = 3
MIN_TOP_K = 1

app = FastAPI()


@app.get("/health")
def get_health():
    """Report that the service is running."""
    return {
        "status": "Healthy",
        "message": "Service is Running",
    }


@app.get("/customers")
def get_customers(value_tier: str | None = None):
    """List the customers, optionally filtered by value tier.

    :param value_tier: High, Medium or Standard, ignoring case.
    :return: Matching customer records.
    """
    customers = list(CUSTOMERS.values())
    if value_tier is None:
        return customers
    return filter_by_value_tier(customers, value_tier)


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):
    """Return one customer.

    :param customer_id: Integer ID of the customer.
    :return: The customer record.
    :raises HTTPException: 404 when the customer does not exist.
    """
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@app.get("/documents")
def get_documents():
    """List the documents with their chunk counts."""
    return summarize_documents(DOCUMENTS, CHUNKS)


@app.get("/documents/search")
def search_documents(q: str, top_k: int = Query(DEFAULT_TOP_K, ge=MIN_TOP_K)):
    """Search the document chunks by keyword.

    :param q: Search text.
    :param top_k: Maximum number of chunks to return, at least 1.
    :return: Best matching chunks with their source document and score.
    """
    return search_chunks(CHUNKS, q, top_k)


def filter_by_value_tier(customers, value_tier):
    """Keep the customers whose value tier matches, ignoring case.

    :param customers: Customer records.
    :param value_tier: Value tier to match.
    :return: Customers with that value tier.
    """
    return [
        customer
        for customer in customers
        if customer["value_tier"].lower() == value_tier.lower()
    ]


def load_customers():
    """Read the customers from the JSON file at CUSTOMERS_PATH.

    :return: Customer records keyed by integer customer_id.
    """
    with CUSTOMERS_PATH.open("r", encoding="utf-8") as file:
        stored_customers = json.load(file)
    return {
        int(customer_id): customer
        for customer_id, customer in stored_customers.items()
    }


CUSTOMERS = load_customers()
DOCUMENTS = load_documents(DOCUMENTS_PATH)
CHUNKS = build_chunks(DOCUMENTS)
