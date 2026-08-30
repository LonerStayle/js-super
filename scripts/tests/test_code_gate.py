"""code_gate 단위 테스트 — 검사 게이트 0단계.

검증 시나리오:
1. CRAP 공식의 성질 (v=1.0 → CRAP==c / v=0.0 → c²+c / c=1,v=0 → 2)
2. 커버리지-복잡도 결합 세 경로 (시작줄 일치 / 줄 범위 폴백 / istanbul 범위 겹침)
3. lizard CSV 파싱과 형식 불일치 행 폐기
4. git diff 헝크 파서 (개수 생략형 포함)
5. 변경분 밖 함수 제외 (R3)
6. 설정 파일 폴백 (부재 / 깨진 JSON / 잘못된 값) — R6
7. 도구 부재 시 건너뜀 + 설치 방법 + 시간 (R1·R4)
8. 의존 방향 규칙 (부재 / 위반 / 통과)
9. 항목 격리 (시간 초과·예외가 나도 다음 항목이 돈다) — R2
10. 종료 코드 0 보장 (CLI 실측, 알 수 없는 인자 포함) — R2
11. 인터페이스에 흐름 구분 인자가 없음 — R5
12. 비-0 종료를 유발하는 인자 차단 — R2
13. 검사하지 않은 것이 통과로 보이지 않음 (테스트 0개 / 측정 줄 없음 /
    lizard 출력 전량 폐기 / 파싱 실패 / 레이어 밖) — R4
14. 의존성·빌드 디렉토리가 변경분에서 빠짐 — R1
15. 뮤테이션 점수 공식(D1) / 실제 리포트 파싱(D2) / 예산 초과 부분 결과(D4) /
    산출물이 대상 프로젝트 밖에 떨어짐(D3) / 설정 폴백
"""

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts import code_gate
from scripts.code_gate import (
    CHECKS,
    DEFAULT_COMPLEXITY_THRESHOLD,
    DEFAULT_CRAP_THRESHOLD,
    DEFAULT_TIMEOUT_SECONDS,
    ChangeSet,
    FileCoverage,
    GateContext,
    _apply_exclude,
    _config_payload,
    _forbidden_arg,
    _js_outcome,
    _match_glob,
    _parse_pytest_counts,
    _mutation_detail_line,
    _run,
    build_parser,
    check_complexity,
    check_coverage,
    check_crap,
    check_duplication,
    check_layers,
    check_mutation,
    check_tests,
    collect_changes,
    compute_crap,
    crap_score,
    detect_languages,
    detect_pytest_paths,
    load_config,
    parse_diff,
    parse_lizard_csv,
    resolve_coverage,
    resolve_python,
    run_checks,
)
from scripts.mutation import go as mutation_go
from scripts.mutation import javascript as mutation_javascript
from scripts.mutation import python as mutation_python
from scripts.mutation import score as mutation_score_mod
from scripts.mutation import (
    _merge_mutation_languages,
    _mutation_share,
)
from scripts.mutation.javascript import (
    _mutation_changed_javascript as _mutation_changed_files,
    _mutation_no_report,
    _mutation_partial,
    _mutation_targets,
    _stryker_glob,
    _stryker_project_config,
    _write_stryker_config,
    mutation_state_file,
    parse_mutation_events,
    parse_mutation_report,
)
from scripts.mutation.python import (
    _mutation_changed_python as _mutation_changed_python_files,
    _mutmut_incremental_guard,
    _mutmut_link,
    _mutmut_link_name,
    _mutmut_no_result,
    _mutmut_partial,
    _mutmut_reclaim,
    _mutmut_source_roots,
    _mutmut_targets,
    _mutmut_test_roots,
    _write_mutmut_config,
    build_mutmut_records,
    mutmut_change,
    mutmut_def_lines,
    mutmut_function_name,
    mutmut_gate_status,
    mutmut_status,
    mutmut_work_dir,
    parse_mutmut_run,
    python_decorated_skips,
)
from scripts.mutation.score import (
    _ko_topic,
    _mutation_budget,
    _mutation_distribution,
    _mutation_gaps,
    _mutation_outcome,
    _mutation_timing,
    mutation_score,
    slice_lines,
    slice_source,
    summarize_mutants,
    unknown_mutant_statuses,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "code_gate.py"


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _row(file="a.py", function="f", complexity=5, start=10, end=20):
    return {"file": file, "function": function, "complexity": complexity,
            "start_line": start, "end_line": end}


def _cov(kind="coverage-json", functions=(), executed=(), missing=(), istanbul=None, percent=None):
    return FileCoverage(kind=kind, percent=percent, functions=tuple(functions),
                        executed=frozenset(executed), missing=frozenset(missing), istanbul=istanbul)


def _changeset(files, lines=None):
    files = tuple(files)
    return ChangeSet(base="main", base_reason="", files=files, excluded=(),
                     lines=lines if lines is not None else {f: None for f in files})


def _no_tools(python_exe=sys.executable):
    """전부 설치 안 된 상태 — probe_tools 가 만드는 것과 같은 모양."""
    tools = {}
    for name in ("pytest", "coverage", "lizard", "mutmut"):
        tools[name] = {"available": False, "path": None,
                       "install_hint": f"{python_exe} -m pip install {name}"}
    tools["jscpd"] = {"available": False, "path": None, "install_hint": "npm i -D jscpd"}
    tools["depcruise"] = {"available": False, "path": None, "install_hint": "npm i -D dependency-cruiser"}
    tools["stryker"] = {"available": False, "path": None, "install_hint": "npm i -D @stryker-mutator/core"}
    for name in ("node", "git"):
        tools[name] = {"available": False, "path": None, "install_hint": f"{name} 를 설치하십시오."}
    return tools


def _with_lizard(python_exe=sys.executable):
    """lizard 만 설치된 상태."""
    tools = _no_tools(python_exe)
    tools["lizard"] = {"available": True, "path": f"{python_exe} -m lizard", "install_hint": ""}
    return tools


class _FakeProc:
    """`_run` 을 대신할 최소 객체 — 서브프로세스 없이 출력 형식만 흉내낸다."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    """홈 캐시를 테스트마다 격리한다.

    뮤테이션 항목은 회차를 넘어 사는 증분 상태를 사용자 캐시(`XDG_CACHE_HOME`) 아래에 둔다.
    격리하지 않으면 테스트를 돌릴 때마다 사용자의 진짜 캐시에 저장소 해시 디렉토리가 하나씩
    쌓인다 (실제로 수백 개가 쌓여 있었다). 개별 테스트가 다시 `monkeypatch.setenv` 로 자기
    자리를 지정하면 그쪽이 이긴다.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("xdg-cache")))


def _ctx(tmp_path, files=(), lines=None, config=None, tools=None):
    tmpdir = tmp_path / "_gate_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    return GateContext(
        repo_root=tmp_path,
        config=config or load_config(tmp_path / "no-such-config.json"),
        change=_changeset(files, lines),
        langs=detect_languages(files),
        tools=tools if tools is not None else _no_tools(),
        python_exe=sys.executable,
        tmpdir=tmpdir,
        notes=[],
    )


# ---------------------------------------------------------------------------
# 1 — CRAP 공식
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("complexity", [1, 5, 14, 32])
def test_crap_equals_complexity_when_fully_covered(complexity):
    """커버리지가 완전하면 뒤 항이 0 이 되어 CRAP == c 여야 한다.

    이 성질이 깨지면 공식이 잘못 구현된 것이다. CRAP 이 복잡도와 커버리지를
    한 값으로 묶는다는 전제 자체가 여기서 나온다.
    """
    assert math.isclose(crap_score(complexity, 1.0), float(complexity))


@pytest.mark.parametrize("complexity", [1, 5, 14, 32])
def test_crap_with_zero_coverage(complexity):
    assert math.isclose(crap_score(complexity, 0.0), complexity * complexity + complexity)


def test_crap_c1_v0_is_two():
    assert math.isclose(crap_score(1, 0.0), 2.0)


def test_crap_is_monotonic_in_coverage():
    """커버리지가 오르면 CRAP 은 떨어져야 한다 — 부호를 뒤집는 회귀 방지."""
    values = [crap_score(10, v / 10.0) for v in range(11)]
    assert all(a >= b for a, b in zip(values, values[1:]))


# ---------------------------------------------------------------------------
# 2 — 커버리지-복잡도 결합
# ---------------------------------------------------------------------------

def test_coverage_path_a_matches_exact_start_line():
    cov = {"a.py": _cov(functions=((10, 0.8), (40, 0.1)))}
    ratio, source = resolve_coverage(_row(start=10, end=20), cov)
    assert (ratio, source) == (0.8, "exact-start-line")


def test_coverage_path_b_skips_the_def_line():
    """줄 범위 폴백은 def 줄(시작줄)을 빼고 센다.

    def 줄은 import 시점에 항상 실행되므로, 포함하면 한 번도 호출되지 않은
    두 줄짜리 함수가 50% 커버로 보인다. 실측에서 최대 오차 0.5 를 만들던 지점이다.
    """
    row = _row(start=10, end=11)
    cov = {"a.py": _cov(executed=(10,), missing=(11,))}
    ratio, source = resolve_coverage(row, cov)
    assert source == "range-fallback"
    assert ratio == 0.0     # def 줄을 포함했다면 0.5 가 나온다


def test_coverage_path_b_empty_range_is_unresolved_not_full():
    """잴 줄이 없으면 '완전 커버'가 아니라 '측정 불가'다.

    여기서 1.0 을 주면 커버리지 없는 복잡한 코드를 잡겠다는 CRAP 의 도입 이유가
    그대로 뒤집힌다 — 짝짓기에 실패한 함수가 전부 초록이 된다.
    """
    row = _row(start=10, end=11)
    cov = {"a.py": _cov(executed=(1, 2), missing=(3,))}
    assert resolve_coverage(row, cov) == (None, "range-empty")


def test_coverage_one_line_function_is_not_reported_as_covered():
    """한 줄 함수는 def 줄 제외(+1) 때문에 범위가 항상 빈다.

    실측 회귀: 한 번도 호출되지 않은 한 줄 화살표 함수(c=8)가 v=1.00 / CRAP=8.00
    으로 인쇄됐다. 참값은 v=0 / CRAP=72 다.
    """
    row = _row(file="a.js", complexity=8, start=5, end=5)
    cov = {"a.js": _cov(kind="lcov", executed=(1, 2), missing=(5,))}
    assert resolve_coverage(row, cov) == (None, "range-empty")

    entries = compute_crap([row], cov, _changeset(["a.js"]))
    assert entries[0]["crap"] is None
    assert entries[0]["coverage_source"] == "range-empty"


def test_istanbul_join_failure_is_not_reported_as_covered():
    """fnMap 짝짓기 실패도 '완전 커버'로 새면 안 된다 (같은 계열의 회귀)."""
    istanbul = {"fnMap": {}, "statementMap": {}, "s": {}, "f": {}}
    cov = {"a.js": _cov(kind="istanbul", istanbul=istanbul)}
    ratio, source = resolve_coverage(_row(file="a.js", complexity=20, start=10, end=30), cov)
    assert ratio is None and source == "range-empty"


def test_coverage_missing_file_is_reported_not_skipped():
    """커버리지 데이터가 없는 함수는 조용히 빠지지 않고 출처가 남는다 (R4)."""
    ratio, source = resolve_coverage(_row(file="unmeasured.py"), {})
    assert (ratio, source) == (0.0, "no-coverage-data")


def test_coverage_path_c_istanbul_overlap():
    istanbul = {
        "fnMap": {"0": {"name": "f", "loc": {"start": {"line": 10}, "end": {"line": 20}}},
                  "1": {"name": "g", "loc": {"start": {"line": 30}, "end": {"line": 40}}}},
        "statementMap": {"0": {"start": {"line": 11}}, "1": {"start": {"line": 12}},
                         "2": {"start": {"line": 31}}},
        "s": {"0": 3, "1": 0, "2": 1},
        "f": {"0": 3, "1": 1},
    }
    cov = {"a.js": _cov(kind="istanbul", istanbul=istanbul)}
    ratio, source = resolve_coverage(_row(file="a.js", start=10, end=20), cov)
    assert source == "istanbul-overlap"
    assert math.isclose(ratio, 0.5)


def test_istanbul_index_prefers_the_innermost_function():
    """중첩된 함수에서 안쪽을 고른다 — 색인을 넣으면서 짝짓기 결과가 바뀌면 안 된다."""
    istanbul = {
        "fnMap": {"outer": {"loc": {"start": {"line": 1}, "end": {"line": 100}}},
                  "inner": {"loc": {"start": {"line": 40}, "end": {"line": 50}}}},
        "statementMap": {"a": {"start": {"line": 41}}, "b": {"start": {"line": 45}},
                         "c": {"start": {"line": 90}}},
        "s": {"a": 1, "b": 0, "c": 0},
        "f": {"outer": 1, "inner": 1},
    }
    cov = {"a.js": _cov(kind="istanbul", istanbul=istanbul)}
    ratio, source = resolve_coverage(_row(file="a.js", start=40, end=50), cov)
    assert source == "istanbul-overlap"
    assert math.isclose(ratio, 0.5)     # 90번 줄(바깥 함수)은 섞이지 않는다


def test_istanbul_index_is_reused_across_rows():
    """색인은 파일당 한 번만 만든다 — 없으면 (함수 수 × 구문 수)로 제곱 증가한다."""
    istanbul = {
        "fnMap": {"0": {"loc": {"start": {"line": 10}, "end": {"line": 20}}}},
        "statementMap": {"0": {"start": {"line": 11}}},
        "s": {"0": 1}, "f": {"0": 1},
    }
    cov = {"a.js": _cov(kind="istanbul", istanbul=istanbul)}
    cache: dict = {}
    for _ in range(3):
        resolve_coverage(_row(file="a.js", start=10, end=20), cov, cache)
    assert list(cache) == ["a.js"]


def test_coverage_path_c_join_mismatch_is_flagged():
    """진입 횟수 0 인데 구문은 실행된 것으로 나오면 파싱 모순 — 결합 실패로 보고한다."""
    istanbul = {
        "fnMap": {"0": {"loc": {"start": {"line": 10}, "end": {"line": 20}}}},
        "statementMap": {"0": {"start": {"line": 11}}},
        "s": {"0": 5},
        "f": {"0": 0},
    }
    cov = {"a.js": _cov(kind="istanbul", istanbul=istanbul)}
    assert resolve_coverage(_row(file="a.js", start=10, end=20), cov) == (None, "join-mismatch")


# ---------------------------------------------------------------------------
# 3 — lizard CSV
# ---------------------------------------------------------------------------

GOOD_CSV = (
    '27,5,107,1,28,"code_pretty_check@57-84@scripts/preflight.py",'
    '"scripts/preflight.py","code_pretty_check","code_pretty_check( file_path : Path )",57,84\n'
)


def test_lizard_csv_parses_eleven_columns():
    rows, failures = parse_lizard_csv(GOOD_CSV)
    assert failures == 0
    assert rows == [{"file": "scripts/preflight.py", "function": "code_pretty_check",
                     "complexity": 5, "start_line": 57, "end_line": 84}]


def test_lizard_csv_discards_location_mismatch():
    """헤더 없는 CSV 라 컬럼이 밀려도 조용히 통과할 수 있다.

    location 필드의 `이름@시작-끝@파일` 과 9/10번 컬럼을 대조해 어긋난 행은 버린다.
    """
    bad = GOOD_CSV.replace("@57-84@", "@99-120@")
    rows, failures = parse_lizard_csv(bad)
    assert rows == [] and failures == 1


def test_lizard_csv_discards_wrong_column_count():
    rows, failures = parse_lizard_csv("1,2,3\n" + GOOD_CSV)
    assert failures == 1 and len(rows) == 1


# ---------------------------------------------------------------------------
# 4 — diff 헝크 파서 (R3)
# ---------------------------------------------------------------------------

def test_parse_diff_handles_both_hunk_forms():
    text = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"
        "@@ -3,0 +4,2 @@\n+x\n+y\n"
        "@@ -10 +12 @@\n-old\n+new\n"
        "diff --git a/b.py b/b.py\n--- a/b.py\n+++ b/b.py\n"
        "@@ -5,3 +5,0 @@\n-gone\n"
    )
    parsed = parse_diff(text)
    assert parsed["a.py"] == {4, 5, 12}
    assert parsed["b.py"] == {5}      # 삭제만 있는 헝크도 위치를 변경으로 표시


def test_parse_diff_ignores_dev_null_target():
    text = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ /dev/null\n@@ -1,3 +0,0 @@\n-x\n"
    assert parse_diff(text) == {}


def test_parse_diff_catches_content_free_rename():
    """유사도 100% rename 은 `+++` 줄이 없어 `+++` 만 보면 통째로 빠진다.

    파일을 레이어 밖/안으로 옮기기만 한 커밋이 정확히 이 형태인데, 하필 그 이동을
    봐야 하는 의존 방향 검사가 파일 단위로 돌기 때문에 목록에 없으면 안 돈다.
    """
    text = (
        "diff --git a/ui/mod.py b/core/mod.py\n"
        "similarity index 100%\nrename from ui/mod.py\nrename to core/mod.py\n"
    )
    assert parse_diff(text) == {"core/mod.py": None}      # None = 파일 전체가 변경분


def test_parse_diff_catches_mode_only_change():
    text = "diff --git a/run.sh b/run.sh\nold mode 100644\nnew mode 100755\n"
    assert parse_diff(text) == {"run.sh": None}


def test_parse_diff_keeps_hunks_after_a_plus_plus_body_line():
    """내용이 `++ ` 로 시작하는 추가 줄은 diff 에서 `+++ ...` 로 보인다.

    그것을 헤더로 오인하면 뒤따르는 헝크가 존재하지 않는 파일에 붙고, 실제로 고친
    함수가 조용히 검사 대상에서 빠진 채 '변경된 함수 N개 모두 기준 이하'가 된다.
    """
    text = (
        "diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n"
        "@@ -2,0 +2 @@\n+++ note\n"
        "@@ -36,0 +36,2 @@\n+def heavy(x):\n+    return x\n"
    )
    parsed = parse_diff(text)
    assert set(parsed) == {"f.py"}                # 팬텀 파일 'note' 가 생기지 않는다
    assert parsed["f.py"] == {2, 36, 37}


def test_merge_lines_lets_whole_file_win_over_line_numbers():
    """'파일 전체 변경'(None)은 줄 집합보다 넓다 — 합칠 때 넓은 쪽이 이겨야 한다.

    rename 구획을 읽게 되면서 커밋 갈래도 None 을 낼 수 있게 됐다. 합치는 쪽이
    그것을 모르면 `None` 을 set 에 update 하려다 게이트가 통째로 크래시한다.
    """
    target = {"a.py": {1, 2}}
    code_gate._merge_lines(target, {"a.py": None, "b.py": {3}})
    assert target == {"a.py": None, "b.py": {3}}
    code_gate._merge_lines(target, {"a.py": {9}})
    assert target["a.py"] is None


def test_parse_diff_rename_with_edits_still_records_lines():
    text = (
        "diff --git a/ui/mod.py b/core/mod.py\n"
        "similarity index 90%\nrename from ui/mod.py\nrename to core/mod.py\n"
        "--- a/ui/mod.py\n+++ b/core/mod.py\n@@ -4,0 +5,2 @@\n+a\n+b\n"
    )
    assert parse_diff(text) == {"core/mod.py": {5, 6}}


# ---------------------------------------------------------------------------
# 5 — 변경분 밖 함수 제외 (R3)
# ---------------------------------------------------------------------------

def test_compute_crap_skips_functions_outside_the_diff():
    change = _changeset(["a.py"], lines={"a.py": frozenset({12, 13})})
    rows = [_row(function="touched", start=10, end=20), _row(function="untouched", start=100, end=120)]
    entries = compute_crap(rows, {}, change)
    assert [e["function"] for e in entries] == ["touched"]


def test_changeset_untracked_file_counts_as_fully_changed():
    change = _changeset(["new.py"])          # lines 값이 None = 파일 전체
    assert change.overlaps("new.py", 500, 600) is True
    assert change.overlaps("other.py", 1, 2) is False


def test_dependency_directories_never_enter_the_change_set(tmp_path):
    """의존성·빌드 디렉토리는 exclude 설정과 무관하게 항상 뺀다 (R1).

    아직 gitignore 되지 않은 node_modules 는 `ls-files --others` 에 통째로 잡힌다.
    실측: 실제 코드 1줄만 고친 저장소에서 변경 파일이 1,201개, 분석 함수가 1,200개가
    됐다. 검사 시간이 자릿수로 늘고 중복 검사는 의존성끼리의 중복으로 파묻힌다.
    """
    _write(tmp_path / "src.py", "x = 1\n")
    _write(tmp_path / "node_modules" / "pkg" / "index.js", "export default 1;\n")
    _write(tmp_path / ".venv" / "lib" / "site-packages" / "dep.py", "y = 2\n")
    _write(tmp_path / "dist" / "bundle.js", "var a = 1;\n")
    lines = {"src.py": None, "node_modules/pkg/index.js": None,
             ".venv/lib/site-packages/dep.py": None, "dist/bundle.js": None}

    kept, excluded, pruned = _apply_exclude(tmp_path, lines, ())
    assert list(kept) == ["src.py"]
    assert excluded == []                    # 사용자 exclude 와 따로 센다 (R4)
    assert len(pruned) == 3


def test_a_broken_adapter_module_does_not_take_the_whole_report_down(tmp_path, monkeypatch):
    """어댑터 하나가 import 에서 터지면 항목 일곱이 전부 오류가 됐다 (확정 3).

    실측: `scripts/mutation/` 에 `raise` 한 줄짜리 파일을 두었더니 종료 코드는 0 인데
    (R2 는 지켜진다) 리포트가 "게이트 내부 오류" 한 줄이 되고 복잡도·CRAP·중복처럼
    뮤테이션과 무관한 항목까지 함께 죽었다. 설정 블록의 언어 칸도 통째로 사라져,
    정상 회차와 구분이 안 됐다.
    """
    def boom():
        raise RuntimeError("어댑터가 import 중에 터진다")

    monkeypatch.setattr(code_gate.mutation_pkg, "adapters", boom)

    config = load_config(tmp_path / "no-such-config.json")
    assert config.mutation_tools == ()
    assert any("뮤테이션 어댑터를 불러오지 못해" in note for note in config.notes)

    # 도구 탐지와 기본값 조회도 같은 문을 지난다 — 여기서 터지면 R2 가 깨진다.
    tools = {"node": {"available": True, "path": "node", "install_hint": None}}
    code_gate._probe_adapter_tools(tools)
    assert set(tools) == {"node"}
    assert code_gate._adapter_tool_defaults() == {}

    # 언어 칸이 사라진 이유를 스키마가 말한다. 정상 회차에는 이 칸이 없다.
    assert _config_payload(config)["mutation"]["languages_unavailable"] is True
    assert _config_payload(None)["mutation"]["languages_unavailable"] is True


def test_a_healthy_registry_does_not_add_the_unavailable_flag(tmp_path):
    """정상 회차의 설정 스키마는 그대로다 — 칸을 늘리면 소비자가 흔들린다."""
    payload = _config_payload(load_config(tmp_path / "no-such-config.json"))
    assert "languages_unavailable" not in payload["mutation"]
    assert payload["mutation"]["javascript"] == "stryker"
    assert "languages_unavailable" not in _config_payload(None)["mutation"]


def test_gradle_work_cache_is_pruned(tmp_path):
    """자바 회차가 남긴 `.gradle` 이 다음 회차의 변경분으로 잡혔다 (확정 4).

    실측: `.gitignore` 가 없는 Gradle 저장소에서 소스 하나만 고쳤는데 두 번째 회차의
    변경 파일이 13개가 됐다. 게이트가 자기 산출물을 자기 검사 대상으로 되먹는 자리라
    R3("변경분만 검사")를 스스로 깬다. `build` 는 이미 빠져 있었고 `.gradle` 만 빠졌다.
    """
    _write(tmp_path / "src/main/java/demo/A.java", "package demo;\nclass A {}\n")
    _write(tmp_path / ".gradle" / "9.7.1" / "executionHistory" / "executionHistory.bin", "x")
    _write(tmp_path / "build" / "classes" / "A.class", "x")
    lines = {"src/main/java/demo/A.java": None,
             ".gradle/9.7.1/executionHistory/executionHistory.bin": None,
             "build/classes/A.class": None}
    kept, _excluded, pruned = _apply_exclude(tmp_path, lines, ())
    assert list(kept) == ["src/main/java/demo/A.java"]
    assert len(pruned) == 2


# ---------------------------------------------------------------------------
# 6 — 설정 파일 폴백 (R6)
# ---------------------------------------------------------------------------

def test_config_missing_falls_back_to_defaults(tmp_path):
    config = load_config(tmp_path / "nope.json")
    assert config.crap_threshold == DEFAULT_CRAP_THRESHOLD
    assert config.complexity_threshold == DEFAULT_COMPLEXITY_THRESHOLD
    assert config.source is None
    assert any("기본값" in note for note in config.notes)


def test_config_broken_json_falls_back_without_raising(tmp_path):
    """깨진 설정 파일이 게이트를 죽이면 안 된다 — 기본값으로 내려가고 사유를 남긴다."""
    path = _write(tmp_path / ".code-gate.json", "{ not json ,,,")
    config = load_config(path)
    assert config.crap_threshold == DEFAULT_CRAP_THRESHOLD
    assert any("읽지 못해" in note for note in config.notes)


@pytest.mark.parametrize("bad", ["여섯", 0, -3, True])
def test_config_invalid_threshold_recovers_to_default(tmp_path, bad):
    path = _write(tmp_path / ".code-gate.json", json.dumps({"crap_threshold": bad}))
    config = load_config(path)
    assert config.crap_threshold == DEFAULT_CRAP_THRESHOLD
    assert any("crap_threshold" in note for note in config.notes)


def test_config_reads_valid_values(tmp_path):
    path = _write(tmp_path / ".code-gate.json", json.dumps({
        "crap_threshold": 4, "complexity_threshold": 8,
        "duplication": {"min_lines": 3, "min_tokens": 20},
        "exclude": ["vendor/**"], "layers_file": "custom.json",
    }))
    config = load_config(path)
    assert (config.crap_threshold, config.complexity_threshold) == (4, 8)
    assert (config.dup_min_lines, config.dup_min_tokens) == (3, 20)
    assert config.exclude == ("vendor/**",) and config.layers_file == "custom.json"
    assert config.source == str(path)


def test_config_not_a_dict_falls_back(tmp_path):
    path = _write(tmp_path / ".code-gate.json", "[1, 2, 3]")
    config = load_config(path)
    assert config.crap_threshold == DEFAULT_CRAP_THRESHOLD
    assert any("JSON 객체가 아니라" in note for note in config.notes)


def test_repo_config_file_keeps_the_agent_edit_warning():
    """기준값 파일의 '사람만 수정' 문구가 사라지면 R6 의 절반이 빈다.

    스크립트 상단 주석과 설정 파일 양쪽에 있어야 한 쪽만 읽은 세션이 그냥 못 고친다.
    """
    data = json.loads((REPO_ROOT / ".code-gate.json").read_text(encoding="utf-8"))
    assert "사람만 수정" in data["_주의"]
    assert "사람만 수정" in SCRIPT.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 7 — 도구 부재 (R1·R4)
# ---------------------------------------------------------------------------

def test_missing_tools_are_skipped_with_install_hint_and_time(tmp_path):
    """검사를 안 했는데 통과처럼 보이면 안 된다 — 건너뜀 + 설치 방법 + 시간."""
    _write(tmp_path / "tests" / "test_a.py", "def test_x():\n    assert True\n")
    _write(tmp_path / "pkg.py", "def f():\n    return 1\n")
    results = {r.code: r for r in run_checks(_ctx(tmp_path, files=["pkg.py"]))}

    for code in ("C1", "C3", "C5"):
        assert results[code].status == "skipped", code
        assert results[code].install_hint, f"{code} 는 설치 방법을 함께 적어야 한다"
    assert all(r.seconds >= 0.0 for r in results.values())
    assert all("통과" not in r.human_reason for r in results.values() if r.status == "skipped")


def test_every_check_reports_seconds(tmp_path):
    """항목별 실행 시간은 이 도구의 주 산출물이다 (R1). 건너뛴 항목도 초를 찍는다."""
    results = run_checks(_ctx(tmp_path, files=["pkg.py"]))
    assert len(results) == len(CHECKS)
    for result in results:
        payload = result.to_dict()
        assert "seconds" in payload and isinstance(payload["seconds"], float)


@pytest.mark.parametrize("output", ["", "# pass 0\n# fail 0\n", "아무 형식도 아닌 출력\n"])
def test_js_zero_tests_is_skipped_not_ok(output):
    """테스트가 한 개도 안 돌았으면 통과가 아니다 (R4).

    파이썬 쪽에는 같은 뜻의 가드가 이미 있다(pytest 종료 코드 5). 이쪽에만 없어서,
    테스트 파일이 node 의 기본 탐색 밖에 있는 프로젝트에서 헤드라인 항목이
    '0개 통과, 0개 실패' 초록으로 떴다.
    """
    outcome = _js_outcome("node", output, 0)
    assert outcome["status"] == "skipped"
    assert "통과" not in outcome["human"]


def test_js_passing_run_is_ok():
    assert _js_outcome("node", "# pass 3\n# fail 0\n", 0)["status"] == "ok"


def test_js_failures_are_findings():
    assert _js_outcome("node", "# pass 1\n# fail 2\n", 1)["status"] == "findings"


@pytest.mark.parametrize("line, runner", [
    (" Tests  4 passed (4)", "vitest"),
    ("Tests:       3 passed, 3 total", "jest"),
])
def test_js_summary_line_runners_are_counted(line, runner):
    """vitest·jest 는 TAP 을 내지 않는다 — 요약줄을 읽어야 통과를 통과로 셀 수 있다."""
    outcome = _js_outcome(runner, line + "\n", 0)
    assert outcome["status"] == "ok"


def test_complexity_all_rows_discarded_is_an_error_not_a_pass(tmp_path, monkeypatch):
    """lizard 출력이 전량 폐기되면 '함수 0개 모두 기준 이하'가 아니라 오류다 (R4).

    lizard 는 파싱 실패와 무관하게 종료 코드 0 으로 끝나서, 종료 코드만 보면 C3 가
    영구히 통과하고 C4 는 영구히 건너뜀이 된다 — 복잡도 30짜리 함수를 넣어도 초록이다.
    """
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _FakeProc(stdout="1,2,3\n"))
    outcome = check_complexity(_ctx(tmp_path, files=["a.py"], tools=_with_lizard()))
    assert outcome["status"] == "error"
    assert "통과" not in outcome["human_reason"]


def test_complexity_partial_discard_is_visible_in_the_status_row(tmp_path, monkeypatch):
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _FakeProc(stdout="1,2,3\n" + GOOD_CSV))
    ctx = _ctx(tmp_path, files=["scripts/preflight.py"])
    ctx.tools.update(_with_lizard())
    outcome = check_complexity(ctx)
    assert outcome["status"] == "ok"
    assert "형식 불일치로 버린 출력 1건" in outcome["human_reason"]


def test_no_changed_files_skips_every_check(tmp_path):
    ctx = _ctx(tmp_path)
    object.__setattr__(ctx.change, "skip_reason", "변경된 파일이 없습니다.")
    results = run_checks(ctx)
    assert {r.status for r in results} == {"skipped"}
    assert all("변경된 파일이 없습니다." == r.human_reason for r in results)


# ---------------------------------------------------------------------------
# 8 — 의존 방향
# ---------------------------------------------------------------------------

def test_layers_rules_missing_is_skipped_in_korean(tmp_path):
    outcome = check_layers(_ctx(tmp_path, files=["a.py"]))
    assert outcome["status"] == "skipped"
    assert ".code-gate-layers.json" in outcome["human_reason"]


def _layered_repo(tmp_path):
    _write(tmp_path / "ui" / "__init__.py", "")
    _write(tmp_path / "ui" / "view.py", "VALUE = 1\n")
    _write(tmp_path / "core" / "__init__.py", "")
    _write(tmp_path / ".code-gate-layers.json", json.dumps({
        "layers": {"core": ["core/**"], "ui": ["ui/**"]},
        "forbidden": [{"from": "core", "to": "ui", "reason": "core 는 ui 를 몰라야 합니다"}],
    }))


def test_layers_detects_forbidden_python_import(tmp_path):
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "bad.py", "import os\nfrom ui.view import VALUE\n")
    outcome = check_layers(_ctx(tmp_path, files=["core/bad.py"]))
    assert outcome["status"] == "findings"
    finding = outcome["findings"][0]
    assert finding["from_file"] == "core/bad.py"
    assert finding["to_file"] == "ui/view.py"
    assert finding["line"] == 2


def test_layers_passes_when_direction_is_allowed(tmp_path):
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "good.py", "VALUE = 2\n")
    _write(tmp_path / "ui" / "ok.py", "from core.good import VALUE\n")
    outcome = check_layers(_ctx(tmp_path, files=["ui/ok.py", "core/good.py"]))
    assert outcome["status"] == "ok" and not outcome.get("findings")


def test_layers_detects_relative_javascript_import(tmp_path):
    _write(tmp_path / "ui" / "view.js", "export const V = 1;\n")
    _write(tmp_path / "core" / "bad.js", "import { V } from '../ui/view.js';\n")
    _write(tmp_path / ".code-gate-layers.json", json.dumps({
        "layers": {"core": ["core/**"], "ui": ["ui/**"]},
        "forbidden": [{"from": "core", "to": "ui", "reason": "금지"}],
    }))
    outcome = check_layers(_ctx(tmp_path, files=["core/bad.js"]))
    assert outcome["status"] == "findings"
    assert outcome["findings"][0]["to_file"] == "ui/view.js"


def test_layers_reports_files_it_could_not_parse(tmp_path):
    """편집 중이라 문법이 깨진 파일이 '위반 없음'으로 통과하면 안 된다 (R4).

    실측 회귀: core→ui 위반 import 를 그대로 둔 채 파일 끝에 문법 오류만 더하면
    '통과 | 규칙 1건 기준 위반 없음' 으로 바뀌고 참고란에도 아무 언급이 없었다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "broken.py", "from ui.view import VALUE\ndef broken(:\n")
    ctx = _ctx(tmp_path, files=["core/broken.py"])
    outcome = check_layers(ctx)
    assert outcome["status"] != "ok"
    assert any("파싱하지 못해" in note for note in ctx.notes)


def test_layers_skips_when_no_changed_file_belongs_to_a_layer(tmp_path):
    """레이어에 속한 파일이 0개면 '통과'가 아니라 '건너뜀'이다 (R4)."""
    _layered_repo(tmp_path)
    _write(tmp_path / "README.md", "# hi\n")
    outcome = check_layers(_ctx(tmp_path, files=["README.md"]))
    assert outcome["status"] == "skipped"


def test_layers_pass_message_states_how_many_files_were_scanned(tmp_path):
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "good.py", "VALUE = 2\n")
    outcome = check_layers(_ctx(tmp_path, files=["core/good.py"]))
    assert outcome["status"] == "ok"
    assert "변경 파일 1개" in outcome["human_reason"]


def test_repo_layer_rules_exempt_the_test_directory():
    """`scripts/*.py` 의 `*` 는 `/` 를 넘어 매치된다 — tests 를 먼저 잡아야 한다.

    이 순서가 뒤집히면 scripts/tests 아래 파일이 core 로 잡혀, 결합 룰 확인용으로
    evals 를 import 하는 테스트를 넣는 순간 core→harness 오탐이 난다.
    """
    layers = json.loads((REPO_ROOT / ".code-gate-layers.json").read_text(encoding="utf-8"))["layers"]
    assert code_gate._layer_of("scripts/tests/test_code_gate.py", layers) == "tests"
    assert code_gate._layer_of("scripts/code_gate.py", layers) == "core"
    assert code_gate._layer_of("evals/runner/coupling.py", layers) == "harness"


def test_match_glob_is_the_single_matcher():
    """exclude 와 레이어 규칙이 같은 함수를 쓴다. `**` 는 구분자를 넘어 매치된다."""
    assert _match_glob("scripts/tests/test_x.py", "scripts/**")
    assert _match_glob("scripts/a.py", "scripts/*.py")
    assert not _match_glob("evals/a.py", "scripts/**")


# ---------------------------------------------------------------------------
# 9 — 항목 격리 (R2)
# ---------------------------------------------------------------------------

def test_timeout_isolates_one_check_and_continues(tmp_path, monkeypatch):
    """한 항목이 시간 초과해도 나머지 항목은 계속 돌아야 한다 (R2)."""
    def slow(ctx):
        raise subprocess.TimeoutExpired(cmd=["sleep"], timeout=DEFAULT_TIMEOUT_SECONDS)

    def fine(ctx):
        return {"status": "ok", "reason": "ok", "human_reason": "정상"}

    monkeypatch.setattr(code_gate, "CHECKS", (
        ("C1", "tests", "테스트", slow),
        ("C2", "coverage", "커버리지", fine),
    ))
    results = run_checks(_ctx(tmp_path, files=["a.py"]))
    assert results[0].status == "timeout"
    assert f"{DEFAULT_TIMEOUT_SECONDS}초" in results[0].human_reason
    assert results[1].status == "ok"


def test_unexpected_exception_isolates_one_check(tmp_path, monkeypatch):
    def boom(ctx):
        raise RuntimeError("터졌다")

    def fine(ctx):
        return {"status": "ok", "reason": "ok", "human_reason": "정상"}

    monkeypatch.setattr(code_gate, "CHECKS", (
        ("C1", "tests", "테스트", boom),
        ("C2", "coverage", "커버리지", fine),
    ))
    results = run_checks(_ctx(tmp_path, files=["a.py"]))
    assert results[0].status == "error" and "터졌다" in results[0].human_reason
    assert results[1].status == "ok"


def test_error_payload_keeps_the_normal_schema():
    payload = code_gate._error_payload(RuntimeError("깨짐"), 0.0)
    assert payload["exit_code"] == 0
    assert payload["error"].startswith("RuntimeError")
    assert len(payload["checks"]) == len(CHECKS)
    assert all("seconds" in c for c in payload["checks"])
    assert "total_seconds" in payload


def test_error_payload_config_has_the_same_keys_as_a_normal_run(tmp_path):
    """크래시했을 때만 config 키가 빠지면 소비자가 하필 그 순간 KeyError 로 죽는다.

    종료 코드 0 으로 흐름을 안 끊겠다는 R2 의 취지가 소비자 쪽에서 무너지는 지점이다.
    """
    normal = _config_payload(load_config(tmp_path / "nope.json"))
    crashed = code_gate._error_payload(RuntimeError("깨짐"), 0.0)["config"]
    assert set(crashed) == set(normal)
    assert set(crashed["duplication"]) == set(normal["duplication"])


# ---------------------------------------------------------------------------
# 10 — 종료 코드 0 보장 (CLI 실측, R2)
# ---------------------------------------------------------------------------

def _run_cli(*args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=120,
    )


def test_cli_exits_zero_outside_a_git_repository(tmp_path):
    """git 저장소가 아닌 곳에서도 트레이스백 없이 종료 코드 0 이어야 한다 (R2)."""
    proc = _run_cli("--json", "--repo-root", str(tmp_path), cwd=tmp_path)
    assert proc.returncode == 0
    assert "Traceback" not in proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["exit_code"] == 0
    assert "total_seconds" in payload
    assert all("seconds" in check for check in payload["checks"])


def test_cli_exits_zero_with_missing_config_path(tmp_path):
    proc = _run_cli("--json", "--repo-root", str(tmp_path),
                    "--config", str(tmp_path / "없는파일.json"), cwd=tmp_path)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["config"]["crap_threshold"] == DEFAULT_CRAP_THRESHOLD


def test_cli_human_report_is_korean_and_shows_time(tmp_path):
    proc = _run_cli("--repo-root", str(tmp_path), cwd=tmp_path)
    assert proc.returncode == 0
    assert "검사 게이트 0단계" in proc.stdout
    assert "전체" in proc.stdout and "초" in proc.stdout
    assert "준비" in proc.stdout      # 항목 합 밖의 시간도 드러난다 (R1)


@pytest.mark.parametrize("extra", [["--bogus"], ["--track", "fast"], ["--mode=subagent"]])
def test_cli_exits_zero_on_unknown_arguments(tmp_path, extra):
    """인자 오류로 게이트가 비-0 종료하면 흐름이 멈춘다 (R2).

    `parse_args` 가 던지는 SystemExit 는 BaseException 이라 `except Exception` 에
    안 걸린다. 실측에서 `--bogus` / `--track fast` / `--base`(값 누락)가 전부
    종료 코드 2 였다. 모르는 인자는 받아들이는 게 아니라 무시하고 참고란에 적는다.
    """
    proc = _run_cli("--json", "--repo-root", str(tmp_path), *extra, cwd=tmp_path)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert any("알 수 없는 인자" in note for note in payload["notes"])


def test_cli_exits_zero_when_an_option_value_is_missing(tmp_path):
    proc = _run_cli("--json", "--base", cwd=tmp_path)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["exit_code"] == 0
    assert "인자를 해석하지 못했습니다" in (payload["error"] or "")


def test_cli_help_still_exits_zero(tmp_path):
    proc = _run_cli("--help", cwd=tmp_path)
    assert proc.returncode == 0
    assert "--base" in proc.stdout


def _init_git_repo(tmp_path):
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=str(tmp_path), capture_output=True, text=True, check=False)


@pytest.mark.skipif(not code_gate.shutil.which("git"), reason="git 없음")
def test_cli_exits_zero_when_the_test_suite_fails(tmp_path):
    """대상 프로젝트의 테스트가 실패해도 게이트 종료 코드는 0 이다 (R2).

    서브프로세스의 종료 코드를 게이트 종료 코드로 전파하면 게이트가 흐름을 막는
    차단기가 된다. 0단계는 리포트만 한다.
    """
    _init_git_repo(tmp_path)
    _write(tmp_path / "pkg.py", "def f(x):\n    return x + 1\n")
    _write(tmp_path / "tests" / "test_pkg.py", "def test_fails():\n    assert False\n")
    proc = _run_cli("--json", "--repo-root", str(tmp_path), cwd=tmp_path)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    tests = next(c for c in payload["checks"] if c["code"] == "C1")
    assert tests["status"] in ("findings", "skipped")
    if tests["status"] == "findings":
        assert "실패" in tests["human_reason"]


@pytest.mark.skipif(not code_gate.shutil.which("git"), reason="git 없음")
def test_exclude_glob_removes_files_and_is_reported(tmp_path):
    """exclude 로 뺀 파일 수가 리포트에 남아야 한다 — 조용히 빠지면 안 된다 (R4)."""
    _init_git_repo(tmp_path)
    _write(tmp_path / "keep.py", "x = 1\n")
    _write(tmp_path / "vendor" / "skip.py", "y = 2\n")
    change = collect_changes(tmp_path, "HEAD", "", ("vendor/**",))
    assert "keep.py" in change.files
    assert change.excluded == ("vendor/skip.py",)


@pytest.mark.skipif(not code_gate.shutil.which("git"), reason="git 없음")
def test_untracked_dependency_files_do_not_enter_the_change_set(tmp_path):
    """npm install / venv 직후가 정확히 이 상태다 — 의존성이 아직 gitignore 되기 전."""
    _init_git_repo(tmp_path)
    _write(tmp_path / "src.py", "x = 1\n")
    for i in range(3):
        _write(tmp_path / "node_modules" / "pkg" / f"m{i}.js", "export default 1;\n")
    change = collect_changes(tmp_path, "HEAD", "", ())
    assert "src.py" in change.files
    assert not any(f.startswith("node_modules/") for f in change.files)
    assert len(change.pruned) == 3


@pytest.mark.skipif(not code_gate.shutil.which("git"), reason="git 없음")
def test_unresolvable_base_is_reported_not_silent(tmp_path):
    """없는 ref 를 base 로 주면 아무것도 비교하지 못했다는 사실이 남아야 한다 (R4).

    실측 회귀: `--base no-such-ref` 가 '변경 파일 0개 / 여섯 항목 전부 건너뜀' 이라는
    완전히 깨끗한 리포트를 냈다. 경고도 참고 문구도 없었다.
    """
    _init_git_repo(tmp_path)
    _write(tmp_path / "a.py", "x = 1\n")
    for args in (["add", "-A"], ["commit", "-m", "c"]):
        subprocess.run(["git", *args], cwd=str(tmp_path), capture_output=True, check=False)
    change = collect_changes(tmp_path, "no-such-ref", "", ())
    assert "no-such-ref" in change.base_problem

    proc = _run_cli("--repo-root", str(tmp_path), "--base", "no-such-ref", cwd=tmp_path)
    assert proc.returncode == 0
    assert "no-such-ref" in proc.stdout


@pytest.mark.skipif(not code_gate.shutil.which("git"), reason="git 없음")
def test_content_free_rename_stays_in_the_change_set(tmp_path):
    """내용 변경 없는 rename 커밋이 통째로 빠지면 의존 방향 검사가 못 돈다."""
    _init_git_repo(tmp_path)
    _write(tmp_path / "ui" / "mod.py", "VALUE = 1\n")
    for args in (["add", "-A"], ["commit", "-m", "first"]):
        subprocess.run(["git", *args], cwd=str(tmp_path), capture_output=True, check=False)
    (tmp_path / "core").mkdir(parents=True, exist_ok=True)
    for args in (["mv", "ui/mod.py", "core/mod.py"], ["commit", "-m", "move"]):
        subprocess.run(["git", *args], cwd=str(tmp_path), capture_output=True, check=False)

    change = collect_changes(tmp_path, "HEAD~1", "", ())
    assert "core/mod.py" in change.files


# ---------------------------------------------------------------------------
# 11 — 인터페이스에 흐름 구분 인자가 없음 (R5)
# ---------------------------------------------------------------------------

FLOW_TOKENS = ("track", "mode", "flow", "stage", "profile", "only", "fail-under", "fail_under")


def test_cli_has_no_flow_discriminating_arguments():
    """게이트 안에 '누가 불렀는지' 를 아는 코드가 생기면 안 된다 (R5).

    호출 흐름별 분기 인자를 받으면 게이트가 흐름을 알게 되고, 두 흐름이 같은
    게이트를 공유한다는 전제가 깨진다.
    """
    parser = build_parser()
    names = []
    for action in parser._actions:
        names += [opt.lstrip("-").lower() for opt in action.option_strings]
        names.append(str(action.dest).lower())
    for token in FLOW_TOKENS:
        assert not any(token in name for name in names), f"금지된 인자 이름: {token}"


def test_cli_exposes_only_the_agreed_arguments():
    """인자를 늘릴 때 근거를 대게 하는 자물쇠다. 늘리려면 이 목록을 먼저 고쳐야 한다.

    `--limit` 은 **보여 주는 줄 수**만 정한다. 무엇을 재는지도, 무엇을 위반으로
    보는지도, 종료 코드도 바꾸지 않는다. 그래서 `--only`(재는 항목을 고름)나
    `--fail-under`(종료 코드 계약을 깸)와 다르고, 그 둘은 여전히 없다.
    """
    parser = build_parser()
    options = {opt for action in parser._actions for opt in action.option_strings}
    assert options == {"-h", "--help", "--base", "--config", "--repo-root", "--json", "--limit"}


# ---------------------------------------------------------------------------
# 12 — 비-0 종료를 유발하는 인자 차단 (R2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("token", list(code_gate._FORBIDDEN_SUBPROCESS_ARGS))
def test_forbidden_arguments_appear_only_in_the_block_list(token):
    """금지 인자 문자열이 실제 명령줄 조립부에 다시 등장하면 회귀다.

    pytest -x / node --test-coverage-* / jest --coverageThreshold / jscpd --threshold 는
    임계 미달 시 도구를 비-0 으로 종료시키고, npx --yes 는 동의 없이 네트워크에서
    패키지를 받아온다. 둘 다 0단계 계약을 깬다.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count(f'"{token}"') == 1, f"{token} 이 차단 목록 밖에서도 쓰이고 있다"


@pytest.mark.parametrize("token", list(code_gate._FORBIDDEN_SUBPROCESS_ARGS))
def test_forbidden_arguments_are_rejected_at_run_time(token, tmp_path):
    assert _forbidden_arg(["pytest", token]) == token
    with pytest.raises(ValueError):
        _run(["pytest", token], cwd=tmp_path, timeout=5)


def test_forbidden_check_also_catches_equals_form():
    assert _forbidden_arg(["node", "--test-coverage-lines=90"]) == "--test-coverage-lines=90"
    assert _forbidden_arg(["node", "--test-coverage-include=src/a.js"]) is None


def test_all_subprocesses_go_through_the_single_gateway():
    """서브프로세스는 `_run` 한 곳에서만 뜬다 — 금지 인자 검사를 우회할 길을 막는다."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count("subprocess.run(") == 1


# ---------------------------------------------------------------------------
# 15 — 뮤테이션 (C7)
#
# 아래 리포트 조각은 Stryker 10 을 실제로 돌려 얻은 값 그대로다. 손으로 지어낸 값으로
# 파서를 맞추면, 형식이 조금이라도 다를 때 시험은 통과하는데 실제 실행은 못 읽는다.
# ---------------------------------------------------------------------------

VALIDATE_SOURCE = (
    "export function isAdult(age) {\n"
    "  return age >= 18;\n"
    "}\n"
    "\n"
    "export function describe(user) {\n"
    '  const name = user.name || "guest";\n'
    '  const level = user.score > 50 ? "high" : "low";\n'
    '  return name + ":" + level;\n'
    "}\n"
)

# src/validate.js 를 대상으로 한 실제 실행의 리포트에서 옮긴 것 (변이 4개만 발췌).
STRYKER_REPORT = {
    "schemaVersion": "1.0",
    "testFiles": {
        "test/validate.test.js": {
            "tests": [
                {"id": "0", "name": "isAdult 호출만 하고 결과 유형만 본다"},
                {"id": "1", "name": "describe 문자열이 나오기만 하면 통과"},
            ],
        },
    },
    "files": {
        "src/validate.js": {
            "language": "javascript",
            "source": VALIDATE_SOURCE,
            "mutants": [
                {"id": "9", "mutatorName": "StringLiteral", "replacement": '""',
                 "status": "NoCoverage", "static": False, "coveredBy": [],
                 "location": {"start": {"line": 6, "column": 29}, "end": {"line": 6, "column": 36}}},
                {"id": "15", "mutatorName": "StringLiteral", "replacement": '""',
                 "status": "NoCoverage", "static": False, "coveredBy": [],
                 "location": {"start": {"line": 7, "column": 44}, "end": {"line": 7, "column": 49}}},
                {"id": "1", "mutatorName": "ConditionalExpression", "replacement": "true",
                 "status": "Survived", "static": False, "testsCompleted": 1, "coveredBy": ["0"],
                 "location": {"start": {"line": 2, "column": 10}, "end": {"line": 2, "column": 19}}},
                {"id": "0", "mutatorName": "BlockStatement", "replacement": "{}",
                 "statusReason": "expected 'undefined' to be 'boolean' // Object.is equality",
                 "status": "Killed", "static": False, "testsCompleted": 1,
                 "killedBy": ["0"], "coveredBy": ["0"],
                 "location": {"start": {"line": 1, "column": 30}, "end": {"line": 3, "column": 2}}},
            ],
        },
    },
}


def _with_stryker(repo_root=None):
    """Stryker 만 설치된 상태. 러너 플러그인 디렉토리도 함께 만든다."""
    tools = _no_tools()
    tools["stryker"] = {"available": True, "path": "/fake/stryker",
                        "install_hint": "npm i -D @stryker-mutator/core"}
    if repo_root is not None:
        (repo_root / "node_modules" / "@stryker-mutator" / "vitest-runner").mkdir(parents=True, exist_ok=True)
    return tools


# --- D1 점수 공식 --------------------------------------------------------

def test_mutation_score_keeps_no_coverage_in_the_denominator():
    """NoCoverage 를 분모에서 빼면 테스트가 없는 코드가 점수에서 사라진다.

    그러면 테스트를 안 쓸수록 점수가 오르는 값이 되어, 재는 의미 자체가 뒤집힌다.
    아래 두 값이 갈리는 것이 D1 의 핵심이다.
    """
    assert mutation_score({"Killed": 5, "Survived": 0, "NoCoverage": 5}) == 50.0
    assert mutation_score({"Killed": 5, "Survived": 0}) == 100.0


def test_mutation_score_counts_timeout_as_killed():
    """변이가 무한루프를 만들었고 테스트 실행이 그것을 걸어 세웠으니 감지된 것으로 본다."""
    assert mutation_score({"Killed": 5, "Timeout": 2}) == 100.0
    assert mutation_score({"Timeout": 1, "Survived": 1}) == 50.0


@pytest.mark.parametrize("status", ["CompileError", "RuntimeError", "Ignored", "Pending"])
def test_mutation_score_excludes_non_results_from_the_denominator(status):
    """테스트의 성적이 아닌 상태는 분모에 넣지 않는다 — 넣으면 점수가 부당하게 내려간다."""
    assert mutation_score({"Killed": 2, "Survived": 2, status: 96}) == 50.0


def test_mutation_score_is_none_when_nothing_is_scorable():
    """분모가 0 이면 0% 가 아니라 '잰 것이 없음'이다. 0% 로 내면 나쁜 성적처럼 보인다 (R4)."""
    assert mutation_score({}) is None
    assert mutation_score({"Ignored": 4}) is None


@pytest.mark.parametrize("counts, expected", [
    ({"Killed": 13, "Survived": 15, "NoCoverage": 12}, 32.50),
    ({"Killed": 5, "Timeout": 2}, 100.00),
    ({"Killed": 2, "Survived": 11, "Ignored": 4}, 15.38),
])
def test_mutation_score_matches_the_measured_stryker_total(counts, expected):
    """Stryker 가 화면에 찍는 total 점수와 같은 값이 나와야 한다 — 실제 실행 세 건으로 확인한 조합이다."""
    assert mutation_score(counts) == expected


# --- 리포트 파싱 ---------------------------------------------------------

def test_parse_mutation_report_reads_real_stryker_output():
    summary = parse_mutation_report(STRYKER_REPORT)
    assert summary["total"] == 4
    assert summary["counts"] == {"NoCoverage": 2, "Survived": 1, "Killed": 1}
    assert summary["score"] == 25.0        # 1 / (1 + 1 + 2)
    assert summary["files"] == ["src/validate.js"]
    assert [r["status"] for r in summary["survivors"]] == ["Survived", "NoCoverage", "NoCoverage"]


def test_parse_mutation_report_rebuilds_the_original_text():
    """리포트에는 바뀐 것만 있고 원본 텍스트 필드가 없다 — 소스를 위치로 잘라 만들어야 한다."""
    survivor = parse_mutation_report(STRYKER_REPORT)["survivors"][0]
    assert survivor["original"] == "age >= 18"
    assert survivor["replacement"] == "true"
    assert (survivor["file"], survivor["line"], survivor["column"]) == ("src/validate.js", 2, 10)
    assert survivor["mutator"] == "ConditionalExpression"


def test_parse_mutation_report_names_the_tests_that_failed_to_catch_it():
    """id 만으로는 어느 테스트를 고칠지 알 수 없다. 이름은 최상위 testFiles 에 따로 있다."""
    survivor = parse_mutation_report(STRYKER_REPORT)["survivors"][0]
    assert survivor["tests"] == ["test/validate.test.js > isAdult 호출만 하고 결과 유형만 본다"]


def test_parse_mutation_report_drops_files_outside_the_change_set():
    """증분 실행을 켜면 지난 회차 파일이 이번 리포트에 섞인다 — 걸러내지 않으면 R3 이 깨진다."""
    leaked = json.loads(json.dumps(STRYKER_REPORT))
    leaked["files"]["src/legacy.js"] = {
        "source": "export const x = 1;\n",
        "mutants": [{"id": "99", "mutatorName": "ArithmeticOperator", "replacement": "2",
                     "status": "Survived", "coveredBy": [],
                     "location": {"start": {"line": 1, "column": 18}, "end": {"line": 1, "column": 19}}}],
    }
    assert parse_mutation_report(leaked)["total"] == 5
    narrowed = parse_mutation_report(leaked, {"src/validate.js"})
    assert narrowed["total"] == 4
    assert narrowed["files"] == ["src/validate.js"]


@pytest.mark.parametrize("report", [{}, {"files": None}, {"files": {}}, []])
def test_parse_mutation_report_survives_a_broken_report(report):
    summary = parse_mutation_report(report)
    assert summary["total"] == 0 and summary["score"] is None


def test_slice_source_restores_a_multiline_mutant():
    """여러 줄에 걸친 변이도 그대로 복원돼야 한다. 줄·열 모두 1부터 세고 끝은 포함하지 않는다."""
    block = STRYKER_REPORT["files"]["src/validate.js"]["mutants"][3]
    assert slice_source(VALIDATE_SOURCE, block["location"]) == "{\n  return age >= 18;\n}"


@pytest.mark.parametrize("location", [
    None, {}, {"start": {"line": 99, "column": 1}, "end": {"line": 99, "column": 3}},
    {"start": {"line": 2, "column": 1}, "end": {"line": 1, "column": 3}},
])
def test_slice_source_returns_empty_on_impossible_locations(location):
    assert slice_source(VALIDATE_SOURCE, location) == ""


# --- 예산 초과 시 부분 결과 (D4) -----------------------------------------

def test_parse_mutation_events_uses_the_names_already_in_the_event(tmp_path):
    """이벤트 파일의 coveredBy 에는 테스트 이름이 이미 박혀 있어 id 사전이 필요 없다."""
    events = [
        {"fileName": str(tmp_path / "src" / "math.js"), "id": "10", "mutatorName": "BlockStatement",
         "replacement": "{}", "status": "Killed", "coveredBy": ["test/math.test.js#add 두 수를 더한다"],
         "location": {"start": {"line": 1, "column": 30}, "end": {"line": 1, "column": 32}}},
        {"fileName": str(tmp_path / "src" / "math.js"), "id": "11", "mutatorName": "ArithmeticOperator",
         "replacement": "a - b", "status": "Survived", "coveredBy": ["test/math.test.js#add 두 수를 더한다"],
         "location": {"start": {"line": 1, "column": 30}, "end": {"line": 1, "column": 35}}},
    ]
    summary = parse_mutation_events(events, tmp_path, {"src/math.js": "export const add = (a, b) => a + b;\n"})
    assert summary["total"] == 2 and summary["score"] == 50.0
    assert summary["survivors"][0]["tests"] == ["test/math.test.js#add 두 수를 더한다"]
    assert summary["survivors"][0]["original"] == "a + b"


def test_mutation_partial_says_how_many_of_how_many_were_seen(tmp_path):
    """예산이 끊겼을 때 못 본 것을 말하지 않으면 부분 결과가 전체처럼 읽힌다 (D4·R4)."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    _write(events_dir / "00001-onMutationTestingPlanReady.json",
           json.dumps({"mutantPlans": [
               {"plan": "runTest", "mutant": {"id": str(i), "fileName": str(tmp_path / "src" / "a.js")}}
               for i in range(40)]}))
    _write(events_dir / "00002-onMutantTested.json", json.dumps(
        {"fileName": str(tmp_path / "src" / "a.js"), "mutatorName": "ArithmeticOperator",
         "replacement": "a - b", "status": "Survived", "coveredBy": ["t.js#덧셈"],
         "location": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 6}}}))
    _write(tmp_path / "src" / "a.js", "a + b;\n")

    ctx = _ctx(tmp_path, files=["src/a.js"])
    outcome = _mutation_partial(ctx, {"events": events_dir}, ("src/a.js",), 600.0, 600)
    assert outcome["status"] == "timeout"
    assert "40개 중 1개까지" in outcome["human_reason"]
    assert "전체 점수가 아닙니다" in outcome["human_reason"]
    assert "통과" not in outcome["human_reason"]
    assert len(outcome["findings"]) == 1


def test_mutation_partial_with_nothing_collected_is_not_a_pass(tmp_path):
    ctx = _ctx(tmp_path)
    outcome = _mutation_partial(ctx, {"events": tmp_path / "nowhere"}, (), 600.0, 600)
    assert outcome["status"] == "timeout"
    assert "하나도 재지 못했습니다" in outcome["human_reason"]


# --- 건너뜀·오류가 통과로 보이지 않는가 (R4) ------------------------------

def test_mutation_skipped_when_stryker_is_missing(tmp_path):
    outcome = check_mutation(_ctx(tmp_path, files=["src/a.js"]))
    assert outcome["status"] == "skipped"
    assert outcome["install_hint"] == "npm i -D @stryker-mutator/core"
    assert "통과" not in outcome["human_reason"]


def test_mutation_disabled_in_config_is_skipped_not_ok(tmp_path):
    """꺼 두었다는 사실이 리포트에 남아야 한다. 조용한 통과는 안 된다 (R4)."""
    path = _write(tmp_path / ".code-gate.json", json.dumps({"mutation": {"enabled": False}}))
    ctx = _ctx(tmp_path, files=["src/a.js"], config=load_config(path), tools=_with_stryker(tmp_path))
    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "꺼 두었습니다" in outcome["human_reason"]
    assert "통과" not in outcome["human_reason"]


def test_mutation_without_any_mutable_language_is_skipped(tmp_path):
    """두 언어 어느 쪽도 안 바뀌었으면 재지 않는다. 건너뛴 사실은 남긴다 (R4)."""
    outcome = check_mutation(_ctx(tmp_path, files=["README.md"], tools=_with_stryker(tmp_path)))
    assert outcome["status"] == "skipped"
    assert "자바스크립트" in outcome["human_reason"] and "파이썬" in outcome["human_reason"]
    assert "통과" not in outcome["human_reason"]


def test_mutation_skipped_when_no_test_runner_plugin_is_installed(tmp_path):
    """러너 플러그인이 없으면 Stryker 는 변이마다 `npm test` 를 통째로 돌린다 — 시간이 자릿수로 늘어난다."""
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")
    tools = _no_tools()
    tools["stryker"] = {"available": True, "path": "/fake/stryker", "install_hint": "npm i -D @stryker-mutator/core"}
    outcome = check_mutation(_ctx(tmp_path, files=["src/a.js"], tools=tools))
    assert outcome["status"] == "skipped"
    assert outcome["install_hint"] == "npm i -D @stryker-mutator/vitest-runner"


def test_mutation_targets_drop_tests_and_declarations(tmp_path):
    for rel in ("src/a.js", "src/a.test.js", "test/b.js", "src/types.d.ts", "src/__tests__/c.js"):
        _write(tmp_path / rel, "export const x = 1;\n")
    targets, dropped = _mutation_targets(tmp_path, [
        "src/a.js", "src/a.test.js", "test/b.js", "src/types.d.ts", "src/__tests__/c.js", "src/gone.js"])
    assert targets == ("src/a.js",)
    assert set(dropped) == {"src/a.test.js", "test/b.js", "src/types.d.ts", "src/__tests__/c.js", "src/gone.js"}


def test_mutation_all_targets_dropped_is_skipped_not_ok(tmp_path):
    _write(tmp_path / "src" / "a.test.js", "export const x = 1;\n")
    ctx = _ctx(tmp_path, files=["src/a.test.js"], tools=_with_stryker(tmp_path))
    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "통과" not in outcome["human_reason"]


def test_mutation_missing_report_is_an_error_not_a_pass():
    """설정 오류·초기 테스트 실패·대상 0개가 모두 종료 코드 1 + 리포트 없음으로 온다 (R4)."""
    outcome = _mutation_no_report(_FakeProc(stderr="ConfigError: No tests were executed.", returncode=1), 2.3)
    assert outcome["status"] == "error"
    assert "No tests were executed" in outcome["human_reason"]
    assert "통과" not in outcome["human_reason"]


def test_mutation_unknown_tool_name_is_skipped(tmp_path):
    path = _write(tmp_path / ".code-gate.json", json.dumps({"mutation": {"javascript": "mutmut"}}))
    ctx = _ctx(tmp_path, files=["src/a.js"], config=load_config(path), tools=_with_stryker(tmp_path))
    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "mutmut" in outcome["human_reason"]


# --- 실행 명령과 산출물 자리 (D3·R2·R5) ----------------------------------

def test_mutation_command_stays_inside_the_gate_tmpdir(tmp_path, monkeypatch):
    """대상 프로젝트에는 설정 파일도 리포트도 만들지 않는다 (D3).

    JSON 리포트 경로를 바꾸는 명령줄 옵션이 없어 설정 파일이 한 개 필요한데, 그 파일은
    게이트 임시 디렉토리에 둔다. 변이 대상도 변경된 파일만 들어가야 한다 (R3).
    """
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")
    _write(tmp_path / "src" / "old.js", "export const y = 2;\n")
    captured = {}

    def fake_run(cmd, *, cwd, timeout):
        captured["cmd"] = [str(c) for c in cmd]
        captured["cwd"] = cwd
        return _FakeProc(returncode=1)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path))
    check_mutation(ctx)

    cmd = captured["cmd"]
    assert cmd[1] == "run"
    assert cmd[2].startswith(str(Path(ctx.tmpdir).resolve()))     # 설정 파일이 게이트 임시 디렉토리에
    assert cmd[cmd.index("--mutate") + 1] == "src/a.js"           # 변경분만 (R3)
    assert _forbidden_arg(cmd) is None                            # 비-0 종료를 부르는 인자 없음 (R2)
    assert not any(a in cmd for a in ("--track", "--mode", "--flow"))  # R5
    config_body = Path(cmd[2]).read_text(encoding="utf-8")
    for key in ("jsonReporter", "eventReporter", "tempDirName"):
        assert key in config_body
    assert str(Path(ctx.tmpdir).resolve()) in config_body
    assert not (tmp_path / "reports").exists()
    assert not any(p.name.startswith("stryker.conf") for p in tmp_path.iterdir())


def test_mutation_config_wrapper_lets_the_project_config_win(tmp_path):
    """프로젝트가 이미 갖고 있는 Stryker 설정은 덮어쓰지 않고 흡수한다.

    testRunner 는 프로젝트 값보다 앞에 두고(폴백), 출력 경로는 뒤에 두어 게이트가 이긴다.
    """
    project = _write(tmp_path / "stryker.conf.json", json.dumps({"timeoutMS": 7777}))
    work = tmp_path / "work"
    work.mkdir()
    paths = {"config": work / "stryker.conf.mjs", "report": work / "mutation.json",
             "events": work / "events", "temp": work / "tmp"}
    body = _write_stryker_config(paths, project, "vitest").read_text(encoding="utf-8")
    export = [line for line in body.splitlines() if line.startswith("export default")][0]
    assert export.index("fallback") < export.index("projectConfig") < export.index("override")
    assert str(project) in body
    assert _stryker_project_config(tmp_path) == project


def test_mutation_state_file_lives_outside_the_project(tmp_path, monkeypatch):
    """증분 상태 파일은 회차를 넘어 살아야 하는데, 게이트 임시 디렉토리는 매 실행 지워진다.

    그렇다고 대상 프로젝트 안에 두면 오염이라, 사용자 캐시 아래에 저장소별로 나눠 둔다.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    state = mutation_state_file(repo, [])
    assert state is not None
    assert str(cache.resolve()) in str(state)
    assert str(repo.resolve()) not in str(state)     # 대상 프로젝트 안에 두지 않는다 (D3)
    assert state.parent.is_dir()


# --- 리포트 표시 (D2·D5·R9) ----------------------------------------------

def test_mutation_detail_line_carries_everything_needed_to_fix_it():
    """점수만으로는 고칠 수가 없다 — 자리·변이 종류·원본·바뀐 것·관련 테스트가 한 줄에 있어야 한다."""
    survivor = parse_mutation_report(STRYKER_REPORT)["survivors"][0]
    line = _mutation_detail_line(survivor)
    for part in ("src/validate.js:2:10", "ConditionalExpression", "살아남음",
                 "age >= 18", "true", "isAdult 호출만 하고 결과 유형만 본다"):
        assert part in line


def test_mutation_detail_line_says_when_nothing_covered_it():
    no_coverage = parse_mutation_report(STRYKER_REPORT)["survivors"][-1]
    assert "덮은 테스트 없음" in _mutation_detail_line(no_coverage)


def test_mutation_outcome_reports_all_three_time_numbers(tmp_path):
    """전체 초 / 변이 개수 / 변이당 초 — 세 번째가 있어야 다음 실행 시간을 가늠할 수 있다 (D5)."""
    ctx = _ctx(tmp_path)
    outcome = _mutation_outcome(ctx, parse_mutation_report(STRYKER_REPORT), 3.42, ("src/validate.js",))
    assert "실행 3.4초" in outcome["human_reason"]
    assert "변이 4개" in outcome["human_reason"]
    # 4개 중 테스트를 실제로 돌린 것은 2개다 (나머지 2개는 덮은 테스트가 없어 테스트를
    # 한 번도 돌리지 않는다). 그것까지 분모에 넣으면 변이당 초가 실제 비용과 멀어진다.
    assert "테스트를 돌린 변이 2개" in outcome["human_reason"]
    assert "변이당 1.710초" in outcome["human_reason"]


def test_mutation_below_threshold_is_findings_and_above_is_ok(tmp_path):
    """0단계는 리포트만 한다 — 발견으로 표시하되 종료 코드는 그대로 0 이다."""
    ctx = _ctx(tmp_path)
    assert _mutation_outcome(ctx, parse_mutation_report(STRYKER_REPORT), 1.0, ())["status"] == "findings"
    perfect = {"total": 4, "counts": {"Killed": 4}, "score": 100.0, "survivors": [], "files": []}
    assert _mutation_outcome(ctx, perfect, 1.0, ())["status"] == "ok"


def test_mutation_check_is_registered_with_a_detail_title():
    codes = [code for code, *_ in CHECKS]
    assert codes[-1] == "C7"
    assert dict((code, name) for code, name, *_ in CHECKS)["C7"] == "mutation"
    assert code_gate.DETAIL_TITLES["C7"] == "잡히지 않은 변이"


# --- 설정 파싱 폴백 (R6) --------------------------------------------------

def test_mutation_config_reads_valid_values(tmp_path):
    path = _write(tmp_path / ".code-gate.json", json.dumps(
        {"mutation": {"enabled": False, "score_threshold": 95, "timeout_seconds": 120,
                      "javascript": "stryker", "python": "mutmut"}}))
    config = load_config(path)
    assert config.mutation_enabled is False
    assert config.mutation_score_threshold == 95.0
    assert config.mutation_timeout_seconds == 120
    assert config.mutation_javascript == "stryker"
    assert config.mutation_python == "mutmut"


def test_mutation_config_defaults_when_the_block_is_absent(tmp_path):
    config = load_config(tmp_path / "no-such-config.json")
    assert config.mutation_enabled is True
    assert config.mutation_score_threshold == 80.0
    assert config.mutation_timeout_seconds == 600
    assert config.mutation_javascript == "stryker"
    assert config.mutation_python == "mutmut"


@pytest.mark.parametrize("block, note", [
    ("not-an-object", "mutation 항목이 객체가 아니라"),
    ({"enabled": "yes"}, "mutation.enabled 값이 참/거짓이 아니라"),
    ({"javascript": 7}, "mutation.javascript 값이 문자열이 아니라"),
    ({"python": 7}, "mutation.python 값이 문자열이 아니라"),
    ({"python": "   "}, "mutation.python 값이 문자열이 아니라"),
    ({"score_threshold": 0}, "mutation.score_threshold 값이 0 이하라"),
    ({"score_threshold": "높게"}, "mutation.score_threshold 값이 숫자가 아니라"),
    ({"timeout_seconds": -1}, "mutation.timeout_seconds 값이 0 이하라"),
])
def test_mutation_config_falls_back_with_a_reason(tmp_path, block, note):
    """설정이 안 읽혔는데 리포트가 정상처럼 보이면 무엇을 기준으로 쟀는지 알 수 없다."""
    path = _write(tmp_path / ".code-gate.json", json.dumps({"mutation": block}))
    config = load_config(path)
    assert config.mutation_enabled is True
    assert config.mutation_score_threshold == 80.0
    assert config.mutation_timeout_seconds == 600
    assert config.mutation_javascript == "stryker"
    assert config.mutation_python == "mutmut"
    assert any(note in n for n in config.notes), config.notes


def test_repo_config_file_declares_the_mutation_block():
    """기준값을 낮추는 회귀를 잡는다 (R6). 0단계에서는 켜 두고 숫자만 낸다 (D7).

    언어 키는 나란히 두고 기준값 두 개는 공유한다 — 언어를 더해도 기준이 갈라지지 않는다.
    언어 키가 늘어나는 것은 R6 위반이 아니다 (기준값을 낮추는 것이 아니다). 그래도
    전체를 통째로 못 박아 둔다 — 기준값 셋만 따로 보면, 누군가 언어 키에 엉뚱한 도구
    이름을 적어 그 언어가 통째로 건너뛰어지는 회귀를 여기서 못 잡는다.
    기본 꺼짐(`default_enabled=False`)인 어댑터는 여기 적지 않는다 — 설정에 적는 것이
    곧 켜는 것이라, 적는 순간 "바닥 비용이 커서 기본은 꺼 둔다" 는 선언이 이 저장소에
    대해서만 조용히 뒤집힌다. 자바가 그 선례다 (기본 꺼짐이고 여기에 없다).
    켜는 결정은 사람이 한다 — 이 파일의 첫 줄이 그렇게 적혀 있다.
    """
    data = json.loads((REPO_ROOT / ".code-gate.json").read_text(encoding="utf-8"))
    assert data["mutation"] == {"enabled": True, "score_threshold": 80,
                                "timeout_seconds": 600, "javascript": "stryker",
                                "python": "mutmut"}


def test_adapter_tools_are_found_in_cargo_bin_when_the_path_misses_them(tmp_path, monkeypatch):
    """`cargo install` 이 쓰는 `~/.cargo/bin` 도 마지막으로 본다.

    그 자리는 rustup 으로 깐 기계에서만 PATH 에 들어간다. 실측: 이 기계에
    cargo-mutants 27.1.0 이 `~/.cargo/bin` 에 있는데 `shutil.which` 는 None 이었고,
    게이트는 안내대로 설치를 마친 사용자에게 계속 "설치돼 있지 않습니다" 를 냈다.
    조용한 통과는 아니지만 잴 수 있는 회차를 못 재고 넘어간다는 점에서 실효는 같다.
    """
    home = tmp_path / "집"
    (home / ".cargo" / "bin").mkdir(parents=True)
    (home / ".cargo" / "bin" / "cargo-mutants").write_text("", encoding="utf-8")
    monkeypatch.setattr(code_gate.Path, "home", classmethod(lambda cls: home))

    assert code_gate._cargo_bin_path("cargo-mutants") == str(
        home / ".cargo" / "bin" / "cargo-mutants")
    assert code_gate._cargo_bin_path("없는도구") is None

    monkeypatch.setattr(code_gate.shutil, "which", lambda name: None)
    tools = {}
    code_gate._probe_adapter_tools(tools)
    assert tools["cargo-mutants"]["available"] is True
    assert tools["cargo-mutants"]["path"] == str(home / ".cargo" / "bin" / "cargo-mutants")
    # PATH 조회가 이기는 것은 그대로다 — 홈 자리는 마지막 수단이다.
    monkeypatch.setattr(code_gate.shutil, "which", lambda name: f"/usr/bin/{name}")
    other = {}
    code_gate._probe_adapter_tools(other)
    assert other["cargo-mutants"]["path"] == "/usr/bin/cargo-mutants"


# --- 중재 보고서에서 확정된 지적의 회귀 방지 ------------------------------

def _report_with(statuses, source="const a = 1 + 2;\n"):
    """상태 이름만 바꿔 가며 쓰는 최소 리포트."""
    mutants = []
    for index, status in enumerate(statuses):
        mutants.append({"id": str(index), "mutatorName": "ArithmeticOperator", "replacement": "-",
                        "status": status, "coveredBy": [],
                        "location": {"start": {"line": 1, "column": 12}, "end": {"line": 1, "column": 13}}})
    return {"files": {"src/a.js": {"source": source, "mutants": mutants}}}


def test_bracket_paths_are_escaped_so_the_glob_matches_the_real_file():
    """A — `[id].js` 를 그대로 넘기면 글롭이 한 글자 묶음으로 읽어 그 파일이 통째로 빠진다.

    빠진 채로 나머지 파일 점수가 "통과" 로 나가므로, 조용한 통과의 정확한 형태였다 (R4).
    별표로 바꾸는 방법은 바뀌지 않은 다른 파일까지 잡아 R3 를 깨므로 쓰지 않는다.
    """
    assert _stryker_glob("src/pages/[id].js") == "src/pages/[[]id[]].js"
    assert _stryker_glob("src/a.js") == "src/a.js"
    assert "*" not in _stryker_glob("src/[lm]oop.js")


def test_mutate_argument_carries_the_escaped_path(tmp_path, monkeypatch):
    """A — 이스케이프가 실제 명령줄까지 간다."""
    _write(tmp_path / "src" / "pages" / "[id].js", "export const x = 1;\n")
    captured = {}

    def fake_run(cmd, *, cwd, timeout):
        captured["cmd"] = [str(c) for c in cmd]
        return _FakeProc(returncode=1)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, files=["src/pages/[id].js"], tools=_with_stryker(tmp_path))
    check_mutation(ctx)
    cmd = captured["cmd"]
    assert cmd[cmd.index("--mutate") + 1] == "src/pages/[[]id[]].js"


def test_targets_missing_from_the_report_are_reported_not_swallowed(tmp_path):
    """A·B 공통 안전망 — 넘긴 대상이 리포트에 없으면 그 사실을 반드시 말한다.

    빠진 사유(글롭 불일치 / 다루지 못하는 확장자 / 경로 안 쉼표)가 무엇이든 같은 문에서
    걸린다. 나머지 파일 점수가 변경분 전체의 점수처럼 읽히면 안 된다.
    """
    summary = parse_mutation_report(_report_with(["Killed"]))
    gaps = _mutation_gaps(summary, ("src/a.js", "src/pages/[id].js"))
    assert "src/pages/[id].js" in gaps
    assert "변이가 하나도 만들어지지 않아" in gaps

    outcome = _mutation_outcome(_ctx(tmp_path), summary, 1.0, ("src/a.js", "src/pages/[id].js"))
    assert outcome["status"] == "findings"          # 점수는 100% 지만 통과가 아니다
    assert "src/pages/[id].js" in outcome["human_reason"]


def test_targets_all_measured_stay_a_pass(tmp_path):
    """안전망이 정상 회차를 발견으로 바꾸지 않는지."""
    summary = parse_mutation_report(_report_with(["Killed"]))
    assert _mutation_gaps(summary, ("src/a.js",)) == ""
    assert _mutation_outcome(_ctx(tmp_path), summary, 1.0, ("src/a.js",))["status"] == "ok"


@pytest.mark.parametrize("rel", ["src/Counter.vue", "src/Card.svelte", "src/index.html", "src/old.htm"])
def test_stryker_native_extensions_are_not_dropped(tmp_path, rel):
    """B — Stryker 10 이 직접 파싱하는 확장자가 흔적 없이 빠지던 것.

    공용 언어 판정(JS_SUFFIXES)에는 이 확장자들이 없다. 그 상수를 넓히면 C2·C6 판정까지
    바뀌므로 C7 만 따로 고른다.
    """
    ctx = _ctx(tmp_path, files=[rel, "note.md"])
    assert _mutation_changed_files(ctx) == [rel]
    assert rel not in (ctx.langs.get("javascript") or [])       # 공용 판정은 그대로 둔다


def test_vue_only_change_still_runs_the_check(tmp_path, monkeypatch):
    """B — .vue 만 바뀐 회차가 "잴 것 없음" 으로 건너뛰지 않는다."""
    _write(tmp_path / "src" / "Counter.vue", "<script>export default {}</script>\n")
    captured = {}

    def fake_run(cmd, *, cwd, timeout):
        captured["cmd"] = [str(c) for c in cmd]
        return _FakeProc(returncode=1)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    outcome = check_mutation(_ctx(tmp_path, files=["src/Counter.vue"], tools=_with_stryker(tmp_path)))
    assert outcome["status"] != "skipped"
    assert captured["cmd"][captured["cmd"].index("--mutate") + 1] == "src/Counter.vue"


def test_scope_note_says_the_whole_file_is_mutated(tmp_path, monkeypatch):
    """C — 변이는 파일 단위인데 안내가 "바뀌지 않은 코드는 포함되지 않았다" 고 말했다.

    같은 화면의 두 정보가 서로를 부정하던 자리다.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")
    ctx = _ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path))
    paths = mutation_javascript._mutation_paths(ctx)
    _, notes = mutation_javascript._mutation_command(ctx, paths, ("src/a.js",))
    joined = " ".join(notes)
    assert "파일 단위로" in joined
    assert "바뀌지 않은 줄도 함께" in joined
    assert "바뀌지 않은 기존 코드는 이번 검사에 포함되지 않았습니다" not in joined


def test_slice_source_counts_columns_in_utf16_units():
    """D — Stryker 의 열은 UTF-16 코드 단위, 파이썬 색인은 코드 포인트다.

    이모지가 앞에 있으면 한 글자마다 한 칸씩 밀려, 고치라고 내놓은 "원본" 이 엉뚱한
    문자열이 된다 (D2·R9 가 그 줄에서만 무너진다).
    """
    line = "🚀🚀🚀 return n > 0;"
    target = "n > 0"
    start = line.index(target)
    start_col = len(line[:start].encode("utf-16-le")) // 2 + 1
    end_col = start_col + len(target.encode("utf-16-le")) // 2
    location = {"start": {"line": 1, "column": start_col}, "end": {"line": 1, "column": end_col}}
    assert slice_source(line, location) == target


def test_slice_source_is_unchanged_for_ascii():
    """D — ASCII 에서는 두 셈이 같아 결과가 달라지지 않는다."""
    line = "const value = 1 + 2;"
    location = {"start": {"line": 1, "column": 15}, "end": {"line": 1, "column": 20}}
    assert slice_source(line, location) == "1 + 2"


def test_planned_count_is_filtered_by_this_run_targets(tmp_path):
    """E — 증분이면 계획에 지난 회차 파일이 섞인다. 거르지 않으면 다 잰 회차가 덜 잰 것처럼 보고된다."""
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    plans = [{"plan": "runTest", "mutant": {"fileName": str(tmp_path / "src" / "a.js")}} for _ in range(3)]
    plans += [{"plan": "runTest", "mutant": {"fileName": str(tmp_path / "src" / "old.js")}} for _ in range(37)]
    _write(events_dir / "00001-onMutationTestingPlanReady.json", json.dumps({"mutantPlans": plans}))
    _write(events_dir / "00002-onMutantTested.json", json.dumps(
        {"fileName": str(tmp_path / "src" / "a.js"), "mutatorName": "ArithmeticOperator",
         "replacement": "a - b", "status": "Survived", "coveredBy": ["t.js#덧셈"],
         "location": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 6}}}))
    _write(tmp_path / "src" / "a.js", "a + b;\n")

    ctx = _ctx(tmp_path, files=["src/a.js"])
    outcome = _mutation_partial(ctx, {"events": events_dir}, ("src/a.js",), 600.0, 600)
    assert "3개 중 1개까지" in outcome["human_reason"]
    assert "40개" not in outcome["human_reason"]


def test_report_parsing_does_not_grow_with_line_count(tmp_path):
    """F — 변이마다 소스를 다시 쪼개면 (변이 수 x 줄 수) 로 커져 파싱이 2차가 된다 (R1).

    아래 입력은 고치기 전 판본에서 0.6초 안팎이 걸리던 크기다.
    """
    import time as _time
    source = "\n".join(f"const v{i} = {i} + 1;" for i in range(8000))
    mutants = [{"id": str(i), "mutatorName": "ArithmeticOperator", "replacement": "-",
                "status": "Survived", "coveredBy": [],
                "location": {"start": {"line": (i % 8000) + 1, "column": 16},
                             "end": {"line": (i % 8000) + 1, "column": 17}}}
               for i in range(2000)]
    report = {"files": {"src/big.js": {"source": source, "mutants": mutants}}}
    started = _time.perf_counter()
    summary = parse_mutation_report(report)
    elapsed = _time.perf_counter() - started
    assert summary["total"] == 2000
    assert elapsed < 0.25, f"파싱이 {elapsed:.3f}초 걸렸습니다 — 줄 수에 따라 다시 커진 것입니다"


def test_reported_seconds_cover_the_parsing_too(tmp_path, monkeypatch):
    """F — 시간을 서브프로세스가 끝난 자리에서 재면 파싱 구간이 보고 밖으로 샌다."""
    import time as _time
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")

    def fake_run(cmd, *, cwd, timeout):
        Path(cmd[2]).parent.joinpath("mutation.json").write_text(
            json.dumps(_report_with(["Killed"])), encoding="utf-8")
        return _FakeProc(returncode=0)

    def slow_parse(report, targets=None):
        _time.sleep(0.25)
        return mutation_score_mod.summarize_mutants([])

    monkeypatch.setattr(code_gate, "_run", fake_run)
    monkeypatch.setattr(mutation_javascript, "parse_mutation_report", slow_parse)
    outcome = check_mutation(_ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path)))
    assert "실행 0.0초" not in outcome["human_reason"]


def test_per_mutant_seconds_divide_by_the_mutants_that_ran_tests():
    """G — 덮은 테스트가 없는 변이는 테스트를 한 번도 돌리지 않아 비용이 거의 0 이다.

    그것까지 분모에 넣으면 변이당 초가 실제 비용의 몇백 분의 1 로 나와 D5 가 예측에 못 쓰인다.
    """
    text = _mutation_timing(2.7, 3213, 13)
    assert "변이 3213개(테스트를 돌린 변이 13개)" in text
    assert "변이당 0.208초" in text
    # 전부 테스트를 돌린 회차에서는 문장이 늘어나지 않는다.
    assert _mutation_timing(2.0, 4, 4) == "실행 2.0초, 변이 4개, 변이당 0.500초"


def test_incremental_note_does_not_claim_a_previous_run_on_the_first_one(tmp_path, monkeypatch):
    """G — 상태 파일이 없는 첫 실행에서 "지난 회차 결과가 섞여 들어온다" 고 말하던 것."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")
    ctx = _ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path))
    paths = mutation_javascript._mutation_paths(ctx)

    _, first = mutation_javascript._mutation_command(ctx, paths, ("src/a.js",))
    assert any("아직 없어" in n for n in first)
    assert not any("지난 회차 결과가 리포트에 섞여" in n for n in first)

    state = mutation_javascript.mutation_state_file(tmp_path, [])
    state.write_text("{}", encoding="utf-8")
    _, second = mutation_javascript._mutation_command(ctx, paths, ("src/a.js",))
    assert any("지난 회차 결과가 리포트에 섞여" in n for n in second)


@pytest.mark.parametrize("status", ["survived", "BrandNewStatus"])
def test_unknown_mutant_statuses_are_counted_and_named(tmp_path, status):
    """H — 세 묶음 밖 상태는 분모에서 조용히 빠져 "100% 통과" 가 나온다 (R4 가 금지한 형태)."""
    summary = parse_mutation_report(_report_with(["Killed"] * 5 + [status] * 5))
    assert summary["unknown"] == (status,)
    assert summary["score"] == 100.0                    # 공식(D1)은 그대로 둔다
    outcome = _mutation_outcome(_ctx(tmp_path), summary, 1.0, ("src/a.js",))
    assert status in outcome["human_reason"]
    assert outcome["status"] == "findings"              # 모르는 것이 있으면 통과로 내지 않는다


def test_known_statuses_do_not_trigger_the_unknown_warning():
    """H — Pending·Ignored 같은 아는 제외 상태는 경고 대상이 아니다."""
    assert unknown_mutant_statuses({"Killed": 5, "Pending": 5, "Ignored": 2}) == ()


def test_generated_config_turns_incremental_off(tmp_path):
    """I — 캐시를 못 만들어 명령줄이 빠졌을 때 프로젝트의 incremental 이 되살아나던 것.

    되살아나면 증분 상태 파일이 대상 프로젝트 안에 생긴다 (D3 위반).
    """
    project = _write(tmp_path / "stryker.conf.json", json.dumps({"incremental": True}))
    work = tmp_path / "work"
    work.mkdir()
    paths = {"config": work / "stryker.conf.mjs", "report": work / "mutation.json",
             "events": work / "events", "temp": work / "tmp"}
    body = _write_stryker_config(paths, project, "vitest").read_text(encoding="utf-8")
    assert '"incremental": false' in body


def test_no_report_message_names_the_likely_cause():
    """J — 영어 스택트레이스만 나가면 "테스트가 없다" 와 "설정이 어긋났다" 가 구분되지 않는다."""
    outcome = _mutation_no_report(
        _FakeProc(stderr="ConfigError: No tests were executed. Stryker will exit prematurely.", returncode=1), 2.0)
    assert "테스트를 하나도 찾지 못했습니다" in outcome["human_reason"]
    assert "No tests were executed" in outcome["reason"]     # 영어 원문은 남긴다

    other = _mutation_no_report(_FakeProc(stderr="SyntaxError: unexpected token", returncode=1), 2.0)
    assert "Stryker 설정이 어긋났을 때" in other["human_reason"]


def test_timeout_with_a_finished_report_keeps_the_full_result(tmp_path, monkeypatch):
    """K — 리포트를 다 쓴 직후에 죽은 회차에서 완성된 결과를 버리던 것.

    버리면 "N개 중 N개까지 봤고 나머지는 재지 못했습니다" 라는 앞뒤 안 맞는 문장이 나간다.
    """
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")

    def fake_run(cmd, *, cwd, timeout):
        Path(cmd[2]).parent.joinpath("mutation.json").write_text(
            json.dumps(_report_with(["Killed", "Survived"])), encoding="utf-8")
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    outcome = check_mutation(_ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path)))
    assert outcome["status"] == "findings"
    assert "예산을 넘겨 중단했습니다" not in outcome["human_reason"]
    assert "점수 50.0%" in outcome["human_reason"]


@pytest.mark.parametrize("key, block", [
    ("timeout_seconds", {"timeout_seconds": 0.5}),
    ("mutation.timeout_seconds", {"mutation": {"timeout_seconds": 0.9}}),
])
def test_fractional_seconds_do_not_become_zero(tmp_path, key, block):
    """L — 1 미만 소수를 정수로 바꾸면 0 이 된다. 0 이하를 막으려던 검사가 스스로 0 을 만들었다."""
    config = load_config(_write(tmp_path / ".code-gate.json", json.dumps(block)))
    assert config.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert config.mutation_timeout_seconds == 600
    assert any(key in note and "너무 작아" in note for note in config.notes), config.notes


def test_unknown_mutation_config_keys_are_reported(tmp_path):
    """M — 명령줄 오타는 알려 주면서 설정 파일 오타만 조용히 버리면 원인을 못 찾는다."""
    config = load_config(_write(tmp_path / ".code-gate.json", json.dumps(
        {"mutation": {"enabled": True, "ruby": "mutant", "typo_key": 123}})))
    note = [n for n in config.notes if "알 수 없는 키" in n]
    assert note and "ruby" in note[0] and "typo_key" in note[0]


def test_detail_line_marks_an_incomplete_record():
    """N — 자리나 원본이 비어 있으면 그렇다고 적는다. 빈칸이면 정상 항목처럼 보인다."""
    line = _mutation_detail_line({"file": "app/pay.js", "line": 12, "column": None,
                                  "mutator": "EqualityOperator", "status": "Survived",
                                  "original": "", "replacement": "1 >= 2", "tests": []})
    assert "app/pay.js:12:?" in line
    assert "(원본 자리를 알 수 없음)" in line


def test_headline_does_not_reuse_the_word_for_two_numbers(tmp_path):
    """N1 — 머리말의 수(Survived + NoCoverage)와 분포의 "살아남음"(Survived 만)이 달랐다.

    같은 낱말이 한 문장에서 두 수를 가리켜, 숫자가 깨진 것으로 읽혔다.
    """
    summary = parse_mutation_report(_report_with(["Killed", "Survived", "NoCoverage"]))
    human = _mutation_outcome(_ctx(tmp_path), summary, 1.0, ("src/a.js",))["human_reason"]
    assert "잡히지 않음 2개" in human
    assert "살아남음 1" in human
    assert "살아남음 2" not in human


def test_records_keep_the_full_original_and_shorten_only_when_shown():
    """N2 — 기록 시점에 자르면 `--json` 을 읽는 쪽에도 잘린 값만 남는다 (D2)."""
    long_line = "function veryLongFunctionName(alpha, beta, gamma) { return alpha + beta + gamma; }"
    report = {"files": {"src/a.js": {"source": long_line, "mutants": [
        {"id": "0", "mutatorName": "BlockStatement", "replacement": "{}", "status": "Survived",
         "coveredBy": [],
         "location": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": len(long_line) + 1}}}]}}}
    record = parse_mutation_report(report)["survivors"][0]
    assert record["original"] == long_line              # 기록은 온전하게
    assert "…" in _mutation_detail_line(record)         # 표에서만 줄인다


def test_scope_notes_are_not_left_behind_by_a_failed_run(tmp_path, monkeypatch):
    """N3 — 아무것도 재지 못한 회차가 "이렇게 걸러서 점수를 냈다" 고 말하던 것."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _FakeProc(returncode=1))
    ctx = _ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path))
    assert check_mutation(ctx)["status"] == "error"
    assert not any("파일 단위로 변이시켰습니다" in n for n in ctx.notes)


def test_scope_notes_are_kept_on_a_measured_run(tmp_path, monkeypatch):
    """N3 — 실제로 잰 회차에서는 범위 안내가 그대로 남는다 (R4)."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    _write(tmp_path / "src" / "a.js", "export const x = 1;\n")

    def fake_run(cmd, *, cwd, timeout):
        Path(cmd[2]).parent.joinpath("mutation.json").write_text(
            json.dumps(_report_with(["Killed"])), encoding="utf-8")
        return _FakeProc(returncode=0)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, files=["src/a.js"], tools=_with_stryker(tmp_path))
    assert check_mutation(ctx)["status"] == "ok"
    assert any("파일 단위로 변이시켰습니다" in n for n in ctx.notes)


def test_vitest_command_has_no_reporter_flag(tmp_path, monkeypatch):
    """vitest 4 는 `--reporter=basic` 을 사용자 정의 리포터 모듈로 읽으려다 기동에서 죽는다.

    죽으면 C1 이 "vitest 가 비정상 종료했습니다" 로, C2 가 "커버리지 데이터를 만들지
    못했습니다" 로 나온다. 테스트는 전부 통과하는데 게이트가 거짓 실패를 내는 자리라,
    리포터를 다시 지정하는 회귀를 여기서 잡는다.
    """
    binary = tmp_path / "node_modules" / ".bin" / "vitest"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    _write(tmp_path / "vitest.config.js", "export default {};\n")

    seen = {}

    def fake_run(cmd, *, cwd, timeout):
        seen["cmd"] = [str(c) for c in cmd]
        return _FakeProc(stdout=" Tests  9 passed (9)\n", returncode=0)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, files=["src/a.js"])
    outcome = code_gate._run_js_tests(ctx)

    assert outcome["status"] == "ok", outcome
    assert not any(c.startswith("--reporter") for c in seen["cmd"]), seen["cmd"]
    assert "--coverage" in seen["cmd"]


# ---------------------------------------------------------------------------
# 16 — 뮤테이션 파이썬 경로 (mutmut)
#
# 아래 고정 자료는 조사 단계에서 mutmut 3.7.0 을 py-sandbox 에 실제로 돌려 얻은 산출물이다.
# 변이 함수 네 개(원본 + 1 + 4 + 8)만 남기고 `.spans` 의 줄 번호를 그에 맞춰 다시 셌다.
# 나머지 값(종료 코드, 생성된 코드, 테스트 이름)은 실물 그대로다.
# ---------------------------------------------------------------------------

LOOPX_SOURCE = (
    '"""반복문이 있는 모듈 — 무한루프 변이(timeout)가 나올 수 있다."""\n'
    "\n"
    "LIMIT = 3\n"
    "\n"
    "\n"
    "def count_up(n):\n"
    "    total = 0\n"
    "    i = 0\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i += 1\n"
    "    return total\n"
)

LOOPX_MUTANTS = (
    '"""반복문이 있는 모듈 — 무한루프 변이(timeout)가 나올 수 있다."""\n'
    "\n"
    "LIMIT = 3\n"
    "\n"
    "\n"
    "from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict\n"
    "mutants_x_count_up__mutmut: MutantDict = {}  # type: ignore\n"
    "\n"
    "\n"
    "@_mutmut_mutated(mutants_x_count_up__mutmut)\n"
    "def count_up(n):\n"
    "    total = 0\n"
    "    i = 0\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i += 1\n"
    "    return total\n"
    "\n"
    "\n"
    "def x_count_up__mutmut_orig(n):\n"
    "    total = 0\n"
    "    i = 0\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i += 1\n"
    "    return total\n"
    "\n"
    "\n"
    "def x_count_up__mutmut_1(n):\n"
    "    total = None\n"
    "    i = 0\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i += 1\n"
    "    return total\n"
    "\n"
    "\n"
    "def x_count_up__mutmut_4(n):\n"
    "    total = 0\n"
    "    i = 1\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i += 1\n"
    "    return total\n"
    "\n"
    "\n"
    "def x_count_up__mutmut_8(n):\n"
    "    total = 0\n"
    "    i = 0\n"
    "    while i < n:\n"
    "        total += i\n"
    "        i = 1\n"
    "    return total"
)

LOOPX_SPANS = {
    "version": 1,
    "spans": {
        "x_count_up__mutmut_orig": [18, 26],
        "x_count_up__mutmut_1": [27, 35],
        "x_count_up__mutmut_4": [36, 44],
        "x_count_up__mutmut_8": [45, 53],
    },
}

# 실측 종료 코드 그대로 — 1 은 잡힘, 0 은 살아남음, -24 는 무한루프(시간초과)다.
LOOPX_META = {
    "exit_code_by_key": {
        "pysandbox.loopx.x_count_up__mutmut_1": 1,
        "pysandbox.loopx.x_count_up__mutmut_4": 0,
        "pysandbox.loopx.x_count_up__mutmut_8": -24,
    },
    "hash_by_function_name": {"x_count_up": "5b5649216622"},
    "type_check_error_by_key": {},
    "durations_by_key": {
        "pysandbox.loopx.x_count_up__mutmut_1": 0.047347,
        "pysandbox.loopx.x_count_up__mutmut_4": 0.044088,
        "pysandbox.loopx.x_count_up__mutmut_8": 15.00681,
    },
    "estimated_durations_by_key": {},
}

LOOPX_TESTS = {
    "pysandbox.loopx.x_count_up": ["tests/test_loopx.py::test_count_up_0부터_n_1까지_더한다"],
}

REL = "src/pysandbox/loopx.py"


def _loopx_records(meta=None):
    return build_mutmut_records(REL, meta or LOOPX_META, LOOPX_SPANS,
                                LOOPX_MUTANTS, LOOPX_SOURCE, LOOPX_TESTS)


def _with_mutmut(python_exe=sys.executable):
    """mutmut 만 설치된 상태."""
    tools = _no_tools(python_exe)
    tools["mutmut"] = {"available": True, "path": f"{python_exe} -m mutmut", "install_hint": ""}
    return tools


def _mutmut_work_from(ctx):
    """대상 프로젝트 밖의 mutmut 작업 디렉토리 — 테스트가 사본을 직접 놓을 자리."""
    return mutmut_work_dir(ctx.repo_root, ctx.notes)


def _fake_mutmut_run(rel=REL, meta=None, spans=None, mutants=None):
    """mutmut 을 대신해 사본 산출물만 남기는 가짜 실행. 서브프로세스를 띄우지 않는다."""

    def run(cmd, *, cwd, timeout):
        target = Path(cwd) / "mutants" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(mutants if mutants is not None else LOOPX_MUTANTS, encoding="utf-8")
        target.with_suffix(".py.meta").write_text(
            json.dumps(meta if meta is not None else LOOPX_META), encoding="utf-8")
        target.with_suffix(".py.spans").write_text(
            json.dumps(spans if spans is not None else LOOPX_SPANS), encoding="utf-8")
        (Path(cwd) / "mutants" / "mutmut-stats.json").write_text(
            json.dumps({"tests_by_mangled_function_name": LOOPX_TESTS}), encoding="utf-8")
        return _FakeProc(returncode=0)

    return run


# --- D1 상태 어휘 변환 ----------------------------------------------------

@pytest.mark.parametrize("word, gate", [
    ("killed", "Killed"),
    ("timeout", "Timeout"),
    ("survived", "Survived"),
    ("no tests", "NoCoverage"),
    ("skipped", "Ignored"),
    ("not checked", "Pending"),
    ("check was interrupted by user", "Pending"),
    ("segfault", "RuntimeError"),
])
def test_mutmut_words_map_into_the_gate_vocabulary(word, gate):
    """도구 어휘는 어댑터에서 끝난다 — 점수 공식에는 게이트 어휘만 들어간다 (D1).

    변환을 공식 쪽에 두면 점수 함수가 도구 이름을 알게 되고, 언어를 더할 때마다 그 함수가
    갈라진다. 그래서 여기서만 바꾼다.
    """
    assert mutmut_gate_status(word) == gate


def test_mutmut_statuses_land_in_the_three_d1_groups():
    """세 묶음(분자 / 분모 / 제외)에 정확히 떨어지는지. 이 배분이 점수의 전부다 (D1)."""
    scored = {mutmut_gate_status(w) for w in ("killed", "timeout", "survived", "no tests")}
    assert scored == {"Killed", "Timeout", "Survived", "NoCoverage"}
    counts = {mutmut_gate_status("killed"): 3, mutmut_gate_status("timeout"): 1,
              mutmut_gate_status("survived"): 2, mutmut_gate_status("no tests"): 2}
    assert mutation_score(counts) == 50.0
    excluded = {mutmut_gate_status(w) for w in ("skipped", "not checked", "segfault",
                                                "check was interrupted by user")}
    assert unknown_mutant_statuses({name: 1 for name in excluded}) == ()
    assert mutation_score({name: 9 for name in excluded}) is None


@pytest.mark.parametrize("exit_code, word", [
    (1, "killed"), (3, "killed"),
    (0, "survived"),
    (5, "no tests"), (33, "no tests"),
    (34, "skipped"), (35, "suspicious"),
    (36, "timeout"), (24, "timeout"), (-24, "timeout"), (152, "timeout"), (255, "timeout"),
    (37, "caught by type check"), (2, "check was interrupted by user"),
    (-11, "segfault"), (-9, "segfault"),
    (None, "not checked"),
])
def test_mutmut_exit_codes_become_the_measured_statuses(exit_code, word):
    """`.meta` 에는 상태 이름이 아니라 종료 코드가 들어 있다. 표는 mutmut 3.7.0 실측이다."""
    assert mutmut_status(exit_code) == word


def test_mutmut_unknown_status_is_not_silently_dropped():
    """모르는 상태는 점수 분모에서 조용히 빠져 100% 가 나온다 — R4 가 금지한 형태다.

    `suspicious` 와 `caught by type check` 는 실물을 못 만들어 봐서 대응을 정하지 않았다.
    짐작으로 채우는 대신 모르는 채로 두고 이름을 적어 낸다.
    """
    assert mutmut_gate_status("suspicious") == "suspicious"
    assert mutmut_status(99) == "unknown exit code 99"
    summary = summarize_mutants(_loopx_records({"exit_code_by_key": {
        "pysandbox.loopx.x_count_up__mutmut_1": 1,
        "pysandbox.loopx.x_count_up__mutmut_4": 35,
    }}))
    assert summary["unknown"] == ("suspicious",)


# --- 실제 출력 파싱 (D2) --------------------------------------------------

def test_build_mutmut_records_reads_real_mutmut_output():
    """조사에서 얻은 실제 산출물 그대로 — 종료 코드 세 개가 세 상태로 떨어진다."""
    summary = summarize_mutants(_loopx_records())
    assert summary["total"] == 3
    assert summary["counts"] == {"Killed": 1, "Survived": 1, "Timeout": 1}
    assert summary["score"] == 66.67          # (잡힘 1 + 시간초과 1) / 3
    assert summary["files"] == [REL]


def test_mutmut_record_line_points_at_the_original_file():
    """mutmut 은 파일 안 줄 번호를 주지 않는다. 사본과 원본을 견줘 되짚은 값이 맞는지.

    `i = 0` 은 원본 8번째 줄, `i += 1` 은 11번째 줄이다 (실측으로 확인한 자리다).
    """
    by_key = {r["mutant"]: r for r in _loopx_records()}
    survived = by_key["pysandbox.loopx.x_count_up__mutmut_4"]
    assert (survived["line"], survived["original"], survived["replacement"]) == (8, "    i = 0", "    i = 1")
    timed_out = by_key["pysandbox.loopx.x_count_up__mutmut_8"]
    assert (timed_out["line"], timed_out["original"], timed_out["replacement"]) == (11, "        i += 1", "        i = 1")


def test_mutmut_record_leaves_the_columns_it_cannot_know_blank():
    """없는 것을 지어내지 않는다 (D2). 열과 변이 종류는 mutmut 이 어떤 방법으로도 안 준다."""
    record = _loopx_records()[1]
    assert record["column"] is None
    assert record["mutator"] is None
    line = _mutation_detail_line(record)
    assert f"{REL}:8:?" in line               # 열 자리는 물음표
    assert "[변이 종류 없음]" in line          # None 을 그대로 찍지 않는다
    assert "i = 0 → i = 1" in line             # 대신 원본과 바뀐 것으로 자리를 알린다


def test_mutmut_tests_are_function_level_not_per_mutant():
    """관련 테스트는 변이별이 아니라 함수 단위다. 같은 함수의 변이는 같은 목록을 갖는다."""
    records = _loopx_records()
    assert {tuple(r["tests"]) for r in records} == {
        ("tests/test_loopx.py::test_count_up_0부터_n_1까지_더한다",)}
    assert "테스트 1개" in _mutation_detail_line(records[1])


def test_mutmut_change_is_blank_when_the_diff_is_not_one_place():
    """자리가 한 군데가 아니면 비운다 — 틀린 자리를 적으면 없는 곳을 찾으러 간다 (D2)."""
    orig = ["def x_f__mutmut_orig(a):", "    b = 1", "    c = 2", "    return b"]
    two_places = ["def x_f__mutmut_2(a):", "    b = 2", "    c = 2", "    return b + 1"]
    assert mutmut_change(orig, two_places) == (None, "", "")
    assert mutmut_change([], []) == (None, "", "")
    one_place = ["def x_f__mutmut_2(a):", "    b = 2", "    c = 2", "    return b"]
    assert mutmut_change(orig, one_place) == (1, "    b = 1", "    b = 2")
    # 붙어 있는 여러 줄이 한 번에 바뀐 것은 한 군데다 — 첫 줄을 자리로 삼는다.
    block = ["def x_f__mutmut_3(a):", "    b = 2", "    c = 3", "    return b"]
    assert mutmut_change(orig, block) == (1, "    b = 1\n    c = 2", "    b = 2\n    c = 3")


def test_mutmut_line_is_blank_when_two_functions_share_a_name():
    """이름이 겹치면 어느 쪽인지 가릴 수 없다. 그때는 줄을 비운다."""
    source = "def f():\n    return 1\n\n\nclass A:\n    def f(self):\n        return 2\n"
    lines = mutmut_def_lines(source)
    assert lines[(None, "f")] == [1]
    assert lines[("A", "f")] == [6]
    twice = "def f():\n    return 1\n\n\ndef f():\n    return 2\n"
    assert mutmut_def_lines(twice)[(None, "f")] == [1, 5]
    assert mutmut_def_lines("def broken(:\n")== {}


@pytest.mark.parametrize("mangled, expected", [
    ("x_count_up", (None, "count_up")),
    ("xǁCartǁtotal", ("Cart", "total")),
    ("count_up", (None, None)),
    ("x_", (None, None)),
])
def test_mutmut_function_name_reads_both_manglings(mangled, expected):
    """모듈 함수는 `x_<이름>`, 메서드는 `xǁ<클래스>ǁ<이름>` 이다."""
    assert mutmut_function_name(mangled) == expected


def test_parse_mutmut_run_drops_files_outside_the_change_set(tmp_path):
    """작업 디렉토리는 회차를 넘어 산다 — 거르지 않으면 지난 회차 파일이 점수에 들어간다 (R3)."""
    mutants = tmp_path / "mutants" / "src" / "pysandbox"
    mutants.mkdir(parents=True)
    for name in ("loopx.py", "old.py"):
        (mutants / f"{name}.meta").write_text(json.dumps(LOOPX_META), encoding="utf-8")
        (mutants / f"{name}.spans").write_text(json.dumps(LOOPX_SPANS), encoding="utf-8")
        (mutants / name).write_text(LOOPX_MUTANTS, encoding="utf-8")
    _write(tmp_path / "mutants" / "mutmut-stats.json",
           json.dumps({"tests_by_mangled_function_name": LOOPX_TESTS}))
    _write(tmp_path / REL, LOOPX_SOURCE)
    _write(tmp_path / "src" / "pysandbox" / "old.py", LOOPX_SOURCE)

    assert parse_mutmut_run(tmp_path, tmp_path, [REL, "src/pysandbox/old.py"])["total"] == 6
    narrowed = parse_mutmut_run(tmp_path, tmp_path, [REL])
    assert narrowed["total"] == 3 and narrowed["files"] == [REL]


@pytest.mark.parametrize("meta", [{}, {"exit_code_by_key": "망가진 값"}])
def test_parse_mutmut_run_survives_a_broken_meta(tmp_path, meta):
    """산출물이 어그러져도 게이트가 죽지 않는다. 재지 못한 것은 0 으로 남고 통과가 아니다."""
    mutants = tmp_path / "mutants" / "src" / "pysandbox"
    mutants.mkdir(parents=True)
    (mutants / "loopx.py.meta").write_text(json.dumps(meta), encoding="utf-8")
    assert parse_mutmut_run(tmp_path, tmp_path, [REL])["total"] == 0


# --- 건너뜀 사유 (D6·R4) --------------------------------------------------

def test_mutmut_missing_is_skipped_with_an_install_hint(tmp_path):
    """도구가 없으면 건너뛰되 설치 방법을 함께 낸다 (D6). 조용한 통과는 없다 (R4)."""
    outcome = check_mutation(_ctx(tmp_path, files=["pkg.py"]))
    assert outcome["status"] == "skipped"
    assert "mutmut" in outcome["human_reason"]
    assert outcome["install_hint"] == f"{sys.executable} -m pip install mutmut"
    assert "통과" not in outcome["human_reason"]


def test_mutmut_unknown_tool_name_is_skipped(tmp_path):
    path = _write(tmp_path / ".code-gate.json", json.dumps({"mutation": {"python": "cosmic-ray"}}))
    ctx = _ctx(tmp_path, files=["pkg.py"], config=load_config(path), tools=_with_mutmut())
    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "cosmic-ray" in outcome["human_reason"]


def test_mutmut_is_skipped_when_the_python_tests_did_not_pass(tmp_path):
    """mutmut 은 기준 테스트가 통과해야 돈다. 모르고 부르면 스위트를 두 번 더 돌리고 실패한다 (R1)."""
    ctx = _ctx(tmp_path, files=["pkg.py"], tools=_with_mutmut())
    ctx.python_tests_status = "findings"
    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "테스트가 통과하지 않아" in outcome["human_reason"]


def test_mutmut_targets_drop_test_files(tmp_path):
    """테스트를 변이시켜도 얻을 것이 없고, 삭제된 파일을 넘기면 mutmut 이 준비에서 죽는다."""
    _write(tmp_path / "pkg" / "core.py", "def f():\n    return 1\n")
    _write(tmp_path / "pkg" / "test_core.py", "def test_f():\n    assert True\n")
    _write(tmp_path / "conftest.py", "")
    _write(tmp_path / "tests" / "helper.py", "")
    targets, dropped = _mutmut_targets(tmp_path, [
        "pkg/core.py", "pkg/core_test.py", "pkg/test_core.py", "conftest.py",
        "tests/helper.py", "pkg/deleted.py"])
    assert targets == ("pkg/core.py",)
    assert set(dropped) == {"pkg/core_test.py", "pkg/test_core.py", "conftest.py",
                            "tests/helper.py", "pkg/deleted.py"}


def test_mutmut_all_targets_dropped_is_skipped_not_ok(tmp_path):
    _write(tmp_path / "tests" / "test_a.py", "def test_x():\n    assert True\n")
    outcome = check_mutation(_ctx(tmp_path, files=["tests/test_a.py"], tools=_with_mutmut()))
    assert outcome["status"] == "skipped"
    assert "통과" not in outcome["human_reason"]


def test_mutmut_source_roots_take_the_top_level_name():
    """mutmut 은 소스 루트를 설정으로 받는다. 최상위에 놓인 .py 는 그 파일 자체가 루트다."""
    roots, unusable = _mutmut_source_roots(("src/a.py", "src/b.py", "app/c.py", "setup_helper.py"))
    assert roots == ("src", "app", "setup_helper.py")
    assert unusable == ()
    _, clash = _mutmut_source_roots(("mutants/a.py",))
    assert clash == ("mutants/a.py",)


def test_mutmut_no_result_names_the_likely_cause():
    """영어 원문만 나가면 "테스트가 없다" 와 "설정이 어긋났다" 가 구분되지 않는다."""
    outcome = _mutmut_no_result(
        _FakeProc(stderr="AssertionError: Module name starts with `src.`, which is invalid", returncode=1), 2.0)
    assert outcome["status"] == "error"
    assert "`src.` 로 시작하는 경로로 import" in outcome["human_reason"]
    assert "Module name starts with" in outcome["reason"]      # 영어 원문은 남긴다
    assert "통과" not in outcome["human_reason"]

    stats = _mutmut_no_result(_FakeProc(stderr="failed to collect stats. runner returned 1", returncode=1), 2.0)
    assert "기준 테스트가 실패" in stats["human_reason"]


def test_mutmut_partial_counts_both_numbers_from_one_place(tmp_path):
    """"몇 개 중 몇 개" 의 두 숫자가 같은 곳에서 나와야 한다 (D4).

    mutmut 은 변이를 만들 때 모든 이름을 `.meta` 에 넣고, 돌린 것만 종료 코드를 채운다.
    아직 안 돈 변이는 실행 안 됨(Pending)이라 점수 분모에서도 빠진다.
    """
    meta = {"exit_code_by_key": {
        "pysandbox.loopx.x_count_up__mutmut_1": 1,
        "pysandbox.loopx.x_count_up__mutmut_4": 0,
        "pysandbox.loopx.x_count_up__mutmut_8": None,
    }}
    summary = summarize_mutants(_loopx_records(meta))
    assert summary["counts"]["Pending"] == 1
    assert summary["score"] == 50.0                       # 실행 안 됨은 분모에서 빠진다
    outcome = _mutmut_partial(_ctx(tmp_path), summary, [REL], 600.0, 600)
    assert outcome["status"] == "timeout"
    assert "변이 3개 중 2개까지" in outcome["human_reason"]
    assert "전체 점수가 아닙니다" in outcome["human_reason"]


def test_partial_reports_say_which_files_were_never_reached(tmp_path):
    """중단된 회차에도 "이 파일은 한 줄도 못 봤다" 를 적는다 (확정 14).

    적지 않으면 남은 파일의 점수가 변경분 전체의 점수처럼 읽힌다. 두 언어가 같은 문장을 쓴다.
    """
    summary = summarize_mutants(_loopx_records())
    outcome = _mutmut_partial(_ctx(tmp_path), summary, [REL, "src/pysandbox/other.py"], 600.0, 600)
    assert "대상 파일 1개는 한 줄도 재지 못했습니다" in outcome["human_reason"]
    assert "src/pysandbox/other.py" in outcome["human_reason"]

    ctx = _ctx(tmp_path)
    paths = {"events": tmp_path / "no-such-events"}
    (tmp_path / "a.js").write_text("export const x = 1;\n", encoding="utf-8")
    js = _mutation_partial(ctx, paths, ["a.js"], 5.0, 600)
    assert js["status"] == "timeout"        # 중간 결과가 없으면 그 사실만 낸다


# --- 대상 프로젝트를 건드리지 않는다 (D3) --------------------------------

def test_mutmut_runs_outside_the_project_and_leaves_nothing_behind(tmp_path, monkeypatch):
    """mutmut 은 사본 `mutants/` 를 **현재 작업 디렉토리** 아래 만든다.

    대상 프로젝트에서 그냥 돌리면 저장소 안에 사본이 쌓인다. 작업 디렉토리를 사용자 캐시로
    잡고 소스·테스트를 심링크로 걸면 프로젝트에는 아무것도 남지 않는다 (실측).
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    _write(project / "tests" / "test_loopx.py", "def test_x():\n    assert True\n")
    captured = {}

    def run(cmd, *, cwd, timeout):
        captured["cmd"] = [str(c) for c in cmd]
        captured["cwd"] = Path(cwd)
        return _fake_mutmut_run()(cmd, cwd=cwd, timeout=timeout)

    monkeypatch.setattr(code_gate, "_run", run)
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    before = sorted(p.relative_to(project).as_posix() for p in project.rglob("*"))
    outcome = check_mutation(ctx)

    assert outcome["status"] == "findings"
    assert str(cache.resolve()) in str(captured["cwd"])        # 프로젝트 밖에서 돌았다
    assert str(project.resolve()) not in str(captured["cwd"])
    after = sorted(p.relative_to(project).as_posix() for p in project.rglob("*"))
    assert after == before                                      # 프로젝트에 새 파일 없음
    assert _forbidden_arg(captured["cmd"]) is None               # 비-0 종료를 부르는 인자 없음 (R2)
    assert not any(a in captured["cmd"] for a in ("--track", "--mode", "--flow"))   # R5
    assert captured["cmd"][-3:] == ["-m", "mutmut", "run"]


def test_mutmut_config_never_turns_on_covered_lines_only(tmp_path, monkeypatch):
    """`mutate_only_covered_lines` 를 켜면 덮이지 않은 줄의 변이를 아예 만들지 않는다.

    그러면 no_coverage 가 0 이 되어 테스트를 안 쓸수록 점수가 오른다 — D1 이 막으려던 상황이다.
    설정 파일도 변경분 한정도 전부 작업 디렉토리 안이라 프로젝트에는 남지 않는다 (D3).
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    monkeypatch.setattr(code_gate, "_run", _fake_mutmut_run())
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    check_mutation(ctx)

    work = mutmut_work_dir(project, [])
    body = (work / "setup.cfg").read_text(encoding="utf-8")
    assert "mutate_only_covered_lines=False" in body
    assert "only_mutate=\n\tsrc/pysandbox/loopx.py\n" in body     # 변경분만 (R3)
    assert "source_paths=\n\tsrc\n" in body
    assert not (project / "setup.cfg").exists()
    assert (work / "src").is_symlink()


def test_mutmut_work_dir_lives_outside_the_project(tmp_path, monkeypatch):
    """증분 상태가 회차를 넘어 살아야 하는데 게이트 임시 디렉토리는 매 실행 지워진다.

    Stryker 쪽은 파일 하나, mutmut 쪽은 디렉토리 하나라는 것만 다르다.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    work = mutmut_work_dir(repo, [])
    assert work is not None and work.is_dir()
    assert str(cache.resolve()) in str(work)
    assert str(repo.resolve()) not in str(work)


def test_mutmut_project_config_is_read_not_written(tmp_path, monkeypatch):
    """프로젝트가 이미 갖고 있는 mutmut 설정은 이어 쓰되 파일은 건드리지 않는다 (D3)."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    original = "[mutmut]\ntimeout_multiplier=3.0\nsource_paths=everything\n"
    _write(project / "setup.cfg", original)
    monkeypatch.setattr(code_gate, "_run", _fake_mutmut_run())
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    check_mutation(ctx)

    body = (mutmut_work_dir(project, []) / "setup.cfg").read_text(encoding="utf-8")
    assert "timeout_multiplier=3.0" in body                     # 프로젝트 값은 이어 쓴다
    assert "everything" not in body                             # 소스 루트는 게이트가 정한다
    assert (project / "setup.cfg").read_text(encoding="utf-8") == original
    assert any("이어 썼습니다" in note for note in ctx.notes)


# --- 두 언어를 한 항목으로 (D1·R1) ----------------------------------------

def _skip_outcome():
    return {"status": "skipped", "reason": "stryker missing",
            "human_reason": "Stryker 가 설치돼 있지 않습니다.",
            "install_hint": "npm i -D @stryker-mutator/core"}


def _language_part(language, label, counts, seconds):
    """언어 한 조각. 개수만 다르게 해 합산이 맞는지 본다."""
    records = []
    for status, number in counts.items():
        records += [{"file": f"a.{language}", "line": 1, "column": None, "mutator": None,
                     "original": "a", "replacement": "b", "status": status, "tests": []}
                    for _ in range(number)]
    summary = summarize_mutants(records)
    score = summary["score"]
    outcome = {"status": "findings" if (score or 0) < 80 else "ok",
               "reason": f"mutation score {score}",
               "human_reason": f"점수 {score:.1f}%. 실행 {seconds:.1f}초, 변이 {summary['total']}개",
               "findings": summary["survivors"]}
    return {"language": language, "label": label, "outcome": outcome, "summary": summary}


def test_two_languages_share_one_score_and_show_each_one(tmp_path):
    """점수는 개수를 합쳐 한 번만 계산한다 (D1). 언어별 점수도 함께 보여야 어디가 약한지 안다."""
    parts = [
        _language_part("javascript", "자바스크립트", {"Killed": 9, "Survived": 1}, 12.0),
        _language_part("python", "파이썬", {"Killed": 1, "Survived": 1, "NoCoverage": 8}, 30.0),
    ]
    merged = _merge_mutation_languages(_ctx(tmp_path), parts)
    assert "합산 점수 50.0%" in merged["human_reason"]           # (9+1) / 20
    assert "변이 20개" in merged["human_reason"]
    assert "자바스크립트 90.0% / 파이썬 10.0%" in merged["human_reason"]
    assert merged["status"] == "findings"                        # 가장 나쁜 상태가 이긴다
    assert len(merged["findings"]) == 10                         # 두 언어의 목록이 다 실린다


def test_two_languages_report_their_seconds_separately(tmp_path):
    """시간은 언어마다 자릿수가 다르다. 합쳐 버리면 다음 실행을 가늠할 수 없다 (R1)."""
    parts = [
        _language_part("javascript", "자바스크립트", {"Killed": 4}, 12.0),
        _language_part("python", "파이썬", {"Killed": 4}, 30.0),
    ]
    human = _merge_mutation_languages(_ctx(tmp_path), parts)["human_reason"]
    assert "자바스크립트: 점수 100.0%. 실행 12.0초" in human
    assert "파이썬: 점수 100.0%. 실행 30.0초" in human


def test_one_language_is_reported_as_is(tmp_path):
    """한 언어만 바뀌었으면 합산 문장을 덧붙이지 않는다 — 없는 비교를 만들지 않는다."""
    part = _language_part("python", "파이썬", {"Killed": 4}, 3.0)
    assert _merge_mutation_languages(_ctx(tmp_path), [part]) is part["outcome"]


def test_a_language_that_was_skipped_does_not_vanish_from_the_report(tmp_path):
    """한쪽이 건너뛰어도 그 사실이 남는다. 잰 쪽 점수만 나가면 전체를 잰 것처럼 읽힌다 (R4).

    한 언어만 쟀으면 "합산" 이라고 부르지 않는다 — 재지 못한 언어가 그 숫자 안에 있는 것처럼
    읽힌다 (확정 12).
    """
    measured = _language_part("python", "파이썬", {"Killed": 4}, 3.0)
    skipped = {"language": "javascript", "label": "자바스크립트", "summary": None,
               "outcome": _skip_outcome()}
    merged = _merge_mutation_languages(_ctx(tmp_path), [skipped, measured])
    assert "Stryker 가 설치돼" in merged["human_reason"]
    assert "파이썬 점수 100.0%" in merged["human_reason"]
    assert "합산" not in merged["human_reason"]
    assert "자바스크립트는 재지 못해 이 점수에 들어 있지 않습니다" in merged["human_reason"]
    assert merged["install_hint"] == "npm i -D @stryker-mutator/core"


def test_merged_head_says_which_language_is_below_the_threshold(tmp_path):
    """합산 점수는 두 언어 비율 사이의 값이라 한쪽이 미달이어도 기준을 넘길 수 있다.

    기준과의 비교가 나오는 자리는 머리말 하나뿐인데, 그 비교가 통과를 가리키면서 항목 판정은
    발견이 되는 어긋남이 실제로 나왔다 (확정 12).
    """
    parts = [
        _language_part("javascript", "자바스크립트", {"Killed": 5, "Survived": 5}, 2.0),
        _language_part("python", "파이썬", {"Killed": 500}, 30.0),
    ]
    merged = _merge_mutation_languages(_ctx(tmp_path), parts)
    assert merged["status"] == "findings"
    assert "합산 점수 99.0%" in merged["human_reason"]
    assert "자바스크립트는 기준에 못 미칩니다" in merged["human_reason"]


@pytest.mark.parametrize("word, expected", [("자바스크립트", "는"), ("파이썬", "은"), ("java", "은")])
def test_korean_topic_particle_follows_the_last_syllable(word, expected):
    """안내문에 "자바스크립트 은" 같은 문장이 나가지 않게 한다."""
    assert _ko_topic(word) == expected



def test_python_files_are_picked_for_c7_without_touching_the_shared_language_split(tmp_path):
    """C7 만의 확장자 목록을 따로 둔다 — PY_SUFFIXES 는 C1·C6 이 함께 쓴다."""
    ctx = _ctx(tmp_path, files=["a.py", "b.js", "c.md"])
    assert _mutation_changed_python_files(ctx) == ["a.py"]
    assert _mutation_changed_files(ctx) == ["b.js"]
    assert ctx.langs["python"] == ["a.py"]


def test_both_languages_run_when_both_changed(tmp_path, monkeypatch):
    """자바스크립트만 바뀌면 자바스크립트만, 파이썬만 바뀌면 파이썬만, 둘 다면 둘 다."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    _write(project / "src" / "a.js", "export const x = 1;\n")
    tools = _with_mutmut()
    tools["stryker"] = {"available": True, "path": "/fake/stryker",
                        "install_hint": "npm i -D @stryker-mutator/core"}
    (project / "node_modules" / "@stryker-mutator" / "vitest-runner").mkdir(parents=True)

    def run(cmd, *, cwd, timeout):
        if "mutmut" in [str(c) for c in cmd]:
            return _fake_mutmut_run()(cmd, cwd=cwd, timeout=timeout)
        Path(cmd[2]).parent.joinpath("mutation.json").write_text(
            json.dumps(_report_with(["Killed", "Killed", "Killed"])), encoding="utf-8")
        return _FakeProc(returncode=0)

    monkeypatch.setattr(code_gate, "_run", run)
    ctx = _ctx(project, files=[REL, "src/a.js"], tools=tools)
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert "합산 점수" in outcome["human_reason"]
    assert "자바스크립트:" in outcome["human_reason"] and "파이썬:" in outcome["human_reason"]
    assert "변이 6개" in outcome["human_reason"]                 # 3 + 3


def test_python_gap_notes_say_what_the_list_cannot_show(tmp_path, monkeypatch):
    """빈칸으로 두면 자바스크립트 목록과 같은 것으로 읽힌다. 세 칸이 다르다는 것을 적는다 (D2)."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    monkeypatch.setattr(code_gate, "_run", _fake_mutmut_run())
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    check_mutation(ctx)
    joined = " ".join(ctx.notes)
    assert "열 번호와 변이 종류 이름이 없습니다" in joined
    assert "함수 단위" in joined
    assert "사본을 만들어 돌렸습니다" in joined


def test_mutmut_prepared_but_ran_nothing_is_an_error_not_a_quiet_skip(tmp_path, monkeypatch):
    """준비 단계에서 죽으면 `.meta` 는 남고 종료 코드만 비어 있다.

    그 상태를 "점수를 낼 변이가 없다" 로만 내면 도구가 남긴 사유가 사라져 원인을 찾을 수
    없다. 실제로 한 번 그렇게 나가는 것을 보고 고쳤다 (R4).
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    pending = {"exit_code_by_key": {k: None for k in LOOPX_META["exit_code_by_key"]}}

    def run(cmd, *, cwd, timeout):
        _fake_mutmut_run(meta=pending)(cmd, cwd=cwd, timeout=timeout)
        return _FakeProc(stderr="failed to collect stats. runner returned 1", returncode=1)

    monkeypatch.setattr(code_gate, "_run", run)
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert outcome["status"] == "error"
    assert "기준 테스트가 실패" in outcome["human_reason"]
    assert "통과" not in outcome["human_reason"]
    assert not any("열 번호와 변이 종류" in note for note in ctx.notes)   # 없는 목록을 설명하지 않는다


# ---------------------------------------------------------------------------
# 17 — 1b 검토에서 확인된 결함들
#
# 아래는 전부 실물 실행으로 재현된 것이다. 각 테스트의 문서 문자열에 그 회차에서 실제로
# 나온 잘못된 출력을 적어 둔다 — 무엇을 막는 테스트인지가 이름만으로는 남지 않는다.
# ---------------------------------------------------------------------------

def test_the_interpreter_path_is_absolute(tmp_path, monkeypatch):
    """상대 경로로 부르면 C7 의 파이썬 경로만 오류로 끝났다 (확정 11).

    파이썬 경로는 이 인터프리터를 저장소 밖(캐시 작업 디렉토리)에서 부르는 유일한 자리다.
    `--repo-root .` 로 부르면 `.venv/bin/python` 을 그 자리에서 찾지 못해
    "FileNotFoundError: '.venv/bin/python'" 이 나갔다.
    """
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    _write(tmp_path / "system" / "python3.14", "")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").symlink_to(tmp_path / "system" / "python3.14")
    monkeypatch.chdir(tmp_path)
    resolved = resolve_python(Path("."))
    assert Path(resolved).is_absolute()
    assert Path(resolved).is_file()
    # 심링크는 풀지 않는다 — 가상환경의 python 은 대개 시스템 인터프리터를 가리키는
    # 심링크라, 풀면 가상환경 밖으로 나가 그 환경에만 있는 패키지(mutmut 등)가 사라진다.
    assert resolved.endswith("/.venv/bin/python")


def test_repo_root_is_always_absolute(tmp_path, monkeypatch):
    """상대 경로 루트로 부르면 사본의 심링크가 아무 데도 가리키지 않았다 (확정 11).

    "0 files mutated" 로 끝나고, 그 전에는 인터프리터 경로부터 못 찾아 그 항목만 오류였다.
    """
    monkeypatch.chdir(tmp_path)
    assert code_gate._resolve_repo_root(".") == Path(tmp_path)
    assert code_gate._resolve_repo_root("sub").is_absolute()


def test_repo_root_falls_back_to_git_then_to_the_current_dir(tmp_path, monkeypatch):
    """루트를 안 주면 git 최상위를, git 이 없으면 현재 디렉토리를 쓴다 (기존 동작 유지)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(code_gate.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(code_gate, "_run",
                        lambda cmd, *, cwd, timeout: _FakeProc(stdout=f"{tmp_path}\n"))
    assert code_gate._resolve_repo_root(None) == Path(tmp_path)

    monkeypatch.setattr(code_gate.shutil, "which", lambda name: None)
    assert code_gate._resolve_repo_root(None) == Path.cwd()

    monkeypatch.setattr(code_gate.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _FakeProc(returncode=128))
    assert code_gate._resolve_repo_root(None) == Path.cwd()

    def boom(cmd, *, cwd, timeout):
        raise OSError("git 을 띄우지 못했습니다")

    monkeypatch.setattr(code_gate, "_run", boom)
    assert code_gate._resolve_repo_root(None) == Path.cwd()   # 게이트는 죽지 않는다 (R2)


def test_the_active_virtualenv_wins_over_the_project_one(tmp_path, monkeypatch):
    """활성화된 가상환경이 프로젝트 것보다 앞이다 — 없으면 게이트 자신으로 물러선다."""
    _write(tmp_path / "venvA" / "bin" / "python", "")
    _write(tmp_path / ".venv" / "bin" / "python", "")
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "venvA"))
    assert resolve_python(tmp_path) == str(tmp_path / "venvA" / "bin" / "python")
    monkeypatch.delenv("VIRTUAL_ENV")
    assert resolve_python(tmp_path) == str(tmp_path / ".venv" / "bin" / "python")
    assert resolve_python(tmp_path / "nowhere") == sys.executable

    class _Unreadable:
        """읽을 수 없는 후보 — 권한이 없거나 경로가 망가진 경우."""

        def is_file(self):
            raise OSError("permission denied")

    monkeypatch.setattr(code_gate, "_python_candidates",
                        lambda root: [_Unreadable(), tmp_path / ".venv" / "bin" / "python"])
    assert resolve_python(tmp_path) == str(tmp_path / ".venv" / "bin" / "python")


def test_python_test_status_is_kept_when_the_suite_times_out(tmp_path, monkeypatch):
    """C1 이 예산을 넘겨 죽으면 상태가 비어 있어 C7 의 가드가 통과됐다 (확정 7).

    스위트 예산(3초)을 못 지킨 저장소에서 그 스위트를 뮤테이션 예산(기본 600초)으로 다시
    돌리는 회차가 실제로 나왔다.
    """
    _write(tmp_path / "tests" / "test_a.py", "def test_x():\n    assert True\n")
    _write(tmp_path / "pkg.py", "def f():\n    return 1\n")
    tools = _with_mutmut()
    tools["pytest"] = {"available": True, "path": "pytest", "install_hint": ""}
    ctx = _ctx(tmp_path, files=["pkg.py"], tools=tools)

    def run(cmd, *, cwd, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(code_gate, "_run", run)
    with pytest.raises(subprocess.TimeoutExpired):
        check_tests(ctx)
    assert ctx.python_tests_status == "timeout"

    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "예산 안에 끝나지 않아" in outcome["human_reason"]


def test_skipped_python_tests_do_not_tell_the_user_to_fix_them(tmp_path):
    """C1 이 건너뛴 것과 실패한 것을 한 문장으로 묶으면 안 된다 (확정 8).

    저장소 최상위에 test_*.py 를 둔 배치에서 pytest 는 통과하는데 게이트는
    "파이썬 테스트가 통과하지 않아 ... 테스트를 먼저 고치십시오" 라고 말했다.
    """
    ctx = _ctx(tmp_path, files=["pkg.py"], tools=_with_mutmut())
    ctx.python_tests_status = "skipped"
    outcome = check_mutation(ctx)
    assert outcome["status"] == "skipped"
    assert "테스트 자체는 실패하지 않았습니다" in outcome["human_reason"]
    assert "먼저 고치십시오" not in outcome["human_reason"]

    ctx.python_tests_status = "findings"
    assert "먼저 고치십시오" in check_mutation(ctx)["human_reason"]


def test_mutation_on_the_def_line_is_not_lost(tmp_path):
    """`def` 줄에서 일어난 변이가 세 칸을 모두 비운 채 나갔다 (확정 9).

    기본 인자값 변이와 한 줄 def 이 그 자리다. 이름 줄을 떼어 내고 견주면 남는 것이 같아져
    "자리를 알 수 없음" 으로 떨어졌는데, 정보는 사본에 멀쩡히 있었다.
    """
    orig = ["def x_retry__mutmut_orig(times=3):", "    return times"]
    mutant = ["def x_retry__mutmut_1(times=4):", "    return times"]
    assert mutmut_change(orig, mutant) == (0, "def retry(times=3):", "def retry(times=4):")

    one_line = (["def x_double__mutmut_orig(a): return a * 2"],
                ["def x_double__mutmut_2(a): return a * 3"])
    assert mutmut_change(*one_line) == (0, "def double(a): return a * 2", "def double(a): return a * 3")

    method = (["def xǁCartǁtotal__mutmut_orig(self):", "    return 1"],
              ["def xǁCartǁtotal__mutmut_1(self):", "    return 2"])
    assert mutmut_change(*method) == (1, "    return 1", "    return 2")


def test_python_decorated_skips_names_what_mutmut_never_mutates():
    """데코레이터가 붙은 함수와 클래스 안은 통째로 변이되지 않는데 아무 표시가 없었다 (확정 3).

    커버리지 79% 인 파일이 뮤테이션 100% 통과로 나갔고, 금액 계산 함수 셋이 한 번도
    변이되지 않았다. 파일 단위 안전망은 이 경우를 못 잡는다 — 그 파일에도 변이 가능한
    함수가 하나 있었기 때문이다.
    """
    source = (
        "import dataclasses\n"
        "def route(fn):\n    return fn\n"
        "@route\n"
        "def price(x):\n    return x * 2\n"
        "@dataclasses.dataclass\n"
        "class Cart:\n"
        "    def total(self):\n        return 1\n"
        "    @property\n"
        "    def count(self):\n        return 2\n"
        "class Plain:\n"
        "    @staticmethod\n"
        "    def helper():\n        return 3\n"
        "def version():\n    return 'v1'\n"
    )
    assert python_decorated_skips(source) == ("Cart.count", "Cart.total", "price")
    assert python_decorated_skips("def broken(:\n") == ()


def test_decorated_functions_are_reported_to_the_user(tmp_path, monkeypatch):
    """빠진 함수가 사용자 눈에 보여야 한다 (확정 3·R4)."""
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE + "\n@staticmethod\n@property\ndef fee(x):\n    return x\n")
    monkeypatch.setattr(code_gate, "_run", _fake_mutmut_run())
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert "데코레이터가 붙어 있어 변이가 하나도 만들어지지 않았습니다" in outcome["human_reason"]
    assert f"{REL}::fee" in outcome["human_reason"]
    # 못 본 것이 있으면 통과로 내지 않는다 — 사본의 변이는 전부 잡혔지만 이 함수는 안 쟀다.
    assert outcome["status"] == "findings"


@pytest.mark.parametrize("rel, expected", [
    ("tests", "tests"),
    ("tests/unit", "tests"),
    ("../sharedtests", ""),
    ("/private/tmp/sharedtests", ""),
    (".", ""),
    ("mutants", ""),
    ("setup.cfg", ""),
])
def test_link_names_must_live_inside_the_work_dir(rel, expected):
    """이름을 검증하지 않아 작업 디렉토리 밖을 지웠다 (확정 5).

    `testpaths = ../sharedtests` 하나로 캐시 디렉토리가 통째로 비었다 — 자바스크립트 증분
    상태 파일까지 함께 사라졌고, 그 배치에서는 매 회차 반복됐다. 절대 경로면 그 자리에
    `/` 가 온다.
    """
    assert _mutmut_link_name(rel) == expected


def test_a_rejected_test_path_never_reaches_the_unlink_step(tmp_path):
    """걸 수 없는 이름은 링크 단계 앞에서 멈춘다 — 지우는 쪽이 밖을 만지기 전이다 (확정 5)."""
    outside = tmp_path / "outside"
    _write(outside / "keep.txt", "지워지면 안 되는 파일")
    work = tmp_path / "work"
    work.mkdir()
    assert "만들 수 없는 이름" in _mutmut_link(work, tmp_path, ["../outside"])
    assert (outside / "keep.txt").is_file()

    (tmp_path / "sharedtests").mkdir()          # 소스 루트 밖의 테스트 (모노레포 배치)
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "tests" / "unit").mkdir()
    _write(repo / "pytest.ini",
           "[pytest]\ntestpaths = ../sharedtests . tests tests/unit src\n")
    found, rejected = _mutmut_test_roots(repo, ("src",))
    # tests 는 걸 수 있고, tests/unit 은 같은 최상위라 한 번만 센다. src 는 이미 소스 루트다.
    assert found == ["tests"]
    assert rejected == ["../sharedtests", "."]


def test_a_stale_mutants_symlink_is_reclaimed(tmp_path):
    """사본 자리에 링크가 걸리면 원인을 없애도 회차마다 프로젝트에 사본이 쌓였다 (추가 2)."""
    project = tmp_path / "repo"
    project.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    (work / "mutants").symlink_to(project)
    notes: list = []
    _mutmut_reclaim(work, notes)
    assert not (work / "mutants").exists()
    assert project.is_dir()                       # 프로젝트는 그대로 둔다
    assert any("지난 회차의 링크가 걸려 있어 지웠습니다" in note for note in notes)


def _work_with_mutants(tmp_path, targets):
    """지난 회차 사본이 남아 있는 작업 디렉토리."""
    work = tmp_path / "work"
    (work / "mutants" / "src").mkdir(parents=True)
    _write(work / "mutants" / "src" / "a.py.meta", "{}")
    _write(work / mutation_python._MUTMUT_STATE_NAME, json.dumps({"targets": list(targets)}))
    return work


def test_incremental_copy_is_dropped_when_the_tests_changed(tmp_path):
    """확인문을 전부 지운 회차가 100% 로 통과했다 (확정 1).

    같은 상태를 처음부터 돌리면 0% 다. mutmut 은 사본 안 결과를 함수 해시로만 무효화해서,
    테스트가 바뀌어도 지난 회차의 "잡힘" 을 그대로 재사용한다.
    """
    work = _work_with_mutants(tmp_path, ["src/a.py"])
    ctx = _ctx(tmp_path)
    _mutmut_incremental_guard(ctx, work, ["src/a.py"], ["tests/test_a.py"])
    assert not (work / "mutants").exists()
    assert any("테스트 파일이 이번 변경분에 있어" in note for note in ctx.notes)


def test_incremental_copy_is_dropped_when_the_target_set_changed(tmp_path):
    """대상이 늘어난 회차에서 새 파일이 통째로 "덮은 테스트 없음" 으로 굳었다 (확정 2).

    회차를 더 돌려도 회복되지 않았다 — mutmut 은 `only_mutate` 변경을 무효화 사유로 보지 않는다.
    """
    work = _work_with_mutants(tmp_path, ["src/a.py"])
    ctx = _ctx(tmp_path)
    _mutmut_incremental_guard(ctx, work, ["src/a.py", "src/b.py"], [])
    assert not (work / "mutants").exists()
    assert any("대상 파일 목록이 지난 회차와 달라" in note for note in ctx.notes)


def test_incremental_copy_is_kept_when_nothing_relevant_changed(tmp_path):
    """버릴 이유가 없으면 그대로 쓴다 — 매 회차 버리면 증분이 무의미해진다 (R1)."""
    work = _work_with_mutants(tmp_path, ["src/a.py"])
    ctx = _ctx(tmp_path)
    _mutmut_incremental_guard(ctx, work, ["src/a.py"], [])
    assert (work / "mutants").is_dir()
    assert ctx.notes == []


def test_a_run_that_stopped_early_is_not_a_pass(tmp_path, monkeypatch):
    """종료 코드 1 로 죽었는데 지난 회차 사본이 남아 "통과 100%" 가 나갔다 (확정 4).

    실측 문장: "점수 100.0% (기준 80%), 변이 7개 중 잡히지 않음 0개 — 잡힘 2 / 실행 안 됨 5".
    같은 문장 안에서 "변이 7개" 와 "잡히지 않음 0개" 의 모수가 다르다 (D4).
    """
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    mixed = {"exit_code_by_key": {
        "pysandbox.loopx.x_count_up__mutmut_1": 1,
        "pysandbox.loopx.x_count_up__mutmut_4": None,
        "pysandbox.loopx.x_count_up__mutmut_8": None,
    }}

    def run(cmd, *, cwd, timeout):
        _fake_mutmut_run(meta=mixed)(cmd, cwd=cwd, timeout=timeout)
        return _FakeProc(stderr="failed to collect stats. runner returned 1", returncode=1)

    monkeypatch.setattr(code_gate, "_run", run)
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert outcome["status"] == "error"
    assert "변이 3개 중 2개를 재지 못해 점수를 내지 않았습니다" in outcome["human_reason"]
    assert "통과" not in outcome["human_reason"]


def test_no_test_covering_the_change_is_a_zero_score_not_a_setup_error(tmp_path, monkeypatch):
    """무테스트 파일만 바뀐 회차에서 점수 0% 대신 오류가 났고, 사유도 틀렸다 (확정 10).

    D1 이 no_coverage 를 분모에 남기는 이유가 바로 이 경우인데, 이 경우에만 점수가 안 나왔다.
    안내는 실제 원인 대신 설정 오류를 가리켜 사용자를 엉뚱한 데로 보냈다.
    """
    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    pending = {"exit_code_by_key": {k: None for k in LOOPX_META["exit_code_by_key"]}}

    def run(cmd, *, cwd, timeout):
        _fake_mutmut_run(meta=pending)(cmd, cwd=cwd, timeout=timeout)
        return _FakeProc(
            stderr="could not find any test case for any mutant, aborting", returncode=1)

    monkeypatch.setattr(code_gate, "_run", run)
    ctx = _ctx(project, files=[REL], tools=_with_mutmut())
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert outcome["status"] == "findings"
    assert "점수 0.0%" in outcome["human_reason"]
    assert "덮은 테스트 없음 3" in outcome["human_reason"]
    assert any("덮는 테스트를 mutmut 이 하나도 찾지 못했습니다" in note for note in ctx.notes)


def test_bracketed_paths_are_escaped_in_the_target_list(tmp_path):
    """대괄호가 든 경로는 자기 자신과 안 맞아 어떤 회차에도 변이되지 않았다 (확정 13).

    `only_mutate` 는 mutmut 이 fnmatch 로 맞추는 글롭이다. 소스 루트는 글롭이 아니라 경로라
    이스케이프하지 않는다.
    """
    work = tmp_path / "work"
    work.mkdir()
    _write_mutmut_config(work, ("src",), ("src/pkg/legacy[old].py", "src/pkg/mathx.py"), (), {})
    body = (work / "setup.cfg").read_text(encoding="utf-8")
    assert "src/pkg/legacy[[]old].py" in body
    assert "src/pkg/mathx.py" in body
    assert "source_paths=\n\tsrc\n" in body


def test_the_budget_belongs_to_the_check_not_to_each_language(tmp_path, monkeypatch):
    """두 언어가 예산을 각자 통째로 잡아 C7 하나가 설정값의 두 배까지 돌았다 (확정 6).

    실측: 설정 2초에 항목 4.04초. 기본값 600 에서는 최대 1,200초다.
    """
    ctx = _ctx(tmp_path, files=["a.py"])
    assert _mutation_budget(ctx) == ctx.config.mutation_timeout_seconds   # 마감이 없으면 전부
    ctx.mutation_deadline = time.perf_counter() + 5
    assert 0 < _mutation_budget(ctx) <= 5
    ctx.mutation_deadline = time.perf_counter() - 1
    assert _mutation_budget(ctx) == 0

    project = tmp_path / "repo"
    _write(project / REL, LOOPX_SOURCE)
    _write(project / "src" / "a.js", "export const x = 1;\n")

    def burn(inner_ctx, js_files):
        """자바스크립트가 예산을 다 쓴 회차 — 실제로 시간을 태운다.

        마감 시각을 뒤로 미는 방식으로는 이제 흉내 낼 수 없다. 어댑터마다 자기 몫을 다시
        정하므로(_mutation_share) 앞 어댑터가 그 값을 만져도 뒤에 넘어가지 않는다.
        진짜로 바닥나는 길은 벽시계 시간뿐이라 그것을 그대로 쓴다.
        """
        time.sleep(1.2)
        return {"language": "javascript", "label": "자바스크립트", "summary": None,
                "outcome": _skip_outcome()}

    monkeypatch.setattr(mutation_javascript, "_check_mutation_javascript", burn)
    # 준비 단계에서 예산이 바닥나도 같은 문장이 나간다 — 0초로 띄우면 "중간 결과가 없다" 가
    # 되어 재지 못한 이유가 바뀐다.
    exhausted = _ctx(tmp_path)
    exhausted.mutation_deadline = time.perf_counter() - 1
    outcome, summary = mutation_python._mutmut_run(exhausted, tmp_path, ["true"], (), [])
    assert summary is None and "앞 언어가 뮤테이션 예산" in outcome["human_reason"]

    _write(project / ".code-gate.json", '{"mutation": {"timeout_seconds": 1}}')
    ctx = _ctx(project, files=[REL, "src/a.js"], tools=_with_mutmut(),
               config=load_config(project / ".code-gate.json"))
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert "앞 언어가 뮤테이션 예산" in outcome["human_reason"]
    assert "파이썬은 재지 못했습니다" in outcome["human_reason"]


def test_the_budget_is_split_so_the_order_does_not_decide_who_runs(tmp_path, monkeypatch):
    """앞 어댑터가 예산을 통째로 쓰면 뒤 언어의 점수·목록·설치 안내가 함께 사라졌다 (확정 2).

    실측: 자바 + 자바스크립트에 예산 6초를 주었더니, 자바스크립트 입력이 한 글자도
    바뀌지 않았는데 `84.6% + 살아남음 2개` 가 `재지 못했습니다 + 목록 0개` 가 됐다.
    등록 순서는 언어 이름의 알파벳순이라 뜻이 없는데, 그 뜻 없는 값이 누가 재는지를
    정하고 있었다.
    """
    deadline = time.perf_counter() + 6
    # 셋이 남았으면 3분의 1, 하나만 남았으면 남은 전부.
    assert 1.9 < _mutation_share(deadline, 3) < 2.1
    assert 5.9 < _mutation_share(deadline, 1) < 6.1
    # 이미 지난 마감에서는 0 이다 — 음수 몫이 timeout 인자로 흘러가면 안 된다.
    assert _mutation_share(time.perf_counter() - 5, 2) == 0.0


def test_a_skipping_adapter_does_not_starve_the_next_language(tmp_path, monkeypatch):
    """도구가 없어 0초에 건너뛴 앞 언어가 뒤 언어를 굶겼다 (확정 2).

    실측: 고는 0초에 건너뛰었는데 자바스크립트에게 "앞 언어가 예산을 다 썼다" 고 말하고,
    자바스크립트 설치 안내가 통째로 사라졌다 (R4).
    """
    project = tmp_path / "repo"
    _write(project / "src" / "a.js", "export const x = 1;\n")
    _write(project / ".code-gate.json", '{"mutation": {"timeout_seconds": 1}}')

    def instant_skip(inner_ctx, files):
        return {"language": "go", "label": "고", "summary": None,
                "outcome": code_gate._skip("gremlins 가 설치돼 있지 않습니다.", "gremlins missing",
                                           "gremlins 를 설치하십시오.")}

    monkeypatch.setattr(mutation_go, "_check_mutation_go", instant_skip)
    monkeypatch.setattr(mutation_go, "_mutation_changed_go", lambda ctx: ["a.go"])
    ctx = _ctx(project, files=["a.go", "src/a.js"],
               config=load_config(project / ".code-gate.json"))
    ctx.repo_root = project
    outcome = check_mutation(ctx)
    assert "앞 언어가 뮤테이션 예산" not in outcome["human_reason"]
    assert "Stryker 가 설치돼 있지 않습니다" in outcome["human_reason"]
    assert "@stryker-mutator/core" in (outcome["install_hint"] or "")
    assert "gremlins 를 설치하십시오." in (outcome["install_hint"] or "")


def test_python_sources_named_spec_are_not_mistaken_for_tests(tmp_path):
    """자바스크립트 관례(`spec` / `__mocks__` / `_spec`)로 파이썬 소스가 빠졌다 (추가 1).

    실측: 사양 문서를 파싱하는 `src/spec/parser.py` 가 "테스트·삭제된 파일" 로 보고되며
    한 번도 변이되지 않았다.
    """
    for rel in ("src/spec/parser.py", "src/api_spec.py", "src/__mocks__/fake.py",
                "tests/test_a.py", "pkg/core_test.py"):
        _write(tmp_path / rel, "def f():\n    return 1\n")
    targets, dropped = _mutmut_targets(tmp_path, [
        "src/spec/parser.py", "src/api_spec.py", "src/__mocks__/fake.py",
        "tests/test_a.py", "pkg/core_test.py"])
    assert set(targets) == {"src/spec/parser.py", "src/api_spec.py", "src/__mocks__/fake.py"}
    assert set(dropped) == {"tests/test_a.py", "pkg/core_test.py"}


def test_unknown_status_names_are_marked_as_unknown_in_korean():
    """게이트 어휘 밖의 이름이 한국어 문장에 영어 그대로 실려 정상 항목처럼 읽혔다 (추가 3).

    이름은 지어내지 않고 그대로 두되, 모르는 것임을 함께 적는다 (R4).
    """
    text = _mutation_distribution({"Killed": 9, "suspicious": 3, "caught by type check": 2})
    assert "잡힘 9" in text
    assert "모르는 상태 'suspicious' 3" in text
    assert "모르는 상태 'caught by type check' 2" in text


# ---------------------------------------------------------------------------
# 16 — 상세 줄 수 (--limit) 와 렌더링 사슬
# ---------------------------------------------------------------------------

def _payload_with(code, findings, status="findings"):
    return {
        "total_seconds": 0.1, "base": "HEAD", "base_reason": "기준",
        "changed": 1, "excluded": 0, "notes": [],
        "checks": [{"code": code, "name": "x", "label": "이름", "status": status,
                    "seconds": 0.1, "reason": "", "human_reason": "요약",
                    "install_hint": None, "findings": findings}],
    }


def _c3_findings(n):
    return [{"file": f"src/m{i}.py", "line": i, "function": f"f{i}", "complexity": 11}
            for i in range(n)]


def test_detail_lines_cuts_and_says_how_many_are_hidden():
    """자를 때 가린 건수를 반드시 적는다. 안 적으면 그 목록이 전부인 줄로 읽힌다."""
    check = _payload_with("C3", _c3_findings(20))["checks"][0]
    lines = code_gate._detail_lines(check, 15)
    assert len(lines) == 16
    assert lines[-1].strip() == "... 외 5건"


def test_detail_lines_zero_means_all_and_no_hidden_note():
    """0 은 전부다. 가린 것이 없으므로 '외 N건' 도 붙지 않는다."""
    check = _payload_with("C3", _c3_findings(20))["checks"][0]
    lines = code_gate._detail_lines(check, 0)
    assert len(lines) == 20
    assert not any("외" in line for line in lines)


def test_detail_lines_ignores_unknown_check_code():
    """모르는 항목 코드는 빈 목록이다. 형식을 지어내면 사용자가 잘못 읽는다."""
    check = _payload_with("C9", _c3_findings(3))["checks"][0]
    assert code_gate._detail_lines(check, 15) == []


def test_crap_line_separates_no_data_from_zero_coverage():
    """커버리지를 못 구한 것과 0 인 것은 다른 사실이다. 못 구한 것을 0 으로 적으면
    '테스트가 없다' 로 읽힌다."""
    base = {"file": "a.py", "line": 3, "function": "f", "complexity": 8,
            "coverage_source": "range-empty"}
    unknown = code_gate._crap_detail_line({**base, "crap": None})
    known = code_gate._crap_detail_line({**base, "crap": 72.0, "coverage": 0.0})
    assert "CRAP 계산 실패" in unknown
    assert "v=0.00" in known and "CRAP=72.00" in known


def test_render_details_passes_limit_through_the_chain():
    """--limit 이 렌더 사슬 끝까지 전달되는지. 한 군데만 빠져도 15줄에서 잘린다."""
    payload = _payload_with("C3", _c3_findings(20))
    assert payload["checks"][0]["findings"]
    all_lines = code_gate.render_human(payload, 0)
    cut_lines = code_gate.render_human(payload, 15)
    assert all_lines.count("src/m") == 20
    assert cut_lines.count("src/m") == 15
    assert "외 5건" in cut_lines


def test_render_details_skips_coverage_item():
    """C2 는 상세를 내지 않는다 — 항목 요약 줄에 이미 파일별 비율이 들어 있다."""
    payload = _payload_with("C2", [{"file": "a.py"}], status="measured")
    assert code_gate._render_details(payload["checks"], 15) == []


def test_emit_falls_back_to_json_when_rendering_breaks(capsys, monkeypatch):
    """렌더링이 실패해도 결과는 내놓는다. 삼키면 잰 것이 통째로 사라진다."""
    monkeypatch.setattr(code_gate, "render_human",
                        lambda *a, **k: (_ for _ in ()).throw(ValueError("깨짐")))
    code_gate._emit(_payload_with("C3", _c3_findings(1)), as_json=False)
    out = capsys.readouterr().out
    assert "렌더링에 실패해" in out
    assert '"code": "C3"' in out


# ---------------------------------------------------------------------------
# 17 — 게이트 자신의 커버리지 구멍 (CRAP 높은 순)
#
# 이 절의 대상은 전부 "테스트 파일에 이름조차 없던" 함수들이다. 서브프로세스로만
# 돌아 커버리지가 못 보던 것(main / run_gate)과 구분해서, 실제로 아무 확인문도
# 없던 것만 여기서 메운다.
# ---------------------------------------------------------------------------

def _crap_ctx(tmp_path, rows, coverage_map=None):
    ctx = _ctx(tmp_path, files=tuple({r["file"] for r in rows}) or ("a.py",))
    ctx.complexity_rows = list(rows)
    ctx.coverage_map = coverage_map or {}
    return ctx


# --- C4 판정 (check_crap) -------------------------------------------------

def test_crap_without_complexity_data_is_skipped_not_ok(tmp_path):
    """복잡도 행이 없으면 '통과' 가 아니라 '건너뜀' 이어야 한다 (R4).

    lizard 가 없거나 전부 폐기된 회차가 정확히 이 상태다. 여기서 ok 를 내면
    "복잡한 함수가 하나도 없다" 로 읽혀, 아무것도 재지 않은 회차가 가장 깨끗한
    리포트를 낸다.
    """
    outcome = check_crap(_crap_ctx(tmp_path, []))
    assert outcome["status"] == "skipped"
    assert outcome["reason"] == "no complexity rows"


def test_crap_with_no_overlapping_function_is_skipped_not_ok(tmp_path):
    """변경분과 겹치는 함수가 없을 때도 통과가 아니다 (R3+R4).

    복잡도는 잰 게 있는데 그 중 변경분에 걸린 것이 없다는 사실 자체를 남겨야
    한다. ok 로 내면 '변경된 함수 0개 모두 기준 이하' 라는 참이지만 무의미한
    문장이 통과로 보인다.
    """
    ctx = _crap_ctx(tmp_path, [_row(file="a.py", start=10, end=20)])
    ctx.change = _changeset(("a.py",), {"a.py": frozenset({500})})
    outcome = check_crap(ctx)
    assert outcome["status"] == "skipped"
    assert outcome["reason"] == "no changed functions"


def test_crap_over_threshold_is_sorted_worst_first(tmp_path):
    """초과 목록은 CRAP 내림차순이어야 한다 — --limit 으로 자를 때 가장 나쁜 것이 남는다.

    정렬이 뒤집히면 잘린 목록에 제일 안전한 함수만 남아, 자른 리포트가 실제와
    정반대의 인상을 준다.
    """
    rows = [_row(file="a.py", function="low", complexity=7, start=1, end=5),
            _row(file="a.py", function="high", complexity=20, start=10, end=15)]
    outcome = check_crap(_crap_ctx(tmp_path, rows))
    assert outcome["status"] == "findings"
    assert [f["function"] for f in outcome["findings"]] == ["high", "low"]
    assert outcome["findings"][0]["crap"] > outcome["findings"][1]["crap"]


def test_crap_counts_functions_without_coverage_data_in_the_summary(tmp_path):
    """커버리지 데이터가 아예 없던 함수 수를 요약 줄에 적어야 한다 (R4).

    이 숫자가 빠지면 '커버리지 0%' 와 '커버리지를 못 구함' 이 한 덩어리가 된다.
    앞은 테스트가 없다는 뜻이고 뒤는 아무것도 모른다는 뜻이라 대응이 다르다.
    """
    outcome = check_crap(_crap_ctx(tmp_path, [_row(complexity=20)]))
    assert "커버리지 데이터 없는 함수 1개 포함" in outcome["human_reason"]


def test_crap_unresolved_functions_are_findings_even_without_any_over(tmp_path):
    """CRAP 을 계산 못 한 함수만 있어도 통과가 아니다.

    `range-empty` (잴 줄이 하나도 없음) 가 그 경우다. 이것을 ok 로 흘리면
    커버리지 짝짓기에 실패한 함수가 전부 조용히 사라진다.
    """
    rows = [_row(file="a.py", complexity=3, start=10, end=11)]
    cov = {"a.py": _cov(executed=(), missing=())}
    outcome = check_crap(_crap_ctx(tmp_path, rows, cov))
    assert outcome["status"] == "findings"
    assert outcome["findings"][0]["crap"] is None
    assert "계산 못 한 함수 1개" in outcome["human_reason"]


def test_crap_all_within_threshold_is_ok_with_the_count(tmp_path):
    """전부 기준 이하면 ok 이고, 몇 개를 봤는지 숫자가 남아야 한다.

    숫자가 없으면 '0개를 검사해서 0개 초과' 인 회차와 구별되지 않는다.
    """
    rows = [_row(file="a.py", complexity=2, start=10, end=20)]
    cov = {"a.py": _cov(functions=((10, 1.0),))}
    outcome = check_crap(_crap_ctx(tmp_path, rows, cov))
    assert outcome["status"] == "ok"
    assert "변경된 함수 1개 모두 기준" in outcome["human_reason"]


# --- C1 pytest 판정 (_pytest_outcome / _parse_pytest_counts) --------------

def test_pytest_counts_read_the_last_summary_line():
    """요약 줄은 마지막 것이 진짜다 — 앞쪽 출력에도 '3 passed' 같은 문자열이 섞인다."""
    text = "some log mentioning 99 passed\n=== 4 passed, 2 failed ==="
    assert _parse_pytest_counts(text) == {"passed": 4, "failed": 2}


def test_pytest_counts_normalise_errors_to_a_singular_key():
    """`errors` 와 `error` 가 같은 칸에 들어가야 한다.

    `_pytest_outcome` 은 `counts.get("error")` 로만 읽는다. 철자를 정규화하지
    않으면 에러만 난 회차가 실패 0 건으로 집계돼 ok 로 보고된다.
    """
    assert _parse_pytest_counts("=== 2 errors in 1s ===") == {"error": 2}
    assert _parse_pytest_counts("=== 1 error in 1s ===") == {"error": 1}


def test_pytest_counts_are_empty_when_no_summary_line_exists():
    assert _parse_pytest_counts("collecting ...\nboom\n") == {}


def test_pytest_outcome_treats_errors_as_failures():
    """수집 에러는 실패로 세어야 한다. 통과로 보고되면 깨진 스위트가 초록으로 보인다."""
    proc = _FakeProc(stdout="ERROR tests/test_a.py\n=== 3 passed, 2 errors ===", returncode=1)
    outcome = code_gate._pytest_outcome(proc)
    assert outcome["status"] == "findings"
    assert "3개 통과, 2개 실패" == outcome["human"]
    assert outcome["findings"][0]["detail"].startswith("ERROR")


def test_pytest_outcome_caps_the_failure_detail_at_twenty_lines():
    """실패 상세는 20줄까지만 싣는다. 전량을 실으면 리포트가 로그로 뒤덮인다."""
    body = "\n".join(f"FAILED tests/test_a.py::t{i}" for i in range(50))
    proc = _FakeProc(stdout=f"{body}\n=== 0 passed, 50 failed ===", returncode=1)
    assert len(code_gate._pytest_outcome(proc)["findings"]) == 20


def test_pytest_outcome_collected_nothing_is_skipped_not_ok():
    """종료 코드 5(수집 0건)는 건너뜀이다 (R4).

    ok 로 내면 테스트 경로 오타 하나가 '통과' 로 보고된다 — 게이트가 있으나
    마나 한 상태를 가장 깨끗한 결과로 표시하게 된다.
    """
    outcome = code_gate._pytest_outcome(_FakeProc(stdout="no tests ran", returncode=5))
    assert outcome["status"] == "skipped"
    assert outcome["reason"] == "pytest collected nothing"


def test_pytest_outcome_abnormal_exit_without_counts_is_a_finding():
    """요약 줄이 없는데 비-0 종료면 발견이다.

    import 시점 크래시가 정확히 이 모양이다 (요약 줄 자체가 안 나온다).
    통과로 흘리면 스위트가 한 줄도 안 돌았는데 초록이 된다.
    """
    proc = _FakeProc(stderr="ImportError: no module named x", returncode=2)
    outcome = code_gate._pytest_outcome(proc)
    assert outcome["status"] == "findings"
    assert "비정상 종료" in outcome["human"]
    assert "ImportError" in outcome["findings"][0]["detail"]


def test_pytest_outcome_all_passing_is_ok():
    outcome = code_gate._pytest_outcome(_FakeProc(stdout="=== 7 passed in 1s ===", returncode=0))
    assert outcome["status"] == "ok"
    assert outcome["human"] == "7개 통과, 0개 실패"


# --- 기준 결정 (resolve_base) ---------------------------------------------

def _git_probe(known):
    """`git rev-parse` / `symbolic-ref` 성공 여부만 흉내내는 _run 대역."""
    def run(cmd, *, cwd, timeout):
        target = cmd[-1]
        if target in known:
            return _FakeProc(stdout=known[target] + "\n", returncode=0)
        return _FakeProc(returncode=1)
    return run


def test_resolve_base_prefers_the_user_value_without_touching_git(monkeypatch):
    """--base 를 준 회차는 git 을 아예 보지 않는다.

    사용자가 지정한 기준을 자동 판정이 덮으면 R3(변경분만 검사)의 범위가
    사용자 의도와 달라진 채로 조용히 돈다.
    """
    monkeypatch.setattr(code_gate, "_run",
                        lambda *a, **k: pytest.fail("--base 가 있으면 git 을 부르면 안 된다"))
    ref, why = code_gate.resolve_base(Path("."), "release/1.0")
    assert ref == "release/1.0"
    assert "지정한" in why


@pytest.mark.parametrize("known, expected", [
    ({"main": "abc", "refs/remotes/origin/HEAD": "origin/dev", "HEAD~1": "old"}, "main"),
    ({"refs/remotes/origin/HEAD": "origin/dev", "HEAD~1": "old"}, "origin/dev"),
    ({"HEAD~1": "old"}, "HEAD~1"),
    ({}, code_gate.EMPTY_TREE),
])
def test_resolve_base_falls_back_in_a_fixed_order(monkeypatch, known, expected):
    """main → 원격 기본 브랜치 → HEAD~1 → 빈 트리 순서가 고정이어야 한다.

    순서가 바뀌면 main 이 있는 저장소가 HEAD~1 기준으로 돌아 검사 범위가 직전
    커밋 한 개로 쪼그라든다. 아무 경고 없이 '변경 파일 2개' 라는 정상적인
    리포트가 나오기 때문에 눈으로는 못 잡는다.
    """
    monkeypatch.setattr(code_gate, "_run", _git_probe(known))
    ref, why = code_gate.resolve_base(Path("."), None)
    assert ref == expected
    assert why  # 사유는 항상 한국어로 남는다


def test_resolve_base_ignores_an_empty_but_successful_git_answer(monkeypatch):
    """종료 코드 0 인데 출력이 빈 경우는 '없음' 으로 봐야 한다.

    `rev-parse --verify --quiet` 는 없는 ref 에도 0 을 돌려주는 조합이 있다.
    코드만 보고 채택하면 존재하지 않는 ref 를 기준으로 잡아 diff 가 통째로 빈다.
    """
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _FakeProc(stdout="  \n", returncode=0))
    ref, _ = code_gate.resolve_base(Path("."), None)
    assert ref == code_gate.EMPTY_TREE


# --- 도구 탐지 (_probe_python_modules) ------------------------------------

def test_probe_python_modules_reads_the_subprocess_answer(monkeypatch):
    monkeypatch.setattr(code_gate, "_run",
                        lambda *a, **k: _FakeProc(stdout='{"pytest": true, "lizard": false}'))
    found = code_gate._probe_python_modules(Path("."), sys.executable, ("pytest", "lizard"), 5)
    assert found == {"pytest": True, "lizard": False}


def test_probe_python_modules_ignores_names_it_did_not_ask_for(monkeypatch):
    """묻지 않은 이름이 답에 섞여도 표에 넣지 않는다.

    반환 사전의 키 집합이 곧 도구 표의 칸이라, 낯선 키가 들어오면 뒤에서
    `found[name]` 이 아니라 표 자체가 부풀어 KeyError 없이 조용히 어긋난다.
    """
    monkeypatch.setattr(code_gate, "_run",
                        lambda *a, **k: _FakeProc(stdout='{"pytest": true, "낯선것": true}'))
    found = code_gate._probe_python_modules(Path("."), sys.executable, ("pytest",), 5)
    assert found == {"pytest": True}


@pytest.mark.parametrize("proc, boom", [
    (_FakeProc(stdout='{"pytest": true}', returncode=1), None),
    (_FakeProc(stdout="not json"), None),
    (None, OSError("no python")),
    (None, subprocess.TimeoutExpired(cmd="python", timeout=1)),
])
def test_probe_python_modules_reports_absence_when_the_probe_fails(monkeypatch, proc, boom):
    """탐지가 실패하면 전부 '없음' 이어야 한다 — 있음으로 추정하면 안 된다.

    '있음' 쪽으로 틀리면 없는 도구를 실행하려다 항목이 오류로 죽고, 그 오류가
    도구 부재라는 진짜 사유를 가린다. 없음으로 틀리면 건너뜀 + 설치 안내가
    나가므로 사용자가 바로 고칠 수 있다.
    """
    def run(*a, **k):
        if boom is not None:
            raise boom
        return proc
    monkeypatch.setattr(code_gate, "_run", run)
    found = code_gate._probe_python_modules(Path("."), sys.executable, ("pytest", "coverage"), 5)
    assert found == {"pytest": False, "coverage": False}


# --- 커버리지 적재 (_load_python_coverage / _function_regions / lcov / istanbul) ---

def test_python_coverage_is_empty_when_the_data_file_was_never_written(tmp_path):
    """C1 이 커버리지 아래에서 돌지 않았으면 빈 사전이다 — 오류가 아니다.

    데이터 파일이 없는 것은 정상적인 회차(coverage 미설치)라서, 여기서 예외를
    던지면 C2 가 오류로 표시돼 진짜 사유(도구 부재)를 덮는다.
    """
    ctx = _ctx(tmp_path, files=("a.py",))
    assert code_gate._load_python_coverage(ctx) == {}
    ctx.coverage_data_file = tmp_path / "없는파일.data"
    assert code_gate._load_python_coverage(ctx) == {}


def test_python_coverage_export_failure_raises_with_the_tool_message(tmp_path, monkeypatch):
    """`coverage json` 이 파일을 못 만들면 조용히 빈 결과를 내면 안 된다 (R4).

    빈 결과는 '커버리지 0%' 로 흘러 CRAP 이 전부 최악값이 된다. 무엇이 잘못됐는지
    도구가 낸 문장을 그대로 물고 올라와야 원인을 찾을 수 있다.
    """
    ctx = _ctx(tmp_path, files=("a.py",))
    ctx.coverage_data_file = _write(tmp_path / "cov.data", "x")
    monkeypatch.setattr(code_gate, "_run",
                        lambda *a, **k: _FakeProc(stderr="No data to report.", returncode=1))
    with pytest.raises(ValueError) as excinfo:
        code_gate._load_python_coverage(ctx)
    assert "No data to report." in str(excinfo.value)


def test_python_coverage_maps_absolute_paths_back_to_repo_relative(tmp_path, monkeypatch):
    """coverage 가 내는 절대 경로를 저장소 상대로 되돌려야 한다.

    변경 파일 목록은 상대 경로라, 되돌리지 않으면 키가 하나도 안 맞아 모든
    변경 파일이 '커버리지 데이터 없음' 이 된다.
    """
    ctx = _ctx(tmp_path, files=("pkg/a.py",))
    ctx.coverage_data_file = _write(tmp_path / "cov.data", "x")
    payload = {"files": {str(tmp_path / "pkg" / "a.py"): {
        "summary": {"percent_covered": 80.0},
        "executed_lines": [2, 3], "missing_lines": [4],
        "functions": {"f": {"start_line": 2, "summary": {"percent_covered": 50.0}}},
    }, "총계": "dict 가 아닌 값은 버린다"}}

    def run(cmd, *, cwd, timeout):
        _write(ctx.tmpdir / "coverage.json", json.dumps(payload))
        return _FakeProc()
    monkeypatch.setattr(code_gate, "_run", run)

    loaded = code_gate._load_python_coverage(ctx)
    assert set(loaded) == {"pkg/a.py"}
    assert loaded["pkg/a.py"].percent == 80.0
    assert loaded["pkg/a.py"].functions == ((2, 0.5),)


def test_function_regions_convert_percent_to_a_ratio():
    """coverage 는 백분율(0~100)을, CRAP 은 비율(0~1)을 쓴다.

    100 배 어긋난 값이 그대로 들어가면 `crap_score` 가 커버리지 100 을 받아
    모든 함수의 CRAP 이 복잡도 그대로가 된다 — 즉 C4 가 사실상 꺼진다.
    """
    entry = {"functions": {"f": {"start_line": 10, "summary": {"percent_covered": 42.0}}}}
    assert code_gate._function_regions(entry) == ((10, 0.42),)


@pytest.mark.parametrize("fn", [
    {"summary": {"percent_covered": 50.0}},              # 시작줄 없음
    {"start_line": 10, "summary": {}},                   # 비율 없음
    {"start_line": "10", "summary": {"percent_covered": 50.0}},   # 시작줄이 문자열
    None,                                                # 항목 자체가 없음
])
def test_function_regions_drop_entries_it_cannot_trust(fn):
    """모양이 다른 항목은 버린다 — 지어낸 값으로 채우면 안 된다.

    시작줄이 없는 항목에 0 을 넣으면 파일 첫 줄의 함수와 짝지어져 엉뚱한
    함수의 커버리지가 다른 함수에 붙는다.
    """
    assert code_gate._function_regions({"functions": {"f": fn}}) == ()


def test_file_coverage_from_entry_keeps_missing_percent_as_none():
    """요약이 없으면 비율은 None 이다 — 0 으로 채우면 '완전 미커버' 로 읽힌다."""
    entry = code_gate._file_coverage_from_entry({})
    assert entry.kind == "coverage-json"
    assert entry.percent is None
    assert entry.executed == frozenset() and entry.missing == frozenset()


def test_lcov_splits_hit_lines_from_missed_lines(tmp_path):
    """DA 의 히트 수 0 은 미실행, 1 이상은 실행이다.

    이 경계가 뒤집히면 커버리지가 통째로 반전돼, 테스트 없는 코드가 가장
    안전한 것으로 보고된다.
    """
    lcov = _write(tmp_path / "lcov.info",
                  "SF:src/a.js\nDA:1,3\nDA:2,0\nDA:3,1\nend_of_record\n")
    loaded = code_gate._load_lcov(tmp_path, lcov)
    entry = loaded["src/a.js"]
    assert entry.kind == "lcov"
    assert entry.executed == frozenset({1, 3})
    assert entry.missing == frozenset({2})
    assert entry.percent == pytest.approx(200.0 / 3)


def test_lcov_ignores_a_record_that_never_ends(tmp_path):
    """`end_of_record` 가 없는 구획은 채택하지 않는다.

    도구가 도중에 죽으면 마지막 구획이 잘린 채 남는다. 그 반쪽을 그대로 쓰면
    실제보다 적은 실행 줄로 커버리지가 낮게 잡혀 없는 문제를 만들어낸다.
    """
    lcov = _write(tmp_path / "lcov.info",
                  "SF:src/a.js\nDA:1,1\nend_of_record\nSF:src/b.js\nDA:1,1\n")
    loaded = code_gate._load_lcov(tmp_path, lcov)
    assert set(loaded) == {"src/a.js"}


def test_lcov_skips_a_malformed_da_line_without_losing_the_record(tmp_path):
    """숫자가 아닌 DA 줄 하나 때문에 파일 전체를 잃으면 안 된다."""
    lcov = _write(tmp_path / "lcov.info",
                  "SF:src/a.js\nDA:x,y\nDA:2,1\nend_of_record\n")
    assert code_gate._load_lcov(tmp_path, lcov)["src/a.js"].executed == frozenset({2})


def test_istanbul_percent_counts_statements_that_ran(tmp_path):
    """istanbul 의 `s` 는 구문별 실행 횟수다 — 0 이 아닌 것만 실행으로 센다."""
    report = _write(tmp_path / "cov.json", json.dumps({
        "src/a.js": {"s": {"0": 1, "1": 0, "2": 5, "3": 0}},
    }))
    entry = code_gate._load_istanbul(tmp_path, report)["src/a.js"]
    assert entry.kind == "istanbul"
    assert entry.percent == 50.0
    assert entry.istanbul is not None      # 경로 C(범위 겹침)가 원본 항목을 다시 본다


def test_istanbul_empty_statement_map_has_no_percent(tmp_path):
    """구문이 하나도 없으면 비율은 None 이다.

    0 을 주면 인터페이스 정의처럼 잴 것이 없는 파일이 '완전 미커버' 로 보고돼,
    고칠 수 없는 발견이 매 회차 쌓인다.
    """
    report = _write(tmp_path / "cov.json", json.dumps({"src/a.d.ts": {"s": {}}}))
    assert code_gate._load_istanbul(tmp_path, report)["src/a.d.ts"].percent is None


def test_istanbul_non_dict_entries_are_dropped(tmp_path):
    """항목이 사전이 아니면 버린다 — 리포트 형식이 바뀌어도 회차가 죽지 않는다."""
    report = _write(tmp_path / "cov.json", json.dumps({"a.js": "깨진 값", "b.js": {"s": {"0": 1}}}))
    assert set(code_gate._load_istanbul(tmp_path, report)) == {"b.js"}


def test_js_coverage_merges_both_formats_and_skips_absent_files(tmp_path):
    """lcov 와 istanbul 을 모두 모으고, 없는 파일은 조용히 건너뛴다.

    러너가 두 형식을 동시에 낼 수 있어 한쪽만 읽으면 절반이 사라진다. 반대로
    경로만 등록되고 파일이 안 생긴 경우(러너 실패)에 예외를 던지면 C2 가 통째로
    오류가 된다.
    """
    ctx = _ctx(tmp_path, files=("src/a.js",))
    ctx.js_lcov_files = [_write(tmp_path / "lcov.info", "SF:src/a.js\nDA:1,1\nend_of_record\n"),
                         tmp_path / "없는파일.info"]
    ctx.js_istanbul_files = [_write(tmp_path / "cov.json", json.dumps({"src/b.js": {"s": {"0": 1}}})),
                             tmp_path / "없는파일.json"]
    collected, problems = {}, []
    code_gate._collect_js_coverage(ctx, collected, problems)
    assert set(collected) == {"src/a.js", "src/b.js"}
    assert problems == []


def test_js_coverage_without_any_runner_output_records_the_reason(tmp_path):
    """낼 파일이 하나도 없으면 그 사실을 사유로 남긴다 (R4)."""
    collected, problems = {}, []
    code_gate._collect_js_coverage(_ctx(tmp_path, files=("src/a.js",)), collected, problems)
    assert problems and "러너가 없습니다" in problems[0][0]


# --- C2 요약 (check_coverage) ---------------------------------------------

def test_coverage_check_says_how_many_changed_files_had_no_data(tmp_path):
    """데이터 없는 변경 파일 수를 요약에 적어야 한다 (R4).

    적지 않으면 잰 파일만 나열된 줄이 '전부 쟀다' 로 읽힌다 — 새로 만든 파일이
    커버리지 리포트에 안 들어간 상황이 정확히 이 모양이다.
    """
    ctx = _ctx(tmp_path, files=("a.py", "b.py"))
    ctx.coverage_data_file = _write(tmp_path / "cov.data", "x")
    ctx.tools["coverage"] = {"available": True, "path": "", "install_hint": ""}
    ctx.coverage_map = {}

    def fake_load(_ctx):
        return {"a.py": _cov(percent=75.0)}
    monkey = pytest.MonkeyPatch()
    monkey.setattr(code_gate, "_load_python_coverage", fake_load)
    try:
        outcome = check_coverage(ctx)
    finally:
        monkey.undo()
    assert outcome["status"] == "ok"
    assert "a.py 75%" in outcome["human_reason"]
    assert "데이터 없는 변경 파일 1개" in outcome["human_reason"]


def test_coverage_check_without_any_data_is_skipped_with_the_first_reason(tmp_path):
    """한 건도 못 모으면 건너뜀이고, 사유는 먼저 걸린 문제를 쓴다.

    ok 로 내면 커버리지를 한 줄도 못 잰 회차가 통과로 보이고, 그 위에서 도는
    C4 의 CRAP 이 전부 '데이터 없음' 이 된 이유가 리포트에서 사라진다.
    """
    outcome = check_coverage(_ctx(tmp_path, files=("a.py",)))
    assert outcome["status"] == "skipped"
    assert "coverage 가 설치돼 있지 않습니다." in outcome["human_reason"]
    assert outcome["install_hint"]


# --- C5 중복 (check_duplication / _duplicate_finding) ---------------------

def test_duplication_without_the_tool_is_skipped_with_the_install_hint(tmp_path):
    outcome = check_duplication(_ctx(tmp_path, files=("a.py",)))
    assert outcome["status"] == "skipped"
    assert outcome["install_hint"] == "npm i -D jscpd"


def test_duplication_without_changed_files_is_skipped_not_ok(tmp_path):
    """검사할 변경 파일이 0개면 건너뜀이다 — ok 로 흘리면 '중복 없음' 이라는 결론이 된다 (R4).

    형제 항목들은 이 분기를 `..._is_skipped_not_ok` 로 정확히 못 박아 두는데 여기만
    비어 있었다. 실측으로 확인했다: 이 분기를 ok 로 바꿔도 스위트 전체가 초록이었다.
    """
    outcome = check_duplication(_ctx(tmp_path, files=()))
    assert outcome["status"] == "skipped"
    assert outcome["reason"] == "no changed files"


def test_duplication_missing_report_is_an_error_not_a_pass(tmp_path, monkeypatch):
    """jscpd 를 불렀는데 리포트가 없으면 오류다 (R4).

    ok 로 흘리면 도구가 죽은 회차가 '중복 없음' 이라는 가장 깨끗한 결과를 낸다.
    """
    ctx = _ctx(tmp_path, files=("a.py",))
    ctx.tools["jscpd"] = {"available": True, "path": "jscpd", "install_hint": ""}
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _FakeProc())
    outcome = check_duplication(ctx)
    assert outcome["status"] == "error"
    assert outcome["reason"] == "jscpd report missing"


def test_duplication_records_that_only_changed_files_were_compared(tmp_path, monkeypatch):
    """변경 파일 안에서만 비교했다는 한계를 참고란에 남겨야 한다 (R3+R4).

    이 문장이 없으면 '중복 없음' 이 저장소 전체에 대한 결론으로 읽힌다.
    """
    ctx = _ctx(tmp_path, files=("a.py", "b.py"))
    ctx.tools["jscpd"] = {"available": True, "path": "jscpd", "install_hint": ""}
    dup = {"lines": 12, "tokens": 80,
           "firstFile": {"name": "a.py", "start": 1, "end": 12},
           "secondFile": {"name": "b.py", "start": 30, "end": 41}}

    def run(cmd, *, cwd, timeout):
        _write(ctx.tmpdir / "jscpd" / "jscpd-report.json",
               json.dumps({"duplicates": [dup, "사전이 아닌 값"]}))
        return _FakeProc()
    monkeypatch.setattr(code_gate, "_run", run)

    outcome = check_duplication(ctx)
    assert outcome["status"] == "findings"
    assert len(outcome["findings"]) == 1
    assert outcome["findings"][0]["first_file"] == "a.py"
    assert outcome["findings"][0]["second_start"] == 30
    assert any("변경된 파일 2개 안에서만" in note for note in ctx.notes)


def test_duplicate_finding_keeps_both_sides_of_the_pair():
    """중복은 두 자리를 다 적어야 뜻이 있다 — 한쪽만 있으면 어디와 겹치는지 모른다."""
    finding = code_gate._duplicate_finding(
        {"lines": 9, "tokens": 60,
         "firstFile": {"name": "a.py", "start": 1, "end": 9},
         "secondFile": {"name": "b.py", "start": 4, "end": 12}})
    assert finding["first_file"] == "a.py" and finding["first_end"] == 9
    assert finding["second_file"] == "b.py" and finding["second_start"] == 4
    # 두 칸을 맞바꿔도 아무 테스트가 안 깨지던 자리다 (실측). 값이 서로 달라야 잡힌다.
    assert finding["lines"] == 9 and finding["tokens"] == 60


def test_duplicate_finding_survives_a_half_empty_entry():
    """한쪽 파일 정보가 비어도 터지지 않고 None 으로 남는다."""
    finding = code_gate._duplicate_finding({"lines": 9})
    assert finding["first_file"] is None and finding["second_file"] is None


# --- 자바스크립트 러너 탐지 (_detect_js_runner) ---------------------------

def test_js_runner_prefers_vitest_over_jest(tmp_path):
    """둘 다 선언돼 있으면 vitest 가 이긴다 — 판정이 흔들리면 회차마다 러너가 바뀐다."""
    _write(tmp_path / "package.json",
           json.dumps({"devDependencies": {"vitest": "1", "jest": "29"}}))
    assert code_gate._detect_js_runner(tmp_path) == "vitest"


@pytest.mark.parametrize("name", ["vitest.config.js", "vitest.config.ts", "vitest.config.mjs"])
def test_js_runner_finds_vitest_by_config_file_alone(tmp_path, name):
    """설정 파일만 있고 package.json 에 없는 배치가 흔하다 (모노레포 워크스페이스)."""
    _write(tmp_path / name, "export default {}\n")
    assert code_gate._detect_js_runner(tmp_path) == "vitest"


def test_js_runner_reads_the_jest_key_inside_package_json(tmp_path):
    """jest 는 설정을 package.json 안에 두는 관례가 있다."""
    _write(tmp_path / "package.json", json.dumps({"jest": {"testEnvironment": "node"}}))
    assert code_gate._detect_js_runner(tmp_path) == "jest"


def test_js_runner_falls_back_to_node_only_when_node_exists(tmp_path, monkeypatch):
    """아무 선언도 없으면 node 내장 러너로 내려가되, node 가 없으면 None 이다.

    None 을 못 내면 C1 이 존재하지 않는 러너를 실행하려다 오류가 되고, 그
    오류가 '러너 없음' 이라는 진짜 사유를 가린다.
    """
    monkeypatch.setattr(code_gate.shutil, "which", lambda name: "/usr/bin/node")
    assert code_gate._detect_js_runner(tmp_path) == "node"
    monkeypatch.setattr(code_gate.shutil, "which", lambda name: None)
    assert code_gate._detect_js_runner(tmp_path) is None


def test_js_runner_ignores_a_broken_package_json(tmp_path, monkeypatch):
    """package.json 이 깨져도 탐지가 죽지 않는다."""
    _write(tmp_path / "package.json", "{ 이건 JSON 이 아니다")
    monkeypatch.setattr(code_gate.shutil, "which", lambda name: None)
    assert code_gate._detect_js_runner(tmp_path) is None


# --- 검사 전 참고란 (_prelude_notes) --------------------------------------

def test_prelude_notes_report_what_was_taken_out_before_any_check_ran(tmp_path):
    """기준 문제·exclude·의존성 프루닝은 검사 전에 이미 정해진 사실이라 먼저 남긴다 (R4).

    세 가지 모두 '변경 파일 수' 를 줄인다. 줄어든 이유가 리포트에 없으면 파일이
    적게 잡힌 회차가 그냥 작은 변경으로 보인다.
    """
    ctx = _ctx(tmp_path, files=("a.py",))
    change = ChangeSet(base="x", base_reason="", files=("a.py",), excluded=("vendor/v.py",),
                       lines={"a.py": None}, pruned=("node_modules/m.js", "node_modules/n.js"),
                       base_problem="기준 x 를 해석하지 못했습니다.")
    code_gate._prelude_notes(ctx, change)
    assert ctx.notes[0] == "기준 x 를 해석하지 못했습니다."
    assert any("파일 1개를 검사에서 뺐습니다" in n for n in ctx.notes)
    assert any("파일 2개를 검사에서 뺐습니다" in n for n in ctx.notes)


def test_prelude_notes_stay_silent_when_nothing_was_taken_out(tmp_path):
    """뺀 것이 없으면 아무 문장도 넣지 않는다 — 늘 뜨는 문구는 읽히지 않는다."""
    ctx = _ctx(tmp_path, files=("a.py",))
    code_gate._prelude_notes(ctx, _changeset(("a.py",)))
    assert ctx.notes == []


# ---------------------------------------------------------------------------
# 18 — 간접 실행만 되던 함수들 (이름이 테스트에 한 번도 안 나오던 것)
#
# 앞 절과 달리 이쪽은 커버리지가 0 이 아니었다. `run_checks` / `render_human` 을
# 부르는 다른 테스트가 지나가며 밟았을 뿐, 이 함수가 무엇을 보장하는지 확인한
# 문장은 없었다. 밟히기만 한 줄은 뮤테이션이 그대로 살아남는다.
# ---------------------------------------------------------------------------

def _rules(tmp_path, payload):
    return _write(tmp_path / ".code-gate-layers.json",
                  payload if isinstance(payload, str) else json.dumps(payload))


def test_layer_rules_unreadable_json_is_an_error_not_a_skip(tmp_path):
    """규칙 파일이 깨져 있으면 오류다 — 건너뜀으로 흘리면 안 된다 (R4).

    건너뜀은 '규칙이 없다' 는 뜻이고 오류는 '규칙이 있는데 못 읽었다' 는 뜻이다.
    앞으로 읽으면 규칙 파일을 잘못 편집한 회차가 정상적인 무규칙 저장소와
    구별되지 않아, 의존 방향 검사가 꺼진 줄 모르고 계속 돈다.
    """
    _, _, failure = code_gate._load_layer_rules(_rules(tmp_path, "{ 이건 JSON 이 아니다"))
    assert failure["status"] == "error"
    assert "읽지 못했습니다" in failure["human_reason"]


def test_layer_rules_that_are_not_an_object_are_an_error(tmp_path):
    """최상위가 배열이면 오류다. layers/forbidden 을 꺼낼 자리가 없다."""
    _, _, failure = code_gate._load_layer_rules(_rules(tmp_path, ["core", "ui"]))
    assert failure["status"] == "error"
    assert failure["reason"] == "layers rules not an object"


@pytest.mark.parametrize("payload", [
    {"layers": {"core": ["core/**"]}},                       # forbidden 없음
    {"forbidden": [{"from": "core", "to": "ui"}]},           # layers 없음
    {"layers": {"core": "core/**"}, "forbidden": [{}]},      # layers 값이 목록이 아님
    {"layers": {"core": ["core/**"]}, "forbidden": ["문자열"]},  # 규칙이 사전이 아님
])
def test_layer_rules_half_written_are_skipped_not_passed(tmp_path, payload):
    """한쪽만 적힌 규칙 파일은 건너뜀이다 — 통과로 보이면 안 된다 (R4).

    layers 만 있고 forbidden 이 없으면 금지할 방향이 하나도 없어 어떤 코드를
    넣어도 '위반 없음' 이 나온다. 그것을 ok 로 내면 검사가 꺼진 상태가 가장
    깨끗한 결과로 표시된다.
    """
    layers, forbidden, failure = code_gate._load_layer_rules(_rules(tmp_path, payload))
    assert (layers, forbidden) == (None, None)
    assert failure["status"] == "skipped"
    assert failure["reason"] == "layers rules empty"


def test_layer_rules_read_a_file_with_a_byte_order_mark(tmp_path):
    """윈도우 편집기가 붙이는 BOM 때문에 규칙이 통째로 무시되면 안 된다."""
    path = tmp_path / ".code-gate-layers.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({
        "layers": {"core": ["core/**"], "ui": ["ui/**"]},
        "forbidden": [{"from": "core", "to": "ui"}],
    }).encode("utf-8"))
    layers, forbidden, failure = code_gate._load_layer_rules(path)
    assert failure is None
    assert set(layers) == {"core", "ui"} and len(forbidden) == 1


def test_violations_ignore_imports_that_stay_inside_one_layer(tmp_path):
    """같은 레이어 안의 import 는 위반이 아니다.

    레이어 비교를 빼면 core 안의 정상 import 가 전부 위반으로 잡혀 리포트가
    거짓 발견으로 뒤덮이고, 진짜 위반이 그 안에 묻힌다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "a.py", "VALUE = 1\n")
    _write(tmp_path / "core" / "b.py", "from core.a import VALUE\n")
    layers = {"core": ["core/**"], "ui": ["ui/**"]}
    forbidden = [{"from": "core", "to": "ui", "reason": "r"}]
    found, parse_failed = code_gate._violations_for_file(tmp_path, "core/b.py", layers, forbidden)
    assert found == [] and parse_failed is False


def test_violations_are_empty_for_a_file_outside_every_layer(tmp_path):
    """레이어에 안 속한 파일은 아예 보지 않는다 — 규칙이 없으니 판정할 것도 없다."""
    _layered_repo(tmp_path)
    _write(tmp_path / "tools" / "x.py", "from ui.view import VALUE\n")
    found, parse_failed = code_gate._violations_for_file(
        tmp_path, "tools/x.py", {"core": ["core/**"], "ui": ["ui/**"]},
        [{"from": "core", "to": "ui"}])
    assert found == [] and parse_failed is False


def test_violations_name_both_layers_and_the_line_of_the_offending_import(tmp_path):
    """위반이 **실제로 잡히는** 자리를 직접 확인한다.

    이 함수의 확인문이 전부 `found == []` 이면 세 가드(레이어 밖 조기 반환 / 같은 레이어
    건너뛰기 / 규칙의 방향 비교)가 서로를 가린다 — 어느 하나를 지워도 세 시나리오 모두
    여전히 빈 목록을 낸다. 실측으로 확인했다: 세 가드를 하나씩 지워도 스위트 전체가
    초록이었다. 양성 하나가 그 가림을 걷어낸다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "svc.py", "from ui.view import VALUE\n")
    layers = {"core": ["core/**"], "ui": ["ui/**"]}
    forbidden = [{"from": "core", "to": "ui", "reason": "core 는 ui 를 몰라야 합니다"}]
    found, parse_failed = code_gate._violations_for_file(
        tmp_path, "core/svc.py", layers, forbidden)
    assert parse_failed is False
    assert len(found) == 1
    assert found[0]["from_file"] == "core/svc.py" and found[0]["to_file"] == "ui/view.py"
    assert found[0]["from_layer"] == "core" and found[0]["to_layer"] == "ui"
    assert found[0]["line"] == 1
    assert found[0]["reason"] == "core 는 ui 를 몰라야 합니다"


def test_violations_need_both_ends_of_the_rule_to_match(tmp_path):
    """금지 규칙은 출발과 도착을 **둘 다** 봐야 한다.

    한쪽만 보면 `core→ui` 하나만 적어 둔 저장소에서 core 가 어디로 import 하든, 또는
    누가 ui 로 import 하든 전부 위반이 된다. 실측: `to` 비교를 통째로 지워도 `from`
    비교를 통째로 지워도 스위트 전체가 초록이었다 — 규칙이 하나뿐이면 남은 한쪽이 늘
    맞아 결과가 같아지기 때문이다. 반쪽만 맞는 규칙을 둬야 그 가림이 걷힌다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "svc.py", "from ui.view import VALUE\n")
    layers = {"core": ["core/**"], "ui": ["ui/**"], "db": ["db/**"]}
    # 출발만 맞는 규칙 — 도착이 다르므로 위반이 아니다.
    assert code_gate._violations_for_file(
        tmp_path, "core/svc.py", layers, [{"from": "core", "to": "db"}])[0] == []
    # 도착만 맞는 규칙 — 출발이 다르므로 위반이 아니다.
    assert code_gate._violations_for_file(
        tmp_path, "core/svc.py", layers, [{"from": "db", "to": "ui"}])[0] == []


def test_a_file_outside_every_layer_is_not_even_parsed(tmp_path):
    """레이어에 안 속한 파일은 열지도 않는다 — 규칙이 없으니 볼 이유가 없다.

    조기 반환을 지우면 그 파일이 파싱 대상이 되고, 문법이 깨진 파일이 "파싱하지 못해
    건너뜀" 참고에 실린다 — 검사 범위 밖의 파일이 사용자 시야에 잡음으로 올라온다.
    실측: 결과 목록만 보는 확인문으로는 이 차이가 안 잡혔다 (조기 반환을 지워도 어느
    쪽이든 빈 목록이 나온다). 파싱 여부 칸이 그 차이를 드러낸다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "tools" / "x.py", "def broken(:\n")
    found, parse_failed = code_gate._violations_for_file(
        tmp_path, "tools/x.py", {"core": ["core/**"], "ui": ["ui/**"]},
        [{"from": "core", "to": "ui"}])
    assert found == [] and parse_failed is False


def test_violations_skip_same_layer_imports_even_when_a_rule_names_that_layer_twice(tmp_path):
    """레이어 안쪽 import 는 `core→core` 규칙이 적혀 있어도 위반이 아니다.

    앞의 "같은 레이어" 확인문은 금지 규칙이 `core→ui` 라, 같은 레이어 건너뛰기를 지워도
    짝지을 규칙이 없어 여전히 빈 목록이 나온다 (실측: 그 가드를 지워도 통과했다).
    규칙 쪽을 `core→core` 로 두어야 그 가드 하나만 사라져도 결과가 달라진다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "a.py", "VALUE = 1\n")
    _write(tmp_path / "core" / "b.py", "from core.a import VALUE\n")
    layers = {"core": ["core/**"], "ui": ["ui/**"]}
    forbidden = [{"from": "core", "to": "core", "reason": "있을 수 없는 규칙"}]
    found, parse_failed = code_gate._violations_for_file(
        tmp_path, "core/b.py", layers, forbidden)
    assert found == [] and parse_failed is False


def test_violations_only_fire_for_the_declared_direction(tmp_path):
    """금지는 방향을 가진다 — core→ui 를 금지해도 ui→core 는 정상이다.

    방향 비교가 무너지면 의도한 의존(상위가 하위를 쓰는 것)까지 위반이 돼
    규칙 자체를 못 쓰게 된다.
    """
    _layered_repo(tmp_path)
    _write(tmp_path / "core" / "svc.py", "VALUE = 1\n")
    _write(tmp_path / "ui" / "page.py", "from core.svc import VALUE\n")
    layers = {"core": ["core/**"], "ui": ["ui/**"]}
    forbidden = [{"from": "core", "to": "ui", "reason": "r"}]
    assert code_gate._violations_for_file(tmp_path, "ui/page.py", layers, forbidden)[0] == []


# --- 테스트 경로 탐지 (_configured_testpaths / detect_pytest_paths) --------

@pytest.mark.parametrize("name, body", [
    ("pyproject.toml", 'testpaths = ["tests"]\n'),
    ("pytest.ini", "testpaths = tests\n"),
    ("tox.ini", "testpaths = tests\n"),
    ("setup.cfg", "testpaths = tests\n"),
])
def test_configured_testpaths_win_over_directory_scanning(tmp_path, name, body):
    """설정 파일의 testpaths 가 있으면 그것이 우선이다.

    프로젝트가 일부러 좁혀 둔 범위를 게이트가 무시하고 전체를 훑으면 C1 시간이
    통째로 늘어난다 (R1). 반대로 설정에 없는 디렉토리를 돌려 남의 테스트까지
    실패로 집계하는 문제도 생긴다.
    """
    _write(tmp_path / name, body)
    _write(tmp_path / "tests" / "test_a.py", "def test_x():\n    assert True\n")
    _write(tmp_path / "extra" / "test_b.py", "def test_y():\n    assert True\n")
    assert code_gate._configured_testpaths(tmp_path) == ["tests"]
    assert detect_pytest_paths(tmp_path) == ["tests"]


def test_configured_testpaths_drop_entries_that_do_not_exist(tmp_path):
    """설정에 적힌 경로가 실제로 없으면 채택하지 않는다.

    없는 경로를 그대로 pytest 에 넘기면 종료 코드 4 로 죽고, 그 실패가 '테스트
    실패' 로 보고돼 원인(설정이 낡음)이 리포트에서 사라진다.
    """
    _write(tmp_path / "pytest.ini", "testpaths = 없는폴더\n")
    assert code_gate._configured_testpaths(tmp_path) == []


def test_detect_pytest_paths_skips_a_test_directory_without_test_files(tmp_path):
    """이름만 tests 인 빈 디렉토리는 넘기지 않는다 — pytest 가 수집 0건으로 죽는다."""
    (tmp_path / "tests").mkdir()
    _write(tmp_path / "tests" / "helper.py", "X = 1\n")
    _write(tmp_path / "pkg" / "test" / "thing_test.py", "def test_z():\n    assert True\n")
    assert detect_pytest_paths(tmp_path) == ["pkg/test"]


def test_detect_pytest_paths_returns_sorted_paths(tmp_path):
    """순서가 흔들리면 같은 저장소에서 회차마다 다른 명령이 나가, 시간 비교가 무의미해진다."""
    for name in ("z_pkg", "a_pkg"):
        _write(tmp_path / name / "tests" / "test_x.py", "def test_x():\n    assert True\n")
    assert detect_pytest_paths(tmp_path) == ["a_pkg/tests", "z_pkg/tests"]


# --- 머리글 렌더링 (_render_header) ---------------------------------------

def _header_payload(**over):
    payload = {"total_seconds": 2.0, "base": "main", "changed_files": ["a.py"],
               "excluded_files": [], "pruned_files": [],
               "checks": [{"seconds": 1.5}], "error": None, "base_problem": None}
    payload.update(over)
    return payload


def test_header_splits_preparation_time_out_of_the_item_total():
    """항목 합과 준비 구간을 따로 보여야 한다 (R1).

    전체 시간만 적으면 어디서 느려졌는지 알 수 없다. 실제로 도구 탐지와 diff
    수집이 항목 밖에서 시간을 쓴다.
    """
    lines = code_gate._render_header(_header_payload())
    assert "전체 2.00초 (준비 0.50초 + 항목 1.50초)" in lines[-2]


def test_header_never_shows_a_negative_preparation_time():
    """항목 합이 전체보다 크게 잰 회차에서도 음수를 적지 않는다.

    항목은 각자 재고 전체는 따로 재기 때문에 반올림으로 뒤집힐 수 있다.
    '준비 -0.01초' 는 잰 값이 틀렸다는 인상만 주고 읽는 사람을 멈춰 세운다.
    """
    lines = code_gate._render_header(_header_payload(total_seconds=1.0, checks=[{"seconds": 9.0}]))
    assert "준비 0.00초" in lines[-2]
    assert "-" not in lines[-2].split("전체")[1]


def test_header_counts_excluded_and_pruned_files_together():
    """제외 수는 exclude 설정과 의존성 프루닝을 합한 값이다.

    한쪽만 세면 '변경 파일 1개' 옆의 제외 수가 실제로 뺀 양보다 적게 보여,
    무엇이 빠졌는지 추적할 단서가 사라진다 (R4).
    """
    lines = code_gate._render_header(
        _header_payload(excluded_files=["v/a.py"], pruned_files=["n/b.js", "n/c.js"]))
    assert "(제외 3개)" in lines[-2]


def test_header_surfaces_the_internal_error_and_the_base_problem():
    """게이트 자체 오류와 기준 문제는 머리글 맨 위에 있어야 한다 (R4).

    두 경우 모두 아래 표가 통째로 비거나 건너뜀으로 채워진다. 사유가 표 밑에
    묻히면 그 회차가 그냥 '검사할 게 없는 회차' 로 읽힌다.
    """
    lines = code_gate._render_header(
        _header_payload(error="ValueError: 깨짐", base_problem="기준 x 를 못 찾았습니다."))
    assert "게이트 내부 오류: ValueError: 깨짐" in lines[1]
    assert "주의: 기준 x 를 못 찾았습니다." in lines[2]


def test_header_says_base_is_absent_instead_of_printing_none():
    """기준을 못 정한 회차에 'None' 을 적지 않는다 — 사용자가 읽는 줄이다."""
    lines = code_gate._render_header(_header_payload(base=None))
    assert "기준: (없음)" in lines[-2]
