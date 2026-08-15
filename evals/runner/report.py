"""사람이 읽는 보고서를 만든다.

건너뛴 항목을 조용히 통과로 집계하지 않는 것이 이 모듈의 존재 이유다
(요구사항 수용 기준 5). 무엇이 돌았고 무엇이 안 돌았는지가 매 실행마다
보여야 한다.
"""

from __future__ import annotations

from evals.runner.baseline import NOT_COUNTED, PASSING, Classified
from evals.runner.lint import LintReport

ORDER = [
    "REGRESSION", "FAIL", "NEW", "KNOWN", "FIXED", "PASS",
    "NOT-SELECTED", "DEFERRED", "BLOCKED", "PENDING",
]

LABEL = {
    "REGRESSION": "새로 깨짐",
    "FAIL": "실패",
    "NEW": "신규 (미분류)",
    "KNOWN": "이미 알려진 실패",
    "FIXED": "고쳐짐",
    "PASS": "통과",
    "NOT-SELECTED": "이번에 선택 안 됨",
    "DEFERRED": "예산 초과로 미룸",
    "BLOCKED": "실행 못 함",
    "PENDING": "판정 대기",
}

LIST_STATES = ("REGRESSION", "FAIL", "NEW", "BLOCKED", "PENDING")
UNCOVERED_SHOWN = 20


def passing_count(rows: list[Classified]) -> int:
    """통과로 집계되는 수. NOT_COUNTED 는 절대 포함하지 않는다."""
    return sum(
        1 for row in rows
        if row.status in PASSING and row.status not in NOT_COUNTED
    )


def render(rows: list[Classified], lint: LintReport, elapsed_s: float) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1

    lines = ["", f"검증 결과 — {len(rows)}건, {elapsed_s:.1f}초", ""]
    for status in ORDER:
        if status in counts:
            lines.append(f"  {LABEL[status]:<16} {counts[status]:>4}")
    lines.append("")

    for status in LIST_STATES:
        listed = [row for row in rows if row.status == status]
        if not listed:
            continue
        lines.append(f"[{LABEL[status]}]")
        for row in listed[:UNCOVERED_SHOWN]:
            suffix = f" — {row.detail}" if row.detail else ""
            lines.append(f"  {row.case_id}{suffix}")
        if len(listed) > UNCOVERED_SHOWN:
            lines.append(f"  … 외 {len(listed) - UNCOVERED_SHOWN}건")
        lines.append("")

    if lint.case_errors:
        lines.append("[케이스 형식 오류]")
        lines.extend(f"  {item}" for item in lint.case_errors)
        lines.append("")

    if lint.conflicts:
        lines.append("[상충하는 기대값 — 실행 거부]")
        lines.extend(f"  {item}" for item in lint.conflicts)
        lines.append("")

    if lint.uncovered:
        lines.append(f"[케이스에 안 걸린 대상 {len(lint.uncovered)}건]")
        lines.extend(f"  {item}" for item in lint.uncovered[:UNCOVERED_SHOWN])
        if len(lint.uncovered) > UNCOVERED_SHOWN:
            lines.append(f"  … 외 {len(lint.uncovered) - UNCOVERED_SHOWN}건")
        lines.append("")

    if lint.gate_gaps:
        lines.append(f"[승인 게이트 케이스 결손 {len(lint.gate_gaps)}건]")
        lines.extend(f"  {item}" for item in lint.gate_gaps[:UNCOVERED_SHOWN])
        if len(lint.gate_gaps) > UNCOVERED_SHOWN:
            lines.append(f"  … 외 {len(lint.gate_gaps) - UNCOVERED_SHOWN}건")
        lines.append("")

    return "\n".join(lines)
