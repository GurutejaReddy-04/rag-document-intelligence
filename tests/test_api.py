"""
Integration tests for FastAPI REST routes, latency middleware, and collection management.
"""

import io
import pytest


def test_health_check(client):
    """Verify /health liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Process-Time" in response.headers


@pytest.mark.parametrize(
    "collection_name,expected_status",
    [
        ("valid-collection", 200),
        ("paper_2026", 200),
        ("a", 400),               # too short (< 3 chars)
        ("name with spaces", 400), # spaces forbidden
        ("-invalid-prefix", 400),  # must start with alphanumeric
        ("invalid-suffix-", 400),  # must end with alphanumeric
        ("invalid@chars!", 400),   # special characters forbidden
    ],
)
def test_collection_name_validation(client, sample_pdf, collection_name, expected_status):
    """Verify collection name validation rules enforced across routes."""
    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"collection_name": collection_name, "force": "true"},
        )
    assert response.status_code == expected_status


def test_upload_non_pdf_rejected(client):
    """Verify uploading non-PDF files is rejected with 400 Bad Request."""
    response = client.post(
        "/upload",
        files={"file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")},
        data={"collection_name": "text-collection", "force": "false"},
    )
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_malformed_pdf_handled(client, malformed_file):
    """Verify uploading a corrupt or malformed PDF is handled gracefully with an error response."""
    with open(malformed_file, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("corrupt.pdf", f, "application/pdf")},
            data={"collection_name": "malformed-test-coll", "force": "true"},
        )
    # Server should return 500 with descriptive error detail rather than crashing unhandled
    assert response.status_code == 500
    assert "detail" in response.json()


def test_upload_and_query_flow(client, sample_pdf):
    """Test full upload followed by query and cited response."""
    coll = "e2e-test-collection"

    # 1. Ingest document
    with open(sample_pdf, "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("sample_doc.pdf", f, "application/pdf")},
            data={"collection_name": coll, "force": "true"},
        )
    assert upload_resp.status_code == 200
    assert "chunks stored in collection" in upload_resp.json()["message"]

    # 2. Query empty question (should fail)
    bad_query_resp = client.post(
        "/query",
        json={"question": "   ", "collection_name": coll},
    )
    assert bad_query_resp.status_code == 400

    # 3. Valid Query
    query_resp = client.post(
        "/query",
        json={"question": "What is Raft consensus?", "collection_name": coll},
    )
    assert query_resp.status_code == 200
    body = query_resp.json()
    assert "answer" in body
    assert "sources" in body
    assert len(body["sources"]) > 0
    assert body["sources"][0]["source"] == "sample_doc.pdf"


def test_collections_crud(client, sample_pdf):
    """Test listing, deleting, and resetting collections."""
    coll = "crud-test-coll"

    # Ingest to ensure collection exists
    with open(sample_pdf, "rb") as f:
        client.post(
            "/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"collection_name": coll, "force": "true"},
        )

    # 1. List collections
    list_resp = client.get("/collections")
    assert list_resp.status_code == 200
    assert coll in list_resp.json()["collections"]

    # 2. Delete existing collection
    del_resp = client.delete(f"/collections/{coll}")
    assert del_resp.status_code == 200
    assert f"Collection '{coll}' deleted." in del_resp.json()["message"]

    # 3. Delete non-existent collection (returns 404)
    del_nonexistent = client.delete(f"/collections/{coll}")
    assert del_nonexistent.status_code == 404

    # 4. Reset system
    reset_resp = client.post("/reset?wipe_uploads=false")
    assert reset_resp.status_code == 200
    assert "All collections deleted" in reset_resp.json()["message"]
