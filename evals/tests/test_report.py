"""보고 테스트.

검증하는 것: 상태별 건수를 내는가. 미선택·연기·차단·보류 네 상태가
통과 집계에서 빠지고 각각 별도 목록으로 표시되는가.
"""

from evals.runner.baseline import Classified
from evals.runner.lint import LintReport
from evals.runner.report import passing_count, render


def rows():
    return [
        Classified("a", "PASS", "PASS", "confirmed"),
        Classified("b", "REGRESSION", "FAIL", "confirmed", "새로 깨짐 상세"),
        Classified("c", "KNOWN", "FAIL", "regression-open"),
        Classified("d", "BLOCKED", "BLOCKED", None, "자리표시자"),
        Classified("e", "NOT-SELECTED", "NOT-SELECTED", None),
        Classified("f", "NEW", "PASS", None),
    ]


def test_상태별_건수가_나온다():
    text = render(rows(), LintReport(), 1.2)
    assert "통과" in text
    assert "새로 깨짐" in text
    assert "1.2초" in text


def test_통과_집계에_차단_연기_보류_미선택이_안_들어간다():
    assert passing_count(rows()) == 2  # PASS + KNOWN


def test_새로_깨진_항목은_목록으로_따로_뜬다():
    text = render(rows(), LintReport(), 0.5)
    assert "새로 깨짐 상세" in text
    assert "b" in text


def test_차단_항목도_목록으로_뜬다():
    text = render(rows(), LintReport(), 0.5)
    assert "자리표시자" in text


def test_모순은_실행_거부_문구와_함께_뜬다():
    text = render([], LintReport(conflicts=["무언가 상충"]), 0.1)
    assert "실행 거부" in text
    assert "무언가 상충" in text


def test_미등록_목록은_20건까지만_보이고_나머지는_수로_알린다():
    lint = LintReport(uncovered=[f"skills/x{i}/SKILL.md" for i in range(35)])
    text = render([], lint, 0.1)
    assert "skills/x0/SKILL.md" in text
    assert "skills/x34/SKILL.md" not in text
    assert "15건" in text


def test_케이스_형식_오류가_보인다():
    text = render([], LintReport(case_errors=["bad.md: 필수 항목 누락"]), 0.1)
    assert "bad.md" in text


def test_게이트_결손이_보인다():
    text = render([], LintReport(gate_gaps=["skills/x/SKILL.md — 게이트 3회"]), 0.1)
    assert "게이트" in text


def test_아무것도_없으면_조용하다():
    text = render([], LintReport(), 0.1)
    assert "실행 거부" not in text
    assert "새로 깨짐" not in text
