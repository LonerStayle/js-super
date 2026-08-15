"""CLAUDE.md 의 bash 코드 블록에서 결합 회귀 룰을 추출한다.

룰을 파일로 복제하지 않는다. CLAUDE.md 가 정답 원천이고 (설계서 D2),
러너는 실행할 때마다 새로 읽는다. 복제하면 정답이 둘이 되고,
CLAUDE.md 는 3.5개월에 54회 갱신되므로 매 릴리즈마다 어긋날 기회를 갖는다.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from evals.runner.guard import mask_quoted

FENCE_OPEN = re.compile(r"^```(bash|sh|shell)\s*$")
FENCE_CLOSE = re.compile(r"^```\s*$")
EXPECTED = re.compile(r"^#\s*expected:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
COMMENT = re.compile(r"^\s*#")
LEADING_INT = re.compile(r"^\s*(?:각\s*)?(?:>=|<=|==)?\s*(\d+)")

# 순수 숫자 기대값. 숫자 뒤에 조건이 붙으면 (예: "0 (Anti-Pattern catch 라인만 허용)")
# 기계 비교로 판정할 수 없다 — 그건 자연어 기대값이라 사람이나 모델이 봐야 한다.
PURE_INT = re.compile(r"^\s*(?:각\s*)?(?:>=|<=|==)?\s*\d+\s*(?:줄|건|개|lines?|line)?\s*$")


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
        """기계 비교가 가능한 순수 숫자 기대값인가.

        `0` 은 숫자지만 `0 (Anti-Pattern catch 라인만 허용)` 은 아니다.
        뒤의 조건이 판정을 바꾸므로 자연어로 취급해 모델 판정으로 보낸다.
        """
        return self.expected is not None and bool(PURE_INT.match(self.expected))

    @property
    def key(self) -> str:
        """기준선에 쓸 안정적인 식별자.

        줄 번호를 쓰면 CLAUDE.md 에 한 줄만 끼어도 전체 기준선이 어긋난다.
        명령 내용의 해시라 룰이 파일 안에서 옮겨다녀도 그대로다.
        """
        normalized = " ".join(self.command.split())
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        return f"coupling/{digest[:12]}"

    @property
    def wants_at_least(self) -> bool:
        """'각 >= 1' 처럼 하한을 뜻하는 기대값인가."""
        if self.expected is None:
            return False
        return ">=" in self.expected or "이상" in self.expected


WC_L = re.compile(r"\bwc\s+(-\w+\s+)*-\w*l")
GREP_COUNT = re.compile(r"\bgrep\b(?:\s+-\w+)*\s+-\w*c\w*\b")
# `python3 -c "... print(len(x))"` 처럼 값을 찍는 한 줄 명령. 목록이 아니다.
PY_ONELINER = re.compile(r"\bpython3?\s+-c\b")


def infer_check(rule: Rule) -> tuple[str, str]:
    """룰 하나에 맞는 (비교 연산, 출력 해석 방식) 을 정한다.

    CLAUDE.md 룰은 두 종류다.

    - 개수를 내는 명령 (`grep -c`, `... | wc -l`) — 출력이 숫자다.
      파일이 여럿이면 `경로:개수` 형식이 된다.
    - 목록을 내는 명령 (`grep -n`, `grep -l`, `ls`, `find`) — 출력이 줄 목록이다.
      이때 `# expected: 0` 은 숫자 0 이 아니라 '출력 없음' 을 뜻한다.

    이 구분을 안 하면 목록 명령의 기대값 0 을 숫자 비교로 처리해
    "숫자를 못 읽음" 이 무더기로 난다.
    """
    last_segment = _last_pipeline_segment(rule.command)
    is_count = bool(
        WC_L.search(last_segment)
        or GREP_COUNT.search(last_segment)
        or PY_ONELINER.search(last_segment)
    )

    if is_count:
        return ("gte" if rule.wants_at_least else "eq"), "count"

    # "각 N" 은 파일마다 N 이라는 뜻이다. 목록을 내는 명령에서는 파일이 몇 개인지
    # 명령만 봐서 알 수 없으므로 기계 판정을 포기하고 모델 판정으로 넘긴다.
    if rule.expected and rule.expected.strip().startswith("각"):
        return "pending", "lines"

    target = rule.expected_int
    if target == 0:
        return "zero", "lines"
    return ("lines_gte" if rule.wants_at_least else "lines_eq"), "lines"


def _last_pipeline_segment(command: str) -> str:
    """따옴표 밖의 마지막 파이프 뒤 구간을 돌려준다.

    그냥 `command.split("|")[-1]` 을 쓰면 따옴표 안의 정규식 대체 기호까지
    파이프로 오인한다. `grep -c "a\\|b" file` 이 잘려서 grep 을 못 알아보고
    개수 명령을 목록 명령으로 잘못 판정한다.
    """
    masked = mask_quoted(command)
    if masked is None:
        return command
    index = masked.rfind("|")
    return command if index == -1 else command[index + 1:]


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

    # 두 곳을 본다. fixture 가 스킬 옆에 있기도 하고 (skills/*/tests/),
    # 슬래시 커맨드로 잘못 등록되는 걸 피해 저장소 루트로 옮겨진 것도 있다
    # (tests/eval-fixtures/). 한쪽만 보면 조용히 빠진다 — 실제로 audit fixture
    # 11 룰이 이 이유로 수집 밖에 있었다 (2026-08-15 검증에서 실측).
    seen: set[Path] = set()
    for pattern in ("skills/*/tests/**/*.md", "tests/eval-fixtures/**/*.md"):
        for readme in sorted(repo_root.glob(pattern)):
            if readme in seen:
                continue
            seen.add(readme)
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
