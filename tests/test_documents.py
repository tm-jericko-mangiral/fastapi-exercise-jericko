import pytest
from fastapi.testclient import TestClient

from documents import build_chunks, search_chunks, split_into_chunks
from main import app

DOCUMENT_COUNT = 3
SAMPLE_CHUNKS = [
    {"chunk_id": "a-0", "document_id": "a", "text": "lost card hotline"},
    {"chunk_id": "a-1", "document_id": "a", "text": "card annual fee"},
    {"chunk_id": "b-0", "document_id": "b", "text": "loan repayment"},
]


@pytest.fixture
def client():
    return TestClient(app)


def test_split_into_chunks_returns_empty_list_for_empty_text():
    assert split_into_chunks("") == []


def test_split_into_chunks_keeps_short_text_in_one_chunk():
    assert split_into_chunks("short text", chunk_size=50, overlap=10) == [
        "short text"
    ]


def test_split_into_chunks_overlaps_consecutive_chunks():
    text = "".join(str(number % 10) for number in range(500))

    chunks = split_into_chunks(text, chunk_size=200, overlap=40)

    assert [len(chunk) for chunk in chunks] == [200, 200, 180]
    assert chunks[0][-40:] == chunks[1][:40]


def test_build_chunks_names_chunks_by_document_and_index():
    documents = [{"document_id": "guide", "text": "x" * 700}]

    chunks = build_chunks(documents)

    assert [chunk["chunk_id"] for chunk in chunks] == ["guide-0", "guide-1"]


def test_search_chunks_ranks_by_number_of_matching_terms():
    results = search_chunks(SAMPLE_CHUNKS, "lost card", top_k=3)

    assert [chunk["chunk_id"] for chunk in results] == ["a-0", "a-1"]
    assert [chunk["score"] for chunk in results] == [2, 1]


def test_search_chunks_limits_results_to_top_k():
    results = search_chunks(SAMPLE_CHUNKS, "card", top_k=1)

    assert len(results) == 1


def test_search_chunks_ignores_case():
    results = search_chunks(SAMPLE_CHUNKS, "LOAN", top_k=3)

    assert [chunk["chunk_id"] for chunk in results] == ["b-0"]


def test_search_chunks_returns_empty_list_when_nothing_matches():
    assert search_chunks(SAMPLE_CHUNKS, "mortgage", top_k=3) == []


def test_documents_route_lists_documents_with_chunk_counts(client):
    response = client.get("/documents")

    documents = response.json()
    assert response.status_code == 200
    assert len(documents) == DOCUMENT_COUNT
    assert all(document["chunk_count"] > 0 for document in documents)


def test_search_route_returns_chunk_from_matching_document(client):
    response = client.get("/documents/search", params={"q": "lounge"})

    results = response.json()
    assert response.status_code == 200
    assert results[0]["document_id"] == "astra-travel-miles-platinum"


def test_search_route_limits_results_to_top_k(client):
    response = client.get("/documents/search", params={"q": "the", "top_k": 2})

    assert len(response.json()) == 2


def test_search_route_requires_a_query(client):
    response = client.get("/documents/search")

    assert response.status_code == 422


def test_search_route_rejects_top_k_below_one(client):
    response = client.get("/documents/search", params={"q": "card", "top_k": 0})

    assert response.status_code == 422
