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
_FENCE_LINE_RE = re.compile(r"^\s*(`{3,})")
_DETAIL_LINK_RE = re.compile(r"^\*\*상세\*\*:\s*(\S+)\s*$", re.MULTILINE)
_FILES_LINE_RE = re.compile(r"^-\s*(Create|Modify|Test):\s*`([^`]+)`", re.MULTILINE)
_MODEL_RE = re.compile(r"^\*\*Model\*\*:\s*(\S+)\s*$", re.MULTILINE)
_VERIFY_RE = re.compile(r"^\*\*검증\*\*:\s*(.+?)\s*$", re.MULTILINE)
_ORIGINAL_RE = re.compile(r"\*\*원본\*\*\s*\(")
_MODIFIED_RE = re.compile(r"\*\*수정 후\*\*")
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n(.*?)```", re.DOTALL)

# 축약 마커: 주석 기호 뒤에 생략을 뜻하는 표현이 오는 라인만 잡는다.
# 맨몸 "..." 한 줄은 정상 코드(Python Ellipsis stub 등)와 충돌하므로 제외.
# ⚠️ RISK(side-effect): 패턴을 넓히면 정상 코드가 오탐으로 걸려 저장 게이트가 막힌다 — 원본 면제 규칙과 함께 유지 — by 구현계획서-코드강제-분할 task 1
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


# ⚠️ RISK(side-effect): 문서 집합 해석의 단일 진입점 — 소비자가 자체 해석으로 우회하면 인덱스만 검사하는 false-pass 재발 — by 구현계획서-코드강제-분할 task 1
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

    한 줄씩 훑으며 펜스 상태를 따라간다. 정규식 한 방으로 처리하면 예시를
    감싼 바깥 펜스가 예시 안쪽 펜스에서 닫혀버려 마스킹 경계가 어긋난다 —
    계획서가 코드 블록 안에 코드 블록을 싣는 일이 실제로 흔하다. 여는 펜스와
    같거나 더 긴 백틱만 닫는 것으로 본다 (CommonMark 규칙).
    """
    out: List[str] = []
    fence: Optional[str] = None
    for line in text.splitlines(keepends=True):
        m = _FENCE_LINE_RE.match(line)
        marker = m.group(1) if m else None
        if fence is None:
            if marker:
                fence = marker
                out.append(_blank_line(line))
            else:
                out.append(line)
        else:
            if marker and len(marker) >= len(fence):
                fence = None
            out.append(_blank_line(line))
    return "".join(out)


def _blank_line(line: str) -> str:
    return "".join("\n" if c == "\n" else " " for c in line)


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
