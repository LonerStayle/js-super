"""어댑터 계약 테스트 — 선언부(AdapterSpec)와 동작의 일치 (1c).

기존 code_gate 테스트와 별개의 신규 묶음이다. 선언부는 런타임 분기를 만들지 않는
대신, 선언이 거짓이면 여기서 잡는다.

검증 시나리오:
1. status_map 의 값 전부가 게이트 어휘 여덟 이름 안에 있다.
2. 선언의 language / label 이 실행부가 돌려주는 네 칸과 같다.
3. requires 가 비어 있지 않은 어댑터만 선행 항목 상태(python_tests_status)를 읽는다.
4. 어댑터가 만지는 뼈대 표면이 신고된 목록 안에 있다 (새 이름을 잡으면 여기 추가).
5. 어댑터는 서브프로세스를 직접 부르지 않는다 — 뼈대의 gate._run 만 쓴다.
6. 사본을 만들지 않는 어댑터는 copy_limitations 가 빈 튜플이다.
7. 실패 각인 — 입력이 같으면 즉시 같은 오류, 무효화는 증분 무효화 조건을 재사용.
"""

import io
import inspect
import tokenize
import types

from scripts import code_gate
from scripts import mutation
from scripts.mutation import javascript as mutation_javascript
from scripts.mutation import python as mutation_python
from scripts.mutation import score as mutation_score_mod

ADAPTERS = {
    "javascript": mutation_javascript.JAVASCRIPT_ADAPTER,
    "python": mutation_python.PYTHON_ADAPTER,
}
MODULES = {
    "javascript": mutation_javascript,
    "python": mutation_python,
}

# 어댑터·중립층·합치는 층이 뼈대에서 만질 수 있는 표면 (실측 전수).
# 이 밖의 뼈대 이름을 새로 잡으면 이 목록에 추가하고 그 사유를 코드 주석에 남긴다.
ALLOWED_GATE_SURFACE = frozenset({
    "_run", "_skip", "_tool",
    "JS_SUFFIXES", "GateContext",
    "_read_json_object", "_rel_to_repo", "detect_pytest_paths",
})


def _is_gate_attribute(first, second, third) -> bool:
    """세 토큰이 `gate.<이름>` 형태인가."""
    if first.type != tokenize.NAME or first.string != "gate":
        return False
    if second.type != tokenize.OP or second.string != ".":
        return False
    return third.type == tokenize.NAME


def _gate_attribute_names(module) -> set:
    """모듈 소스에서 `gate.<이름>` 형태의 속성 접근을 전부 모은다 (문자열·주석 제외)."""
    source = inspect.getsource(module)
    names = set()
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    for index in range(len(tokens) - 2):
        if _is_gate_attribute(tokens[index], tokens[index + 1], tokens[index + 2]):
            names.add(tokens[index + 2].string)
    return names


def test_status_map_values_are_gate_vocabulary():
    """변환표의 목적지는 반드시 게이트 어휘다 — 밖의 철자는 unknown 경로로 새 나간다."""
    for spec in ADAPTERS.values():
        for own_word, gate_word in spec.status_map.items():
            assert gate_word in mutation_score_mod.MUTATION_KNOWN_STATUSES, (
                spec.language, own_word, gate_word)


def test_javascript_status_map_is_identity():
    """자바스크립트 변환표는 항등이고 여덟 이름을 전부 명시한다."""
    spec = ADAPTERS["javascript"]
    assert set(spec.status_map) == set(mutation_score_mod.MUTATION_KNOWN_STATUSES)
    for own_word, gate_word in spec.status_map.items():
        assert own_word == gate_word


def test_language_and_label_match_executor_part(monkeypatch):
    """선언의 language / label 은 실행부가 돌려주는 네 칸의 값과 같아야 한다."""
    fake = ({"status": "ok", "reason": "", "human_reason": ""}, None)
    monkeypatch.setattr(mutation_javascript, "_run_mutation_javascript",
                        lambda ctx, files: fake)
    monkeypatch.setattr(mutation_python, "_run_mutation_python",
                        lambda ctx, files: fake)
    parts = {
        "javascript": mutation_javascript._check_mutation_javascript(None, []),
        "python": mutation_python._check_mutation_python(None, []),
    }
    for language, part in parts.items():
        spec = ADAPTERS[language]
        assert part["language"] == spec.language
        assert part["label"] == spec.label
        assert set(part) == {"language", "label", "summary", "outcome"}


def test_requires_matches_baseline_reads():
    """선행 항목 의존은 선언 없이 생기면 안 된다 — 소스와 선언을 맞대 본다."""
    for language, spec in ADAPTERS.items():
        source = inspect.getsource(MODULES[language])
        reads_baseline = "python_tests_status" in source
        assert bool(spec.requires) == reads_baseline, (
            f"{language}: requires={spec.requires} 인데 "
            f"선행 항목 상태 읽기 {'있음' if reads_baseline else '없음'}")


def test_gate_surface_is_declared():
    """뮤테이션 모듈이 만지는 뼈대 이름은 신고된 표면 안이어야 한다."""
    for module in (mutation, mutation_score_mod, mutation_javascript, mutation_python):
        extra = _gate_attribute_names(module) - ALLOWED_GATE_SURFACE
        assert not extra, (module.__name__, sorted(extra))


def test_adapters_do_not_spawn_subprocesses_directly():
    """서브프로세스는 뼈대의 _run 하나만 지난다 — R2 보호가 어댑터마다 갈리면 안 된다."""
    for module in (mutation, mutation_score_mod, mutation_javascript, mutation_python):
        source = inspect.getsource(module)
        assert "subprocess.run(" not in source, module.__name__
        assert "subprocess.Popen(" not in source, module.__name__
        assert "os.system(" not in source, module.__name__


def test_no_copy_no_copy_limitations():
    """사본을 만들지 않는 어댑터의 copy_limitations 는 빈 튜플이다."""
    assert ADAPTERS["javascript"].copy_limitations == ()
    assert ADAPTERS["python"].copy_limitations != ()


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
                     human="사본 안에서 기준 테스트가 실패했습니다."):
    """실패 회차를 재현한다 — 가드가 상태(지문)를 쓰고, 실패가 각인된다."""
    mutation_python._mutmut_write_state(ctx, work, targets, changed_tests)
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


def test_failure_imprint_invalidated_by_incremental_triggers(tmp_path):
    """각인의 무효화는 증분 무효화 선언(incremental_triggers)의 세 조건을 그대로 쓴다."""
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
