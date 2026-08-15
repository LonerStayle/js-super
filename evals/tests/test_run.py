"""진입점 테스트.

검증하는 것: --accept 없이는 기준선 파일을 절대 고치지 않는가.
분류 안 된 항목이 있으면 --accept 를 거부하는가.
검사 단계에서 모순이 잡히면 실행 자체를 거부하는가.
"""

import json
from pathlib import Path

from evals import run as runner
from evals.runner.baseline import Classified

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_기준선_경로가_저장소_안이다():
    assert runner.BASELINE_PATH.parent == REPO_ROOT / "evals"
    assert runner.LABELS_PATH.parent == REPO_ROOT / "evals"


def test_accept_없이는_기준선을_안_고친다(monkeypatch, tmp_path):
    target = tmp_path / "baseline.json"
    target.write_text('{"schema_version": 1, "cases": {}}\n', encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    monkeypatch.setattr(runner, "BASELINE_PATH", target)

    runner.main([("--quiet")])
    assert target.read_text(encoding="utf-8") == before


def test_미분류가_있으면_accept_를_거부한다(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "BASELINE_PATH", tmp_path / "baseline.json")
    monkeypatch.setattr(runner, "LABELS_PATH", tmp_path / "labels.json")

    rows = [Classified("x", "NEW", "FAIL", None, "무언가 실패")]
    assert runner.accept(rows) == 3
    assert not (tmp_path / "baseline.json").exists()


def test_통과만_있으면_라벨_없이도_굳힌다(monkeypatch, tmp_path):
    target = tmp_path / "baseline.json"
    monkeypatch.setattr(runner, "BASELINE_PATH", target)
    monkeypatch.setattr(runner, "LABELS_PATH", tmp_path / "labels.json")

    rows = [Classified("x", "NEW", "PASS", None)]
    assert runner.accept(rows) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["cases"]["x"]["label"] == "confirmed"


def test_라벨_파일에_적힌_판단이_기준선에_들어간다(monkeypatch, tmp_path):
    target = tmp_path / "baseline.json"
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps({"labels": {"x": {"label": "stale", "reason": "낡은 룰"}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "BASELINE_PATH", target)
    monkeypatch.setattr(runner, "LABELS_PATH", labels)

    rows = [Classified("x", "NEW", "FAIL", None, "실패")]
    assert runner.accept(rows) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["cases"]["x"]["label"] == "stale"
    assert data["cases"]["x"]["reason"] == "낡은 룰"


def test_모순이_있으면_실행을_거부한다(monkeypatch, capsys):
    class FakeLint:
        must_refuse = True
        conflicts = ["무언가 상충"]
        uncovered: list = []
        gate_gaps: list = []
        case_errors: list = []

    monkeypatch.setattr(runner.lint, "run_lint", lambda *a, **k: FakeLint())
    assert runner.main([]) == 2
    assert "실행 거부" in capsys.readouterr().out


def test_러너_안에서_다시_불리면_pytest_를_안_돈다(monkeypatch, tmp_path):
    """재귀 방지 장치. 이게 없으면 러너 → pytest → 러너 로 끝없이 반복된다."""
    monkeypatch.setenv(runner.NESTED_FLAG, "1")
    monkeypatch.setattr(runner, "BASELINE_PATH", tmp_path / "baseline.json")
    rows = runner.collect_pytest({"schema_version": 1, "cases": {}})
    assert len(rows) == 1
    assert rows[0].status == "NOT-SELECTED"
    assert "재귀" in rows[0].detail
