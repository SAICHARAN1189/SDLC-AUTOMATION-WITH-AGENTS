from unittest.mock import MagicMock, patch
import pytest

from backend.llm.config import (
    GEMINI_3_1_FLASH_LITE,
    GEMINI_3_5_FLASH_LITE,
    GEMINI_3_8_FLASH,
    GROQ_GPT_OSS_20B,
    GROQ_GPT_OSS_120B,
    AGENT_MODEL_CONFIG,
    get_agent_config,
)
from backend.llm.context import prepare_agent_context
from backend.llm.gemini_client import (
    GeminiDailyQuotaExhaustedError,
    GeminiPermanentError,
    GeminiRetryExhaustedError,
    classify_gemini_error,
)
from backend.llm.groq_client import (
    GroqPermanentError,
    GroqRateLimitExhaustedError,
    LLMResult,
)
from backend.llm.router import model_router


def test_agent_model_assignments():
    """Verify exact task-to-model mapping for all 7 engineering agents."""
    assert model_router.get_model("requirements") == GEMINI_3_5_FLASH_LITE
    assert model_router.get_provider("requirements") == "gemini"

    assert model_router.get_model("architecture") == GEMINI_3_8_FLASH
    assert model_router.get_provider("architecture") == "gemini"
    assert model_router.get_config("architecture").primary.thinking_level == "low"

    assert model_router.get_model("visual_architecture") == GEMINI_3_1_FLASH_LITE
    assert model_router.get_provider("visual_architecture") == "gemini"

    assert model_router.get_model("developer") == GROQ_GPT_OSS_120B
    assert model_router.get_provider("developer") == "groq"

    assert model_router.get_model("security") == GROQ_GPT_OSS_20B
    assert model_router.get_provider("security") == "groq"

    assert model_router.get_model("qa") == GROQ_GPT_OSS_120B
    assert model_router.get_provider("qa") == "groq"

    assert model_router.get_model("review") == GEMINI_3_5_FLASH_LITE
    assert model_router.get_provider("review") == "gemini"


def test_per_agent_fallback_configurations():
    """Verify per-agent fallback chains match specifications."""
    req_cfg = model_router.get_config("requirements")
    assert [fb.model for fb in req_cfg.fallbacks] == [GEMINI_3_1_FLASH_LITE, GROQ_GPT_OSS_20B]

    arch_cfg = model_router.get_config("architecture")
    assert [fb.model for fb in arch_cfg.fallbacks] == [GEMINI_3_5_FLASH_LITE, GROQ_GPT_OSS_20B]

    dev_cfg = model_router.get_config("developer")
    assert [fb.model for fb in dev_cfg.fallbacks] == [GEMINI_3_5_FLASH_LITE, GROQ_GPT_OSS_20B]

    sec_cfg = model_router.get_config("security")
    assert [fb.model for fb in sec_cfg.fallbacks] == [GEMINI_3_5_FLASH_LITE]

    qa_cfg = model_router.get_config("qa")
    assert [fb.model for fb in qa_cfg.fallbacks] == [GEMINI_3_5_FLASH_LITE, GROQ_GPT_OSS_20B]

    rev_cfg = model_router.get_config("review")
    assert [fb.model for fb in rev_cfg.fallbacks] == [GEMINI_3_1_FLASH_LITE, GROQ_GPT_OSS_20B]


def test_classify_gemini_daily_quota():
    """Verify that daily quota exhaustion is properly classified and distinct from transient 429."""
    class MockQuotaError(Exception):
        code = 429
        status = "RESOURCE_EXHAUSTED"

    quota_exc = MockQuotaError("Quota exceeded: GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    category, code, desc = classify_gemini_error(quota_exc)
    assert category == "DAILY_QUOTA"
    assert code == 429

    transient_exc = MockQuotaError("Rate limit exceeded: Requests per minute")
    category2, code2, desc2 = classify_gemini_error(transient_exc)
    assert category2 == "TRANSIENT"


def test_daily_quota_immediate_fallback_no_retry():
    """Verify daily quota error causes immediate fallback without retries on the same model."""
    attempts = []

    def mock_gemini_generate(*args, **kwargs):
        attempts.append(kwargs.get("model") or args[1])
        raise GeminiDailyQuotaExhaustedError("Daily quota exhausted")

    fake_groq_result = LLMResult(
        content='{"status": "ok"}',
        model=GROQ_GPT_OSS_20B,
        latency_ms=120.0,
        usage={},
        provider="groq",
    )

    with patch("backend.llm.providers.GeminiProviderAdapter.generate", side_effect=mock_gemini_generate):
        with patch("backend.llm.providers.GroqProviderAdapter.generate", return_value=fake_groq_result):
            # For architecture: Primary is Gemini 3.8, Fallback 1 is Gemini 3.5, Fallback 2 is Groq 20B
            result = model_router.generate(
                agent_name="architecture",
                messages=[{"role": "user", "content": "hello"}],
            )
            assert result.provider == "groq"
            assert result.model == GROQ_GPT_OSS_20B
            assert result.fallback_used is True
            # Both Gemini attempts (primary & fallback 1) should have fired exactly once with no backoff looping
            assert attempts == [GEMINI_3_8_FLASH, GEMINI_3_5_FLASH_LITE]


def test_permanent_error_fails_immediately():
    """Verify 401 permanent client errors fail immediately without executing fallbacks."""
    groq_called = False

    def mock_groq(*args, **kwargs):
        nonlocal groq_called
        groq_called = True
        return LLMResult(content="ok", model="groq", latency_ms=10.0, usage={})

    with patch(
        "backend.llm.providers.GeminiProviderAdapter.generate",
        side_effect=GeminiPermanentError("API key invalid", status_code=401),
    ):
        with patch("backend.llm.providers.GroqProviderAdapter.generate", side_effect=mock_groq):
            with pytest.raises(GeminiPermanentError):
                model_router.generate(
                    agent_name="requirements",
                    messages=[{"role": "user", "content": "hello"}],
                )
            assert groq_called is False


def test_context_preparation_token_efficiency():
    """Verify prepare_agent_context selects only relevant fields and preserves essential data."""
    raw_state = {
        "user_idea": "Build an online bookstore",
        "requirements": {
            "project_summary": "Online bookstore summary",
            "functional_requirements": ["Search books", "Checkout cart"],
            "acceptance_criteria": ["Given a cart, user can pay"],
        },
        "architecture": {
            "architecture_style": "Modular Monolith",
            "backend": "Flask",
            "database": "PostgreSQL",
            "services": ["catalog", "order"],
        },
        "code": {
            "files": [
                {"path": "app.py", "content": "from flask import Flask\napp = Flask(__name__)"}
            ]
        },
        "security_report": {
            "overall_status": "FAIL",
            "vulnerabilities": [
                {
                    "severity": "HIGH",
                    "category": "sql_injection",
                    "description": "SQL Injection in cart query",
                    "evidence": "SELECT * FROM carts WHERE id = " + "1",
                    "affected_file": "app.py",
                    "affected_line": 10,
                    "remediation": "Use parameterized query",
                }
            ],
        },
        "test_report": {
            "overall_status": "FAIL",
            "failures": [{"test_name": "test_checkout", "actual": "500", "expected": "200"}],
        },
        "workflow_events": [{"event": "DUMP_OF_MASSIVE_LOGS"} for _ in range(100)],
        "messages": [{"msg": "chatty message"} for _ in range(50)],
    }

    # 1. Requirements agent context
    req_ctx = prepare_agent_context("requirements", raw_state)
    assert "user_idea" in req_ctx
    assert "workflow_events" not in req_ctx
    assert "messages" not in req_ctx

    # 2. Developer agent context
    dev_ctx = prepare_agent_context("developer", raw_state)
    assert dev_ctx["architecture"]["backend"] == "Flask"
    assert len(dev_ctx["existing_files"]) == 1
    assert dev_ctx["existing_files"][0]["path"] == "app.py"
    # Preserves exact security findings needed for remediation
    assert len(dev_ctx["security_feedback"]) == 1
    assert dev_ctx["security_feedback"][0]["severity"] == "HIGH"
    # Preserves exact test failures
    assert len(dev_ctx["qa_feedback"]) == 1
    # Removes massive logs
    assert "workflow_events" not in dev_ctx

    # 3. Security agent context
    sec_ctx = prepare_agent_context("security", raw_state)
    assert "files" in sec_ctx
    assert sec_ctx["files"][0]["path"] == "app.py"
    assert "workflow_events" not in sec_ctx
