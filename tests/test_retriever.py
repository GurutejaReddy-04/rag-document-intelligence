"""
Tests for semantic retrieval from ChromaDB collections using cosine distance.
"""

import pytest
from ingest import ingest_pdf
from retriever import retrieve_context


def test_retrieve_context_success(sample_pdf):
    """Test semantic retrieval of top-K relevant chunks with cosine distance scores."""
    collection_name = "test-retriever-collection"
    ingest_pdf(sample_pdf, collection_name, force=True, source_name="sample_doc.pdf")

    # Query matching page 1 ("Distributed consensus protocols like Raft")
    results = retrieve_context("What does Raft consensus achieve?", collection_name, top_k=2)

    assert len(results) > 0
    top_result = results[0]

    assert "content" in top_result
    assert "page" in top_result
    assert "source" in top_result
    assert "score" in top_result
    assert isinstance(top_result["score"], float)
    assert top_result["source"] == "sample_doc.pdf"
    # In Raft query, Page 1 should be ranked top
    assert top_result["page"] == 1


def test_retrieve_context_nonexistent_collection():
    """Test retrieval from an empty/unpopulated collection returns empty list without crashing."""
    results = retrieve_context("Anything here?", "nonexistent-coll-xyz", top_k=3)
    assert results == []
