import json
import re
from pathlib import Path

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def load_documents(path):
    """Read the documents from a JSON file.

    :param path: Location of the JSON file.
    :return: List of documents with document_id, title and text.
    """
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def build_chunks(documents):
    """Split every document into overlapping chunks.

    :param documents: Documents with document_id and text.
    :return: Chunks with chunk_id, document_id, chunk_index and text.
    """
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
    """Split text into fixed-length character chunks that overlap.

    :param text: Text to split.
    :param chunk_size: Number of characters in each chunk.
    :param overlap: Number of characters shared by consecutive chunks.
    :return: List of chunk strings, empty when the text is empty.
    """
    if not text:
        return []
    step = chunk_size - overlap
    start_limit = max(len(text) - overlap, 1)
    return [
        text[start:start + chunk_size]
        for start in range(0, start_limit, step)
    ]


def summarize_documents(documents, chunks):
    """Describe each document with its number of chunks.

    :param documents: Documents with document_id and title.
    :param chunks: Chunks built from the documents.
    :return: List with document_id, title and chunk_count per document.
    """
    return [
        {
            "document_id": document["document_id"],
            "title": document["title"],
            "chunk_count": count_chunks(chunks, document["document_id"]),
        }
        for document in documents
    ]


def count_chunks(chunks, document_id):
    """Count the chunks that belong to one document.

    :param chunks: Chunks with a document_id.
    :param document_id: Document to count chunks for.
    :return: Number of chunks of that document.
    """
    return sum(1 for chunk in chunks if chunk["document_id"] == document_id)


def search_chunks(chunks, query, top_k):
    """Rank chunks by how many query words they contain.

    Chunks that contain no query word are left out.

    :param chunks: Chunks to search.
    :param query: Search text.
    :param top_k: Maximum number of chunks to return.
    :return: Best matching chunks with a score added, best first.
    """
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


def score_chunk(chunk, query_terms):
    """Count the query words found in a chunk.

    :param chunk: Chunk with text.
    :param query_terms: Set of lowercase query words.
    :return: Number of query words the chunk contains.
    """
    return len(query_terms & tokenize(chunk["text"]))


def tokenize(text):
    """Lowercase text and collect its distinct words.

    :param text: Text to split into words.
    :return: Set of lowercase words.
    """
    return set(re.findall(r"\w+", text.lower()))


def make_document_id(title):
    """Turn a title into a lowercase, hyphenated document ID.

    A plus sign is spelled out, as in build-plus-student-starter.

    :param title: Title of the document.
    :return: ID made of lowercase letters, digits and hyphens.
    """
    spelled_out = title.lower().replace("+", " plus ")
    return re.sub(r"[^a-z0-9]+", "-", spelled_out).strip("-")


def find_document(documents, document_id):
    """Look up one document by its ID.

    :param documents: Documents with document_id.
    :param document_id: ID to look for.
    :return: The document, or None when the ID is unknown.
    """
    return next(
        (
            document
            for document in documents
            if document["document_id"] == document_id
        ),
        None,
    )


def has_duplicate(documents, title, document_id):
    """Check whether a title or an ID is already taken.

    Titles are compared ignoring case.

    :param documents: Documents with document_id and title.
    :param title: Title to check.
    :param document_id: ID to check.
    :return: True when a document has the same title or the same ID.
    """
    return any(
        document["document_id"] == document_id
        or document["title"].casefold() == title.casefold()
        for document in documents
    )
