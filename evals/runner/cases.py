"""케이스 파일을 읽는다.

형식은 '마크다운 앞머리 YAML + --- 아래 원문 본문' 이다 (설계서 D3).
본문은 기존 fixture README 를 그대로 복사한 것이라 파서가 건드리지 않는다.
사람이 계속 읽는 문서로 남아야 갱신될 확률이 유지된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REQUIRED = ("id", "title", "status", "layer", "covers", "expect")
VALID_STATUS = {"active", "stale", "wip", "blocked"}
VALID_LAYER = {"A", "B", "C", "D"}


class CaseError(ValueError):
    """케이스 파일이 형식에 안 맞을 때."""


@dataclass
class Case:
    path: Path
    meta: dict
    body: str

    id: str = ""
    title: str = ""
    status: str = "active"
    layer: list = field(default_factory=list)
    covers: list = field(default_factory=list)
    expect: list = field(default_factory=list)

    def __post_init__(self) -> None:
        for key in REQUIRED:
            setattr(self, key, self.meta[key])

    @property
    def needs_claude(self) -> bool:
        """run 이 있으면 실제 Claude 를 띄우는 케이스다."""
        return "run" in self.meta

    @property
    def danger(self) -> str:
        return str(self.meta.get("danger", "-"))

    @property
    def priority(self) -> int:
        return int(self.meta.get("priority", 50))


def load_case(path: Path) -> Case | None:
    """케이스 하나를 읽는다. 앞머리가 없으면 None."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None

    rest = text[4:]
    raw_meta, separator, body = rest.partition("\n---\n")
    if not separator:
        raise CaseError(f"{path.name}: 앞머리가 닫히지 않음 ({path})")

    try:
        meta = yaml.safe_load(raw_meta) or {}
    except yaml.YAMLError as exc:
        raise CaseError(f"{path.name}: 앞머리 YAML 오류 — {exc} ({path})") from exc

    missing = [key for key in REQUIRED if key not in meta]
    if missing:
        raise CaseError(f"{path.name}: 필수 항목 누락 — {', '.join(missing)} ({path})")
    if meta["status"] not in VALID_STATUS:
        raise CaseError(f"{path.name}: 모르는 status — {meta['status']} ({path})")

    bad_layer = [item for item in meta["layer"] if item not in VALID_LAYER]
    if bad_layer:
        raise CaseError(f"{path.name}: 모르는 layer — {', '.join(bad_layer)} ({path})")

    return Case(path=path, meta=meta, body=body)


def load_all(root: Path) -> tuple[list[Case], list[str]]:
    """cases/ 아래를 전부 읽는다. (케이스 목록, 오류 목록)

    오류를 예외로 던지지 않고 모아서 돌려준다. 한 파일이 깨졌다고
    나머지를 못 읽으면 검사 단계가 무의미해진다.
    """
    cases: list[Case] = []
    errors: list[str] = []
    if not root.exists():
        return cases, errors

    for path in sorted(root.rglob("*.md")):
        try:
            case = load_case(path)
        except CaseError as exc:
            errors.append(str(exc))
            continue
        if case is not None:
            cases.append(case)

    seen: dict[str, Path] = {}
    for case in cases:
        if case.id in seen:
            errors.append(f"{case.id}: 같은 id 가 둘 — {seen[case.id]} / {case.path}")
        seen[case.id] = case.path

    return cases, errors
