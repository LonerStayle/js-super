from pathlib import Path

import pytest

from scripts.changelog_buffer import (
    write_manifest,
    read_manifest,
    list_buffer_files,
    detect_stale_buffer,
    consolidate_to_entry,
)


def _write(p: Path, manifest: dict):
    write_manifest(p, manifest)


def test_write_and_read_minimal_manifest(tmp_path: Path):
    target = tmp_path / "task-01.md"
    manifest = {
        "task_id": 1,
        "task_name": "Hello",
        "status": "DONE",
        "base_sha": "deadbee",
        "commits": [],
        "files_changed": [],
        "concerns": [],
    }
    write_manifest(target, manifest)
    assert target.exists()
    loaded = read_manifest(target)
    assert loaded["task_id"] == 1
    assert loaded["task_name"] == "Hello"
    assert loaded["status"] == "DONE"


def test_list_buffer_files_sorted_by_task_id(tmp_path: Path):
    base = tmp_path / "feature-a"
    _write(base / "task-02.md", {"task_id": 2, "task_name": "B", "status": "DONE"})
    _write(base / "task-10.md", {"task_id": 10, "task_name": "J", "status": "DONE"})
    _write(base / "task-01.md", {"task_id": 1, "task_name": "A", "status": "DONE"})
    files = list_buffer_files(base)
    assert [f.name for f in files] == ["task-01.md", "task-02.md", "task-10.md"]


def test_detect_stale_buffer_returns_path_when_present(tmp_path: Path):
    base = tmp_path / ".js-super" / "changelog-buffer" / "feature-a"
    _write(base / "task-01.md", {"task_id": 1, "task_name": "A", "status": "DONE"})
    stale = detect_stale_buffer(tmp_path / ".js-super" / "changelog-buffer", "feature-a")
    assert stale is not None
    assert stale.name == "feature-a"


def test_detect_stale_buffer_returns_none_when_absent(tmp_path: Path):
    stale = detect_stale_buffer(tmp_path / ".js-super" / "changelog-buffer", "feature-a")
    assert stale is None


def test_consolidate_two_tasks_into_single_entry(tmp_path: Path):
    base = tmp_path / "feat"
    _write(base / "task-01.md", {
        "task_id": 1, "task_name": "Init", "status": "DONE",
        "base_sha": "aaa", "commits": [{"sha": "aaa1", "message": "feat: init"}],
        "files_changed": [{"path": "src/a.py", "line_range": "1-10",
                            "summary": "create A", "risk_hints": []}],
        "concerns": [],
    })
    _write(base / "task-02.md", {
        "task_id": 2, "task_name": "Wire", "status": "DONE",
        "base_sha": "aaa1", "commits": [{"sha": "bbb2", "message": "feat: wire"}],
        "files_changed": [{"path": "src/b.py", "line_range": "5-20",
                            "summary": "wire B", "risk_hints": ["side-effect"]}],
        "concerns": [],
    })
    out = consolidate_to_entry(
        manifests_dir=base,
        ch_id="CH-FIXTURE-100",
        timestamp="2026-05-09 18:00",
    )
    assert "[코드-수정] (batch: tasks 1..2)" in out
    assert "CH-FIXTURE-100" in out
    assert "src/a.py" in out and "src/b.py" in out
    assert "side-effect" in out
    assert "**변경 전/후 코드**: 생략" in out
    assert "aaa1" in out and "bbb2" in out


def test_F1_basic_batch_fixture():
    repo_root = Path(__file__).resolve().parents[2]
    fixtures = repo_root / "skills/js-super-sub-driven/tests/F1-basic-batch"
    out = consolidate_to_entry(
        manifests_dir=fixtures / "manifests",
        ch_id="CH-FIXTURE-100",
        timestamp="2026-05-09 18:00",
    )
    expected = (fixtures / "expected-entry.md").read_text()
    assert out.strip() == expected.strip()
