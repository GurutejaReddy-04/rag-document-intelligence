"""
Tests for Gemini prompt assembly, deterministic fallbacks, and answer generation.
"""

from unittest.mock import MagicMock
import pytest
from generator import generate_answer


def test_generate_answer_empty_context():
    """Verify deterministic fallback is returned immediately when context is empty."""
    ans = generate_answer("What is Raft?", [])
    assert ans == "No relevant content was found in the document for this question."


def test_generate_answer_with_mocked_llm(mock_gemini_client):
    """Verify context formatting and LLM invocation with retrieved chunks."""
    context = [
        {"content": "Leader election is held upon heartbeat timeout.", "page": 1, "source": "doc.pdf"},
        {"content": "Log replication occurs monotonically.", "page": 2, "source": "doc.pdf"},
    ]

    answer = generate_answer("How does leader election work?", context)
    assert len(answer) > 0
    mock_gemini_client.models.generate_content.assert_called_once()

    # Verify prompt arguments passed to the model
    call_args = mock_gemini_client.models.generate_content.call_args
    assert "contents" in call_args.kwargs
    prompt_sent = call_args.kwargs["contents"]
    assert "[Page 1 | doc.pdf]" in prompt_sent
    assert "[Page 2 | doc.pdf]" in prompt_sent
    assert "How does leader election work?" in prompt_sent


def test_generate_answer_llm_failure(monkeypatch):
    """Verify RuntimeError is raised gracefully if the GenAI API call fails."""
    mock_failing_client = MagicMock()
    mock_failing_client.models.generate_content.side_effect = ConnectionError("Quota exceeded or upstream timeout")

    import generator
    monkeypatch.setattr(generator, "get_client", lambda: mock_failing_client)

    context = [{"content": "Some text", "page": 1, "source": "doc.pdf"}]
    with pytest.raises(RuntimeError, match="Answer generation failed"):
        generate_answer("Query", context)
