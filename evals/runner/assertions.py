"""단언을 평가한다.

두 경로가 있다 (설계서 D5).

- run_argv: 우리가 케이스에 직접 쓰는 단언. 인자 배열만 받고 셸을 안 거친다.
  케이스 약 150개 중 오타 하나가 원본 저장소를 파괴하는 경로를 없앤다.
- run_shell_rule: CLAUDE.md 에서 가져온 결합 룰. 파이프라인이라 셸이 필요하다.
  대신 읽기 전용 관문을 먼저 통과해야 한다.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from evals.runner.guard import check_read_only

TIMEOUT_S = 30


@dataclass(frozen=True)
class Outcome:
    status: str          # PASS | FAIL | BLOCKED
    actual: str = ""
    reason: str = ""


def run_argv(argv: list[str], cwd: Path) -> tuple[int, str]:
    """인자 배열을 셸 없이 실행한다."""
    proc = subprocess.run(
        argv, cwd=str(cwd), capture_output=True, text=True,
        timeout=TIMEOUT_S, shell=False,
    )
    return proc.returncode, proc.stdout


def run_shell_rule(command: str, cwd: Path) -> Outcome:
    """CLAUDE.md 결합 룰을 관문 통과 후 bash 로 실행한다.

    셸을 bash 로 고정한다. zsh 는 매치 없는 글롭을 오류로 만들어
    같은 룰이 환경마다 다르게 동작한다. 실제로 이 저장소 작업 중에
    zsh 가 `--include=*.md` 를 글롭으로 먹어 검사가 죽은 사례가 두 번 있었다.
    """
    verdict = check_read_only(command)
    if not verdict.allowed:
        return Outcome("BLOCKED", reason=verdict.reason)
    try:
        proc = subprocess.run(
            ["bash", "-c", command], cwd=str(cwd), capture_output=True,
            text=True, timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return Outcome("BLOCKED", reason=f"{TIMEOUT_S}초 초과")
    return Outcome("PASS", actual=proc.stdout)


def extract_counts(text: str) -> list[int]:
    """개수 출력을 숫자 목록으로 읽는다.

    `grep -c` 는 파일이 하나면 `3`, 여럿이면 `경로:3` 형식으로 낸다.
    `wc -l` 은 그냥 숫자다. 두 형식을 모두 받는다.
    """
    numbers: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        tail = line.rsplit(":", 1)[-1].strip()
        if tail.lstrip("-").isdigit():
            numbers.append(int(tail))
            continue
        for token in line.split():
            if token.lstrip("-").isdigit():
                numbers.append(int(token))
    return numbers


def _nonempty_lines(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def compare(op: str, actual: str, expected) -> Outcome:
    """관측값과 기대값을 비교한다."""
    text = actual.strip()

    if op == "zero":
        ok = text == "" or set(text.split()) <= {"0"}
        return _verdict(ok, text, "출력이 비어 있어야 함")
    if op == "exists":
        return _verdict(bool(text), text, "출력이 있어야 함")
    if op == "capture":
        return Outcome("PASS", actual=text)
    if op == "lines_eq":
        count = _nonempty_lines(actual)
        return _verdict(count == int(expected), str(count), f"{expected} 줄이어야 함")
    if op == "lines_gte":
        count = _nonempty_lines(actual)
        return _verdict(count >= int(expected), str(count), f"{expected} 줄 이상이어야 함")

    if op not in {"eq", "gte", "lte"}:
        return Outcome("BLOCKED", actual=text, reason=f"모르는 연산: {op}")

    numbers = extract_counts(text)
    if not numbers:
        return Outcome("FAIL", actual=text, reason="숫자를 못 읽음")

    target = int(expected)
    if op == "eq":
        return _verdict(all(n == target for n in numbers), text, f"{target} 이어야 함")
    if op == "gte":
        return _verdict(all(n >= target for n in numbers), text, f"{target} 이상이어야 함")
    return _verdict(all(n <= target for n in numbers), text, f"{target} 이하여야 함")


def _verdict(ok: bool, actual: str, want: str) -> Outcome:
    if ok:
        return Outcome("PASS", actual=actual)
    return Outcome("FAIL", actual=actual, reason=want)
