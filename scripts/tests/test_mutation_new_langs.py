"""자바 / 고 / C# 어댑터 단위 테스트 (1d).

자바는 실물(pitest 1.22.0 + Gradle)로 돌려 본 어댑터이고, 고와 C# 은 도구가 이 기계에
없어 **한 회차도 돌려 보지 못한** 어댑터다. 그래서 세 어댑터의 검증 무게가 다르다.

  - 세 어댑터 공통으로 검증하는 것: 대상 고르기, 리포트 → 기록 변환, 어휘 변환,
    선행 조건(설정 값·도구 부재·프로젝트 형태), 명령 조립, 리포트 없음·중단 처리.
    전부 서브프로세스 없이 도는 순수 함수이거나, `gate._run` 을 바꿔치기한 경로다.
  - **검증되지 않는 것**: 고와 C# 이 실제로 내는 리포트의 내용. 여기 쓰인 표본은
    두 도구의 소스에서 읽은 자료 구조를 그대로 옮긴 것이지 실행 산출물이 아니다.
    도구를 깔 수 있는 기계에서 한 번은 실물로 맞대 봐야 한다.
"""

import json
import types
from pathlib import Path

import pytest

from scripts import code_gate
from scripts.mutation import csharp as mutation_csharp
from scripts.mutation import go as mutation_go
from scripts.mutation import java as mutation_java


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    """캐시를 tmp 로 격리한다 — 이 묶음이 사용자 캐시를 읽거나 쓰지 않게."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("cache")))


def _ctx(tmp_path, tools=None, base="main", files=()):
    """어댑터가 읽는 칸만 채운 최소 맥락."""
    return types.SimpleNamespace(
        repo_root=tmp_path,
        tmpdir=tmp_path / "tmp",
        config=code_gate.load_config(tmp_path / "없는설정.json"),
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
# ---------------------------------------------------------------------------

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
    assert any("검증하지 않았습니다" in note for note in notes)
    # `--diff` 를 준 회차에 gremlins 는 **바뀐 줄 범위 안의 변이만** 돌린다 (확정 8).
    # 파일 단위라고 말하면 실제보다 넓게 쟀다고 알리는 셈이다.
    assert any("바뀐 줄 범위 안의 변이만" in note for note in notes)
    assert not any("바뀌지 않은 줄도 함께 변이됩니다" in note for note in notes)


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


def test_unverified_warning_survives_a_failed_round(tmp_path, monkeypatch):
    """"이 어댑터는 미검증" 경고가 완주 회차에만 붙었다 (확정 5).

    실측: 리포트를 안 쓰는 도구로 돌리면 참고에 그 경고가 통째로 없었다. 경고가 가장
    필요한 순간은 성공했을 때가 아니라 실패했을 때다 — 사용자는 도구 문제인지 한 번도
    검증되지 않은 명령줄 조립 문제인지 가를 단서를 잃는다 (R4).
    """
    _write(tmp_path / "go.mod", "module x\n")
    _write(tmp_path / "a.go", "package p\n")
    ctx = _ctx(tmp_path, tools=_tool_present("gremlins"))
    monkeypatch.setattr(code_gate, "_run", lambda *a, **k: _proc(0, "리포트를 쓰지 않음"))
    outcome, summary = mutation_go._run_mutation_go(ctx, ["a.go"])
    assert outcome["status"] == "error" and summary is None
    assert any("실물로 검증하지 않았습니다" in note for note in ctx.notes)


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
