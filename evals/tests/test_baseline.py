"""기준선 대조 테스트.

검증하는 것: 기준선에 통과로 적힌 항목이 이번에 실패하면 REGRESSION,
회귀로 적힌 항목이 이번에도 실패하면 KNOWN, 통과하면 FIXED,
기준선에 없으면 NEW 로 분류하는가. 라벨 없는 항목이 통과 집계에
들어가지 않는가.
"""

import json
from pathlib import Path

from evals.runner.baseline import (
    Classified,
    classify,
    has_blocking_failure,
    load_baseline,
    passing_ids,
    save_baseline,
    summarize,
)


def base(**cases) -> dict:
    return {"schema_version": 1, "cases": cases}


def test_기준선에_없으면_NEW():
    row = classify("x", "PASS", base())
    assert row.status == "NEW"


def test_통과하던_게_실패하면_REGRESSION():
    row = classify("x", "FAIL", base(x={"verdict": "PASS", "label": "confirmed"}))
    assert row.status == "REGRESSION"


def test_회귀로_라벨된_게_또_실패하면_KNOWN():
    row = classify("x", "FAIL", base(x={"verdict": "FAIL", "label": "regression-open"}))
    assert row.status == "KNOWN"


def test_실패하던_게_통과하면_FIXED():
    row = classify("x", "PASS", base(x={"verdict": "FAIL", "label": "regression-open"}))
    assert row.status == "FIXED"


def test_통과하던_게_또_통과하면_PASS():
    row = classify("x", "PASS", base(x={"verdict": "PASS", "label": "confirmed"}))
    assert row.status == "PASS"


def test_라벨_없이_실패하던_건_FAIL():
    row = classify("x", "FAIL", base(x={"verdict": "FAIL"}))
    assert row.status == "FAIL"


def test_차단_연기_보류_미선택은_그대로_남는다():
    for state in ("BLOCKED", "DEFERRED", "PENDING", "NOT-SELECTED"):
        row = classify("x", state, base(x={"verdict": "PASS", "label": "confirmed"}))
        assert row.status == state, f"{state} 가 {row.status} 로 바뀜"


def test_차단_연기_보류_미선택은_통과_집계에_안_들어간다():
    rows = [
        Classified("a", "BLOCKED", "BLOCKED", None),
        Classified("b", "DEFERRED", "DEFERRED", None),
        Classified("c", "PENDING", "PENDING", None),
        Classified("d", "NOT-SELECTED", "NOT-SELECTED", None),
        Classified("e", "PASS", "PASS", "confirmed"),
    ]
    assert passing_ids(rows) == ["e"]


def test_NEW_는_통과_집계에_안_들어간다():
    rows = [Classified("a", "NEW", "PASS", None)]
    assert passing_ids(rows) == []


def test_새로_깨진_게_있으면_실패로_끝낸다():
    assert has_blocking_failure([Classified("a", "REGRESSION", "FAIL", "confirmed")])
    assert has_blocking_failure([Classified("a", "FAIL", "FAIL", None)])
    assert has_blocking_failure([Classified("a", "NEW", "PASS", None)])


def test_알려진_실패만_있으면_실패로_안_끝낸다():
    rows = [
        Classified("a", "KNOWN", "FAIL", "regression-open"),
        Classified("b", "PASS", "PASS", "confirmed"),
    ]
    assert has_blocking_failure(rows) is False


def test_요약은_상태별_건수를_센다():
    rows = [
        Classified("a", "PASS", "PASS", "confirmed"),
        Classified("b", "PASS", "PASS", "confirmed"),
        Classified("c", "FAIL", "FAIL", None),
    ]
    assert summarize(rows) == {"PASS": 2, "FAIL": 1}


def test_기준선_파일이_없으면_빈_기준선(tmp_path):
    data = load_baseline(tmp_path / "없음.json")
    assert data["cases"] == {}
    assert data["schema_version"] == 1


def test_저장하고_다시_읽으면_같다(tmp_path):
    path = tmp_path / "sub" / "baseline.json"
    data = base(x={"verdict": "PASS", "label": "confirmed", "reason": "한글 이유"})
    save_baseline(path, data)
    assert json.loads(path.read_text(encoding="utf-8")) == data
    assert "한글 이유" in path.read_text(encoding="utf-8"), "한글이 이스케이프됨"
