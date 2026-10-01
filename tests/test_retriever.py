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


def test_cross_collection_isolation(tmp_path):
    """Verify that document chunks are strictly isolated across collection boundaries."""
    import fitz

    # Generate Document A for Collection Alpha
    pdf_a = tmp_path / "doc_alpha.pdf"
    doc_a = fitz.open()
    p_a = doc_a.new_page()
    p_a.insert_text((50, 72), "Alpha Project Confidential Code: ALPHA-SECRET-9942.")
    doc_a.save(str(pdf_a))
    doc_a.close()

    # Generate Document B for Collection Beta
    pdf_b = tmp_path / "doc_beta.pdf"
    doc_b = fitz.open()
    p_b = doc_b.new_page()
    p_b.insert_text((50, 72), "Beta Project Confidential Code: BETA-SECRET-7715.")
    doc_b.save(str(pdf_b))
    doc_b.close()

    ingest_pdf(str(pdf_a), "coll-alpha", force=True, source_name="doc_alpha.pdf")
    ingest_pdf(str(pdf_b), "coll-beta", force=True, source_name="doc_beta.pdf")

    # Querying Collection Alpha must NEVER return Beta content
    results_alpha = retrieve_context("Confidential Code", "coll-alpha", top_k=5)
    assert len(results_alpha) > 0
    for r in results_alpha:
        assert "ALPHA-SECRET-9942" in r["content"]
        assert "BETA-SECRET-7715" not in r["content"]
        assert r["source"] == "doc_alpha.pdf"

    # Querying Collection Beta must NEVER return Alpha content
    results_beta = retrieve_context("Confidential Code", "coll-beta", top_k=5)
    assert len(results_beta) > 0
    for r in results_beta:
        assert "BETA-SECRET-7715" in r["content"]
        assert "ALPHA-SECRET-9942" not in r["content"]
        assert r["source"] == "doc_beta.pdf"
