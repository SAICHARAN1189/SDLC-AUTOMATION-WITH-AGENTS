from backend.app import create_app


def test_health():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "database" in payload["data"]


def test_create_project_and_run_demo():
    app = create_app()
    client = app.test_client()
    headers = {"Authorization": "Bearer demo-token"}
    created = client.post("/api/projects", json={"name": "Food", "idea": "Build a secure online food delivery platform."}, headers=headers)
    assert created.status_code == 201
    project_id = created.get_json()["data"]["id"]
    agents = client.get("/api/agents", headers=headers)
    assert agents.status_code == 200
    assert len(agents.get_json()["data"]) == 8
    run = client.post(
        f"/api/projects/{project_id}/runs",
        json={"execution_mode": "FULL_AUTONOMOUS", "demo_mode": True},
        headers=headers,
    )
    assert run.status_code == 201
