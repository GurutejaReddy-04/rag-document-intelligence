"""
Shared pytest fixtures and test configuration for RAG Document Intelligence.
Ensures clean-clone credential-free execution and isolated ChromaDB storage.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path for direct imports
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Safe defaults before importing any backend module
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("GEMINI_API_KEY", "mock-gemini-test-key")


@pytest.fixture(scope="session", autouse=True)
def test_workspace():
    """Create isolated temp directories for ChromaDB and uploads during the test run."""
    temp_dir = tempfile.mkdtemp(prefix="rag_test_workspace_")
    chroma_test_path = os.path.join(temp_dir, "chroma_db")
    upload_test_path = os.path.join(temp_dir, "uploads")
    os.makedirs(chroma_test_path, exist_ok=True)
    os.makedirs(upload_test_path, exist_ok=True)

    os.environ["CHROMA_PATH"] = chroma_test_path
    os.environ["UPLOAD_DIR"] = upload_test_path

    # Point db.py singleton to the test path
    import config
    config.CHROMA_PATH = chroma_test_path
    config.UPLOAD_DIR = upload_test_path

    yield {
        "root": temp_dir,
        "chroma": chroma_test_path,
        "uploads": upload_test_path,
    }

    # Teardown
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf(tmp_path):
    """Generate a valid 2-page PDF file with predictable test text."""
    pdf_path = tmp_path / "sample_doc.pdf"
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Distributed consensus protocols like Raft ensure fault tolerance across networked state machines. "
        "The leader handles all client requests and replicates log entries.",
    )

    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "In section 2, operational latencies under partition are evaluated. "
        "Heartbeat timeouts range from 150ms to 300ms to prevent split-vote scenarios.",
    )

    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def empty_pdf(tmp_path):
    """Generate a valid PDF containing only blank pages (no extractable text)."""
    pdf_path = tmp_path / "empty_doc.pdf"
    doc = fitz.open()
    doc.new_page()  # blank page 1
    doc.new_page()  # blank page 2
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def malformed_file(tmp_path):
    """Generate a non-PDF file with a .pdf extension."""
    bad_path = tmp_path / "corrupt.pdf"
    bad_path.write_bytes(b"%PDF-1.4\nCorrupt header and random invalid binary garbage\x00\xff\xfe")
    return str(bad_path)


@pytest.fixture
def mock_gemini_client(monkeypatch):
    """Mock the Google GenAI SDK client to prevent real network calls and API key dependence."""
    mock_response = MagicMock()
    mock_response.text = (
        "Distributed consensus protocols like Raft ensure fault tolerance via leader log replication [Page 1, sample_doc.pdf]."
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    import generator
    monkeypatch.setattr(generator, "_client", mock_client)
    monkeypatch.setattr(generator, "get_client", lambda: mock_client)
    return mock_client


@pytest.fixture
def client(mock_gemini_client):
    """FastAPI TestClient fixture with mocked LLM client."""
    from main import app
    return TestClient(app)
