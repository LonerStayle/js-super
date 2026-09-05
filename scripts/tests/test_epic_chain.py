"""epic_chain 단위 테스트 — 브랜치 이름 규칙과 git 미추적 판정.

검증 시나리오:
1. 규칙에 맞는 브랜치에서 (에픽 이름, 번호) 를 읽는다
2. 맞지 않는 브랜치는 그 자신이 첫 파트다 — (브랜치, 1)
3. 다음 이름은 번호에 1 을 더하고 앞 파트 이름을 누적하지 않는다
4. 작업명의 공백 · `__` · `/` 는 하이픈으로 바뀐다
5. untracked_paths 는 커밋된 경로를 빼고 무시된 경로와 미추적 경로만 돌려주며 없는 경로는 뺀다
6. latest_member_feature 는 mtime 이 가장 큰 파일을 가진 폴더를 고르고 없으면 None
7. CLI next 가 이름을 출력한다
"""

import os
import subprocess
from pathlib import Path

from scripts.epic_chain import (
    latest_member_feature,
    main,
    next_branch_name,
    parse_part,
    topic_slug,
    untracked_paths,
)


def test_parse_part_regular():
    assert parse_part("결제__ep_part2_환불") == ("결제", 2)


def test_parse_part_first_part_is_branch_itself():
    assert parse_part("결제") == ("결제", 1)


def test_parse_part_keeps_single_underscore_in_epic_name():
    assert parse_part("a_b__ep_part3_x") == ("a_b", 3)


def test_next_branch_name_does_not_accumulate():
    assert next_branch_name("결제__ep_part2_환불", "정산") == "결제__ep_part3_정산"


def test_next_branch_name_from_first_part():
    assert next_branch_name("결제", "환불 처리") == "결제__ep_part2_환불-처리"


def test_topic_slug_replaces_separators():
    assert topic_slug("a__b/c  d") == "a-b-c-d"
    assert topic_slug("  -x- ") == "x"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_untracked_paths_returns_ignored_and_untracked_only(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    tracked = tmp_path / "docs" / "features" / "f"
    tracked.mkdir(parents=True)
    (tracked / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("docs/epics/\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    ignored = tmp_path / "docs" / "epics" / "e"
    ignored.mkdir(parents=True)
    (ignored / "overview.md").write_text("o", encoding="utf-8")
    untracked = tmp_path / "docs" / "features" / "g"
    untracked.mkdir()
    (untracked / "b.md").write_text("y", encoding="utf-8")

    got = untracked_paths(
        tmp_path,
        ["docs/epics/e", "docs/features/f", "docs/features/g", "docs/nope"],
    )
    assert got == ["docs/epics/e", "docs/features/g"]


def test_latest_member_feature_picks_newest_file(tmp_path: Path):
    for name, stamp in (("old", 100), ("new", 200)):
        folder = tmp_path / name
        folder.mkdir()
        doc = folder / "x.md"
        doc.write_text("x", encoding="utf-8")
        os.utime(doc, (stamp, stamp))
    assert latest_member_feature(tmp_path, ["old", "new", "missing"]) == "new"
    assert latest_member_feature(tmp_path, ["missing"]) is None


def test_cli_next_prints_name(capsys):
    assert main(["epic_chain.py", "next", "결제", "정산"]) == 0
    assert capsys.readouterr().out.strip() == "결제__ep_part2_정산"
