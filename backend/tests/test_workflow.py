from backend.agents.developer_agent import DeveloperAgent
from backend.agents.security_agent import SecurityAgent
from backend.orchestration.graph import invoke_workflow
from backend.orchestration.state import initial_state


def test_security_rework_loop_demo():
    state = initial_state(
        {
            "project_id": "p1",
            "run_id": "run-loop-1",
            "user_id": "demo-user",
            "user_idea": "Build a secure online food delivery platform.",
            "execution_mode": "FULL_AUTONOMOUS",
            "demo_mode": True,
            "security_max_retries": 2,
            "qa_max_retries": 2,
            "review_max_retries": 2,
        }
    )
    result = invoke_workflow(dict(state))
    assert result["security_status"] == "PASS"
    assert result["testing_status"] == "PASS"
    assert result["review_status"] == "PASS"
    assert result["final_status"] == "COMPLETED"
    assert any(m.get("message_type") == "SECURITY_FEEDBACK" for m in result.get("messages") or [])
    assert (result.get("retry_counts") or {}).get("security", 0) >= 1


def test_developer_modes():
    agent = DeveloperAgent()
    initial = agent.demo_output({"developer_mode": "INITIAL_IMPLEMENTATION"})
    rework = agent.demo_output({"developer_mode": "SECURITY_REWORK"})
    assert "super-secret-db-password" in initial.files[0].content
    assert "super-secret-db-password" not in rework.files[0].content


def test_security_agent_fail_then_pass():
    agent = SecurityAgent()
    fail = agent.demo_output({"code": {"files": [{"path": "app.py", "content": 'DB_PASSWORD = "super-secret-db-password"'}]}})
    passed = agent.demo_output({"code": {"files": [{"path": "app.py", "content": "query = 'INSERT INTO orders (restaurant, user_id) VALUES (%s, %s)'"}]}})
    assert fail.blocking
    assert not passed.blocking
