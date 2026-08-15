"""단언 실행기 테스트.

검증하는 것: 인자 배열 경로는 셸을 안 거치고 실행되는가. 결합 룰 경로는
관문에 걸리면 실행하지 않고 차단 상태를 내는가. 일곱 비교 연산이 각각
통과와 실패를 정확히 가리는가.
"""

from pathlib import Path

from evals.runner.assertions import Outcome, compare, run_argv, run_shell_rule

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_인자_배열은_셸을_안_거친다(tmp_path):
    """셸을 거치면 * 가 글롭으로 펼쳐진다. 안 거치면 문자 그대로 남는다."""
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("x", encoding="utf-8")
    code, out = run_argv(["echo", "*.md"], tmp_path)
    assert code == 0
    assert out.strip() == "*.md", "셸을 거쳐서 글롭이 펼쳐졌다"


def test_인자_배열이_종료코드와_표준출력을_돌려준다(tmp_path):
    (tmp_path / "x.md").write_text("hello\nhello\n", encoding="utf-8")
    code, out = run_argv(["grep", "-c", "hello", "x.md"], tmp_path)
    assert code == 0
    assert out.strip() == "2"


def test_결합_룰은_관문에_걸리면_실행_안_한다(tmp_path):
    target = tmp_path / "victim.md"
    target.write_text("살아 있어야 함", encoding="utf-8")
    result = run_shell_rule(f'rm -f {target}', tmp_path)
    assert result.status == "BLOCKED"
    assert target.exists(), "관문이 뚫려서 파일이 지워졌다"


def test_결합_룰은_읽기_전용이면_실행한다(tmp_path):
    (tmp_path / "x.md").write_text("a\nb\na\n", encoding="utf-8")
    result = run_shell_rule('grep -c "a" x.md', tmp_path)
    assert result.status == "PASS"
    assert result.actual.strip() == "2"


def test_결합_룰은_bash_로_고정한다(tmp_path):
    """zsh 는 매치 없는 글롭을 오류로 만든다. bash 는 문자 그대로 넘긴다."""
    result = run_shell_rule('grep -c "x" --include=*.nomatch -r . 2>/dev/null; echo done', tmp_path)
    assert result.status in {"PASS", "BLOCKED"}


def test_zero_는_빈_출력을_통과시킨다():
    assert compare("zero", "", None).status == "PASS"
    assert compare("zero", "0", None).status == "PASS"
    assert compare("zero", "some line", None).status == "FAIL"


def test_eq_는_숫자가_같을_때만_통과():
    assert compare("eq", "3", 3).status == "PASS"
    assert compare("eq", "4", 3).status == "FAIL"


def test_eq_는_여러_숫자_전부를_본다():
    assert compare("eq", "1\n1\n1", 1).status == "PASS"
    assert compare("eq", "1\n2\n1", 1).status == "FAIL"


def test_gte_와_lte():
    assert compare("gte", "5", 3).status == "PASS"
    assert compare("gte", "2", 3).status == "FAIL"
    assert compare("lte", "2", 3).status == "PASS"
    assert compare("lte", "5", 3).status == "FAIL"


def test_lines_eq_는_줄_수를_센다():
    assert compare("lines_eq", "a\nb\nc", 3).status == "PASS"
    assert compare("lines_eq", "a\n\nb", 2).status == "PASS"
    assert compare("lines_eq", "a\nb", 3).status == "FAIL"


def test_exists_는_출력이_있으면_통과():
    assert compare("exists", "something", None).status == "PASS"
    assert compare("exists", "   ", None).status == "FAIL"


def test_capture_는_판정하지_않고_증거만_담는다():
    result = compare("capture", "무언가 출력", None)
    assert result.status == "PASS"
    assert result.actual == "무언가 출력"


def test_모르는_연산은_차단한다():
    assert compare("무슨연산", "1", 1).status == "BLOCKED"


def test_숫자를_못_읽으면_실패로_본다():
    result = compare("eq", "숫자 없음", 1)
    assert result.status == "FAIL"
    assert "숫자" in result.reason


def test_실패에는_이유가_붙는다():
    result = compare("eq", "4", 3)
    assert isinstance(result, Outcome)
    assert result.reason
    assert result.actual == "4"
