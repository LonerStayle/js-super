"""실행 전 검사 테스트.

검증하는 것: 같은 명령에 다른 기대값을 가진 쌍을 모순으로 잡아내는가.
모순이 있으면 실행 거부 신호를 내는가. 어느 케이스에도 안 걸린 대상을
미등록 목록으로 내는가.
"""

from pathlib import Path

from evals.runner.cases import Case
from evals.runner.coupling import Rule
from evals.runner.lint import LintReport, find_conflicts, normalize, run_lint

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_case(case_id: str, covers: list[str], layer=None, status="active") -> Case:
    meta = {
        "id": case_id,
        "title": case_id,
        "status": status,
        "layer": layer or ["C"],
        "covers": covers,
        "expect": [],
    }
    return Case(path=Path(f"{case_id}.md"), meta=meta, body="")


def test_같은_명령에_기대값이_다르면_모순으로_잡는다():
    rules = [
        Rule(source="CLAUDE.md:10", command='grep -c "x" a.md', expected="3"),
        Rule(source="H17/README.md:5", command='grep -c "x" a.md', expected="0"),
    ]
    conflicts = find_conflicts(rules, [])
    assert len(conflicts) == 1
    assert "CLAUDE.md:10" in conflicts[0]
    assert "H17/README.md:5" in conflicts[0]


def test_기대값이_같으면_모순이_아니다():
    rules = [
        Rule(source="a:1", command='grep -c "x" a.md', expected="3"),
        Rule(source="b:2", command='grep -c "x" a.md', expected="3"),
    ]
    assert find_conflicts(rules, []) == []


def test_공백_차이는_같은_명령으로_본다():
    rules = [
        Rule(source="a:1", command='grep  -c   "x"   a.md', expected="3"),
        Rule(source="b:2", command='grep -c "x" a.md', expected="0"),
    ]
    assert len(find_conflicts(rules, [])) == 1


def test_기대값이_없는_룰은_모순_판정에서_뺀다():
    rules = [
        Rule(source="a:1", command='grep -c "x" a.md', expected=None),
        Rule(source="b:2", command='grep -c "x" a.md', expected="3"),
    ]
    assert find_conflicts(rules, []) == []


def test_normalize_는_줄바꿈과_공백을_없앤다():
    assert normalize("a  b\n  c") == "a b c"


def test_모순이_있으면_실행_거부():
    report = LintReport(conflicts=["무언가 상충"])
    assert report.must_refuse is True


def test_케이스_형식_오류가_있어도_실행_거부():
    report = LintReport(case_errors=["형식 오류"])
    assert report.must_refuse is True


def test_미등록_목록만_있으면_실행은_계속():
    report = LintReport(uncovered=["skills/x/SKILL.md"])
    assert report.must_refuse is False


def test_실제_저장소에서_돌아간다():
    from evals.runner.coupling import collect_rules

    rules = collect_rules(REPO_ROOT)
    cases = [make_case("self/x", ["evals/**"])]
    report = run_lint(REPO_ROOT, rules, cases, [])
    assert isinstance(report, LintReport)
    # 케이스가 하나뿐이므로 미등록이 대량으로 나오는 게 정상이다
    assert len(report.uncovered) > 10
    assert all(isinstance(item, str) for item in report.uncovered)


def test_covers_에_걸린_파일은_미등록에서_빠진다():
    from evals.runner.lint import find_uncovered

    cases = [make_case("all", ["skills/*/SKILL.md", "commands/*.md",
                               "scripts/*.py", "agents/*.md", "hooks/*"])]
    uncovered = find_uncovered(REPO_ROOT, cases)
    assert not any(item.endswith("/SKILL.md") for item in uncovered)


def test_낡은_케이스는_커버리지로_안_친다():
    from evals.runner.lint import find_uncovered

    stale = [make_case("old", ["skills/*/SKILL.md"], status="stale")]
    uncovered = find_uncovered(REPO_ROOT, stale)
    assert any(item.endswith("/SKILL.md") for item in uncovered)
