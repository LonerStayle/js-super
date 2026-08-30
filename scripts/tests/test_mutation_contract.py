"""어댑터 계약 테스트 — 선언부(AdapterSpec)와 동작의 일치 (1c).

기존 code_gate 테스트와 별개의 신규 묶음이다. 선언부는 런타임 분기를 만들지 않는
대신, 선언이 거짓이면 여기서 잡는다.

어댑터 목록은 손으로 등록하지 않고 `scripts/mutation/` 안의 `*_ADAPTER` 상수를 훑어
찾는다. 손으로 등록하던 때는 등록을 잊은 어댑터가 검사 0건으로 통과했다 (실측).

검증 시나리오:
1. status_map 의 값 전부가 게이트 어휘 여덟 이름 안에 있다.
2. 선언의 language / label 이 실행부가 돌려주는 네 칸과 같다.
3. requires 는 선행 항목 코드 → 뼈대 상태 칸 표를 지나 소스와 양방향으로 맞는다.
4. 어댑터가 만지는 뼈대 표면이 신고된 목록 안에 있다 (새 이름을 잡으면 여기 추가).
5. 어댑터는 서브프로세스를 직접 부르지 않는다 — 뼈대의 gate._run 만 쓴다.
6. 사본을 만드는 어댑터만 copy_limitations 가 차 있다 (소스에서 사본 여부를 본다).
7. 실패 각인 — 입력이 같으면 즉시 같은 오류, 무효화는 사본 구성 변화까지 본다.
8. tool / incremental / field_confidence 가 실제 동작과 맞는다.
9. 레지스트리(런타임 목록)가 자동 수집과 같고, config_key / tool 선언을 실제로 쓴다.
"""

import dataclasses
import importlib
import io
import inspect
import json
import pkgutil
import re
import tokenize
import types

import pytest

from scripts import code_gate
from scripts import mutation
from scripts.mutation import csharp as mutation_csharp
from scripts.mutation import go as mutation_go
from scripts.mutation import java as mutation_java
from scripts.mutation import javascript as mutation_javascript
from scripts.mutation import python as mutation_python
from scripts.mutation import rust as mutation_rust
from scripts.mutation import score as mutation_score_mod


def _discover_adapters():
    """`scripts/mutation/` 안의 `*_ADAPTER` 상수를 전부 찾는다 — 등록 망각을 없앤다."""
    adapters: dict = {}
    modules: dict = {}
    for info in pkgutil.iter_modules(mutation.__path__):
        module = importlib.import_module(f"{mutation.__name__}.{info.name}")
        for name, value in vars(module).items():
            if name.endswith("_ADAPTER") and isinstance(value, mutation_score_mod.AdapterSpec):
                adapters[value.language] = value
                modules[value.language] = module
    return adapters, modules


ADAPTERS, MODULES = _discover_adapters()

# 어댑터·중립층·합치는 층이 뼈대에서 만질 수 있는 표면 (실측 전수).
# 이 밖의 뼈대 이름을 새로 잡으면 이 목록에 추가하고 그 사유를 코드 주석에 남긴다.
ALLOWED_GATE_SURFACE = frozenset({
    "_run", "_skip", "_tool",
    "JS_SUFFIXES", "GateContext",
    "_read_json_object", "_rel_to_repo", "detect_pytest_paths",
    # EMPTY_TREE — 고·C# 어댑터가 "비교 기준이 있는가" 를 판단할 때 쓴다. 두 도구는
    # 변경분 한정을 git ref 로 받는데(--diff / --since), 커밋이 하나도 없는 저장소에서
    # ctx.change.base 에 들어오는 빈 트리 해시를 ref 로 넘기면 도구가 거절한다.
    # 그 값을 어댑터가 문자열로 다시 적으면 뼈대와 갈린다.
    "EMPTY_TREE",
})

# 선행 항목 코드 → 그 결과가 담기는 뼈대 상태 칸. requires 선언을 소스와 맞대는 근거다.
# 새 선행 항목을 요구하는 어댑터를 붙이려면 여기부터 넓힌다 — 표에 없는 코드는 실패다.
# (리터럴 한 줄로 "python_tests_status 를 읽는가" 만 보던 때는, 선행 항목을 정직하게
#  선언한 세 번째 어댑터가 오히려 실패했다.)
BASELINE_CONTEXT_FIELDS = {"C1:python": "python_tests_status"}

# 사본을 만드는 어댑터를 소스에서 가려내는 표식.
_COPY_MARKERS = ("symlink_to(", "os.symlink(", "copytree(")

# 기록 칸 신뢰도의 허용 값. tests 칸만 단위로 답한다.
_CONFIDENCE_VALUES = frozenset({"tool", "reconstructed", "absent"})
_TESTS_CONFIDENCE_VALUES = frozenset({"per-mutant", "per-function", "absent"})

_TOOL_PROBE_RE = re.compile(r"gate\._tool\(\s*ctx\s*,\s*\"([^\"]+)\"")


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    """캐시를 tmp 로 격리한다 — 이 묶음이 사용자 캐시를 읽거나 쓰지 않게."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("cache")))


def _is_attribute_of(name, first, second, third) -> bool:
    """세 토큰이 `<name>.<이름>` 형태인가."""
    if first.type != tokenize.NAME or first.string != name:
        return False
    if second.type != tokenize.OP or second.string != ".":
        return False
    return third.type == tokenize.NAME


def _attribute_names(module, holder: str) -> set:
    """모듈 소스에서 `<holder>.<이름>` 형태의 속성 접근을 전부 모은다 (문자열·주석 제외)."""
    source = inspect.getsource(module)
    names = set()
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    for index in range(len(tokens) - 2):
        if _is_attribute_of(holder, tokens[index], tokens[index + 1], tokens[index + 2]):
            names.add(tokens[index + 2].string)
    return names


def _gate_attribute_names(module) -> set:
    return _attribute_names(module, "gate")


def _all_modules():
    return [mutation, mutation_score_mod] + sorted(MODULES.values(), key=lambda m: m.__name__)


def test_adapters_are_discovered():
    """어댑터 자동 수집이 실제로 무언가를 찾았는가 — 빈 목록이면 모든 검사가 공회전한다."""
    assert set(ADAPTERS) >= {"javascript", "python"}
    assert set(ADAPTERS) == set(MODULES)


def test_adapter_modules_follow_entry_naming():
    """어댑터 모듈은 `_check_mutation_<언어>` / `_run_mutation_<언어>` 를 갖는다."""
    for language, module in MODULES.items():
        assert hasattr(module, f"_check_mutation_{language}"), language
        assert hasattr(module, f"_run_mutation_{language}"), language


def test_status_map_values_are_gate_vocabulary():
    """변환표의 목적지는 반드시 게이트 어휘다 — 밖의 철자는 unknown 경로로 새 나간다."""
    for spec in ADAPTERS.values():
        for own_word, gate_word in spec.status_map.items():
            assert gate_word in mutation_score_mod.MUTATION_KNOWN_STATUSES, (
                spec.language, own_word, gate_word)


def test_javascript_status_map_is_applied_at_runtime():
    """자바스크립트 변환표는 여덟 이름을 덮고, 기록이 실제로 그 표를 지난다.

    표가 항등이라는 것만 못 박아 두면, 선언은 있는데 적용하는 코드가 없는 상태가
    통과한다 — 도구가 어휘를 바꾼 날 표가 아무것도 흡수하지 못한다.
    """
    spec = ADAPTERS["javascript"]
    assert set(spec.status_map) == set(mutation_score_mod.MUTATION_KNOWN_STATUSES)
    for own_word, gate_word in spec.status_map.items():
        assert mutation_javascript._gate_status(own_word) == gate_word
        record = mutation_javascript._mutant_record("a.js", {"status": own_word}, "", [])
        assert record["status"] == gate_word
    # 표 밖 낱말은 원어 그대로 통과한다 (unknown 경로가 잡아 분모에서 뺀다).
    assert mutation_javascript._gate_status("survived") == "survived"


def test_language_and_label_match_executor_part(monkeypatch):
    """선언의 language / label 은 실행부가 돌려주는 네 칸의 값과 같아야 한다."""
    fake = ({"status": "ok", "reason": "", "human_reason": ""}, None)
    for language, module in MODULES.items():
        monkeypatch.setattr(module, f"_run_mutation_{language}", lambda ctx, files: fake)
    for language, spec in ADAPTERS.items():
        part = getattr(MODULES[language], f"_check_mutation_{language}")(None, [])
        assert part["language"] == spec.language
        assert part["label"] == spec.label
        assert set(part) == {"language", "label", "summary", "outcome"}


def test_requires_matches_baseline_reads():
    """선행 항목 의존은 선언 없이 생기면 안 된다 — 표를 지나 소스와 맞대 본다."""
    for language, spec in ADAPTERS.items():
        for code in spec.requires:
            assert code in BASELINE_CONTEXT_FIELDS, (language, code)
        declared = {BASELINE_CONTEXT_FIELDS[code] for code in spec.requires}
        read = _attribute_names(MODULES[language], "ctx") & set(BASELINE_CONTEXT_FIELDS.values())
        assert declared == read, (
            f"{language}: requires={spec.requires} 인데 실제로 읽는 선행 항목 칸은 {sorted(read)}")


def test_tool_matches_availability_probe():
    """선언한 도구 이름은 그 어댑터가 실제로 있는지 묻는 이름과 같아야 한다."""
    for language, spec in ADAPTERS.items():
        probed = set(_TOOL_PROBE_RE.findall(inspect.getsource(MODULES[language])))
        assert probed == {spec.tool}, (language, sorted(probed), spec.tool)


def test_incremental_declares_its_invalidation():
    """회차를 넘겨 재사용한다고 선언했으면 무엇이 그것을 버리는지도 말해야 한다.

    "증분을 안 쓴다" 와 "아무것도 무효화하지 않는다" 가 빈 튜플 하나로 겹치면, 뒤쪽이
    조용히 통과한다 — 그 상태가 1b 의 거짓 통과 그 자체였다.
    """
    for language, spec in ADAPTERS.items():
        assert isinstance(spec.incremental, bool), language
        if spec.incremental:
            assert spec.incremental_triggers, language
        else:
            assert spec.incremental_triggers == (), language


def test_field_confidence_vocabulary():
    """기록 칸 신뢰도의 값은 정해진 낱말 안이어야 한다 — tests 칸만 단위로 답한다."""
    for language, spec in ADAPTERS.items():
        assert set(spec.field_confidence) == {"line", "column", "mutator", "tests"}, language
        for column, value in spec.field_confidence.items():
            allowed = _TESTS_CONFIDENCE_VALUES if column == "tests" else _CONFIDENCE_VALUES
            assert value in allowed, (language, column, value)


def _sample_records() -> dict:
    """어댑터별 기록 한 줄 — 도구가 줄 수 있는 것을 전부 준 입력이다."""
    return {
        "javascript": mutation_javascript._mutant_record(
            "a.js",
            {"location": {"start": {"line": 1, "column": 2}}, "mutatorName": "m",
             "status": "Survived"},
            "orig", ["t"]),
        "python": mutation_python._mutmut_record(
            "a.py", "k", "Survived", (None, "x", "y"), 3, ["t"]),
        # 자바는 리포트 XML 한 조각을 그대로 지나게 한다 — 기록을 만드는 길이 그것뿐이다.
        "java": mutation_java._pit_records(
            "<mutations><mutation status='SURVIVED'>"
            "<mutatedClass>p.A</mutatedClass><mutatedMethod>f</mutatedMethod>"
            "<lineNumber>2</lineNumber>"
            "<mutator>org.pitest.mutationtest.engine.gregor.mutators.MathMutator</mutator>"
            "<killingTest>[class:p.ATest]/[method:f()]</killingTest>"
            "<description>changed math</description>"
            "</mutation></mutations>",
            {"p.A": "a.java"}, {"a.java": ["x", "y"]})[0],
        "go": mutation_go._go_record(
            "a.go", {"line": 3, "column": 5, "type": "CONDITIONALS_NEGATION",
                     "status": "LIVED"}, ["x", "y", "z"]),
        "csharp": mutation_csharp._cs_record(
            "a.cs",
            {"location": {"start": {"line": 1, "column": 2}}, "mutatorName": "m",
             "status": "Survived"},
            "orig", ["t"]),
        # 러스트는 리포트에 원본 텍스트가 없어, 줄 목록을 함께 넘겨야 원본 자리가 찬다.
        "rust": mutation_rust._rust_record(
            "a.rs",
            {"span": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 4}},
             "genre": "BinaryOperator", "replacement": "-"},
            "MissedMutant", ["a+b"]),
    }


def test_absent_columns_are_empty_in_records():
    """absent 라고 신고한 칸은 도구가 다 줘도 비어 있어야 한다 — 반대도 마찬가지다."""
    records = _sample_records()
    missing = sorted(set(ADAPTERS) - set(records))
    assert not missing, (
        f"어댑터 {missing} 의 기록 표본이 없습니다. _sample_records 에 그 어댑터의 기록 "
        "한 줄을 추가하십시오 — absent 로 신고한 칸이 실제로 비는지 볼 근거입니다.")
    for language, spec in ADAPTERS.items():
        record = records[language]
        for column, value in spec.field_confidence.items():
            assert column in record, (language, column)
            if value == "absent":
                assert record[column] is None, (language, column, record[column])
            else:
                assert record[column] is not None, (language, column)


def test_gate_surface_is_declared():
    """뮤테이션 모듈이 만지는 뼈대 이름은 신고된 표면 안이어야 한다."""
    for module in _all_modules():
        extra = _gate_attribute_names(module) - ALLOWED_GATE_SURFACE
        assert not extra, (module.__name__, sorted(extra))


def test_adapters_do_not_spawn_subprocesses_directly():
    """서브프로세스는 뼈대의 _run 하나만 지난다 — R2 보호가 어댑터마다 갈리면 안 된다."""
    for module in _all_modules():
        source = inspect.getsource(module)
        assert "subprocess.run(" not in source, module.__name__
        assert "subprocess.Popen(" not in source, module.__name__
        assert "os.system(" not in source, module.__name__


def test_copy_limitations_match_whether_a_copy_is_made():
    """사본을 만드는 어댑터만 copy_limitations 가 차 있다 — 소스에서 사본 여부를 본다."""
    for language, spec in ADAPTERS.items():
        source = inspect.getsource(MODULES[language])
        copies = any(marker in source for marker in _COPY_MARKERS)
        assert bool(spec.copy_limitations) == copies, (
            f"{language}: 사본 {'있음' if copies else '없음'} 인데 "
            f"copy_limitations={spec.copy_limitations}")


def _imprint_env(tmp_path):
    """(ctx, work) — 저장소 노릇을 할 디렉토리와 상태 파일 자리."""
    repo = tmp_path / "repo"
    work = tmp_path / "work"
    repo.mkdir()
    work.mkdir()
    (repo / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (repo / "test_a.py").write_text("def test_f():\n    assert True\n", encoding="utf-8")
    ctx = types.SimpleNamespace(notes=[], repo_root=repo)
    return ctx, work


def _imprint_failure(ctx, work, targets, changed_tests,
                     human="사본 안에서 기준 테스트가 실패했습니다.",
                     extra=(), carried=None):
    """실패 회차를 재현한다 — 가드가 상태(지문)를 쓰고, 실패가 각인된다."""
    mutation_python._mutmut_write_state(ctx, work, targets, changed_tests, extra, carried)
    mutation_python._mutmut_imprint_failure(
        ctx, work, {"status": "error", "reason": "exit 1: not a git repository",
                    "human_reason": human})


def test_failure_imprint_suppresses_rerun_on_same_inputs(tmp_path):
    """지난 실패와 입력 지문이 같으면 기준 테스트를 다시 돌리지 않고 같은 오류를 낸다."""
    ctx, work = _imprint_env(tmp_path)
    _imprint_failure(ctx, work, ["a.py"], ["test_a.py"])

    hit = mutation_python._mutmut_imprinted_outcome(ctx, work, ["a.py"], ["test_a.py"])
    assert hit is not None
    assert hit["status"] == "error"
    assert "지난 회차와 입력이 같아 다시 돌지 않았습니다" in hit["human_reason"]
    assert "사본 안에서 기준 테스트가 실패했습니다" in hit["human_reason"]
    assert str(work) in hit["human_reason"]


def test_failure_imprint_names_the_file_to_delete(tmp_path):
    """탈출 안내는 지울 파일을 이름으로 말해야 한다.

    "사본 디렉토리를 지우십시오" 만 있으면 그 말대로 `mutants/` 를 지운 사용자에게 각인이
    그대로 남아 같은 오류가 계속 나갔다 (실측). 각인은 그 밖의 상태 파일에 산다.
    """
    ctx, work = _imprint_env(tmp_path)
    _imprint_failure(ctx, work, ["a.py"], [])

    hit = mutation_python._mutmut_imprinted_outcome(ctx, work, ["a.py"], [])
    assert hit is not None
    assert str(work / mutation_python._MUTMUT_STATE_NAME) in hit["human_reason"]


def test_failure_imprint_invalidated_by_input_changes(tmp_path):
    """각인의 무효화 — 대상 목록 / 변경분의 테스트 목록 / 그 파일들의 내용."""
    ctx, work = _imprint_env(tmp_path)
    _imprint_failure(ctx, work, ["a.py"], ["test_a.py"])

    # 대상 목록 변화 → 무효
    assert mutation_python._mutmut_imprinted_outcome(ctx, work, ["b.py"], ["test_a.py"]) is None
    # 테스트 파일 변경분 목록 변화 → 무효
    assert mutation_python._mutmut_imprinted_outcome(ctx, work, ["a.py"], []) is None
    # 내용 변화 (사용자가 테스트의 git 의존을 끊는 수정) → 무효 — 낡은 오류가 나가면 안 된다
    (ctx.repo_root / "test_a.py").write_text("def test_f():\n    assert 1 == 1\n",
                                             encoding="utf-8")
    assert mutation_python._mutmut_imprinted_outcome(ctx, work, ["a.py"], ["test_a.py"]) is None


def test_failure_imprint_invalidated_by_copy_composition(tmp_path):
    """각인은 사본 구성 변화도 본다 — 실패를 없애는 수정은 대개 파이썬 파일이 아니다.

    기준 단계 실패를 없애는 조치는 pytest.ini / setup.cfg 에서 일어난다. 그중 pytest.ini 는
    사본에 걸 이름을 실제로 정하는 파일이라 실행 결과를 바꾼다. 파이썬 파일만 보면
    사용자가 안내대로 조치해도 낡은 오류가 굳는다 (실측).
    """
    ctx, work = _imprint_env(tmp_path)
    ini = ctx.repo_root / "pytest.ini"
    ini.write_text("[pytest]\ntestpaths = tests gittests\n", encoding="utf-8")
    extra, carried = ["pytest.ini"], {"max_children": "4"}
    _imprint_failure(ctx, work, ["a.py"], [], extra=extra, carried=carried)

    # 구성이 그대로면 억제된다
    assert mutation_python._mutmut_imprinted_outcome(
        ctx, work, ["a.py"], [], extra, carried) is not None
    # 걸 이름의 내용 변화 (안내대로 문제 디렉토리를 뺀 조치) → 무효
    ini.write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    assert mutation_python._mutmut_imprinted_outcome(
        ctx, work, ["a.py"], [], extra, carried) is None
    ini.write_text("[pytest]\ntestpaths = tests gittests\n", encoding="utf-8")
    # 걸 이름 목록 변화 → 무효
    assert mutation_python._mutmut_imprinted_outcome(
        ctx, work, ["a.py"], [], [], carried) is None
    # 이어 쓴 프로젝트 설정 변화 → 무효
    assert mutation_python._mutmut_imprinted_outcome(
        ctx, work, ["a.py"], [], extra, {"max_children": "8"}) is None


def test_failure_imprint_absent_means_no_suppression(tmp_path):
    """각인이 없으면 억제하지 않는다 — 상태만 있는 정상 회차는 그대로 돈다."""
    ctx, work = _imprint_env(tmp_path)
    mutation_python._mutmut_write_state(ctx, work, ["a.py"], [])
    assert mutation_python._mutmut_imprinted_outcome(ctx, work, ["a.py"], []) is None


def test_running_round_clears_imprint(tmp_path):
    """실제로 도는 회차는 상태를 새로 써 각인을 지운다 — 각인은 억제된 회차에서만 산다."""
    ctx, work = _imprint_env(tmp_path)
    _imprint_failure(ctx, work, ["a.py"], [])
    mutation_python._mutmut_write_state(ctx, work, ["a.py"], [])
    assert mutation_python._mutmut_imprinted_outcome(ctx, work, ["a.py"], []) is None


def test_config_notes_survive_the_imprint(tmp_path, monkeypatch):
    """각인으로 억제된 회차에서도 설정을 어떻게 다뤘는지는 그대로 보고한다 (R4).

    각인이 생략하는 것은 기준 테스트 재실행이지, 이번 회차에도 참인 사실의 보고가
    아니다. 빠지면 사용자는 프로젝트의 mutmut 설정이 쓰였는지 알 수 없다.
    """
    ctx, work = _imprint_env(tmp_path)
    (ctx.repo_root / "pyproject.toml").write_text("[tool.mutmut]\n", encoding="utf-8")
    (ctx.repo_root / "setup.cfg").write_text("[mutmut]\nmax_children=4\n", encoding="utf-8")
    ctx.tmpdir = tmp_path / "tmp"
    ctx.tmpdir.mkdir()
    (ctx.repo_root / "src").mkdir()
    (ctx.repo_root / "src" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    monkeypatch.setattr(mutation_python, "mutmut_work_dir", lambda root, notes: work)
    monkeypatch.setattr(mutation_python, "_mutmut_extra_links", lambda root, roots: ([], []))
    _imprint_failure(ctx, work, ["src/a.py"], [], carried={"max_children": "4"})
    ctx.notes.clear()

    _work, _roots, blocked = mutation_python._mutmut_setup(ctx, ["src/a.py"], [])
    assert blocked is not None and blocked["status"] == "error"
    joined = " ".join(ctx.notes)
    assert "지난 회차의 실패 각인이 유효해" in joined
    assert "pyproject.toml 의 mutmut 설정은 이번 실행에 쓰지 않았습니다" in joined
    assert "setup.cfg 의 mutmut 설정" in joined


def test_python_test_list_is_sorted():
    """mutmut 의 테스트 목록은 집합이라 실행마다 순서가 달라진다 — 정렬해 고정한다.

    고정하지 않으면 같은 입력에 같은 출력이 나오지 않아, 재구성 뒤 동작이 같은지를
    기계로 확인할 수 없다. 실측에서 같은 코드를 3회 돌려 네 개의 테스트 이름이
    매번 다른 순서로 나왔다. 순서 자체에는 뜻이 없다.
    """
    from scripts.mutation.python import _mutmut_record

    unsorted = ["tests/t.py::가", "tests/t.py::나", "tests/t.py::다"]
    record = _mutmut_record("src/a.py", "k", "Survived", (None, "x", "y"), 3,
                            reversed(unsorted))
    assert record["tests"] == sorted(unsorted)


def test_javascript_test_list_keeps_tool_order():
    """자바스크립트는 도구가 배열로 준 순서를 그대로 둔다.

    Stryker 의 coveredBy 는 배열이라 순서가 이미 일정하다. 여기까지 정렬하면
    도구가 준 순서를 게이트가 임의로 바꾸는 것이라 출력이 실제로 달라진다.
    """
    from scripts.mutation.javascript import _mutant_record

    given = ["나", "가", "다"]
    record = _mutant_record("src/a.js", {"location": {"start": {"line": 1, "column": 2}}},
                            "orig", given)
    assert record["tests"] == given


# ---------------------------------------------------------------------------
# 레지스트리 — 런타임 어댑터 목록과 선언부의 소비 (1d)
# ---------------------------------------------------------------------------

def test_registry_matches_discovered_adapters():
    """런타임 레지스트리와 자동 수집이 같은 어댑터를 같은 순서로 본다.

    둘이 갈리면 계약 테스트가 보는 어댑터와 게이트가 실제로 돌리는 어댑터가 달라진다 —
    검사를 통과한 선언이 아무 데도 쓰이지 않는 상태다.
    """
    registry = mutation.adapters()
    assert [adapter.language for adapter in registry] == sorted(ADAPTERS)
    for adapter in registry:
        assert adapter.spec is ADAPTERS[adapter.language]
        assert adapter.module is MODULES[adapter.language]


def test_registry_entry_points_are_reachable():
    """레지스트리가 이름으로 찾는 진입점이 실제로 있어야 한다 (변경분 산출 + 실행)."""
    for language, module in MODULES.items():
        assert hasattr(module, f"_mutation_changed_{language}"), language
        assert hasattr(module, f"_check_mutation_{language}"), language


def test_registry_entry_points_are_looked_up_at_call_time(monkeypatch):
    """진입점을 값으로 붙잡아 두면 실행 중 교체가 조용히 무시된다."""
    language = sorted(ADAPTERS)[0]
    adapter = next(a for a in mutation.adapters() if a.language == language)
    monkeypatch.setattr(MODULES[language], f"_mutation_changed_{language}", lambda ctx: ["바꿔치기"])
    assert adapter.changed_files(None) == ["바꿔치기"]


def test_config_key_is_the_seat_the_loader_reads(tmp_path):
    """선언한 설정 자리에 넣은 값이 그 어댑터의 도구 이름으로 읽혀야 한다.

    이 검사가 없을 때는 config_key 를 거짓으로 적어도 22건이 전부 통과했다 (실측).
    자리 이름은 `mutation.<언어>` 로 고정한다 — 자리와 언어가 갈리면 설정 파일을 읽는
    쪽과 결과를 내는 쪽이 서로 다른 이름을 부른다.
    """
    for language, spec in ADAPTERS.items():
        block, _, leaf = spec.config_key.partition(".")
        assert (block, leaf) == ("mutation", language), (language, spec.config_key)
        path = tmp_path / f"{language}.json"
        path.write_text(json.dumps({"mutation": {leaf: "다른도구"}}), encoding="utf-8")
        config = code_gate.load_config(path)
        assert config.mutation_tool(language) == "다른도구", language
        assert not [note for note in config.notes if "알 수 없는 키" in note], config.notes


def test_declared_tool_is_the_config_default_and_the_supported_value(tmp_path):
    """선언한 도구 이름이 설정 기본값이고, 다른 값이 오면 그 어댑터가 건너뛴다."""
    config = code_gate.load_config(tmp_path / "없는파일.json")
    for language, spec in ADAPTERS.items():
        assert config.mutation_tool(language) == spec.tool, language
        assert getattr(config, f"mutation_{language}") == spec.tool, language

    path = tmp_path / "다른도구.json"
    for adapter in mutation.adapters():
        path.write_text(json.dumps({"mutation": {adapter.language: "다른도구"}}), encoding="utf-8")
        # tools 를 빈 사전으로 준다 — 설정 값이 어긋나면 도구 조회 앞에서 돌아서므로,
        # 여기까지 내려오면 그 자체가 선언과 동작이 갈렸다는 신호다.
        ctx = types.SimpleNamespace(config=code_gate.load_config(path), tools={})
        outcome = adapter.check(ctx, [])["outcome"]
        assert outcome["status"] == "skipped", adapter.language
        assert adapter.spec.config_key in outcome["human_reason"], (
            f"{adapter.language}: 설정 값이 어긋났는데 그 사실을 말하지 않는다 — "
            f"어댑터는 도구를 찾기 전에 config_key 자리의 값부터 본다")


def test_a_new_adapter_opens_its_config_seat(monkeypatch, tmp_path):
    """세 번째 언어를 등록하면 그 설정 자리가 곧바로 열린다.

    뼈대가 두 언어를 박아 두었을 때는 `.code-gate.json` 의 mutation 에 새 언어를 넣으면
    "알 수 없는 키" 로 버려졌다 (실측). 어댑터 파일 없이 레지스트리만 넓혀 확인한다.
    """
    spec = dataclasses.replace(ADAPTERS["python"], language="가짜언어", label="가짜",
                               tool="가짜도구", config_key="mutation.가짜언어")
    extra = mutation.Adapter(spec=spec, module=None)
    monkeypatch.setattr(mutation, "_registry", mutation.adapters() + (extra,))

    path = tmp_path / ".code-gate.json"
    path.write_text(json.dumps({"mutation": {"가짜언어": "다른도구"}}), encoding="utf-8")
    config = code_gate.load_config(path)
    assert config.mutation_tool("가짜언어") == "다른도구"
    assert not [note for note in config.notes if "알 수 없는 키" in note], config.notes

    # 값을 안 주면 선언한 도구 이름이 기본값이다
    empty = tmp_path / "빈설정.json"
    empty.write_text(json.dumps({"mutation": {}}), encoding="utf-8")
    assert code_gate.load_config(empty).mutation_tool("가짜언어") == "가짜도구"


def test_unknown_mutation_key_is_still_reported(tmp_path):
    """등록되지 않은 이름은 그대로 알린다 — 오타를 조용히 버리면 원인을 못 찾는다."""
    path = tmp_path / ".code-gate.json"
    path.write_text(json.dumps({"mutation": {"등록안된언어": "무엇"}}), encoding="utf-8")
    config = code_gate.load_config(path)
    assert [note for note in config.notes if "알 수 없는 키" in note]

def test_report_survives_a_broken_registry(monkeypatch):
    """어댑터 모듈 하나가 import 되지 않아도 리포트 골격은 나가야 한다 (R2).

    크래시 경로의 리포트가 레지스트리를 다시 부르다 또 터지면 "무슨 일이 있어도 종료
    코드 0" 이 깨진다. 실측으로 확인한 자리다 — 깨진 어댑터 파일을 넣고 게이트를 돌리면
    JSON 과 사람용 표 모두 종료 코드 0 으로 오류를 싣는다.
    """
    def broken():
        raise ImportError("어댑터 모듈이 깨졌다")

    monkeypatch.setattr(mutation, "adapters", broken)
    payload = code_gate._config_payload(None)
    assert payload["mutation"]["enabled"] is code_gate.DEFAULT_MUTATION_ENABLED
    assert not [key for key in payload["mutation"] if key in ADAPTERS]


# ---------------------------------------------------------------------------
# 도구 탐지와 설치 안내 — R4 (도구가 없으면 건너뛰되 반드시 보고)
# ---------------------------------------------------------------------------

def _tools_with_nothing_installed(monkeypatch, tmp_path) -> dict:
    """아무 도구도 깔려 있지 않은 기계의 탐지 결과. 이 기계에 무엇이 깔렸는지와 무관해진다."""
    monkeypatch.setattr(code_gate.shutil, "which", lambda name: None)
    monkeypatch.setattr(code_gate, "_probe_python_modules",
                        lambda root, exe, modules, timeout: {name: False for name in modules})
    # PATH 밖 자리(`~/.cargo/bin`)도 함께 막는다. 이것을 빼면 이 기계에 실제로 깔린
    # 도구가 "아무것도 안 깔린 기계" 를 흉내 내는 도중에 튀어나와, 위 docstring 의
    # 약속이 깨진다.
    monkeypatch.setattr(code_gate, "_cargo_bin_path", lambda name: None)
    return code_gate.probe_tools(tmp_path, "python3")


def test_every_adapter_tool_is_probed(monkeypatch, tmp_path):
    """어댑터가 묻는 도구 이름이 탐지 표에 있어야 한다.

    표에 이름이 없으면 `_tool` 이 늘 "없음" 을 돌려줘, 도구가 깔려 있는데도 그 언어가
    영영 건너뛰어진다. 두 언어를 손으로 적어 두던 때 세 번째 언어가 정확히 그렇게 막혔다.
    """
    tools = _tools_with_nothing_installed(monkeypatch, tmp_path)
    missing = sorted(spec.tool for spec in ADAPTERS.values() if spec.tool not in tools)
    assert not missing, f"탐지 표에 없는 어댑터 도구: {missing}"


def test_missing_tool_skip_reports_how_to_install(monkeypatch, tmp_path):
    """도구가 없으면 건너뛰되 **설치 방법을 반드시 낸다** (R4). 조용한 통과도, 빈 안내도 안 된다."""
    tools = _tools_with_nothing_installed(monkeypatch, tmp_path)
    config = code_gate.load_config(tmp_path / "없는설정.json")
    for adapter in mutation.adapters():
        ctx = types.SimpleNamespace(config=config, tools=tools, repo_root=tmp_path, notes=[])
        outcome = adapter.check(ctx, ["바뀐파일"])["outcome"]
        assert outcome["status"] == "skipped", (adapter.language, outcome)
        assert outcome.get("install_hint"), (
            f"{adapter.language}: 도구가 없다고만 하고 설치 방법을 내지 않는다 (R4)")


def test_no_target_sentence_names_every_adapter(monkeypatch):
    """"대상이 없다" 안내는 등록된 어댑터를 전부 말해야 한다.

    문장에 언어를 손으로 적어 두면 어댑터를 더할 때마다 뒤처져, 사용자가 자기 언어를
    게이트가 아예 모른다고 읽는다.
    """
    config = types.SimpleNamespace(mutation_enabled=True)
    ctx = types.SimpleNamespace(config=config, notes=[])
    blocked = mutation._mutation_preconditions(ctx, [(a, []) for a in mutation.adapters()])
    assert blocked["status"] == "skipped"
    for adapter in mutation.adapters():
        assert adapter.target_note in blocked["human_reason"], adapter.language


def test_merged_head_does_not_hardcode_the_number_of_languages():
    """언어가 셋을 넘어도 머리말이 거짓이 되지 않아야 한다.

    "두 언어를 합쳐도 …" 라고 박아 두었을 때는 어댑터가 늘어난 순간 문장이 거짓이 됐다.
    """
    parts = [{"label": "고", "summary": None, "language": "go",
              "outcome": {"status": "skipped"}},
             {"label": "C#", "summary": None, "language": "csharp",
              "outcome": {"status": "skipped"}}]
    ctx = types.SimpleNamespace(config=types.SimpleNamespace(mutation_score_threshold=80.0))
    head = mutation._mutation_merged_head(ctx, parts, {}, [])
    assert "두 언어" not in head
    assert head == "어느 언어도 재지 못했습니다 (고, C#)."


def test_merged_install_hints_keep_every_language(monkeypatch, tmp_path):
    """도구가 여럿 없으면 설치 방법도 여럿 나가야 한다 (R4).

    하나만 남기던 때는 뒤 언어의 안내가 말없이 사라졌다.
    """
    parts = [{"label": "가", "outcome": {"install_hint": "첫째 설치"}},
             {"label": "나", "outcome": {"install_hint": "둘째 설치"}},
             {"label": "다", "outcome": {"install_hint": "첫째 설치"}},
             {"label": "라", "outcome": {}}]
    _findings, hint = mutation._mutation_merged_findings(parts)
    # 여럿이면 어느 언어의 안내인지 앞에 붙인다. 그냥 이어 붙이면 안내 자체에 든 빗금
    # (`@stryker-mutator/core`)과 구분이 안 되고, 복사해 붙여도 실행되지 않는다 (확정 13).
    assert hint == "가: 첫째 설치 · 나: 둘째 설치"


def test_a_single_install_hint_stays_exactly_as_the_adapter_wrote_it():
    """하나뿐이면 언어 이름을 붙이지 않는다 — 지금까지의 출력이 그대로여야 한다."""
    parts = [{"label": "자바스크립트",
              "outcome": {"install_hint": "npm i -D @stryker-mutator/core"}},
             {"label": "파이썬", "outcome": {}}]
    _findings, hint = mutation._mutation_merged_findings(parts)
    assert hint == "npm i -D @stryker-mutator/core"


def test_budget_order_counts_only_the_adapters_that_run(monkeypatch):
    """예산 순서는 **이번에 도는** 어댑터 사이에서 매긴다.

    등록 순서로 매기면, 변경분이 없어 돌지도 않는 앞 어댑터 때문에 첫 주자가 예산 검사에
    걸린다 — 어댑터를 더할 때마다 기존 언어가 조용히 뒤로 밀리는 회귀 자리다.
    """
    seen: list = []

    def spy(ctx, adapter, files, order, budget):
        seen.append((adapter.language, order))
        return {"language": adapter.language, "label": adapter.label,
                "summary": None, "outcome": {"status": "ok"}}

    monkeypatch.setattr(mutation, "_mutation_part", spy)
    last = mutation.adapters()[-1]
    monkeypatch.setattr(mutation, "_mutation_preconditions", lambda ctx, changed: None)
    ctx = types.SimpleNamespace(
        config=types.SimpleNamespace(mutation_enabled=True, mutation_timeout_seconds=600,
                                     mutation_score_threshold=80.0,
                                     # 마지막 어댑터가 기본 꺼짐일 수도 있다 (자바·러스트).
                                     # 켜 두지 않으면 이 검사가 "돌 어댑터가 없다" 로 바뀌어,
                                     # 예산 순서를 확인하지 못한 채 통과한다.
                                     mutation_languages_on=frozenset({last.language})),
        notes=[], mutation_deadline=None)
    monkeypatch.setattr(mutation.Adapter, "changed_files",
                        lambda self, ctx: ["파일"] if self is last else [])
    mutation.check_mutation(ctx)
    assert seen == [(last.language, 0)]
