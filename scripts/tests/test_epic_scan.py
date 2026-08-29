"""epic_scan 단위 테스트 — 임시 디렉터리 가짜 docs 구조 기반.

검증 시나리오:
1. 진행 중인 큰 작업을 찾는다 (상태 줄 없으면 진행 중으로 본다)
2. 완료 표시된 큰 작업은 후보에서 빠진다
3. 소속 피처를 기획 / 설계 / 계획 / 실행 네 단계로 분류한다
4. 소속 표식이 없는 피처는 별도 목록으로 센다
5. 다른 큰 작업 소속 피처는 목록에 안 들어간다
6. 진행 중인 큰 작업이 없으면 빈 결과를 돌려준다
7. 진행 중인 것이 여럿이면 가장 최근에 고친 쪽을 쓴다
8. 읽을 수 없는 파일이 있어도 죽지 않는다
"""

import os
from pathlib import Path

from scripts.epic_scan import (
    STAGE_DESIGNED,
    STAGE_EXECUTED,
    STAGE_PLANNED,
    STAGE_SCHEDULED,
    STATUS_ACTIVE,
    current_epic,
    epic_status,
    feature_epic,
    feature_stage,
    find_active_epics,
    scan,
)


def _epic(docs: Path, name: str, status: str = STATUS_ACTIVE) -> Path:
    d = docs / "epics" / name
    d.mkdir(parents=True)
    (d / "overview.md").write_text(
        f"# 큰 작업: {name}\n\n> **상태**: {status}\n", encoding="utf-8"
    )
    (d / "carry-over.md").write_text("# 이월 노트\n", encoding="utf-8")
    (d / "forecast.md").write_text("# 예상도\n", encoding="utf-8")
    return d


def _feature(docs: Path, name: str, owner=None, stage=STAGE_PLANNED) -> Path:
    d = docs / "features" / name
    d.mkdir(parents=True)
    head = f"# 요구사항: {name}\n\n"
    if owner is not None:
        head += f"> **큰 작업**: {owner}\n"
    head += "> **다음 단계 안내**: ...\n"
    (d / f"{name}-requirements.md").write_text(head, encoding="utf-8")
    if stage in (STAGE_DESIGNED, STAGE_SCHEDULED, STAGE_EXECUTED):
        (d / f"{name}-tech-design.md").write_text("# 기술설계\n", encoding="utf-8")
    if stage in (STAGE_SCHEDULED, STAGE_EXECUTED):
        body = "# 구현계획서\n\n## 변경이력\n"
        if stage == STAGE_EXECUTED:
            body += "\n### [2026-08-29 10:00] [코드-수정] (batch: tasks 1..3)\n- **id**: CH-1\n"
        (d / f"{name}-implementation-plan.md").write_text(body, encoding="utf-8")
    return d


def test_finds_active_epic(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파")
    assert [p.name for p in find_active_epics(docs)] == ["2026-08-29-알파"]
    assert current_epic(docs).name == "2026-08-29-알파"


def test_status_line_missing_means_active(tmp_path):
    docs = tmp_path / "docs"
    d = docs / "epics" / "2026-08-29-베타"
    d.mkdir(parents=True)
    (d / "overview.md").write_text("# 큰 작업: 베타\n", encoding="utf-8")
    assert epic_status(d / "overview.md") == STATUS_ACTIVE
    assert len(find_active_epics(docs)) == 1


def test_done_epic_excluded(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파", status="완료")
    assert find_active_epics(docs) == []
    assert current_epic(docs) is None


def test_stage_classification(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파")
    _feature(docs, "f1", owner="2026-08-29-알파", stage=STAGE_PLANNED)
    _feature(docs, "f2", owner="2026-08-29-알파", stage=STAGE_DESIGNED)
    _feature(docs, "f3", owner="2026-08-29-알파", stage=STAGE_SCHEDULED)
    _feature(docs, "f4", owner="2026-08-29-알파", stage=STAGE_EXECUTED)

    result = scan(docs)
    stages = {m["name"]: m["stage"] for m in result["members"]}
    assert stages == {
        "f1": STAGE_PLANNED,
        "f2": STAGE_DESIGNED,
        "f3": STAGE_SCHEDULED,
        "f4": STAGE_EXECUTED,
    }


def test_unmarked_features_counted_separately(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파")
    _feature(docs, "mine", owner="2026-08-29-알파")
    _feature(docs, "orphan", owner=None)

    result = scan(docs)
    assert [m["name"] for m in result["members"]] == ["mine"]
    assert result["unmarked"] == ["orphan"]


def test_other_epic_features_excluded(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파")
    _feature(docs, "mine", owner="2026-08-29-알파")
    _feature(docs, "theirs", owner="2026-08-01-감마")

    result = scan(docs)
    assert [m["name"] for m in result["members"]] == ["mine"]
    assert result["unmarked"] == []


def test_no_epic_returns_empty(tmp_path):
    docs = tmp_path / "docs"
    (docs / "features").mkdir(parents=True)
    _feature(docs, "solo", owner=None)

    result = scan(docs)
    assert result["epic"] is None
    assert result["active_count"] == 0
    assert result["members"] == []
    assert result["unmarked"] == []


def test_missing_docs_dir_is_safe(tmp_path):
    result = scan(tmp_path / "nope")
    assert result["epic"] is None


def test_multiple_active_picks_most_recent(tmp_path):
    docs = tmp_path / "docs"
    old = _epic(docs, "2026-08-01-오래된")
    new = _epic(docs, "2026-08-29-최근")
    os.utime(old / "overview.md", (1000, 1000))
    os.utime(new / "overview.md", (2000, 2000))

    assert current_epic(docs).name == "2026-08-29-최근"
    assert scan(docs)["active_count"] == 2


def test_unreadable_file_does_not_crash(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파")
    d = docs / "features" / "broken"
    d.mkdir(parents=True)
    (d / "broken-requirements.md").write_bytes(b"\xff\xfe\x00\x00invalid")

    assert feature_epic(d) is None
    assert feature_stage(d) == STAGE_PLANNED
    assert scan(docs)["unmarked"] == ["broken"]


def test_file_entries_in_features_dir_ignored(tmp_path):
    docs = tmp_path / "docs"
    _epic(docs, "2026-08-29-알파")
    (docs / "features").mkdir(parents=True, exist_ok=True)
    (docs / "features" / "stray.md").write_text("not a folder\n", encoding="utf-8")

    result = scan(docs)
    assert result["members"] == []
    assert result["unmarked"] == []
