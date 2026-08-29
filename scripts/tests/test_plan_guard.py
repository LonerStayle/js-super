"""Unit tests for scripts.plan_guard."""
from pathlib import Path

from scripts.plan_guard import (
    MAX_TASKS_PER_SUBDOC,
    SPLIT_THRESHOLD,
    check_plan,
    resolve_documents,
    verify_documents_byte_equal,
)


def _write(p: Path, content: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# resolve_documents — 문서 집합 해석 (단일 / 분할)
# ---------------------------------------------------------------------------

def test_resolve_documents_single(tmp_path):
    idx = _write(tmp_path / "plan.md", "# Plan\n### Task 1: a\n")
    docs = resolve_documents(idx)
    assert docs.is_split is False
    assert docs.sub_paths == []
    assert docs.all_paths == [idx]


def test_resolve_documents_split(tmp_path):
    idx = _write(tmp_path / "plan.md", "# Plan\n")
    sub = _write(tmp_path / "plan" / "tasks-01.md", "### Task 1: a\n")
    docs = resolve_documents(idx)
    assert docs.is_split is True
    assert docs.sub_paths == [sub]


def test_resolve_documents_ignores_non_matching_names(tmp_path):
    idx = _write(tmp_path / "plan.md", "# Plan\n")
    _write(tmp_path / "plan" / "notes.md", "some unrelated note\n")
    docs = resolve_documents(idx)
    assert docs.is_split is False
    assert docs.sub_paths == []


def test_plan_documents_all_paths_sorted(tmp_path):
    idx = _write(tmp_path / "plan.md", "# Plan\n")
    sub1 = _write(tmp_path / "plan" / "tasks-01.md", "### Task 1: a\n")
    sub2 = _write(tmp_path / "plan" / "tasks-02.md", "### Task 2: b\n")
    docs = resolve_documents(idx)
    assert docs.all_paths == [idx, sub1, sub2]


# ---------------------------------------------------------------------------
# G1 — 코드 블록 존재
# ---------------------------------------------------------------------------

def test_g1_modify_task_missing_code_pair(tmp_path):
    """코드 블록 없는 Modify task 가 G1 위반으로 잡힌다."""
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: fix bug
**Files:**
- Modify: `src/foo.py`

**검증**: 동작을 확인한다.
""")
    violations = check_plan(plan)
    g1 = [v for v in violations if v.code == "G1"]
    assert len(g1) == 1
    assert g1[0].task_id == 1


def test_g1_create_task_missing_modified_block(tmp_path):
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: add file
**Files:**
- Create: `src/new.py`

**검증**: 파일이 생성된다.
""")
    violations = check_plan(plan)
    g1 = [v for v in violations if v.code == "G1"]
    assert len(g1) == 1
    assert g1[0].task_id == 1


def test_g1_modify_task_with_pair_passes(tmp_path):
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: fix bug
**Files:**
- Modify: `src/foo.py`

**원본** (`src/foo.py:1-2`):
```python
def f():
    pass
```
**수정 후**:
```python
def f():
    return 1
```
""")
    violations = check_plan(plan)
    assert [v for v in violations if v.code == "G1"] == []


# ---------------------------------------------------------------------------
# G2 — 축약 마커
# ---------------------------------------------------------------------------

def test_g2_elision_marker_detected(tmp_path):
    """축약 마커가 G2 로 잡힌다."""
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: refactor
**Files:**
- Modify: `src/foo.py`

**원본** (`src/foo.py:1-3`):
```python
def f():
    x = 1
    return x
```
**수정 후**:
```python
def f():
    # 생략
    return x
```
""")
    violations = check_plan(plan)
    g2 = [v for v in violations if v.code == "G2"]
    assert len(g2) == 1
    assert g2[0].task_id == 1
    assert "생략" in g2[0].reason


def test_g2_exempt_when_line_also_in_원본(tmp_path):
    """같은 task 의 `**원본**` 에 있던 동일 라인은 축약 마커처럼 보여도 면제된다."""
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: refactor
**Files:**
- Modify: `src/foo.py`

**원본** (`src/foo.py:1-3`):
```python
def f():
    # 생략 처리 안내
    return 1
```
**수정 후**:
```python
def f():
    # 생략 처리 안내
    return 2
```
""")
    violations = check_plan(plan)
    assert [v for v in violations if v.code == "G2"] == []


# ---------------------------------------------------------------------------
# G3 — 분할 강제 (10개 이상인데 단일 문서)
# ---------------------------------------------------------------------------

def test_g3_split_required_over_threshold(tmp_path):
    tasks = "\n".join(f"### Task {i}: t{i}\n" for i in range(1, SPLIT_THRESHOLD + 1))
    plan = _write(tmp_path / "plan.md", f"# Plan\n{tasks}")
    violations = check_plan(plan)
    g3 = [v for v in violations if v.code == "G3"]
    assert len(g3) == 1


def test_g3_under_threshold_no_violation(tmp_path):
    tasks = "\n".join(f"### Task {i}: t{i}\n" for i in range(1, SPLIT_THRESHOLD))
    plan = _write(tmp_path / "plan.md", f"# Plan\n{tasks}")
    violations = check_plan(plan)
    assert [v for v in violations if v.code == "G3"] == []


# ---------------------------------------------------------------------------
# G4 — 하위 문서당 task 상한
# ---------------------------------------------------------------------------

def test_g4_subdoc_task_count_exceeds_max(tmp_path):
    """하위 문서 4 task 가 G4 위반으로 잡힌다."""
    n = MAX_TASKS_PER_SUBDOC + 1
    index_tasks = "\n".join(
        f"### Task {i}: t{i}\n**상세**: plan/tasks-01.md\n" for i in range(1, n + 1)
    )
    idx = _write(tmp_path / "plan.md", f"# Plan\n{index_tasks}")
    sub_tasks = "\n".join(f"### Task {i}: t{i}\n" for i in range(1, n + 1))
    sub = _write(tmp_path / "plan" / "tasks-01.md", sub_tasks)

    violations = check_plan(idx)
    g4 = [v for v in violations if v.code == "G4"]
    assert len(g4) == 1
    assert g4[0].doc_path == sub
    assert str(n) in g4[0].reason


# ---------------------------------------------------------------------------
# G5 — 구조 무결성 (끊긴 링크 / 고아 문서 / 연번 / 필드 정합성)
# ---------------------------------------------------------------------------

def test_g5_broken_detail_link(tmp_path):
    idx = _write(tmp_path / "plan.md", """# Plan
### Task 1: a
**상세**: plan/tasks-99.md
""")
    _write(tmp_path / "plan" / "tasks-01.md", "### Task 1: a\n")
    violations = check_plan(idx)
    g5 = [v for v in violations if v.code == "G5"]
    assert any("broken" in v.reason and "상세" in v.reason for v in g5)


def test_g5_orphan_subdocument(tmp_path):
    idx = _write(tmp_path / "plan.md", """# Plan
### Task 1: a
**상세**: plan/tasks-01.md
""")
    _write(tmp_path / "plan" / "tasks-01.md", "### Task 1: a\n")
    orphan_sub = _write(tmp_path / "plan" / "tasks-02.md", "### Task 2: b\n")
    violations = check_plan(idx)
    g5 = [v for v in violations if v.code == "G5"]
    orphan = [v for v in g5 if "orphan" in v.reason]
    assert len(orphan) == 1
    assert orphan[0].doc_path == orphan_sub


def test_g5_task_ids_not_contiguous(tmp_path):
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: a
### Task 3: c
""")
    violations = check_plan(plan)
    g5 = [v for v in violations if v.code == "G5"]
    assert any("contiguous" in v.reason for v in g5)


def test_g5_field_mismatch_between_index_and_detail(tmp_path):
    idx = _write(tmp_path / "plan.md", """# Plan
### Task 1: fix
**Files:**
- Modify: `src/foo.py`
**상세**: plan/tasks-01.md
""")
    _write(tmp_path / "plan" / "tasks-01.md", """### Task 1: fix
**Files:**
- Modify: `src/bar.py`
""")
    violations = check_plan(idx)
    g5 = [v for v in violations if v.code == "G5"]
    assert any("Modify" in v.reason and "differs" in v.reason for v in g5)


# ---------------------------------------------------------------------------
# G6 — byte-equal, 문서 집합 전체 순회 (false-pass 회귀 고정)
# ---------------------------------------------------------------------------

def test_g6_byte_mismatch_detected_in_subdocument_via_index_entry(tmp_path):
    """하위 문서에만 있는 byte-mismatch 가 인덱스 경로로 진입해도 검출된다."""
    _write(tmp_path / "src" / "foo.py", "def hello():\n    return 'hi'\n")
    idx = _write(tmp_path / "plan.md", """# Plan
### Task 1: fix
**상세**: plan/tasks-01.md
""")
    _write(tmp_path / "plan" / "tasks-01.md", """### Task 1: fix
**원본** (`src/foo.py:1-2`):
```python
def hello():
    return 'WRONG'
```
**수정 후**:
```python
def hello():
    return 'hello'
```
""")
    mismatches = verify_documents_byte_equal(idx, tmp_path)
    assert len(mismatches) == 1
    assert mismatches[0].file_path.name == "foo.py"

    # regression pin: calling the byte-check directly on the index alone
    # (i.e. not resolving the split document set first) would false-pass,
    # because the index itself carries no **원본** block.
    from scripts.plan_byte_check import verify_plan_block_byte_equal
    assert verify_plan_block_byte_equal(idx, tmp_path) == []


def test_g6_byte_equal_pass_across_documents(tmp_path):
    _write(tmp_path / "src" / "foo.py", "def hello():\n    return 'hi'\n")
    idx = _write(tmp_path / "plan.md", """# Plan
### Task 1: fix
**상세**: plan/tasks-01.md
""")
    _write(tmp_path / "plan" / "tasks-01.md", """### Task 1: fix
**원본** (`src/foo.py:1-2`):
```python
def hello():
    return 'hi'
```
**수정 후**:
```python
def hello():
    return 'hello'
```
""")
    mismatches = verify_documents_byte_equal(idx, tmp_path)
    assert mismatches == []


# ---------------------------------------------------------------------------
# 코드 블록 안 예시(task 헤더 / Files 줄)에 오염되지 않는지
# ---------------------------------------------------------------------------

def test_fence_masking_prevents_example_pollution(tmp_path):
    """규약을 설명하는 계획서가 예시 task 헤더/Files 줄을 코드 블록에 실어도
    task 수와 필드가 그 예시로 오염되지 않는다."""
    plan = _write(tmp_path / "plan.md", """# Plan
### Task 1: real task
**Files:**
- Modify: `src/real.py`

Explanation with an example embedded in a code block:
```markdown
### Task 99: example task
**Files:**
- Create: `fake.py`
```

**원본** (`src/real.py:1-1`):
```python
x = 1
```
**수정 후**:
```python
x = 2
```
""")
    violations = check_plan(plan)
    # 예시 task 99 는 실제 task 로 세어지지 않는다 (task_id 로 노출되면 안 됨)
    assert all(v.task_id != 99 for v in violations)
    # 실제 task 는 1개뿐이므로 G3(분할 강제)는 절대 발화하지 않는다
    assert [v for v in violations if v.code == "G3"] == []
    # 실제 task 의 Modify 는 원본/수정 후 쌍이 있으므로 G1 도 발화하지 않는다
    assert [v for v in violations if v.code == "G1"] == []
    # 예시 안의 `fake.py` 가 실제 Create 필드로 잡히지 않는다
    assert all("fake.py" not in v.reason for v in violations)


# ---------------------------------------------------------------------------
# 잘 구성된 분할 문서 — 위반 0건 (sanity)
# ---------------------------------------------------------------------------

def test_well_formed_split_plan_has_no_violations(tmp_path):
    _write(tmp_path / "src" / "foo.py", "x = 1\n")
    idx = _write(tmp_path / "plan.md", """# Plan
### Task 1: fix
**Files:**
- Modify: `src/foo.py`
**Model**: sonnet
**상세**: plan/tasks-01.md
""")
    _write(tmp_path / "plan" / "tasks-01.md", """### Task 1: fix
**Files:**
- Modify: `src/foo.py`
**Model**: sonnet

**원본** (`src/foo.py:1-1`):
```python
x = 1
```
**수정 후**:
```python
x = 2
```
""")
    violations = check_plan(idx)
    assert violations == []
