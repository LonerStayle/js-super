"""Deterministic pre-flight checks for js-super-sub-driven skills.

Replaces LLM inference in skill pre-flight steps with bash-callable Python
helpers. Each function returns a PreflightResult; callers parse exit code
0 (ok) / 1 (fail with reason on stderr or stdout).
"""
import re
from pathlib import Path
from typing import NamedTuple


class PreflightResult(NamedTuple):
    ok: bool
    reason: str
    human_reason: str = ""  # v1.1.15+ optional 한국어 1줄 설명. backward compat: default 빈 문자열.


_FEATURE_MD_PATTERN = re.compile(
    r".*-(requirements|tech-design|implementation-plan)\.md$"
)
_PLAN_MD_PATTERN = re.compile(r".*-implementation-plan\.md$")
_CHANGELOG_ENTRY = re.compile(r"^### \[", re.MULTILINE)
_FRONTMATTER_COMMIT_POLICY = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL
)
_COMMIT_POLICY_LINE = re.compile(
    r"^commit_policy:\s*(per-task|single|none)\s*$", re.MULTILINE
)


def _has_changelog_entries(text: str) -> bool:
    if "## 변경이력" not in text:
        return False
    footer = text.rsplit("## 변경이력", 1)[1]
    return _CHANGELOG_ENTRY.search(footer) is not None


def _read_commit_policy(text: str) -> str:
    m = _FRONTMATTER_COMMIT_POLICY.match(text)
    if not m:
        return "per-task"
    line = _COMMIT_POLICY_LINE.search(m.group(1))
    return line.group(1) if line else "per-task"


def docs_pretty_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(
            False,
            f"file not found: {file_path}",
            f"대상 파일이 존재하지 않습니다: {file_path}",
        )
    if not _FEATURE_MD_PATTERN.match(str(file_path)):
        return PreflightResult(
            False,
            "filename doesn't match feature MD pattern",
            "파일명이 feature MD 패턴 (-requirements.md / -tech-design.md / -implementation-plan.md) 과 일치하지 않습니다",
        )
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(
            False,
            "변경이력 footer not empty (doc is live)",
            "이미 변경이력 entry 가 존재합니다 (live doc). docs-pretty 는 최초 생성 단계에서만 발화합니다",
        )
    return PreflightResult(True, "ok", "정상")


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


def execute_plan_mode_check(plan_path: Path) -> PreflightResult:
    if not plan_path.exists():
        hint = ""
        if feature_depth(plan_path.parent) == 2:
            hint = (
                " — 이 피처는 2개 문서로 확정된 트랙입니다."
                " 구현이 필요해졌다면 /write-plan 으로 승격하세요."
            )
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"구현계획서를 찾을 수 없습니다: {plan_path}{hint}",
        )
    text = plan_path.read_text(encoding="utf-8")
    policy = _read_commit_policy(text)
    return PreflightResult(True, f"commit_policy={policy}", f"정상 (commit_policy: {policy})")


def subagent_task_entry_check(plan_path: Path) -> PreflightResult:
    if not plan_path.exists():
        hint = ""
        if feature_depth(plan_path.parent) == 2:
            hint = (
                " — 이 피처는 2개 문서로 확정된 트랙입니다."
                " 구현이 필요해졌다면 /write-plan 으로 승격하세요."
            )
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"플랜 파일이 존재하지 않습니다: {plan_path}{hint}",
        )
    text = plan_path.read_text(encoding="utf-8")
    policy = _read_commit_policy(text)
    if policy != "per-task":
        return PreflightResult(
            False,
            f"js-super-sub-driven requires commit_policy: per-task (got {policy})",
            f"js-super-sub-driven 는 commit_policy: per-task 를 요구합니다 (현재: {policy})",
        )
    return PreflightResult(True, "ok", "정상")


_DEPTH_LINE = re.compile(r"^depth:\s*([23])\s*$", re.MULTILINE)


def feature_depth(feature_dir: Path) -> int:
    """피처 폴더의 산출물 깊이 (산출물 깊이 선택 기능).

    *-tech-design.md 의 frontmatter 에 depth: 2 가 명시된 경우에만 2 (2-doc
    확정 트랙). 필드 부재 / depth: 3 / 파일 부재 / 파싱 실패는 전부 3 (기존
    3-doc 기본 트랙). 판독 규칙 엄격 — 안전한 방향(3)으로 fallback.
    """
    if not feature_dir.exists():
        return 3
    for md in sorted(feature_dir.glob("*-tech-design.md")):
        m = _FRONTMATTER_COMMIT_POLICY.match(md.read_text(encoding="utf-8"))
        if not m:
            continue
        line = _DEPTH_LINE.search(m.group(1))
        if line and line.group(1) == "2":
            return 2
    return 3
