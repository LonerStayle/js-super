"""Detect backend auth pattern by scanning project files."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

JWT_LOGIN_RE = re.compile(r"['\"](/auth/login|/login|/sessions|/token)['\"]")
STATIC_TOKEN_RE = re.compile(r"os\.environ\[['\"][A-Z_]*TOKEN[A-Z_]*['\"]\]|os\.getenv\(['\"][A-Z_]*TOKEN[A-Z_]*['\"]")


@dataclass
class AuthDetection:
    pattern: str       # jwt-login | static-env-token | unknown
    evidence: list[str] = field(default_factory=list)


def detect_auth_pattern(project_root: Path) -> AuthDetection:
    evidence: list[str] = []
    for py_file in project_root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if JWT_LOGIN_RE.search(text):
            evidence.append(f"{py_file}: login route")
            return AuthDetection("jwt-login", evidence)
        if STATIC_TOKEN_RE.search(text):
            evidence.append(f"{py_file}: env-var token")
            return AuthDetection("static-env-token", evidence)
    return AuthDetection("unknown", evidence)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    result = detect_auth_pattern(root)
    # 첫 줄에 pattern 을 찍어 호출부(api-auto-testing Step 4)가 분기 판단에 사용
    print(f"pattern: {result.pattern}")
    for line in result.evidence:
        print(f"evidence: {line}")
