"""기준선 대조.

baseline.json 은 verdict (그때 관측된 값) 와 label (사람의 판단) 을 나눠 담는다.
관측만 굳히면 지금 실패 중인 진짜 회귀가 정답으로 박제된다 (요구사항 결정 8).

소요 시간·비용·토큰은 담지 않는다. 같은 종류 호출이 1,703밀리초와
30,058밀리초로 갈릴 만큼 편차가 커서 회귀 판정에 못 쓴다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

# 통과로 집계되는 상태.
PASSING = {"PASS", "KNOWN", "FIXED"}

# 통과로도 실패로도 집계하지 않는 상태. 조용히 묻히면 안 되므로
# 보고서에 별도 목록으로 뜬다 (요구사항 수용 기준 5).
NOT_COUNTED = {"NOT-SELECTED", "DEFERRED", "BLOCKED", "PENDING"}

VALID_LABELS = {"confirmed", "regression-open", "stale", "blocked"}


@dataclass(frozen=True)
class Classified:
    case_id: str
    status: str
    verdict: str
    label: str | None
    detail: str = ""


def load_baseline(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "cases": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_baseline(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def classify(case_id: str, verdict: str, baseline: dict, detail: str = "") -> Classified:
    """이번 관측을 기준선과 대조해 상태를 정한다."""
    if verdict in NOT_COUNTED:
        return Classified(case_id, verdict, verdict, None, detail)

    record = baseline.get("cases", {}).get(case_id)
    if record is None:
        return Classified(case_id, "NEW", verdict, None, detail)

    label = record.get("label")
    was_passing = record.get("verdict") == "PASS"

    if verdict == "PASS":
        status = "PASS" if was_passing else "FIXED"
    elif label in {"regression-open", "blocked", "stale"}:
        status = "KNOWN"
    elif was_passing:
        status = "REGRESSION"
    else:
        status = "KNOWN" if label else "FAIL"

    return Classified(case_id, status, verdict, label, detail)


def passing_ids(rows: list[Classified]) -> list[str]:
    """통과로 집계되는 케이스 id. NOT_COUNTED 는 절대 포함하지 않는다."""
    return [
        row.case_id for row in rows
        if row.status in PASSING and row.status not in NOT_COUNTED
    ]


def summarize(rows: list[Classified]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def has_blocking_failure(rows: list[Classified]) -> bool:
    """새로 깨진 것이나 미분류가 있으면 실패로 끝낸다."""
    return any(row.status in {"REGRESSION", "FAIL", "NEW"} for row in rows)


def unclassified(rows: list[Classified]) -> list[Classified]:
    """사람이 아직 회귀인지 낡음인지 정하지 않은 항목."""
    return [row for row in rows if row.status in {"NEW", "FAIL", "PENDING"}]
