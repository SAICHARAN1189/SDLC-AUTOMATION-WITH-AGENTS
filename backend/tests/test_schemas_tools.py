from backend.models.schemas import RequirementsOutput, SecurityOutput, GateStatus
from backend.tools.security_scanner import scan_files
from backend.tools.mermaid_validator import validate_mermaid


def test_requirements_schema():
    output = RequirementsOutput(project_summary="x")
    assert output.project_summary == "x"


def test_scanner_finds_secret_and_sql():
    findings = scan_files(
        [
            {
                "path": "app.py",
                "content": 'password = "hunter2"\nquery = f"INSERT INTO orders (restaurant) VALUES (\'{restaurant}\')"\n',
            }
        ]
    )
    cats = {item.category for item in findings}
    assert "hardcoded_secret" in cats
    assert "sql_injection" in cats


def test_mermaid_validator():
    ok = validate_mermaid("flowchart TD\n  A-->B")
    assert ok.valid
    bad = validate_mermaid("not a diagram")
    assert not bad.valid


def test_security_output_disclaimer():
    report = SecurityOutput(overall_status=GateStatus.PASS)
    assert "certified" in report.disclaimer.lower()
