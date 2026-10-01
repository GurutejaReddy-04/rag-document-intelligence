"""
Tests for PDF ingestion: text loading, recursive chunking, and ChromaDB vector persistence.
"""

import pytest
from ingest import load_pdf, chunk_documents, embed_and_store, ingest_pdf


def test_load_pdf_valid(sample_pdf):
    """Test extracting text page-by-page from a valid multi-page PDF."""
    pages = load_pdf(sample_pdf)
    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert "Distributed consensus" in pages[0]["content"]
    assert pages[1]["page"] == 2
    assert "operational latencies" in pages[1]["content"]
    assert pages[0]["source"] == "sample_doc.pdf"


def test_load_pdf_custom_source_name(sample_pdf):
    """Test overriding source name in metadata for temp uploads."""
    pages = load_pdf(sample_pdf, source_name="custom_title.pdf")
    assert len(pages) == 2
    assert pages[0]["source"] == "custom_title.pdf"


def test_load_pdf_empty_document(empty_pdf):
    """Test handling of an image-only / blank PDF (no extractable text)."""
    pages = load_pdf(empty_pdf)
    assert len(pages) == 0


def test_chunk_documents(sample_pdf):
    """Test recursive character text splitting and metadata preservation."""
    pages = load_pdf(sample_pdf)
    chunks, metadatas = chunk_documents(pages)

    assert len(chunks) >= 2
    assert len(chunks) == len(metadatas)

    for meta in metadatas:
        assert "page" in meta
        assert "source" in meta
        assert meta["page"] in (1, 2)
        assert meta["source"] == "sample_doc.pdf"


def test_embed_and_store_lifecycle(sample_pdf):
    """Test initial storage, deduplication skipping, and force re-ingestion."""
    collection_name = "test-ingest-lifecycle"
    pages = load_pdf(sample_pdf)
    chunks, metadatas = chunk_documents(pages)

    # 1. Initial ingestion
    msg1 = embed_and_store(chunks, metadatas, collection_name, "sample_doc.pdf", force=False)
    assert "chunks stored in collection" in msg1

    # 2. Duplicate upload without force=True (should skip)
    msg2 = embed_and_store(chunks, metadatas, collection_name, "sample_doc.pdf", force=False)
    assert "already ingested" in msg2
    assert "Pass force=True" in msg2

    # 3. Re-ingestion with force=True (should replace)
    msg3 = embed_and_store(chunks, metadatas, collection_name, "sample_doc.pdf", force=True)
    assert "chunks stored in collection" in msg3


def test_ingest_pdf_pipeline(sample_pdf):
    """Test end-to-end ingest_pdf helper function."""
    collection_name = "test-pipeline-collection"
    msg = ingest_pdf(sample_pdf, collection_name, force=True, source_name="pipeline_test.pdf")
    assert "chunks stored in collection" in msg
