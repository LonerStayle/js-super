"""자바 / 고 / C# / 러스트 어댑터 단위 테스트 (1d).

자바(pitest 1.22.0 + Gradle), 러스트(cargo-mutants 27.1.0 + cargo 1.98.0), 고
(gremlins v0.6.0 + go 1.27.0)는 실물로 돌려 본 어댑터이고, C# 은 도구가 이 기계에 없어
**한 회차도 돌려 보지 못한** 어댑터다. 그래서 네 어댑터의 검증 무게가 다르다.

  - 네 어댑터 공통으로 검증하는 것: 대상 고르기, 리포트 → 기록 변환, 어휘 변환,
    선행 조건(설정 값·도구 부재·프로젝트 형태), 명령 조립, 리포트 없음·중단 처리.
    전부 서브프로세스 없이 도는 순수 함수이거나, `gate._run` 을 바꿔치기한 경로다.
  - **검증되지 않는 것**: C# 이 실제로 내는 리포트의 내용. 그 표본은 Stryker.NET 소스에서
    읽은 자료 구조를 옮긴 것이지 실행 산출물이 아니다. 도구를 깔 수 있는 기계에서 한 번은
    실물로 맞대 봐야 한다.
  - 러스트와 고 표본은 다르다. 러스트 묶음의 리포트 조각은 실제로 돌린
    `mutants.out/outcomes.json` 에서, 고 묶음의 `_GO_REAL_*` 표본은 실제로 돌린
    `gremlins.json` 에서 칸 이름과 값을 그대로 옮긴 것이다.
"""

import json
import types
from pathlib import Path

import pytest

from scripts import code_gate
from scripts.mutation import csharp as mutation_csharp
from scripts.mutation import go as mutation_go
from scripts.mutation import java as mutation_java
from scripts.mutation import rust as mutation_rust


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    """캐시를 tmp 로 격리한다 — 이 묶음이 사용자 캐시를 읽거나 쓰지 않게."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("cache")))


def _ctx(tmp_path, tools=None, base="main", files=(), config=None):
    """어댑터가 읽는 칸만 채운 최소 맥락."""
    return types.SimpleNamespace(
        repo_root=tmp_path,
        tmpdir=tmp_path / "tmp",
        config=config if config is not None else code_gate.load_config(tmp_path / "없는설정.json"),
        tools=tools if tools is not None else {},
        change=types.SimpleNamespace(base=base, files=tuple(files)),
        notes=[],
        mutation_deadline=None,
    )


def _tool_present(name, path="/bin/도구"):
    return {name: {"available": True, "path": path, "install_hint": None}}


def _proc(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# 자바 — 대상 고르기
# ---------------------------------------------------------------------------

def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("rel, expected", [
    ("src/test/java/p/A.java", True),
    ("src/testFixtures/java/p/A.java", True),
    ("src/main/java/p/ATest.java", True),
    ("src/main/java/p/ATests.java", True),
    ("src/main/java/p/AIT.java", True),
    ("src/main/java/p/A.java", False),
    ("src/main/java/p/Latest.java", False),
])
def test_java_test_files_are_recognised(rel, expected):
    """테스트 파일은 자리와 이름 둘 다로 가린다. `Latest` 처럼 끝이 겹치는 이름은 대상이다."""
    assert mutation_java._java_is_test(rel) is expected


def test_java_targets_map_paths_to_class_names(tmp_path):
    """대상은 `패키지.클래스` 로 옮긴다. 테스트·선언 전용·없는 파일은 뺀다."""
    _write(tmp_path / "src/main/java/p/A.java", "package p;\nclass A {}\n")
    _write(tmp_path / "src/main/java/B.java", "class B {}\n")            # 기본 패키지
    _write(tmp_path / "src/main/java/p/package-info.java", "package p;\n")
    _write(tmp_path / "src/test/java/p/ATest.java", "package p;\n")
    targets, dropped = mutation_java._java_targets(tmp_path, [
        "src/main/java/p/A.java", "src/main/java/B.java",
        "src/main/java/p/package-info.java", "src/test/java/p/ATest.java",
        "src/main/java/p/사라진.java",
    ])
    assert targets == (("src/main/java/p/A.java", ("p.A",)), ("src/main/java/B.java", ("B",)))
    assert set(dropped) == {"src/main/java/p/package-info.java", "src/test/java/p/ATest.java",
                            "src/main/java/p/사라진.java"}
    assert mutation_java._java_class_index(targets)["p.A"] == "src/main/java/p/A.java"


def test_java_targets_take_every_top_level_type_in_the_file(tmp_path):
    """파일 이름에서 클래스를 짐작하던 때는 형제 최상위 클래스가 통째로 빠졌다 (확정 1).

    실측: 한 파일에 변이 12개가 있는데 2개만 재고 "통과 100%" 가 나왔다. 그 파일에 기록이
    하나라도 있으면 대조(`_mutation_gaps`)도 "쟀다" 로 분류해 아무도 못 봤다.
    """
    _write(tmp_path / "src/main/java/p/MathX.java",
           "package p;\n"
           "public class MathX {\n"
           "    static class Inner { int f() { return 1; } }\n"
           "}\n"
           "class Helper {}\n"
           "enum Flag { A, B }\n"
           "interface Shape {}\n"
           "record Point(int x, int y) {}\n")
    names = mutation_java._java_class_names(tmp_path, "src/main/java/p/MathX.java")
    assert names == ("p.MathX", "p.Helper", "p.Flag", "p.Shape", "p.Point")


def test_java_top_level_types_ignore_nested_and_literal_braces():
    """중첩·지역 타입은 최상위가 아니다. 문자열·주석 안의 중괄호는 깊이를 흔들면 안 된다."""
    text = ('class A {\n'
            '    // class NotThis {\n'
            '    /* class NorThis { */\n'
            '    String s = "} class Fake {";\n'
            '    char c = \'}\';\n'
            '    void f() { class Local {} }\n'
            '    static class Inner {}\n'
            '}\n'
            'class B {}\n')
    assert mutation_java._java_top_level_types(text) == ("A", "B")


def test_java_text_block_braces_do_not_shift_the_depth():
    """텍스트 블록(`\"\"\"`) 안의 중괄호도 깊이 밖이다."""
    text = 'class A {\n    String s = """\n} class Fake {\n""";\n}\nclass B {}\n'
    assert mutation_java._java_top_level_types(text) == ("A", "B")


def test_java_file_without_any_type_is_dropped(tmp_path):
    """최상위 타입을 하나도 못 찾으면 대상에서 빼고 그 사실이 보고에 남는다 (R4)."""
    _write(tmp_path / "src/main/java/p/Empty.java", "package p;\n// 선언이 없다\n")
    targets, dropped = mutation_java._java_targets(tmp_path, ["src/main/java/p/Empty.java"])
    assert targets == ()
    assert dropped == ("src/main/java/p/Empty.java",)


def test_pit_target_classes_cover_nested_classes(tmp_path):
    """PIT 는 중첩 클래스를 `바깥$안` 이라는 별개 이름으로 본다 (확정 1).

    실측: 대상 `demo.MathX` 만 주면 변이 2개, `demo.MathX$*` 를 더하면 7개.
    """
    targets = (("a.java", ("p.A", "p.B")),)
    assert mutation_java._pit_target_classes(targets) == ["p.A", "p.A$*", "p.B", "p.B$*"]


def test_java_incremental_triggers_only_name_observed_axes():
    """무효화 축은 **좁게** 적는 쪽이 보수적이다 (확정 9).

    이 자리의 뜻은 "무엇이 바뀌면 지난 상태를 버리는가" 이고, 실제보다 넓게 적으면 낡은
    결과가 굳는 것을 못 본다. 통제 실험(같은 history 자리, 매 회차 --rerun-tasks):
    콜드 `Ran 3 tests` / 무변경 `Ran 0` / 로컬 jar 하나 추가 `Ran 0` / 대상 클래스
    바이트코드 변경 `Ran 3`. 의존 라이브러리를 올린 회차가 무변경 회차와 같았으므로
    클래스패스는 무효화 축이 아니다.
    계약 테스트는 이 튜플이 비었는지만 보므로 내용은 여기서 못 박는다.
    """
    triggers = mutation_java.JAVA_ADAPTER.incremental_triggers
    assert "클래스패스" not in triggers
    assert set(triggers) == {"대상 클래스 바이트코드", "테스트 클래스 변경", "pitest 판"}


def test_pit_tail_folds_a_multi_line_failure_into_one_line():
    """실패 원문을 그대로 실으면 한 항목 한 줄이라는 표의 전제가 깨진다 (확정 6)."""
    folded = mutation_java._pit_tail("첫 줄\n  둘째 줄\n\n셋째")
    assert folded == "첫 줄 둘째 줄 셋째"


# ---------------------------------------------------------------------------
# 자바 — 리포트 읽기
# ---------------------------------------------------------------------------

def _pit_xml(*mutations, closed=True):
    body = "<mutations>" + "".join(mutations)
    return body + "</mutations>" if closed else body


def _pit_mutation(status="SURVIVED", cls="p.A", line=2, killing="", mutator="M"):
    kill = f"<killingTest>{killing}</killingTest>" if killing else "<killingTest/>"
    return (f"<mutation status='{status}'><mutatedClass>{cls}</mutatedClass>"
            f"<mutatedMethod>f</mutatedMethod><lineNumber>{line}</lineNumber>"
            f"<mutator>org.pitest.mutationtest.engine.gregor.mutators.{mutator}</mutator>"
            f"{kill}<description>바꿈</description></mutation>")


def test_pit_record_fills_what_the_tool_gives(tmp_path):
    """줄·변이 종류·죽인 테스트는 도구에서 오고, 열은 비운다 (PIT 는 줄까지만 준다)."""
    xml = _pit_xml(_pit_mutation(status="KILLED", line=2,
                                 killing="[class:p.ATest]/[method:f()]"))
    records = mutation_java._pit_records(xml, {"p.A": "a.java"}, {"a.java": ["첫줄", "  둘째줄  "]})
    assert len(records) == 1
    record = records[0]
    assert record["file"] == "a.java"
    assert record["line"] == 2
    assert record["column"] is None
    assert record["mutator"] == "M"
    assert record["original"] == "둘째줄"
    assert record["status"] == "Killed"
    assert record["tests"] == ["p.ATest.f()"]


def test_pit_survivor_says_the_tool_gave_no_test_list():
    """살아남은 변이의 테스트 목록은 **없음(None)** 이다 — "덮은 테스트가 없다" 와 다르다."""
    records = mutation_java._pit_records(_pit_xml(_pit_mutation()), {"p.A": "a.java"}, {})
    assert records[0]["tests"] is None
    assert records[0]["status"] == "Survived"


def test_pit_nested_class_maps_to_its_outer_file():
    """중첩 클래스(`Outer$Inner`)는 바깥 클래스의 파일로 되돌린다."""
    records = mutation_java._pit_records(_pit_xml(_pit_mutation(cls="p.A$Inner")),
                                         {"p.A": "a.java"}, {})
    assert [r["file"] for r in records] == ["a.java"]


def test_pit_drops_classes_outside_this_round():
    """이번 대상이 아닌 클래스는 세지 않는다 (R3)."""
    records = mutation_java._pit_records(_pit_xml(_pit_mutation(cls="p.Other")),
                                         {"p.A": "a.java"}, {})
    assert records == []


def test_pit_unknown_status_passes_through():
    """표에 없는 상태는 원어 그대로 통과한다 — unknown 경로가 잡아 분모에서 뺀다 (R4)."""
    records = mutation_java._pit_records(_pit_xml(_pit_mutation(status="NON_VIABLE")),
                                         {"p.A": "a.java"}, {})
    assert records[0]["status"] == "NON_VIABLE"


def test_pit_salvage_recovers_a_truncated_report():
    """중단돼 잘린 XML 에서 온전히 닫힌 변이까지는 살린다 (D4)."""
    truncated = _pit_xml(_pit_mutation(line=1), "<mutation status='SUR", closed=False)
    records = mutation_java._pit_records(truncated, {"p.A": "a.java"}, {})
    assert len(records) == 1


@pytest.mark.parametrize("text", ["", "<mutations>", "쓰레기"])
def test_pit_salvage_gives_up_on_hopeless_text(text):
    """되살릴 변이가 하나도 없으면 빈 목록이다 — 예외로 게이트를 죽이지 않는다 (R2)."""
    assert mutation_java._pit_records(text, {"p.A": "a.java"}, {}) == []


def test_pit_reports_from_several_modules_are_merged():
    """모듈마다 나뉜 리포트를 한 점수로 합친다."""
    first = _pit_xml(_pit_mutation(status="KILLED", killing="t"))
    second = _pit_xml(_pit_mutation(status="SURVIVED"), _pit_mutation(status="NO_COVERAGE"))
    summary = mutation_java.parse_pit_reports([first, second], {"p.A": "a.java"}, {})
    assert summary["total"] == 3
    assert summary["counts"] == {"Killed": 1, "Survived": 1, "NoCoverage": 1}
    assert summary["score"] == pytest.approx(33.33)
    assert len(summary["survivors"]) == 2


def test_pit_sources_reads_target_files(tmp_path):
    """원본 자리를 보여 주려면 대상 파일을 직접 읽어야 한다. 못 읽는 파일은 건너뛴다."""
    _write(tmp_path / "a.java", "첫줄\n둘째줄\n")
    sources = mutation_java._pit_sources(tmp_path, (("a.java", "p.A"), ("없음.java", "p.X")))
    assert sources["a.java"][:2] == ["첫줄", "둘째줄"]
    assert "없음.java" not in sources


def test_pit_report_texts_reads_every_module_directory(tmp_path):
    """리포트는 모듈별 디렉토리 아래에 있다. 없으면 빈 목록."""
    assert mutation_java._pit_report_texts(tmp_path / "없는자리") == []
    _write(tmp_path / "report/_/mutations.xml", "첫째")
    _write(tmp_path / "report/_sub/mutations.xml", "둘째")
    assert mutation_java._pit_report_texts(tmp_path / "report") == ["첫째", "둘째"]


# ---------------------------------------------------------------------------
# 자바 — init script
# ---------------------------------------------------------------------------

def test_groovy_quote_escapes_backslash_and_quote():
    assert mutation_java._groovy_quote("a'b\\c") == "'a\\'b\\\\c'"


def test_pit_init_script_pins_the_version_and_neutralises_thresholds(tmp_path):
    """임계값 셋과 `failWhenNoMutations` 를 덮는다 — 안 덮으면 종료 코드가 비-0 이 된다 (R2)."""
    body = mutation_java.pit_init_script(["p.A"], tmp_path / "리포트", tmp_path / "이력")
    assert f"pitestVersion = '{mutation_java.PITEST_VERSION}'" in body
    assert "targetClasses = ['p.A']" in body
    # 대상 목록과 테스트 목록은 서로 다른 자리다 — 좁히면 판정이 통째로 뒤집힌다 (실측).
    assert "targetTests = ['*']" in body
    for line in ("mutationThreshold = 0", "coverageThreshold = 0",
                 "testStrengthThreshold = 0", "failWhenNoMutations = false"):
        assert line in body
    assert "historyInputLocation" in body


def test_pit_init_script_without_history_omits_it(tmp_path):
    """증분 자리를 못 잡으면 그 줄을 아예 넣지 않는다 (전체를 다시 돈다)."""
    body = mutation_java.pit_init_script(["p.A"], tmp_path / "리포트", None)
    assert "historyInputLocation" not in body


def test_java_history_dir_lives_in_the_cache_and_names_the_version(tmp_path):
    """증분 상태는 대상 프로젝트 밖(캐시)에 두고, pitest 판을 이름에 넣는다."""
    notes: list = []
    found = mutation_java.java_history_dir(tmp_path, notes)
    assert found is not None and found.name == f"pit-{mutation_java.PITEST_VERSION}"
    assert notes == []


def test_java_history_dir_reports_when_it_cannot_be_made(tmp_path, monkeypatch):
    """자리를 못 만들면 조용히 넘어가지 않고 사유를 남긴다 (R4)."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(_write(tmp_path / "파일", "x")))
    notes: list = []
    assert mutation_java.java_history_dir(tmp_path, notes) is None
    assert notes and "캐시 디렉토리를 만들지 못해" in notes[0]


# ---------------------------------------------------------------------------
# 자바 — 선행 조건과 실행
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("marker, build_files, reason_part", [
    ("maven", ("pom.xml",), "Maven"),
    ("none", (), "Gradle 빌드 파일"),
])
def test_java_skips_when_the_build_system_is_not_gradle(tmp_path, marker, build_files, reason_part):
    """Gradle 이 아니면 재지 않고 그 사실을 말한다 (조용한 통과 금지, R4)."""
    for name in build_files:
        _write(tmp_path / name, "")
    assert mutation_java._java_build_system(tmp_path) == marker
    ctx = _ctx(tmp_path, tools=_tool_present("gradle"))
    blocked = mutation_java._java_preconditions(ctx)
    assert blocked["status"] == "skipped"
    assert reason_part in blocked["human_reason"]


def test_java_runs_when_a_gradle_file_is_present(tmp_path):
    _write(tmp_path / "settings.gradle.kts", "")
    assert mutation_java._java_build_system(tmp_path) == "gradle"
    assert mutation_java._java_preconditions(_ctx(tmp_path, tools=_tool_present("gradle"))) is None


def test_java_missing_gradle_names_how_to_install(tmp_path):
    """도구가 없으면 건너뛰되 설치 방법을 낸다 (R4)."""
    blocked = mutation_java._java_preconditions(_ctx(tmp_path))
    assert blocked["status"] == "skipped"
    assert blocked["install_hint"] == mutation_java._INSTALL_HINT


def test_java_scope_drops_and_reports(tmp_path):
    """뺀 파일은 사유와 함께 남기고, 남는 것이 없으면 건너뛴다."""
    _write(tmp_path / "src/test/java/p/ATest.java", "package p;\n")
    ctx = _ctx(tmp_path)
    targets, blocked = mutation_java._java_scope(ctx, ["src/test/java/p/ATest.java"])
    assert targets == ()
    assert blocked["status"] == "skipped"
    assert any("뺐습니다" in note for note in ctx.notes)


@pytest.mark.parametrize("detail, marker", [
    ("… no history plugin …", "내장 증분"),
    ("Unsupported class file major version 70", "바이트코드를 읽지 못했"),
    ("1 tests did not pass without mutation", "테스트를 먼저 고치십시오"),
    ("알 수 없는 실패", ""),
])
def test_pit_failure_cause_names_what_it_recognises(detail, marker):
    assert marker in mutation_java._pit_failure_cause(detail)


def test_pit_no_report_separates_zero_mutants_from_failure():
    """변이 0개는 정상(건너뜀)이고 나머지는 오류다 — 종료 코드만으로는 갈리지 않는다."""
    ok = mutation_java._pit_no_report(_proc(0, "No mutations found. …"), 0.5)
    assert ok["status"] == "skipped"
    bad = mutation_java._pit_no_report(_proc(1, "무슨 실패"), 0.5)
    assert bad["status"] == "error"
    assert "무슨 실패" in bad["human_reason"]
    assert mutation_java._pit_no_report(None, 0.5)["status"] == "error"


def _java_project(tmp_path):
    _write(tmp_path / "build.gradle", "")
    _write(tmp_path / "src/main/java/p/A.java", "package p;\nclass A {}\n")
    return _ctx(tmp_path, tools=_tool_present("gradle"), files=("src/main/java/p/A.java",))


def test_java_end_to_end_with_a_stubbed_gradle(tmp_path, monkeypatch):
    """준비 → 실행 → 리포트 읽기까지 한 번에. Gradle 자리에는 가짜를 세운다."""
    def fake_run(cmd, *, cwd, timeout):
        report = Path(cmd[2]).parent / "report" / "_"
        report.mkdir(parents=True, exist_ok=True)
        (report / "mutations.xml").write_text(
            _pit_xml(_pit_mutation(status="KILLED", killing="t"), _pit_mutation()),
            encoding="utf-8")
        assert cmd[3] == "pitest"
        return _proc(0)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _java_project(tmp_path)
    part = mutation_java._check_mutation_java(ctx, ["src/main/java/p/A.java"])
    assert part["language"] == "java" and part["label"] == "자바"
    assert part["summary"]["counts"] == {"Killed": 1, "Survived": 1}
    assert part["outcome"]["status"] == "findings"          # 50% 는 기준 80% 아래
    assert any("init script" in note for note in ctx.notes)


def test_java_reports_when_gradle_produces_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _proc(1, "무슨 실패"))
    ctx = _java_project(tmp_path)
    outcome, summary = mutation_java._run_mutation_java(ctx, ["src/main/java/p/A.java"])
    assert summary is None and outcome["status"] == "error"


def test_java_timeout_keeps_what_it_saw(tmp_path, monkeypatch):
    """예산을 넘겨도 본 만큼은 낸다 (D4)."""
    import subprocess

    def fake_run(cmd, *, cwd, timeout):
        report = Path(cmd[2]).parent / "report" / "_"
        report.mkdir(parents=True, exist_ok=True)
        (report / "mutations.xml").write_text(_pit_xml(_pit_mutation(), closed=False),
                                              encoding="utf-8")
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _java_project(tmp_path)
    outcome, summary = mutation_java._run_mutation_java(ctx, ["src/main/java/p/A.java"])
    assert outcome["status"] == "timeout"
    assert summary["total"] == 1
    assert "예산을 넘겨 중단했습니다" in outcome["human_reason"]


def test_java_changed_files_pick_java_only(tmp_path):
    ctx = _ctx(tmp_path, files=("a.java", "b.py", "c.JAVA"))
    assert mutation_java._mutation_changed_java(ctx) == ["a.java", "c.JAVA"]


# ---------------------------------------------------------------------------
# 고 (gremlins)
#
# 아래 `_GO_REAL_*` 셋은 go 1.27.0 + gremlins v0.6.0 을 실제로 돌려 받은 `gremlins.json`
# 전문이다 (칸 이름·값·항목 순서 그대로). 대상 모듈은 `_GO_REAL_SOURCE` 이고, 세 갈래가
# 다 나오게 일부러 짰다.
#   5행  `return a + b`  테스트가 값을 확인한다        → KILLED
#   10행 `return v > 0`  테스트가 부르지만 확인 안 한다 → LIVED 둘 (경계·부정)
#   15행 `return v * 2`  테스트가 없다                  → NOT COVERED
# ---------------------------------------------------------------------------

_GO_REAL_SOURCE = """package sandbox

// Add 는 두 수를 더한다. 테스트가 결과를 확인한다 — 변이가 잡힌다.
func Add(a, b int) int {
\treturn a + b
}

// IsPositive 는 0 보다 큰지 본다. 테스트가 부르지만 결과를 확인하지 않는다.
func IsPositive(v int) bool {
\treturn v > 0
}

// Double 은 두 배로 만든다. 테스트가 없다.
func Double(v int) int {
\treturn v * 2
}
"""

# `--diff` 없이 모듈 전체를 돌린 회차.
_GO_REAL_REPORT = {
    "go_module": "sandbox",
    "files": [{"file_name": "calc.go", "mutations": [
        {"type": "ARITHMETIC_BASE", "status": "NOT COVERED", "line": 15, "column": 11},
        {"type": "CONDITIONALS_BOUNDARY", "status": "LIVED", "line": 10, "column": 11},
        {"type": "CONDITIONALS_NEGATION", "status": "LIVED", "line": 10, "column": 11},
        {"type": "ARITHMETIC_BASE", "status": "KILLED", "line": 5, "column": 11}]}],
    "test_efficacy": 33.33333333333333, "mutations_coverage": 75,
    "mutants_total": 3, "mutants_killed": 1, "mutants_lived": 2,
    "mutants_not_viable": 0, "mutants_not_covered": 1,
    "elapsed_time": 0.949210625,
    "mutator_statistics": {"arithmetic_base": 2, "conditionals_negation": 1,
                           "conditionals_boundary": 1},
}

# 같은 모듈을 `--diff HEAD` 로 돌린 회차. 바뀐 줄이 문맥과 번갈아 나와 뒤쪽 둘이
# gremlins 의 구간 밖으로 떨어졌고, 남은 하나는 제한시간에 걸렸다.
_GO_REAL_DIFF_REPORT = {
    "go_module": "sandbox",
    "files": [{"file_name": "calc.go", "mutations": [
        {"type": "ARITHMETIC_BASE", "status": "SKIPPED", "line": 15, "column": 11},
        {"type": "CONDITIONALS_BOUNDARY", "status": "SKIPPED", "line": 10, "column": 11},
        {"type": "CONDITIONALS_NEGATION", "status": "SKIPPED", "line": 10, "column": 11},
        {"type": "ARITHMETIC_BASE", "status": "TIMED OUT", "line": 5, "column": 11}]}],
    "test_efficacy": 0, "mutations_coverage": 0,
    "mutants_total": 0, "mutants_killed": 0, "mutants_lived": 0,
    "mutants_not_viable": 0, "mutants_not_covered": 0,
    "elapsed_time": 0.318833666,
    "mutator_statistics": {"arithmetic_base": 2, "conditionals_negation": 1,
                           "conditionals_boundary": 1},
}

# 하위 패키지가 있는 다른 모듈. 이름이 어떤 형태로 실리는지 보려고 따로 돌렸다.
_GO_REAL_SUB_REPORT = {
    "go_module": "subsandbox",
    "files": [
        {"file_name": "root.go", "mutations": [
            {"type": "ARITHMETIC_BASE", "status": "LIVED", "line": 3, "column": 33}]},
        {"file_name": "pkg/util/util.go", "mutations": [
            {"type": "ARITHMETIC_BASE", "status": "KILLED", "line": 3, "column": 33}]}],
    "test_efficacy": 50, "mutations_coverage": 100,
    "mutants_total": 2, "mutants_killed": 1, "mutants_lived": 1,
    "mutants_not_viable": 0, "mutants_not_covered": 0,
    "elapsed_time": 0.722270334,
    "mutator_statistics": {"arithmetic_base": 2},
}


def test_go_real_report_scores_three_kinds_of_mutant(tmp_path):
    """실측 리포트 전문이 게이트 어휘로 정확히 옮겨진다.

    잡힘 1 / 살아남음 2 / 덮은 테스트 없음 1 → 점수 25%. 도구가 낸 `test_efficacy`
    33.33 과 다른 것이 정상이다 — 도구는 NOT COVERED 를 분모에서 빼고 게이트는 넣는다.
    """
    _write(tmp_path / "calc.go", _GO_REAL_SOURCE)
    summary = mutation_go.parse_gremlins_report(_GO_REAL_REPORT, tmp_path, {"calc.go"})
    assert summary["total"] == 4
    assert summary["counts"] == {"Killed": 1, "Survived": 2, "NoCoverage": 1}
    assert summary["score"] == 25.0
    assert summary["unknown"] == ()
    assert [(s["line"], s["status"], s["original"]) for s in summary["survivors"]] == [
        (10, "Survived", "return v > 0"),
        (10, "Survived", "return v > 0"),
        (15, "NoCoverage", "return v * 2"),
    ]
    assert summary["survivors"][0]["mutator"] == "CONDITIONALS_BOUNDARY"
    assert summary["survivors"][0]["column"] == 11


def test_go_real_diff_report_turns_skipped_into_excluded(tmp_path):
    """`--diff` 회차의 SKIPPED 는 '제외됨' 이라 분모에서 빠진다 (실측 리포트 전문).

    변이 4개 중 3개가 빠지고 남은 하나가 TIMED OUT 이라 점수가 100% 로 나온다. 잰 것이
    거의 없는데도 통과처럼 보이는 자리라, 참고에 그 사실이 실려야 한다 (R4).
    """
    _write(tmp_path / "calc.go", _GO_REAL_SOURCE)
    summary = mutation_go.parse_gremlins_report(_GO_REAL_DIFF_REPORT, tmp_path, {"calc.go"})
    assert summary["counts"] == {"Ignored": 3, "Timeout": 1}
    assert summary["score"] == 100.0 and summary["survivors"] == []


def test_go_timeout_note_says_the_score_can_be_inflated(tmp_path):
    """TIMED OUT 이 있으면 제한시간이 어떻게 정해지는지 참고에 적는다."""
    ctx = _ctx(tmp_path)
    mutation_go._go_note_timeouts(ctx, {"counts": {"Ignored": 3, "Timeout": 1}})
    assert any("TIMED OUT" in note and "timeout-coefficient" in note for note in ctx.notes)
    # 없으면 아무것도 남기지 않는다 — 정상 회차에 잡음을 얹지 않는다.
    quiet = _ctx(tmp_path)
    mutation_go._go_note_timeouts(quiet, {"counts": {"Killed": 2}})
    mutation_go._go_note_timeouts(quiet, None)
    assert quiet.notes == []


def test_go_real_report_keeps_the_package_directory(tmp_path):
    """리포트의 이름은 모듈 루트 기준 상대 경로다 — 디렉토리째 그대로 맞는다 (실측)."""
    _write(tmp_path / "root.go", "package subsandbox\n\nfunc Root(v int) int { return v + 1 }\n")
    _write(tmp_path / "pkg/util/util.go", "package util\n\nfunc Util(v int) int { return v * 3 }\n")
    targets = {"root.go", "pkg/util/util.go"}
    summary = mutation_go.parse_gremlins_report(_GO_REAL_SUB_REPORT, tmp_path, targets)
    assert summary["files"] == ["pkg/util/util.go", "root.go"]
    assert summary["score"] == 50.0
    assert summary["survivors"][0]["file"] == "root.go"
    assert mutation_go.unmatched_report_files(_GO_REAL_SUB_REPORT, tmp_path, targets) == []


def test_go_targets_drop_tests_and_generated(tmp_path):
    for name in ("a.go", "a_test.go", "api.pb.go", "x.gen.go"):
        _write(tmp_path / name, "")
    targets, dropped = mutation_go._go_targets(
        tmp_path, ["a.go", "a_test.go", "api.pb.go", "x.gen.go", "사라진.go"])
    assert targets == ("a.go",)
    assert set(dropped) == {"a_test.go", "api.pb.go", "x.gen.go", "사라진.go"}


def test_go_report_path_falls_back_to_a_unique_suffix(tmp_path):
    """도구가 임시 사본의 경로를 실을 수 있어, 접미사가 **하나만** 맞을 때 그것으로 본다."""
    targets = {"pkg/a.go", "pkg/b.go"}
    assert mutation_go._go_report_path(tmp_path, "pkg/a.go", targets) == "pkg/a.go"
    assert mutation_go._go_report_path(tmp_path, "/tmp/gremlins-1/pkg/a.go", targets) == "pkg/a.go"
    # 둘 이상 맞으면 맞추지 않는다 — 잘못 맞추면 다른 파일의 점수가 된다
    assert mutation_go._go_report_path(tmp_path, "/tmp/gremlins-1/a.go",
                                       {"x/a.go", "y/a.go"}) is None
    assert mutation_go._go_report_path(tmp_path, "/tmp/gremlins-1/없음.go", targets) is None


def test_go_record_fills_the_original_line_from_the_file(tmp_path):
    """gremlins 는 원본 텍스트를 안 주지만 줄 번호는 준다 — 파일에서 읽어 채운다 (확정 11).

    비워 두면 살아남은 변이 한 줄이 "원본 자리를 알 수 없음" 으로만 나가 고칠 수가 없다 (R9).
    """
    _write(tmp_path / "a.go", "package p\n\nfunc f(v int) int {\n\treturn v + 1\n}\n")
    report = {"files": [{"file_name": "a.go", "mutations": [
        {"type": "ARITHMETIC_BASE", "status": "LIVED", "line": 4, "column": 9}]}]}
    summary = mutation_go.parse_gremlins_report(report, tmp_path, {"a.go"})
    assert summary["survivors"][0]["original"] == "return v + 1"


def test_go_unmatched_report_files_are_named(tmp_path):
    """리포트 이름을 하나도 못 맞추면 요약이 비어 정상 종료 문장이 나갔다 (확정 12)."""
    _write(tmp_path / "pkg1/a.go", "package p\n")
    _write(tmp_path / "pkg2/a.go", "package p\n")
    report = {"files": [{"file_name": "a.go", "mutations": [
        {"type": "T", "status": "LIVED", "line": 1, "column": 1}]}]}
    targets = {"pkg1/a.go", "pkg2/a.go"}
    assert mutation_go.parse_gremlins_report(report, tmp_path, targets)["total"] == 0
    assert mutation_go.unmatched_report_files(report, tmp_path, targets) == ["a.go"]
    # 맞춘 회차에는 아무 이름도 남기지 않는다.
    assert mutation_go.unmatched_report_files(report, tmp_path, {"pkg1/a.go"}) == []
    # 모양이 어긋난 리포트, 이름 없는 항목, 변이가 빈 항목은 셈에서 빠진다.
    assert mutation_go.unmatched_report_files({"files": "쓰레기"}, tmp_path, targets) == []
    assert mutation_go.unmatched_report_files("쓰레기", tmp_path, targets) == []
    assert mutation_go.unmatched_report_files(
        {"files": [{"mutations": [{"status": "LIVED"}]}, {"file_name": "b.go"}, "쓰레기"]},
        tmp_path, targets) == []


def test_go_record_has_line_and_column_but_no_test_list():
    record = mutation_go._go_record("a.go", {"line": 3, "column": 5, "type": "T",
                                            "status": "LIVED"}, ["첫줄", "둘째줄", "셋째줄"])
    assert (record["line"], record["column"], record["mutator"]) == (3, 5, "T")
    assert record["status"] == "Survived"
    assert record["tests"] is None


def test_go_report_maps_every_documented_status(tmp_path):
    """소스에서 옮긴 일곱 낱말이 모두 게이트 어휘로 간다 (공백이 든 철자 그대로)."""
    mutations = [{"line": i, "column": 1, "type": "T", "status": word}
                 for i, word in enumerate(mutation_go.GREMLINS_STATUS_TO_GATE, start=1)]
    report = {"files": [{"file_name": "a.go", "mutations": mutations}]}
    summary = mutation_go.parse_gremlins_report(report, tmp_path, {"a.go"})
    assert summary["unknown"] == ()
    assert set(summary["counts"]) == set(mutation_go.GREMLINS_STATUS_TO_GATE.values())


def test_go_report_filters_to_this_round(tmp_path):
    report = {"files": [{"file_name": "a.go", "mutations": [{"line": 1, "status": "KILLED"}]},
                        {"file_name": "다른.go", "mutations": [{"line": 1, "status": "LIVED"}]},
                        "쓰레기"]}
    summary = mutation_go.parse_gremlins_report(report, tmp_path, {"a.go"})
    assert summary["total"] == 1 and summary["files"] == ["a.go"]
    assert mutation_go.parse_gremlins_report({"files": "쓰레기"}, tmp_path, set())["total"] == 0


def test_go_preconditions_need_a_module_and_the_tool(tmp_path):
    missing = mutation_go._go_preconditions(_ctx(tmp_path))
    assert missing["status"] == "skipped" and missing["install_hint"] == mutation_go._INSTALL_HINT
    no_module = mutation_go._go_preconditions(_ctx(tmp_path, tools=_tool_present("gremlins")))
    assert "go.mod" in no_module["human_reason"]
    _write(tmp_path / "go.mod", "module x\n")
    assert mutation_go._go_preconditions(_ctx(tmp_path, tools=_tool_present("gremlins"))) is None


def test_go_command_passes_the_base_and_zeroes_thresholds(tmp_path):
    """변경분 한정은 `--diff <기준>`, 임계값은 0 (R2·R3)."""
    cmd, notes = mutation_go._go_command(_ctx(tmp_path, tools=_tool_present("gremlins")),
                                         tmp_path / "out.json", ("a.go",))
    assert cmd[1] == "unleash"
    assert "--diff" in cmd and cmd[cmd.index("--diff") + 1] == "main"
    assert cmd[cmd.index("--threshold-efficacy") + 1] == "0"
    assert cmd[cmd.index("--threshold-mcover") + 1] == "0"
    # `--diff` 를 준 회차에 gremlins 는 **바뀐 줄 범위 안의 변이만** 돌린다 (확정 8).
    # 파일 단위라고 말하면 실제보다 넓게 쟀다고 알리는 셈이다.
    assert any("바뀐 줄 범위 안의 변이만" in note for note in notes)
    assert not any("바뀌지 않은 줄도 함께 변이됩니다" in note for note in notes)
    # 실측으로 확인한 거친 범위 계산과, 그래서 빠지는 몫을 함께 말한다.
    assert any("앞 문맥 다음 줄부터" in note and "제외됨" in note for note in notes)
    # 실물로 검증한 뒤로는 "미검증" 경고를 달지 않는다 — 거짓말이 된다.
    assert not any("검증하지 않았습니다" in note for note in notes)


def test_go_command_without_a_base_runs_everything(tmp_path):
    ctx = _ctx(tmp_path, tools=_tool_present("gremlins"), base=code_gate.EMPTY_TREE)
    cmd, notes = mutation_go._go_command(ctx, tmp_path / "out.json", ("a.go",))
    assert "--diff" not in cmd
    assert any("모듈 전체를 돌렸습니다" in note for note in notes)
    assert any("바뀌지 않은 줄도 함께 변이됩니다" in note for note in notes)


def test_go_end_to_end_with_a_stubbed_tool(tmp_path, monkeypatch):
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "a.go", "package x\n")

    def fake_run(cmd, *, cwd, timeout):
        Path(cmd[cmd.index("--output") + 1]).write_text(json.dumps(
            {"files": [{"file_name": "a.go",
                        "mutations": [{"line": 1, "column": 2, "type": "T", "status": "LIVED"},
                                      {"line": 2, "column": 1, "type": "T", "status": "KILLED"}]}]}),
            encoding="utf-8")
        return _proc(0)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, tools=_tool_present("gremlins"))
    part = mutation_go._check_mutation_go(ctx, ["a.go"])
    assert part["language"] == "go" and part["label"] == "고"
    assert part["summary"]["score"] == 50.0
    assert part["outcome"]["status"] == "findings"


def test_go_scope_note_survives_a_failed_round(tmp_path, monkeypatch):
    """범위 안내가 완주 회차에만 붙던 문제 (확정 5).

    실측: 리포트를 안 쓰는 도구로 돌리면 참고에 안내가 통째로 없었다. 무엇을 어디까지
    재려 했는지가 가장 필요한 순간은 성공했을 때가 아니라 실패했을 때다 — 도구 문제인지
    범위 문제인지 가를 단서가 그것뿐이다 (R4).
    """
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "a.go", "package p\n")
    ctx = _ctx(tmp_path, tools=_tool_present("gremlins"))
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _proc(1, "리포트를 쓰지 않음"))
    outcome, summary = mutation_go._run_mutation_go(ctx, ["a.go"])
    assert outcome["status"] == "error" and summary is None
    assert any("바뀐 줄 범위 안의 변이만" in note for note in ctx.notes)


def test_go_no_report_with_exit_zero_is_not_an_error(tmp_path, monkeypatch):
    """변이가 없으면 리포트 파일 자체가 안 생기고 종료 코드는 0 이다 (실측).

    그것을 오류로 내던 동안, 구조체 선언만 든 파일을 바꾼 멀쩡한 회차가
    "리포트가 나오지 않았습니다 (종료 코드 0)" 로 나갔다. 통과로 내지도 않는다 (R4).
    """
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "a.go", "package p\n")
    monkeypatch.setattr(code_gate, "_run",
                        lambda *a, **k: _proc(0, "No results to report."))
    outcome, summary = mutation_go._run_mutation_go(_ctx(tmp_path, tools=_tool_present("gremlins")),
                                                    ["a.go"])
    assert outcome["status"] == "skipped" and summary is None
    assert "변이가 하나도 만들어지지 않아" in outcome["human_reason"]
    assert outcome["reason"] == "no mutants for changed files"


def test_go_reports_when_nothing_is_written(tmp_path, monkeypatch):
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "a.go", "package x\n")
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _proc(2, "무슨 실패"))
    outcome, summary = mutation_go._run_mutation_go(_ctx(tmp_path, tools=_tool_present("gremlins")),
                                                    ["a.go"])
    assert outcome["status"] == "error" and summary is None
    assert "무슨 실패" in outcome["human_reason"]


def test_go_timeout_says_how_far_it_got(tmp_path):
    outcome = mutation_go._go_timed_out(None, ("a.go",), 1.0, 30)
    assert outcome["status"] == "timeout" and outcome["findings"] == []
    assert "30초 예산" in outcome["human_reason"]


def test_go_scope_and_changed_files(tmp_path):
    _write(tmp_path / "a_test.go", "")
    ctx = _ctx(tmp_path, files=("a.go", "b.py"))
    assert mutation_go._mutation_changed_go(ctx) == ["a.go"]
    targets, blocked = mutation_go._go_scope(ctx, ["a_test.go"])
    assert targets == () and blocked["status"] == "skipped"


# ---------------------------------------------------------------------------
# C# (Stryker.NET)
# ---------------------------------------------------------------------------

def test_csharp_targets_drop_tests_build_output_and_generated(tmp_path):
    for name in ("A.cs", "Tests/BTests.cs", "obj/Debug/C.cs", "D.Designer.cs"):
        _write(tmp_path / name, "")
    targets, dropped = mutation_csharp._csharp_targets(
        tmp_path, ["A.cs", "Tests/BTests.cs", "obj/Debug/C.cs", "D.Designer.cs", "사라진.cs"])
    assert targets == ("A.cs",)
    assert len(dropped) == 4


def test_csharp_report_uses_absolute_keys_and_the_gate_vocabulary(tmp_path):
    """리포트의 키는 절대 경로다 — 저장소 상대로 되돌린 뒤 이번 대상만 센다."""
    report = {
        "files": {
            str(tmp_path / "A.cs"): {
                "source": "가나다\n",
                "mutants": [
                    {"location": {"start": {"line": 1, "column": 1},
                                  "end": {"line": 1, "column": 2}},
                     "mutatorName": "m", "replacement": "라", "status": "Survived",
                     "coveredBy": ["1"]},
                    {"status": "Killed"},
                    "쓰레기",
                ],
            },
            str(tmp_path / "다른.cs"): {"mutants": [{"status": "Survived"}]},
        },
        "testFiles": {"ATests.cs": {"tests": [{"id": "1", "name": "가짜 테스트"}]}},
    }
    summary = mutation_csharp.parse_stryker_net_report(report, tmp_path, {"A.cs"})
    assert summary["total"] == 2
    assert summary["counts"] == {"Survived": 1, "Killed": 1}
    first = summary["survivors"][0]
    assert first["file"] == "A.cs" and first["original"] == "가"
    assert first["tests"] == ["ATests.cs > 가짜 테스트"]


def test_csharp_report_survives_a_broken_shape(tmp_path):
    assert mutation_csharp.parse_stryker_net_report({"files": "쓰레기"}, tmp_path, None)["total"] == 0
    assert mutation_csharp._cs_test_index({"testFiles": "쓰레기"}, tmp_path) == {}


def test_csharp_test_file_paths_are_relative_to_the_repo(tmp_path):
    """`testFiles` 의 키도 절대 경로다. 되돌리지 않으면 표에 전체 경로가 실린다 (확정 10)."""
    report = {
        "files": {str(tmp_path / "src" / "A.cs"): {
            "source": "int f() { return 1; }\n",
            "mutants": [{"id": "1", "status": "Survived", "mutatorName": "m",
                         "location": {"start": {"line": 1, "column": 1},
                                      "end": {"line": 1, "column": 2}},
                         "coveredBy": ["t1"]}]}},
        "testFiles": {str(tmp_path / "src" / "ATests.cs"): {
            "tests": [{"id": "t1", "name": "X.ATests.AddWorks"}]}},
    }
    summary = mutation_csharp.parse_stryker_net_report(report, tmp_path, {"src/A.cs"})
    assert summary["survivors"][0]["tests"] == ["src/ATests.cs > X.ATests.AddWorks"]


def test_csharp_tail_folds_a_multi_line_failure_into_one_line():
    """실패 원문의 개행을 접지 않으면 사람용 표가 깨진다 (확정 6)."""
    class _Proc:
        stdout = "첫 줄\n둘째 줄"
        stderr = "\n셋째"
    assert mutation_csharp._csharp_tail(_Proc()) == "첫 줄 둘째 줄 셋째"


def test_csharp_preconditions_need_a_project_and_the_tool(tmp_path):
    missing = mutation_csharp._csharp_preconditions(_ctx(tmp_path))
    assert missing["install_hint"] == mutation_csharp._INSTALL_HINT
    tools = _tool_present("dotnet-stryker")
    no_project = mutation_csharp._csharp_preconditions(_ctx(tmp_path, tools=tools))
    assert ".csproj" in no_project["human_reason"]
    _write(tmp_path / "src/App.csproj", "")
    assert mutation_csharp._csharp_preconditions(_ctx(tmp_path, tools=tools)) is None


def test_csharp_command_uses_the_colon_form_and_neutralises_the_threshold(tmp_path):
    """`--since` 는 값이 선택인 옵션이라 콜론으로 붙인다 [소스 확인]. 임계값은 0 (R2)."""
    _write(tmp_path / "App.sln", "")
    ctx = _ctx(tmp_path, tools=_tool_present("dotnet-stryker"))
    cmd, notes = mutation_csharp._csharp_command(ctx, tmp_path / "out", ("A.cs",))
    assert "--since:main" in cmd
    assert cmd[cmd.index("--break-at") + 1] == "0"
    assert cmd[cmd.index("--reporter") + 1] == "json"
    assert cmd[cmd.index("--solution") + 1].endswith("App.sln")
    assert any("검증하지 않았습니다" in note for note in notes)


def test_csharp_command_without_a_base_runs_everything(tmp_path):
    ctx = _ctx(tmp_path, tools=_tool_present("dotnet-stryker"), base=code_gate.EMPTY_TREE)
    cmd, notes = mutation_csharp._csharp_command(ctx, tmp_path / "out", ("A.cs",))
    assert not [arg for arg in cmd if arg.startswith("--since")]
    assert any("프로젝트 전체를 돌렸고" in note for note in notes)


def test_csharp_end_to_end_with_a_stubbed_tool(tmp_path, monkeypatch):
    _write(tmp_path / "App.csproj", "")
    _write(tmp_path / "A.cs", "가나다\n")

    def fake_run(cmd, *, cwd, timeout):
        out = Path(cmd[cmd.index("--output") + 1]).joinpath(*mutation_csharp._CS_REPORT_TAIL)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"files": {str(tmp_path / "A.cs"): {
            "source": "가나다\n", "mutants": [{"status": "Survived"}, {"status": "Killed"}]}}}),
            encoding="utf-8")
        return _proc(0)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, tools=_tool_present("dotnet-stryker"))
    part = mutation_csharp._check_mutation_csharp(ctx, ["A.cs"])
    assert part["language"] == "csharp" and part["label"] == "C#"
    assert part["summary"]["score"] == 50.0
    assert part["outcome"]["status"] == "findings"


def test_csharp_and_java_keep_their_scope_notes_on_a_failed_round(tmp_path, monkeypatch):
    """범위 안내가 완주 회차에만 붙어, 실패한 회차에서 통째로 사라졌다 (확정 5).

    자바스크립트 어댑터는 중단 회차에도 남겼는데 새 어댑터 셋만 달랐다 — 물려받은
    패턴이 아니라 새로 생긴 갈림이다.
    """
    _write(tmp_path / "app.csproj", "<Project />\n")
    _write(tmp_path / "src/A.cs", "class A {}\n")
    ctx = _ctx(tmp_path, tools=_tool_present("dotnet-stryker"))
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _proc(1, "무너짐"))
    outcome, _summary = mutation_csharp._run_mutation_csharp(ctx, ["src/A.cs"])
    assert outcome["status"] == "error"
    assert any("실물로 검증하지 않았습니다" in note for note in ctx.notes)

    _write(tmp_path / "build.gradle", "plugins { id 'java' }\n")
    _write(tmp_path / "src/main/java/demo/A.java", "package demo;\nclass A {}\n")
    jctx = _ctx(tmp_path, tools=_tool_present("gradle"))
    joutcome, _js = mutation_java._run_mutation_java(jctx, ["src/main/java/demo/A.java"])
    assert joutcome["status"] == "error"
    assert any("init script 로 밖에서 붙였고" in note for note in jctx.notes)


def test_csharp_reports_when_nothing_is_written(tmp_path, monkeypatch):
    _write(tmp_path / "App.csproj", "")
    _write(tmp_path / "A.cs", "")
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _proc(1, "무슨 실패"))
    outcome, summary = mutation_csharp._run_mutation_csharp(
        _ctx(tmp_path, tools=_tool_present("dotnet-stryker")), ["A.cs"])
    assert outcome["status"] == "error" and summary is None


def test_csharp_timeout_and_scope(tmp_path):
    outcome = mutation_csharp._csharp_timed_out(None, ("A.cs",), 30)
    assert outcome["status"] == "timeout" and "30초 예산" in outcome["human_reason"]
    _write(tmp_path / "Tests/ATests.cs", "")
    ctx = _ctx(tmp_path, files=("A.cs", "b.py"))
    assert mutation_csharp._mutation_changed_csharp(ctx) == ["A.cs"]
    targets, blocked = mutation_csharp._csharp_scope(ctx, ["Tests/ATests.cs"])
    assert targets == () and blocked["status"] == "skipped"


def test_pit_root_gives_up_on_mismatched_tags():
    """되살린 XML 이 그래도 안 맞으면 예외 대신 None 이다 (R2 — 게이트는 어떤 경우에도 산다)."""
    assert mutation_java._pit_root("<x><mutation></mutation>") is None
    assert mutation_java._pit_records("<x><mutation></mutation>", {}, {}) == []


def test_go_entry_path_rejects_a_broken_entry(tmp_path):
    assert mutation_go._go_entry_path("쓰레기", {"a.go"}, tmp_path) is None
    assert mutation_go._go_entry_path({"file_name": 3}, {"a.go"}, tmp_path) is None
    assert mutation_go._go_mutations("쓰레기") == []


def test_csharp_helpers_survive_a_broken_entry():
    assert mutation_csharp._cs_mutants("쓰레기") == []
    assert mutation_csharp._cs_source_lines("쓰레기") == [""]
    assert mutation_csharp._cs_tests_of("쓰레기") == []


def test_java_timeout_before_any_report_is_still_a_timeout(tmp_path, monkeypatch):
    """리포트가 나오기 전에 끊겨도 오류가 아니라 중단이라고 말해야 한다.

    오류로 적으면 "종료 코드 ?" 만 보여, 예산을 늘리면 될 일을 사용자가 못 알아본다.
    """
    import subprocess

    def fake_run(cmd, *, cwd, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _java_project(tmp_path)
    outcome, summary = mutation_java._run_mutation_java(ctx, ["src/main/java/p/A.java"])
    assert summary is None
    assert outcome["status"] == "timeout"
    assert "리포트가 나오기 전에 끊겨" in outcome["human_reason"]


# ---------------------------------------------------------------------------
# 기본이 꺼진 어댑터 (자바)
# ---------------------------------------------------------------------------

def test_java_is_off_by_default():
    """자바는 기본이 꺼짐이다. PIT 가 회차마다 프로젝트 테스트 전체를 다시 돌기 때문이다.

    기본으로 켜 두면 테스트가 2분인 프로젝트가 매 회차 2분을 물고, 사용자는 게이트
    자체를 끄는 쪽을 택하게 된다. 켤지는 사람이 정한다.
    """
    from scripts.mutation.java import JAVA_ADAPTER

    assert JAVA_ADAPTER.default_enabled is False
    assert JAVA_ADAPTER.default_off_reason, "왜 꺼졌는지를 말하지 않으면 미지원으로 읽힌다"


def test_other_adapters_stay_on_by_default():
    """나머지는 기본이 켜짐이다 — 자바와 러스트만 예외라는 것을 못 박는다.

    둘 다 커버리지 선별이 없어 변이마다 테스트 스위트를 통째로 돈다. 목록을 여기
    적어 두는 이유는, 새 어댑터가 "안전하게" 꺼진 채 들어와 아무도 모르게 계속
    안 재어지는 일을 막기 위해서다.
    """
    from scripts.mutation import adapters

    off = {a.language for a in adapters() if not a.spec.default_enabled}
    assert off == {"java", "rust"}, off


def test_disabled_adapter_reports_why_and_how_to_turn_on(tmp_path, monkeypatch):
    """꺼진 어댑터는 조용히 넘어가지 않는다 (R4).

    변경분에 그 언어가 있는데 안 재는 것이라, 사유가 없으면 사용자는 잰 줄로 읽는다.
    켜는 방법까지 함께 낸다.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    from scripts.mutation import _adapter_is_on, adapters

    java = next(a for a in adapters() if a.language == "java")
    ctx = _ctx(tmp_path, files=["src/main/java/d/A.java"])

    assert _adapter_is_on(ctx, java) is False
    joined = " ".join(ctx.notes)
    assert "기본이 꺼짐" in joined
    assert java.spec.default_off_reason in joined
    assert '"java"' in joined and '"gradle"' in joined


def test_disabled_adapter_turns_on_when_config_names_it(tmp_path, monkeypatch):
    """설정의 `mutation.<언어>` 자리에 도구 이름을 적으면 켜진다."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    from scripts.mutation import _adapter_is_on, adapters
    from scripts.code_gate import load_config

    (tmp_path / ".code-gate.json").write_text(
        json.dumps({"mutation": {"java": "gradle"}}), encoding="utf-8")
    java = next(a for a in adapters() if a.language == "java")
    ctx = _ctx(tmp_path, files=["src/main/java/d/A.java"],
               config=load_config(tmp_path / ".code-gate.json"))

    assert _adapter_is_on(ctx, java) is True
    assert not ctx.notes


def test_all_adapters_disabled_is_a_skip_not_a_crash(tmp_path, monkeypatch):
    """꺼진 어댑터만 걸린 회차는 건너뜀이다. 빈 목록을 합치면 max() 가 터졌다 (실측)."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    from scripts.mutation import _merge_mutation_languages

    ctx = _ctx(tmp_path, files=["src/main/java/d/A.java"])
    outcome = _merge_mutation_languages(ctx, [])
    assert outcome["status"] == "skipped"
    assert "꺼져 있어" in outcome["human_reason"]


# ---------------------------------------------------------------------------
# 러스트 (cargo-mutants)
#
# 아래 리포트 조각은 실제로 돌린 `mutants.out/outcomes.json` 에서 칸 이름과 값을
# 그대로 옮긴 것이다 (cargo-mutants 27.1.0 / rustc 1.98.0).
# ---------------------------------------------------------------------------

def _rs_mutant(file="src/lib.rs", line=2, column=5, end_line=None, end_column=10,
               genre="FnValue", replacement="0"):
    """변이 회차 하나. 실제 리포트의 `scenario` 모양 그대로다."""
    return {"Mutant": {"name": f"{file}:{line}:{column}: replace f with {replacement}",
                       "package": "p", "file": file,
                       "function": {"function_name": "f", "return_type": "-> i32"},
                       "span": {"start": {"line": line, "column": column},
                                "end": {"line": end_line or line, "column": end_column}},
                       "replacement": replacement, "genre": genre}}


def _rs_report(*entries, baseline="Success"):
    """리포트 한 벌. 기준(Baseline) 회차가 늘 맨 앞에 온다 (실측)."""
    outcomes = [{"scenario": "Baseline", "summary": baseline, "phase_results": []}]
    outcomes += [{"scenario": scenario, "summary": summary, "phase_results": []}
                 for scenario, summary in entries]
    return {"outcomes": outcomes, "total_mutants": len(entries)}


def test_rust_targets_drop_tests_benches_and_build_scripts(tmp_path):
    """통합 테스트·벤치·예제·빌드 산출물·빌드 스크립트는 변이 대상이 아니다."""
    for rel in ("src/lib.rs", "tests/it.rs", "benches/b.rs", "examples/e.rs",
                "target/debug/x.rs", "build.rs"):
        _write(tmp_path / rel, "pub fn f() {}\n")
    targets, dropped = mutation_rust._rust_targets(
        tmp_path, ["src/lib.rs", "tests/it.rs", "benches/b.rs", "examples/e.rs",
                   "target/debug/x.rs", "build.rs", "사라진.rs"])
    assert targets == ("src/lib.rs",)
    assert set(dropped) == {"tests/it.rs", "benches/b.rs", "examples/e.rs",
                            "target/debug/x.rs", "build.rs", "사라진.rs"}


def test_rust_report_skips_the_baseline_scenario(tmp_path):
    """기준 회차는 변이가 아니다 — 세면 점수가 흔들린다.

    실측: 기준 회차의 `scenario` 는 문자열 "Baseline" 이고 summary 는 Success 다.
    걸러내지 않으면 그 Success 가 게이트 어휘 밖 낱말로 분포에 실리고, 변이 수가
    실제보다 하나 많아진다.
    """
    report = _rs_report((_rs_mutant(), "CaughtMutant"))
    summary = mutation_rust.parse_cargo_mutants_report(report, tmp_path, {"src/lib.rs"})
    assert summary["total"] == 1
    assert summary["counts"] == {"Killed": 1}
    assert summary["unknown"] == ()


def test_rust_missed_maps_to_survived_not_no_coverage(tmp_path):
    """MissedMutant → Survived. NoCoverage 로 보내지 않는다.

    cargo-mutants 는 변이마다 테스트 스위트를 통째로 돌린 뒤 그 결과가 성공이면
    MissedMutant 라고 적는다 (소스의 `mutant_missed`). 즉 "테스트가 돌았는데 못
    잡았다"(Survived)는 참이고 "덮는 테스트가 없어 돌리지 않았다"(NoCoverage)는
    거짓이다. 점수는 둘 다 분모에만 들어가 어느 쪽이든 같지만, 사람이 읽는 문장은
    참인 쪽이어야 한다.
    """
    assert mutation_rust._gate_status("MissedMutant") == "Survived"
    report = _rs_report((_rs_mutant(), "MissedMutant"))
    summary = mutation_rust.parse_cargo_mutants_report(report, tmp_path, {"src/lib.rs"})
    assert summary["counts"] == {"Survived": 1}
    assert summary["counts"].get("NoCoverage") is None
    assert summary["score"] == 0.0


def test_rust_status_map_covers_the_five_declared_words(tmp_path):
    """선언한 다섯 낱말이 실제로 게이트 어휘로 바뀐다 — 표만 있고 적용이 없으면 안 된다."""
    expected = {"CaughtMutant": "Killed", "MissedMutant": "Survived",
                "Unviable": "CompileError", "Timeout": "Timeout", "Failure": "RuntimeError"}
    assert mutation_rust.CARGO_MUTANTS_STATUS_TO_GATE == expected
    for own, gate_word in expected.items():
        assert mutation_rust._gate_status(own) == gate_word
        record = mutation_rust._rust_record("a.rs", _rs_mutant()["Mutant"], own, [])
        assert record["status"] == gate_word


def test_rust_unknown_status_passes_through(tmp_path):
    """표 밖 낱말은 원어 그대로 지나 unknown 경로가 잡는다 (R4).

    변이 회차의 `Success` 가 그 자리다. 소스가 스스로 "should be rare or impossible"
    이라고 적은 갈래라 뜻을 정하지 않았다 — 짐작으로 Killed 나 Survived 에 넣으면
    점수가 조용히 틀어진다.
    """
    assert "Success" not in mutation_rust.CARGO_MUTANTS_STATUS_TO_GATE
    report = _rs_report((_rs_mutant(), "Success"))
    summary = mutation_rust.parse_cargo_mutants_report(report, tmp_path, {"src/lib.rs"})
    assert summary["unknown"] == ("Success",)
    assert summary["score"] is None      # 분모에서 빠졌다


def test_rust_span_slice_counts_characters_not_utf16():
    """span 의 열은 UTF-16 이 아니라 문자(코드 포인트) 번호다 (실측).

    중립층의 slice_lines 는 Stryker 의 UTF-16 셈이라, 이모지가 앞에 있는 줄에서
    자리가 두 칸씩 밀린다. 실제로 돌려 본 값(`"🚀🚀"` 이 든 줄에서 `+` 가 37열)이
    문자 셈으로만 맞았다.
    """
    line = '    let _s = "🚀🚀"; let _t = "한글"; n + 1'
    span = {"start": {"line": 1, "column": 37}, "end": {"line": 1, "column": 38}}
    assert mutation_rust._rust_slice([line], span) == "+"


def test_rust_span_slice_spans_lines_and_gives_up_on_nonsense():
    """여러 줄에 걸친 변이도 잘라내고, 자리가 어긋나면 빈 문자열이다."""
    lines = ["fn f() {", "    a + b", "}"]
    # 끝 열은 포함하지 않는다 — 3줄 2열이면 3줄의 1열(`}`)까지다. 실측한 함수 span
    # (1줄 1열 ~ 3줄 2열 = 함수 전체)이 이 규칙과 같았다.
    span = {"start": {"line": 1, "column": 8}, "end": {"line": 3, "column": 2}}
    assert mutation_rust._rust_slice(lines, span) == "{\n    a + b\n}"
    assert mutation_rust._rust_slice(lines, {"start": {"line": 9, "column": 1},
                                             "end": {"line": 9, "column": 2}}) == ""
    assert mutation_rust._rust_slice(lines, "쓰레기") == ""
    assert mutation_rust._rust_slice(lines, {"start": {}, "end": {}}) == ""


def test_rust_original_is_capped_to_one_table_row():
    """함수 몸통 전체가 바뀌는 변이의 원본 자리는 잘라서 싣는다.

    자르지 않으면 살아남은 변이 한 줄이 수백 글자가 돼 표가 읽히지 않는다.
    """
    long_line = "x" * 500
    span = {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 501}}
    assert len(mutation_rust._rust_slice([long_line], span)) == mutation_rust._ORIGINAL_MAX


def test_rust_record_says_the_tool_gave_no_test_list():
    """cargo-mutants 는 어느 테스트가 덮었는지 주지 않는다 — 지어내지 않고 비운다.

    빈 목록으로 두면 표가 "덮은 테스트 없음" 이라고 적는데, 그것은 이 도구가 알 수
    없는 사실이다. None 이어야 "도구가 알려 주지 않습니다" 로 나간다.
    """
    record = mutation_rust._rust_record("src/lib.rs", _rs_mutant()["Mutant"],
                                        "MissedMutant", ["fn f() {", "    a + b"])
    assert record["tests"] is None
    assert record["line"] == 2 and record["column"] == 5
    assert record["mutator"] == "FnValue" and record["replacement"] == "0"
    assert record["original"] == "a + b"


def test_rust_report_filters_to_this_round(tmp_path):
    """이번 대상 밖의 파일은 세지 않는다 (R3)."""
    report = _rs_report((_rs_mutant(file="src/lib.rs"), "CaughtMutant"),
                        (_rs_mutant(file="src/다른.rs"), "MissedMutant"))
    summary = mutation_rust.parse_cargo_mutants_report(report, tmp_path, {"src/lib.rs"})
    assert summary["total"] == 1 and summary["files"] == ["src/lib.rs"]
    assert mutation_rust.parse_cargo_mutants_report({"outcomes": "쓰레기"}, tmp_path,
                                                    set())["total"] == 0
    assert mutation_rust.parse_cargo_mutants_report({}, tmp_path, set())["total"] == 0


def test_rust_report_path_falls_back_to_a_unique_suffix(tmp_path):
    """워크스페이스 기준 경로가 저장소 기준과 어긋나면 접미사가 하나뿐일 때만 맞춘다."""
    assert mutation_rust._rust_report_path(tmp_path, "src/lib.rs", {"crates/a/src/lib.rs"}) \
        == "crates/a/src/lib.rs"
    # 둘 이상이면 맞추지 않는다 — 잘못 맞추면 다른 파일의 점수가 된다
    assert mutation_rust._rust_report_path(
        tmp_path, "src/lib.rs", {"crates/a/src/lib.rs", "crates/b/src/lib.rs"}) is None
    # 경로 구분자 경계에서만 맞춘다 (`xlib.rs` 가 `lib.rs` 에 맞으면 안 된다)
    assert mutation_rust._rust_report_path(tmp_path, "lib.rs", {"src/xlib.rs"}) is None


def test_rust_unmatched_report_files_are_named(tmp_path):
    """못 맞춘 파일 이름을 세어 남긴다 — 안 그러면 요약이 비어 정상 종료처럼 보인다 (R4)."""
    report = _rs_report((_rs_mutant(file="크레이트X/src/lib.rs"), "MissedMutant"))
    assert mutation_rust.unmatched_report_files(report, tmp_path, {"src/other.rs"}) \
        == ["크레이트X/src/lib.rs"]
    # 기준 회차는 파일이 없으니 목록에 끼지 않는다
    assert mutation_rust.unmatched_report_files(_rs_report(), tmp_path, set()) == []


def test_rust_preconditions_need_cargo_toml_and_the_tool(tmp_path):
    """도구가 없으면 건너뛰되 설치 방법을 낸다 (R4). Cargo.toml 이 없어도 건너뛴다."""
    missing = mutation_rust._rust_preconditions(_ctx(tmp_path))
    assert missing["status"] == "skipped"
    assert missing["install_hint"] == mutation_rust._INSTALL_HINT
    assert "cargo install cargo-mutants" in missing["install_hint"]

    tools = _tool_present("cargo-mutants")
    no_manifest = mutation_rust._rust_preconditions(_ctx(tmp_path, tools=tools))
    assert "Cargo.toml" in no_manifest["human_reason"]

    _write(tmp_path / "Cargo.toml", "[package]\n")
    assert mutation_rust._rust_preconditions(_ctx(tmp_path, tools=tools)) is None


def test_rust_preconditions_reject_an_unknown_configured_tool(tmp_path):
    """설정에 다른 도구 이름이 적혀 있으면 그 자리를 말하고 건너뛴다."""
    (tmp_path / ".code-gate.json").write_text(
        json.dumps({"mutation": {"rust": "다른도구"}}), encoding="utf-8")
    ctx = _ctx(tmp_path, config=code_gate.load_config(tmp_path / ".code-gate.json"))
    blocked = mutation_rust._rust_preconditions(ctx)
    assert blocked["status"] == "skipped"
    assert "mutation.rust" in blocked["human_reason"]


def test_rust_command_uses_the_subcommand_and_narrows_by_file(tmp_path):
    """직접 부를 때는 `mutants` 하위 명령을 붙인다 (실측). 파일 좁히기는 `--file`."""
    ctx = _ctx(tmp_path, tools=_tool_present("cargo-mutants"))
    cmd, notes = mutation_rust._rust_command(ctx, tmp_path / "out", ("src/lib.rs",), None)
    assert cmd[1] == "mutants"
    assert cmd[cmd.index("--output") + 1] == str(tmp_path / "out")
    assert cmd[cmd.index("--file") + 1] == "src/lib.rs"
    assert "--in-place" not in cmd, "사본 안에서 돌아야 소스가 오염되지 않는다"
    assert "--iterate" not in cmd, "증분은 잡힌 변이를 결과에서 빼 점수를 무너뜨린다 (실측)"
    assert any("바뀌지 않은 줄도 함께 변이됩니다" in note for note in notes)


def test_rust_command_narrows_by_changed_lines_when_a_diff_is_given(tmp_path):
    """diff 파일을 받으면 바뀐 줄 범위까지 좁힌다 (R1·R3)."""
    ctx = _ctx(tmp_path, tools=_tool_present("cargo-mutants"))
    diff = tmp_path / "changed.diff"
    cmd, notes = mutation_rust._rust_command(ctx, tmp_path / "out", ("src/lib.rs",), diff)
    assert cmd[cmd.index("--in-diff") + 1] == str(diff)
    assert any("바뀐 줄 범위 안의 변이만" in note for note in notes)
    assert not any("바뀌지 않은 줄도 함께 변이됩니다" in note for note in notes)


def test_rust_command_gives_up_file_narrowing_on_glob_metacharacters(tmp_path):
    """글롭 특수문자가 든 경로가 섞이면 파일 좁히기를 통째로 포기하고 그 사실을 말한다.

    `--file` 값은 globset 을 지난다 (소스 확인). 그 하나만 빼면 그 파일이 아예 안
    재어지는데, 안 재는 것보다 넓게 재는 편이 낫다 — 점수 범위는 어차피 게이트가
    대상 목록으로 거른다.
    """
    assert mutation_rust._glob_safe("src/lib.rs") is True
    assert mutation_rust._glob_safe("src/[gen]/lib.rs") is False
    ctx = _ctx(tmp_path, tools=_tool_present("cargo-mutants"))
    cmd, notes = mutation_rust._rust_command(
        ctx, tmp_path / "out", ("src/lib.rs", "src/[gen]/x.rs"), None)
    assert "--file" not in cmd
    assert any("글롭 특수문자" in note for note in notes)


def test_rust_blind_spot_warning_is_in_the_scope_notes(tmp_path):
    """두 종류의 살아남음을 구분하지 못한다는 사실이 실행 전 참고에 들어간다 (R4).

    실행 전에 남기는 이유는 실패한 회차에서도 남아야 하기 때문이다 — 리포트가 안
    나온 회차에서 이 문장이 사라지면, 사용자는 러스트 결과의 성격을 모른 채 다음
    회차를 돈다.
    """
    ctx = _ctx(tmp_path, tools=_tool_present("cargo-mutants"))
    _cmd, notes = mutation_rust._rust_command(ctx, tmp_path / "out", ("src/lib.rs",), None)
    joined = " ".join(notes)
    assert "두 종류의 살아남음을 구분하지 못합니다" in joined
    assert "'덮은 테스트 없음' 칸은 언제나 0" in joined
    assert "변이마다 사본 안에서 다시 빌드" in joined      # R1 비용도 함께 신고한다


def _rust_project(tmp_path):
    _write(tmp_path / "Cargo.toml", "[package]\nname = \"p\"\n")
    _write(tmp_path / "src/lib.rs", "pub fn f(a: i32) -> i32 {\n    a + 1\n}\n")


def test_rust_end_to_end_with_a_stubbed_tool(tmp_path, monkeypatch):
    """리포트를 쓰는 가짜 도구로 한 바퀴. 점수 문장 옆에 한계 한 줄이 실려야 한다."""
    _rust_project(tmp_path)

    def fake_run(cmd, *, cwd, timeout):
        if cmd[0] == "git":
            return _proc(1, "")            # diff 를 못 뜬 회차 — 파일 단위로만 좁힌다
        out = Path(cmd[cmd.index("--output") + 1])
        (out / "mutants.out").mkdir(parents=True, exist_ok=True)
        (out / "mutants.out" / "outcomes.json").write_text(json.dumps(_rs_report(
            (_rs_mutant(line=2, column=5, end_column=10), "CaughtMutant"),
            (_rs_mutant(line=2, column=7, end_column=8, genre="BinaryOperator",
                        replacement="-"), "MissedMutant"))), encoding="utf-8")
        return _proc(2, "2 mutants tested: 1 missed, 1 caught")

    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, tools=_tool_present("cargo-mutants"))
    part = mutation_rust._check_mutation_rust(ctx, ["src/lib.rs"])

    assert part["language"] == "rust" and part["label"] == "러스트"
    assert part["summary"]["score"] == 50.0
    assert part["outcome"]["status"] == "findings"
    # 종료 코드 2 는 "잡히지 않은 변이가 있다" 라는 정상 결과다 — 오류로 읽으면 안 된다
    assert "두 종류의 살아남음을 구분하지 못합니다" in part["outcome"]["human_reason"]
    survivor = part["outcome"]["findings"][0]
    assert survivor["file"] == "src/lib.rs" and survivor["original"] == "+"
    assert survivor["tests"] is None


def test_rust_baseline_failure_is_not_a_quiet_pass(tmp_path, monkeypatch):
    """기준 테스트가 이미 빨간 회차는 "변이가 없었다" 가 아니라 오류다 (R4).

    실측: 그 회차에도 리포트는 나오고 total_mutants 가 0 이며, 기준 회차 하나가
    Failure 로 남는다. 그것을 "변이가 하나도 만들어지지 않았습니다" 로 내면 통과처럼
    읽히는데, 사용자가 할 일은 전혀 다르다.
    """
    _rust_project(tmp_path)

    def fake_run(cmd, *, cwd, timeout):
        if cmd[0] == "git":
            return _proc(1, "")
        out = Path(cmd[cmd.index("--output") + 1])
        (out / "mutants.out").mkdir(parents=True, exist_ok=True)
        (out / "mutants.out" / "outcomes.json").write_text(
            json.dumps(_rs_report(baseline="Failure")), encoding="utf-8")
        return _proc(4, "cargo test failed in an unmutated tree, so no mutants were tested")

    monkeypatch.setattr(code_gate, "_run", fake_run)
    outcome, summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["src/lib.rs"])
    assert outcome["status"] == "error" and summary is None
    assert "이미 실패" in outcome["human_reason"]


def test_rust_baseline_failure_carries_the_tool_output(tmp_path, monkeypatch):
    """기준 실패 안내는 원인을 단정하지 않고 도구 원문을 함께 실어야 한다.

    실측: 타입 오류로 빌드가 깨진 크레이트와, 테스트가 `.git` 을 요구하는 크레이트가
    **한 글자도 다르지 않은** 문장을 냈다. 앞쪽에서 그 단정은 거짓이고, 사용자는 있지도
    않은 원인을 찾으러 간다. 형제 분기(`_rust_no_report`)는 같은 자리에서 원문 꼬리를
    싣는데 여기만 `proc` 을 받지 않아 진단 정보가 통째로 버려지고 있었다.
    """
    _rust_project(tmp_path)

    def fake_run(cmd, *, cwd, timeout):
        if cmd[0] == "git":
            return _proc(1, "")
        out = Path(cmd[cmd.index("--output") + 1])
        (out / "mutants.out").mkdir(parents=True, exist_ok=True)
        (out / "mutants.out" / "outcomes.json").write_text(
            json.dumps(_rs_report(baseline="Failure")), encoding="utf-8")
        return _proc(4, "error[E0277]: cannot add `&str` to `i32`\n"
                        "ERROR cargo build failed in an unmutated tree")

    monkeypatch.setattr(code_gate, "_run", fake_run)
    outcome, _summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["src/lib.rs"])
    human = outcome["human_reason"]
    assert "cargo build failed in an unmutated tree" in human
    assert "E0277" in human
    assert "흔한 원인" in human, "하나로 단정하지 않는다"
    assert "\n" not in human, "표는 항목 하나가 한 줄이라는 전제 위에 있다"


def test_rust_parse_diff_failure_is_named_not_just_dumped(tmp_path, monkeypatch):
    """도구가 diff 를 해석하지 못한 회차는 무엇이 잘못됐는지 이름을 붙여 낸다 (R4)."""
    _rust_project(tmp_path)
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _proc(
        6, "ERROR Failed to parse diff: invalid escaped character") if cmd[0] != "git"
        else _proc(0, "diff --git a/src/lib.rs b/src/lib.rs\n"))
    outcome, summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["src/lib.rs"])
    assert outcome["status"] == "error" and summary is None
    assert "해석하지 못했습니다" in outcome["human_reason"]


def test_rust_no_report_with_exit_zero_is_a_skip_not_an_error(tmp_path, monkeypatch):
    """변경분 안에 변이가 없으면 도구가 리포트를 아예 안 쓰고 0 으로 끝난다 (실측).

    그것을 오류로 내면 거짓 경보다 — 잴 것이 없었다는 뜻이다.
    """
    _rust_project(tmp_path)
    monkeypatch.setattr(code_gate, "_run",
                        lambda cmd, *, cwd, timeout: _proc(0, "Diff file is empty"))
    outcome, summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["src/lib.rs"])
    assert outcome["status"] == "skipped" and summary is None
    assert "잴 것이 없었습니다" in outcome["human_reason"]


def test_rust_no_report_with_a_failure_names_what_it_recognises(tmp_path, monkeypatch):
    """리포트가 없고 비-0 으로 끝났으면 오류다. 알아본 사유는 함께 적는다."""
    _rust_project(tmp_path)
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: _proc(
        6, "ERROR Failed to open diff file: No such file\nor directory"))
    outcome, summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["src/lib.rs"])
    assert outcome["status"] == "error" and summary is None
    assert "diff 파일을 열지 못했습니다" in outcome["human_reason"]
    # 여러 줄인 원문이 한 줄로 접혀야 표가 깨지지 않는다
    assert "\n" not in outcome["human_reason"]


def test_rust_failure_cause_stays_silent_on_text_it_cannot_read():
    """못 알아본 실패는 사유를 지어내지 않는다."""
    assert mutation_rust._rust_failure_cause("무슨 소린지 모를 출력") == ""


def test_rust_timeout_keeps_what_it_saw(tmp_path, monkeypatch):
    """예산을 넘겨 중단해도 그때까지의 리포트를 읽어 낸다 (실측: 회차마다 다시 쓴다)."""
    _rust_project(tmp_path)

    def fake_run(cmd, *, cwd, timeout):
        if cmd[0] == "git":
            return _proc(1, "")
        out = Path(cmd[cmd.index("--output") + 1])
        (out / "mutants.out").mkdir(parents=True, exist_ok=True)
        (out / "mutants.out" / "outcomes.json").write_text(json.dumps(_rs_report(
            (_rs_mutant(), "MissedMutant"))), encoding="utf-8")
        raise __import__("subprocess").TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(code_gate, "_run", fake_run)
    outcome, summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["src/lib.rs"])
    assert outcome["status"] == "timeout"
    assert summary["total"] == 1
    assert len(outcome["findings"]) == 1
    assert "두 종류의 살아남음을 구분하지 못합니다" in outcome["human_reason"]


def _git_calls(recorder):
    """`gate._run` 을 대신해 git 호출만 기록하는 가짜. diff 원문은 인자마다 다르게 낸다."""
    def fake_run(cmd, *, cwd, timeout):
        recorder.append(list(cmd))
        if "--no-index" in cmd:
            return _proc(1, f"diff --git a/dev/null b/{cmd[-1]}\n")
        if "--merge-base" in cmd:
            return _proc(0, "diff --git a/src/lib.rs b/src/lib.rs\n")
        return _proc(0, "diff --git a/두점 b/두점\n")
    return fake_run


def test_rust_diff_quotes_paths_the_way_the_tool_can_parse(tmp_path, monkeypatch):
    """모든 git 호출에 `core.quotepath=false` 가 붙어야 한다.

    git 의 기본값은 비ASCII 경로를 `"a/docs/\\354\\204\\244..."` 로 이스케이프해
    내보내고, cargo-mutants 의 diff 파서는 그것을 종료 코드 6 으로 거절한다
    (실측: `Failed to parse diff: invalid escaped character`). 한글 경로가 하나만
    섞여도 러스트 측정이 통째로 사라졌다 — 이 저장소에서는 상시 실패 경로다.
    """
    calls = []
    monkeypatch.setattr(code_gate, "_run", _git_calls(calls))
    path, note = mutation_rust._rust_diff_file(_ctx(tmp_path), tmp_path)
    assert path is not None and note == ""
    assert calls, "git 을 한 번도 부르지 않았다"
    for cmd in calls:
        assert cmd[:3] == ["git", "-c", "core.quotepath=false"], cmd


def test_rust_diff_uses_the_same_merge_base_as_the_gate(tmp_path, monkeypatch):
    """변경분 판정 기준이 뼈대와 같아야 한다 (R3).

    두 점 비교(`git diff <기준>`)만 쓰면 분기한 브랜치에서 **상대 브랜치가 바꾼 줄**까지
    변이 대상이 된다. 실측: 서로 다른 함수를 고친 두 브랜치에서 분모의 절반(변이 10개 중
    5개)이 이번 변경분 밖이었고, `--merge-base` 를 붙이자 5개로 정정됐다.
    뼈대의 `_raw_changed_lines` 와 같이 실패하면 두 점 비교로 내려간다.
    """
    calls = []
    monkeypatch.setattr(code_gate, "_run", _git_calls(calls))
    text, no_git = mutation_rust._rust_tracked_diff(_ctx(tmp_path, base="main"), "main")
    assert no_git is False
    assert calls[0][3:] == ["diff", "--merge-base", "main"], calls[0]
    assert "src/lib.rs" in text and "두점" not in text

    # `--merge-base` 를 못 쓰는 기준에서는 두 점 비교로 내려간다.
    calls.clear()
    monkeypatch.setattr(code_gate, "_run", lambda cmd, *, cwd, timeout: (
        calls.append(list(cmd)) or (_proc(128, "") if "--merge-base" in cmd
                                    else _proc(0, "diff --git a/두점 b/두점\n"))))
    text, no_git = mutation_rust._rust_tracked_diff(_ctx(tmp_path, base="main"), "main")
    assert no_git is False and "두점" in text
    assert len(calls) == 2


def test_rust_diff_includes_untracked_targets_the_gate_counted(tmp_path, monkeypatch):
    """추적되지 않은 새 파일도 `--in-diff` 범위에 들어가야 한다 (R3·R4).

    `git diff <기준>` 에는 추적되지 않은 파일이 없다. 그대로 넘기면 게이트가 대상으로
    잡은 새 파일이 도구 쪽에서 통째로 잘려 나간다 — 실측: 변이 8개가 있는 회차가
    "이번 변경분 안에 러스트 변이가 하나도 없어 잴 것이 없었습니다" 로 나갔다.
    `git add` 한 번으로 판정이 뒤집혔고 파일 내용은 한 글자도 안 바뀌었다.
    """
    calls = []
    monkeypatch.setattr(code_gate, "_run", _git_calls(calls))
    ctx = _ctx(tmp_path, files=("src/lib.rs", "src/newmod.rs"))
    ctx.change.lines = {"src/lib.rs": {3}, "src/newmod.rs": None}

    assert mutation_rust._rust_whole_file_targets(
        ctx, ("src/lib.rs", "src/newmod.rs")) == ("src/newmod.rs",)

    path, note = mutation_rust._rust_diff_file(
        ctx, tmp_path, ("src/lib.rs", "src/newmod.rs"))
    assert note == "" and path is not None
    text = path.read_text(encoding="utf-8")
    assert "b/src/lib.rs" in text and "b/src/newmod.rs" in text
    # `--no-index` 는 내용이 다르면 종료 코드 1 이다 — 그것을 실패로 읽으면 다시 빠진다.
    assert any("--no-index" in cmd for cmd in calls)


def test_rust_diff_still_narrows_when_only_untracked_targets_changed(tmp_path, monkeypatch):
    """추적된 변경이 하나도 없어도 새 파일만으로 좁히기가 성립한다."""
    def fake_run(cmd, *, cwd, timeout):
        if "--no-index" in cmd:
            return _proc(1, "diff --git a/dev/null b/src/newmod.rs\n")
        return _proc(0, "")                       # 추적된 변경분 없음
    monkeypatch.setattr(code_gate, "_run", fake_run)
    ctx = _ctx(tmp_path, files=("src/newmod.rs",))
    ctx.change.lines = {"src/newmod.rs": None}
    path, note = mutation_rust._rust_diff_file(ctx, tmp_path, ("src/newmod.rs",))
    assert note == "" and path is not None
    assert "src/newmod.rs" in path.read_text(encoding="utf-8")


def test_rust_diff_file_is_skipped_without_a_base(tmp_path):
    """비교 기준이 없으면 diff 를 뜨지 않는다 — 안 좁히는 것은 느려질 뿐이다."""
    ctx = _ctx(tmp_path, base=code_gate.EMPTY_TREE)
    assert mutation_rust._rust_diff_file(ctx, tmp_path) == (None, "")


def test_rust_diff_file_survives_a_missing_git(tmp_path, monkeypatch):
    """git 이 없어도 죽지 않는다. 못 좁혔다는 사실만 남기고 넘어간다 (R2)."""
    def boom(cmd, *, cwd, timeout):
        raise OSError("git 이 없다")

    monkeypatch.setattr(code_gate, "_run", boom)
    path, note = mutation_rust._rust_diff_file(_ctx(tmp_path), tmp_path)
    assert path is None and "git diff 를 뜨지 못해" in note


def test_rust_diff_file_is_written_and_passed(tmp_path, monkeypatch):
    """git diff 를 떠서 파일로 남기고 그 경로를 넘긴다."""
    monkeypatch.setattr(code_gate, "_run",
                        lambda cmd, *, cwd, timeout: _proc(0, "diff --git a/x b/x\n"))
    path, note = mutation_rust._rust_diff_file(_ctx(tmp_path), tmp_path)
    assert note == "" and path is not None
    assert path.read_text(encoding="utf-8").startswith("diff --git")


def test_rust_scope_and_changed_files(tmp_path):
    """변경분에서 .rs 만 고르고, 남는 대상이 없으면 사유와 함께 건너뛴다."""
    _write(tmp_path / "tests/it.rs", "")
    ctx = _ctx(tmp_path, files=("src/lib.rs", "a.py", "b.RS"))
    assert mutation_rust._mutation_changed_rust(ctx) == ["src/lib.rs", "b.RS"]
    targets, blocked = mutation_rust._rust_scope(ctx, ["tests/it.rs"])
    assert targets == () and blocked["status"] == "skipped"
    assert any("뺐습니다" in note for note in ctx.notes)


def test_rust_is_off_by_default():
    """러스트는 기본이 꺼짐이다 — 커버리지 선별이 없어 변이마다 다시 빌드한다 (R1).

    실측: 함수 셋짜리 장난감 크레이트에서 변이 15개에 8.5초(변이당 0.56초)였고,
    그중 빌드가 2.61초였다. 실제 크레이트에서는 빌드 시간이 그대로 얹힌다.
    """
    assert mutation_rust.RUST_ADAPTER.default_enabled is False
    assert "빌드" in mutation_rust.RUST_ADAPTER.default_off_reason


def test_rust_declares_that_it_does_not_reuse_previous_rounds():
    """증분을 안 쓴다고 선언한다 — `--iterate` 는 점수를 무너뜨린다 (실측).

    지난 회차에 잡힌 변이를 이번 결과에서 빼 버려, 같은 코드에 두 번 돌리면
    27.8% 가 0.0% 가 됐다. 잡힌 변이가 분자에서 사라지기 때문이다.
    """
    assert mutation_rust.RUST_ADAPTER.incremental is False
    assert mutation_rust.RUST_ADAPTER.incremental_triggers == ()


def test_rust_baseline_summary_is_none_when_there_is_no_baseline():
    """기준 회차가 아예 없는 리포트도 있다 — 그때는 "기준 실패" 로 몰지 않는다."""
    assert mutation_rust._rust_baseline_summary(
        {"outcomes": [{"scenario": _rs_mutant(), "summary": "MissedMutant"}]}) is None
    assert mutation_rust._rust_baseline_summary({}) is None


def test_rust_span_point_gives_up_on_a_broken_shape():
    """span 의 점이 사전이 아니거나 숫자가 아니면 자리를 지어내지 않는다.

    없는 자리를 0 이나 1 로 채우면 표가 존재하지 않는 줄을 가리킨다.
    """
    assert mutation_rust._rust_span_point("쓰레기", "line") is None
    assert mutation_rust._rust_span_point({"line": "둘"}, "line") is None
    assert mutation_rust._rust_span_point({"line": 2}, "line") == 2


def test_rust_diff_file_survives_an_unwritable_work_dir(tmp_path, monkeypatch):
    """diff 파일을 못 써도 회차를 죽이지 않는다 — 못 좁혔다는 사실만 남긴다 (R2)."""
    monkeypatch.setattr(code_gate, "_run",
                        lambda cmd, *, cwd, timeout: _proc(0, "diff --git a/x b/x\n"))
    path, note = mutation_rust._rust_diff_file(_ctx(tmp_path), tmp_path / "없는폴더")
    assert path is None and note == mutation_rust._DIFF_UNWRITABLE


def test_rust_unmatched_files_reach_the_user_notes(tmp_path):
    """맞추지 못한 파일 이름이 참고에 실린다 — 안 그러면 요약이 빈 채로 통과한다 (R4)."""
    ctx = _ctx(tmp_path)
    mutation_rust._rust_note_unmatched(
        ctx, _rs_report((_rs_mutant(file="크레이트X/src/lib.rs"), "MissedMutant")),
        {"src/other.rs"})
    assert any("맞추지 못해" in note and "크레이트X/src/lib.rs" in note for note in ctx.notes)
    # 리포트 자체가 없으면 할 말이 없다
    ctx.notes.clear()
    mutation_rust._rust_note_unmatched(ctx, {}, {"src/other.rs"})
    assert ctx.notes == []


def test_rust_stops_before_running_when_preconditions_block(tmp_path, monkeypatch):
    """도구가 없으면 서브프로세스를 한 번도 띄우지 않는다 (R1 — 없는 도구에 시간을 쓰지 않는다)."""
    def boom(*a, **k):
        raise AssertionError("선행 조건이 막았는데 실행했다")

    monkeypatch.setattr(code_gate, "_run", boom)
    outcome, summary = mutation_rust._run_mutation_rust(_ctx(tmp_path), ["src/lib.rs"])
    assert outcome["status"] == "skipped" and summary is None


def test_rust_stops_before_running_when_nothing_is_mutable(tmp_path, monkeypatch):
    """대상이 통합 테스트뿐이면 도구를 부르지 않고 사유를 낸다 (R1·R4)."""
    _rust_project(tmp_path)
    _write(tmp_path / "tests/it.rs", "#[test]\nfn t() {}\n")

    def boom(*a, **k):
        raise AssertionError("변이 대상이 없는데 실행했다")

    monkeypatch.setattr(code_gate, "_run", boom)
    outcome, summary = mutation_rust._run_mutation_rust(
        _ctx(tmp_path, tools=_tool_present("cargo-mutants")), ["tests/it.rs"])
    assert outcome["status"] == "skipped" and summary is None
    assert "변이 대상이 아닙니다" in outcome["human_reason"]
