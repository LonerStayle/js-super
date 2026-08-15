"""케이스 로더 테스트.

검증하는 것: 앞머리가 있는 마크다운에서 필수 6개 항목을 뽑아내는가.
필수 항목이 빠지면 파일 경로와 빠진 항목 이름을 담은 오류를 내는가.
앞머리가 아예 없는 파일은 케이스가 아니라고 판단하고 건너뛰는가.
"""

from pathlib import Path

import pytest

from evals.runner.cases import Case, CaseError, load_all, load_case

MINIMAL = """---
id: owner/local-id
title: 제목
status: active
layer: [C]
covers:
  - skills/**
expect:
  - {kind: shell, argv: ["echo", "1"], op: eq, value: 1}
---

본문은 원문 그대로 남는다.
"""


def write(tmp_path: Path, text: str, name: str = "case.md") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_필수_6개를_뽑아낸다(tmp_path):
    case = load_case(write(tmp_path, MINIMAL))
    assert isinstance(case, Case)
    assert case.id == "owner/local-id"
    assert case.title == "제목"
    assert case.status == "active"
    assert case.layer == ["C"]
    assert case.covers == ["skills/**"]
    assert len(case.expect) == 1


def test_본문을_원문_그대로_보존한다(tmp_path):
    case = load_case(write(tmp_path, MINIMAL))
    assert "본문은 원문 그대로 남는다." in case.body


def test_앞머리가_없으면_케이스가_아니다(tmp_path):
    path = write(tmp_path, "# 그냥 문서\n\n내용\n")
    assert load_case(path) is None


def test_필수_항목이_빠지면_경로와_항목명을_알려준다(tmp_path):
    path = write(tmp_path, """---
id: owner/x
title: 제목
---

본문
""")
    with pytest.raises(CaseError) as excinfo:
        load_case(path)
    message = str(excinfo.value)
    assert "case.md" in message
    assert "status" in message and "layer" in message


def test_앞머리가_닫히지_않으면_오류(tmp_path):
    path = write(tmp_path, "---\nid: x\ntitle: y\n")
    with pytest.raises(CaseError):
        load_case(path)


def test_모르는_status_는_오류(tmp_path):
    path = write(tmp_path, MINIMAL.replace("status: active", "status: 이상함"))
    with pytest.raises(CaseError) as excinfo:
        load_case(path)
    assert "status" in str(excinfo.value)


def test_모르는_layer_는_오류(tmp_path):
    path = write(tmp_path, MINIMAL.replace("layer: [C]", "layer: [Z]"))
    with pytest.raises(CaseError) as excinfo:
        load_case(path)
    assert "layer" in str(excinfo.value)


def test_run_이_없으면_비용_0_케이스다(tmp_path):
    case = load_case(write(tmp_path, MINIMAL))
    assert case.needs_claude is False


def test_run_이_있으면_실행_케이스다(tmp_path):
    case = load_case(write(tmp_path, MINIMAL.replace("expect:", "run: '무언가 프롬프트'\nexpect:")))
    assert case.needs_claude is True


def test_danger_기본값은_없음(tmp_path):
    case = load_case(write(tmp_path, MINIMAL))
    assert case.danger == "-"


def test_load_all_은_오류를_모아서_돌려준다(tmp_path):
    write(tmp_path, MINIMAL, "good.md")
    write(tmp_path, "---\nid: x\n---\n\n본문\n", "bad.md")
    write(tmp_path, "# 앞머리 없음\n", "plain.md")
    cases, errors = load_all(tmp_path)
    assert len(cases) == 1
    assert len(errors) == 1
    assert "bad.md" in errors[0]


def test_실제_저장소의_케이스가_전부_읽힌다():
    repo_root = Path(__file__).resolve().parents[2]
    cases_dir = repo_root / "evals" / "cases"
    if not cases_dir.exists():
        pytest.skip("cases 디렉토리 없음")
    cases, errors = load_all(cases_dir)
    assert errors == [], f"케이스 형식 오류: {errors}"
    assert len(cases) >= 1
