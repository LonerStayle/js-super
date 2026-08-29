"""큰 작업(에픽) 폴더와 소속 피처를 훑어 진행 상태를 계산한다.

표준 라이브러리만 쓰고 어떤 파일도 고치지 않는다. 진행 상태를 파일에
저장해두지 않고 매번 세는 것이 이 모듈의 존재 이유다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

EPICS_DIRNAME = "epics"
FEATURES_DIRNAME = "features"
OVERVIEW_NAME = "overview.md"
CARRY_OVER_NAME = "carry-over.md"
FORECAST_NAME = "forecast.md"

STATUS_ACTIVE = "진행 중"
STATUS_DONE = "완료"

STAGE_PLANNED = "기획"
STAGE_DESIGNED = "설계"
STAGE_SCHEDULED = "계획"
STAGE_EXECUTED = "실행"

_STATUS_RE = re.compile(r"^>\s*\*\*상태\*\*:\s*(.+?)\s*$", re.MULTILINE)
_EPIC_RE = re.compile(r"^>\s*\*\*큰 작업\*\*:\s*(.+?)\s*$", re.MULTILINE)
_CODE_ENTRY_RE = re.compile(r"^###\s*\[[^\]]*\]\s*\[코드-수정\]", re.MULTILINE)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def epic_status(overview_path: Path) -> str:
    """큰 그림 문서의 상태 줄을 읽는다. 줄이 없으면 진행 중으로 본다."""
    match = _STATUS_RE.search(_read(overview_path))
    return match.group(1).strip() if match else STATUS_ACTIVE


def find_active_epics(docs_dir: Path) -> list[Path]:
    """진행 중인 큰 작업 폴더를 이름 순으로 모은다."""
    epics_dir = docs_dir / EPICS_DIRNAME
    if not epics_dir.is_dir():
        return []
    found = []
    for child in sorted(epics_dir.iterdir()):
        overview = child / OVERVIEW_NAME
        if child.is_dir() and overview.is_file():
            if epic_status(overview) == STATUS_ACTIVE:
                found.append(child)
    return found


def current_epic(docs_dir: Path) -> Optional[Path]:
    """진행 중인 것이 여럿이면 큰 그림을 가장 최근에 고친 쪽을 쓴다."""
    actives = find_active_epics(docs_dir)
    if not actives:
        return None
    return max(actives, key=lambda d: (d / OVERVIEW_NAME).stat().st_mtime)


def feature_epic(feature_dir: Path) -> Optional[str]:
    """피처 요구사항 문서 머리의 소속 표식을 읽는다."""
    for md in sorted(feature_dir.glob("*-requirements.md")):
        match = _EPIC_RE.search(_read(md))
        if match:
            return match.group(1).strip()
    return None


def feature_stage(feature_dir: Path) -> str:
    """폴더에 있는 산출물로 어느 단계까지 왔는지 판정한다."""
    plans = sorted(feature_dir.glob("*-implementation-plan.md"))
    designs = sorted(feature_dir.glob("*-tech-design.md"))
    for doc in plans + designs:
        if _CODE_ENTRY_RE.search(_read(doc)):
            return STAGE_EXECUTED
    if plans:
        return STAGE_SCHEDULED
    if designs:
        return STAGE_DESIGNED
    return STAGE_PLANNED


def collect_features(docs_dir: Path, epic_name: str) -> dict:
    """소속 피처와 표식 없는 피처를 갈라 모은다."""
    features_dir = docs_dir / FEATURES_DIRNAME
    members: list[dict] = []
    unmarked: list[str] = []
    if not features_dir.is_dir():
        return {"members": members, "unmarked": unmarked}
    for child in sorted(features_dir.iterdir()):
        if not child.is_dir():
            continue
        owner = feature_epic(child)
        if owner is None:
            unmarked.append(child.name)
        elif owner == epic_name:
            members.append({"name": child.name, "stage": feature_stage(child)})
    return {"members": members, "unmarked": unmarked}


def scan(docs_dir: Path) -> dict:
    """진행 중인 큰 작업 하나와 그 소속 피처들의 현재 상태를 돌려준다."""
    epic = current_epic(docs_dir)
    if epic is None:
        return {
            "epic": None,
            "epic_path": None,
            "active_count": 0,
            "members": [],
            "unmarked": [],
        }
    collected = collect_features(docs_dir, epic.name)
    return {
        "epic": epic.name,
        "epic_path": str(epic),
        "active_count": len(find_active_epics(docs_dir)),
        "members": collected["members"],
        "unmarked": collected["unmarked"],
    }


def main(argv: list[str]) -> int:
    docs_dir = Path(argv[1]) if len(argv) > 1 else Path("docs")
    print(json.dumps(scan(docs_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
