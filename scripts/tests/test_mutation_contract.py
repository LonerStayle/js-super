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
"""

import importlib
import io
import inspect
import pkgutil
import re
import tokenize
import types

import pytest

from scripts import code_gate
from scripts import mutation
from scripts.mutation import javascript as mutation_javascript
from scripts.mutation import python as mutation_python
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
