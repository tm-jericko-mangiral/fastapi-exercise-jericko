"""Tests for the POST, PATCH and DELETE routes of both resources.

Every test runs against a temporary copy of the data, so neither the raw JSON
files nor the working copy in .runtime/ is ever written.
"""

import itertools
import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from documents import build_chunks, load_documents

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_CUSTOMERS = PROJECT_ROOT / "customers.json"
RAW_DOCUMENTS = PROJECT_ROOT / "documents.json"

CUSTOMER_COUNT = 6
EXISTING_CUSTOMER_ID = 101
OTHER_CUSTOMER_ID = 102
MISSING_CUSTOMER_ID = 999
FIRST_NEW_CUSTOMER_ID = 107
SECOND_NEW_CUSTOMER_ID = 108

DOCUMENT_COUNT = 3
EXISTING_DOCUMENT_ID = "everyday-max-cashback"
EXISTING_DOCUMENT_TITLE = "Everyday Max Cashback"
OTHER_DOCUMENT_ID = "astra-travel-miles-platinum"
OTHER_DOCUMENT_TITLE = "Astra Travel Miles Platinum"
MISSING_DOCUMENT_ID = "missing-document"
SEARCH_TOP_K = 10
OLD_TEXT_TERM = "pharmacies"
OTHER_DOCUMENT_TERM = "lounge"
NEW_TEXT_TERM = "zebrafish"
TWO_CHUNK_TEXT = f"{NEW_TEXT_TERM} " * 70

NEW_CUSTOMER = {
    "source_system": "core",
    "email": "new.customer@example.com",
    "first_name": "Lia",
    "last_name": "Ramos",
    "age": 30,
    "phone": "+63-000-000-0107",
    "city": "Pasig",
    "province": "Metro Manila",
    "postal_code": "1600",
    "country": "PH",
    "created_at": "2026-11-01T09:00:00+08:00",
    "tenure_years": 0.1,
    "tenure_category": "New",
    "kyc_level": "Basic",
    "tier": "Standard",
    "segment": "Retail",
    "status": "Active",
    "marketing_opt_in": True,
    "total_relationship_balance": 1000.0,
    "average_daily_balance": 500.0,
    "value_tier": "Standard",
    "completeness_score": 90.0,
}
NEW_DOCUMENT = {"title": "Test Savings Card", "text": f"{NEW_TEXT_TERM} card"}
NEW_DOCUMENT_ID = "test-savings-card"

INVALID_CUSTOMER_VALUES = [
    ("age", 121),
    ("age", -1),
    ("age", "34"),
    ("age", 34.5),
    ("email", "not-an-email"),
    ("first_name", "   "),
    ("tenure_years", -1),
    ("total_relationship_balance", -0.01),
    ("average_daily_balance", None),
    ("completeness_score", 100.5),
    ("marketing_opt_in", "yes"),
    ("marketing_opt_in", 1),
    ("value_tier", "high"),
    ("created_at", "not-a-date"),
]
LOCKED_OR_UNKNOWN_CUSTOMER_FIELDS = [
    ("customer_id", 1),
    ("as_of_date", "2026-01-01"),
    ("nickname", "Lia"),
]
INVALID_NEW_DOCUMENTS = [
    {},
    {"title": "Only a title"},
    {"text": "Only a text"},
    {"title": "!!!", "text": "Title without letters or digits"},
    {"title": "Blank text", "text": "   "},
    {"title": None, "text": "Null title"},
    {"title": 5, "text": "Title is not text"},
]
INVALID_DOCUMENT_CHANGES = [
    {},
    {"title": None},
    {"text": None},
    {"title": "!!!"},
    {"text": "   "},
    {"document_id": "new-id"},
    {"nickname": "unknown field"},
]


@pytest.fixture
def working_dir(tmp_path, monkeypatch):
    """Point the app at a temporary copy of both data files.

    main.py loads the data once at import, so the paths, the in-memory
    records, the chunks and the customer ID counter are all replaced. The
    monkeypatch puts the originals back after each test.
    """
    customers_path = tmp_path / RAW_CUSTOMERS.name
    documents_path = tmp_path / RAW_DOCUMENTS.name
    shutil.copyfile(RAW_CUSTOMERS, customers_path)
    shutil.copyfile(RAW_DOCUMENTS, documents_path)
    monkeypatch.setattr(main, "CUSTOMERS_PATH", customers_path)
    monkeypatch.setattr(main, "DOCUMENTS_PATH", documents_path)
    customers = main.load_customers()
    documents = load_documents(documents_path)
    monkeypatch.setattr(main, "CUSTOMERS", customers)
    monkeypatch.setattr(
        main, "NEW_CUSTOMER_IDS", itertools.count(max(customers) + 1)
    )
    monkeypatch.setattr(main, "DOCUMENTS", documents)
    monkeypatch.setattr(main, "CHUNKS", build_chunks(documents))
    return tmp_path


@pytest.fixture
def client(working_dir):
    return TestClient(main.app)


def new_customer(**overrides):
    return {**NEW_CUSTOMER, **overrides}


def read_saved(working_dir, file_name):
    path = working_dir / file_name
    return json.loads(path.read_text(encoding="utf-8"))


def search(client, term):
    response = client.get(
        "/documents/search", params={"q": term, "top_k": SEARCH_TOP_K}
    )
    assert response.status_code == 200
    return response.json()


def searched_document_ids(client, term):
    return {chunk["document_id"] for chunk in search(client, term)}


# --- POST /customers ---


def test_post_customer_returns_201_with_server_set_fields(client):
    response = client.post("/customers", json=new_customer())

    created = response.json()
    assert response.status_code == 201
    assert created["customer_id"] == FIRST_NEW_CUSTOMER_ID
    assert created["as_of_date"] == date.today().isoformat()
    assert created["email"] == NEW_CUSTOMER["email"]


def test_post_customer_can_be_read_back_and_listed(client):
    created = client.post("/customers", json=new_customer()).json()

    fetched = client.get(f"/customers/{FIRST_NEW_CUSTOMER_ID}")

    assert fetched.json() == created
    assert len(client.get("/customers").json()) == CUSTOMER_COUNT + 1


def test_post_customer_saves_the_working_copy(client, working_dir):
    created = client.post("/customers", json=new_customer()).json()

    saved = read_saved(working_dir, RAW_CUSTOMERS.name)
    assert saved[str(FIRST_NEW_CUSTOMER_ID)] == created


def test_post_customer_gives_each_new_customer_the_next_id(client):
    client.post("/customers", json=new_customer())

    second = client.post(
        "/customers", json=new_customer(email="second@example.com")
    )

    assert second.json()["customer_id"] == SECOND_NEW_CUSTOMER_ID


@pytest.mark.parametrize(
    "email",
    [
        "customer101@example.com",
        "CUSTOMER101@EXAMPLE.COM",
        "  customer101@example.com  ",
    ],
)
def test_post_customer_returns_409_for_a_duplicate_email(client, email):
    response = client.post("/customers", json=new_customer(email=email))

    assert response.status_code == 409
    assert len(client.get("/customers").json()) == CUSTOMER_COUNT


@pytest.mark.parametrize("field", list(NEW_CUSTOMER))
def test_post_customer_returns_422_when_a_field_is_missing(client, field):
    payload = new_customer()
    del payload[field]

    response = client.post("/customers", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(("field", "value"), INVALID_CUSTOMER_VALUES)
def test_post_customer_returns_422_for_an_invalid_value(
    client, field, value
):
    response = client.post("/customers", json=new_customer(**{field: value}))

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"), LOCKED_OR_UNKNOWN_CUSTOMER_FIELDS
)
def test_post_customer_returns_422_for_locked_or_unknown_field(
    client, field, value
):
    response = client.post("/customers", json=new_customer(**{field: value}))

    assert response.status_code == 422


def test_failed_post_customer_does_not_use_up_an_id(client):
    client.post("/customers", json=new_customer(age=121))
    client.post(
        "/customers", json=new_customer(email="customer101@example.com")
    )

    created = client.post("/customers", json=new_customer())

    assert created.json()["customer_id"] == FIRST_NEW_CUSTOMER_ID


# --- PATCH /customers/{customer_id} ---


def test_patch_customer_changes_only_the_sent_fields(client):
    url = f"/customers/{EXISTING_CUSTOMER_ID}"
    original = client.get(url).json()

    response = client.patch(url, json={"city": "Taguig", "age": 35})

    assert response.status_code == 200
    assert response.json() == {**original, "city": "Taguig", "age": 35}
    assert client.get(url).json() == response.json()


def test_patch_customer_saves_the_working_copy(client, working_dir):
    response = client.patch(
        f"/customers/{EXISTING_CUSTOMER_ID}", json={"city": "Taguig"}
    )

    saved = read_saved(working_dir, RAW_CUSTOMERS.name)
    assert saved[str(EXISTING_CUSTOMER_ID)] == response.json()


def test_patch_customer_keeps_its_own_email_in_another_case(client):
    response = client.patch(
        f"/customers/{EXISTING_CUSTOMER_ID}",
        json={"email": "CUSTOMER101@EXAMPLE.COM"},
    )

    assert response.status_code == 200


def test_patch_customer_returns_404_for_an_unknown_id(client):
    response = client.patch(
        f"/customers/{MISSING_CUSTOMER_ID}", json={"city": "Taguig"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_patch_customer_returns_409_for_another_customers_email(client):
    response = client.patch(
        f"/customers/{EXISTING_CUSTOMER_ID}",
        json={"email": "CUSTOMER102@example.com"},
    )

    assert response.status_code == 409


@pytest.mark.parametrize(("field", "value"), INVALID_CUSTOMER_VALUES)
def test_patch_customer_returns_422_for_an_invalid_value(
    client, field, value
):
    response = client.patch(
        f"/customers/{EXISTING_CUSTOMER_ID}", json={field: value}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"), LOCKED_OR_UNKNOWN_CUSTOMER_FIELDS
)
def test_patch_customer_returns_422_for_locked_or_unknown_field(
    client, field, value
):
    response = client.patch(
        f"/customers/{EXISTING_CUSTOMER_ID}", json={field: value}
    )

    assert response.status_code == 422


def test_patch_customer_returns_422_for_an_empty_body(client):
    response = client.patch(f"/customers/{EXISTING_CUSTOMER_ID}", json={})

    assert response.status_code == 422


def test_patch_customer_returns_422_for_a_non_integer_id(client):
    response = client.patch("/customers/abc", json={"city": "Taguig"})

    assert response.status_code == 422


def test_patch_customer_checks_the_body_before_the_id(client):
    response = client.patch(f"/customers/{MISSING_CUSTOMER_ID}", json={})

    assert response.status_code == 422


# --- DELETE /customers/{customer_id} ---


def test_delete_customer_returns_204_and_removes_the_customer(client):
    response = client.delete(f"/customers/{EXISTING_CUSTOMER_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/customers/{EXISTING_CUSTOMER_ID}").status_code == 404
    assert len(client.get("/customers").json()) == CUSTOMER_COUNT - 1


def test_delete_customer_saves_the_working_copy(client, working_dir):
    client.delete(f"/customers/{EXISTING_CUSTOMER_ID}")

    saved = read_saved(working_dir, RAW_CUSTOMERS.name)
    assert str(EXISTING_CUSTOMER_ID) not in saved
    assert len(saved) == CUSTOMER_COUNT - 1


def test_delete_customer_returns_404_for_an_unknown_id(client):
    response = client.delete(f"/customers/{MISSING_CUSTOMER_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_delete_customer_returns_404_the_second_time(client):
    client.delete(f"/customers/{EXISTING_CUSTOMER_ID}")

    response = client.delete(f"/customers/{EXISTING_CUSTOMER_ID}")

    assert response.status_code == 404


def test_delete_customer_returns_422_for_a_non_integer_id(client):
    response = client.delete("/customers/abc")

    assert response.status_code == 422


def test_delete_customer_frees_the_email(client):
    client.delete(f"/customers/{EXISTING_CUSTOMER_ID}")

    response = client.post(
        "/customers", json=new_customer(email="customer101@example.com")
    )

    assert response.status_code == 201


def test_delete_customer_does_not_free_the_id_for_reuse(client):
    client.post("/customers", json=new_customer())
    client.delete(f"/customers/{FIRST_NEW_CUSTOMER_ID}")

    created = client.post(
        "/customers", json=new_customer(email="second@example.com")
    )

    assert created.json()["customer_id"] == SECOND_NEW_CUSTOMER_ID


# --- POST /documents ---


def test_post_document_returns_201_with_id_and_chunk_count(client):
    response = client.post("/documents", json=NEW_DOCUMENT)

    assert response.status_code == 201
    assert response.json() == {
        "document_id": NEW_DOCUMENT_ID,
        "title": NEW_DOCUMENT["title"],
        "chunk_count": 1,
    }


def test_post_document_can_be_read_back_and_listed(client):
    client.post("/documents", json=NEW_DOCUMENT)

    fetched = client.get(f"/documents/{NEW_DOCUMENT_ID}")

    assert fetched.status_code == 200
    assert fetched.json() == {"document_id": NEW_DOCUMENT_ID, **NEW_DOCUMENT}
    assert len(client.get("/documents").json()) == DOCUMENT_COUNT + 1


def test_post_document_saves_the_working_copy(client, working_dir):
    client.post("/documents", json=NEW_DOCUMENT)

    saved = read_saved(working_dir, RAW_DOCUMENTS.name)
    assert {"document_id": NEW_DOCUMENT_ID, **NEW_DOCUMENT} in saved


def test_post_document_makes_the_new_text_searchable(client):
    client.post("/documents", json=NEW_DOCUMENT)

    assert searched_document_ids(client, NEW_TEXT_TERM) == {NEW_DOCUMENT_ID}


@pytest.mark.parametrize(
    "title",
    [EXISTING_DOCUMENT_TITLE, EXISTING_DOCUMENT_TITLE.upper()],
)
def test_post_document_returns_409_for_a_duplicate_title(client, title):
    response = client.post(
        "/documents", json={"title": title, "text": "Some text"}
    )

    assert response.status_code == 409
    assert len(client.get("/documents").json()) == DOCUMENT_COUNT


def test_post_document_returns_409_when_the_generated_id_is_taken(client):
    response = client.post(
        "/documents",
        json={"title": "Everyday-Max Cashback", "text": "Some text"},
    )

    assert response.status_code == 409


@pytest.mark.parametrize("payload", INVALID_NEW_DOCUMENTS)
def test_post_document_returns_422_for_an_invalid_body(client, payload):
    response = client.post("/documents", json=payload)

    assert response.status_code == 422


# --- GET /documents/{document_id} ---


def test_get_document_returns_the_document_with_its_text(client):
    response = client.get(f"/documents/{EXISTING_DOCUMENT_ID}")

    assert response.status_code == 200
    assert response.json()["title"] == EXISTING_DOCUMENT_TITLE
    assert OLD_TEXT_TERM in response.json()["text"]


def test_get_document_returns_404_for_an_unknown_id(client):
    response = client.get(f"/documents/{MISSING_DOCUMENT_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


# --- PATCH /documents/{document_id} ---


def test_patch_document_changes_the_title_and_keeps_the_id(client):
    response = client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"title": "Max Cashback"}
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == EXISTING_DOCUMENT_ID
    assert response.json()["title"] == "Max Cashback"
    assert (
        client.get(f"/documents/{EXISTING_DOCUMENT_ID}").json()["title"]
        == "Max Cashback"
    )


def test_patch_document_changes_the_text_and_chunk_count(client):
    response = client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"text": TWO_CHUNK_TEXT}
    )

    assert response.status_code == 200
    assert response.json()["chunk_count"] == 2
    assert (
        client.get(f"/documents/{EXISTING_DOCUMENT_ID}").json()["text"]
        == TWO_CHUNK_TEXT
    )


def test_patch_document_changes_title_and_text_together(client):
    response = client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}",
        json={"title": "Max Cashback", "text": NEW_DOCUMENT["text"]},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Max Cashback"
    assert response.json()["chunk_count"] == 1


def test_patch_document_saves_the_working_copy(client, working_dir):
    client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"title": "Max Cashback"}
    )

    saved = read_saved(working_dir, RAW_DOCUMENTS.name)
    titles = {document["document_id"]: document["title"] for document in saved}
    assert titles[EXISTING_DOCUMENT_ID] == "Max Cashback"


def test_patch_document_keeps_its_own_title_in_another_case(client):
    response = client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}",
        json={"title": EXISTING_DOCUMENT_TITLE.upper()},
    )

    assert response.status_code == 200


def test_patch_document_returns_404_for_an_unknown_id(client):
    response = client.patch(
        f"/documents/{MISSING_DOCUMENT_ID}", json={"title": "Anything"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_patch_document_returns_409_for_another_documents_title(client):
    response = client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}",
        json={"title": OTHER_DOCUMENT_TITLE.lower()},
    )

    assert response.status_code == 409


@pytest.mark.parametrize("payload", INVALID_DOCUMENT_CHANGES)
def test_patch_document_returns_422_for_an_invalid_body(client, payload):
    response = client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json=payload
    )

    assert response.status_code == 422


def test_patch_document_checks_the_body_before_the_id(client):
    response = client.patch(f"/documents/{MISSING_DOCUMENT_ID}", json={})

    assert response.status_code == 422


# --- DELETE /documents/{document_id} ---


def test_delete_document_returns_204_and_removes_the_document(client):
    response = client.delete(f"/documents/{EXISTING_DOCUMENT_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/documents/{EXISTING_DOCUMENT_ID}").status_code == 404
    assert len(client.get("/documents").json()) == DOCUMENT_COUNT - 1


def test_delete_document_saves_the_working_copy(client, working_dir):
    client.delete(f"/documents/{EXISTING_DOCUMENT_ID}")

    saved = read_saved(working_dir, RAW_DOCUMENTS.name)
    assert EXISTING_DOCUMENT_ID not in [
        document["document_id"] for document in saved
    ]


def test_delete_document_returns_404_for_an_unknown_id(client):
    response = client.delete(f"/documents/{MISSING_DOCUMENT_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_delete_document_returns_404_the_second_time(client):
    client.delete(f"/documents/{EXISTING_DOCUMENT_ID}")

    response = client.delete(f"/documents/{EXISTING_DOCUMENT_ID}")

    assert response.status_code == 404


def test_delete_document_frees_the_title_and_id(client):
    client.delete(f"/documents/{EXISTING_DOCUMENT_ID}")

    response = client.post(
        "/documents",
        json={"title": EXISTING_DOCUMENT_TITLE, "text": "Fresh text"},
    )

    assert response.status_code == 201
    assert response.json()["document_id"] == EXISTING_DOCUMENT_ID


# --- Search stays consistent ---


def test_delete_document_removes_its_chunks_from_search(client):
    assert searched_document_ids(client, OTHER_DOCUMENT_TERM) == {
        OTHER_DOCUMENT_ID
    }

    client.delete(f"/documents/{OTHER_DOCUMENT_ID}")

    assert search(client, OTHER_DOCUMENT_TERM) == []


def test_delete_document_keeps_other_documents_searchable(client):
    client.delete(f"/documents/{OTHER_DOCUMENT_ID}")

    assert searched_document_ids(client, OLD_TEXT_TERM) == {
        EXISTING_DOCUMENT_ID
    }


def test_patch_document_text_replaces_the_searchable_chunks(client):
    assert searched_document_ids(client, OLD_TEXT_TERM) == {
        EXISTING_DOCUMENT_ID
    }

    client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"text": TWO_CHUNK_TEXT}
    )

    assert search(client, OLD_TEXT_TERM) == []
    new_chunk_ids = [
        chunk["chunk_id"] for chunk in search(client, NEW_TEXT_TERM)
    ]
    assert sorted(new_chunk_ids) == [
        f"{EXISTING_DOCUMENT_ID}-0",
        f"{EXISTING_DOCUMENT_ID}-1",
    ]


def test_patch_document_title_keeps_the_chunks_searchable(client):
    before = search(client, OLD_TEXT_TERM)

    client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"title": "Max Cashback"}
    )

    assert search(client, OLD_TEXT_TERM) == before


def test_search_chunk_count_matches_the_document_list(client):
    client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"text": TWO_CHUNK_TEXT}
    )

    listed = {
        document["document_id"]: document["chunk_count"]
        for document in client.get("/documents").json()
    }
    assert listed[EXISTING_DOCUMENT_ID] == len(search(client, NEW_TEXT_TERM))


# --- Raw files ---


def test_raw_json_files_stay_unchanged(client, working_dir):
    raw_customers = RAW_CUSTOMERS.read_bytes()
    raw_documents = RAW_DOCUMENTS.read_bytes()

    client.post("/customers", json=new_customer())
    client.patch(f"/customers/{EXISTING_CUSTOMER_ID}", json={"city": "Taguig"})
    client.delete(f"/customers/{OTHER_CUSTOMER_ID}")
    client.post("/documents", json=NEW_DOCUMENT)
    client.patch(
        f"/documents/{EXISTING_DOCUMENT_ID}", json={"title": "Max Cashback"}
    )
    client.delete(f"/documents/{OTHER_DOCUMENT_ID}")

    assert RAW_CUSTOMERS.read_bytes() == raw_customers
    assert RAW_DOCUMENTS.read_bytes() == raw_documents
    assert (working_dir / RAW_CUSTOMERS.name).read_bytes() != raw_customers
    assert (working_dir / RAW_DOCUMENTS.name).read_bytes() != raw_documents
