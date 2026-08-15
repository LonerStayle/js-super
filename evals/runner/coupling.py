"""CLAUDE.md 의 bash 코드 블록에서 결합 회귀 룰을 추출한다.

룰을 파일로 복제하지 않는다. CLAUDE.md 가 정답 원천이고 (설계서 D2),
러너는 실행할 때마다 새로 읽는다. 복제하면 정답이 둘이 되고,
CLAUDE.md 는 3.5개월에 54회 갱신되므로 매 릴리즈마다 어긋날 기회를 갖는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FENCE_OPEN = re.compile(r"^```(bash|sh|shell)\s*$")
FENCE_CLOSE = re.compile(r"^```\s*$")
EXPECTED = re.compile(r"^#\s*expected:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
COMMENT = re.compile(r"^\s*#")
LEADING_INT = re.compile(r"^\s*(?:각\s*)?(?:>=|<=|==)?\s*(\d+)")


@dataclass(frozen=True)
class Rule:
    """CLAUDE.md 한 곳에서 뽑은 검사 명령 하나."""

    source: str           # "CLAUDE.md:1234"
    command: str          # 실행할 셸 명령 (여러 줄 가능)
    expected: str | None  # "# expected:" 주석 값. 없으면 None

    @property
    def expected_int(self) -> int | None:
        if self.expected is None:
            return None
        match = LEADING_INT.match(self.expected)
        return int(match.group(1)) if match else None

    @property
    def expected_is_numeric(self) -> bool:
        return self.expected_int is not None

    @property
    def wants_at_least(self) -> bool:
        """'각 >= 1' 처럼 하한을 뜻하는 기대값인가."""
        if self.expected is None:
            return False
        return ">=" in self.expected or "이상" in self.expected


def collect_rules(repo_root: Path) -> list[Rule]:
    """결합 룰의 두 원천을 모두 읽는다.

    설계서의 116건은 CLAUDE.md 하나가 아니라
    CLAUDE.md 약 90건 + fixture README 약 26건의 합이다.
    한쪽만 읽으면 조용히 4분의 1을 놓친다.
    """
    rules: list[Rule] = []
    claude_md = repo_root / "CLAUDE.md"
    if claude_md.exists():
        rules.extend(parse_claude_md(claude_md))

    for readme in sorted(repo_root.glob("skills/*/tests/**/*.md")):
        rules.extend(parse_claude_md(readme, label=str(readme.relative_to(repo_root))))

    return rules


def parse_claude_md(path: Path, label: str | None = None) -> list[Rule]:
    """마크다운 하나를 읽어 Rule 목록을 만든다.

    이름은 CLAUDE.md 를 주 대상으로 삼아 붙였지만, 같은 형식(bash 코드 블록 +
    '# expected:' 주석)을 쓰는 fixture README 에도 그대로 쓴다.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    rules: list[Rule] = []
    in_fence = False
    buffer: list[str] = []
    buffer_start = 0

    for index, line in enumerate(lines, start=1):
        if not in_fence:
            if FENCE_OPEN.match(line):
                in_fence = True
                buffer = []
                buffer_start = index + 1
            continue
        if FENCE_CLOSE.match(line):
            rules.extend(_split_block(buffer, buffer_start, label or path.name))
            in_fence = False
            continue
        buffer.append(line)

    return rules


def _split_block(block: list[str], start_line: int, filename: str) -> list[Rule]:
    """코드 블록 하나를 '명령 + expected 주석' 단위로 자른다.

    CLAUDE.md 안에서 형식이 일관되게 '명령 여러 줄 → # expected: 값' 이다.
    expected 주석 없이 블록이 끝나면 기대값 없는 룰로 닫는다.
    """
    rules: list[Rule] = []
    pending: list[str] = []
    pending_line = start_line

    def close(expected: str | None) -> None:
        command = "\n".join(pending).strip()
        if command:
            rules.append(
                Rule(
                    source=f"{filename}:{pending_line}",
                    command=command,
                    expected=expected,
                )
            )

    for offset, raw in enumerate(block):
        line_number = start_line + offset
        matched = EXPECTED.match(raw.strip())
        if matched:
            close(matched.group("value"))
            pending = []
            pending_line = line_number + 1
            continue
        if COMMENT.match(raw) or not raw.strip():
            if not pending:
                pending_line = line_number + 1
            continue
        if not pending:
            pending_line = line_number
        pending.append(raw)

    close(None)
    return rules
