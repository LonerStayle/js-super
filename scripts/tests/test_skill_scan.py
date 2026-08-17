"""skill_scan 단위 테스트 — 임시 디렉터리 가짜 홈 구조 기반.

plan 검증 시나리오 8개:
1. 표식 필터 (마커 없는 skill 제외)
2. `.removed-<ts>` 디렉터리 제외
3. 숨김·무거운 폴더 프루닝
4. 세 그룹 분류 + 중복 배제
5. 하위 폴더 cwd 상향 탐지 (홈 자체 제외 포함)
6. 설명 추출 실패 시 "(설명 없음)" 폴백
7. 접근 권한 오류 무시 (죽지 않음)
8. 표식 skill 0개 프로젝트는 다른-프로젝트 목록에서 제외
"""

import json
import os

import pytest

from scripts.skill_scan import scan, find_current_project

MARKER = ".js-super-skill.json"


def make_skill(skills_root, slug, description="테스트 skill", marker=True, created=None,
               frontmatter=True):
    d = skills_root / slug
    d.mkdir(parents=True, exist_ok=True)
    if marker:
        data = {"generated_by": "js-super:new-skill", "scope": "project"}
        if created:
            data["created"] = created
        (d / MARKER).write_text(json.dumps(data), encoding="utf-8")
    if frontmatter:
        body = f"---\ndescription: {description}\n---\n\n# {slug}\n"
    else:
        body = f"# {slug}\n\nfrontmatter 없는 SKILL.md\n"
    (d / "SKILL.md").write_text(body, encoding="utf-8")
    return d


@pytest.fixture
def fake_home(tmp_path):
    home = tmp_path / "home"
    # 글로벌 스코프
    make_skill(home / ".claude" / "skills", "global-skill", "글로벌 skill")
    # 현재 프로젝트 proj-a + 하위 폴더
    make_skill(home / "work" / "proj-a" / ".claude" / "skills", "a-skill", "프로젝트 A skill")
    (home / "work" / "proj-a" / "sub" / "dir").mkdir(parents=True)
    # 다른 프로젝트 proj-b — 마커 있는 것 / 없는 것 / removed / frontmatter 없는 것
    b = home / "work" / "proj-b" / ".claude" / "skills"
    make_skill(b, "b-skill", "프로젝트 B skill", created="2026-08-01T00:00:00")
    make_skill(b, "no-marker", marker=False)
    make_skill(b, "gone.removed-20260801000000")
    make_skill(b, "no-desc", frontmatter=False)
    # 표식 skill 0개 프로젝트 proj-e (마커 없는 skill 만)
    make_skill(home / "work" / "proj-e" / ".claude" / "skills", "plain", marker=False)
    # 숨김 폴더 아래 프로젝트 (프루닝 대상)
    make_skill(home / ".hiddenzone" / "proj-c" / ".claude" / "skills", "c-skill")
    # 무거운 폴더 아래 프로젝트 (프루닝 대상)
    make_skill(home / "node_modules" / "proj-d" / ".claude" / "skills", "d-skill")
    return home


def _other_roots(result):
    return [g["root"] for g in result["other_projects"]]


def test_marker_filter_and_removed_and_desc_fallback(fake_home):
    result = scan(fake_home, fake_home / "work" / "proj-b")
    cur = result["current_project"]
    slugs = [s["slug"] for s in cur["skills"]]
    # 시나리오 1 — 마커 있는 것만
    assert "b-skill" in slugs
    assert "no-marker" not in slugs
    # 시나리오 2 — removed 제외
    assert not any(s.startswith("gone.removed-") for s in slugs)
    # 시나리오 6 — 설명 폴백
    by_slug = {s["slug"]: s for s in cur["skills"]}
    assert by_slug["no-desc"]["description"] == "(설명 없음)"
    # created 는 표식 파일 값에서만
    assert by_slug["b-skill"]["created"] == "2026-08-01T00:00:00"
    assert "created" not in by_slug["no-desc"]


def test_three_groups_and_dedup(fake_home):
    cwd = fake_home / "work" / "proj-a" / "sub" / "dir"
    result = scan(fake_home, cwd)
    # 시나리오 4 — 세 그룹 분류
    assert result["current_project"]["root"] == str((fake_home / "work" / "proj-a").resolve())
    assert [s["slug"] for s in result["current_project"]["skills"]] == ["a-skill"]
    assert [s["slug"] for s in result["global"]["skills"]] == ["global-skill"]
    others = _other_roots(result)
    assert str((fake_home / "work" / "proj-b").resolve()) in [str(r) for r in others]
    # 중복 배제 — 현재 프로젝트·글로벌은 다른 프로젝트 그룹에 없음
    assert str((fake_home / "work" / "proj-a").resolve()) not in [str(r) for r in others]
    assert all(".claude" not in r for r in others)


def test_pruning_hidden_and_heavy(fake_home):
    result = scan(fake_home, fake_home)
    others = _other_roots(result)
    # 시나리오 3 — 숨김·무거운 폴더 아래 프로젝트는 안 잡힘
    assert not any("proj-c" in r for r in others)
    assert not any("proj-d" in r for r in others)


def test_empty_marker_project_excluded(fake_home):
    result = scan(fake_home, fake_home)
    others = _other_roots(result)
    # 시나리오 8 — 표식 skill 0개 프로젝트 제외
    assert not any("proj-e" in r for r in others)


def test_upward_detection(fake_home):
    home = fake_home.resolve()
    # 시나리오 5 — 하위 폴더에서 프로젝트 루트 인식
    found = find_current_project(home / "work" / "proj-a" / "sub" / "dir", home)
    assert found == home / "work" / "proj-a"
    # 홈 자체는 후보에서 제외 (글로벌 스코프)
    assert find_current_project(home, home) is None
    # 프로젝트 밖 cwd → None + scan 결과 root 는 null
    result = scan(fake_home, fake_home / "work")
    assert result["current_project"]["root"] is None
    assert result["current_project"]["skills"] == []


def test_permission_error_ignored(fake_home):
    locked = fake_home / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)
    try:
        # 시나리오 7 — 접근 불가 폴더가 있어도 예외 없이 완주
        result = scan(fake_home, fake_home)
        assert "other_projects" in result
    finally:
        os.chmod(locked, 0o755)
