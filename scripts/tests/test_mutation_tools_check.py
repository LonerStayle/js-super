"""뮤테이션 도구 사전 확인 (scripts.preflight.mutation_tools_check) 단위 테스트.

실행 흐름 진입 시 "이 프로젝트 언어의 뮤테이션 도구가 없으면 한 번만 묻는다" 를 위한
판정 함수와 기록 함수를 검사한다. 도구 유무는 probe 를 주입해 고정한다 — 실제
`code_gate.probe_tools` 는 서브프로세스를 띄우므로 여기서는 쓰지 않는다.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.preflight import (
    MUTATION_TOOLS_MARKER,
    mutation_tools_check,
    read_mutation_decisions,
    record_mutation_decision,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _probe(**available):
    """이름 → 있음/없음 만 고정한 가짜 probe. 없는 이름은 '없음' 이다."""
    def probe(repo_root, python_exe):
        names = ("pytest", "coverage", "lizard", "mutmut", "jscpd", "depcruise",
                 "stryker", "node", "git", "gremlins", "dotnet-stryker", "gradle", "cargo-mutants")
        return {name: {"available": bool(available.get(name, False)),
                       "path": None, "install_hint": None} for name in names}
    return probe


def _python_project(root: Path) -> None:
    _write(root / "src" / "app.py", "def add(a, b):\n    return a + b\n")
    _write(root / "tests" / "test_app.py", "def test_add():\n    assert 1 + 1 == 2\n")


def _js_project(root: Path, runner: str = "vitest") -> None:
    _write(root / "src" / "app.ts", "export const add = (a: number, b: number) => a + b;\n")
    _write(root / "package.json", json.dumps({
        "name": "x", "scripts": {"test": runner},
        "devDependencies": {runner: "^1.0.0"},
    }))


# ---------------------------------------------------------------------------
# 파이썬 — 네 조건 (지원 언어 파일 · 테스트 경로 · 도구 없음 · 기록 없음)
# ---------------------------------------------------------------------------

def test_python_missing_mutmut_with_tests_asks(tmp_path, monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    _python_project(tmp_path)
    _write(tmp_path / ".venv" / "bin" / "python", "")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    languages = [s.language for s in result.ask]
    assert languages == ["python"]
    status = result.ask[0]
    assert status.tool == "mutmut"
    assert "pip install" in status.install_cmd and "mutmut" in status.install_cmd
    assert status.install_scope == "project"


def test_python_without_tests_does_not_ask(tmp_path):
    """테스트가 없는 프로젝트에서는 mutmut 이 있어도 못 재므로 묻지 않는다."""
    _write(tmp_path / "src" / "app.py", "x = 1\n")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    assert result.ask == ()
    assert "테스트" in result.human_reason


def test_python_tool_present_does_not_ask(tmp_path):
    _python_project(tmp_path)
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True, mutmut=True))
    assert result.ask == ()


def test_python_missing_pytest_adds_it_to_install_cmd(tmp_path):
    """pytest 가 없으면 mutmut 만 깔아도 C7 이 안 돈다 (C1 선행). 같이 적는다."""
    _python_project(tmp_path)
    result = mutation_tools_check(tmp_path, probe=_probe())
    cmd = result.ask[0].install_cmd
    assert "pytest" in cmd and "mutmut" in cmd


def test_declined_marker_suppresses_ask(tmp_path):
    _python_project(tmp_path)
    record_mutation_decision(tmp_path, "python", "declined")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    assert result.ask == ()
    assert "python" not in [s.language for s in result.ask]


def test_install_failed_marker_suppresses_ask(tmp_path):
    """설치를 시도했다 실패한 언어도 다시 묻지 않는다 — 매 회차 실패를 반복하지 않는다."""
    _python_project(tmp_path)
    record_mutation_decision(tmp_path, "python", "install_failed")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    assert result.ask == ()


# ---------------------------------------------------------------------------
# 자바스크립트 — Stryker 본체 + 러너 플러그인 둘 다 있어야 "있음"
# ---------------------------------------------------------------------------

def test_js_missing_stryker_asks_with_runner_plugin(tmp_path):
    _js_project(tmp_path, runner="vitest")
    result = mutation_tools_check(tmp_path, probe=_probe(node=True))
    assert [s.language for s in result.ask] == ["javascript"]
    cmd = result.ask[0].install_cmd
    assert "@stryker-mutator/core" in cmd and "@stryker-mutator/vitest-runner" in cmd
    assert cmd.startswith("npm i -D")


def test_js_core_present_but_runner_plugin_missing_asks_for_plugin_only(tmp_path):
    _js_project(tmp_path, runner="jest")
    (tmp_path / "node_modules" / ".bin").mkdir(parents=True)
    _write(tmp_path / "node_modules" / ".bin" / "stryker")
    result = mutation_tools_check(tmp_path, probe=_probe(node=True, stryker=True))
    assert [s.language for s in result.ask] == ["javascript"]
    cmd = result.ask[0].install_cmd
    assert "@stryker-mutator/jest-runner" in cmd
    assert "@stryker-mutator/core" not in cmd


def test_js_core_and_runner_plugin_present_does_not_ask(tmp_path):
    _js_project(tmp_path, runner="vitest")
    (tmp_path / "node_modules" / "@stryker-mutator" / "vitest-runner").mkdir(parents=True)
    result = mutation_tools_check(tmp_path, probe=_probe(node=True, stryker=True))
    assert result.ask == ()


def test_js_project_stryker_config_counts_as_runner(tmp_path):
    """프로젝트 Stryker 설정이 있으면 러너 플러그인 없이도 게이트가 돈다 — 묻지 않는다."""
    _js_project(tmp_path, runner="vitest")
    _write(tmp_path / "stryker.config.json", "{}")
    result = mutation_tools_check(tmp_path, probe=_probe(node=True, stryker=True))
    assert result.ask == ()


def test_html_only_project_is_not_javascript(tmp_path):
    """게이트의 JS 변이 대상에는 .html 이 들어가지만, package.json 도 테스트도 없는
    파이썬 프로젝트의 템플릿 하나 때문에 Stryker 설치를 물으면 안 된다."""
    _python_project(tmp_path)
    _write(tmp_path / "templates" / "index.html", "<p>x</p>")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True, mutmut=True))
    assert result.ask == ()


# ---------------------------------------------------------------------------
# 고 · C# — 사용자 환경 설치 (프로젝트 로컬 아님) 를 표에 드러낸다
# ---------------------------------------------------------------------------

def test_go_missing_gremlins_asks_with_user_scope(tmp_path):
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "add.go", "package x\n")
    _write(tmp_path / "add_test.go", "package x\n")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert [s.language for s in result.ask] == ["go"]
    assert result.ask[0].install_scope == "user"
    assert "go install" in result.ask[0].install_cmd


def test_go_without_test_files_does_not_ask(tmp_path):
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "add.go", "package x\n")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert result.ask == ()


def test_csharp_missing_stryker_net_asks_with_user_scope(tmp_path):
    _write(tmp_path / "App" / "Add.cs", "class A {}\n")
    _write(tmp_path / "App.Tests" / "AddTests.cs", "class T {}\n")
    _write(tmp_path / "App.Tests" / "App.Tests.csproj", "<Project/>")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert [s.language for s in result.ask] == ["csharp"]
    assert result.ask[0].install_scope == "user"
    assert "dotnet tool install" in result.ask[0].install_cmd


# ---------------------------------------------------------------------------
# 자바 · 러스트 — 기본 꺼짐. 묻지 않고 켜는 법만 한 번 안내한다
# ---------------------------------------------------------------------------

def test_java_files_produce_note_not_ask(tmp_path):
    _write(tmp_path / "src" / "main" / "java" / "A.java", "class A {}\n")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert result.ask == ()
    assert len(result.notes) == 1
    assert "java" in result.notes[0] and "gradle" in result.notes[0]
    assert ".code-gate.json" in result.notes[0]


def test_noted_marker_suppresses_default_off_note(tmp_path):
    _write(tmp_path / "src" / "lib.rs", "fn a() {}\n")
    record_mutation_decision(tmp_path, "rust", "noted")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert result.notes == ()


# ---------------------------------------------------------------------------
# 지원 언어 없음 · 여러 언어 · 기록 파일
# ---------------------------------------------------------------------------

def test_no_supported_files_is_quiet(tmp_path):
    _write(tmp_path / "README.md", "# x\n")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert result.ask == () and result.notes == ()
    assert "없" in result.human_reason


def test_two_languages_ask_in_registry_order(tmp_path):
    _python_project(tmp_path)
    _js_project(tmp_path, runner="vitest")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True, node=True))
    assert [s.language for s in result.ask] == ["javascript", "python"]


def test_ignored_directories_are_not_scanned(tmp_path):
    """node_modules · 가상환경 · 숨김 폴더 안의 파일은 프로젝트 언어로 세지 않는다."""
    _write(tmp_path / "node_modules" / "dep" / "index.js", "x")
    _write(tmp_path / ".venv" / "lib" / "site.py", "x")
    _write(tmp_path / "README.md", "# x\n")
    result = mutation_tools_check(tmp_path, probe=_probe())
    assert all(not s.has_files for s in result.statuses)


def test_record_writes_marker_json(tmp_path):
    path = record_mutation_decision(tmp_path, "python", "declined")
    assert path == tmp_path / MUTATION_TOOLS_MARKER
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["python"]["decision"] == "declined"
    assert data["python"]["at"]
    assert read_mutation_decisions(tmp_path) == {"python": "declined"}


def test_record_keeps_other_languages(tmp_path):
    record_mutation_decision(tmp_path, "python", "declined")
    record_mutation_decision(tmp_path, "javascript", "installed")
    assert read_mutation_decisions(tmp_path) == {"python": "declined", "javascript": "installed"}


def test_record_rejects_unknown_decision_or_language(tmp_path):
    with pytest.raises(ValueError):
        record_mutation_decision(tmp_path, "python", "maybe")
    with pytest.raises(ValueError):
        record_mutation_decision(tmp_path, "cobol", "declined")


def test_corrupt_marker_is_treated_as_empty(tmp_path):
    _write(tmp_path / MUTATION_TOOLS_MARKER, "{not json")
    _python_project(tmp_path)
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    assert [s.language for s in result.ask] == ["python"]


# ---------------------------------------------------------------------------
# CLI — 커맨드 본문이 부르는 진입점
# ---------------------------------------------------------------------------

_PREFLIGHT = Path(__file__).resolve().parents[1] / "preflight.py"


def _cli(*args, cwd):
    return subprocess.run([sys.executable, str(_PREFLIGHT), "mutation-tools", *args],
                          cwd=cwd, capture_output=True, text=True, timeout=60)


def test_cli_first_line_is_ask_or_ok(tmp_path):
    _write(tmp_path / "README.md", "# x\n")
    proc = _cli(cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == "MUTATION_TOOLS_OK"


def test_cli_record_then_check(tmp_path):
    _python_project(tmp_path)
    proc = _cli("--record", "python=declined", cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "python" in proc.stdout
    assert read_mutation_decisions(tmp_path) == {"python": "declined"}


def test_cli_rejects_bad_record(tmp_path):
    proc = _cli("--record", "python", cwd=tmp_path)
    assert proc.returncode != 0


def test_python_without_venv_is_user_scope(tmp_path, monkeypatch):
    """가상환경이 없으면 pip 가 시스템 파이썬에 깐다 — 프로젝트 로컬이라고 적으면 거짓이다."""
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    _python_project(tmp_path)
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    status = result.ask[0]
    assert status.install_scope == "user"
    assert "가상환경" in status.note


def test_python_with_project_venv_is_project_scope(tmp_path, monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    _python_project(tmp_path)
    _write(tmp_path / ".venv" / "bin" / "python", "")
    result = mutation_tools_check(tmp_path, probe=_probe(pytest=True))
    status = result.ask[0]
    assert status.install_scope == "project"
    assert str(tmp_path / ".venv") in status.install_cmd
