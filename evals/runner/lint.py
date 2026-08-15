"""실행 전 검사. 비용 0.

세 가지를 본다.
1. 같은 명령에 기대값이 다른 쌍 (있으면 실행 거부)
2. 어느 케이스의 covers 에도 안 걸린 대상 파일
3. 승인 게이트가 있는 스킬 중 절차 케이스가 없는 것

1번이 핵심이다. H17 fixture 와 CLAUDE.md 가 같은 명령에 0건과 3건을
기대하며 오래 공존해 왔는데 아무도 몰랐다. 같은 종류의 두 번째 충돌을
형식 차원에서 막는다. 러너가 어느 쪽도 임의로 고르지 않는다.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from evals.runner.cases import Case
from evals.runner.coupling import Rule

TARGET_PREFIXES = ("skills/", "commands/", "agents/", "hooks/", "scripts/")
GATE_PATTERN = re.compile(r"AskUserQuestion")


@dataclass
class LintReport:
    conflicts: list[str] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    gate_gaps: list[str] = field(default_factory=list)
    case_errors: list[str] = field(default_factory=list)

    @property
    def must_refuse(self) -> bool:
        """모순이나 케이스 형식 오류가 있으면 실행하지 않는다."""
        return bool(self.conflicts or self.case_errors)


def normalize(command: str) -> str:
    """공백과 줄바꿈 차이를 없앤 비교용 형태."""
    return " ".join(command.split())


def _numeric(expected: str) -> int | None:
    """기대값에서 숫자를 뽑는다. 없으면 None."""
    match = re.match(r"^\s*(?:각\s*)?(?:>=|<=|==)?\s*(\d+)", expected)
    return int(match.group(1)) if match else None


def find_conflicts(rules: list[Rule], cases: list[Case]) -> list[str]:
    """같은 명령인데 기대값이 다른 쌍을 찾는다.

    숫자 기대값끼리만 모순으로 본다. 자연어 기대값은 같은 뜻을 다르게
    적은 경우가 많고("0 (Anti-Pattern catch 라인만 허용)" 대 "0 (Anti-Patterns
    표 안의 catch 라인만 허용)"), 같은 명령을 서로 다른 상황에서 돌리는
    fixture 도 있어 기계적으로 판정하면 오탐이 난다.
    """
    seen: dict[str, tuple[int, str]] = {}
    conflicts: list[str] = []

    def register(command: str, expected: str | None, source: str) -> None:
        if expected is None or not command.strip():
            return
        value = _numeric(expected)
        if value is None:
            return
        key = normalize(command)
        if key in seen and seen[key][0] != value:
            previous_value, previous_source = seen[key]
            conflicts.append(
                "같은 명령에 기대값이 다름\n"
                f"      명령: {key[:110]}\n"
                f"      {previous_source} → {previous_value}\n"
                f"      {source} → {value}"
            )
            return
        seen.setdefault(key, (value, source))

    for rule in rules:
        register(rule.command, rule.expected, rule.source)

    for case in cases:
        for item in case.expect:
            if item.get("kind") != "shell":
                continue
            argv = item.get("argv") or []
            command = argv[-1] if argv else ""
            value = item.get("value")
            register(command, None if value is None else str(value), case.id)

    return conflicts


def find_uncovered(repo_root: Path, cases: list[Case]) -> list[str]:
    """어느 케이스의 covers 에도 안 걸린 대상 파일.

    낡음으로 표시된 케이스는 커버리지로 치지 않는다. 낡은 케이스가
    커버한다고 계산하면 실제로는 아무도 안 보는 대상이 가려진다.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=str(repo_root),
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()

    targets = [
        path for path in tracked
        if path.startswith(TARGET_PREFIXES) and "/tests/" not in path
    ]
    globs = [
        pattern
        for case in cases if case.status == "active"
        for pattern in case.covers
    ]

    return [
        path for path in targets
        if not any(fnmatch.fnmatch(path, pattern) for pattern in globs)
    ]


def find_gate_gaps(repo_root: Path, cases: list[Case]) -> list[str]:
    """승인 게이트를 언급하는 스킬 중 절차 케이스가 없는 것.

    게이트 개수를 사람이 세지 않는다. 여기서 결손 목록을 내고,
    절대 수치를 assert 로 박지 않는다 (설계서 D11).
    """
    covered = {
        pattern
        for case in cases
        if "B" in case.layer and case.status == "active"
        for pattern in case.covers
    }
    gaps: list[str] = []
    for skill in sorted((repo_root / "skills").glob("*/SKILL.md")):
        body = skill.read_text(encoding="utf-8")
        hits = len(GATE_PATTERN.findall(body))
        if hits == 0:
            continue
        relative = str(skill.relative_to(repo_root))
        if not any(fnmatch.fnmatch(relative, pattern) for pattern in covered):
            gaps.append(f"{relative} — 게이트 언급 {hits}회, 절차 케이스 없음")
    return gaps


def run_lint(
    repo_root: Path,
    rules: list[Rule],
    cases: list[Case],
    case_errors: list[str],
) -> LintReport:
    return LintReport(
        conflicts=find_conflicts(rules, cases),
        uncovered=find_uncovered(repo_root, cases),
        gate_gaps=find_gate_gaps(repo_root, cases),
        case_errors=list(case_errors),
    )
