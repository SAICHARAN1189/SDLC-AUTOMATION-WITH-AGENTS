from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import pytest

from backend.config.settings import settings


@pytest.fixture(autouse=True)
def mock_db_for_agent_tests(request):
    """Provide a mock session for agent/LLM unit tests when DATABASE_URL is unconfigured.
    Explicitly skipped for test_supabase_persistence to allow testing real DB error behaviors.
    """
    if "test_supabase_persistence" in request.node.nodeid or "test_api" in request.node.nodeid:
        yield
        return

    if not settings.normalized_database_url:
        mock_session = MagicMock()
        mock_session.scalar.return_value = None
        mock_session.scalars.return_value.all.return_value = []
        mock_session.scalars.return_value.first.return_value = None

        @contextmanager
        def _mock_session_scope():
            yield mock_session

        with patch("backend.persistence.database.session_scope", _mock_session_scope), \
             patch("backend.persistence.repositories.session_scope", _mock_session_scope):
            yield
    else:
        yield
