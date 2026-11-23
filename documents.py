import json
import re
from pathlib import Path

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def load_documents(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def build_chunks(documents):
    return [
        {
            "chunk_id": f"{document['document_id']}-{chunk_index}",
            "document_id": document["document_id"],
            "chunk_index": chunk_index,
            "text": chunk_text,
        }
        for document in documents
        for chunk_index, chunk_text in enumerate(
            split_into_chunks(document["text"])
        )
    ]


def split_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if not text:
        return []
    step = chunk_size - overlap
    last_start = max(len(text) - overlap, 1)
    return [
        text[start:start + chunk_size]
        for start in range(0, last_start, step)
    ]


def search_chunks(chunks, query, top_k):
    query_terms = tokenize(query)
    scored_chunks = [
        {**chunk, "score": score_chunk(chunk, query_terms)}
        for chunk in chunks
    ]
    matching_chunks = [
        chunk for chunk in scored_chunks if chunk["score"] > 0
    ]
    ranked_chunks = sorted(
        matching_chunks,
        key=lambda chunk: (-chunk["score"], chunk["chunk_id"]),
    )
    return ranked_chunks[:top_k]


def summarize_documents(documents, chunks):
    return [
        {
            "document_id": document["document_id"],
            "title": document["title"],
            "chunk_count": count_chunks(chunks, document["document_id"]),
        }
        for document in documents
    ]


def count_chunks(chunks, document_id):
    return sum(1 for chunk in chunks if chunk["document_id"] == document_id)


def score_chunk(chunk, query_terms):
    return len(query_terms & tokenize(chunk["text"]))


def tokenize(text):
    return set(re.findall(r"\w+", text.lower()))
