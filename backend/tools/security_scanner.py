from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

SECRET_REGEX = re.compile(
    r"(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]+['\"]",
    re.I,
)
SQL_INJECTION = re.compile(
    r"(execute|executemany)\s*\(\s*[f\"'].*%s|f[\"'].*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)|cursor\.execute\(\s*[f\"']",
    re.I,
)
XSS = re.compile(r"(innerHTML|dangerouslySetInnerHTML|markupsafe\.Markup\()", re.I)
COMMAND = re.compile(r"(os\.system|subprocess\.(call|run|Popen)|eval\(|exec\()", re.I)
DESERIALIZE = re.compile(r"(pickle\.loads|yaml\.load\(|marshal\.loads)", re.I)
WEAK_CRYPTO = re.compile(r"(md5|sha1)\(", re.I)


@dataclass
class DeterministicFinding:
    category: str
    severity: str
    description: str
    evidence: str
    affected_file: str
    affected_line: int
    remediation: str
    confidence: float = 0.9
    source: str = "DETERMINISTIC_FINDING"


def scan_files(files: Iterable[dict[str, str]]) -> list[DeterministicFinding]:
    findings: list[DeterministicFinding] = []
    for item in files:
        path = item.get("path") or ""
        content = item.get("content") or ""
        for idx, line in enumerate(content.splitlines(), start=1):
            checks = [
                (SECRET_REGEX, "hardcoded_secret", "HIGH", "Possible hardcoded secret", "Move secrets to environment variables."),
                (SQL_INJECTION, "sql_injection", "HIGH", "Possible SQL injection via string formatting", "Use parameterized queries."),
                (XSS, "xss", "MEDIUM", "Possible XSS sink", "Escape or sanitize untrusted output."),
                (COMMAND, "command_injection", "HIGH", "Dangerous dynamic execution", "Avoid eval/exec/os.system; use safe APIs."),
                (DESERIALIZE, "unsafe_deserialization", "HIGH", "Unsafe deserialization", "Avoid pickle/yaml.load on untrusted data."),
                (WEAK_CRYPTO, "insecure_cryptography", "MEDIUM", "Weak hash algorithm", "Use SHA-256 or stronger."),
            ]
            for regex, category, severity, description, remediation in checks:
                if regex.search(line):
                    findings.append(
                        DeterministicFinding(
                            category=category,
                            severity=severity,
                            description=description,
                            evidence=line.strip()[:300],
                            affected_file=path,
                            affected_line=idx,
                            remediation=remediation,
                        )
                    )
    return findings
