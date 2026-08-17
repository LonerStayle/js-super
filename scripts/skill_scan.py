"""js-super skill 홈 전체 스캔 helper.

`/list-skills` 커맨드가 호출한다. 홈 디렉터리 아래의 `.claude/skills/` 를 찾아
출처 표식(`.js-super-skill.json`)이 있는 skill 만 세 그룹(현재 프로젝트 / 글로벌 /
다른 프로젝트)으로 분류해 JSON 으로 출력한다. 읽기 전용 — 어떤 파일도 쓰지 않는다.

표준 라이브러리만 사용한다. 사용자 프로젝트에는 이 저장소의 가상환경이 없어
시스템 `python3` 로 어디서든 실행돼야 한다.
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

# 홈 스캔에서 내려가지 않는 디렉터리 이름.
# 숨김 디렉터리(이름이 "." 시작)는 이름 규칙으로 별도 프루닝된다.
PRUNE_DIR_NAMES = {
    "Library",
    "Applications",
    "node_modules",
    "site-packages",
    "__pycache__",
    "venv",
    "Music",
    "Movies",
    "Pictures",
    "Public",
}


def read_description(skill_dir: Path) -> str:
    """SKILL.md frontmatter 의 description 1줄. 실패 시 '(설명 없음)'."""
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return "(설명 없음)"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "(설명 없음)"
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            value = line[len("description:"):].strip().strip("\"'")
            return value if value else "(설명 없음)"
    return "(설명 없음)"


def read_created(skill_dir: Path):
    """출처 표식의 created 값. 없거나 못 읽으면 None (파일시스템 시각은 쓰지 않는다)."""
    try:
        data = json.loads((skill_dir / MARKER_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    created = data.get("created")
    return created if isinstance(created, str) else None


def collect_skills(skills_root: Path) -> list:
    """한 `.claude/skills/` 아래에서 출처 표식 있는 skill 항목만 모은다."""
    entries = []
    try:
        children = sorted(skills_root.iterdir(), key=lambda p: p.name)
    except OSError:
        return entries
    for child in children:
        try:
            if not child.is_dir() or REMOVED_RE.search(child.name):
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


def find_current_project(cwd: Path, home: Path):
    """cwd 에서 위로 올라가며 `.claude/skills` 를 가진 첫 디렉터리 (홈 자체는 제외)."""
    for cand in [cwd, *cwd.parents]:
        if cand == home:
            return None
        try:
            if (cand / ".claude" / "skills").is_dir():
                return cand
        except OSError:
            continue
    return None


# ⚠️ RISK(side-effect): 홈 전체 순회 — 프루닝 상수를 줄이면 보호 폴더 접근·스캔 시간이 급증 — by 스킬목록-전체프로젝트조회
def scan_home_projects(home: Path) -> list:
    """홈 아래 프로젝트 루트(`.claude/skills` 보유) 목록.

    숨김 디렉터리와 PRUNE_DIR_NAMES 는 내려가지 않는다. `.claude` 는 프루닝 전에
    매치한다 (숨김이지만 찾는 대상). 접근 오류는 os.walk 기본 동작으로 무시된다.
    """
    roots = []
    for dirpath, dirnames, _filenames in os.walk(home, topdown=True, followlinks=False):
        current = Path(dirpath)
        # 홈 자체의 `.claude` 는 글로벌 스코프라 프로젝트로 치지 않는다
        if ".claude" in dirnames and current != home:
            try:
                if (current / ".claude" / "skills").is_dir():
                    roots.append(current)
            except OSError:
                pass
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in PRUNE_DIR_NAMES
        ]
    return roots


def scan(home: Path, cwd: Path) -> dict:
    """세 그룹(current_project / global / other_projects) 분류 결과."""
    home = home.resolve()
    cwd = cwd.resolve()
    current_root = find_current_project(cwd, home)
    global_root = home / ".claude" / "skills"

    others = []
    for root in scan_home_projects(home):
        if current_root is not None and root.resolve() == current_root:
            continue
        skills = collect_skills(root / ".claude" / "skills")
        if not skills:
            # 표식 있는 skill 이 하나도 없는 프로젝트는 목록에 내지 않는다 (노이즈 방지)
            continue
        others.append({"root": str(root), "skills": skills})
    others.sort(key=lambda g: g["root"])

    return {
        "current_project": {
            "root": str(current_root) if current_root else None,
            "skills": (
                collect_skills(current_root / ".claude" / "skills")
                if current_root
                else []
            ),
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
    print(json.dumps(scan(args.home, args.cwd), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
