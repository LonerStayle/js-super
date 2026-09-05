"""에픽 파트 사슬 — 브랜치 이름과 워크트리 경로를 다루는 결정적 계산.

epic-close 스킬이 부른다. 표준 라이브러리만 쓰고 저장소를 고치지 않는다.
브랜치 이름 규칙:  <에픽 워크트리 이름>__ep_part<번호>_<작업명>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

PART_SEP = "__ep_part"
_PART_RE = re.compile(r"^(?P<epic>.+?)__ep_part(?P<num>\d+)_(?P<topic>.+)$")


def parse_part(branch: str) -> tuple[str, int]:
    """브랜치 이름에서 (에픽 워크트리 이름, 파트 번호) 를 읽는다.

    규칙에 맞지 않으면 그 브랜치 자체가 첫 파트다 — (branch, 1).
    """
    match = _PART_RE.match(branch)
    if not match:
        return branch, 1
    return match.group("epic"), int(match.group("num"))


def topic_slug(topic: str) -> str:
    """작업명을 브랜치에 넣을 수 있는 꼴로 만든다.

    공백은 하이픈으로. 구분자로 예약된 `__` 와 폴더를 중첩시키는 `/` 는 하이픈으로.
    앞뒤 하이픈은 지운다.
    """
    text = topic.strip().replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"_{2,}", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def next_branch_name(current_branch: str, topic: str) -> str:
    """현재 브랜치에서 다음 파트의 브랜치 이름을 만든다."""
    epic, num = parse_part(current_branch)
    return f"{epic}{PART_SEP}{num + 1}_{topic_slug(topic)}"


# ⚠️ RISK(side-effect): ls-files 가 비면 무시된 경로도 미추적으로 보고 자식 워크트리에 복사한다 — 요구 8 의 의도된 동작, 추적 중인 경로는 절대 복사 대상이 되지 않는다 — by epic-close Step 4
def is_tracked(repo_root: Path, rel_path: str) -> bool:
    """경로가 git 에 추적되는지 본다. ls-files 가 비면 미추적이다 (무시 목록 여부와 무관)."""
    result = subprocess.run(
        ["git", "ls-files", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def untracked_paths(repo_root: Path, rel_paths: list[str]) -> list[str]:
    """존재하지만 git 이 추적하지 않는 경로만 돌려준다. 자식 워크트리로 복사할 대상이다."""
    found = []
    for rel in rel_paths:
        if (repo_root / rel).exists() and not is_tracked(repo_root, rel):
            found.append(rel)
    return found


def latest_member_feature(features_dir: Path, member_names: list[str]) -> Optional[str]:
    """주어진 폴더 이름들 중 파일이 가장 최근에 수정된 폴더 이름을 고른다. 소속 판정은 부르는 쪽이 한다."""
    best_name: Optional[str] = None
    best_mtime = -1.0
    for name in member_names:
        folder = features_dir / name
        if not folder.is_dir():
            continue
        mtimes = [p.stat().st_mtime for p in folder.rglob("*") if p.is_file()]
        mtime = max(mtimes) if mtimes else folder.stat().st_mtime
        if mtime > best_mtime:
            best_name, best_mtime = name, mtime
    return best_name


USAGE = """사용법:
  epic_chain.py parse <현재 브랜치>
  epic_chain.py next <현재 브랜치> <작업명>
  epic_chain.py untracked <저장소 루트> <경로>...
  epic_chain.py latest <features 폴더> <피처 폴더 이름>..."""


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(USAGE)
        return 2
    cmd = argv[1]
    if cmd == "parse" and len(argv) == 3:
        epic, num = parse_part(argv[2])
        print(json.dumps({"epic": epic, "part": num}, ensure_ascii=False))
        return 0
    if cmd == "next" and len(argv) == 4:
        print(next_branch_name(argv[2], argv[3]))
        return 0
    if cmd == "untracked" and len(argv) >= 4:
        print(json.dumps(untracked_paths(Path(argv[2]), argv[3:]), ensure_ascii=False))
        return 0
    if cmd == "latest" and len(argv) >= 4:
        print(latest_member_feature(Path(argv[2]), argv[3:]) or "")
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
