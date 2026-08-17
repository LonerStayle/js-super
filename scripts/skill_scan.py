"""js-super skill 홈 전체 스캔 helper.

`/list-skills` 커맨드가 호출한다. 홈 디렉터리 아래의 `.claude/skills/` 를 찾아
출처 표식(`.js-super-skill.json`)이 있는 skill 만 세 그룹(현재 프로젝트 / 글로벌 /
다른 프로젝트)으로 분류해 JSON 으로 출력한다. 읽기 전용 — 어떤 파일도 쓰지 않는다.

표준 라이브러리만 사용한다. 사용자 프로젝트에는 이 저장소의 가상환경이 없어
시스템 `python3` 로 어디서든 실행돼야 한다.

남의 디렉터리를 훑는 도구라 어떤 입력에도 죽지 않는 것이 요구사항이다. 깨진 파일
하나가 스캔 전체를 날리면 안 된다 — 읽기 실패는 전부 그 항목만 건너뛰거나 폴백한다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MARKER_NAME = ".js-super-skill.json"
# 14자리 = YYYYMMDDHHMMSS (/remove-skill 의 safe-rename 타임스탬프 형식)
REMOVED_RE = re.compile(r"\.removed-\d{14}$")
NO_DESCRIPTION = "(설명 없음)"
# 설명 한 줄이 컨텍스트를 잡아먹지 않게 자른다
MAX_DESCRIPTION = 200
# 마커 파일이 아무리 커도 이만큼만 읽는다
MAX_MARKER_BYTES = 64 * 1024

# 어느 깊이에서든 내려가지 않는 이름 — 빌드 산출물과 패키지 캐시.
# 실제 프로젝트가 이 이름을 쓰는 경우는 사실상 없다.
PRUNE_ANYWHERE = {
    "node_modules",
    "site-packages",
    "__pycache__",
    "Pods",
    "DerivedData",
}

# 홈 **최상위에서만** 건너뛰는 이름 — macOS 표준 폴더.
# 이 이름을 깊은 곳에서 프로젝트 이름으로 쓰는 경우는 있으므로 최상위로 한정한다.
PRUNE_AT_HOME_TOP = {
    "Library",
    "Applications",
    "Music",
    "Movies",
    "Pictures",
}


def _read_text(path: Path, limit: int | None = None):
    """일반 파일일 때만 UTF-8(BOM 허용)로 읽는다. 아니거나 실패하면 None.

    `is_file()` 게이트가 named pipe 를 걸러낸다 — 없으면 writer 를 기다리며
    영구히 멈춘다. 인코딩이 깨진 파일은 대체 문자로 읽어 넘긴다.
    """
    try:
        if not path.is_file():
            return None
        if limit is not None and path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def _clean_description(value: str):
    """frontmatter 에서 뽑은 값을 표시용 한 줄로 다듬는다. 못 쓰면 None."""
    value = value.replace("\x00", "").strip()
    if not value:
        return None
    # YAML 블록 스칼라(`|`, `>`)는 다음 줄부터가 본문이라 한 줄 요약이 아니다
    if value[0] in "|>":
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    if len(value) > MAX_DESCRIPTION:
        value = value[:MAX_DESCRIPTION].rstrip() + "…"
    return value or None


def read_description(skill_dir: Path) -> str:
    """SKILL.md frontmatter 의 description 1줄. 실패하면 '(설명 없음)'."""
    text = _read_text(skill_dir / "SKILL.md")
    if text is None:
        return NO_DESCRIPTION
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return NO_DESCRIPTION
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            cleaned = _clean_description(line[len("description:"):])
            return cleaned if cleaned else NO_DESCRIPTION
    return NO_DESCRIPTION


def read_created(skill_dir: Path):
    """출처 표식의 created 값. 없거나 못 읽으면 None (파일시스템 시각은 쓰지 않는다)."""
    text = _read_text(skill_dir / MARKER_NAME, limit=MAX_MARKER_BYTES)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    # 유효한 JSON 이어도 dict 가 아닐 수 있다 (배열 / null / 숫자 / 문자열)
    if not isinstance(data, dict):
        return None
    created = data.get("created")
    return created if isinstance(created, str) else None


def _is_real_dir(path: Path) -> bool:
    """심링크를 거치지 않는 실제 디렉터리일 때만 True.

    심링크를 따라가면 홈 밖 내용이 홈 안 skill 로 보고되고, 같은 skill 이
    별칭 때문에 두 번 나온다. 마지막 요소뿐 아니라 경로 중간에 낀 심링크도
    걸러야 해서 실제 위치와 표기 경로를 대조한다.
    """
    try:
        if not path.is_dir():
            return False
        return os.path.realpath(path) == os.path.abspath(path)
    except OSError:
        return False


def collect_skills(skills_root: Path) -> list:
    """한 `.claude/skills/` 아래에서 출처 표식 있는 skill 항목만 모은다."""
    entries = []
    try:
        children = sorted(skills_root.iterdir(), key=lambda p: p.name)
    except OSError:
        return entries
    for child in children:
        try:
            if not _is_real_dir(child) or REMOVED_RE.search(child.name):
                continue
            if not (child / MARKER_NAME).is_file():
                continue
        except OSError:
            continue
        entry = {
            "slug": child.name,
            "path": str(child),
            "description": read_description(child),
        }
        created = read_created(child)
        if created is not None:
            entry["created"] = created
        entries.append(entry)
    return entries


def _skills_dir(root: Path) -> Path:
    return root / ".claude" / "skills"


def find_current_project(cwd: Path, home: Path):
    """cwd 에서 위로 올라가며 `.claude/skills` 를 가진 첫 디렉터리.

    홈 자체와 홈의 조상은 후보에서 뺀다. 홈의 것은 글로벌 스코프이고, 홈보다
    위쪽은 스캔 범위 밖이라 그곳을 '현재 프로젝트'로 부르면 틀린 안내가 된다.
    """
    blocked = {home, *home.parents}
    for cand in [cwd, *cwd.parents]:
        if cand in blocked:
            return None
        if _is_real_dir(_skills_dir(cand)):
            return cand
    return None


def scan_home_projects(home: Path) -> list:
    """홈 아래 프로젝트 루트(`.claude/skills` 보유) 목록.

    숨김 디렉터리와 프루닝 목록은 내려가지 않는다. `.claude` 는 프루닝 전에
    매치한다 (숨김이지만 찾는 대상). 접근 오류는 os.walk 기본 동작으로 무시된다.
    """
    roots = []
    for dirpath, dirnames, _filenames in os.walk(home, topdown=True, followlinks=False):
        current = Path(dirpath)
        # 홈 자체의 `.claude` 는 글로벌 스코프라 프로젝트로 치지 않는다
        if ".claude" in dirnames and current != home:
            if _is_real_dir(_skills_dir(current)):
                roots.append(current)
        pruned = PRUNE_ANYWHERE | (PRUNE_AT_HOME_TOP if current == home else set())
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in pruned
        ]
    return roots


def scan(home: Path, cwd: Path) -> dict:
    """세 그룹(current_project / global / other_projects) 분류 결과."""
    home = home.resolve()
    cwd = cwd.resolve()
    current_root = find_current_project(cwd, home)
    global_root = _skills_dir(home)

    others = []
    for root in scan_home_projects(home):
        if current_root is not None and root.resolve() == current_root:
            continue
        skills = collect_skills(_skills_dir(root))
        if not skills:
            # 표식 있는 skill 이 하나도 없는 프로젝트는 목록에 내지 않는다 (노이즈 방지)
            continue
        others.append({"root": str(root), "skills": skills})
    others.sort(key=lambda g: g["root"])

    return {
        "current_project": {
            "root": str(current_root) if current_root else None,
            "skills": collect_skills(_skills_dir(current_root)) if current_root else [],
        },
        "global": {
            "root": str(global_root),
            "skills": collect_skills(global_root),
        },
        "other_projects": others,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="js-super skill 홈 전체 스캔 (읽기 전용)")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        payload = scan(args.home, args.cwd)
    except Exception as exc:  # noqa: BLE001 — 트레이스백 대신 JSON 오류로 알린다
        payload = {
            "current_project": {"root": None, "skills": []},
            "global": {"root": None, "skills": []},
            "other_projects": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
