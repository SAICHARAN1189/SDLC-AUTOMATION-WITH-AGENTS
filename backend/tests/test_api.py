from backend.app import create_app


def test_health():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "database" in payload["data"]


def test_create_project_fail_fast_without_db():
    """Verify that project creation fails with 500 CONFIGURATION_ERROR if DATABASE_URL is not set."""
    from unittest.mock import patch
    from backend.config.settings import settings
    from backend.persistence.database import reset_engine

    reset_engine()
    with patch.object(settings, "database_url", ""):
        app = create_app()
        client = app.test_client()
        headers = {"Authorization": "Bearer demo-token"}
        response = client.post(
            "/api/projects",
            json={"name": "Food", "idea": "Build a secure online food delivery platform."},
            headers=headers,
        )
        assert response.status_code == 500
        payload = response.get_json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "CONFIGURATION_ERROR"
    reset_engine()


def test_provider_routing():
    from backend.llm.provider import provider
    from backend.config.settings import settings

    # Current provider is gemini
    assert provider.current_provider == "gemini"
    prov, model = provider.resolve_provider_and_model("primary")
    assert prov == "gemini"
    assert model == "gemini-3.8-flash"

    # Explicit Groq model override routes to Groq
    prov_groq, model_groq = provider.resolve_provider_and_model(override="openai/gpt-oss-120b")
    assert prov_groq == "groq"
    assert model_groq == "openai/gpt-oss-120b"

