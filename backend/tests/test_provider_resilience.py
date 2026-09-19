from unittest.mock import patch
from google.genai import errors

from backend.config.settings import settings
from backend.llm.gemini_client import (
    GeminiPermanentError,
    GeminiRetryExhaustedError,
)
from backend.llm.provider import provider
from backend.orchestration.routing import after_qa, after_review, after_security
from backend.orchestration.state import ProjectState


def test_primary_model_configuration():
    assert settings.llm_provider == "gemini"
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.primary_model == "gemini-3.8-flash"
    assert settings.gemini_thinking_level == "low"
    assert settings.enable_llm_fallback is True
    assert settings.groq_fallback_model == "openai/gpt-oss-20b"


def test_transient_503_bounded_retries_and_fallback():
    call_count = 0

    def mock_503(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise errors.APIError(
            code=503,
            response_json={"error": {"message": "Service Unavailable", "status": "UNAVAILABLE"}},
        )

    with patch.object(provider.gemini._get_client().models, "generate_content", side_effect=mock_503):
        with patch("time.sleep", return_value=None):
            result = provider.complete(
                system="sys",
                user="usr",
                slot="primary",
                json_mode=False,
                max_completion_tokens=50,
            )
            assert call_count == 3, f"Expected 3 Gemini attempts, got {call_count}"
            assert result.provider == "groq"
            assert result.model == "openai/gpt-oss-20b"
            assert result.fallback_used is True


def test_permanent_error_no_retry_no_fallback():
    call_count = 0

    def mock_401(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise errors.APIError(
            code=401,
            response_json={"error": {"message": "API_KEY_INVALID", "status": "UNAUTHENTICATED"}},
        )

    with patch.object(provider.gemini._get_client().models, "generate_content", side_effect=mock_401):
        try:
            provider.complete(
                system="sys",
                user="usr",
                slot="primary",
                json_mode=False,
            )
            assert False, "Expected GeminiPermanentError"
        except GeminiPermanentError:
            assert call_count == 1, f"Expected exactly 1 call without retry, got {call_count}"


def test_routing_loop_safety_total_reworks():
    # If total reworks reach limit, route to finalization
    state = ProjectState(
        security_report={"blocking": True, "overall_status": "FAIL"},
        retry_counts={"security": 2, "qa": 2, "review": 2},
        security_max_retries=5,
    )
    assert after_security(state) == "finalization_node"
