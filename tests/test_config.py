"""
Tests for configuration loading, environment variables, and credential failure behavior.
"""

import os
import pytest
from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K_RESULTS,
    EMBEDDING_MODEL,
    ALLOWED_ORIGINS,
    check_gemini_api_key,
)


def test_config_defaults():
    """Verify default chunking, retrieval, and embedding parameters."""
    assert CHUNK_SIZE > 0
    assert CHUNK_OVERLAP >= 0
    assert TOP_K_RESULTS >= 1
    assert EMBEDDING_MODEL == "all-MiniLM-L6-v2"
    assert isinstance(ALLOWED_ORIGINS, list)


def test_check_gemini_api_key_success(monkeypatch):
    """Verify check_gemini_api_key returns the key when configured."""
    monkeypatch.setenv("GEMINI_API_KEY", "valid-test-key-12345")
    key = check_gemini_api_key()
    assert key == "valid-test-key-12345"


def test_check_gemini_api_key_missing_raises_environment_error(monkeypatch):
    """Verify EnvironmentError is raised when GEMINI_API_KEY is unset or empty."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="GEMINI_API_KEY is not set"):
        check_gemini_api_key()

    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(EnvironmentError, match="GEMINI_API_KEY is not set"):
        check_gemini_api_key()
