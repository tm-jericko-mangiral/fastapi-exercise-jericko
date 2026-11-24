import json
import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, StringConstraints

from documents import (
    build_chunks,
    find_document,
    has_duplicate,
    load_documents,
    make_document_id,
    search_chunks,
    summarize_documents,
)
from storage import prepare_working_copy, write_json

CUSTOMERS_PATH = prepare_working_copy(
    os.environ.get("DATABASE_LOCATION", "customers.json")
)
DOCUMENTS_PATH = prepare_working_copy(
    os.environ.get("DOCUMENTS_LOCATION", "documents.json")
)
DEFAULT_TOP_K = 3
MIN_TOP_K = 1

DocumentTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"[A-Za-z0-9]")
]
DocumentText = Annotated[str, StringConstraints(pattern=r"\S")]

app = FastAPI()


class NewDocument(BaseModel):
    """Request body for creating a document."""

    title: DocumentTitle
    text: DocumentText


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


@app.post("/documents", status_code=status.HTTP_201_CREATED)
def add_document(payload: NewDocument):
    """Create a document and rebuild the chunks.

    :param payload: Title and text of the new document.
    :return: The new document's ID, title and chunk count.
    :raises HTTPException: 409 when the title or the generated ID is taken.
    """
    document_id = make_document_id(payload.title)
    if has_duplicate(DOCUMENTS, payload.title, document_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Document '{payload.title}' already exists",
        )
    document = {"document_id": document_id, **payload.model_dump()}
    DOCUMENTS.append(document)
    save_documents_and_rebuild_chunks()
    return summarize_documents([document], CHUNKS)[0]


@app.get("/documents/{document_id}")
def get_document(document_id: str):
    """Return one document with its text.

    :param document_id: ID of the document.
    :return: The document record.
    :raises HTTPException: 404 when the document does not exist.
    """
    document = find_document(DOCUMENTS, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


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


def save_documents_and_rebuild_chunks():
    """Write the documents to the working copy and rebuild the chunks."""
    write_json(DOCUMENTS_PATH, DOCUMENTS)
    CHUNKS[:] = build_chunks(DOCUMENTS)


CUSTOMERS = load_customers()
DOCUMENTS = load_documents(DOCUMENTS_PATH)
CHUNKS = build_chunks(DOCUMENTS)
