---
commit_policy: per-task
---

# 구현계획서: 구현계획서 코드 강제 + 위키형 분할

상위 문서: `구현계획서-코드강제-분할-requirements.md` (FR-1~FR-8) / `구현계획서-코드강제-분할-tech-design.md` (§1~§7)

> **이 계획서 자체는 단일 문서다.** task 가 12개라 새 규약(10개 이상 분할)의 적용 대상이지만, 분할 구조를 읽는 도구가 아직 이 계획서를 실행하는 시점에 존재하지 않는다. 새 규약은 이 피처가 머지된 뒤 작성되는 계획서부터 적용된다.

## 1. 단계별 작업

### Task 1: 검사 모듈 신규 작성 (plan_guard)

**Files:**
- Create: `scripts/plan_guard.py`
- Test: `scripts/tests/test_plan_guard.py`

**Model**: sonnet

**검증**: 문서 집합 해석(단일/분할/끊긴 링크/고아 문서)과 검사 G1~G6 각각을 단위 테스트로 확인한다. 성공 기준은 — 코드 블록 없는 Modify task 가 G1 위반으로 잡히고, 축약 마커가 G2 로 잡히되 같은 task 의 `**원본**` 에 있던 동일 라인은 면제되며, 하위 문서에만 있는 byte-mismatch 가 인덱스 경로로 진입해도 검출되고(false-pass 회귀 고정), task 10개 단일 문서가 G3 위반, 하위 문서 4 task 가 G4 위반으로 잡히는 것. 여기에 더해 **코드 블록 안에 예시 task 헤더나 예시 Files 줄이 들어 있는 계획서**에서 task 수와 필드가 예시에 오염되지 않는 것도 확인한다 — 규약을 설명하는 계획서는 예시를 코드 블록에 싣기 마련이고, 이 계획서 자체가 그 경우다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계가 테스트 코드를 직접 작성한다. 기존 테스트 관례를 따른다 — 모듈 docstring, `from scripts.plan_guard import ...` 절대 import, 파일 로컬 `_write(path, content)` 헬퍼, `tmp_path` 픽스처, 클래스 없이 평평한 `def test_*`. `**원본**` 리터럴이 필요하면 `"**" + "원본" + "**"` 조합으로 우회한다 (`test_plan_byte_check.py` 의 기존 패턴).

Run: `pytest scripts/tests/test_plan_guard.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 모듈 작성**

**수정 후** (`new file: scripts/plan_guard.py`):
```python
"""Plan structure + code-presence guard.

Deterministic checks that an implementation plan actually carries its
implementation code, and that a long plan is split into an index plus
per-task sub-documents.

Complements scripts.plan_byte_check: that module verifies the CONTENT of
`**원본**` blocks that exist; this one verifies that the blocks exist at
all, that no block is elided with a shorthand marker, and that the plan's
document layout follows the split rules. Both are run over the full
document set (index + sub-documents) resolved by resolve_documents().
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

SPLIT_THRESHOLD = 10  # tasks 이상이면 분할 구조 필수
MAX_TASKS_PER_SUBDOC = 3  # 하위 문서 하나가 담을 수 있는 task 수 상한

_SUBDOC_DIR = "plan"
_SUBDOC_NAME_RE = re.compile(r"^tasks-(\d{2})(?:-(\d{2}))?\.md$")

_TASK_HEADER_RE = re.compile(r"^### Task (\d+):\s*(.+?)\s*$", re.MULTILINE)
_FENCE_MASK_RE = re.compile(r"```.*?```", re.DOTALL)
_DETAIL_LINK_RE = re.compile(r"^\*\*상세\*\*:\s*(\S+)\s*$", re.MULTILINE)
_FILES_LINE_RE = re.compile(r"^-\s*(Create|Modify|Test):\s*`([^`]+)`", re.MULTILINE)
_MODEL_RE = re.compile(r"^\*\*Model\*\*:\s*(\S+)\s*$", re.MULTILINE)
_VERIFY_RE = re.compile(r"^\*\*검증\*\*:\s*(.+?)\s*$", re.MULTILINE)
_ORIGINAL_RE = re.compile(r"\*\*원본\*\*\s*\(")
_MODIFIED_RE = re.compile(r"\*\*수정 후\*\*")
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n(.*?)```", re.DOTALL)

# 축약 마커: 주석 기호 뒤에 생략을 뜻하는 표현이 오는 라인만 잡는다.
# 맨몸 "..." 한 줄은 정상 코드(Python Ellipsis stub 등)와 충돌하므로 제외.
_ELISION_BODY = (
    r"(?:생략|중략|이하\s*동일|나머지\s*동일|기존\s*코드\s*유지|동일\s*패턴"
    r"|omitted|unchanged|rest\s+of|existing\s+code|same\s+as\s+(?:above|before))"
)
_ELISION_RES = (
    re.compile(r"^\s*(?:#|//|--|;|/\*|<!--)\s*\.{0,3}\s*" + _ELISION_BODY, re.IGNORECASE),
    re.compile(r"^\s*\.{3}\s*" + _ELISION_BODY, re.IGNORECASE),
    re.compile(r"^\s*\(\s*(?:중략|생략)\s*\)\s*$"),
)


@dataclass(frozen=True)
class Violation:
    code: str  # G1..G5
    doc_path: Path
    task_id: Optional[int]
    reason: str
    human_reason: str


@dataclass(frozen=True)
class TaskBlock:
    task_id: int
    name: str
    doc_path: Path
    body: str
    creates: List[str]
    modifies: List[str]
    tests: List[str]
    model: Optional[str]
    verify: Optional[str]
    detail_link: Optional[str]


@dataclass(frozen=True)
class PlanDocuments:
    index_path: Path
    sub_paths: List[Path]
    is_split: bool

    @property
    def all_paths(self) -> List[Path]:
        return [self.index_path] + self.sub_paths


def resolve_documents(index_path: Path) -> PlanDocuments:
    """인덱스 경로에서 문서 집합을 해석한다.

    plan/ 하위 폴더가 있고 이름 규약에 맞는 문서가 하나라도 있으면 분할 구조.
    소비자는 전부 이 함수를 통해 문서 집합을 얻어야 한다 — 각자 해석하면
    한 곳만 어긋나도 인덱스만 검사하고 통과하는 false-pass 가 난다.
    """
    sub_dir = index_path.parent / _SUBDOC_DIR
    sub_paths: List[Path] = []
    if sub_dir.is_dir():
        for child in sorted(sub_dir.iterdir()):
            if child.is_file() and _SUBDOC_NAME_RE.match(child.name):
                sub_paths.append(child)
    return PlanDocuments(index_path, sub_paths, bool(sub_paths))


def _mask_fences(text: str) -> str:
    """코드 펜스 안 내용을 공백으로 덮되 오프셋과 줄 수를 보존한다.

    계획서는 규약을 설명하려고 예시 task 헤더를 코드 블록 안에 싣는다.
    마스킹하지 않으면 그 예시가 실제 task 로 세어져 번호 연속성 검사와
    분할 임계 판정이 함께 어긋난다.
    """
    def _blank(m: re.Match) -> str:
        return "".join("\n" if c == "\n" else " " for c in m.group(0))

    return _FENCE_MASK_RE.sub(_blank, text)


def _slice_task_bodies(text: str, doc_path: Path) -> List[TaskBlock]:
    blocks: List[TaskBlock] = []
    headers = list(_TASK_HEADER_RE.finditer(_mask_fences(text)))
    for i, h in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[h.end():end]
        # 헤더 필드는 마스킹된 본문에서 읽는다 — 코드 블록 안 예시가 실제
        # 필드로 잡히면 인덱스-상세 정합성 검사가 헛돈다. 코드 블록 내용
        # 자체를 보는 검사(G1/G2)는 원본 body 를 쓴다.
        masked = _mask_fences(body)
        creates, modifies, tests = [], [], []
        for kind, path in _FILES_LINE_RE.findall(masked):
            {"Create": creates, "Modify": modifies, "Test": tests}[kind].append(path)
        model = _MODEL_RE.search(masked)
        verify = _VERIFY_RE.search(masked)
        link = _DETAIL_LINK_RE.search(masked)
        blocks.append(TaskBlock(
            task_id=int(h.group(1)),
            name=h.group(2),
            doc_path=doc_path,
            body=body,
            creates=creates,
            modifies=modifies,
            tests=tests,
            model=model.group(1) if model else None,
            verify=verify.group(1) if verify else None,
            detail_link=link.group(1) if link else None,
        ))
    return blocks


def _original_lines(body: str) -> set:
    """`**원본**` 블록 안 라인 집합 — G2 면제 판정에 쓴다."""
    lines: set = set()
    for m in _ORIGINAL_RE.finditer(body):
        fence = _FENCE_RE.search(body, m.end())
        if fence:
            lines.update(ln.strip() for ln in fence.group(1).splitlines())
    return lines


def _find_elisions(body: str) -> List[str]:
    exempt = _original_lines(body)
    hits: List[str] = []
    for fence in _FENCE_RE.finditer(body):
        for line in fence.group(1).splitlines():
            if line.strip() in exempt:
                continue
            if any(rx.search(line) for rx in _ELISION_RES):
                hits.append(line.strip())
    return hits


def check_plan(index_path: Path) -> List[Violation]:
    """G1~G5 검사. byte-equal(G6)은 verify_documents_byte_equal 이 담당."""
    docs = resolve_documents(index_path)
    violations: List[Violation] = []

    index_text = index_path.read_text(encoding="utf-8")
    index_tasks = _slice_task_bodies(index_text, index_path)

    detail_tasks: List[TaskBlock] = []
    for sub in docs.sub_paths:
        detail_tasks.extend(_slice_task_bodies(sub.read_text(encoding="utf-8"), sub))

    # G3 — 분할 강제 (10개 이상인데 단일 문서). 반대 방향은 검사하지 않는다:
    # 임계 미만의 분할은 허용된 재량이다.
    if not docs.is_split and len(index_tasks) >= SPLIT_THRESHOLD:
        violations.append(Violation(
            "G3", index_path, None,
            f"{len(index_tasks)} tasks in a single document (threshold {SPLIT_THRESHOLD})",
            f"task 가 {len(index_tasks)}개인데 단일 문서입니다. {SPLIT_THRESHOLD}개 이상이면 "
            f"인덱스 + plan/ 하위 문서 구조로 나눠주세요.",
        ))

    # G4 — 하위 문서당 task 상한
    for sub in docs.sub_paths:
        count = len([t for t in detail_tasks if t.doc_path == sub])
        if count > MAX_TASKS_PER_SUBDOC:
            violations.append(Violation(
                "G4", sub, None,
                f"{count} tasks in one sub-document (max {MAX_TASKS_PER_SUBDOC})",
                f"하위 문서 하나에 task 가 {count}개입니다. 최대 {MAX_TASKS_PER_SUBDOC}개까지만 "
                f"담을 수 있습니다.",
            ))

    # G5 — 구조 무결성 (링크 / 연번 / 헤더 필드 정합성)
    if docs.is_split:
        linked = set()
        for t in index_tasks:
            if not t.detail_link:
                violations.append(Violation(
                    "G5", index_path, t.task_id,
                    f"Task {t.task_id} has no **상세** link",
                    f"Task {t.task_id} 에 상세 문서 링크가 없습니다.",
                ))
                continue
            target = (index_path.parent / t.detail_link).resolve()
            if not target.exists():
                violations.append(Violation(
                    "G5", index_path, t.task_id,
                    f"broken 상세 link: {t.detail_link}",
                    f"Task {t.task_id} 의 상세 문서가 없습니다: {t.detail_link}",
                ))
                continue
            linked.add(target)
        for sub in docs.sub_paths:
            if sub.resolve() not in linked:
                violations.append(Violation(
                    "G5", sub, None,
                    "orphan sub-document (not linked from index)",
                    "인덱스에서 링크되지 않은 하위 문서입니다.",
                ))
        detail_by_id = {t.task_id: t for t in detail_tasks}
        for t in index_tasks:
            d = detail_by_id.get(t.task_id)
            if d is None:
                violations.append(Violation(
                    "G5", index_path, t.task_id,
                    f"Task {t.task_id} missing from sub-documents",
                    f"Task {t.task_id} 의 상세 내용이 하위 문서에 없습니다.",
                ))
                continue
            for field, a, b in (
                ("Create", t.creates, d.creates),
                ("Modify", t.modifies, d.modifies),
                ("Test", t.tests, d.tests),
                ("Model", [t.model or ""], [d.model or ""]),
            ):
                if a != b:
                    violations.append(Violation(
                        "G5", index_path, t.task_id,
                        f"Task {t.task_id} {field} differs between index and detail",
                        f"Task {t.task_id} 의 {field} 값이 인덱스와 상세 문서에서 다릅니다.",
                    ))

    all_ids = sorted(t.task_id for t in (detail_tasks if docs.is_split else index_tasks))
    if all_ids != list(range(1, len(all_ids) + 1)):
        violations.append(Violation(
            "G5", index_path, None,
            f"task ids not a contiguous 1..N sequence: {all_ids}",
            f"task 번호가 1부터 이어지지 않습니다: {all_ids}",
        ))

    # G1 / G2 — 코드 블록 존재 + 축약 마커. 상세를 담은 문서에서만 판정한다.
    for t in (detail_tasks if docs.is_split else index_tasks):
        labels = _mask_fences(t.body)  # 라벨은 펜스 밖에 있다
        if t.modifies and not (_ORIGINAL_RE.search(labels) and _MODIFIED_RE.search(labels)):
            violations.append(Violation(
                "G1", t.doc_path, t.task_id,
                f"Task {t.task_id} modifies files but has no 원본/수정 후 pair",
                f"Task {t.task_id} 는 파일을 수정하는데 변경 전후 코드 블록이 없습니다. "
                f"자연어 설명만으로는 안 됩니다.",
            ))
        if t.creates and not _MODIFIED_RE.search(labels):
            violations.append(Violation(
                "G1", t.doc_path, t.task_id,
                f"Task {t.task_id} creates files but has no 수정 후 block",
                f"Task {t.task_id} 는 파일을 새로 만드는데 코드 블록이 없습니다.",
            ))
        for hit in _find_elisions(t.body):
            violations.append(Violation(
                "G2", t.doc_path, t.task_id,
                f"Task {t.task_id} code block contains an elision marker: {hit!r}",
                f"Task {t.task_id} 의 코드 블록에 생략 표현이 있습니다: {hit}",
            ))

    return violations


def verify_documents_byte_equal(index_path: Path, repo_root: Path) -> list:
    """G6 — byte-equal 검사를 문서 집합 전체에 순회 적용.

    인덱스만 검사하면 코드 블록이 하위 문서로 옮겨간 계획서에서 검사 대상이
    0건이 되어 무조건 통과한다. 이 wrapper 가 그 false-pass 를 막는다.
    """
    from scripts.plan_byte_check import verify_plan_block_byte_equal

    mismatches = []
    for path in resolve_documents(index_path).all_paths:
        mismatches.extend(verify_plan_block_byte_equal(path, repo_root))
    return mismatches
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `pytest scripts/tests/test_plan_guard.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/plan_guard.py scripts/tests/test_plan_guard.py
git commit -m "feat(plan-guard): 계획서 코드 존재 + 분할 구조 결정적 검사 모듈 추가"
```

---

### Task 2: preflight 가 분할 구조를 인지하도록 확장

**Files:**
- Modify: `scripts/preflight.py:43-92`
- Test: `scripts/tests/test_preflight.py`

**Model**: sonnet

**검증**: 분할 구조 계획서(인덱스에 `**수정 후**` 없음 + 하위 문서에 있음)에서 code-pretty 사전 검사가 통과하고, 어느 문서에도 없으면 기존처럼 실패하는지 확인한다. 기존 단일 문서 계획서의 판정과 함수 시그니처·exit code 규약이 그대로인 것도 함께 확인한다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `pytest scripts/tests/test_preflight.py -v`
Expected: FAIL (분할 케이스 미지원)

- [ ] **Step 2: code_pretty_check / glossary_check 확장**

**원본** (`scripts/preflight.py:43-92`):
```python
def code_pretty_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(
            False,
            f"file not found: {file_path}",
            f"대상 파일이 존재하지 않습니다: {file_path}",
        )
    if not _PLAN_MD_PATTERN.match(str(file_path)):
        return PreflightResult(
            False,
            "code-pretty target must be implementation-plan.md",
            "code-pretty 대상은 -implementation-plan.md 파일이어야 합니다",
        )
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(
            False,
            "변경이력 footer not empty (doc is live)",
            "이미 변경이력 entry 가 존재합니다 (live doc). code-pretty 는 최초 생성 단계에서만 발화합니다",
        )
    if "**수정 후**" not in text:
        return PreflightResult(
            False,
            "no '수정 후' code blocks found — nothing to prettify",
            "'수정 후' 코드 블록이 없습니다. prettify 할 내용이 없습니다",
        )
    return PreflightResult(True, "ok", "정상")


def glossary_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(
            False,
            f"file not found: {file_path}",
            f"대상 파일이 존재하지 않습니다: {file_path}",
        )
    if not _PLAN_MD_PATTERN.match(str(file_path)):
        return PreflightResult(
            False,
            "glossary target must be implementation-plan.md",
            "용어집 대상은 -implementation-plan.md 파일이어야 합니다",
        )
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(
            False,
            "변경이력 footer not empty (doc is live)",
            "이미 변경이력 entry 가 존재합니다 (live doc). 용어집은 최초 생성 단계에서만 발화합니다",
        )
    return PreflightResult(True, "ok", "정상")
```

**수정 후**:
```python
def _plan_text_bundle(file_path: Path) -> str:
    """인덱스 + 분할 하위 문서의 본문을 이어붙인다.

    분할 구조에서는 코드 블록이 하위 문서에 있으므로, 인덱스만 읽으면
    '수정 후 블록 없음' 으로 잘못 판정한다.
    """
    from scripts.plan_guard import resolve_documents

    parts = []
    for path in resolve_documents(file_path).all_paths:
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def code_pretty_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(
            False,
            f"file not found: {file_path}",
            f"대상 파일이 존재하지 않습니다: {file_path}",
        )
    if not _PLAN_MD_PATTERN.match(str(file_path)):
        return PreflightResult(
            False,
            "code-pretty target must be implementation-plan.md",
            "code-pretty 대상은 -implementation-plan.md 파일이어야 합니다",
        )
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(
            False,
            "변경이력 footer not empty (doc is live)",
            "이미 변경이력 entry 가 존재합니다 (live doc). code-pretty 는 최초 생성 단계에서만 발화합니다",
        )
    # ⚠️ RISK(side-effect): 분할 구조에서는 코드 블록이 하위 문서에 있어 인덱스 본문만으로 판정하면 오탐 — by 구현계획서-코드강제-분할 task 2
    if "**수정 후**" not in _plan_text_bundle(file_path):
        return PreflightResult(
            False,
            "no '수정 후' code blocks found — nothing to prettify",
            "'수정 후' 코드 블록이 없습니다. prettify 할 내용이 없습니다",
        )
    return PreflightResult(True, "ok", "정상")


def glossary_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(
            False,
            f"file not found: {file_path}",
            f"대상 파일이 존재하지 않습니다: {file_path}",
        )
    if not _PLAN_MD_PATTERN.match(str(file_path)):
        return PreflightResult(
            False,
            "glossary target must be implementation-plan.md",
            "용어집 대상은 -implementation-plan.md 파일이어야 합니다",
        )
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(
            False,
            "변경이력 footer not empty (doc is live)",
            "이미 변경이력 entry 가 존재합니다 (live doc). 용어집은 최초 생성 단계에서만 발화합니다",
        )
    return PreflightResult(True, "ok", "정상")
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `pytest scripts/tests/test_preflight.py scripts/tests/test_plan_guard.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/preflight.py scripts/tests/test_preflight.py
git commit -m "feat(preflight): code-pretty 사전 검사가 분할 하위 문서까지 인지"
```

---

### Task 3: writing-plans — Checklist 에 분할 판정 단계 추가

**Files:**
- Modify: `skills/writing-plans/SKILL.md:77`

**Model**: sonnet

**검증**: Checklist 항목 5.5 가 자체 점검과 코드 정리 사이에 들어가고, TaskCreate 항목 이름이 사용자 친화 한국어인지 확인한다. 성공 기준은 항목 번호가 이어지고 기존 6~10번 항목 본문이 그대로인 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2: Checklist 항목 삽입**

**원본** (`skills/writing-plans/SKILL.md:77`):
```markdown
6. **코드 정리 + 용어집 작성 (병렬)** — dispatch `code-pretty` (Sonnet subagent, prettifies `**수정 후**` blocks) and `glossary` (Sonnet subagent, writes `<slug>-glossary.md`) in the SAME message so they run concurrently. Both run BEFORE verifying-spec and stop once the first change-history entry is logged.
```

**수정 후**:
```markdown
5.5. **문서 구조 확정 + 코드 강제 검사** — task 수를 세고, 10개 이상이면 인덱스 + `plan/` 하위 문서로 나눈다 (Plan Split 섹션). 그런 다음 `plan_guard` 검사를 돌려 코드 블록 부재 / 축약 마커 / 구조 위반을 확인한다. 위반이 하나라도 있으면 계획서는 저장되지 않는다.
6. **코드 정리 + 용어집 작성 (병렬)** — dispatch `code-pretty` (Sonnet subagent, prettifies `**수정 후**` blocks) and `glossary` (Sonnet subagent, writes `<slug>-glossary.md`) in the SAME message so they run concurrently. Both run BEFORE verifying-spec and stop once the first change-history entry is logged.
```

- [ ] **Step 3: Commit**

```bash
git add skills/writing-plans/SKILL.md
git commit -m "docs(writing-plans): Checklist 에 분할 판정 + 코드 강제 검사 단계 추가"
```

---

### Task 4: writing-plans — 분할 규약 섹션 + 검사 helper 교체

**Files:**
- Modify: `skills/writing-plans/SKILL.md:191`
- Modify: `skills/writing-plans/SKILL.md:366-367`

**Model**: sonnet

**검증**: 분할 규약 섹션이 Task Structure 앞에 들어가고, Self-Review 에 코드 존재 확인과 문서 구조 확인 항목이 추가됐는지 확인한다. 성공 기준은 두 지점이 반영되고 기존 규칙 본문(byte-copy / 검증 필드)이 그대로인 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2-a: 분할 규약 섹션 삽입**

**원본** (`skills/writing-plans/SKILL.md:191`):
```markdown
## Task Structure (inherited)
```

**수정 후**:
````markdown
## Plan Split — 인덱스 + 하위 문서

task 가 **10개 이상**이면 계획서를 나눈다. 미만이면 단일 문서 그대로다. 미만이어도 코드량이 많다고 판단되면 나눠도 된다 — 재량은 나누는 방향으로만 열려 있다.

```
docs/features/<date>-<slug>/
├── <slug>-implementation-plan.md     ← 인덱스 (이름 그대로)
└── plan/
    ├── tasks-01-03.md
    ├── tasks-04-06.md
    └── tasks-07.md
```

하위 문서 이름은 `plan/tasks-NN.md` 또는 `plan/tasks-NN-MM.md` (2자리, 연속 범위). task 번호는 문서를 가로질러 1부터 이어지는 전역 연번이고, 연관된 task 가 인접 번호가 되도록 정렬한다. **하위 문서 하나에 task 는 최대 3개**까지다.

인덱스의 task 블록은 헤더 필드만 남긴다 — `**상세**` 링크 / `**Files:**` / `**Model**` / `**검증**`. step 목록과 코드 블록은 하위 문서에 둔다. 실행 단계가 인덱스만 읽고 DAG 를 짤 수 있어야 하기 때문이다.

```markdown
### Task 4: 결제 검증 helper

**상세**: plan/tasks-04-06.md
**Files:**
- Modify: `src/pay/verify.py:40-88`
- Test: `tests/pay/test_verify.py`
**Model**: sonnet
**검증**: <자연어 1~2줄>
```

하위 문서는 인덱스와 같은 헤더 필드 + step 목록 + 코드 블록을 담는다. **변경이력 footer 는 두지 않는다** — 계획서의 변경이력은 인덱스 한 곳으로 모은다.

## Task Structure (inherited)
````

- [ ] **Step 2-b: Self-Review 에 코드 존재 항목 추가**

**원본** (`skills/writing-plans/SKILL.md:366-367`):
```markdown
5. **same-file 묶음 룰 위반 검사**: task 들 중 같은 파일만 만지는 chain 이 2건 이상 있는지 확인. 있으면 D1 의 3 조건 (같은 파일 / test 경계 X / mechanical) 재검토 → 묶을지 결정. (v2.0.1+)
6. **검증 필드 구체성 (v2.9+)**: 코드 변경 task 마다 `**검증**:` 필드가 있고 "무엇을 + 어떤 기준" 을 담았는지 확인. 동어반복 ("테스트 작성" 한 줄) 이나 테스트 코드 블록이 남아 있으면 수정.
```

**수정 후**:
```markdown
5. **same-file 묶음 룰 위반 검사**: task 들 중 같은 파일만 만지는 chain 이 2건 이상 있는지 확인. 있으면 D1 의 3 조건 (같은 파일 / test 경계 X / mechanical) 재검토 → 묶을지 결정. (v2.0.1+)
6. **검증 필드 구체성 (v2.9+)**: 코드 변경 task 마다 `**검증**:` 필드가 있고 "무엇을 + 어떤 기준" 을 담았는지 확인. 동어반복 ("테스트 작성" 한 줄) 이나 테스트 코드 블록이 남아 있으면 수정.
7. **구현 코드 존재 확인**: 파일을 만들거나 고치는 task 마다 코드 블록이 실제로 있는지 확인. 자연어 설명만 남은 task, 코드 블록 안의 생략 표현 (`... 생략`, `기존 코드 유지`, `이하 동일`) 은 그 자리에서 실제 코드로 채운다. 계획서가 길어질수록 이 항목이 무너지기 쉬우니 task 를 하나씩 짚어가며 본다.
8. **문서 구조 확인**: task 가 10개 이상이면 인덱스 + `plan/` 하위 문서로 나뉘어 있는지, 하위 문서마다 task 가 3개 이하인지, 인덱스 링크와 실제 파일이 맞는지 확인.
```

- [ ] **Step 3: Commit**

```bash
git add skills/writing-plans/SKILL.md
git commit -m "docs(writing-plans): 분할 규약 섹션 + 코드 존재 자체 점검 추가"
```

---

### Task 5: writing-plans — 검사 one-liner 를 plan_guard 로 교체

**Files:**
- Modify: `skills/writing-plans/SKILL.md:371-374`
- Modify: `skills/writing-plans/SKILL.md:377-392`
- Modify: `skills/writing-plans/SKILL.md:395-400`

**Model**: sonnet

**검증**: 저장 전 검사가 byte-equal 만 보던 것에서 G1~G6 전체를 보는 형태로 바뀌고, 실패 시 안내 문구가 "코드 블록을 채워라 / 구조를 나눠라" 를 포함하는지 확인한다. 성공 기준은 명령이 실제로 실행 가능하고 위반 목록을 사람이 읽을 수 있는 한국어로 출력하는 것.

> 이 task 는 한 섹션을 세 조각(제목·설명 / 명령 본문 / 실패 안내)으로 나눠 고친다. 조각들이 코드 펜스를 사이에 두고 떨어져 있어서, 펜스를 포함한 한 덩어리로 잡으면 검사 도구가 블록 경계를 잘못 읽는다.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

Run: 임시 계획서로 명령 실행 — 코드 블록 없는 task 가 있으면 exit 1 + 위반 목록 출력
Expected: 위반 검출

- [ ] **Step 2-a: 섹션 제목 + 설명 교체**

**원본** (`skills/writing-plans/SKILL.md:371-374`):
```markdown
### plan_byte_check helper (v2.0.0+)

After all tasks are written and self-review checks pass, run the byte-equal
verifier:
```

**수정 후**:
```markdown
### plan_guard + plan_byte_check helper

After all tasks are written and self-review checks pass, run the guard. It
covers code presence (G1), elision markers (G2), split structure (G3~G5),
and byte-equality across the whole document set (G6):
```

- [ ] **Step 2-b: 명령 본문 교체 (펜스 안쪽만)**

**원본** (`skills/writing-plans/SKILL.md:377-392`):
```python
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_byte_check import verify_plan_block_byte_equal
mismatches = verify_plan_block_byte_equal(
    Path('docs/features/<date>-<slug>/<slug>-implementation-plan.md'),
    Path('.'),
)
if mismatches:
    for m in mismatches:
        print(f'MISMATCH #{m.block_index} — {m.reason}')
        print(f'  file: {m.file_path}')
    sys.exit(1)
print('plan_byte_check ✅ all blocks byte-equal')
sys.exit(0)
" 2>&1
```

**수정 후**:
```python
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_guard import check_plan, verify_documents_byte_equal
index = Path('docs/features/<date>-<slug>/<slug>-implementation-plan.md')
violations = check_plan(index)
mismatches = verify_documents_byte_equal(index, Path('.'))
for v in violations:
    print(f'{v.code} — {v.human_reason}')
    print(f'  문서: {v.doc_path}')
for m in mismatches:
    print(f'G6 — {m.reason}')
    print(f'  파일: {m.file_path}')
if violations or mismatches:
    sys.exit(1)
print('plan_guard ✅ 코드 블록 / 구조 / byte-equal 모두 통과')
sys.exit(0)
" 2>&1
```

- [ ] **Step 2-c: 실패 안내 교체**

**원본** (`skills/writing-plans/SKILL.md:395-400`):
```markdown
If exit 1 (mismatches found):
- Mismatch list shown to user.
- Plan is NOT saved. Fix the `**원본**` blocks (they must be byte-identical
  to current file content) and re-run the helper.
- This enforces v2.0.0 byte-copy implementer's precondition: it will
  fail-fast on mismatch with no LLM fuzzy match fallback.
```

**수정 후**:
```markdown
If exit 1:
- The violation list is shown to the user.
- **Plan is NOT saved.** Fix and re-run:
  - G1 — the task changes files but carries no code. Write the actual
    `**원본**` / `**수정 후**` blocks. A natural-language description is
    not a substitute, no matter how long the plan already is.
  - G2 — a code block contains an elision marker. Replace it with the real code.
  - G3~G5 — split the plan (10+ tasks), keep sub-documents to 3 tasks, fix
    broken links / duplicate task numbers / field mismatches.
  - G6 — the `**원본**` block is not byte-identical to the current file.
- This enforces the byte-copy implementer's precondition (fail-fast, no LLM
  fuzzy match fallback) AND the code-presence rule that the fuzzy path used
  to let through.
```

- [ ] **Step 3: Commit**

```bash
git add skills/writing-plans/SKILL.md
git commit -m "feat(writing-plans): 저장 전 검사를 plan_guard 로 교체 (코드 강제 + 구조)"
```

---

### Task 6: auto-writing-plans — 분할 규약 + 검사 교체 (mirror)

**Files:**
- Modify: `skills/auto-writing-plans/SKILL.md:40-42`
- Modify: `skills/auto-writing-plans/SKILL.md:52-54`
- Modify: `skills/auto-writing-plans/SKILL.md:57-70`
- Modify: `skills/auto-writing-plans/SKILL.md:73`

**Model**: sonnet

**검증**: 자동 흐름의 task 분해 단계에 분할 판정이 들어가고, 사후 검사가 정식 흐름과 같은 검사 모듈을 부르는지 확인한다. 성공 기준은 두 흐름의 규약이 같은 값(임계 10 / 상한 3 / 위반 시 차단)을 쓰는 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2-a: Step 2 에 분할 판정 추가**

**원본** (`skills/auto-writing-plans/SKILL.md:40-42`):
```markdown
세 조건 중 하나라도 어기면 분리. multi-step task 안 step 구조: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 1회) → byte-copy Edit (N회) → test pass → self-review. 애매하면 분리 (보수적 default).

**Step 2 끝 자체 검토 (same-file 묶음 자체 검토)**: 자동 분해 결과 같은 파일만 만지는 task chain ≥ 2건 있으면 메인이 직접 D1 의 3 조건 재검토 → 묶을지 결정. 사용자 응답 wait X (auto 모드).
```

**수정 후**:
```markdown
세 조건 중 하나라도 어기면 분리. multi-step task 안 step 구조: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 1회) → byte-copy Edit (N회) → test pass → self-review. 애매하면 분리 (보수적 default).

**분할 판정**: 분해 결과 task 가 **10개 이상**이면 인덱스 + `plan/` 하위 문서 구조로 쓴다. 하위 문서 이름은 `plan/tasks-NN.md` / `plan/tasks-NN-MM.md` (2자리, 연속 범위), 하나에 task 최대 3개, 번호는 전역 연번. 인덱스 task 블록은 `**상세**` 링크 + `**Files:**` + `**Model**` + `**검증**` 만 담고, step 목록과 코드 블록은 하위 문서에 둔다. 하위 문서에는 변경이력 footer 를 두지 않는다 (인덱스 한 곳으로 모음). 10개 미만이면 단일 문서 — 코드량이 많다고 판단되면 나눠도 된다 (재량은 나누는 방향으로만).

**구현 코드 강제**: 파일을 만들거나 고치는 task 는 예외 없이 코드 블록을 싣는다. 계획서가 길어졌다고 자연어 설명으로 대체하지 않는다. 코드 블록 안에 `... 생략` / `기존 코드 유지` / `이하 동일` 류 생략 표현을 쓰지 않는다 — Step 4.5 검사가 결정적으로 차단한다.

**Step 2 끝 자체 검토 (same-file 묶음 자체 검토)**: 자동 분해 결과 같은 파일만 만지는 task chain ≥ 2건 있으면 메인이 직접 D1 의 3 조건 재검토 → 묶을지 결정. 사용자 응답 wait X (auto 모드).
```

- [ ] **Step 2-b: Step 4.5 제목 + 설명 교체**

**원본** (`skills/auto-writing-plans/SKILL.md:52-54`):
```markdown
### Step 4.5 — plan_byte_check 자동 (v2.0.0+)

Plan 본문 자동 작성 직후, 메인이 helper 자동 호출:
```

**수정 후**:
```markdown
### Step 4.5 — plan_guard 자동 (3회 재시도)

Plan 본문 자동 작성 직후, 메인이 helper 자동 호출. 코드 블록 존재 (G1) / 생략 표현 (G2) / 분할 구조 (G3~G5) / byte-equal (G6) 을 한 번에 본다:
```

- [ ] **Step 2-c: Step 4.5 명령 본문 교체 (펜스 안쪽만)**

**원본** (`skills/auto-writing-plans/SKILL.md:57-70`):
```python
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_byte_check import verify_plan_block_byte_equal
mismatches = verify_plan_block_byte_equal(
    Path('<PLAN_PATH>'),
    Path('.'),
)
if mismatches:
    for m in mismatches:
        print(f'MISMATCH #{m.block_index} — {m.reason}')
    sys.exit(1)
sys.exit(0)
"
```

**수정 후**:
```python
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_guard import check_plan, verify_documents_byte_equal
index = Path('<PLAN_PATH>')
violations = check_plan(index)
mismatches = verify_documents_byte_equal(index, Path('.'))
for v in violations:
    print(f'{v.code} — {v.human_reason} ({v.doc_path})')
for m in mismatches:
    print(f'G6 — {m.reason}')
if violations or mismatches:
    sys.exit(1)
sys.exit(0)
"
```

- [ ] **Step 2-d: Step 4.5 실패 안내 교체**

**원본** (`skills/auto-writing-plans/SKILL.md:73`):
```markdown
미스매치 발견 시 메인이 즉시 plan 의 `**원본**` 블록 수정 후 재시도 (auto 모드 — 사용자 응답 wait X). 3회 재시도 후에도 실패 시 `ℹ️ plan_byte_check 가 3회 실패했습니다. 사용자가 직접 개입해주세요.` 안내 후 종료. byte-copy 정밀도 강제는 v2.0.0 구현계획서의 핵심 precondition.
```

**수정 후**:
```markdown
위반 발견 시 메인이 즉시 수정 후 재시도 (auto 모드 — 사용자 응답 wait X). G1 은 코드 블록을 실제로 채워서, G2 는 생략 표현을 실제 코드로 바꿔서, G3~G5 는 문서를 나누거나 링크·번호를 맞춰서, G6 은 `**원본**` 블록을 현재 파일과 맞춰서 해소한다. 3회 재시도 후에도 실패 시 `ℹ️ plan_guard 가 3회 실패했습니다. 사용자가 직접 개입해주세요.` 안내 후 종료. 이 검사는 실행 단계의 원본 그대로 보존 방식이 성립하기 위한 전제이자, 계획서에 코드가 실리도록 강제하는 유일한 장치다.
```

- [ ] **Step 3: Commit**

```bash
git add skills/auto-writing-plans/SKILL.md
git commit -m "docs(auto-writing-plans): 분할 규약 + plan_guard 검사 mirror"
```

---

### Task 7: executing-plans — 분할 구조 읽기 분기

**Files:**
- Modify: `skills/executing-plans/SKILL.md:34-38`

**Model**: sonnet

**검증**: 인라인 실행이 분할 계획서를 만났을 때 인덱스를 먼저 읽고 하위 문서는 해당 task 진행 시점에 읽는지 확인한다. 성공 기준은 단일 문서 계획서의 기존 동작이 그대로이고 분할 계획서에서 task 가 누락되지 않는 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2: Plan Loading 분기 추가**

**원본** (`skills/executing-plans/SKILL.md:34-38`):
```markdown
### Step 1: Load and Review Plan
1. Read `docs/features/<date>-<slug>/<slug>-implementation-plan.md`
2. Review critically — list any gaps or concerns
3. If concerns exist: raise them with the user before starting
4. If clean: create TaskCreate tasks (one per plan task) and proceed
```

**수정 후**:
```markdown
### Step 1: Load and Review Plan
1. Read `docs/features/<date>-<slug>/<slug>-implementation-plan.md`
2. **분할 구조 분기** — 같은 폴더에 `plan/tasks-*.md` 가 있으면 그 계획서는 인덱스다. 인덱스에는 task 헤더 필드(`**상세**` 링크 / Files / Model / 검증)만 있고 step 목록과 코드 블록은 하위 문서에 있다. 여기서 하위 문서를 전부 읽지 마라 — **각 task 를 시작하는 시점에 그 task 의 `**상세**` 문서만 읽는다.** 미리 다 읽으면 나눠 놓은 의미가 없다.
3. Review critically — list any gaps or concerns
4. If concerns exist: raise them with the user before starting
5. If clean: create TaskCreate tasks (one per plan task) and proceed
```

- [ ] **Step 3: Commit**

```bash
git add skills/executing-plans/SKILL.md
git commit -m "docs(executing-plans): 분할 계획서 lazy 읽기 분기 추가"
```

---

### Task 8: js-super-sub-driven — Plan Analysis 를 인덱스 기반으로

**Files:**
- Modify: `skills/js-super-sub-driven/SKILL.md:82`

**Model**: sonnet

**검증**: DAG 분석이 인덱스만 읽고도 wave 를 짜고, 보조 에이전트 호출 직전에 해당 wave 의 하위 문서만 읽는지 확인한다. 성공 기준은 보조 에이전트 프롬프트 3종(구현 / 재정렬 / 검토)이 변경되지 않고 task 전문 붙여넣기 방식 그대로인 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2: Read plan tasks 항목 확장**

**원본** (`skills/js-super-sub-driven/SKILL.md:82`):
```markdown
1. **Read plan tasks** — `<slug>-implementation-plan.md` 의 §1 단계별 작업 모든 task block.
```

**수정 후**:
```markdown
1. **Read plan tasks** — `<slug>-implementation-plan.md` 의 §1 단계별 작업 모든 task block. 같은 폴더에 `plan/tasks-*.md` 가 있으면 그 파일은 인덱스다 — DAG 분석에 필요한 헤더 필드 (`**Files:**` / `**Model**` / `**검증**` / `**상세**` 링크) 가 인덱스에 다 있으므로 **여기서는 인덱스만 읽는다**. 각 task 의 step 목록과 코드 블록은 wave dispatch 직전 (W-2 Stage 1) 에 그 task 의 `**상세**` 문서에서 읽어 프롬프트에 붙여넣는다. 보조 에이전트는 계획서 파일을 직접 열지 않으므로 프롬프트 3종은 분할 여부와 무관하게 그대로다.
```

- [ ] **Step 3: Commit**

```bash
git add skills/js-super-sub-driven/SKILL.md
git commit -m "docs(sub-driven): DAG 분석은 인덱스, task 전문은 wave 시점 읽기"
```

---

### Task 9: verifying-spec — 분할 대상 읽기 규약 (3파일 동시)

**Files:**
- Modify: `skills/verifying-spec/SKILL.md:21`
- Modify: `skills/verifying-spec/clean-solo-prompt.md:25`
- Modify: `skills/verifying-spec/clean-cross-prompt.md:32`

**Model**: sonnet

**검증**: 검증 대상이 분할 계획서일 때 하위 문서가 대상의 일부로 읽히고, 단독 검증자에게는 여전히 상위 문서 경로가 주어지지 않는지 확인한다. 성공 기준은 세 파일이 같은 규약을 말하고 단독 검증자 프롬프트에 상위 문서 경로 자리표시자가 없는 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2-a: When to Invoke 표에 주석 추가**

**원본** (`skills/verifying-spec/SKILL.md:21`):
```markdown
| End of `writing-plans` | <slug>-implementation-plan.md | [<slug>-requirements.md, <slug>-tech-design.md] |
```

**수정 후**:
```markdown
| End of `writing-plans` | <slug>-implementation-plan.md (+ `plan/tasks-*.md` if split) | [<slug>-requirements.md, <slug>-tech-design.md] |
```

- [ ] **Step 2-b: 단독 검증자 프롬프트에 규약 추가**

**원본** (`skills/verifying-spec/clean-solo-prompt.md:25`):
```markdown
    Read it with the Read tool. This is the ONLY file you may read.
```

**수정 후**:
```markdown
    Read it with the Read tool.

    If that document links to detail documents under a `plan/` folder
    beside it, those are part of THIS document — read them too. Read
    nothing else: no sibling specs, no upstream documents.
```

- [ ] **Step 2-c: 대조 검증자 프롬프트에 규약 추가**

**원본** (`skills/verifying-spec/clean-cross-prompt.md:32`):
```markdown
    Read all of them with the Read tool. Read nothing else.
```

**수정 후**:
```markdown
    Read all of them with the Read tool. If the target links to detail
    documents under a `plan/` folder beside it, those are part of the
    target — read them too. Read nothing else.
```

- [ ] **Step 3: Commit**

```bash
git add skills/verifying-spec/SKILL.md skills/verifying-spec/clean-solo-prompt.md skills/verifying-spec/clean-cross-prompt.md
git commit -m "docs(verifying-spec): 분할 대상의 하위 문서를 대상의 일부로 읽기"
```

---

### Task 10: code-pretty + glossary — 분할 대상 처리

**Files:**
- Modify: `skills/code-pretty/SKILL.md:100`
- Modify: `skills/glossary/SKILL.md:105`

**Model**: sonnet

**검증**: 코드 정리 보조 에이전트가 분할 구조에서 문서마다 하나씩 병렬로 호출되고, 용어집 보조 에이전트는 하나가 하위 문서까지 읽는지 확인한다. 성공 기준은 두 프롬프트의 경로 주입 방식이 분할 여부에 따라 명확히 갈리는 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2-a: code-pretty 프롬프트 대상 지정**

**원본** (`skills/code-pretty/SKILL.md:100`):
```markdown
Target file: <ABSOLUTE_PATH>
```

**수정 후**:
```markdown
Target file: <ABSOLUTE_PATH>

(분할 구조 계획서에서는 caller 가 `**수정 후**` 블록을 가진 문서마다 이 보조 에이전트를 하나씩, 같은 메시지에 실어 병렬로 호출한다. 각 호출은 자기 대상 파일 하나만 만진다.)
```

- [ ] **Step 2-b: glossary 프롬프트 읽기 범위**

**원본** (`skills/glossary/SKILL.md:105`):
```markdown
읽을 파일: <PLAN_ABSOLUTE_PATH>
```

**수정 후**:
```markdown
읽을 파일: <PLAN_ABSOLUTE_PATH>
           (이 파일 옆 `plan/` 폴더에 상세 문서들이 있으면 그것도 함께 읽으세요. 코드 블록이 거기 있습니다.)
```

- [ ] **Step 3: Commit**

```bash
git add skills/code-pretty/SKILL.md skills/glossary/SKILL.md
git commit -m "docs(code-pretty,glossary): 분할 계획서 대상 처리 규약"
```

---

### Task 11: change-history — 하위 문서 footer 예외

**Files:**
- Modify: `skills/change-history/SKILL.md:18`

**Model**: sonnet

**검증**: 계획서 하위 문서가 변경이력 footer 를 갖지 않고 모든 entry 가 인덱스로 모이는 규약이 명시됐는지 확인한다. 성공 기준은 기존 용어집 예외 문장이 그대로 남아 있는 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

- [ ] **Step 2: 예외 항목 추가**

**원본** (`skills/change-history/SKILL.md:18`):
```markdown
**파생 문서 예외 (용어집)**: `<slug>-glossary.md` 는 리비전마다 통째로 재생성되는 파생 문서라 `## 변경이력` footer 를 갖지 않는다. 이 파일의 생성·갱신은 본 skill 의 트리거 대상이 아니다 (`glossary` skill 본문의 동일 룰과 쌍).
```

**수정 후**:
```markdown
**파생 문서 예외 (용어집)**: `<slug>-glossary.md` 는 리비전마다 통째로 재생성되는 파생 문서라 `## 변경이력` footer 를 갖지 않는다. 이 파일의 생성·갱신은 본 skill 의 트리거 대상이 아니다 (`glossary` skill 본문의 동일 룰과 쌍).

**분할 계획서 예외 (하위 문서)**: 계획서가 인덱스 + `plan/tasks-*.md` 로 나뉜 경우, 하위 문서는 `## 변경이력` footer 를 갖지 않는다. 하위 문서를 고쳐서 생기는 entry 도 전부 인덱스 (`<slug>-implementation-plan.md`) 의 footer 로 모은다. 이력이 문서마다 흩어지면 감사 흐름이 끊긴다.
```

- [ ] **Step 3: Commit**

```bash
git add skills/change-history/SKILL.md
git commit -m "docs(change-history): 분할 계획서 하위 문서 footer 예외"
```

---

### Task 12: commands 안내 + CLAUDE.md 결합 메모 + fixture

**Files:**
- Modify: `commands/write-plan.md:13`
- Modify: `commands/pretty-md.md:16`
- Create: `skills/js-super-sub-driven/tests/H20-plan-split/README.md`
- Modify: `CLAUDE.md`

**Model**: sonnet

**검증**: 사용자 안내에 분할 산출물이 드러나고, 결합 메모의 회귀 확인 명령이 실제로 실행 가능한지 확인한다. 성공 기준은 결합 메모 bash 블록이 `# expected:` 주석 형식을 지켜 검증 러너가 수집할 수 있고, 명령이 읽기 전용인 것.

- [ ] **Step 1: 통합 확인 (실행 단계 수행)**

Run: `python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"`
Expected: 규칙 수가 직전보다 증가

- [ ] **Step 2-a: write-plan 산출물 안내**

**원본** (`commands/write-plan.md:13`):
```markdown
- `docs/features/<날짜>-<slug>/<slug>-implementation-plan.md` — 구현계획서 (정본)
```

**수정 후**:
```markdown
- `docs/features/<날짜>-<slug>/<slug>-implementation-plan.md` — 구현계획서 (정본). task 가 10개 이상이면 이 파일은 인덱스가 되고, task 상세와 코드는 같은 폴더의 `plan/tasks-*.md` 로 나뉩니다.
```

- [ ] **Step 2-b: pretty-md 검출 대상**

**원본** (`commands/pretty-md.md:16`):
```markdown
2. `docs/features/<date>-<slug>/<slug>-{requirements,tech-design,implementation-plan}.md` 중 존재하는 모든 `.md` 검출 (feature 폴더에는 날짜 접두어가 붙으므로, slug 만 알 때는 `docs/features/*-<slug>/` 로 glob 해서 실제 폴더를 찾을 것)
```

**수정 후**:
```markdown
2. `docs/features/<date>-<slug>/<slug>-{requirements,tech-design,implementation-plan}.md` 중 존재하는 모든 `.md` 검출 (feature 폴더에는 날짜 접두어가 붙으므로, slug 만 알 때는 `docs/features/*-<slug>/` 로 glob 해서 실제 폴더를 찾을 것). 구현계획서가 분할 구조면 `plan/tasks-*.md` 도 함께 검출할 것
```

- [ ] **Step 2-c: fixture 작성**

**수정 후** (`new file: skills/js-super-sub-driven/tests/H20-plan-split/README.md`):
```markdown
# H20 — 분할 계획서 실행 + 코드 강제 차단

## 목적

계획서가 인덱스 + `plan/` 하위 문서로 나뉜 경우의 실행 흐름과, 코드 블록이 빠진 계획서가 저장 게이트에서 막히는지를 확인한다.

## 시나리오 A (통과) — 분할 계획서 실행

**입력**: task 12개짜리 계획서. 인덱스에는 헤더 필드와 `**상세**` 링크만, `plan/tasks-01-03.md` ~ `plan/tasks-10-12.md` 에 step 과 코드 블록.

**기대 동작**
1. 진입 검사가 인덱스의 `commit_policy: per-task` 를 읽고 통과
2. DAG 분석이 **인덱스만** 읽고 wave 구성 (하위 문서 미리 읽지 않음)
3. wave 별 dispatch 직전에 해당 task 의 상세 문서를 읽어 프롬프트에 전문 붙여넣기
4. 보조 에이전트 프롬프트 3종은 계획서 파일을 열지 않음 (경로 주입 없음)
5. 실행 종료 후 변경이력 entry 는 **인덱스** footer 에만 append

**실패 신호**: 하위 문서를 전부 미리 읽음 / 하위 문서에 변경이력이 append 됨 / 보조 에이전트에게 계획서 경로가 주입됨

## 시나리오 B (차단) — 코드 없는 task

**입력**: `Modify:` 파일이 있는데 `**원본**` / `**수정 후**` 블록이 없고 "이 부분을 적절히 수정한다" 는 자연어만 있는 task.

**기대 동작**: 저장 게이트에서 G1 위반으로 차단. 계획서가 저장되지 않고, 안내에 "코드 블록을 실제로 채워라" 가 나온다.

**실패 신호**: 통과 / 경고만 내고 진행

## 시나리오 C (차단) — 축약 마커

**입력**: `**수정 후**` 블록 안에 `# ... 이하 동일` 한 줄.

**기대 동작**: G2 위반으로 차단.

**변형 (통과해야 함)**: 같은 표현이 `**원본**` 블록에도 똑같이 있으면 (원래 파일에 있던 주석) 면제되어 통과.

## 시나리오 D (차단) — 분할 누락

**입력**: task 10개인데 단일 문서.

**기대 동작**: G3 위반으로 차단 + 나누라는 안내.

**변형 (통과해야 함)**: task 9개 단일 문서는 통과. task 6개인데 분할한 것도 통과 (재량은 나누는 방향으로만 열려 있음).

## 시나리오 E (차단) — 구조 깨짐

**입력**: 인덱스가 `plan/tasks-04-06.md` 를 링크하는데 파일이 없음 / 하위 문서에 task 4개 / task 번호가 1,2,4 로 건너뜀.

**기대 동작**: 각각 G5 / G4 / G5 위반으로 차단.
```

- [ ] **Step 2-d: CLAUDE.md 결합 메모 추가**

**원본** (`CLAUDE.md:1897`):
```markdown
- og-* / auto-* / worktree 계열 / `scripts/preflight.py` / hooks 영향 0
```

**수정 후**:
````markdown
- og-* / auto-* / worktree 계열 / `scripts/preflight.py` / hooks 영향 0
## 구현계획서 코드 강제 + 위키형 분할 결합

계획서가 길어지면 구현 코드 블록을 생략하고 자연어만 남기는 drift 가 실제로 발생했다 (사용자 catch — 코드를 검토하려 했는데 계획서에 코드가 없었다). 원인은 코드 존재를 검사하는 장치가 없었던 것 — 기존 byte-equal 검사는 존재하는 블록의 내용만 보므로 블록이 없으면 0건 매치로 통과한다. `scripts/plan_guard.py` 가 그 빈 자리를 메운다. spec: `docs/features/2026-08-29-구현계획서-코드강제-분할/`.

### 핵심 룰

- **문서 집합 해석은 한 곳에서만** — `plan_guard.resolve_documents()` 가 인덱스 → 하위 문서 집합을 푸는 단일 진입점이다. 소비자가 각자 해석하면 한 곳만 어긋나도 인덱스만 검사하고 통과하는 false-pass 가 난다
- **임계값 10 / 상한 3** — task 10개 이상이면 분할 필수, 하위 문서 하나에 task 최대 3개. 둘 다 결정적 상수 (`SPLIT_THRESHOLD` / `MAX_TASKS_PER_SUBDOC`)
- **재량은 나누는 방향으로만** — 10개 미만의 분할은 허용, 10개 이상의 단일 문서는 차단
- **인덱스 파일 이름 불변** — `<slug>-implementation-plan.md` 그대로. 하위 문서는 `plan/tasks-NN-MM.md` 로, 기존 파일명 정규식에 **일부러 매치되지 않게** 짓는다 (최신 계획서 자동 선택이 하위 문서를 오선택하는 사고 차단)
- **하위 문서에 변경이력 footer 없음** — 모든 entry 는 인덱스로 모인다
- **축약 마커는 주석 형태만 탐지** — 맨몸 `...` 한 줄은 정상 코드와 충돌하므로 제외. 같은 task 의 `**원본**` 블록에 있던 라인은 면제 (원래 파일에 있던 표현)
- **기존 byte-check 모듈 무변경** — `plan_byte_check.py` 는 그대로 두고 wrapper 가 문서별로 호출한다. 그 파일은 구현 / 재정렬 프롬프트 + sub-driven 본문과 atomic 번들로 묶여 있어 건드리면 번들 전체 재검증이 필요하다

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 소비자가 `resolve_documents` 를 안 쓰고 자체 해석 | 그 소비자만 인덱스를 보고 통과 — false-pass 재발 |
| G1 검사 약화 | 코드 없는 계획서가 다시 통과 (이번 사고 그대로 재현) |
| 축약 마커 면제 규칙 삭제 | 원래 파일에 있던 주석이 오탐으로 잡혀 게이트가 막힘 |
| 하위 문서 이름을 `-implementation-plan.md` 접미사로 변경 | 최신 계획서 자동 선택이 하위 문서를 본체로 오선택 |
| 하위 문서에 변경이력 footer 추가 | 이력이 흩어져 감사 흐름이 끊김 + live 판정이 어긋남 |
| 정식 흐름만 수정 (자동 흐름 미동기) | 두 경로의 규약이 갈림 — 자동 흐름 계획서에 코드 생략 잔존 |
| 실행 진입 시에도 강제 검사 추가 | 기존 계획서가 전부 차단 — 소급 비대상 원칙 위반 |

### 회귀 확인

```bash
python3 -c "from scripts.plan_guard import resolve_documents, check_plan, verify_documents_byte_equal; print('OK')"
# expected: OK
```

```bash
grep -c "SPLIT_THRESHOLD = 10" scripts/plan_guard.py
# expected: 1
```

```bash
grep -c "MAX_TASKS_PER_SUBDOC = 3" scripts/plan_guard.py
# expected: 1
```

```bash
grep -lF "plan_guard" skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md | wc -l
# expected: 2
```

```bash
grep -c "plan/tasks-" skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 각 1 이상
```

```bash
test -f skills/js-super-sub-driven/tests/H20-plan-split/README.md && echo OK
# expected: OK
```

```bash
grep -c "분할 계획서 예외 (하위 문서)" skills/change-history/SKILL.md
# expected: 1
```

### 영향 범위

- 스크립트 2 신규 + 1 수정 (추가 전용 — 기존 함수 시그니처·exit code 규약 무변경이라 3 skill 의 사전 검사 명령 동기 불필요), 스킬 본문 8, 커맨드 2, fixture 1, CLAUDE.md
- 보조 에이전트 프롬프트 3종 (`implementer-prompt.md` / `reorder-prompt.md` / `spec-reviewer-prompt.md`) **무변경** — task 전문을 붙여넣는 방식이라 계획서 레이아웃과 무관
- 기존 계획서 소급 적용 없음 — 새 규약은 머지 후 작성되는 계획서부터
- 테스트 코드는 그대로 자연어 `**검증**:` 유지 — 이번 강제화는 구현 코드 전용
- og-* / worktree 계열 / fast-tasks 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
````

- [ ] **Step 3: Commit**

```bash
git add commands/write-plan.md commands/pretty-md.md skills/js-super-sub-driven/tests/H20-plan-split/README.md CLAUDE.md
git commit -m "docs: 분할 산출물 안내 + H20 fixture + 결합 메모"
```

## 2. 위험 코드 지점

- `scripts/plan_guard.py:resolve_documents` — side-effect: 문서 집합 해석의 단일 진입점. 소비자가 자체 해석으로 우회하면 인덱스만 검사하는 false-pass 가 재발한다 (mitigation: 결합 메모의 회귀 패턴 표 + 단위 테스트가 하위 문서 mismatch 를 인덱스 경로로 검출하는지 고정)
- `scripts/plan_guard.py:_ELISION_RES` — side-effect: 축약 마커 패턴이 넓어지면 정상 코드가 오탐으로 걸려 게이트가 막힌다 (mitigation: 주석 형태로 한정 + 원본 면제 규칙 + 맨몸 `...` 비매치, 셋을 단위 테스트로 고정)
- `scripts/preflight.py:code_pretty_check` — side-effect: 공유 사전 검사 helper. 5개 스킬이 인라인으로 호출하므로 시그니처나 exit code 규약이 바뀌면 전부 동기 수정이 필요하다 (mitigation: 이번 변경은 내부 판정만 넓히는 추가 전용 — 시그니처·반환 형식 무변경)
- `skills/js-super-sub-driven/SKILL.md:82` — side-effect: DAG 분석의 task 읽기 경로 변경. 인덱스에 헤더 필드가 없으면 wave 구성이 깨진다 (mitigation: G5 정합성 검사가 인덱스-하위 문서 필드 불일치를 저장 전에 차단)
- `skills/writing-plans/SKILL.md` 저장 게이트 — breaking: 코드 블록 없는 계획서가 저장되지 않는다. 기존 계획서에는 적용되지 않지만 새 계획서 작성 흐름은 확실히 막힌다 (mitigation: 안내 문구가 무엇을 채워야 하는지 항목별로 알려줌, 우회 옵션은 두지 않음 — 그것이 이 피처의 목적)
- 하위 문서 이름 규약 — breaking: 이름이 기존 계획서 파일명 정규식에 매치되면 최신 계획서 자동 선택이 하위 문서를 본체로 오선택한다 (mitigation: `plan/tasks-NN-MM.md` 는 접미사가 달라 매치되지 않음 + 결합 메모에 명시)

## 3. 롤백 전략

- Task 1~2 (스크립트) 롤백: 두 커밋을 되돌리면 검사 모듈이 사라지고 기존 byte-equal 검사만 남는다. 스킬 본문이 이미 새 검사를 부르고 있으면 명령이 실패하므로, 스크립트만 단독 롤백하지 말고 Task 5~6 (검사 호출 교체) 과 함께 되돌린다
- Task 3~11 (스킬 본문) 롤백: 각 커밋이 파일 단위로 독립적이라 개별 되돌리기가 가능하다. 단 Task 9 의 3파일과 Task 10 의 2파일은 같은 규약을 나눠 담으므로 커밋 단위로 통째 되돌린다
- Task 12 롤백: 문서·fixture 만이라 단독 되돌리기가 안전하다
- 전체 롤백: 이 피처의 커밋 범위를 `git revert` 하면 기존 동작으로 완전히 돌아간다. 이미 분할 구조로 쓰인 계획서가 있으면 실행 단계가 하위 문서를 못 읽으므로, 그 계획서는 단일 문서로 합쳐야 한다

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 09:37] [구현계획서-수정]
- **id**: CH-20260829-003
- **이유**: 기술설계 §5 결정 6건을 실행 가능한 task 12개로 분해 (auto-flow). 검사 모듈 신규 → 사전 검사 확장 → 작성 흐름 2곳 → 실행·검증 소비자 6곳 → 문서·fixture 순서
- **무엇이**: 구현계획서-코드강제-분할-implementation-plan.md 전체 (§1 task 1~12 / §2 위험 코드 지점 5건 / §3 롤백 전략)
- **영향범위**: 신규 `scripts/plan_guard.py` + 테스트, `scripts/preflight.py` 추가 전용 수정, 스킬 본문 8 (writing-plans / auto-writing-plans / executing-plans / js-super-sub-driven / verifying-spec + 프롬프트 2 / code-pretty / glossary / change-history), 커맨드 2, fixture H20 신규, CLAUDE.md 결합 메모. 보조 에이전트 프롬프트 3종 무변경
- **연관 항목**: CH-20260829-002
- **검증 결과**: plan_byte_check 통과 (원본 블록 22건 전부 byte-equal). 무맥락 검증자 2개는 사용량 크레딧 소진으로 실패(미수행). 작성 중 자체 발견 1건 — 코드 블록 안 예시 task 헤더가 실제 task 로 세어지는 오탐(이 계획서에서 13 vs 12로 재현)을 Task 1 의 펜스 마스킹으로 해소

### [2026-08-29 09:51] [코드-수정] (batch: tasks 1..12)
- **id**: CH-20260829-004
- **이유**: 계획서가 길어지면 구현 코드를 생략하는 drift 를 결정적 검사로 차단하고, task 10개 이상 계획서를 인덱스 + 하위 문서로 나누는 규약을 도입
- **무엇이**: scripts/plan_guard.py (신규), scripts/tests/test_plan_guard.py (신규), scripts/preflight.py, scripts/tests/test_preflight.py, skills/writing-plans/SKILL.md, skills/auto-writing-plans/SKILL.md, skills/executing-plans/SKILL.md, skills/js-super-sub-driven/SKILL.md, skills/verifying-spec/SKILL.md, skills/verifying-spec/clean-solo-prompt.md, skills/verifying-spec/clean-cross-prompt.md, skills/code-pretty/SKILL.md, skills/glossary/SKILL.md, skills/change-history/SKILL.md, commands/write-plan.md, commands/pretty-md.md, skills/js-super-sub-driven/tests/H20-plan-split/README.md (신규), CLAUDE.md
- **영향범위**: 계획서 작성 흐름(정식 + 자동)에 저장 차단 게이트 신설. 실행·검증 소비자 6곳은 분할·단일 양쪽을 읽는 하위 호환. 보조 에이전트 프롬프트 3종 무변경. 단위 테스트 107 → 110건, 결합 회귀 규칙 145 → 152건
- **위험 카테고리**: side-effect, breaking
- **task별 세부 (12건)**:
  - Task 1: `scripts/plan_guard.py`, `scripts/tests/test_plan_guard.py` — 문서 집합 해석 + G1~G6 검사 (`side-effect`) — commits: `592a02f`
  - Task 2: `scripts/preflight.py`, `scripts/tests/test_preflight.py` — 분할 하위 문서 인지 (`side-effect`) — commits: `33c2f02`
  - Task 3~5: `skills/writing-plans/SKILL.md` — Checklist 5.5 + Plan Split 섹션 + Self-Review 7·8 + 저장 게이트 교체 (`breaking`) — commits: `b7baf50`
  - Task 6: `skills/auto-writing-plans/SKILL.md` — 자동 흐름 mirror (`breaking`) — commits: `a5cae5e`
  - Task 7~8: `skills/executing-plans/SKILL.md`, `skills/js-super-sub-driven/SKILL.md` — 분할 계획서 읽기 (`side-effect`) — commits: `1827e2a`
  - Task 9: `skills/verifying-spec/` 3파일 — 하위 문서를 대상의 일부로 (`none`) — commits: `b03c92b`
  - Task 10~11: `skills/code-pretty/SKILL.md`, `skills/glossary/SKILL.md`, `skills/change-history/SKILL.md` — 보조 산출물 처리 + footer 예외 (`none`) — commits: `65de607`
  - Task 12: `commands/` 2파일, H20 fixture, `CLAUDE.md` — 안내 + 결합 메모 (`none`) — commits: `84bc677`
- **연관 commits**: `8cd80bd..84bc677`
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260829-003
- **실행 중 보정 2건 (메인 직접)**: (1) 펜스 마스킹이 중첩 코드 블록에서 경계를 잘못 잡던 문제 — 정규식 한 방 처리에서 줄 단위 상태 추적으로 교체. 이 계획서 자신이 반례였다. (2) 자동 흐름 Checklist 항목이 Step 헤딩과 어긋난 것 — 보조 에이전트가 범위 밖이라 남긴 지적을 메인이 반영
