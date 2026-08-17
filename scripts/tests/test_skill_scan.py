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

적대적 테스트 반영분 (아래 TestHostile) — 크래시·오탐 회귀 방지.
"""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.skill_scan import (
    MAX_DESCRIPTION,
    find_current_project,
    read_description,
    scan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "skill_scan.py"

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


# ---------------------------------------------------------------------------
# 적대적 테스트 반영분 — 아래는 실제로 크래시·오탐을 일으켰던 입력들이다.
# ---------------------------------------------------------------------------


def _bare_skill(skills_root, slug, marker_text='{}', skill_bytes=None):
    """마커·SKILL.md 를 원문 그대로 심는다 (깨진 입력 재현용)."""
    d = skills_root / slug
    d.mkdir(parents=True, exist_ok=True)
    if marker_text is not None:
        (d / MARKER).write_text(marker_text, encoding="utf-8")
    if skill_bytes is not None:
        (d / "SKILL.md").write_bytes(skill_bytes)
    return d


@pytest.mark.parametrize("marker_text", ["[]", "null", "12345", '"hello"', "true"])
def test_marker_non_dict_json_does_not_crash(tmp_path, marker_text):
    """유효한 JSON 이지만 dict 가 아닌 마커 — 예전엔 AttributeError 로 죽었다."""
    home = tmp_path / "home"
    _bare_skill(home / "proj" / ".claude" / "skills", "s", marker_text,
                b"---\ndescription: d\n---\n")
    result = scan(home, home / "proj")
    skills = result["current_project"]["skills"]
    assert [s["slug"] for s in skills] == ["s"]
    assert "created" not in skills[0]


def test_non_utf8_skill_md_does_not_crash(tmp_path):
    """비-UTF8 SKILL.md — 예전엔 UnicodeDecodeError 로 스캔 전체가 날아갔다."""
    home = tmp_path / "home"
    _bare_skill(home / "proj" / ".claude" / "skills", "s", "{}", b"\xff\xfe bad")
    result = scan(home, home / "proj")
    assert [s["slug"] for s in result["current_project"]["skills"]] == ["s"]
    assert result["current_project"]["skills"][0]["description"] == "(설명 없음)"


def test_fifo_skill_md_does_not_block(tmp_path):
    """SKILL.md 가 named pipe 여도 즉시 반환해야 한다 (예전엔 영구 블록)."""
    home = tmp_path / "home"
    d = _bare_skill(home / "proj" / ".claude" / "skills", "s", "{}")
    os.mkfifo(d / "SKILL.md")
    signal.alarm(5)
    try:
        assert read_description(d) == "(설명 없음)"
    finally:
        signal.alarm(0)


def test_description_keeps_inner_quotes(tmp_path):
    """문장 안 따옴표가 잘리면 안 된다."""
    home = tmp_path / "home"
    _bare_skill(home / "proj" / ".claude" / "skills", "s", "{}",
                '---\ndescription: 사용자가 "안녕" 이라고 할 때\n---\n'.encode())
    result = scan(home, home / "proj")
    assert result["current_project"]["skills"][0]["description"] == '사용자가 "안녕" 이라고 할 때'


def test_description_strips_matching_quotes(tmp_path):
    """양끝이 짝을 이루는 인용부호는 벗긴다."""
    home = tmp_path / "home"
    _bare_skill(home / "proj" / ".claude" / "skills", "s", "{}",
                '---\ndescription: "따옴표로 감싼 설명"\n---\n'.encode())
    result = scan(home, home / "proj")
    assert result["current_project"]["skills"][0]["description"] == "따옴표로 감싼 설명"


def test_bom_frontmatter_is_read(tmp_path):
    """BOM 이 붙어도 frontmatter 를 읽어야 한다."""
    home = tmp_path / "home"
    _bare_skill(home / "proj" / ".claude" / "skills", "s", "{}",
                "﻿---\ndescription: BOM 붙은 설명\n---\n".encode("utf-8"))
    result = scan(home, home / "proj")
    assert result["current_project"]["skills"][0]["description"] == "BOM 붙은 설명"


def test_block_scalar_description_falls_back(tmp_path):
    """YAML 블록 스칼라는 한 줄 요약이 아니므로 폴백한다 (예전엔 '|' 를 그대로 실었다)."""
    home = tmp_path / "home"
    _bare_skill(home / "proj" / ".claude" / "skills", "s", "{}",
                "---\ndescription: |\n  첫 줄\n  둘째 줄\n---\n".encode())
    result = scan(home, home / "proj")
    assert result["current_project"]["skills"][0]["description"] == "(설명 없음)"


def test_description_length_capped_and_nul_stripped(tmp_path):
    """지나치게 긴 설명은 자르고, NUL 바이트는 제거한다."""
    home = tmp_path / "home"
    skills = home / "proj" / ".claude" / "skills"
    _bare_skill(skills, "long", "{}", ("---\ndescription: " + "가" * 50000 + "\n---\n").encode())
    _bare_skill(skills, "nul", "{}", "---\ndescription: has\x00nul\n---\n".encode())
    by_slug = {s["slug"]: s for s in scan(home, home / "proj")["current_project"]["skills"]}
    assert len(by_slug["long"]["description"]) <= MAX_DESCRIPTION + 1
    assert "\x00" not in by_slug["nul"]["description"]


def test_symlinked_claude_dir_is_not_followed(tmp_path):
    """`.claude` 가 심링크면 따라가지 않는다 — 홈 밖 내용이 새어 들어오면 안 된다."""
    home = tmp_path / "home"
    (home / "proj").mkdir(parents=True)
    outside = tmp_path / "outside"
    make_skill(outside / "skills", "outside-skill", "홈 밖 skill")
    (home / "proj" / ".claude").symlink_to(outside)
    result = scan(home, home / "proj")
    assert result["current_project"]["root"] is None
    assert result["other_projects"] == []


def test_symlinked_skill_dir_is_skipped(tmp_path):
    """skills 안의 별칭 심링크는 중복 항목을 만들지 않는다."""
    home = tmp_path / "home"
    skills = home / "proj" / ".claude" / "skills"
    make_skill(skills, "s1", "원본 skill")
    (skills / "s1_alias").symlink_to(skills / "s1")
    result = scan(home, home / "proj")
    assert [s["slug"] for s in result["current_project"]["skills"]] == ["s1"]


def test_cwd_outside_home_does_not_climb_above_home(tmp_path):
    """홈 밖 cwd 에서 홈의 조상까지 거슬러 올라가면 안 된다."""
    anc = tmp_path / "anc"
    make_skill(anc / ".claude" / "skills", "조상스킬")
    home = anc / "home"
    make_skill(home / ".claude" / "skills", "g1")
    deep = anc / "elsewhere" / "deep"
    deep.mkdir(parents=True)
    assert find_current_project(deep.resolve(), home.resolve()) is None


def test_project_named_like_prune_entry_is_found(tmp_path):
    """`Public/` 이나 `venv` 같은 이름의 실제 프로젝트가 사라지면 안 된다."""
    home = tmp_path / "home"
    (home / ".claude" / "skills").mkdir(parents=True)
    for rel in ("Public/myproj", "venv", "정상"):
        make_skill(home / rel / ".claude" / "skills", "s", "설명")
    roots = [g["root"] for g in scan(home, home)["other_projects"]]
    assert any(r.endswith("Public/myproj") for r in roots)
    assert any(r.endswith("/venv") for r in roots)
    assert any(r.endswith("정상") for r in roots)


def test_home_top_media_folders_are_pruned(tmp_path):
    """홈 최상위의 시스템·미디어 폴더는 건너뛴다 (스캔 시간 보호)."""
    home = tmp_path / "home"
    (home / ".claude" / "skills").mkdir(parents=True)
    make_skill(home / "Library" / "proj" / ".claude" / "skills", "lib-skill")
    make_skill(home / "Pictures" / "proj" / ".claude" / "skills", "pic-skill")
    make_skill(home / "code" / "Library" / ".claude" / "skills", "nested-library-proj")
    roots = [g["root"] for g in scan(home, home)["other_projects"]]
    assert not any("/Library/proj" in r for r in roots)
    assert not any("/Pictures/" in r for r in roots)
    # 홈 최상위가 아닌 곳의 같은 이름은 살아남는다
    assert any(r.endswith("code/Library") for r in roots)


def test_cli_reports_error_as_json_without_traceback(tmp_path):
    """예기치 못한 실패 시 트레이스백 대신 JSON 오류를 낸다."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--home", str(tmp_path / "no-such-home"),
         "--cwd", str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert "Traceback" not in proc.stderr
    payload = json.loads(proc.stdout)
    assert "current_project" in payload
