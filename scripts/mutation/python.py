"""C7 뮤테이션 — 파이썬 어댑터 (mutmut).

자바스크립트(Stryker) 어댑터와 같은 계약(네 칸 사전)을 내지만 내부 단계는 다르다 —
규격은 단계를 강제하지 않는다 (두 도구의 단계가 실제로 전부 달랐다).

이 어댑터의 사실관계는 mutmut 3.7.0 을 실물로 돌려 확인한 것이다. 구현을 좌우한 것 넷.
  - mutmut 은 사본 디렉토리 `mutants/` 를 **현재 작업 디렉토리** 아래에 만든다. 작업
    디렉토리를 사용자 캐시로 잡고 소스·테스트를 심링크로 걸면 대상 프로젝트에는
    `__pycache__` 하나도 생기지 않는다 (D3).
  - 소스 루트와 변경분 한정을 명령줄로 받지 않는다. 설정 파일이 한 개 반드시 필요하다.
  - 변이의 파일 안 줄·열과 변이 종류 이름을 주지 않는다. 열은 어떤 방법으로도 못 얻어
    빈 자리로 둔다. 줄은 생성된 사본과 원본을 견줘 되짚되, 가릴 수 없으면 비운다 (D2).
  - 집계 JSON(`mutmut-cicd-stats.json`)은 중단된 회차에서 총계와 버킷 합이 어긋난다.
    그래서 파일별 `.meta` 를 직접 읽는다 — "몇 개 중 몇 개" 의 두 숫자가 같은 곳에서 나온다 (D4).

서브프로세스는 뼈대의 `gate._run` 만 쓴다. 형제 어댑터(javascript)는 import 하지 않는다.
"""

from __future__ import annotations

import ast
import configparser
import difflib
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from scripts import code_gate as gate
from scripts.mutation import score as score_mod

# ---------------------------------------------------------------------------
# C7 — 파이썬 뮤테이션 (mutmut)
#
# 자바스크립트(Stryker) 경로와 **일부러 나란히** 둔다. 공통층을 지금 뽑으면 규격이 두 도구
# 중 하나에 맞춰지고, 그 규격이 나머지 하나를 왜곡한다. 두 경로의 중복이 다음 단계가 읽을
# 자료다. 다만 아래 셋은 이미 언어 중립이라 그대로 쓴다 (복제하지 않는다).
#   mutation_score / summarize_mutants / unknown_mutant_statuses
# 그래서 mutmut 의 상태 어휘는 **여기서** 게이트 어휘로 바꾼 뒤에 넘긴다.
#
# 이 경로의 사실관계는 mutmut 3.7.0 을 실물로 돌려 확인한 것이다. 구현을 좌우한 것 넷.
#   - mutmut 은 사본 디렉토리 `mutants/` 를 **현재 작업 디렉토리** 아래에 만든다. 작업
#     디렉토리를 사용자 캐시로 잡고 소스·테스트를 심링크로 걸면 대상 프로젝트에는
#     `__pycache__` 하나도 생기지 않는다 (D3).
#   - 소스 루트와 변경분 한정을 명령줄로 받지 않는다. 설정 파일이 한 개 반드시 필요하다.
#   - 변이의 파일 안 줄·열과 변이 종류 이름을 주지 않는다. 열은 어떤 방법으로도 못 얻어
#     빈 자리로 둔다. 줄은 생성된 사본과 원본을 견줘 되짚되, 가릴 수 없으면 비운다 (D2).
#   - 집계 JSON(`mutmut-cicd-stats.json`)은 중단된 회차에서 총계와 버킷 합이 어긋난다.
#     그래서 파일별 `.meta` 를 직접 읽는다 — "몇 개 중 몇 개" 의 두 숫자가 같은 곳에서 나온다 (D4).
# ---------------------------------------------------------------------------

# C7 만의 파이썬 대상 확장자. PY_SUFFIXES 를 대신 쓰지 않는 이유는 그 상수를 C1·C6 이 함께
# 쓰기 때문이다 — JS_SUFFIXES 를 안 넓힌 것과 같은 이유다.
MUTATION_PY_SUFFIXES = frozenset({".py"})

# mutmut 상태 어휘 → 게이트 어휘 (D1). 변환은 반드시 이 어댑터 안에서 끝낸다.
MUTMUT_STATUS_TO_GATE = {
    "killed": "Killed",
    "timeout": "Timeout",
    "survived": "Survived",
    "no tests": "NoCoverage",
    "skipped": "Ignored",
    "not checked": "Pending",
    "check was interrupted by user": "Pending",
    "segfault": "RuntimeError",
}
# `suspicious` 와 `caught by type check` 는 실물을 만들어 보지 못해 대응을 정하지 않았다.
# 짐작으로 넣으면 잘못 센다. 그대로 두면 unknown_mutant_statuses 가 이름을 적어 낸다 (R4).

# `.meta` 의 exit_code_by_key 값 → mutmut 상태. mutmut 3.7.0 의 status_by_exit_code 그대로다.
# -24 가 원본 딕셔너리에 두 번 나오는데 뒤의 timeout 이 이긴다 (실측에서 무한루프 변이가 -24).
MUTMUT_EXIT_CODE_TO_STATUS = {
    1: "killed", 3: "killed",
    0: "survived",
    5: "no tests", 33: "no tests",
    34: "skipped",
    35: "suspicious",
    36: "timeout", 24: "timeout", -24: "timeout", 152: "timeout", 255: "timeout",
    37: "caught by type check",
    2: "check was interrupted by user",
    -11: "segfault", -9: "segfault",
}

# 클래스 안 메서드의 망글링 이름은 `xǁ<클래스>ǁ<메서드>__mutmut_N` 이다 (U+01C1).
MUTMUT_CLASS_SEPARATOR = "ǁ"
_MUTMUT_INDEX_RE = re.compile(r"^(?P<prefix>.+)__mutmut_(?P<index>\d+)$")
# 파이썬 테스트 파일 이름 규약 — 변이시켜도 얻을 것이 없다.
# 자바스크립트 쪽 목록(_MUTATION_TEST_DIRS / _MUTATION_TEST_STEMS)과 **일부러 다르다**.
# `spec` / `__mocks__` / `_spec` 은 자바스크립트 관례라, 사양 문서를 다루는 파이썬 소스가
# 그 이름을 쓰면 소스가 테스트로 오분류돼 검사에서 통째로 빠진다 (실측: src/spec/parser.py 가
# "테스트·삭제된 파일" 로 보고되며 한 번도 변이되지 않았다).
_MUTMUT_TEST_PREFIXES = ("test_",)
_MUTMUT_TEST_STEMS = ("_test",)
_PYTHON_TEST_DIRS = frozenset({"test", "tests"})
# 작업 디렉토리에서 mutmut 이 쓰는 이름. 프로젝트에 같은 이름의 최상위 디렉토리가 있으면
# 사본과 원본이 겹쳐 결과를 믿을 수 없다.
_MUTMUT_RESERVED_ROOTS = frozenset({"mutants", "setup.cfg"})
# 작업 디렉토리 안에 만들 수 없는 이름. 도구가 쓰는 이름에 자기 자신·상위·빈 이름을 더한 것이다.
_MUTMUT_BAD_LINK_NAMES = _MUTMUT_RESERVED_ROOTS | frozenset({"", ".", ".."})


def mutmut_status(exit_code) -> str:
    """`.meta` 의 종료 코드 → mutmut 상태 이름. null 은 아직 안 돈 변이다.

    모르는 코드는 이름을 지어내지 않고 코드를 그대로 실어 보낸다. 그 값은 게이트 어휘
    어디에도 없으므로 unknown_mutant_statuses 가 잡아 결과 문장에 적는다 (R4).
    """
    if exit_code is None:
        return "not checked"
    try:
        code = int(exit_code)
    except (TypeError, ValueError):
        return f"unknown exit code {exit_code!r}"
    return MUTMUT_EXIT_CODE_TO_STATUS.get(code, f"unknown exit code {code}")


def mutmut_gate_status(word: str) -> str:
    """mutmut 어휘 → 게이트 어휘. 모르는 어휘는 그대로 둔다 (조용히 삼키지 않는다)."""
    return MUTMUT_STATUS_TO_GATE.get(word, word)


def _mutmut_method_name(mangled: str) -> tuple:
    """`xǁ<클래스>ǁ<이름>` 을 (클래스, 이름) 으로. 모양이 어긋나면 (None, None)."""
    parts = mangled.split(MUTMUT_CLASS_SEPARATOR)
    if len(parts) != 3:
        return None, None
    if not parts[1] or not parts[2]:
        return None, None
    return parts[1], parts[2]


def mutmut_function_name(mangled: str) -> tuple:
    """망글링된 함수 이름 → (클래스 이름 | None, 함수 이름). 모양이 어긋나면 (None, None).

    모듈 함수는 `x_<이름>`, 메서드는 `xǁ<클래스>ǁ<이름>` 이다.
    """
    if MUTMUT_CLASS_SEPARATOR in mangled:
        return _mutmut_method_name(mangled)
    if not mangled.startswith("x_") or len(mangled) <= 2:
        return None, None
    return None, mangled[2:]


def mutmut_def_lines(source: str) -> dict:
    """원본 파일의 함수 정의 줄 — {(클래스 이름 | None, 함수 이름): [줄 번호, ...]}.

    이름이 겹치면 목록이 길어진다. 그때는 어느 쪽인지 가릴 수 없어 호출자가 줄을 비운다 —
    틀린 줄을 적으면 사용자가 없는 자리를 찾으러 간다 (D2).
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return {}
    found: dict = {}
    stack = [(tree, None)]
    while stack:
        node, class_name = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                stack.append((child, child.name))
                continue
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.setdefault((class_name, child.name), []).append(child.lineno)
            stack.append((child, class_name))
    return found


# 망글링된 함수 이름을 원래 이름으로 되돌리는 자리. `x_<이름>__mutmut_3` 과
# `xǁ<클래스>ǁ<이름>__mutmut_orig` 두 모양을 모두 잡는다.
_MUTMUT_MANGLED_RE = re.compile(
    "x(?:" + MUTMUT_CLASS_SEPARATOR + "[^" + MUTMUT_CLASS_SEPARATOR + "]+"
    + MUTMUT_CLASS_SEPARATOR + r"|_)(?P<name>\w+)__mutmut_(?:orig|\d+)")


def _mutmut_demangle(line: str) -> str:
    """사본의 함수 이름을 원본 이름으로 되돌린 줄. 다른 줄에는 아무 영향이 없다."""
    return _MUTMUT_MANGLED_RE.sub(lambda m: m.group("name"), line)


def _mutmut_demangle_lines(lines) -> list:
    """줄 목록 전체를 원본 이름으로 되돌린다. 본문 줄에는 아무 영향이 없다."""
    return [_mutmut_demangle(line) for line in lines]


def _mutmut_single_change(orig, mutant):
    """다른 자리가 정확히 한 군데면 (i1, i2, j1, j2), 아니면 None."""
    matcher = difflib.SequenceMatcher(a=orig, b=mutant, autojunk=False)
    changes = [op for op in matcher.get_opcodes() if op[0] != "equal"]
    if len(changes) != 1:
        return None
    return changes[0][1:]


def mutmut_change(orig_lines, mutant_lines) -> tuple:
    """원본 함수와 변이 함수를 견줘 (함수 기준 줄 번호(0부터), 원본, 바뀐 것).

    mutmut 은 원본 텍스트도 바뀐 텍스트도 주지 않는다. 대신 생성된 사본 안에 원본 함수와
    변이 함수가 나란히 들어 있어, 둘을 견주면 `mutmut show` 와 같은 것을 얻는다 — 변이마다
    프로세스를 하나씩 띄우지 않고서다 (R1).
    함수 이름 줄은 언제나 다르다 (`__mutmut_orig` 대 `__mutmut_8`). 그대로 견주면 이름
    차이와 진짜 변이가 한 덩어리로 붙어 자리를 가릴 수 없다. 그래서 이름을 원래 것으로
    되돌린 뒤에 견준다 — 줄을 떼어 내면 `def` 줄 자체가 바뀐 변이(기본 인자값, 한 줄 def)를
    통째로 잃는다. 실측에서 그 변이들이 세 칸을 모두 비운 채 나갔다.
    남은 덩어리가 한 군데가 아니면 자리를 가릴 수 없어 빈 자리로 돌려준다.
    """
    if not orig_lines or not mutant_lines:
        return None, "", ""
    orig = _mutmut_demangle_lines(orig_lines)
    mutant = _mutmut_demangle_lines(mutant_lines)
    place = _mutmut_single_change(orig, mutant)
    if place is None:
        return None, "", ""
    i1, i2, j1, j2 = place
    return i1, "\n".join(orig[i1:i2]), "\n".join(mutant[j1:j2])


_MUTMUT_DEF_RE = re.compile(r"^\s*(async\s+)?def\s")

# 데코레이터가 붙어도 mutmut 이 변이시키는 예외 둘. 이 둘만 단독으로 붙어 있을 때다.
_MUTMUT_MUTABLE_DECORATORS = frozenset({"staticmethod", "classmethod"})


def _decorator_name(node) -> str:
    """데코레이터 표현식에서 이름만. `@a.b(c)` 는 `b` 로 본다."""
    while isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else ""


def _mutmut_skips(node, inherited: bool = False) -> bool:
    """이 함수 하나를 mutmut 이 건너뛰는가 (데코레이터 규칙, mutmut 3.7.0).

    `inherited` 는 데코레이터가 붙은 클래스 안이라는 뜻이다 — 그 안은 전부 건너뛴다.
    """
    if inherited:
        return True
    decorators = node.decorator_list
    if not decorators:
        return False
    if len(decorators) == 1 and _decorator_name(decorators[0]) in _MUTMUT_MUTABLE_DECORATORS:
        return False
    return True


def _walk_for_skips(frame, stack: list, skipped: list) -> None:
    """자식 노드 한 겹을 훑어 건너뛴 함수를 모으고 나머지를 스택에 넣는다.

    중첩 함수는 바깥 함수의 일부라 따로 세지 않는다 — 함수 안으로는 내려가지 않는다.
    """
    node, prefix, inherited = frame
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            stack.append((child, f"{prefix}{child.name}.",
                          inherited or bool(child.decorator_list)))
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _mutmut_skips(child, inherited):
                skipped.append(f"{prefix}{child.name}")
        else:
            stack.append((child, prefix, inherited))


def python_decorated_skips(source: str) -> tuple:
    """mutmut 이 데코레이터 때문에 변이를 만들지 않는 함수 이름들. 파싱 실패면 빈 값.

    mutmut 3.7.0 은 데코레이터가 붙은 함수를 통째로 건너뛰고(단독 `@staticmethod` /
    `@classmethod` 만 예외), 데코레이터가 붙은 클래스는 그 안을 전부 건너뛴다.
    파일 단위 안전망(_missing_target_note)의 아래로 빠지는 자리다 — 파일 안에 변이 가능한
    함수가 하나만 있어도 그 파일은 "쟀다" 로 분류된다. 실측에서 커버리지 79% 인 파일이
    뮤테이션 100% 통과로 나갔고, 금액 계산 함수 셋이 한 번도 변이되지 않았다.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return ()
    skipped: list = []
    stack = [(tree, "", False)]
    while stack:
        _walk_for_skips(stack.pop(), stack, skipped)
    return tuple(sorted(skipped))


def _mutmut_span_bounds(spans: dict, name: str, limit: int):
    """`.spans` 항목 하나를 (시작 줄, 끝 줄) 로. 모양이 어긋나거나 범위 밖이면 None."""
    span = (spans.get("spans") or {}).get(name)
    try:
        start, end = int(span[0]), int(span[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    if 1 <= start <= end <= limit:
        return start, end
    return None


def _mutmut_span(lines, spans: dict, name: str) -> list:
    """생성된 사본에서 함수 하나의 줄 목록. `.spans` 는 1부터 세고 끝을 포함한다.

    `def` 줄부터 잘라 돌려준다. 사본의 span 은 함수 앞 빈 줄까지 품고 있어(실측 2줄),
    그대로 쓰면 줄 번호가 그만큼 밀린다. ast 의 함수 줄 번호도 `def` 줄을 가리키므로
    양쪽 기준을 여기서 맞춘다.
    """
    bounds = _mutmut_span_bounds(spans, name, len(lines))
    if bounds is None:
        return []
    picked = lines[bounds[0] - 1:bounds[1]]
    for index, line in enumerate(picked):
        if _MUTMUT_DEF_RE.match(line):
            return picked[index:]
    return []


def _mutmut_line(def_lines: dict, class_name, func_name, offset) -> int | None:
    """원본 파일 안 절대 줄. 되짚을 수 없으면 None — 없는 자리를 지어내지 않는다 (D2)."""
    if offset is None or func_name is None:
        return None
    hits = def_lines.get((class_name, func_name)) or []
    if len(hits) != 1:
        return None
    return hits[0] + offset


def _mutmut_record(rel: str, key: str, status: str, change: tuple, line, tests) -> dict:
    """D2 가 요구하는 항목을 게이트의 한 모양으로. 얻을 수 없는 칸은 None 으로 비운다.

    열은 mutmut 이 어떤 방법으로도 주지 않고, 변이 종류 이름도 없다(번호뿐이다). 비운 칸은
    표시 단계가 물음표와 안내 문구로 드러낸다 — 빈칸으로 두면 정상 항목처럼 보인다.
    `mutant` 는 게이트가 덧붙이는 칸이다. 사용자가 `mutmut show <이름>` 으로 같은 자리를
    직접 열어 볼 수 있어야 해서 남긴다.
    """
    _, original, replacement = change
    return {
        "file": rel,
        "line": line,
        "column": None,
        "mutator": None,
        "original": original,
        "replacement": replacement,
        "status": status,
        "tests": [str(t) for t in tests],
        "mutant": key,
    }


def build_mutmut_records(rel: str, meta: dict, spans: dict, mutant_source: str,
                         original_source: str, tests_by_function: dict) -> list:
    """파일 하나의 mutmut 산출물 → 게이트 기록 목록. 서브프로세스 없이 검증되는 순수 함수.

    입력은 `.meta`(변이별 종료 코드), `.spans`(사본 안 줄 범위), 생성된 사본, 원본,
    그리고 함수 단위 테스트 목록이다.
    """
    mutant_lines = score_mod._split_source(mutant_source)
    def_lines = mutmut_def_lines(original_source)
    by_key = meta.get("exit_code_by_key")
    if not isinstance(by_key, dict):
        return []
    records: list = []
    for key, exit_code in by_key.items():
        status = mutmut_gate_status(mutmut_status(exit_code))
        mangled = str(key).rsplit(".", 1)[-1]
        matched = _MUTMUT_INDEX_RE.match(mangled)
        prefix = matched.group("prefix") if matched else mangled
        class_name, func_name = mutmut_function_name(prefix)
        change = mutmut_change(
            _mutmut_span(mutant_lines, spans, f"{prefix}__mutmut_orig"),
            _mutmut_span(mutant_lines, spans, mangled),
        )
        line = _mutmut_line(def_lines, class_name, func_name, change[0])
        tests = tests_by_function.get(str(key).rsplit("__mutmut_", 1)[0]) or []
        records.append(_mutmut_record(rel, str(key), status, change, line, tests))
    return records


def _mutmut_remap_pending(records: list, pending_as: str | None) -> list:
    """안 돈 변이를 다른 상태로 세어 준다. 요청이 없으면 그대로 돌려준다."""
    if not pending_as:
        return records
    for record in records:
        if record["status"] == "Pending":
            record["status"] = pending_as
    return records


def parse_mutmut_run(work: Path, repo_root: Path, targets, pending_as: str | None = None) -> dict:
    """작업 디렉토리에 남은 mutmut 산출물을 요약으로. 서브프로세스를 부르지 않는다.

    `targets` 로 거르는 이유는 증분 때문이다. 작업 디렉토리는 회차를 넘어 살아 있어서 지난
    회차의 `.meta` 가 그대로 남는다. 거르지 않으면 이번 변경분 밖의 파일까지 점수에 들어간다 (R3).
    `pending_as` 는 "안 돈 변이" 를 다른 상태로 세어 달라는 요청이다. 덮는 테스트가 하나도
    없어 mutmut 이 아무것도 돌리지 못한 회차에만 쓴다 — 그 변이들은 실행 안 됨이 아니라
    덮은 테스트 없음이고, 그 구분이 점수의 분모를 가른다 (D1).
    """
    mutants = Path(work) / "mutants"
    stats = gate._read_json_object(mutants / "mutmut-stats.json")
    tests_by_function = stats.get("tests_by_mangled_function_name")
    if not isinstance(tests_by_function, dict):
        tests_by_function = {}
    records: list = []
    for rel in sorted(targets):
        meta = gate._read_json_object(mutants / f"{rel}.meta")
        if not meta:
            continue
        records += build_mutmut_records(
            rel, meta,
            gate._read_json_object(mutants / f"{rel}.spans"),
            _read_text_or_empty(mutants / rel),
            _read_text_or_empty(Path(repo_root) / rel),
            tests_by_function,
        )
    return score_mod.summarize_mutants(_mutmut_remap_pending(records, pending_as))


def _read_text_or_empty(path: Path) -> str:
    """파일 하나를 읽는다. 없거나 못 읽으면 빈 문자열 — 그 파일의 칸만 비고 나머지는 산다."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _is_python_test_file(path: Path) -> bool:
    """파이썬 테스트 파일 이름 규약. 이름과 자리 둘 다 본다."""
    name = path.name.lower()
    if name == "conftest.py" or name.startswith(_MUTMUT_TEST_PREFIXES):
        return True
    if path.stem.lower().endswith(_MUTMUT_TEST_STEMS):
        return True
    return any(part.lower() in _PYTHON_TEST_DIRS for part in path.parts[:-1])


def _mutmut_targets(repo_root: Path, files) -> tuple:
    """변이시킬 파이썬 파일을 고른다. 테스트 파일과 삭제된 파일은 뺀다.

    테스트를 변이시키는 것은 의미가 없고, 없는 파일을 넘기면 mutmut 이 준비 단계에서 죽는다.
    뺀 것은 사유와 함께 호출자가 리포트에 남긴다 (R4).
    """
    targets: list = []
    dropped: list = []
    for rel in files:
        path = Path(rel)
        if _is_python_test_file(path) or not (repo_root / rel).is_file():
            dropped.append(rel)
        else:
            targets.append(rel)
    return tuple(targets), tuple(dropped)


def _mutmut_source_roots(targets) -> tuple:
    """mutmut 에 넘길 소스 루트와, 다룰 수 없는 파일. 반환은 (루트, 못 다루는 파일).

    저장소 최상위 디렉토리를 그대로 루트로 쓴다. 최상위에 놓인 .py 는 그 파일 자체가 루트다
    (mutmut 은 파일 경로도 소스 루트로 받는다).
    """
    roots: list = []
    unusable: list = []
    for rel in targets:
        head = Path(rel).parts[0]
        if head in _MUTMUT_RESERVED_ROOTS:
            unusable.append(rel)
        elif head not in roots:
            roots.append(head)
    return tuple(roots), tuple(unusable)


def _mutmut_link_name(rel: str) -> str:
    """경로에서 사본에 걸 최상위 이름 하나. 걸 수 없는 모양이면 빈 문자열.

    작업 디렉토리 **안에** 만들 이름이라 반드시 한 겹짜리 이름이어야 한다. 상위 경로(`..`)나
    절대 경로를 그대로 받으면 지난 회차 링크를 지우는 단계가 작업 디렉토리 밖을 지운다 —
    실측에서 `testpaths = ../sharedtests` 하나로 캐시 디렉토리 전체가 사라졌고(자바스크립트
    증분 상태 파일까지), `testpaths` 가 절대 경로면 `/` 가 그 자리에 온다.
    도구가 쓰는 이름(`mutants` / `setup.cfg`)도 막는다. 그 자리에 프로젝트를 걸면 사본이
    대상 프로젝트 안에 쌓인다 (D3).
    """
    parts = Path(rel).parts
    head = parts[0] if parts else ""
    if head in _MUTMUT_BAD_LINK_NAMES or os.path.isabs(head) or os.sep in head:
        return ""
    return head


def _mutmut_test_roots(repo_root: Path, roots) -> tuple:
    """(소스 루트 밖 테스트 경로의 최상위 이름, 걸 수 없어 뺀 경로).

    mutmut 은 사본 안에서 테스트를 돌린다. 테스트 디렉토리가 소스 루트 밖에 있으면 사본에
    딸려 가지 않아 "테스트를 하나도 못 찾았다" 로 끝난다.
    뺀 것은 호출자가 사유와 함께 남긴다 — 조용히 빠지면 사본에 테스트가 없는 이유를 알 수
    없다 (R4).
    """
    # detect_pytest_paths 는 실제로 있는 경로만 돌려주므로 존재 여부를 다시 보지 않는다.
    found: list = []
    rejected: list = []
    for rel in gate.detect_pytest_paths(repo_root):
        head = _mutmut_link_name(rel)
        if not head:
            rejected.append(rel)
        elif head not in roots and head not in found:
            found.append(head)
    return found, rejected


def _mutmut_config_links(repo_root: Path) -> list:
    """사본 안에 함께 있어야 하는 pytest 설정 파일.

    pyproject.toml 에는 조건이 하나 붙는다 — 그 안에 프로젝트의 mutmut 설정이 있으면 걸지
    않는다. 걸면 mutmut 이 게이트 설정 대신 그것을 읽어 변경분 한정이 통째로 풀린다 (R3).
    """
    names = [name for name in ("conftest.py", "pytest.ini", "tox.ini")
             if (repo_root / name).is_file()]
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file() and "[tool.mutmut]" not in _read_text_or_empty(pyproject):
        names.append("pyproject.toml")
    return names


def _mutmut_extra_links(repo_root: Path, roots) -> tuple:
    """(사본에 함께 걸 이름 — 테스트 경로와 pytest 설정, 걸 수 없어 뺀 경로)."""
    test_roots, rejected = _mutmut_test_roots(repo_root, roots)
    return test_roots + _mutmut_config_links(repo_root), rejected


def _mutmut_project_settings(repo_root: Path) -> dict:
    """프로젝트가 setup.cfg 에 갖고 있는 mutmut 설정. 없으면 빈 dict (읽기만 한다).

    게이트가 정하는 키(소스 루트 / 변경분 한정 / 덮인 줄만 변이)는 뺀다. 나머지는 그대로
    옮겨 프로젝트가 정한 값이 살아 있게 한다 (D3).
    """
    path = repo_root / "setup.cfg"
    if not path.is_file():
        return {}
    parser = configparser.ConfigParser()
    try:
        parser.read_string(_read_text_or_empty(path))
        items = dict(parser.items("mutmut"))
    except (configparser.Error, ValueError):
        return {}
    reserved = {"source_paths", "paths_to_mutate", "only_mutate", "mutate_only_covered_lines"}
    return {k: v for k, v in items.items() if k not in reserved}


def _cfg_list(key: str, values) -> str:
    """setup.cfg 의 여러 줄 값. mutmut 은 줄바꿈으로 목록을 읽는다."""
    body = "".join(f"\n\t{value}" for value in values)
    return f"{key}={body}\n"


def _write_mutmut_config(work: Path, roots, targets, extra, carried: dict) -> Path:
    """작업 디렉토리에 mutmut 설정을 쓴다. 대상 프로젝트에는 아무것도 만들지 않는다 (D3).

    설정 파일이 한 개 반드시 필요한 이유는 소스 루트와 변경분 한정을 넘기는 명령줄 옵션이
    없어서다. `mutate_only_covered_lines` 는 반드시 꺼 둔다 — 켜면 덮이지 않은 줄의 변이를
    아예 만들지 않아 no_coverage 가 0 이 되고, 테스트를 안 쓸수록 점수가 오른다 (D1 위반).
    """
    path = Path(work) / "setup.cfg"
    # `only_mutate` 는 mutmut 이 fnmatch 로 맞추는 **글롭**이다. 경로에 대괄호가 있으면
    # 그 파일이 자기 자신과 안 맞아 어떤 회차에도 변이되지 않는다 (실측: legacy[old].py).
    # 소스 루트와 함께 걸 경로는 글롭이 아니라 경로라서 이스케이프하지 않는다.
    body = ["[mutmut]\n", _cfg_list("source_paths", roots),
            _cfg_list("only_mutate", [glob.escape(rel) for rel in targets])]
    if extra:
        body.append(_cfg_list("also_copy", extra))
    body.append("mutate_only_covered_lines=False\n")
    body += [f"{key}={value}\n" for key, value in sorted(carried.items())]
    path.write_text("".join(body), encoding="utf-8")
    return path


_MUTMUT_STATE_NAME = "gate-incremental.json"


def _mutmut_stale_reason(previous: dict, targets, changed_tests) -> str:
    """지난 회차 사본을 그대로 쓰면 안 되는 사유. 쓸 수 있으면 빈 문자열.

    mutmut 은 사본 안 결과를 **함수 해시**로만 무효화한다. 그래서 두 경우에 지난 결과가
    그대로 재사용된다 (둘 다 실측).
      - 테스트가 바뀐 회차. 확인문을 전부 지워도 지난 회차의 "잡힘" 이 그대로 남아 100% 로
        통과했다. 같은 상태를 처음부터 돌리면 0% 다. 3단계에서 차단으로 가면 거짓 통과다.
      - 대상 파일 목록이 바뀐 회차. mutmut 은 `only_mutate` 변경을 무효화 사유로 보지 않아,
        새로 든 파일이 통째로 "덮은 테스트 없음" 으로 굳고 회차를 더 돌려도 회복되지 않았다.
    """
    if changed_tests:
        return "테스트 파일이 이번 변경분에 있어"
    if list(previous.get("targets") or ()) != list(targets):
        return "변이 대상 파일 목록이 지난 회차와 달라"
    return ""


def _mutmut_incremental_guard(ctx: gate.GateContext, work: Path, targets, changed_tests) -> None:
    """쓸 수 없는 사본이면 버리고, 이번 회차의 기준을 남긴다 (R3).

    증분을 버리는 회차는 콜드 실행이라 그만큼 느리다. 그래도 틀린 점수보다는 낫다 —
    이 게이트가 내는 숫자는 사용자가 테스트를 고칠 때 보는 유일한 근거다.
    """
    mutants = Path(work) / "mutants"
    reason = _mutmut_stale_reason(gate._read_json_object(Path(work) / _MUTMUT_STATE_NAME),
                                  targets, changed_tests)
    if reason and mutants.exists() and not _mutmut_drop_mutants(ctx, mutants, reason):
        return
    _mutmut_write_state(ctx, work, targets, changed_tests)


def _mutmut_drop_mutants(ctx: gate.GateContext, mutants: Path, reason: str) -> bool:
    """지난 회차 사본을 지운다. 지우지 못하면 사유를 남기고 False."""
    try:
        shutil.rmtree(mutants)
    except OSError as exc:
        ctx.notes.append(
            f"지난 회차 사본을 지우지 못했습니다 ({type(exc).__name__}). "
            "이번 점수에는 지난 회차 결과가 섞여 있을 수 있습니다.")
        return False
    ctx.notes.append(
        f"{reason} 지난 회차 사본을 버리고 전체를 다시 돌렸습니다 "
        "(그대로 쓰면 지난 회차 결과가 이번 점수로 나갑니다). 이번 회차는 증분 이득이 없습니다.")
    return True


def _mutmut_write_state(ctx: gate.GateContext, work: Path, targets, changed_tests=()) -> None:
    """다음 회차가 견줄 기준을 남긴다. 못 남기면 다음 회차가 사본을 새로 만든다.

    상태에는 실패 각인의 입력 지문(대상 목록 + 변경분의 테스트 파일 목록 + 내용 지문)도
    함께 남는다. 이 상태를 통째로 새로 쓰는 것이 지난 회차의 각인(baseline_failure)을
    지우는 동작이기도 하다 — 실제로 도는 회차는 항상 여기를 지나므로, 각인은
    "억제된 회차" 에서만 살아남는다.
    """
    state = {"targets": list(targets), "changed_tests": list(changed_tests),
             "content": _mutmut_content_fingerprint(ctx, targets, changed_tests)}
    try:
        (Path(work) / _MUTMUT_STATE_NAME).write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        ctx.notes.append(
            f"파이썬 뮤테이션의 증분 기준을 남기지 못했습니다 ({type(exc).__name__}). "
            "다음 회차는 사본을 새로 만듭니다.")


# 실패 각인 — "변이를 하나도 못 돌리고 기준 단계에서 죽은" 회차의 사유를 상태 파일에
# 남기는 자리. 그 회차는 기준 테스트에 회차당 수십 초를 쓰고도 같은 오류만 되풀이하므로,
# 입력이 같으면 다시 돌리지 않고 즉시 같은 오류를 낸다.
#
# 각인의 무효화 조건은 증분 무효화 선언(incremental_triggers)과 같은 것을 쓴다 —
# 별도 조건을 만들면 두 무효화가 어긋나는 자리가 생긴다. 선언한 세 조건을 "지난 실패
# 회차 이후 실제로 바뀌었는가" 로 평가한다:
#   대상 목록 변화        → 지문의 targets 목록 비교
#   테스트 파일 변경분 포함 → 지문의 changed_tests 목록 + 그 파일들의 내용 지문 비교
#   함수 해시(소스 변경)   → 대상 파일들의 내용 지문 비교
# 목록만 비교하면 사용자가 테스트의 git 의존을 끊는 수정을 해도 각인이 남아 낡은 오류가
# 나간다 — 그래서 내용 지문이 필요하다. 이 메커니즘은 이 어댑터의 상태 파일 안 필드다 —
# 중립층과 합치는 층은 이것을 모른다.
_MUTMUT_FAILURE_KEY = "baseline_failure"


def _mutmut_content_fingerprint(ctx: gate.GateContext, targets, changed_tests) -> str:
    """입력 파일들(대상 + 변경분의 테스트)의 내용 지문. 변경분 한정이라 비용이 작다 (R3)."""
    digest = hashlib.sha256()
    for rel in sorted(set(targets) | set(changed_tests)):
        digest.update(rel.encode("utf-8", "replace") + b"\x00")
        try:
            digest.update((Path(ctx.repo_root) / rel).read_bytes())
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\x00")
    return digest.hexdigest()


def _mutmut_imprint_failure(ctx: gate.GateContext, work: Path, outcome: dict) -> None:
    """실패 사유를 각인한다. 지문은 이미 상태에 있다. 못 남기면 다음 회차가 그냥 다시 돈다."""
    path = Path(work) / _MUTMUT_STATE_NAME
    state = gate._read_json_object(path)
    state[_MUTMUT_FAILURE_KEY] = {"reason": outcome.get("reason", ""),
                                  "human_reason": outcome.get("human_reason", "")}
    try:
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        ctx.notes.append(
            f"파이썬 뮤테이션의 실패 각인을 남기지 못했습니다 ({type(exc).__name__}). "
            "다음 회차는 기준 테스트를 다시 돌립니다.")


def _mutmut_imprint_matches(ctx: gate.GateContext, state: dict, targets,
                            changed_tests) -> bool:
    """지난 실패 회차의 입력 지문과 지금이 같은가 — 목록 둘과 내용 지문 전부."""
    if list(state.get("targets") or ()) != list(targets):
        return False
    if list(state.get("changed_tests") or ()) != list(changed_tests):
        return False
    return state.get("content") == _mutmut_content_fingerprint(ctx, targets, changed_tests)


def _mutmut_imprinted_outcome(ctx: gate.GateContext, work: Path, targets,
                              changed_tests) -> dict | None:
    """지난 회차의 실패 각인이 아직 유효하면 그 오류를 즉시 낸다. 아니면 None.

    유효 = 입력 지문(대상 목록 + 변경분의 테스트 파일 목록 + 내용 지문)이 실패한 회차와
    같다 — 무효화 조건의 평가 방식은 _MUTMUT_FAILURE_KEY 주석 참조. status 는 지난 회차와
    같은 error 라 판정이 바뀌지 않는다 — 바뀌는 것은 소요 시간(기준 테스트 생략)과
    문장의 정확도뿐이다.
    """
    state = gate._read_json_object(Path(work) / _MUTMUT_STATE_NAME)
    imprint = state.get(_MUTMUT_FAILURE_KEY)
    if not isinstance(imprint, dict):
        return None
    if not _mutmut_imprint_matches(ctx, state, targets, changed_tests):
        return None
    last_human = imprint.get("human_reason") or imprint.get("reason") or "(기록 없음)"
    ctx.notes.append("지난 회차의 실패 각인이 유효해 기준 테스트를 다시 돌리지 않았습니다.")
    return {
        "status": "error",
        "reason": ("mutmut baseline failure repeated; inputs unchanged since last run: "
                   + (imprint.get("reason") or "")),
        "human_reason": (
            f"지난 회차와 입력이 같아 다시 돌지 않았습니다. 지난 사유: {last_human} "
            f"다시 재려면 대상이나 테스트를 바꾸거나 사본 디렉토리를 지우십시오 ({work})."),
    }


def mutmut_work_dir(repo_root: Path, notes: list) -> Path | None:
    """mutmut 작업 디렉토리 — 반드시 대상 프로젝트 밖이다 (D3). 못 만들면 None.

    mutmut 은 사본과 증분 상태를 통째로 **현재 작업 디렉토리** 아래 `mutants/` 에 둔다.
    게이트 임시 디렉토리는 실행이 끝나면 지워져 증분이 성립하지 않으므로, Stryker 의 상태
    파일과 같은 자리(사용자 캐시 아래 저장소별 디렉토리)에 둔다. 다만 이쪽은 파일 하나가
    아니라 디렉토리 하나다.
    """
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    key = hashlib.sha256(str(Path(repo_root).resolve()).encode("utf-8")).hexdigest()[:16]
    target = Path(base) / "code-gate" / "mutation" / key / "mutmut"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        notes.append(
            f"파이썬 뮤테이션의 작업 디렉토리를 캐시에 만들지 못했습니다 ({type(exc).__name__})."
        )
        return None
    return target.resolve()


def _mutmut_reclaim(work: Path, notes: list) -> None:
    """사본 자리에 게이트가 만들지 않은 링크가 있으면 지운다 (D3).

    지난 회차에 걸리면 안 될 이름이 걸려 `mutants` 가 대상 프로젝트를 가리키게 되면, 그 뒤로는
    원인을 없애도 회차마다 프로젝트 안에 사본이 쌓인다 — 아무도 되돌리지 않기 때문이다 (실측).
    """
    mutants = Path(work) / "mutants"
    if not mutants.is_symlink():
        return
    try:
        mutants.unlink()
    except OSError as exc:
        notes.append(
            f"파이썬 뮤테이션 사본 자리에 걸린 링크를 지우지 못했습니다 ({type(exc).__name__}).")
        return
    notes.append(
        "파이썬 뮤테이션 사본 자리에 지난 회차의 링크가 걸려 있어 지웠습니다. "
        "이번 회차는 증분 없이 전체를 다시 돌립니다.")


def _mutmut_unlink(path: Path) -> None:
    """지난 회차의 링크를 지운다. 실체가 디렉토리면 통째로 지운다."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _mutmut_link(work: Path, repo_root: Path, names) -> str:
    """소스와 테스트를 작업 디렉토리에 심링크로 건다. 실패 사유가 있으면 문자열로.

    링크는 회차마다 다시 건다 — 프로젝트 구조가 바뀌면 지난 회차의 링크가 엉뚱한 곳을
    가리킨다. `mutants/` 는 건드리지 않는다 (증분 상태가 그 안에 있다).
    """
    for name in names:
        if _mutmut_link_name(name) != name:
            # 여기까지 오면 안 되는 이름이다. 지우는 단계가 작업 디렉토리 밖을 만지기 전에 멈춘다.
            return f"{name} (사본 안에 만들 수 없는 이름)"
        link = Path(work) / name
        try:
            _mutmut_unlink(link)
            link.symlink_to(repo_root / name)
        except OSError as exc:
            return f"{name} ({type(exc).__name__})"
    return ""


def _mutmut_command(ctx: gate.GateContext, work: Path, targets) -> tuple:
    """(실행할 명령, 결과가 나온 뒤에 남길 안내).

    변경분 한정도 소스 루트도 설정 파일에 있어 명령줄은 이것뿐이다. 동시 실행 수는
    mutmut 기본값(`os.cpu_count()`)을 그대로 둔다 — 항목은 순차로 도니 다른 검사와 겹치지 않는다.
    안내를 바로 남기지 않고 돌려주는 이유는, 아무것도 재지 못하고 끝난 회차에도 "이렇게
    걸러서 점수를 냈다" 는 문장이 함께 나가 사용자를 원인에서 멀어지게 해서다.
    """
    cmd = [ctx.python_exe, "-m", "mutmut", "run"]
    notes = [
        f"파이썬 뮤테이션은 변경된 파일 {len(targets)}개를 파일 단위로 변이시켰습니다. "
        "그 파일 안에서 이번에 바뀌지 않은 줄도 함께 변이됩니다. "
        "변경되지 않은 다른 파일은 대상이 아닙니다.",
        "파이썬 뮤테이션은 대상 프로젝트 밖(사용자 캐시)에 소스 사본을 만들어 돌렸습니다. "
        "프로젝트에는 파일을 만들지 않았습니다.",
    ]
    notes.append(
        "파이썬 뮤테이션은 증분 실행입니다. 지난 회차 결과가 사본에 남아 있어 이번 변경 "
        "파일 목록으로 걸러낸 뒤 점수를 냈습니다."
        if (Path(work) / "mutants").is_dir() else
        "파이썬 뮤테이션의 사본이 아직 없어 이번에는 전체를 다시 만들었습니다. "
        "다음 회차부터 지난 결과를 재사용합니다."
    )
    return cmd, notes


_MUTMUT_FAILURE_CAUSES = (
    ("Module name starts with", "테스트가 소스를 `src.` 로 시작하는 경로로 import 하면 mutmut 이 멈춥니다."),
    ("none match any mutant key", "테스트가 사본이 아닌 원본을 import 했습니다 (conftest 의 경로 조작과 부딪힌 경우입니다)."),
    # 사본 한계(copy_limitations 선언)의 실측 사례 — "failed to collect stats" 보다 먼저
    # 봐야 한다. 같은 회차에 두 문장이 함께 나오는데 이쪽이 원인이고 저쪽은 증상이다.
    ("not a git repository",
     "사본에는 .git 이 없습니다. git 을 부르는 테스트는 사본 안에서 돌 수 없습니다. "
     "그런 테스트를 뮤테이션 대상 테스트에서 빼거나, 테스트의 git 의존을 끊으십시오."),
    # 같은 오류의 한국어 로케일 문구 (실측 — git 이 LANG 을 따라간다).
    ("깃 저장소가 아닙니다",
     "사본에는 .git 이 없습니다. git 을 부르는 테스트는 사본 안에서 돌 수 없습니다. "
     "그런 테스트를 뮤테이션 대상 테스트에서 빼거나, 테스트의 git 의존을 끊으십시오."),
    ("failed to collect stats", "사본 안에서 기준 테스트가 실패해 변이를 시작하지 못했습니다."),
    ("Could not figure out where the code to mutate is", "소스 루트를 찾지 못했습니다."),
    ("could not find any test case for any mutant",
     "변경된 파일을 덮는 테스트를 하나도 찾지 못했습니다."),
)


def _mutmut_output_tail(proc) -> str:
    """도구가 남긴 마지막 출력. 진짜 설정 오류일 때 이 문장이 유일한 단서다."""
    if proc is None:
        return ""
    return " ".join((proc.stderr or proc.stdout or "").split())[-400:]


def _mutmut_failure_cause(detail: str) -> str:
    """짚이는 원인 한 줄. 못 짚으면 일반 문장으로 남긴다."""
    for needle, korean in _MUTMUT_FAILURE_CAUSES:
        if needle in detail:
            return korean
    return "사본 안에서 테스트가 돌지 않았거나 소스 루트가 mutmut 의 규약과 어긋났을 때 나옵니다."


def _mutmut_no_result(proc, elapsed: float) -> dict:
    """결과 파일이 없으면 통과가 아니라 오류다 (R4).

    mutmut 은 점수가 낮다고 비-0 으로 끝내지 않는다. 종료 코드 1 은 거의 준비 실패다 —
    사본 안에서 기준 테스트가 실패했거나, 테스트가 보는 import 경로가 mutmut 이 보는 것과
    다른 경우다. 짚이는 원인을 한국어로 먼저 적고 영어 원문을 뒤에 붙인다.
    """
    detail = _mutmut_output_tail(proc)
    returncode = proc.returncode if proc is not None else None
    cause = _mutmut_failure_cause(detail)
    tail = f" mutmut 원문: {detail}" if detail else " mutmut 이 아무 출력도 내지 않았습니다."
    return {
        "status": "error",
        "reason": f"mutmut produced no result (exit {returncode}): {detail}",
        "human_reason": (f"mutmut 이 결과를 남기지 못했습니다 (종료 코드 {returncode}, "
                         f"{elapsed:.1f}초). {cause}{tail}"),
    }


def _mutmut_partial(ctx: gate.GateContext, summary: dict, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단했을 때 — 본 만큼만 내고 못 본 것을 반드시 말한다 (D4·R4).

    두 숫자를 같은 곳에서 뽑는다. mutmut 은 변이를 만들 때 모든 이름을 `.meta` 에 넣고
    돌린 것만 종료 코드를 채우므로, 전체와 "여기까지" 의 모수가 어긋나지 않는다.
    """
    total = summary["total"]
    pending = int(summary["counts"].get("Pending", 0) or 0)
    seen = total - pending
    timing = score_mod._mutation_timing(elapsed, total, score_mod._mutation_executed(summary["counts"]))
    score = summary["score"]
    score_text = (
        f"거기까지의 점수는 {score:.1f}% 입니다 (전체 점수가 아닙니다)"
        if score is not None else "거기까지는 점수를 낼 변이가 없었습니다"
    )
    tail = score_mod._mutation_partial_gaps(summary, targets)
    return {
        "status": "timeout",
        "reason": f"timeout after {budget}s ({seen} of {total} mutants tested)",
        "human_reason": (
            f"{budget}초 예산을 넘겨 중단했습니다. 변이 {total}개 중 {seen}개까지 봤고 "
            f"나머지는 재지 못했습니다. {score_text}. {timing}{tail}"
        ),
        "findings": summary["survivors"],
    }


def _mutmut_gap_notes(ctx: gate.GateContext, summary: dict) -> None:
    """이 경로가 낼 수 없는 칸을 사용자에게 드러낸다 (D2·R4).

    빈칸으로 두면 자바스크립트 쪽 목록과 같은 것으로 읽힌다. 세 칸이 다르다.
    """
    ctx.notes.append(
        "파이썬 뮤테이션 목록에는 열 번호와 변이 종류 이름이 없습니다 (mutmut 이 주지 않습니다). "
        "관련 테스트도 변이별이 아니라 함수 단위라, 같은 함수의 변이는 같은 목록을 갖습니다. "
        "정확한 변이 내용은 목록의 원본과 바뀐 것으로 봅니다."
    )
    blind = sum(1 for record in summary["survivors"] if record.get("line") is None)
    if blind:
        ctx.notes.append(
            f"파이썬 변이 {blind}건은 원본 파일의 줄 번호를 되짚지 못했습니다 "
            "(같은 이름의 함수가 여럿이거나 변이 자리가 한 군데가 아닌 경우입니다). 그 자리는 물음표로 적었습니다."
        )


def _mutmut_decorator_gap(ctx: gate.GateContext, targets) -> str:
    """데코레이터 때문에 변이가 아예 만들어지지 않은 함수. 없으면 빈 문자열 (R4).

    파일 단위 안전망은 이 경우를 못 잡는다 — 파일 안에 변이 가능한 함수가 하나만 있어도
    그 파일은 "쟀다" 로 분류된다. 말하지 않으면 커버리지가 낮은 파일이 뮤테이션 100% 통과로
    나간다 (실측: 커버리지 79% 인 파일이 뮤테이션 100% 통과, 금액 계산 함수 셋은 미측정).
    """
    skipped: list = []
    for rel in targets:
        skipped += [f"{rel}::{name}"
                    for name in python_decorated_skips(_read_text_or_empty(ctx.repo_root / rel))]
    if not skipped:
        return ""
    return (f"함수 {len(skipped)}개는 데코레이터가 붙어 있어 변이가 하나도 만들어지지 않았습니다 "
            f"(mutmut 이 건너뜁니다). 이 점수에 들어 있지 않습니다: {score_mod._sample_list(skipped)}")


def _mutmut_apply_gap(outcome: dict, gap: str) -> dict:
    """못 본 것이 있으면 통과로 내지 않는다 — 점수가 변경분 전체를 대표하지 못한다.

    자바스크립트 쪽에서 리포트에 한 줄도 없는 파일을 다루는 규칙과 같다 (_mutation_outcome).
    """
    if not gap:
        return outcome
    outcome["human_reason"] = f"{outcome.get('human_reason', '')}  {gap}"
    if outcome.get("status") == "ok":
        outcome["status"] = "findings"
    return outcome


# C1 의 파이썬 결과별 안내. "테스트가 없다" 와 "테스트가 실패했다" 는 사용자가 할 일이 다르다.
_MUTMUT_TESTS_BLOCKED = {
    "skipped": ("파이썬 테스트를 돌리지 못해 뮤테이션을 재지 않았습니다 "
                "(테스트 경로를 찾지 못했거나 pytest 가 없습니다). 테스트 자체는 실패하지 않았습니다."),
    "timeout": ("파이썬 테스트가 예산 안에 끝나지 않아 뮤테이션을 재지 않았습니다 "
                "(mutmut 은 기준 테스트를 먼저 통과시켜야 돌아갑니다)."),
}
_MUTMUT_TESTS_FAILED = ("파이썬 테스트가 통과하지 않아 뮤테이션을 재지 않았습니다 "
                        "(mutmut 은 기준 테스트가 통과해야 돌아갑니다). 테스트를 먼저 고치십시오.")


def _mutmut_preconditions(ctx: gate.GateContext) -> dict | None:
    """파이썬 경로만의 사유. 있으면 그 결과를, 없으면 None (R4)."""
    config = ctx.config
    if config.mutation_python != "mutmut":
        return gate._skip(
            f"설정의 mutation.python 값 '{config.mutation_python}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported python mutation tool: {config.mutation_python}",
        )
    tool = gate._tool(ctx, "mutmut")
    if not tool["available"]:
        return gate._skip("mutmut 이 설치돼 있지 않습니다.", "mutmut missing", tool["install_hint"])
    status = ctx.python_tests_status
    if status is not None and status != "ok":
        # C1 이 건너뛴 것과 실패한 것을 한 문장으로 묶으면, 고칠 것이 없는 사용자에게
        # "테스트를 먼저 고치십시오" 라고 말하게 된다 (실측: 저장소 최상위에 test_*.py 를
        # 둔 배치에서 pytest 는 통과하는데 이 문장이 나갔다).
        return gate._skip(_MUTMUT_TESTS_BLOCKED.get(status, _MUTMUT_TESTS_FAILED),
                     f"python tests not ok: {status}")
    return None


def _mutmut_scope(ctx: gate.GateContext, py_files) -> tuple:
    """변이시킬 파일 목록과, 남는 것이 없을 때의 건너뜀 결과. 뺀 파일은 사유와 함께 남긴다."""
    targets, dropped = _mutmut_targets(ctx.repo_root, py_files)
    if dropped:
        ctx.notes.append(
            f"파이썬 뮤테이션 대상에서 테스트·삭제된 파일 {len(dropped)}개를 뺐습니다: "
            + score_mod._sample_list(list(dropped))
        )
    if not targets:
        return (), gate._skip(
            f"변경된 파이썬 파일 {len(py_files)}개가 모두 변이 대상이 아닙니다 (테스트·삭제된 파일).",
            "no mutable python targets",
        )
    return targets, None


def _mutmut_workspace(ctx: gate.GateContext, roots) -> tuple:
    """(작업 디렉토리, 함께 건 이름, 건너뜀 결과). 캐시를 못 쓰면 임시 디렉토리로 물러선다."""
    work = mutmut_work_dir(ctx.repo_root, ctx.notes)
    if work is None:
        # 이번 회차는 증분 없이 전부 다시 돌지만, 대상 프로젝트 밖이라는 것(D3)은 그대로다.
        work = (ctx.tmpdir / "mutation-python").resolve()
        work.mkdir(parents=True, exist_ok=True)
        ctx.notes.append("파이썬 뮤테이션은 이번에 증분 없이 전체를 돌렸습니다 (캐시를 쓰지 못했습니다).")
    _mutmut_reclaim(work, ctx.notes)
    extra, rejected = _mutmut_extra_links(ctx.repo_root, roots)
    if rejected:
        ctx.notes.append(
            f"테스트 경로 {len(rejected)}개는 사본 안에 걸 수 없어 뺐습니다 "
            f"(소스 루트 밖의 상위·절대 경로이거나 mutmut 이 쓰는 이름입니다): "
            + score_mod._sample_list(list(rejected))
            + ". 사본에 테스트가 없으면 mutmut 이 변이를 하나도 돌리지 못합니다.")
    failed = _mutmut_link(work, ctx.repo_root, list(roots) + extra)
    if failed:
        return None, (), gate._skip(
            f"파이썬 뮤테이션용 사본을 만들지 못했습니다 ({failed}).", "mutmut link failed")
    return work, extra, None


def _mutmut_config_notes(ctx: gate.GateContext, extra, carried: dict) -> None:
    """프로젝트 설정을 어떻게 다뤘는지 남긴다. 말하지 않으면 무엇이 적용됐는지 알 수 없다 (R4)."""
    if (ctx.repo_root / "pyproject.toml").is_file() and "pyproject.toml" not in extra:
        ctx.notes.append(
            "프로젝트 pyproject.toml 의 mutmut 설정은 이번 실행에 쓰지 않았습니다 "
            "(변경분만 재려면 게이트 설정이 필요합니다). 프로젝트 파일은 읽지도 고치지도 않았습니다."
        )
    if carried:
        ctx.notes.append(
            f"프로젝트 setup.cfg 의 mutmut 설정 {len(carried)}개를 그대로 이어 썼습니다: "
            + score_mod._sample_list(sorted(carried))
        )


def _mutmut_setup(ctx: gate.GateContext, targets, changed_tests) -> tuple:
    """(작업 디렉토리, 소스 루트, 건너뜀 결과). 준비가 안 되면 재지 않고 사유를 낸다."""
    roots, unusable = _mutmut_source_roots(targets)
    if unusable:
        ctx.notes.append(
            f"파이썬 파일 {len(unusable)}개는 최상위 이름이 mutmut 의 작업 이름과 겹쳐 재지 "
            "못했습니다: " + score_mod._sample_list(list(unusable))
        )
    if not roots:
        return None, (), gate._skip("변이시킬 파이썬 소스 루트를 정하지 못했습니다.", "no python source root")

    work, extra, blocked = _mutmut_workspace(ctx, roots)
    if blocked is not None:
        return None, (), blocked
    imprinted = _mutmut_imprinted_outcome(ctx, work, targets, changed_tests)
    if imprinted is not None:
        # 지난 회차가 기준 단계에서 죽었고 입력이 그대로다 — 다시 돌아도 같은 오류에
        # 수십 초만 쓴다. 증분 가드보다 먼저 본다 (가드가 상태를 새로 쓰면 각인이 지워진다).
        return None, (), imprinted
    _mutmut_incremental_guard(ctx, work, targets, changed_tests)
    carried = _mutmut_project_settings(ctx.repo_root)
    _mutmut_config_notes(ctx, extra, carried)
    _write_mutmut_config(work, roots, targets, extra, carried)
    return work, roots, None


def _mutmut_nothing_ran(summary: dict, proc) -> bool:
    """변이를 만들기만 하고 하나도 돌리지 못한 회차인가.

    준비 단계에서 죽으면 `.meta` 는 남는다 — 변이를 만들 때 이름을 전부 넣고 종료 코드는
    비워 두기 때문이다. 그 상태를 "점수를 낼 변이가 없다" 로만 내면 도구가 남긴 사유가
    사라져, 사용자가 원인을 찾을 수 없다.
    """
    if proc is None or proc.returncode == 0:
        return False
    pending = int(summary["counts"].get("Pending", 0) or 0)
    return summary["total"] == 0 or pending == summary["total"]


# 변경된 파일을 덮는 테스트가 하나도 없을 때 mutmut 이 내는 문장. 종료 코드는 결과가 아예
# 없는 회차와 같은 1 이라, 이 문장이 둘을 가르는 유일한 단서다.
_MUTMUT_NO_TESTS = "could not find any test case for any mutant"


def _mutmut_uncovered(ctx: gate.GateContext, work: Path, targets, elapsed: float) -> tuple:
    """변경 파일을 덮는 테스트가 하나도 없는 회차 — 오류가 아니라 점수 0% 다 (D1).

    D1 이 no_coverage 를 분모에 남기는 이유가 바로 이 경우인데, 이 경우에만 점수가 안 나오고
    "설정이 어긋났다" 는 안내가 나갔다. 사용자를 원인에서 멀어지게 하는 문장이다.
    사본에 변이 이름이 남아 있을 때만 이 길로 온다 — 이름조차 없으면 진짜 준비 실패다.
    """
    summary = parse_mutmut_run(work, ctx.repo_root, targets, pending_as="NoCoverage")
    ctx.notes.append(
        "변경된 파이썬 파일을 덮는 테스트를 mutmut 이 하나도 찾지 못했습니다. "
        "그 변이는 전부 '덮은 테스트 없음' 으로 셌습니다 — 테스트가 없는 코드가 점수에서 "
        "사라지지 않게 하기 위해서입니다.")
    return score_mod._mutation_outcome(ctx, summary, elapsed, targets), summary


def _mutmut_incomplete(proc, summary: dict, elapsed: float) -> dict:
    """도구가 끝까지 돌지 못한 회차 — 남은 결과가 있어도 점수를 내지 않는다 (R4·D4).

    지난 회차 사본이 남아 있으면 이번에 하나도 못 돈 변이가 "실행 안 됨" 으로 섞여, 그 수가
    점수 분모에서 빠진 채 "통과 100%" 가 나간다. 같은 문장 안에서 "변이 7개" 와
    "잡히지 않음 0개" 의 모수가 달라지는 자리이기도 하다 (실측).
    """
    pending = int(summary["counts"].get("Pending", 0) or 0)
    detail = _mutmut_output_tail(proc)
    returncode = proc.returncode if proc is not None else None
    tail = f" mutmut 원문: {detail}" if detail else ""
    return {
        "status": "error",
        "reason": (f"mutmut stopped early (exit {returncode}, "
                   f"{pending} of {summary['total']} mutants not run): {detail}"),
        "human_reason": (
            f"mutmut 이 끝까지 돌지 못했습니다 (종료 코드 {returncode}, {elapsed:.1f}초). "
            f"변이 {summary['total']}개 중 {pending}개를 재지 못해 점수를 내지 않았습니다. "
            f"{_mutmut_failure_cause(detail)}{tail}"),
        "findings": summary["survivors"],
    }


def _mutmut_exit_note(ctx: gate.GateContext, proc) -> None:
    """변이는 다 돌았는데 종료 코드가 0 이 아닌 회차. 판정은 그대로 두고 사실만 남긴다 (R4)."""
    if proc is None or proc.returncode == 0:
        return
    detail = _mutmut_output_tail(proc)
    ctx.notes.append(
        f"mutmut 이 종료 코드 {proc.returncode} 로 끝났습니다 (변이는 모두 돌았습니다)."
        + (f" 원문: {detail}" if detail else ""))


def _mutmut_finished(ctx: gate.GateContext, work: Path, targets, proc, summary: dict,
                     elapsed: float) -> tuple:
    """예산 안에 끝난 회차의 판정. 도구가 실제로 끝까지 돌았는지부터 본다 (R4).

    반환의 두 번째 값이 None 이면 점수를 내지 못한 회차다 — 호출자가 목록 안내를 붙이지 않는다.
    """
    if _mutmut_nothing_ran(summary, proc):
        if summary["total"] and _MUTMUT_NO_TESTS in _mutmut_output_tail(proc):
            return _mutmut_uncovered(ctx, work, targets, elapsed)
        # 변이를 만들기만 하고 하나도 돌리지 못한 회차. `.meta` 는 남지만 전부 "실행 안 됨"
        # 이라 점수가 없다. 그대로 "점수를 낼 변이가 없다" 고만 내면 왜 그런지가 사라진다.
        # 이 회차의 사유를 각인해, 입력이 같은 다음 회차가 기준 테스트를 다시 돌리지 않게 한다.
        outcome = _mutmut_no_result(proc, elapsed)
        _mutmut_imprint_failure(ctx, work, outcome)
        return outcome, None
    if int(summary["counts"].get("Pending", 0) or 0):
        return _mutmut_incomplete(proc, summary, elapsed), None
    _mutmut_exit_note(ctx, proc)
    # 결과를 문장으로 만드는 단계는 요약만 보고 도구를 모른다 — 자바스크립트 경로와 같은 것을 쓴다.
    return score_mod._mutation_outcome(ctx, summary, elapsed, targets), summary


def _mutmut_measured_notes(ctx: gate.GateContext, summary: dict, scope_notes: list) -> None:
    """실제로 잰 회차에만 붙이는 안내. 잰 것이 없으면 없는 목록을 설명하게 된다."""
    ctx.notes.extend(scope_notes)
    if summary["total"]:
        _mutmut_gap_notes(ctx, summary)


def _mutmut_timed_out(ctx: gate.GateContext, summary: dict, targets, timing: tuple,
                      scope_notes: list) -> tuple:
    """예산을 넘겨 중단된 회차. 남은 것이 있으면 그것만, 없으면 그 사실만 낸다 (D4)."""
    elapsed, budget = timing
    if summary["total"] == 0:
        return {
            "status": "timeout",
            "reason": f"timeout after {budget}s with no partial result",
            "human_reason": f"{budget}초 예산을 넘겨 중단했습니다. 중간 결과가 남지 않아 변이를 하나도 재지 못했습니다.",
        }, None
    _mutmut_measured_notes(ctx, summary, scope_notes)
    partial = _mutmut_partial(ctx, summary, targets, elapsed, budget)
    return _mutmut_apply_gap(partial, _mutmut_decorator_gap(ctx, targets)), summary


def _mutmut_run(ctx: gate.GateContext, work: Path, cmd: list, targets, scope_notes: list) -> tuple:
    """실행하고 (결과, 요약) 을 만든다. 걸린 시간은 산출물을 다 읽은 뒤에 잰다 (R1).

    예산을 넘겨 죽었더라도 `.meta` 에 여기까지가 남아 있다 — mutmut 이 변이 하나가 끝날
    때마다 저장한다. 다 돈 회차면 그대로 점수를 낸다.
    예산은 항목 하나의 것이라 남은 만큼만 쓴다 (확정 6).
    """
    budget = score_mod._mutation_budget(ctx)
    if budget <= 0:
        # 준비 단계에서 남은 예산을 다 썼다. 0초 예산으로 띄우면 곧바로 시간초과로 죽어,
        # 재지 못한 이유가 "예산이 없었다" 가 아니라 "중간 결과가 없다" 로 나간다.
        return score_mod._mutation_out_of_budget(
            "python", "파이썬", ctx.config.mutation_timeout_seconds)["outcome"], None
    started = time.perf_counter()
    proc = None
    timed_out = False
    try:
        proc = gate._run(cmd, cwd=work, timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out = True

    summary = parse_mutmut_run(work, ctx.repo_root, targets)
    elapsed = time.perf_counter() - started
    if timed_out:
        return _mutmut_timed_out(ctx, summary, targets, (elapsed, budget), scope_notes)

    outcome, measured = _mutmut_finished(ctx, work, targets, proc, summary, elapsed)
    if measured is None:
        return outcome, None
    _mutmut_measured_notes(ctx, measured, scope_notes)
    return _mutmut_apply_gap(outcome, _mutmut_decorator_gap(ctx, targets)), measured


def _check_mutation_python(ctx: gate.GateContext, py_files) -> dict:
    """파이썬 경로 하나를 끝까지. 반환은 언어 한 조각(part)이다."""
    outcome, summary = _run_mutation_python(ctx, py_files)
    return {"language": "python", "label": "파이썬", "outcome": outcome, "summary": summary}


def _mutmut_changed_tests(py_files) -> list:
    """이번 변경분에 든 파이썬 테스트 파일. 증분 사본을 버릴지 판단하는 근거다."""
    return [rel for rel in py_files if _is_python_test_file(Path(rel))]


def _run_mutation_python(ctx: gate.GateContext, py_files) -> tuple:
    blocked = _mutmut_preconditions(ctx)
    if blocked is not None:
        return blocked, None
    targets, blocked = _mutmut_scope(ctx, py_files)
    if blocked is not None:
        return blocked, None
    work, _roots, blocked = _mutmut_setup(ctx, targets, _mutmut_changed_tests(py_files))
    if blocked is not None:
        return blocked, None

    cmd, scope_notes = _mutmut_command(ctx, work, targets)
    return _mutmut_run(ctx, work, cmd, targets, scope_notes)


# ---------------------------------------------------------------------------
# C7 — 두 언어 합치기
# ---------------------------------------------------------------------------

def _mutation_changed_python_files(ctx: gate.GateContext) -> list:
    """C7 이 볼 파이썬 변경 파일. 변경분의 단일 출처는 그대로 ctx.change.files 다."""
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_PY_SUFFIXES]


# ---------------------------------------------------------------------------
# 선언부 — 이 어댑터가 규격에 신고하는 사실 (계약 테스트가 동작과의 일치를 검사한다)
# ---------------------------------------------------------------------------

PYTHON_ADAPTER = score_mod.AdapterSpec(
    language="python",
    label="파이썬",
    tool="mutmut",
    config_key="mutation.python",
    # 변환표 = MUTMUT_STATUS_TO_GATE. 종료 코드 정수 → mutmut 낱말 변환
    # (MUTMUT_EXIT_CODE_TO_STATUS)은 변환표 앞의 어댑터 내부 단계다 — 규격은
    # "자기 어휘 → 게이트 어휘" 한 겹만 본다. 표에 없는 상태(suspicious /
    # caught by type check)는 원어 그대로 통과해 unknown 경로로 간다 (R4).
    status_map=MUTMUT_STATUS_TO_GATE,
    measure_unit="function",               # 함수 단위로 훑는다
    skip_report=("데코레이터 붙은 함수는 통째로 빠진다 — python_decorated_skips 가 "
                 "mutmut 의 규칙을 재현해 빠진 이름을 결과 문장에 신고한다"),
    # 앞의 것은 도구가 스스로 보는 것, 뒤 둘은 게이트 보강(_mutmut_stale_reason)이다.
    # 실패 각인의 무효화도 이 선언을 재사용한다 — 별도 조건을 만들면 두 무효화가
    # 어긋나는 자리가 생긴다.
    incremental_triggers=("함수 해시", "테스트 파일 변경분 포함", "대상 목록 변화"),
    target_syntax=("설정 파일 fnmatch 글롭. only_mutate 에만 glob.escape 를 건다 — "
                   "source_paths 와 also_copy 는 글롭이 아니라 경로라 이스케이프하면 매치가 깨진다"),
    field_confidence={"line": "reconstructed", "column": "absent",
                      "mutator": "absent", "tests": "tool"},
    tests_granularity="per-function",
    requires=("C1:python",),               # ctx.python_tests_status 를 본다
    workspace=("캐시 안에 회차를 넘어 사는 디렉토리 + 소스·테스트 심링크"
               "(mutmut_work_dir). 만료·정리 정책: 없음 (실측 18MB)"),
    copy_limitations=(
        "사본에 .git 이 없다 — git 을 부르는 테스트는 사본 안에서 돌 수 없다",
    ),
)
