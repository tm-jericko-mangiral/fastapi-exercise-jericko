import itertools
import json
import math
import os
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)

from documents import (
    build_chunks,
    find_document,
    has_duplicate,
    is_title_used_by_other,
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
MAX_AGE = 120
MAX_COMPLETENESS_SCORE = 100

DocumentTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"[A-Za-z0-9]")
]
DocumentText = Annotated[str, StringConstraints(pattern=r"\S")]
RequiredText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1)
]
EmailAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    ),
]
NonNegativeNumber = Annotated[float, Field(ge=0, allow_inf_nan=False)]
CompletenessScore = Annotated[
    float,
    Field(ge=0, le=MAX_COMPLETENESS_SCORE, allow_inf_nan=False),
]

app = FastAPI()


class NewDocument(BaseModel):
    """Request body for creating a document."""

    title: DocumentTitle
    text: DocumentText


class DocumentChanges(BaseModel):
    """Request body for changing a document.

    Only title and text are accepted, and at least one must be sent.
    """

    model_config = ConfigDict(extra="forbid")

    title: DocumentTitle | None = None
    text: DocumentText | None = None

    @model_validator(mode="after")
    def require_a_value_to_change(self):
        """Reject an empty body and null values."""
        changes = self.model_dump(exclude_unset=True)
        if not changes or None in changes.values():
            raise ValueError("Send title, text or both, each with a value")
        return self


class NewCustomer(BaseModel):
    """Request body for creating a customer.

    Every field is required. The server sets customer_id and as_of_date, so
    sending them, or any other unknown field, is rejected.
    """

    model_config = ConfigDict(extra="forbid")

    source_system: RequiredText
    email: EmailAddress
    first_name: RequiredText
    last_name: RequiredText
    age: Annotated[StrictInt, Field(ge=0, le=MAX_AGE)]
    phone: RequiredText
    city: RequiredText
    province: RequiredText
    postal_code: RequiredText
    country: RequiredText
    created_at: datetime
    tenure_years: NonNegativeNumber
    tenure_category: RequiredText
    kyc_level: RequiredText
    tier: RequiredText
    segment: RequiredText
    status: RequiredText
    marketing_opt_in: StrictBool
    total_relationship_balance: NonNegativeNumber
    average_daily_balance: NonNegativeNumber
    value_tier: Literal["High", "Medium", "Standard"]
    completeness_score: CompletenessScore


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


@app.post("/customers", status_code=status.HTTP_201_CREATED)
def add_customer(payload: NewCustomer):
    """Create a customer and save the working copy.

    The server sets customer_id (the next unused ID) and as_of_date (today).

    :param payload: Customer fields supplied by the client.
    :return: The new customer record.
    :raises HTTPException: 409 when another customer has the same email.
    """
    if is_email_taken(CUSTOMERS.values(), payload.email):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Customer with email '{payload.email}' already exists",
        )
    customer_id = next(NEW_CUSTOMER_IDS)
    customer = {
        "customer_id": customer_id,
        **payload.model_dump(mode="json"),
        "as_of_date": date.today().isoformat(),
    }
    CUSTOMERS[customer_id] = customer
    save_customers()
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


@app.patch("/documents/{document_id}")
def change_document(document_id: str, payload: DocumentChanges):
    """Change the title, the text or both of a document.

    The document ID stays the same. The chunks are rebuilt.

    :param document_id: ID of the document.
    :param payload: New title and/or new text.
    :return: The document's ID, title and chunk count.
    :raises HTTPException: 404 when the document does not exist, 409 when
        another document already has the new title.
    """
    document = find_document(DOCUMENTS, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    changes = payload.model_dump(exclude_unset=True)
    new_title = changes.get("title")
    if new_title and is_title_used_by_other(
        DOCUMENTS, new_title, document_id
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Document '{new_title}' already exists",
        )
    document.update(changes)
    save_documents_and_rebuild_chunks()
    return summarize_documents([document], CHUNKS)[0]


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str):
    """Delete a document and rebuild the chunks.

    :param document_id: ID of the document.
    :raises HTTPException: 404 when the document does not exist.
    """
    document = find_document(DOCUMENTS, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    DOCUMENTS.remove(document)
    save_documents_and_rebuild_chunks()


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
):
    """Return the usual 422 response, also for NaN and Infinity in a body.

    FastAPI's own handler fails with a 500 when a rejected body held NaN or
    Infinity, because the error repeats that value and JSON cannot carry it.

    :param request: The rejected request.
    :param exc: The validation errors.
    :return: The 422 response with the errors.
    """
    cleaned = RequestValidationError(
        replace_non_finite(exc.errors()), body=exc.body
    )
    return await request_validation_exception_handler(request, cleaned)


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


def is_email_taken(customers, email):
    """Check whether a customer already has this email.

    Emails are compared ignoring case.

    :param customers: Customer records.
    :param email: Email to check.
    :return: True when a customer has the same email.
    """
    return any(
        customer["email"].casefold() == email.casefold()
        for customer in customers
    )


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


def replace_non_finite(value):
    """Replace NaN and Infinity with text, at any depth.

    :param value: Number, list, tuple, dict or any other value.
    :return: The same structure with every non-finite float as a string.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: replace_non_finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [replace_non_finite(item) for item in value]
    return value


def save_customers():
    """Write the customers to the working copy, keyed by customer_id."""
    write_json(
        CUSTOMERS_PATH,
        {
            str(customer_id): customer
            for customer_id, customer in CUSTOMERS.items()
        },
    )


def save_documents_and_rebuild_chunks():
    """Write the documents to the working copy and rebuild the chunks."""
    write_json(DOCUMENTS_PATH, DOCUMENTS)
    CHUNKS[:] = build_chunks(DOCUMENTS)


CUSTOMERS = load_customers()
NEW_CUSTOMER_IDS = itertools.count(max(CUSTOMERS, default=0) + 1)
DOCUMENTS = load_documents(DOCUMENTS_PATH)
CHUNKS = build_chunks(DOCUMENTS)
