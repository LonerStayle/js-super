"""Unit tests for scripts.preflight (v1.1.14)."""
from pathlib import Path

from scripts.preflight import (
    code_pretty_check,
    execute_plan_mode_check,
    subagent_task_entry_check,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_code_pretty_check_only_implementation_plan(tmp_path):
    req = tmp_path / "foo-requirements.md"
    plan = tmp_path / "foo-implementation-plan.md"
    _write(req, "# x\n## 변경이력\n")
    _write(plan, "# x\n**수정 후**:\n```py\npass\n```\n## 변경이력\n")
    assert code_pretty_check(req).ok is False
    assert code_pretty_check(plan).ok is True


def test_code_pretty_check_needs_modified_blocks(tmp_path):
    """수정 후 코드 블록이 하나도 없으면 prettify 할 것이 없다."""
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "# 문서만 고치는 계획\n## Task 1\n**검증**: 문구가 바뀐다.\n## 변경이력\n")
    assert code_pretty_check(plan).ok is False


def test_execute_plan_mode_check_per_task(tmp_path):
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "---\ncommit_policy: per-task\n---\n# x\n## 변경이력\n")
    result = execute_plan_mode_check(plan)
    assert result.ok is True


def test_execute_plan_mode_check_missing_frontmatter(tmp_path):
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "# x\n## 변경이력\n")
    result = execute_plan_mode_check(plan)
    # default per-task assumed → ok
    assert result.ok is True


def test_subagent_task_entry_check_no_plan(tmp_path):
    result = subagent_task_entry_check(tmp_path / "missing-implementation-plan.md")
    assert result.ok is False


def test_subagent_task_entry_check_commit_policy_single_rejected(tmp_path):
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "---\ncommit_policy: single\n---\n# x\n## 변경이력\n")
    result = subagent_task_entry_check(plan)
    assert result.ok is False
    assert "per-task" in result.reason


def test_preflight_result_has_human_reason_field():
    from scripts.preflight import PreflightResult
    r = PreflightResult(False, "file_not_found")
    assert hasattr(r, "human_reason")
    assert r.human_reason == ""  # default empty string


def test_code_pretty_check_human_reason_for_wrong_filename(tmp_path):
    from scripts.preflight import code_pretty_check
    p = tmp_path / "foo-requirements.md"
    p.write_text("# title\n## 변경이력\n", encoding="utf-8")
    r = code_pretty_check(p)
    assert r.ok is False
    assert "implementation-plan" in r.human_reason


def test_code_pretty_check_human_reason_for_no_modified_blocks(tmp_path):
    from scripts.preflight import code_pretty_check
    p = tmp_path / "x-implementation-plan.md"
    p.write_text("# title\n## 변경이력\n", encoding="utf-8")
    r = code_pretty_check(p)
    assert r.ok is False
    assert "수정 후" in r.human_reason


def test_execute_plan_mode_check_human_reason_for_missing_plan():
    from pathlib import Path
    from scripts.preflight import execute_plan_mode_check
    r = execute_plan_mode_check(Path("/tmp/__nonexistent__-implementation-plan.md"))
    assert r.ok is False
    assert "구현계획서를 찾을 수 없습니다" in r.human_reason


def test_subagent_entry_check_human_reason_for_wrong_policy(tmp_path):
    from scripts.preflight import subagent_task_entry_check
    p = tmp_path / "x-implementation-plan.md"
    p.write_text("---\ncommit_policy: single\n---\n# title\n", encoding="utf-8")
    r = subagent_task_entry_check(p)
    assert r.ok is False
    assert "per-task" in r.human_reason


def test_changelog_in_code_block_not_matched(tmp_path):
    """Plan 본문 안 ```markdown ... ## 변경이력 ... ``` literal 매치 안 됨.

    Bug context (v1.1.16): docs-pretty / executing-plans pre-flight 가
    plan 본문의 markdown code block 안 리터럴 `## 변경이력` 을 footer
    entry 로 잘못 판정. fix: rsplit 으로 마지막 occurrence 만 검사.
    """
    from scripts.preflight import _has_changelog_entries
    text = '''
# Plan

## 1. Tasks

### Task 1: example

```markdown
## 변경이력

### [날짜] [요구사항-수정]
- 본문 예시
```

## 변경이력

<!-- empty footer -->
'''
    assert _has_changelog_entries(text) is False


def test_real_changelog_entry_still_detected(tmp_path):
    """진짜 footer entry 는 여전히 감지."""
    from scripts.preflight import _has_changelog_entries
    text = '''
# Plan

## 변경이력

### [2026-05-10 12:00] [요구사항-수정]
- **id**: CH-20260510-001
'''
    assert _has_changelog_entries(text) is True


def test_feature_depth_marker_2(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 2\ndepth_reason: 사용자 선택\n---\n# x\n## 변경이력\n")
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path) == 2


def test_feature_depth_no_frontmatter(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "# x\n## 변경이력\n")
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path) == 3


def test_feature_depth_promoted_3(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 3\ndepth_reason: 승격\n---\n# x\n## 변경이력\n")
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path) == 3


def test_feature_depth_missing_dir(tmp_path):
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path / "nope") == 3


def test_execute_plan_mode_check_depth2_hint(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 2\n---\n# x\n## 변경이력\n")
    result = execute_plan_mode_check(tmp_path / "foo-implementation-plan.md")
    assert result.ok is False
    assert "승격" in result.human_reason


def test_subagent_task_entry_check_depth2_hint(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 2\n---\n# x\n## 변경이력\n")
    result = subagent_task_entry_check(tmp_path / "foo-implementation-plan.md")
    assert result.ok is False
    assert "승격" in result.human_reason


def test_code_pretty_check_split_plan_modified_block_in_subdoc(tmp_path):
    """분할 구조 — 인덱스에는 **수정 후** 가 없고 하위 문서에만 있으면 통과해야 한다."""
    idx = tmp_path / "foo-implementation-plan.md"
    _write(idx, "# x\n### Task 1: a\n**상세**: plan/tasks-01.md\n## 변경이력\n")
    _write(tmp_path / "plan" / "tasks-01.md", "### Task 1: a\n**수정 후**:\n```py\npass\n```\n")
    result = code_pretty_check(idx)
    assert result.ok is True


def test_code_pretty_check_split_plan_no_modified_block_anywhere(tmp_path):
    """분할 구조 — 인덱스와 하위 문서 어디에도 **수정 후** 가 없으면 기존처럼 실패한다."""
    idx = tmp_path / "foo-implementation-plan.md"
    _write(idx, "# x\n### Task 1: a\n**상세**: plan/tasks-01.md\n## 변경이력\n")
    _write(tmp_path / "plan" / "tasks-01.md", "### Task 1: a\n**검증**: 문구만 바뀐다.\n")
    result = code_pretty_check(idx)
    assert result.ok is False
    assert "수정 후" in result.reason


def test_code_pretty_check_single_doc_unaffected(tmp_path):
    """plan/ 하위 폴더가 없는 단일 문서 계획서는 기존과 동일하게 인덱스 본문만으로 판정한다."""
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "# x\n**수정 후**:\n```py\npass\n```\n## 변경이력\n")
    assert code_pretty_check(plan).ok is True
