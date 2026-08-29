"""검사 게이트 0단계 — 변경분 코드 검사 리포트.

`/check-code` 커맨드나 실행 흐름이 `python3 scripts/code_gate.py` 로 부른다.
git diff 로 이번에 바뀐 파일과 줄을 뽑아, 그 범위에 대해서만 일곱 가지를 재고
결과를 사람이 읽는 한국어 표(기본) 또는 JSON(`--json`)으로 출력한다.

  C1 테스트 / C2 커버리지 / C3 복잡도 / C4 CRAP / C5 중복 / C6 의존 방향 /
  C7 뮤테이션

핵심 계약 네 가지:

1. **항상 종료 코드 0.** 0단계는 리포트만 한다. 검사 결과가 나쁘든, 도구가 없든,
   내부에서 예외가 터지든, **명령줄 인자가 틀렸든** 종료 코드는 0이다.
   서브프로세스의 종료 코드도 게이트의 종료 코드로 전파하지 않는다. 게이트 판정
   때문에 개발 흐름이 멈추면 안 된다.
   단 `KeyboardInterrupt` 는 일부러 전파한다 — 사용자의 명시적 중단까지 삼키면
   Ctrl-C 로 죽지 않는 프로세스가 된다. `--help` 도 argparse 의 정상 종료(0)라
   그대로 둔다.
2. **항목별 실행 시간이 주 산출물이다.** 이 게이트가 개발 속도를 얼마나 잡아먹는지가
   존폐를 결정한다. 건너뛴 항목까지 전부 초를 찍는다.
3. **검사하지 않은 것을 통과처럼 보이지 않게 한다.** 도구가 없으면 "건너뜀"으로
   명시하고 설치 방법을 함께 적는다.
4. **호출 흐름을 구분하는 코드를 넣지 않는다.** 이 게이트는 여러 흐름이 공유한다.
   `--track` / `--mode` / `--flow` / `--stage` 같은 인자는 존재하지 않는다.
   게이트는 검사하고 결과를 내놓기만 하고, 언제 부를지는 각 흐름이 정한다.

표준 라이브러리만 사용한다. 검사 대상 프로젝트에는 이 저장소의 가상환경이 없어
시스템 `python3` 로 어디서든 실행돼야 한다. 검사 대상 프로젝트의 도구
(pytest / coverage / lizard / jscpd / stryker 등)는 서브프로세스로 부르고, 없으면 건너뛴다.
"""

from __future__ import annotations

import argparse
import ast
import bisect
import csv
import fnmatch
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# 기준값 — 설정 파일(.code-gate.json)이 최종 권위이고, 아래는 그 폴백이다.
#
# ⚠️ RISK(config): 기준값은 사람만 수정 — 에이전트가 검사를 통과하지 못할 때
# 임계를 낮추거나 exclude 를 늘려 회피하는 행동을 막는다. 통과 못 하면 기준이
# 아니라 코드를 고친다 — by 검사게이트-0단계
# ---------------------------------------------------------------------------

CONFIG_NAME = ".code-gate.json"
DEFAULT_LAYERS_FILE = ".code-gate-layers.json"

DEFAULT_CRAP_THRESHOLD = 6          # 사람 기준 4가 아니라 에이전트 기준 6
DEFAULT_COMPLEXITY_THRESHOLD = 10   # 함수 하나의 순환 복잡도 상한
DEFAULT_DUP_MIN_LINES = 5           # 중복으로 셀 최소 줄 수
DEFAULT_DUP_MIN_TOKENS = 50         # 중복으로 셀 최소 토큰 수
DEFAULT_TIMEOUT_SECONDS = 60        # 항목별 서브프로세스 상한
DEFAULT_TIMEOUT_SECONDS_TESTS = 300 # 테스트 항목만 따로 — 스위트가 긴 저장소 대비

# 뮤테이션 — 0단계에서는 켜 두고 숫자만 낸다. 기준 80 은 아직 아무것도 막지 않는다.
DEFAULT_MUTATION_ENABLED = True
DEFAULT_MUTATION_SCORE_THRESHOLD = 80.0     # 살아남은 변이 비율의 기준 (리포트용)
DEFAULT_MUTATION_TIMEOUT_SECONDS = 600      # 뮤테이션은 다른 항목보다 자릿수로 오래 걸린다
DEFAULT_MUTATION_JAVASCRIPT = "stryker"     # 자바스크립트 뮤테이션 도구
# 이 블록에서 우리가 읽는 키. 여기 없는 키는 무시하되 반드시 알린다 —
# 명령줄 오타는 알려 주면서 설정 파일 오타만 조용히 버리면 사용자가 원인을 못 찾는다.
MUTATION_CONFIG_KEYS = frozenset({"enabled", "score_threshold", "timeout_seconds", "javascript"})

# git 빈 트리 해시 — 커밋이 하나도 없는 저장소에서 base 로 쓴다.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# ⚠️ RISK(exit-code): 아래 인자들은 대상 도구를 임계 미달 시 비-0 으로 종료시키거나
# (pytest -x, node --test-coverage-*, jest --coverageThreshold, jscpd --threshold)
# 동의 없이 네트워크에서 패키지를 받아온다 (npx --yes). 둘 다 0단계 계약을 깬다.
# `_run()` 이 실행 직전에 막는다 — 목록에 추가는 해도 제거는 하지 않는다.
# — by 검사게이트-0단계
_FORBIDDEN_SUBPROCESS_ARGS = (
    "-x",
    "--exitfirst",
    "--maxfail",
    "--test-coverage-lines",
    "--test-coverage-branches",
    "--test-coverage-functions",
    "--coverageThreshold",
    "--threshold",
    "--yes",
)

PY_SUFFIXES = frozenset({".py"})
JS_SUFFIXES = frozenset({".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})

# 어느 깊이에서든 내려가지 않는 이름 — 빌드 산출물과 패키지 캐시.
#
# 디렉토리 탐색과 **변경분 집합** 양쪽에 적용된다. 변경분 쪽에 안 걸면, 아직
# gitignore 되지 않은 의존성 디렉토리(npm install / venv 직후가 정확히 그 상태)가
# 통째로 "이번 변경분"이 되어 검사 시간이 자릿수로 늘어난다 — R1 이 걸린 지점이다.
PRUNE_DIRS = frozenset({
    "node_modules", "__pycache__", ".git", ".venv", "venv", "site-packages",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".worktrees",
})

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_DIFF_NEWFILE_RE = re.compile(r"^\+\+\+ (?:b/)?(.*)$")
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_PYTEST_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed)\b")
_NODE_TAP_RE = re.compile(r"^#\s+(pass|fail)\s+(\d+)\s*$", re.MULTILINE)
# vitest / jest 요약줄 — TAP 을 내지 않는 러너의 개수를 읽는다.
_JS_SUMMARY_RE = re.compile(r"^\s*Tests[:\s]", re.MULTILINE)
_JS_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed)")
_TESTPATHS_RE = re.compile(r"^\s*testpaths\s*=\s*(.+)$", re.MULTILINE)
# lizard 의 location 필드: 이름@시작-끝@파일
_LIZARD_LOC_RE = re.compile(r"@(\d+)-(\d+)@")
_JS_IMPORT_RE = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(\s*|\brequire\s*\(\s*|\bimport\s+)['"]([^'"]+)['"]"""
)

# 커버리지를 어떻게 구했는지 — 리포트에 그대로 보여준다 (무엇을 잰 건지 감추지 않는다).
COVERAGE_SOURCE_KO = {
    "exact-start-line": "시작줄 일치",
    "range-fallback": "줄 범위 추정",
    "range-empty": "측정 줄 없음",
    "no-coverage-data": "데이터 없음",
    "istanbul-overlap": "범위 겹침",
    "join-mismatch": "결합 실패",
}

STATUS_KO = {
    "ok": "통과",
    "findings": "발견",
    "skipped": "건너뜀",
    "error": "오류",
    "timeout": "시간초과",
}


# ---------------------------------------------------------------------------
# 결과 타입
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CheckResult:
    """검사 항목 하나의 결과.

    `reason`(영어, 로그·기계용)과 `human_reason`(한국어, 사용자 노출용)을 나눠
    담는다 — 이 저장소의 `PreflightResult` 관행을 그대로 따른다.
    `code` 는 C1..C7 안정 식별자로, 표시 이름이 바뀌어도 소비자가 안 깨진다.
    """

    code: str
    name: str
    label: str
    status: str          # ok | findings | skipped | error | timeout
    seconds: float
    reason: str = ""
    human_reason: str = ""
    install_hint: str | None = None
    findings: tuple = ()

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "label": self.label,
            "status": self.status,
            "seconds": self.seconds,
            "reason": self.reason,
            "human_reason": self.human_reason,
            "install_hint": self.install_hint,
            "findings": list(self.findings),
        }


@dataclass(frozen=True)
class GateConfig:
    source: str | None
    crap_threshold: float
    complexity_threshold: int
    dup_min_lines: int
    dup_min_tokens: int
    timeout_seconds: int
    timeout_seconds_tests: int
    layers_file: str
    exclude: tuple[str, ...]
    mutation_enabled: bool
    mutation_score_threshold: float
    mutation_timeout_seconds: int
    mutation_javascript: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ChangeSet:
    """변경분 — 게이트가 검사할 범위의 단일 진입점.

    `lines` 의 값이 `None` 이면 "파일 전체가 변경분"이라는 뜻이다 (추적되지 않은
    새 파일). 소비자가 자체로 변경분을 다시 해석하면 판정이 갈리므로, 변경 범위
    질의는 전부 `overlaps()` 를 거친다.
    """

    base: str
    base_reason: str
    files: tuple[str, ...]
    excluded: tuple[str, ...]
    lines: dict
    skip_reason: str = ""
    skip_reason_en: str = ""
    pruned: tuple[str, ...] = ()
    base_problem: str = ""

    def overlaps(self, rel_path: str, start: int | None, end: int | None) -> bool:
        if rel_path not in self.lines:
            return False
        changed = self.lines[rel_path]
        if changed is None:
            return True
        if start is None or end is None:
            return True
        if end < start:
            start, end = end, start
        return not changed.isdisjoint(range(start, end + 1))


@dataclass(frozen=True)
class FileCoverage:
    kind: str                       # coverage-json | istanbul | lcov
    percent: float | None
    functions: tuple                # ((start_line, ratio), ...)
    executed: frozenset
    missing: frozenset
    istanbul: dict | None = None


@dataclass
class GateContext:
    """항목 사이에 넘기는 상태. C1 이 만든 커버리지 데이터를 C2 가, C2/C3 결과를 C4 가 읽는다."""

    repo_root: Path
    config: GateConfig
    change: ChangeSet
    langs: dict
    tools: dict
    python_exe: str
    tmpdir: Path
    notes: list = field(default_factory=list)
    coverage_data_file: Path | None = None
    js_lcov_files: list = field(default_factory=list)
    js_istanbul_files: list = field(default_factory=list)
    coverage_map: dict = field(default_factory=dict)
    complexity_rows: list = field(default_factory=list)
    complexity_failures: int = 0
    coverage_wrapped: bool = False      # 테스트를 커버리지 계측 아래에서 돌렸는가 (C1 시간에 포함)


# ---------------------------------------------------------------------------
# 서브프로세스 — 단일 진입점
# ---------------------------------------------------------------------------

def _forbidden_arg(cmd) -> str | None:
    """R2(항상 exit 0)를 깨는 인자가 명령줄에 섞였는지 본다. 없으면 None."""
    for token in cmd:
        head = str(token).split("=", 1)[0]
        if head in _FORBIDDEN_SUBPROCESS_ARGS:
            return str(token)
    return None


def _run(cmd, *, cwd, timeout):
    """게이트의 모든 서브프로세스가 지나는 단 하나의 문. 여기서만 프로세스를 띄운다.

    실행 직전에 금지 인자를 막는다 — 나중 세션이 "빨리 끝내려고" pytest 에 -x 를
    붙이는 식의 회귀를 코드 리뷰가 아니라 실행 시점에 잡기 위한 것이다.
    종료 코드는 호출자가 판정 재료로만 쓰고, 게이트 종료 코드로 전파하지 않는다.
    """
    bad = _forbidden_arg(cmd)
    if bad is not None:
        raise ValueError(f"금지된 서브프로세스 인자입니다 (게이트가 비-0 종료할 위험): {bad}")
    return subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _git(repo_root: Path, args, timeout: int = 30):
    return _run(["git", "-c", "core.quotepath=false", *args], cwd=repo_root, timeout=timeout)


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

def _match_glob(rel_posix: str, pattern: str) -> bool:
    """저장소 상대 POSIX 경로를 glob 패턴과 대조하는 단일 함수.

    `fnmatch` 의미론상 `*` 와 `**` 는 둘 다 `/` 를 넘어 매치된다. 즉 `scripts/**` 는
    `scripts/tests/test_x.py` 도 잡는다 — 이 게이트가 의도한 동작이다.
    `exclude` 와 레이어 규칙이 같은 함수를 쓴다. 소비자가 따로 매칭하면 두 곳의
    판정이 갈린다.
    """
    return fnmatch.fnmatchcase(rel_posix, pattern)


def _positive_number(raw, default, key: str, notes: list, cast=int):
    """설정 값이 양수일 때만 받아들이고, 아니면 안전한 방향(기본값)으로 되돌린다."""
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        notes.append(f"설정 파일의 {key} 값이 숫자가 아니라 기본값 {default} 을 사용했습니다.")
        return default
    if raw <= 0:
        notes.append(f"설정 파일의 {key} 값이 0 이하라 기본값 {default} 을 사용했습니다.")
        return default
    value = cast(raw)
    if value <= 0:
        # 0.5 같은 값을 정수로 바꾸면 0 이 된다. 0 이하를 막으려던 검사가 스스로 0 을
        # 만들어 내는 자리라, 바꾼 뒤에 한 번 더 본다.
        notes.append(f"설정 파일의 {key} 값 {raw} 이 너무 작아 기본값 {default} 을 사용했습니다.")
        return default
    return value


def _note_unknown_mutation_keys(mutation: dict, notes: list) -> None:
    """읽지 않은 키를 알린다. 명령줄 오타는 알려 주면서 설정 파일 오타만 버리면 안 된다."""
    unknown = sorted(str(k) for k in mutation if str(k) not in MUTATION_CONFIG_KEYS)
    if unknown:
        notes.append("설정 파일의 mutation 항목에서 알 수 없는 키를 무시했습니다: " + ", ".join(unknown))


def _mutation_config(data: dict, notes: list) -> tuple:
    """mutation 블록에서 참/거짓과 문자열 값을 꺼낸다. 숫자 두 개는 `_positive_number` 가 본다.

    반환은 (enabled, javascript, 원본 블록). 어떤 실패든 기본값으로 되돌리고 사유를 남긴다 —
    설정이 안 읽혔는데 리포트가 정상처럼 보이면 무엇을 기준으로 쟀는지 알 수 없다.
    """
    mutation = data.get("mutation")
    if not isinstance(mutation, dict):
        if mutation is not None:
            notes.append("설정 파일의 mutation 항목이 객체가 아니라 기본값을 사용했습니다.")
        mutation = {}

    enabled = mutation.get("enabled", DEFAULT_MUTATION_ENABLED)
    if not isinstance(enabled, bool):
        notes.append(f"설정 파일의 mutation.enabled 값이 참/거짓이 아니라 기본값 {DEFAULT_MUTATION_ENABLED} 을 사용했습니다.")
        enabled = DEFAULT_MUTATION_ENABLED

    js_tool = mutation.get("javascript", DEFAULT_MUTATION_JAVASCRIPT)
    if not isinstance(js_tool, str) or not js_tool.strip():
        notes.append(f"설정 파일의 mutation.javascript 값이 문자열이 아니라 기본값 {DEFAULT_MUTATION_JAVASCRIPT} 을 사용했습니다.")
        js_tool = DEFAULT_MUTATION_JAVASCRIPT

    _note_unknown_mutation_keys(mutation, notes)
    return enabled, js_tool.strip(), mutation


def load_config(path: Path) -> GateConfig:
    """기준값 설정을 읽는다. 어떤 실패든 기본값으로 폴백하고 사유를 notes 에 남긴다.

    조용히 넘어가지 않는 것이 요점이다 — 설정이 안 읽혔는데 리포트가 정상처럼
    보이면 무엇을 기준으로 판정했는지 알 수 없다.
    """
    notes: list = []
    data: dict = {}
    source: str | None = None

    if not path.exists():
        notes.append(f"설정 파일이 없어 기본값을 사용했습니다 (CRAP {DEFAULT_CRAP_THRESHOLD} / 복잡도 {DEFAULT_COMPLEXITY_THRESHOLD}).")
    else:
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, ValueError) as exc:
            raw = None
            notes.append(f"설정 파일을 읽지 못해 기본값을 사용했습니다 ({type(exc).__name__}).")
        if isinstance(raw, dict):
            data = raw
            source = str(path)
        elif raw is not None:
            notes.append("설정 파일이 JSON 객체가 아니라 기본값을 사용했습니다.")

    dup = data.get("duplication")
    if not isinstance(dup, dict):
        if dup is not None:
            notes.append("설정 파일의 duplication 항목이 객체가 아니라 기본값을 사용했습니다.")
        dup = {}

    exclude_raw = data.get("exclude", [])
    if isinstance(exclude_raw, list):
        exclude = tuple(str(x) for x in exclude_raw if isinstance(x, str))
    else:
        exclude = ()
        notes.append("설정 파일의 exclude 항목이 목록이 아니라 무시했습니다.")

    enabled, js_tool, mutation = _mutation_config(data, notes)

    layers_file = data.get("layers_file", DEFAULT_LAYERS_FILE)
    if not isinstance(layers_file, str) or not layers_file.strip():
        layers_file = DEFAULT_LAYERS_FILE
        notes.append("설정 파일의 layers_file 값이 문자열이 아니라 기본값을 사용했습니다.")

    return GateConfig(
        source=source,
        crap_threshold=_positive_number(data.get("crap_threshold"), DEFAULT_CRAP_THRESHOLD, "crap_threshold", notes, float),
        complexity_threshold=_positive_number(data.get("complexity_threshold"), DEFAULT_COMPLEXITY_THRESHOLD, "complexity_threshold", notes),
        dup_min_lines=_positive_number(dup.get("min_lines"), DEFAULT_DUP_MIN_LINES, "duplication.min_lines", notes),
        dup_min_tokens=_positive_number(dup.get("min_tokens"), DEFAULT_DUP_MIN_TOKENS, "duplication.min_tokens", notes),
        timeout_seconds=_positive_number(data.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS, "timeout_seconds", notes),
        timeout_seconds_tests=_positive_number(data.get("timeout_seconds_tests"), DEFAULT_TIMEOUT_SECONDS_TESTS, "timeout_seconds_tests", notes),
        layers_file=layers_file,
        exclude=exclude,
        mutation_enabled=enabled,
        mutation_score_threshold=_positive_number(
            mutation.get("score_threshold"), DEFAULT_MUTATION_SCORE_THRESHOLD,
            "mutation.score_threshold", notes, float),
        mutation_timeout_seconds=_positive_number(
            mutation.get("timeout_seconds"), DEFAULT_MUTATION_TIMEOUT_SECONDS,
            "mutation.timeout_seconds", notes),
        mutation_javascript=js_tool,
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# 변경분 (R3)
# ---------------------------------------------------------------------------

def resolve_base(repo_root: Path, explicit: str | None) -> tuple[str, str]:
    """비교 기준을 정한다. 앞에서 성공하면 멈춘다. 반환은 (ref, 한국어 사유)."""
    if explicit:
        return explicit, "사용자가 지정한 기준입니다."
    probe = _git(repo_root, ["rev-parse", "--verify", "--quiet", "main"])
    if probe.returncode == 0 and probe.stdout.strip():
        return "main", "기본 브랜치 main 을 기준으로 잡았습니다."
    head = _git(repo_root, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"])
    if head.returncode == 0 and head.stdout.strip():
        ref = head.stdout.strip()
        return ref, f"원격 기본 브랜치({ref})를 기준으로 잡았습니다."
    prev = _git(repo_root, ["rev-parse", "--verify", "--quiet", "HEAD~1"])
    if prev.returncode == 0 and prev.stdout.strip():
        return "HEAD~1", "직전 커밋(HEAD~1)을 기준으로 잡았습니다."
    return EMPTY_TREE, "비교할 커밋이 없어 빈 트리를 기준으로 잡았습니다."


@dataclass
class _DiffState:
    """diff 를 읽는 동안의 파일 구획 상태.

    `in_hunk` 가 요점이다. 한 번 헝크 본문에 들어가면 그 구획이 끝날 때까지
    `+++` 를 헤더로 보지 않는다.
    """

    current: str | None = None      # 지금 줄 번호를 모으는 대상 (헤더로 확정된 것)
    path: str | None = None         # 구획이 가리키는 파일 (헝크가 없어도 알 수 있다)
    resolved: bool = False          # 이 구획에서 `+++` 헤더를 봤는가
    in_hunk: bool = False           # 헝크 본문 안인가


def parse_diff(text: str) -> dict:
    """`git diff -U0` 출력에서 파일별 변경 줄 번호를 뽑는다.

    `@@ -a,b +c,d @@` 와 개수를 생략한 `@@ -a +c @@` 를 둘 다 읽는다. 삭제만 있는
    헝크(d=0)는 삭제 위치 한 줄을 변경으로 표시한다 — 함수 안에서 줄을 지운 것도
    그 함수의 변경이기 때문이다.

    헝크가 없는 파일 구획도 놓치지 않는다. 내용이 같은 rename(유사도 100%)과
    파일 모드만 바뀐 변경은 git 이 `+++` 줄을 내지 않아, `+++` 만 보면 그 파일이
    통째로 검사 대상에서 빠진다. 파일을 레이어 밖으로 옮기기만 한 커밋이 정확히
    그 형태라서, 하필 그것을 봐야 하는 의존 방향 검사가 못 돈다.
    """
    result: dict = {}
    state = _DiffState()
    for line in text.splitlines():
        _consume_diff_line(result, state, line)
    _flush_headerless(result, state)
    return result


def _consume_diff_line(result: dict, state: _DiffState, line: str) -> None:
    if line.startswith("diff --git "):
        _flush_headerless(result, state)
        m = _DIFF_HEADER_RE.match(line)
        state.current, state.resolved, state.in_hunk = None, False, False
        state.path = m.group(2).strip() if m else None
        return
    if not state.in_hunk and line.startswith("rename to "):
        state.path = line[len("rename to "):].strip() or state.path
        return
    if not state.in_hunk and line.startswith("+++ "):
        _consume_diff_target(result, state, line)
        return
    if line.startswith("@@"):
        _apply_hunk(result, state, line)


def _consume_diff_target(result: dict, state: _DiffState, line: str) -> None:
    m = _DIFF_NEWFILE_RE.match(line)
    target = m.group(1).strip() if m else ""
    state.resolved = True
    state.current = None if (not target or target == "/dev/null") else target
    if state.current is not None:
        state.path = state.current
        result.setdefault(state.current, set())


def _apply_hunk(result: dict, state: _DiffState, line: str) -> None:
    m = _HUNK_RE.match(line)
    if m is None:
        return
    state.in_hunk = True
    changed = result.get(state.current) if state.current is not None else None
    if changed is None:                 # 대상이 없거나 이미 '파일 전체 변경'
        return
    start = int(m.group(1))
    count = 1 if m.group(2) is None else int(m.group(2))
    if count <= 0:
        changed.add(max(start, 1))
    else:
        changed.update(range(start, start + count))


def _flush_headerless(result: dict, state: _DiffState) -> None:
    """`+++` 헤더 없이 끝난 파일 구획을 '파일 전체가 변경분'(`None`)으로 등록한다."""
    if state.path and not state.resolved and state.path not in result:
        result[state.path] = None


def _merge_lines(target: dict, extra: dict) -> None:
    """변경 줄을 합친다. `None`("파일 전체가 변경분")은 어떤 줄 집합보다 넓어서 이긴다.

    양쪽 다 `None` 을 낼 수 있다 — 추적되지 않은 새 파일과, 헝크가 없는 파일 구획
    (내용이 같은 rename / 모드만 바뀐 변경)이다.
    """
    for path, lines in extra.items():
        if lines is None or (path in target and target[path] is None):
            target[path] = None
            continue
        target.setdefault(path, set()).update(lines)


def collect_changes(repo_root: Path, base: str, base_reason: str, exclude: tuple) -> ChangeSet:
    """이번에 바뀐 파일과 줄을 모은다 — 변경분 해석의 단일 진입점.

    커밋된 것(base 대비) + 미커밋 + 스테이지 + 추적되지 않은 새 파일 네 갈래를
    합친다. 커밋 전 루프에서 도는 게 이 게이트의 주 용도라 미커밋 갈래가 필수다.
    """
    if shutil.which("git") is None:
        return ChangeSet(base, base_reason, (), (), {}, "git 이 없어 변경분을 계산하지 못했습니다.", "git not found")
    inside = _git(repo_root, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return ChangeSet(base, base_reason, (), (), {}, "git 저장소가 아니라 변경분을 계산하지 못했습니다.", "not a git repository")

    lines, base_problem = _raw_changed_lines(repo_root, base)
    kept, excluded, pruned = _apply_exclude(repo_root, lines, exclude)
    skip = "" if kept else "변경된 파일이 없습니다."
    skip_en = "" if kept else "no changed files"
    return ChangeSet(base, base_reason, tuple(kept), tuple(excluded), kept, skip, skip_en,
                     tuple(pruned), base_problem)


def _raw_changed_lines(repo_root: Path, base: str) -> tuple:
    """네 갈래(base 대비 / 미커밋 / 스테이지 / 추적 안 됨)를 합친 파일별 변경 줄.

    반환은 (변경 줄, base 문제 한국어 문장). base 로 준 ref 가 없으면 두 diff 시도가
    모두 실패하는데, 그것을 조용히 넘기면 아무것도 비교하지 못한 채 완전히 깨끗한
    리포트가 나온다. 그래서 사유를 밖으로 올린다.
    """
    lines: dict = {}
    acmr = "--diff-filter=ACMR"
    base_problem = ""

    ranged = _git(repo_root, ["diff", "-U0", acmr, "--merge-base", base, "HEAD"])
    if ranged.returncode != 0:
        ranged = _git(repo_root, ["diff", "-U0", acmr, base, "HEAD"])
    if ranged.returncode == 0:
        _merge_lines(lines, parse_diff(ranged.stdout))
    elif _git(repo_root, ["rev-parse", "--verify", "--quiet", "HEAD"]).returncode == 0:
        # 커밋이 하나도 없는 저장소에서는 비교할 커밋 자체가 없어 손실이 아니다.
        # 커밋이 있는데도 실패했다면 그 base 로는 아무것도 비교하지 못한 것이다.
        base_problem = (f"기준 {base} 를 해석하지 못해 커밋된 변경분은 비교하지 못했습니다 "
                        f"(미커밋·스테이지·추적되지 않은 파일만 검사했습니다).")

    for args in (["diff", "-U0", acmr, "HEAD"], ["diff", "-U0", acmr, "--cached"]):
        proc = _git(repo_root, args)
        if proc.returncode == 0:
            _merge_lines(lines, parse_diff(proc.stdout))

    untracked = _git(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"])
    if untracked.returncode == 0:
        for path in untracked.stdout.split("\0"):
            if path.strip():
                lines[path.strip()] = None      # 파일 전체가 변경분
    return lines, base_problem


def _in_pruned_dir(rel_posix: str) -> bool:
    """의존성·빌드 디렉토리 안의 경로인가. 사용자 exclude 와 무관하게 언제나 뺀다."""
    return any(part in PRUNE_DIRS for part in rel_posix.split("/")[:-1])


def _apply_exclude(repo_root: Path, lines: dict, exclude: tuple) -> tuple:
    """변경분에서 뺄 것을 뺀다. 반환은 (남긴 것, exclude 로 뺀 것, 프루닝으로 뺀 것).

    프루닝을 exclude 와 따로 세는 이유는 R4 다 — 몇 개를 왜 뺐는지 리포트에 남긴다.
    사용자 설정을 건드리는 것이 아니므로 R6(기준 회피 금지)와도 충돌하지 않는다.
    """
    kept: dict = {}
    excluded: list = []
    pruned: list = []
    for path, changed in sorted(lines.items()):
        if _in_pruned_dir(path):
            pruned.append(path)
        elif any(_match_glob(path, pattern) for pattern in exclude):
            excluded.append(path)
        elif (repo_root / path).is_file():
            kept[path] = None if changed is None else frozenset(changed)
    return kept, excluded, pruned


# ---------------------------------------------------------------------------
# 언어 / 도구 탐지
# ---------------------------------------------------------------------------

def detect_languages(files) -> dict:
    langs: dict = {"python": [], "javascript": []}
    for rel in files:
        suffix = Path(rel).suffix.lower()
        if suffix in PY_SUFFIXES:
            langs["python"].append(rel)
        elif suffix in JS_SUFFIXES:
            langs["javascript"].append(rel)
    return langs


def resolve_python(repo_root: Path) -> str:
    """검사 대상 프로젝트의 인터프리터. 프로젝트 가상환경을 게이트 자신보다 우선한다."""
    candidates: list = []
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidates += [Path(venv) / "bin" / "python", Path(venv) / "Scripts" / "python.exe"]
    for name in (".venv", "venv"):
        candidates += [repo_root / name / "bin" / "python", repo_root / name / "Scripts" / "python.exe"]
    for cand in candidates:
        try:
            if cand.is_file():
                return str(cand)
        except OSError:
            continue
    return sys.executable or shutil.which("python3") or "python3"


_PROBE_CODE = (
    "import importlib.util as u, json, sys\n"
    "out = {}\n"
    "for n in sys.argv[1:]:\n"
    "    try:\n"
    "        out[n] = u.find_spec(n) is not None\n"
    "    except Exception:\n"
    "        out[n] = False\n"
    "print(json.dumps(out))\n"
)


def _probe_python_modules(repo_root: Path, python_exe: str, modules, timeout: int) -> dict:
    """모듈 유무를 서브프로세스 한 번에 확인한다. 실패하면 전부 '없음' 으로 본다."""
    found = {name: False for name in modules}
    try:
        proc = _run([python_exe, "-c", _PROBE_CODE, *modules], cwd=repo_root, timeout=timeout)
        parsed = json.loads(proc.stdout or "{}") if proc.returncode == 0 else {}
        if isinstance(parsed, dict):
            found.update({k: bool(v) for k, v in parsed.items() if k in found})
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return found


def probe_tools(repo_root: Path, python_exe: str, timeout: int = 30) -> dict:
    """도구 유무를 최소 비용으로 확인한다.

    파이썬 모듈은 서브프로세스 **한 번**에 전부 본다 (`find_spec` — 모듈을 실제로
    import 하지 않는다). npm 도구는 `node_modules/.bin` 파일 존재 확인으로 끝낸다 —
    `npx --no-install <tool> --version` 은 없을 때 1초 가까이 버린다.
    """
    tools: dict = {}
    modules = ("pytest", "coverage", "lizard")
    found = _probe_python_modules(repo_root, python_exe, modules, timeout)
    for name in modules:
        tools[name] = {
            "available": found[name],
            "path": f"{python_exe} -m {name}" if found[name] else None,
            "install_hint": f"{python_exe} -m pip install {name}",
        }

    for name, hint in (("jscpd", "npm i -D jscpd"),
                       ("depcruise", "npm i -D dependency-cruiser"),
                       ("stryker", "npm i -D @stryker-mutator/core")):
        local = repo_root / "node_modules" / ".bin" / name
        path = str(local) if local.exists() else shutil.which(name)
        tools[name] = {"available": path is not None, "path": path, "install_hint": hint}

    for name in ("node", "git"):
        path = shutil.which(name)
        tools[name] = {"available": path is not None, "path": path, "install_hint": f"{name} 를 설치하십시오."}
    return tools


def _tool(ctx: GateContext, name: str) -> dict:
    return ctx.tools.get(name, {"available": False, "path": None, "install_hint": None})


def _skip(human: str, reason: str, install_hint: str | None = None) -> dict:
    return {"status": "skipped", "reason": reason, "human_reason": human, "install_hint": install_hint}


# ---------------------------------------------------------------------------
# C1 — 테스트
# ---------------------------------------------------------------------------

def _iter_dirs(repo_root: Path, max_depth: int = 4):
    stack = [(repo_root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if entry.name in PRUNE_DIRS or entry.name.startswith("."):
                continue
            yield entry
            stack.append((entry, depth + 1))


def _configured_testpaths(repo_root: Path) -> list:
    for name in ("pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"):
        path = repo_root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _TESTPATHS_RE.search(text)
        if m:
            raw = m.group(1).strip().strip("[]")
            parts = [p.strip().strip("'\"',") for p in re.split(r"[,\s]+", raw) if p.strip()]
            kept = [p for p in parts if (repo_root / p).exists()]
            if kept:
                return kept
    return []


def detect_pytest_paths(repo_root: Path) -> list:
    """pytest 에 넘길 테스트 경로. 설정 파일의 testpaths 가 있으면 그것이 우선."""
    configured = _configured_testpaths(repo_root)
    if configured:
        return configured
    found = []
    for directory in _iter_dirs(repo_root):
        if directory.name not in ("tests", "test"):
            continue
        try:
            has_tests = any(
                p.name.startswith("test_") or p.name.endswith("_test.py")
                for p in directory.iterdir() if p.suffix == ".py"
            )
        except OSError:
            continue
        if has_tests:
            found.append(directory.relative_to(repo_root).as_posix())
    return sorted(found)


def _parse_pytest_counts(text: str) -> dict:
    for line in reversed(text.splitlines()):
        hits = _PYTEST_COUNT_RE.findall(line)
        if hits:
            counts: dict = {}
            for number, kind in hits:
                counts[kind.rstrip("s") if kind.startswith("error") else kind] = int(number)
            return counts
    return {}


def _run_python_tests(ctx: GateContext) -> dict:
    paths = detect_pytest_paths(ctx.repo_root)
    if not paths:
        return {"status": "skipped", "human": "파이썬 테스트 경로를 찾지 못했습니다.", "reason": "no pytest paths"}
    if not _tool(ctx, "pytest")["available"]:
        return {"status": "skipped", "human": "pytest 가 설치돼 있지 않습니다.",
                "reason": "pytest missing", "install_hint": _tool(ctx, "pytest")["install_hint"]}

    proc = _run(_pytest_command(ctx, paths), cwd=ctx.repo_root, timeout=ctx.config.timeout_seconds_tests)
    return _pytest_outcome(proc)


def _pytest_command(ctx: GateContext, paths: list) -> list:
    """커버리지가 있으면 테스트를 그 아래에서 돌린다 — 스위트를 두 번 실행하지 않기 위해서다.

    그래서 C1 의 시간에는 커버리지 계측 부담(파이썬 3.12+ 기준 실측 약 8%)이 포함되고,
    C2 의 시간은 리포트 내보내기만을 뜻한다.
    """
    tail = ["-m", "pytest", *paths, "-q", "-p", "no:cacheprovider"]
    if not _tool(ctx, "coverage")["available"]:
        return [ctx.python_exe, *tail]
    ctx.coverage_data_file = ctx.tmpdir / "coverage.data"
    ctx.coverage_wrapped = True
    return [ctx.python_exe, "-m", "coverage", "run",
            f"--data-file={ctx.coverage_data_file}", f"--source={ctx.repo_root}", *tail]


def _pytest_outcome(proc) -> dict:
    counts = _parse_pytest_counts(proc.stdout + "\n" + proc.stderr)
    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0) + counts.get("error", 0)
    if proc.returncode == 5 and not counts:
        return {"status": "skipped", "human": "수집된 파이썬 테스트가 없습니다.", "reason": "pytest collected nothing"}
    if failed:
        tail = [ln for ln in proc.stdout.splitlines() if ln.startswith(("FAILED", "ERROR"))]
        return {"status": "findings", "human": f"{passed}개 통과, {failed}개 실패",
                "reason": f"pytest {passed} passed {failed} failed",
                "findings": [{"runner": "pytest", "detail": line} for line in tail[:20]]}
    if not counts and proc.returncode != 0:
        return {"status": "findings", "human": f"pytest 가 비정상 종료했습니다 (종료 코드 {proc.returncode}).",
                "reason": f"pytest exited {proc.returncode}",
                "findings": [{"runner": "pytest", "detail": (proc.stderr or proc.stdout).strip()[-500:]}]}
    return {"status": "ok", "human": f"{passed}개 통과, 0개 실패", "reason": f"pytest {passed} passed 0 failed"}


def _read_json_object(path: Path) -> dict:
    """JSON 객체를 읽는다. 없거나 깨졌거나 객체가 아니면 빈 dict."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _has_config(repo_root: Path, stem: str, extensions) -> bool:
    return any((repo_root / f"{stem}{ext}").is_file() for ext in extensions)


def _detect_js_runner(repo_root: Path) -> str | None:
    pkg = _read_json_object(repo_root / "package.json")
    dependencies = {**(pkg.get("devDependencies") or {}), **(pkg.get("dependencies") or {})}
    if "vitest" in dependencies or _has_config(repo_root, "vitest.config", (".js", ".ts", ".mjs")):
        return "vitest"
    if "jest" in dependencies or "jest" in pkg or _has_config(repo_root, "jest.config", (".js", ".ts", ".mjs", ".cjs")):
        return "jest"
    if shutil.which("node"):
        return "node"
    return None


def _run_js_tests(ctx: GateContext) -> dict:
    runner = _detect_js_runner(ctx.repo_root)
    if runner is None:
        return {"status": "skipped", "human": "자바스크립트 테스트 러너를 찾지 못했습니다.", "reason": "no js runner"}

    if runner == "node":
        if not _tool(ctx, "node")["available"]:
            return {"status": "skipped", "human": "node 가 설치돼 있지 않습니다.", "reason": "node missing",
                    "install_hint": "node 를 설치하십시오."}
        lcov = ctx.tmpdir / "js-coverage.info"
        includes = []
        for rel in ctx.langs["javascript"]:
            includes += [f"--test-coverage-include={rel}"]
        cmd = ["node", "--test", "--experimental-test-coverage", *includes,
               "--test-reporter=tap", "--test-reporter-destination=stdout",
               "--test-reporter=lcov", f"--test-reporter-destination={lcov}"]
        ctx.js_lcov_files.append(lcov)
    else:
        binary = ctx.repo_root / "node_modules" / ".bin" / runner
        if not binary.exists():
            return {"status": "skipped", "human": f"{runner} 가 로컬에 설치돼 있지 않습니다.",
                    "reason": f"{runner} missing", "install_hint": f"npm i -D {runner}"}
        cov_dir = ctx.tmpdir / "js-cov"
        if runner == "vitest":
            # 리포터를 지정하지 않는다 — vitest 4 에서 `basic` 이 없어졌고, 지정하면
            # 사용자 정의 리포터 모듈로 읽으려다 기동 단계에서 죽는다. 기본 리포터는
            # 모든 판본에서 `Tests  N passed` 요약줄을 내므로 `_js_counts` 가 그대로 읽는다.
            cmd = [str(binary), "run", "--coverage",
                   "--coverage.reporter=json", f"--coverage.reportsDirectory={cov_dir}"]
        else:
            cmd = [str(binary), "--ci", "--coverage", "--coverageReporters=json",
                   f"--coverageDirectory={cov_dir}"]
        ctx.js_istanbul_files.append(cov_dir / "coverage-final.json")

    ctx.coverage_wrapped = True         # 세 러너 모두 커버리지 계측을 켠 채 돈다
    proc = _run(cmd, cwd=ctx.repo_root, timeout=ctx.config.timeout_seconds_tests)
    return _js_outcome(runner, proc.stdout + "\n" + proc.stderr, proc.returncode)


def _js_counts(output: str) -> dict:
    """실행된 테스트 개수. node 의 TAP(`# pass N`)이 우선, 없으면 vitest/jest 요약줄.

    `known` 이 False 면 개수를 **읽지 못한** 것이고, True 인데 0 이면 실제로 0개다.
    둘을 합치면 "돌지도 않았는데 0개 통과"를 통과로 읽게 된다.
    """
    tap = {kind: int(n) for kind, n in _NODE_TAP_RE.findall(output)}
    if tap:
        return {"pass": tap.get("pass", 0), "fail": tap.get("fail", 0), "known": True}
    for line in output.splitlines():
        if not _JS_SUMMARY_RE.match(line):
            continue
        counts = {kind: int(n) for n, kind in _JS_COUNT_RE.findall(line)}
        if counts:
            return {"pass": counts.get("passed", 0), "fail": counts.get("failed", 0), "known": True}
    return {"pass": 0, "fail": 0, "known": False}


def _js_outcome(runner: str, output: str, returncode: int) -> dict:
    """자바스크립트 러너 출력을 항목 결과로. 0개 실행은 통과가 아니라 건너뜀이다.

    파이썬 쪽에는 같은 뜻의 가드가 이미 있다(pytest 종료 코드 5 = 수집된 테스트 없음).
    이쪽에만 없으면, 테스트 파일을 관례 밖 경로에 둔 프로젝트에서 헤드라인 항목이
    영구히 초록으로 뜬다 — R4 가 금지한 출력의 가장 나쁜 형태다.
    """
    counts = _js_counts(output)
    passed, failed = counts["pass"], counts["fail"]
    if failed:
        return {"status": "findings", "human": f"{passed}개 통과, {failed}개 실패 ({runner})",
                "reason": f"{runner} {passed} passed {failed} failed"}
    if not counts["known"] and returncode != 0:
        return {"status": "findings", "human": f"{runner} 가 비정상 종료했습니다 (종료 코드 {returncode}).",
                "reason": f"{runner} exited {returncode}"}
    if passed == 0 and failed == 0:
        return {"status": "skipped",
                "human": f"{runner} 가 실행한 테스트를 0개로 읽었습니다 "
                         f"(테스트 파일을 찾지 못했거나 결과 형식을 읽지 못했습니다).",
                "reason": f"{runner} collected nothing"}
    return {"status": "ok", "human": f"{passed}개 통과, 0개 실패 ({runner})", "reason": f"{runner} {passed} passed"}


def _merge_outcomes(parts: list) -> dict:
    """언어별 러너 결과를 항목 하나의 결과로 합친다. 가장 나쁜 상태가 이긴다."""
    order = {"ok": 0, "skipped": 1, "findings": 2, "error": 3, "timeout": 4}
    worst = max(parts, key=lambda p: order.get(p["status"], 0))
    findings: list = []
    for part in parts:
        findings += part.get("findings", [])
    hints = [p.get("install_hint") for p in parts if p.get("install_hint")]
    return {
        "status": worst["status"],
        "reason": " | ".join(p["reason"] for p in parts),
        "human_reason": " · ".join(p["human"] for p in parts),
        "install_hint": hints[0] if hints else None,
        "findings": findings,
    }


def check_tests(ctx: GateContext) -> dict:
    parts = []
    if ctx.langs["python"]:
        parts.append(_run_python_tests(ctx))
    if ctx.langs["javascript"]:
        parts.append(_run_js_tests(ctx))
    if not parts:
        return _skip("변경된 파일 중 검사 대상 언어(python / javascript)가 없습니다.", "no supported language")
    return _merge_outcomes(parts)


# ---------------------------------------------------------------------------
# C2 — 커버리지
# ---------------------------------------------------------------------------

def _load_python_coverage(ctx: GateContext) -> dict:
    if ctx.coverage_data_file is None or not ctx.coverage_data_file.exists():
        return {}
    out = ctx.tmpdir / "coverage.json"
    include = ",".join(ctx.langs["python"])
    proc = _run([ctx.python_exe, "-m", "coverage", "json",
                 f"--data-file={ctx.coverage_data_file}", f"--include={include}", "-o", str(out)],
                cwd=ctx.repo_root, timeout=ctx.config.timeout_seconds)
    if not out.exists():
        raise ValueError(f"coverage json 을 만들지 못했습니다: {(proc.stderr or proc.stdout).strip()[:200]}")
    data = _read_json_object(out)
    return {
        _rel_to_repo(ctx.repo_root, raw_path): _file_coverage_from_entry(entry)
        for raw_path, entry in (data.get("files") or {}).items()
        if isinstance(entry, dict)
    }


def _function_regions(entry: dict) -> tuple:
    """coverage 7.6+ 의 함수 리전. `start_line` 은 데코레이터가 아니라 def 줄이다."""
    regions = []
    for fn in (entry.get("functions") or {}).values():
        start = (fn or {}).get("start_line")
        percent = ((fn or {}).get("summary") or {}).get("percent_covered")
        if isinstance(start, int) and isinstance(percent, (int, float)):
            regions.append((start, float(percent) / 100.0))
    return tuple(regions)


def _file_coverage_from_entry(entry: dict) -> FileCoverage:
    return FileCoverage(
        kind="coverage-json",
        percent=(entry.get("summary") or {}).get("percent_covered"),
        functions=_function_regions(entry),
        executed=frozenset(entry.get("executed_lines") or []),
        missing=frozenset(entry.get("missing_lines") or []),
    )


def _rel_to_repo(repo_root: Path, raw: str) -> str:
    path = Path(raw)
    try:
        if path.is_absolute():
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()
    return path.as_posix()


def _load_lcov(repo_root: Path, path: Path) -> dict:
    result: dict = {}
    current: str | None = None
    executed: set = set()
    missing: set = set()
    functions: list = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("SF:"):
            current = _rel_to_repo(repo_root, line[3:].strip())
            executed, missing, functions = set(), set(), []
        elif line.startswith("DA:") and current:
            try:
                num, hits = line[3:].split(",")[:2]
                (executed if int(hits) > 0 else missing).add(int(num))
            except ValueError:
                continue
        elif line.startswith("end_of_record") and current:
            total = len(executed) + len(missing)
            result[current] = FileCoverage(
                kind="lcov",
                percent=(100.0 * len(executed) / total) if total else None,
                functions=tuple(functions),
                executed=frozenset(executed),
                missing=frozenset(missing),
            )
            current = None
    return result


def _load_istanbul(repo_root: Path, path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    result: dict = {}
    for raw_path, entry in (data or {}).items():
        if not isinstance(entry, dict):
            continue
        rel = _rel_to_repo(repo_root, raw_path)
        statements = entry.get("s") or {}
        total = len(statements)
        covered = sum(1 for v in statements.values() if isinstance(v, int) and v > 0)
        result[rel] = FileCoverage(
            kind="istanbul",
            percent=(100.0 * covered / total) if total else None,
            functions=(),
            executed=frozenset(),
            missing=frozenset(),
            istanbul=entry,
        )
    return result


def _collect_python_coverage(ctx: GateContext, collected: dict, problems: list) -> None:
    if not _tool(ctx, "coverage")["available"]:
        problems.append(("coverage 가 설치돼 있지 않습니다.", _tool(ctx, "coverage")["install_hint"]))
    elif ctx.coverage_data_file is None:
        problems.append(("테스트가 실행되지 않아 파이썬 커버리지를 재지 못했습니다.", None))
    else:
        collected.update(_load_python_coverage(ctx))


def _collect_js_coverage(ctx: GateContext, collected: dict, problems: list) -> None:
    for lcov in ctx.js_lcov_files:
        if lcov.exists():
            collected.update(_load_lcov(ctx.repo_root, lcov))
    for istanbul in ctx.js_istanbul_files:
        if istanbul.exists():
            collected.update(_load_istanbul(ctx.repo_root, istanbul))
    if not (ctx.js_lcov_files or ctx.js_istanbul_files):
        problems.append(("자바스크립트 커버리지를 만들 러너가 없습니다.", None))


def _percent_text(rel: str, entry: FileCoverage) -> str:
    pct = entry.percent
    return f"{rel} {pct:.0f}%" if isinstance(pct, (int, float)) else f"{rel} (비율 없음)"


def check_coverage(ctx: GateContext) -> dict:
    """변경 파일의 커버리지를 모은다. 임계값은 두지 않는다 — 판정은 CRAP(C4)이 한다."""
    collected: dict = {}
    problems: list = []
    if ctx.langs["python"]:
        _collect_python_coverage(ctx, collected, problems)
    if ctx.langs["javascript"]:
        _collect_js_coverage(ctx, collected, problems)

    ctx.coverage_map = collected
    if not collected:
        human, hint = problems[0] if problems else ("커버리지 데이터를 만들지 못했습니다.", None)
        return _skip(human, "no coverage data", hint)

    changed = [rel for rel in ctx.change.files if rel in collected]
    parts = [_percent_text(rel, collected[rel]) for rel in changed]
    missing = [rel for rel in ctx.change.files
               if rel not in collected and Path(rel).suffix.lower() in (PY_SUFFIXES | JS_SUFFIXES)]
    human = " · ".join(parts) if parts else "변경 파일에 대한 커버리지 데이터가 없습니다."
    if missing:
        human += f" (데이터 없는 변경 파일 {len(missing)}개)"
    return {
        "status": "ok" if parts else "skipped",
        "reason": f"coverage for {len(parts)} changed files",
        "human_reason": human,
        "findings": [{"file": rel, "percent": collected[rel].percent} for rel in changed],
    }


# ---------------------------------------------------------------------------
# C3 — 복잡도
# ---------------------------------------------------------------------------

def parse_lizard_csv(text: str) -> tuple:
    """lizard `--csv` 출력을 읽는다. 반환은 (행 목록, 폐기 건수).

    이 CSV 에는 헤더가 없어서 컬럼 순서가 바뀌면 조용한 회귀가 된다. 방어책이
    출력 안에 이미 있다 — 인덱스 5 의 `이름@시작-끝@파일` 을 파싱해 인덱스 9/10 의
    시작·끝 줄과 대조하고, 어긋나거나 열이 11개가 아니면 그 행을 버린다.
    """
    rows: list = []
    failures = 0
    for fields in csv.reader(io.StringIO(text)):
        if not fields or not any(f.strip() for f in fields):
            continue
        if len(fields) != 11:
            failures += 1
            continue
        try:
            ccn = int(fields[1])
            start = int(fields[9])
            end = int(fields[10])
        except ValueError:
            failures += 1
            continue
        m = _LIZARD_LOC_RE.search(fields[5])
        if not m or int(m.group(1)) != start or int(m.group(2)) != end:
            failures += 1
            continue
        rows.append({
            "file": Path(fields[6]).as_posix(),
            "function": fields[7] or "(anonymous)",
            "complexity": ccn,
            "start_line": start,
            "end_line": end,
        })
    return rows, failures


def _complexity_failure(returncode: int, failures: int):
    """행을 하나도 얻지 못했을 때의 사유. 없으면 None.

    lizard 는 파싱 실패와 무관하게 종료 코드 0 으로 끝난다. 종료 코드만 보면
    "변경된 함수 0개 모두 기준 이하"로 영구히 통과하고 CRAP 은 영구히 건너뜀이 된다 —
    복잡도 30짜리 함수를 넣어도 리포트가 초록이다.
    """
    if failures:
        return {"status": "error", "reason": f"lizard rows all discarded ({failures})",
                "human_reason": f"복잡도 출력 {failures}건을 모두 형식 불일치로 버려 복잡도를 재지 못했습니다."}
    if returncode != 0:
        return {"status": "error", "reason": f"lizard exited {returncode}",
                "human_reason": f"lizard 가 비정상 종료했습니다 (종료 코드 {returncode})."}
    return None


def check_complexity(ctx: GateContext) -> dict:
    targets = ctx.langs["python"] + ctx.langs["javascript"]
    if not targets:
        return _skip("변경된 파일 중 복잡도를 잴 대상이 없습니다.", "no target files")
    if not _tool(ctx, "lizard")["available"]:
        return _skip("lizard 가 설치돼 있지 않습니다.", "lizard missing", _tool(ctx, "lizard")["install_hint"])

    proc = _run([ctx.python_exe, "-m", "lizard", "--csv", *targets],
                cwd=ctx.repo_root, timeout=ctx.config.timeout_seconds)
    rows, failures = parse_lizard_csv(proc.stdout)
    ctx.complexity_rows = rows
    ctx.complexity_failures = failures
    if failures:
        ctx.notes.append(f"복잡도 출력 {failures}건을 형식 불일치로 버렸습니다.")
    if not rows:
        failure = _complexity_failure(proc.returncode, failures)
        if failure is not None:
            return failure
    return _complexity_outcome(ctx, rows, failures)


def _complexity_outcome(ctx: GateContext, rows: list, failures: int) -> dict:
    """폐기 건수를 상태 열에 직접 붙인다 — 참고란에만 있으면 '통과'를 반박하지 못한다."""
    limit = ctx.config.complexity_threshold
    changed = [r for r in rows if ctx.change.overlaps(r["file"], r["start_line"], r["end_line"])]
    findings = [
        {"file": r["file"], "function": r["function"], "line": r["start_line"], "complexity": r["complexity"]}
        for r in changed if r["complexity"] > limit
    ]
    findings.sort(key=lambda f: -f["complexity"])
    dropped = f" (형식 불일치로 버린 출력 {failures}건)" if failures else ""
    if findings:
        return {"status": "findings", "reason": f"{len(findings)} functions over ccn {limit}",
                "human_reason": f"변경된 함수 {len(changed)}개 중 기준 {limit} 초과 {len(findings)}개{dropped}",
                "findings": findings}
    return {"status": "ok", "reason": f"0 functions over ccn {limit}",
            "human_reason": f"변경된 함수 {len(changed)}개 모두 기준 {limit} 이하{dropped}"}


# ---------------------------------------------------------------------------
# C4 — CRAP
# ---------------------------------------------------------------------------

def crap_score(complexity: float, coverage: float) -> float:
    """CRAP(f) = c^2 * (1 - v)^3 + c.

    커버리지 v 가 1.0 이면 뒤 항이 0 이 되어 CRAP 은 복잡도 c 와 같아진다.
    이 성질이 이 공식의 정의이고, 단위 테스트가 그것을 고정한다.
    """
    return complexity * complexity * (1.0 - coverage) ** 3 + complexity


def _overlap_len(a: tuple, b: tuple) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)


def _loc_span(meta) -> tuple | None:
    """istanbul 항목의 `loc.start.line` ~ `loc.end.line`. 형식이 다르면 None."""
    loc = (meta or {}).get("loc") or {}
    lo = (loc.get("start") or {}).get("line")
    hi = (loc.get("end") or {}).get("line")
    if isinstance(lo, int) and isinstance(hi, int):
        return lo, hi
    return None


def _statement_line(meta) -> int | None:
    line = ((meta or {}).get("start") or {}).get("line")
    return line if isinstance(line, int) else None


@dataclass(frozen=True)
class _IstanbulIndex:
    """istanbul 항목 하나를 미리 색인한 것.

    색인 없이 짜면 함수마다 파일 전체의 fnMap 과 statementMap 을 다시 훑어
    (함수 수 × 구문 수)로 돌아간다. 실측으로 한 파일 안 함수 50개 0.004초,
    500개 0.360초, 2,000개 5.8초 — 생성된 API 클라이언트나 번들이 변경분에
    들어오면 그 값이 그대로 C4 시간이 된다 (R1).
    """

    spans: tuple        # ((lo, hi, fid), ...) — lo 오름차순
    starts: tuple       # spans 의 lo 만 뽑은 것 (bisect 용)
    reach: tuple        # reach[i] = spans[:i+1] 의 hi 최대값 — 뒤로 훑다 멈출 지점
    lines: tuple        # 구문 시작줄 오름차순
    hits: tuple         # hits[i] = lines[:i] 중 실행된 구문 수 (길이 len(lines)+1)
    entered: dict       # fid -> 함수 진입 횟수


def _index_spans(fn_map) -> tuple:
    """(spans, starts, reach) — 함수 범위를 lo 오름차순으로, 누적 최대 끝줄과 함께."""
    spans = []
    for fid, meta in (fn_map or {}).items():
        span = _loc_span(meta)
        if span is not None:
            spans.append((span[0], span[1], fid))
    spans.sort()
    reach, high = [], 0
    for _lo, hi, _fid in spans:
        high = max(high, hi)
        reach.append(high)
    return tuple(spans), tuple(s[0] for s in spans), tuple(reach)


def _index_statements(statement_map, counts: dict) -> tuple:
    """(lines, hits) — 구문 시작줄 오름차순과 실행된 구문의 누적 개수."""
    points = []
    for sid, meta in (statement_map or {}).items():
        line = _statement_line(meta)
        if line is not None:
            points.append((line, 1 if isinstance(counts.get(sid), int) and counts[sid] > 0 else 0))
    points.sort()
    hits = [0]
    for _line, hit in points:
        hits.append(hits[-1] + hit)
    return tuple(p[0] for p in points), tuple(hits)


def _index_istanbul(entry: dict) -> _IstanbulIndex:
    spans, starts, reach = _index_spans(entry.get("fnMap"))
    lines, hits = _index_statements(entry.get("statementMap"), entry.get("s") or {})
    return _IstanbulIndex(spans=spans, starts=starts, reach=reach, lines=lines, hits=hits,
                          entered=dict(entry.get("f") or {}))


def _best_span(index: _IstanbulIndex, span: tuple) -> tuple:
    """lizard 함수 범위와 겹침이 가장 큰 istanbul 함수. 반환은 (fid, (lo, hi)).

    JS 에서는 시작줄 정확 일치를 쓸 수 없다 — 화살표 함수에서 istanbul 은
    `=>` 위치를 잡아 lizard 와 어긋난다. 그래서 범위 겹침 최대로 짝짓는다.
    후보는 시작줄이 범위 끝 이하인 것들뿐이고, 누적 최대 끝줄이 범위 시작보다
    작아지는 지점에서 멈춘다.
    """
    best_id, best_span, best_overlap = None, None, 0
    i = bisect.bisect_right(index.starts, span[1]) - 1
    while i >= 0 and index.reach[i] >= span[0]:
        lo, hi, fid = index.spans[i]
        overlap = _overlap_len(span, (lo, hi))
        if overlap > best_overlap:
            best_id, best_span, best_overlap = fid, (lo, hi), overlap
        i -= 1
    return best_id, best_span


def _span_ratio(index: _IstanbulIndex, span: tuple):
    """범위 안 구문 중 실행된 비율. 범위 안에 구문이 없으면 None."""
    lo = bisect.bisect_left(index.lines, span[0])
    hi = bisect.bisect_right(index.lines, span[1])
    if hi <= lo:
        return None
    return (index.hits[hi] - index.hits[lo]) / (hi - lo)


def _coverage_from_istanbul(index: _IstanbulIndex, row: dict) -> tuple:
    span = (row["start_line"], row["end_line"])
    best_id, best_span = _best_span(index, span)
    if best_id is None:
        return None, None
    ratio = _span_ratio(index, best_span)
    if ratio is None:
        return None, None
    if index.entered.get(best_id) == 0 and ratio > 0:
        return None, "join-mismatch"
    return ratio, "istanbul-overlap"


def _istanbul_index_for(rel: str, entry: FileCoverage, cache) -> _IstanbulIndex:
    if cache is None:
        return _index_istanbul(entry.istanbul)
    if rel not in cache:
        cache[rel] = _index_istanbul(entry.istanbul)
    return cache[rel]


def resolve_coverage(row: dict, coverage_map: dict, index_cache=None) -> tuple:
    """함수 하나의 커버리지 비율을 구한다. 반환은 (비율 또는 None, 출처 문자열).

    경로 A(시작줄 정확 일치)가 기본이고, istanbul 데이터는 경로 C(범위 겹침),
    나머지는 경로 B(줄 범위 폴백)로 내려간다. 데이터 자체가 없으면 0.0 을 쓰되
    출처를 "no-coverage-data" 로 남겨 조용히 통과처럼 보이지 않게 한다.

    잴 줄이 하나도 없을 때(`range-empty`)는 비율을 내지 않고 `None` 을 준다.
    여기서 1.0(완전 커버)을 주면 한 줄짜리 함수와 짝짓기에 실패한 함수가 전부
    "완전히 커버됨"으로 둔갑한다 — 커버리지 없는 복잡한 코드를 잡겠다는 CRAP 의
    도입 이유가 바로 그 지점에서 뒤집힌다.
    """
    entry = coverage_map.get(row["file"])
    if entry is None:
        return 0.0, "no-coverage-data"

    for start, ratio in entry.functions:
        if start == row["start_line"]:
            return ratio, "exact-start-line"

    if entry.kind == "istanbul" and entry.istanbul is not None:
        index = _istanbul_index_for(row["file"], entry, index_cache)
        ratio, source = _coverage_from_istanbul(index, row)
        if source == "join-mismatch":
            return None, "join-mismatch"
        if ratio is not None:
            return ratio, source

    return _range_fallback(entry, row)


def _range_fallback(entry: FileCoverage, row: dict) -> tuple:
    """경로 B — def 줄은 import 시점에 항상 실행되므로 범위에서 뺀다.

    이 +1 이 없으면 한 번도 호출되지 않은 두 줄짜리 함수가 50% 커버로 보인다.
    """
    span = range(row["start_line"] + 1, row["end_line"] + 1)
    known = entry.executed | entry.missing
    denominator = sum(1 for line in span if line in known)
    if denominator == 0:
        return None, "range-empty"
    numerator = sum(1 for line in span if line in entry.executed)
    return numerator / denominator, "range-fallback"


def compute_crap(rows, coverage_map: dict, change: ChangeSet) -> list:
    """변경분과 겹치는 함수만 CRAP 을 계산한다 (R3 를 함수 단위까지 내린 형태)."""
    entries = []
    index_cache: dict = {}
    for row in rows:
        if not change.overlaps(row["file"], row["start_line"], row["end_line"]):
            continue
        ratio, source = resolve_coverage(row, coverage_map, index_cache)
        complexity = row["complexity"]
        if ratio is None:
            entries.append({
                "file": row["file"], "function": row["function"], "line": row["start_line"],
                "complexity": complexity, "coverage": None, "crap": None, "coverage_source": source,
            })
            continue
        entries.append({
            "file": row["file"], "function": row["function"], "line": row["start_line"],
            "complexity": complexity, "coverage": round(ratio, 4),
            "crap": round(crap_score(complexity, ratio), 2), "coverage_source": source,
        })
    return entries


def check_crap(ctx: GateContext) -> dict:
    if not ctx.complexity_rows:
        return _skip("복잡도 데이터가 없어 CRAP 을 계산할 수 없습니다.", "no complexity rows")
    entries = compute_crap(ctx.complexity_rows, ctx.coverage_map, ctx.change)
    if not entries:
        return _skip("변경분과 겹치는 함수가 없습니다.", "no changed functions")

    limit = ctx.config.crap_threshold
    over = [e for e in entries if e["crap"] is not None and e["crap"] > limit]
    unresolved = [e for e in entries if e["crap"] is None]
    over.sort(key=lambda e: -e["crap"])
    no_data = sum(1 for e in entries if e["coverage_source"] == "no-coverage-data")

    suffix = f" (커버리지 데이터 없는 함수 {no_data}개 포함)" if no_data else ""
    if over or unresolved:
        human = f"변경된 함수 {len(entries)}개 중 기준 {limit:g} 초과 {len(over)}개{suffix}"
        if unresolved:
            human += f", 커버리지를 재지 못해 계산 못 한 함수 {len(unresolved)}개"
        return {"status": "findings", "reason": f"{len(over)} functions over CRAP {limit:g}",
                "human_reason": human, "findings": over + unresolved}
    return {"status": "ok", "reason": f"0 functions over CRAP {limit:g}",
            "human_reason": f"변경된 함수 {len(entries)}개 모두 기준 {limit:g} 이하{suffix}"}


# ---------------------------------------------------------------------------
# C5 — 중복
# ---------------------------------------------------------------------------

def _duplicate_finding(entry: dict) -> dict:
    first = entry.get("firstFile") or {}
    second = entry.get("secondFile") or {}
    return {
        "lines": entry.get("lines"), "tokens": entry.get("tokens"),
        "first_file": first.get("name"), "first_start": first.get("start"), "first_end": first.get("end"),
        "second_file": second.get("name"), "second_start": second.get("start"), "second_end": second.get("end"),
    }


def check_duplication(ctx: GateContext) -> dict:
    targets = list(ctx.change.files)
    if not targets:
        return _skip("검사할 변경 파일이 없습니다.", "no changed files")
    tool = _tool(ctx, "jscpd")
    if not tool["available"]:
        return _skip("jscpd 가 설치돼 있지 않습니다.", "jscpd missing", tool["install_hint"])

    out_dir = ctx.tmpdir / "jscpd"
    cmd = [tool["path"], "--reporters", "json", "--output", str(out_dir), "--silent",
           "--min-lines", str(ctx.config.dup_min_lines),
           "--min-tokens", str(ctx.config.dup_min_tokens), *targets]
    _run(cmd, cwd=ctx.repo_root, timeout=ctx.config.timeout_seconds)

    report = out_dir / "jscpd-report.json"
    if not report.exists():
        return {"status": "error", "reason": "jscpd report missing",
                "human_reason": "jscpd 가 리포트를 만들지 못했습니다."}
    data = _read_json_object(report)
    ctx.notes.append(
        f"중복은 변경된 파일 {len(targets)}개 안에서만 비교했습니다. "
        "바뀌지 않은 기존 코드와의 중복은 이번 검사에 포함되지 않았습니다."
    )
    findings = [_duplicate_finding(d) for d in (data.get("duplicates") or []) if isinstance(d, dict)]
    if findings:
        return {"status": "findings", "reason": f"{len(findings)} duplicate blocks",
                "human_reason": f"변경 파일 {len(targets)}개 안에서 중복 {len(findings)}건", "findings": findings}
    return {"status": "ok", "reason": "0 duplicate blocks",
            "human_reason": f"변경 파일 {len(targets)}개 안에서 중복 없음"}


# ---------------------------------------------------------------------------
# C6 — 의존 방향 (외부 도구 없이 자체 구현)
# ---------------------------------------------------------------------------

def _import_statements(tree) -> list:
    """(모듈 이름, 상대 단계 수, 줄번호) 목록. 상대 단계 0 이면 절대 import."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(alias.name, 0, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or "", node.level or 0, node.lineno))
    return found


def _resolve_python_module(repo_root: Path, package: Path, module: str, level: int) -> str | None:
    """모듈 이름을 저장소 안의 실제 파일 경로로. 저장소 밖(표준·서드파티)이면 None."""
    base = package
    for _ in range(max(level - 1, 0)):
        base = base.parent
    parts = module.split(".") if module else []
    if not parts and not level:
        return None
    candidate = base.joinpath(*parts) if level else Path(*parts)
    for probe in (candidate.with_suffix(".py"), candidate / "__init__.py"):
        if (repo_root / probe).is_file():
            return probe.as_posix()
    return None


def _python_imports(repo_root: Path, rel: str) -> tuple:
    """파이썬 파일의 저장소 안 import 대상. 반환은 ((대상 상대경로, 줄번호) 목록, 실패 여부).

    파싱 실패를 삼키고 빈 목록만 돌려주면, 편집 중이라 문법이 깨진 파일이
    "import 없음 → 위반 없음"으로 조용히 통과한다. 이 게이트는 에이전트 편집 루프
    안에서 도는 것이 주 용도라 그 상태가 흔하다.
    """
    try:
        tree = ast.parse((repo_root / rel).read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return [], True
    package = Path(rel).parent
    resolved = []
    for module, level, lineno in _import_statements(tree):
        target = _resolve_python_module(repo_root, package, module, level)
        if target is not None:
            resolved.append((target, lineno))
    return resolved, False


_JS_RESOLVE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _js_imports(repo_root: Path, rel: str) -> tuple:
    """반환 형식은 `_python_imports` 와 같다 — (목록, 읽기 실패 여부)."""
    try:
        text = (repo_root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], True
    here = Path(rel).parent
    resolved = []
    for match in _JS_IMPORT_RE.finditer(text):
        spec = match.group(1)
        if not spec.startswith("."):
            continue
        lineno = text.count("\n", 0, match.start()) + 1
        target = (here / spec)
        probes = [target] + [target.with_suffix(s) for s in _JS_RESOLVE_SUFFIXES]
        probes += [target / f"index{s}" for s in _JS_RESOLVE_SUFFIXES]
        for probe in probes:
            try:
                normalized = Path(os.path.normpath(probe))
            except ValueError:
                continue
            if (repo_root / normalized).is_file():
                resolved.append((normalized.as_posix(), lineno))
                break
    return resolved, False


def _layer_of(rel: str, layers: dict) -> str | None:
    for name, patterns in layers.items():
        if any(_match_glob(rel, p) for p in patterns):
            return name
    return None


def _load_layer_rules(rules_path: Path) -> tuple:
    """레이어 규칙을 읽는다. 반환은 (layers, forbidden, 실패 시 결과 dict)."""
    try:
        data = json.loads(rules_path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, ValueError) as exc:
        return None, None, {"status": "error", "reason": f"layers rules unreadable: {type(exc).__name__}",
                            "human_reason": f"규칙 파일을 읽지 못했습니다 ({type(exc).__name__})."}
    if not isinstance(data, dict):
        return None, None, {"status": "error", "reason": "layers rules not an object",
                            "human_reason": "규칙 파일이 JSON 객체가 아닙니다."}
    layers = {k: [str(p) for p in v] for k, v in (data.get("layers") or {}).items() if isinstance(v, list)}
    forbidden = [r for r in (data.get("forbidden") or []) if isinstance(r, dict)]
    if not layers or not forbidden:
        return None, None, _skip("규칙 파일에 layers 또는 forbidden 항목이 없습니다.", "layers rules empty")
    return layers, forbidden, None


def _imports_of(repo_root: Path, rel: str) -> tuple:
    suffix = Path(rel).suffix.lower()
    if suffix in PY_SUFFIXES:
        return _python_imports(repo_root, rel)
    if suffix in JS_SUFFIXES:
        return _js_imports(repo_root, rel)
    return [], False


def _violations_for_file(repo_root: Path, rel: str, layers: dict, forbidden: list) -> tuple:
    """반환은 (위반 목록, 파싱 실패 여부)."""
    src_layer = _layer_of(rel, layers)
    if src_layer is None:
        return [], False
    imports, parse_failed = _imports_of(repo_root, rel)
    found = []
    for target, lineno in imports:
        dst_layer = _layer_of(target, layers)
        if dst_layer is None or dst_layer == src_layer:
            continue
        for rule in forbidden:
            if rule.get("from") == src_layer and rule.get("to") == dst_layer:
                found.append({
                    "from_file": rel, "to_file": target, "line": lineno,
                    "from_layer": src_layer, "to_layer": dst_layer,
                    "reason": str(rule.get("reason") or ""),
                })
    return found, parse_failed


def _layer_outcome(ctx: GateContext, findings: list, forbidden: list,
                   scanned: int, unparsed: list) -> dict:
    """검사 범위를 결과 문장에 그대로 드러낸다.

    "규칙 N건 기준 위반 없음"만 적으면 레이어에 속한 파일이 0개일 때도, 파일을
    파싱하지 못해 한 줄도 못 본 때도 똑같이 초록으로 보인다 (R4).
    """
    if unparsed:
        ctx.notes.append(
            f"의존 방향 검사에서 파싱하지 못해 건너뛴 파일 {len(unparsed)}개: "
            + ", ".join(unparsed[:5]) + (" 외" if len(unparsed) > 5 else "")
        )
    if findings:
        note = f" (파싱 실패 {len(unparsed)}개 제외)" if unparsed else ""
        return {"status": "findings", "reason": f"{len(findings)} forbidden imports",
                "human_reason": f"금지된 방향의 import {len(findings)}건{note}",
                "findings": findings}
    if unparsed:
        return {"status": "skipped", "reason": f"{len(unparsed)} files unparsed",
                "human_reason": f"레이어에 속한 변경 파일 {scanned}개 중 {len(unparsed)}개를 "
                                f"파싱하지 못해 그만큼은 검사하지 못했습니다."}
    if scanned == 0:
        return _skip("변경 파일 중 레이어 규칙에 해당하는 파일이 없습니다.", "no files in any layer")
    return {"status": "ok", "reason": f"0 forbidden imports in {scanned} files",
            "human_reason": f"레이어에 속한 변경 파일 {scanned}개, 규칙 {len(forbidden)}건 기준 위반 없음"}


def check_layers(ctx: GateContext) -> dict:
    rules_path = ctx.repo_root / ctx.config.layers_file
    if not rules_path.is_file():
        return _skip(f"규칙 파일({ctx.config.layers_file})이 없습니다.", "layers rules file missing")
    layers, forbidden, failure = _load_layer_rules(rules_path)
    if failure is not None:
        return failure

    findings: list = []
    unparsed: list = []
    scanned = 0
    for rel in ctx.change.files:
        if _layer_of(rel, layers) is None:
            continue
        scanned += 1
        violations, parse_failed = _violations_for_file(ctx.repo_root, rel, layers, forbidden)
        findings += violations
        if parse_failed:
            unparsed.append(rel)
    return _layer_outcome(ctx, findings, forbidden, scanned, unparsed)


# ---------------------------------------------------------------------------
# C7 — 뮤테이션 (자바스크립트: Stryker)
#
# 커버리지는 "실행된 줄"만 세므로, 확인문이 하나도 없는 테스트도 100% 로 보인다.
# 뮤테이션은 코드를 일부러 바꿔 놓고 테스트가 실패하는지 본다 — 테스트가 잡아내는지를
# 재는 항목이다. 0단계에서는 점수를 내기만 하고 아무것도 막지 않는다 (R2).
#
# 이 항목의 사실관계는 Stryker 10 을 실물로 돌려 확인한 것이다. 특히 두 가지가
# 구현을 좌우한다.
#   - JSON 리포트 경로를 바꾸는 명령줄 옵션이 없다. 설정 파일이 한 개 반드시 필요하고,
#     그 파일을 게이트 임시 디렉토리에 두면 대상 프로젝트에는 아무것도 안 남는다.
#   - 증분 실행을 켜면 지난 회차에 돌린 파일이 이번 리포트에 섞여 들어온다.
#     이번 변경분 목록으로 걸러내지 않으면 R3(변경분만 검사)이 깨진다.
# ---------------------------------------------------------------------------

# D1 의 상태 분류. 이 세 묶음이 점수 공식의 전부다.
MUTATION_KILLED_STATUSES = ("Killed", "Timeout")
MUTATION_SURVIVING_STATUSES = ("Survived", "NoCoverage")
MUTATION_EXCLUDED_STATUSES = ("CompileError", "RuntimeError", "Ignored", "Pending")

# 세 묶음 어디에도 없는 상태는 점수 분모에서 조용히 빠진다. 그러면 "100% 통과" 가 나온다 —
# R4 가 금지한 조용한 통과의 정확한 형태다. 그런 상태를 세어 결과 문장에 반드시 적는다.
MUTATION_KNOWN_STATUSES = frozenset(
    MUTATION_KILLED_STATUSES + MUTATION_SURVIVING_STATUSES + MUTATION_EXCLUDED_STATUSES)

# 테스트를 실제로 돌린 변이. 덮은 테스트가 없는 변이는 테스트를 한 번도 돌리지 않아 비용이
# 거의 0 이라, 변이당 초의 분모에 넣으면 값이 실제 비용의 몇백 분의 1 로 나온다 (D5).
MUTATION_EXECUTED_STATUSES = ("Killed", "Timeout", "Survived")

MUTANT_STATUS_KO = {
    "Killed": "잡힘",
    "Timeout": "잡힘(무한루프)",
    "Survived": "살아남음",
    "NoCoverage": "덮은 테스트 없음",
    "CompileError": "컴파일 실패",
    "RuntimeError": "실행 실패",
    "Ignored": "제외됨",
    "Pending": "실행 안 됨",
}

# 살아남은 변이를 먼저, 테스트가 아예 없는 변이를 뒤에 놓는다 — 고칠 순서 그대로다.
_SURVIVOR_ORDER = {"Survived": 0, "NoCoverage": 1}

# Stryker 가 스스로 찾는 설정 파일 이름 16가지. 프로젝트 설정 유무를 이 목록으로 본다.
STRYKER_CONFIG_NAMES = tuple(
    f"{dot}stryker{mid}{ext}"
    for dot in ("", ".")
    for mid in (".conf", ".config")
    for ext in (".json", ".js", ".mjs", ".cjs")
)

# node_modules/@stryker-mutator/<디렉토리> → testRunner 이름.
STRYKER_RUNNER_PLUGINS = (
    ("vitest-runner", "vitest"),
    ("jest-runner", "jest"),
    ("mocha-runner", "mocha"),
    ("jasmine-runner", "jasmine"),
    ("karma-runner", "karma"),
    ("cucumber-runner", "cucumber"),
    ("tap-runner", "tap"),
)

# 변이 대상에서 빼는 디렉토리 이름 — 테스트 코드를 변이시켜도 얻을 것이 없다.
_MUTATION_TEST_DIRS = frozenset({"test", "tests", "__tests__", "spec", "__specs__", "__mocks__"})
_MUTATION_TEST_STEMS = (".test", ".spec", "_test", "_spec")

# C7 만의 대상 확장자. Stryker 10 은 .vue / .svelte / .html / .htm 도 스스로 파싱한다 (실측).
# JS_SUFFIXES 를 넓히지 않는 이유는 그 상수를 C2(커버리지)와 C6(의존 방향)이 함께 쓰기
# 때문이다. 거기까지 판정이 바뀌므로 여기서만 넓힌다.
MUTATION_SUFFIXES = frozenset(JS_SUFFIXES | {".vue", ".svelte", ".html", ".htm"})


def mutation_score(counts) -> float | None:
    """D1 의 단일 출처 — killed / (killed + survived + no_coverage) 를 백분율로.

    Timeout 은 killed 에 넣는다. 변이가 무한루프를 만들었고 테스트 실행이 그것을 걸어
    세웠으니 감지된 것으로 본다.
    NoCoverage 를 분모에 남기는 것이 핵심이다. 빼면 테스트가 아예 없는 코드가 점수에서
    사라져, 테스트를 안 쓸수록 점수가 오르는 값이 된다.
    CompileError / RuntimeError / Ignored / Pending 은 테스트의 성적이 아니므로 분모에서 뺀다.
    분모가 0 이면 점수가 정의되지 않는다 — 0.0 이 아니라 None 이다 (0% 는 나쁜 성적처럼
    보이지만 실제로는 잰 것이 없다는 뜻이라 다르다).
    """
    killed = sum(int(counts.get(name, 0) or 0) for name in MUTATION_KILLED_STATUSES)
    surviving = sum(int(counts.get(name, 0) or 0) for name in MUTATION_SURVIVING_STATUSES)
    denominator = killed + surviving
    if denominator <= 0:
        return None
    return round(killed * 100.0 / denominator, 2)


def unknown_mutant_statuses(counts) -> tuple:
    """세 묶음 어디에도 없는 상태 이름. 있으면 점수가 그만큼을 못 본 것이다 (R4).

    철자가 하나 다르거나(`survived`) 도구가 새 상태를 내면 분모에서 조용히 빠져 점수가
    100% 로 올라간다. 그것을 세어 결과 문장에 실으면 조용한 통과가 되지 않는다.
    """
    return tuple(sorted(str(name) for name in counts if str(name) not in MUTATION_KNOWN_STATUSES))


def _mutation_executed(counts) -> int:
    """테스트를 실제로 돌린 변이 수 — 변이당 초의 분모다."""
    return sum(int(counts.get(name, 0) or 0) for name in MUTATION_EXECUTED_STATUSES)


def _compact(text: str, limit: int = 80) -> str:
    """여러 줄에 걸친 변이를 표 한 줄에 넣기 위해 공백을 접고 길면 자른다."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _location_bounds(location, line_count: int):
    """변이 위치를 (시작줄, 시작열, 끝줄, 끝열)로. 형식이 어긋나거나 범위 밖이면 None."""
    if not isinstance(location, dict):
        return None
    start, end = location.get("start"), location.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None
    try:
        bounds = (int(start["line"]), int(start["column"]), int(end["line"]), int(end["column"]))
    except (KeyError, TypeError, ValueError):
        return None
    start_line, start_col, end_line, end_col = bounds
    if min(start_col, end_col) < 1 or not 1 <= start_line <= end_line <= line_count:
        return None
    return bounds


def _utf16_offset(line: str, column: int) -> int:
    """Stryker 의 열 번호(1부터)를 파이썬 문자열 색인으로 바꾼다.

    Stryker 는 UTF-16 코드 단위로 세고 파이썬은 코드 포인트로 센다. 이모지 같은 비BMP
    문자는 UTF-16 에서 두 칸을 차지해, 줄 앞쪽에 하나 있을 때마다 잘라낸 자리가 한 칸씩
    밀린다. ASCII 만 있는 줄에서는 두 셈이 같아 결과가 달라지지 않는다.
    """
    target = column - 1
    if target <= 0:
        return 0
    units = 0
    for index, char in enumerate(line):
        if units >= target:
            return index
        units += 2 if ord(char) > 0xFFFF else 1
    return len(line)


def slice_lines(lines, location) -> str:
    """이미 줄 단위로 쪼갠 소스에서 변이 자리를 잘라낸다.

    쪼개는 일을 호출자로 올린 이유는 시간이다. 변이마다 소스를 다시 쪼개면 파일 하나에
    (변이 수 x 줄 수) 만큼 일이 쌓여 큰 파일에서 파싱 시간이 2차로 커진다 (R1).
    """
    bounds = _location_bounds(location, len(lines))
    if bounds is None:
        return ""
    start_line, start_col, end_line, end_col = bounds
    first = lines[start_line - 1]
    if start_line == end_line:
        return first[_utf16_offset(first, start_col) : _utf16_offset(first, end_col)]
    last = lines[end_line - 1]
    picked = [first[_utf16_offset(first, start_col) :]]
    picked += lines[start_line : end_line - 1]
    picked.append(last[: _utf16_offset(last, end_col)])
    return "\n".join(picked)


def _split_source(source) -> list:
    """소스를 줄 목록으로. 문자열이 아니면 빈 줄 하나 — 위치 검사가 알아서 걸러낸다."""
    return source.split("\n") if isinstance(source, str) else [""]


def slice_source(source: str, location) -> str:
    """리포트의 location 으로 원본 텍스트를 잘라낸다.

    리포트에는 바뀐 것(replacement)만 있고 원본 텍스트를 담은 필드가 없다. 줄과 열을
    모두 1부터 세고 끝 위치는 포함하지 않는다 — 실물로 확인한 규칙이다.
    """
    if not isinstance(source, str):
        return ""
    return slice_lines(_split_source(source), location)


def _mutant_record(rel: str, mutant: dict, original: str, tests) -> dict:
    """D2 가 요구하는 항목을 한 모양으로 맞춘다 — 최종 리포트와 이벤트 파일 양쪽이 쓴다.

    관련 테스트 목록이 중요하다. 그 테스트들이 실행되고도 못 잡았다는 뜻이라, 어느
    테스트의 확인문을 보강해야 하는지가 바로 나온다.

    원본과 바뀐 것은 자르지 않고 그대로 담는다. 표 한 줄에 넣기 위한 줄이기는 표시
    단계에서 한다 — 기록에서 잘라 버리면 `--json` 을 읽는 쪽에도 잘린 값만 남는다 (D2).
    """
    location = mutant.get("location") or {}
    start = location.get("start") or {}
    return {
        "file": rel,
        "line": start.get("line"),
        "column": start.get("column"),
        "mutator": mutant.get("mutatorName"),
        "original": original,
        "replacement": mutant.get("replacement") or "",
        "status": mutant.get("status"),
        "tests": [str(t) for t in tests],
    }


def summarize_mutants(records) -> dict:
    """변이 기록 목록 → 개수·점수·살아남은 목록. 점수는 반드시 mutation_score 하나를 거친다."""
    counts: dict = {}
    for record in records:
        key = record.get("status") or "Unknown"
        counts[key] = counts.get(key, 0) + 1
    survivors = [r for r in records if r.get("status") in MUTATION_SURVIVING_STATUSES]
    survivors.sort(key=lambda r: (
        _SURVIVOR_ORDER.get(r.get("status"), 9), r.get("file") or "",
        r.get("line") or 0, r.get("column") or 0,
    ))
    return {
        "total": len(records),
        "counts": counts,
        "score": mutation_score(counts),
        "survivors": survivors,
        "files": sorted({r["file"] for r in records if r.get("file")}),
        "unknown": unknown_mutant_statuses(counts),
    }


def _test_name_index(report: dict) -> dict:
    """테스트 id → 사람이 읽는 이름.

    변이의 coveredBy / killedBy 에는 id 문자열만 들어 있고, 이름은 최상위 testFiles 에
    따로 있다. id 는 파일을 넘어 전역으로 매겨져서 전부 훑어 사전을 먼저 만들어야 한다.
    """
    index: dict = {}
    files = report.get("testFiles")
    if not isinstance(files, dict):
        return index
    for path, entry in files.items():
        if not isinstance(entry, dict):
            continue
        for test in entry.get("tests") or []:
            if isinstance(test, dict) and test.get("id") is not None:
                index[str(test["id"])] = f"{path} > {test.get('name') or test['id']}"
    return index


def _records_for_file(rel: str, entry, index: dict) -> list:
    """파일 하나의 변이 목록을 게이트 기록으로. 리포트가 어그러져 있어도 그 파일만 비운다."""
    if not isinstance(entry, dict):
        return []
    lines = _split_source(entry.get("source") or "")
    records = []
    for mutant in entry.get("mutants") or []:
        if not isinstance(mutant, dict):
            continue
        tests = [index.get(str(t), str(t)) for t in (mutant.get("coveredBy") or [])]
        records.append(_mutant_record(rel, mutant, slice_lines(lines, mutant.get("location")), tests))
    return records


def parse_mutation_report(report: dict, targets=None) -> dict:
    """Stryker JSON 리포트를 게이트 결과로 옮긴다 — 서브프로세스 없이 검증되는 순수 함수.

    `targets` 를 주면 그 파일들만 센다. 증분 실행을 켜면 지난 회차에 돌린 파일이 이번
    리포트에 그대로 섞이므로, 이번 변경분으로 걸러내지 않으면 점수가 변경분 밖의 코드까지
    반영한다 (R3).
    """
    files = report.get("files") if isinstance(report, dict) else None
    if not isinstance(files, dict):
        return summarize_mutants([])
    index = _test_name_index(report)
    records: list = []
    for rel in sorted(files):
        if targets is None or rel in targets:
            records += _records_for_file(rel, files.get(rel), index)
    return summarize_mutants(records)


def _cached_lines(cache: dict, rel: str, sources: dict) -> list:
    """파일 하나를 한 번만 쪼갠다. 변이마다 다시 쪼개면 파싱이 2차로 커진다 (R1)."""
    if rel not in cache:
        cache[rel] = _split_source(sources.get(rel, ""))
    return cache[rel]


def parse_mutation_events(events, repo_root: Path, sources: dict, targets=None) -> dict:
    """예산 초과로 중단됐을 때 남는 이벤트 파일에서 본 만큼만 뽑는다 — 역시 순수 함수.

    최종 리포트와 두 군데가 다르다. fileName 이 절대 경로이고, coveredBy 에 테스트 이름이
    이미 박혀 있어 id 사전이 필요 없다. 원본 텍스트는 이벤트에 없어 `sources` 로 받는다.
    """
    records: list = []
    split: dict = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        raw = event.get("fileName")
        if not isinstance(raw, str) or not raw:
            continue
        rel = _rel_to_repo(Path(repo_root), raw)
        if targets is not None and rel not in targets:
            continue
        original = slice_lines(_cached_lines(split, rel, sources), event.get("location"))
        records.append(_mutant_record(rel, event, original, event.get("coveredBy") or []))
    return summarize_mutants(records)


def _sample_list(items, limit: int = 5) -> str:
    """목록을 앞 몇 개만 적고 나머지는 "외" 로 줄인다 — 안내문 세 군데가 같이 쓴다."""
    return ", ".join(items[:limit]) + (" 외" if len(items) > limit else "")


def _mutation_targets(repo_root: Path, files) -> tuple:
    """변이시킬 파일을 고른다. 테스트 파일과 타입 선언 파일, 삭제된 파일은 뺀다.

    테스트 파일을 변이시키는 것은 의미가 없고, 삭제된 파일을 넘기면 Stryker 가 종료
    코드 1 로 끝난다. 뺀 것은 사유와 함께 호출자가 리포트에 남긴다 (R4).
    """
    targets: list = []
    dropped: list = []
    for rel in files:
        path = Path(rel)
        name = path.name.lower()
        stem = name.rsplit(".", 1)[0] if "." in name else name
        is_test = (
            name.endswith(".d.ts")
            or any(stem.endswith(suffix) for suffix in _MUTATION_TEST_STEMS)
            or any(part.lower() in _MUTATION_TEST_DIRS for part in path.parts[:-1])
        )
        if is_test or not (repo_root / rel).is_file():
            dropped.append(rel)
        else:
            targets.append(rel)
    return tuple(targets), tuple(dropped)


def _stryker_project_config(repo_root: Path) -> Path | None:
    """프로젝트가 이미 갖고 있는 Stryker 설정. 있으면 덮어쓰지 않고 그대로 흡수한다."""
    for name in STRYKER_CONFIG_NAMES:
        candidate = repo_root / name
        if candidate.is_file():
            return candidate
    return None


def _stryker_runner(repo_root: Path) -> str | None:
    """설치된 러너 플러그인으로 testRunner 를 정한다.

    지정하지 않으면 Stryker 는 `command` 러너로 떨어져 변이마다 `npm test` 를 통째로
    돌린다. 그러면 시간이 자릿수로 늘어나 R1 이 걸린다.
    """
    base = repo_root / "node_modules" / "@stryker-mutator"
    for directory, runner in STRYKER_RUNNER_PLUGINS:
        if (base / directory).is_dir():
            return runner
    return None


def _write_stryker_config(paths: dict, project_config: Path | None, runner: str | None) -> Path:
    """게이트 임시 디렉토리에 설정 파일을 쓴다. 대상 프로젝트에는 아무것도 만들지 않는다 (D3).

    설정 파일이 한 개 반드시 필요한 이유는 JSON 리포트 경로를 바꾸는 명령줄 옵션이 없어서다.
    프로젝트 설정을 먼저 펼치고 출력 경로만 덮으므로 프로젝트가 정한 값은 살아 있다.
    testRunner 는 프로젝트 설정보다 **앞에** 두어 프로젝트 쪽이 이기게 한다.
    """
    fallback = {"testRunner": runner} if runner else {}
    override = {
        "reporters": ["json", "event-recorder"],
        "jsonReporter": {"fileName": str(paths["report"])},
        "eventReporter": {"baseDir": str(paths["events"])},
        "tempDirName": str(paths["temp"]),
        "cleanTempDir": "always",
        # 증분은 게이트가 명령줄로만 켠다. 여기서 꺼 두지 않으면, 캐시 디렉토리를 만들지
        # 못해 명령줄이 빠졌을 때 프로젝트 설정의 incremental 이 되살아나 상태 파일이
        # 대상 프로젝트 안에 생긴다 (D3 위반). 명령줄이 설정보다 세다는 것은 실측했다.
        "incremental": False,
    }
    body = [
        "// 검사 게이트가 실행 중에만 쓰는 설정입니다. 대상 프로젝트에는 저장되지 않습니다.",
        "import fs from 'node:fs';",
        "import { pathToFileURL } from 'node:url';",
        f"const projectConfigPath = {json.dumps(str(project_config) if project_config else None)};",
        "let projectConfig = {};",
        "if (projectConfigPath) {",
        "  projectConfig = projectConfigPath.endsWith('.json')",
        "    ? JSON.parse(fs.readFileSync(projectConfigPath, 'utf-8'))",
        "    : ((await import(pathToFileURL(projectConfigPath).href)).default ?? {});",
        "}",
        f"const fallback = {json.dumps(fallback, ensure_ascii=False)};",
        f"const override = {json.dumps(override, ensure_ascii=False)};",
        "export default { ...fallback, ...projectConfig, ...override };",
    ]
    paths["config"].write_text("\n".join(body) + "\n", encoding="utf-8")
    return paths["config"]


def mutation_state_file(repo_root: Path, notes: list) -> Path | None:
    """증분 상태 파일을 둘 자리. 만들지 못하면 None (증분 없이 전체를 돌린다).

    게이트 임시 디렉토리는 실행이 끝나면 지워져 증분이 성립하지 않고, 대상 프로젝트
    안에는 두지 않는다 (D3). 그래서 사용자 캐시 아래에 저장소별로 나눠 둔다.
    """
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    key = hashlib.sha256(str(Path(repo_root).resolve()).encode("utf-8")).hexdigest()[:16]
    target = Path(base) / "code-gate" / "mutation" / key
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        notes.append(
            f"증분 상태 파일을 둘 캐시 디렉토리를 만들지 못해 이번에는 전체를 다시 돌렸습니다 ({type(exc).__name__})."
        )
        return None
    return target.resolve() / "stryker-incremental.json"


def _mutation_sources(repo_root: Path, targets) -> dict:
    """이벤트 파일에는 소스가 없어 원본 텍스트를 얻으려면 파일을 직접 읽어야 한다."""
    sources: dict = {}
    for rel in targets:
        try:
            sources[rel] = (repo_root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return sources


def _mutation_timing(elapsed: float, total: int, executed: int | None = None) -> str:
    """D5 의 세 숫자를 한 문장으로. 세 번째가 있어야 다음 실행 시간을 가늠할 수 있다.

    변이당 초는 **테스트를 실제로 돌린 변이**로 나눈다. 덮은 테스트가 없는 변이는 테스트를
    한 번도 돌리지 않아 비용이 거의 0 이다. 그것까지 분모에 넣으면 값이 실제 비용의 몇백
    분의 1 로 나와 다음 실행을 예측하는 데 못 쓴다.
    변이당 초에는 준비 비용(사본 만들기 + 초기 테스트)이 섞여 있어, 변이 수가 늘어날수록
    이 값은 내려간다. 그대로 곱해 예측하면 실제보다 크게 나온다.
    """
    ran = total if executed is None else executed
    per = (elapsed / ran) if ran else 0.0
    if executed is not None and executed != total:
        return (f"실행 {elapsed:.1f}초, 변이 {total}개(테스트를 돌린 변이 {executed}개), "
                f"변이당 {per:.3f}초")
    return f"실행 {elapsed:.1f}초, 변이 {total}개, 변이당 {per:.3f}초"


def _mutation_distribution(counts: dict) -> str:
    return " / ".join(f"{MUTANT_STATUS_KO.get(k, k)} {v}" for k, v in sorted(counts.items()))


_STRYKER_NO_TESTS = "No tests were executed"


def _mutation_no_report(proc, elapsed: float) -> dict:
    """리포트가 없으면 통과가 아니라 오류다 (R4).

    설정 오류, 초기 테스트 실패, 변이 대상 0개가 모두 여기로 온다. 셋 다 종료 코드 1 에
    리포트 없음이라 종료 코드만으로는 갈리지 않는다. 사람이 읽는 자리에는 짚이는 원인을
    한국어로 먼저 적고, 영어 원문은 그대로 뒤에 붙인다 — 진짜 설정 오류일 때 그 문장이
    유일한 단서다.
    """
    detail = " ".join((proc.stderr or proc.stdout or "").split())[:300]
    returncode = proc.returncode
    cause = (
        "변이 대상 파일을 실행하는 테스트를 하나도 찾지 못했습니다."
        if _STRYKER_NO_TESTS in detail else
        "대상 파일에 테스트가 닿지 않았거나 Stryker 설정이 어긋났을 때 나옵니다."
    )
    tail = f" Stryker 원문: {detail}" if detail else " Stryker 가 아무 출력도 내지 않았습니다."
    return {
        "status": "error",
        "reason": f"stryker produced no json report (exit {returncode}): {detail}",
        "human_reason": (f"Stryker 가 리포트를 만들지 못했습니다 (종료 코드 {returncode}, "
                         f"{elapsed:.1f}초). {cause}{tail}"),
    }


def _missing_target_note(summary: dict, targets) -> str:
    """대상으로 넘겼는데 리포트에 한 줄도 없는 파일. 없으면 빈 문자열.

    경로가 글롭 패턴에 안 맞았거나 Stryker 가 그 확장자를 다루지 못한 경우다. 말하지
    않으면 남은 파일의 점수가 변경분 전체의 점수처럼 읽히고 그 옆에서 "통과" 가 나간다.
    """
    measured = set(summary.get("files") or ())
    missing = [rel for rel in targets if rel not in measured]
    if not missing:
        return ""
    return (f"대상 파일 {len(missing)}개는 변이가 하나도 만들어지지 않아 이 점수에 들어 "
            f"있지 않습니다: {_sample_list(missing)}")


def _unknown_status_note(summary: dict) -> str:
    """게이트가 모르는 변이 상태. 없으면 빈 문자열.

    점수 분모에서 조용히 빠져 100% 가 나오는 자리라, 있으면 반드시 이름을 적는다.
    """
    unknown = summary.get("unknown") or ()
    if not unknown:
        return ""
    return "게이트가 모르는 변이 상태가 있어 점수 분모에서 빠졌습니다: " + ", ".join(unknown)


def _mutation_gaps(summary: dict, targets) -> str:
    """이번 점수가 못 본 것 — 있으면 문장으로, 없으면 빈 문자열 (R4).

    두 가지를 본다.
      - 대상으로 넘겼는데 리포트에 한 줄도 없는 파일. 경로가 글롭 패턴에 안 맞았거나
        Stryker 가 그 확장자를 다루지 못한 경우다. 말하지 않으면 나머지 파일의 점수가
        변경분 전체의 점수처럼 읽히고, 그 옆에서 "통과" 가 나간다.
      - 게이트가 모르는 변이 상태. 점수 분모에서 빠져 100% 가 나온다.
    """
    notes = (_missing_target_note(summary, targets), _unknown_status_note(summary))
    return "".join(f"  {note}" for note in notes if note)


def _mutation_outcome(ctx: GateContext, summary: dict, elapsed: float, targets) -> dict:
    """점수를 사람이 읽는 문장으로. 기준 미달이면 발견, 아니면 통과 — 어느 쪽이든 막지 않는다.

    머리말에서 "살아남음" 이라는 말을 쓰지 않는다. 그 수(Survived + NoCoverage)는 바로 뒤
    분포의 "살아남음"(Survived 만)과 달라, 한 문장 안에서 같은 낱말이 두 수를 가리켰다.
    """
    total = summary["total"]
    timing = _mutation_timing(elapsed, total, _mutation_executed(summary["counts"]))
    if total == 0:
        return _skip(
            f"변경된 대상 파일 {len(targets)}개에서 변이가 하나도 만들어지지 않았습니다. {timing}",
            "no mutants for changed files",
        )
    distribution = _mutation_distribution(summary["counts"])
    tail = _mutation_gaps(summary, targets)
    if summary["score"] is None:
        return _skip(
            f"점수를 낼 변이가 없습니다 (분포: {distribution}). {timing}{tail}",
            "no scorable mutants",
        )
    score = summary["score"]
    threshold = ctx.config.mutation_score_threshold
    survivors = summary["survivors"]
    head = (
        f"점수 {score:.1f}% (기준 {threshold:g}%), 변이 {total}개 중 잡히지 않음 {len(survivors)}개"
        f" — {distribution}"
    )
    outcome = {
        "reason": f"mutation score {score:.2f} ({len(survivors)} not killed of {total})",
        "human_reason": f"{head}. {timing}{tail}",
        "findings": survivors,
    }
    # 못 본 것이 있으면 통과로 내지 않는다. 점수가 변경분 전체를 대표하지 못하기 때문이다.
    outcome["status"] = "findings" if (score < threshold or tail) else "ok"
    return outcome


def _read_mutation_events(events_dir: Path) -> tuple:
    """이벤트 디렉토리에서 계획 하나와 변이 결과들을 읽는다. 디렉토리가 없으면 빈 결과."""
    plan: dict = {}
    events: list = []
    try:
        entries = sorted(events_dir.iterdir())
    except OSError:
        return plan, events
    for entry in entries:
        if entry.name.endswith("-onMutationTestingPlanReady.json"):
            plan = _read_json_object(entry)
        elif entry.name.endswith("-onMutantTested.json"):
            data = _read_json_object(entry)
            if data:
                events.append(data)
    return plan, events


def _plan_mutant_file(item, repo_root: Path) -> str | None:
    """계획 항목 하나에서 파일의 저장소 상대 경로를 꺼낸다. 모양이 어긋나면 None.

    항목이 mutant 를 감싼 모양과 mutant 자체인 모양을 모두 받는다 — 리포터가 바뀌어도
    한쪽이 조용히 0 이 되지 않게 한다.
    """
    if not isinstance(item, dict):
        return None
    mutant = item.get("mutant")
    if not isinstance(mutant, dict):
        mutant = item
    raw = mutant.get("fileName")
    if not isinstance(raw, str) or not raw:
        return None
    return _rel_to_repo(repo_root, raw)


def _planned_for_targets(plan: dict, repo_root: Path, targets) -> int:
    """계획된 변이 중 이번 대상 파일의 것만 센다.

    증분 실행이면 계획에 지난 회차의 다른 파일까지 들어온다. 거르지 않으면 "몇 개 중 몇 개"
    의 앞 숫자만 모수가 달라져, 다 잰 회차가 덜 잰 것처럼 보고된다 (D4).
    """
    rels = (_plan_mutant_file(item, repo_root) for item in plan.get("mutantPlans") or [])
    return sum(1 for rel in rels if rel in targets)


def _mutation_partial(ctx: GateContext, paths: dict, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단했을 때 — 본 만큼만 내고 못 본 것을 반드시 말한다 (D4·R4).

    JSON 리포트는 실행이 끝날 때 한 번에 쓰이므로 중간에 죽이면 남지 않는다. 그래서
    변이 하나가 끝날 때마다 파일 하나를 남기는 event-recorder 리포터를 함께 켜 둔다.
    """
    plan, events = _read_mutation_events(paths["events"])
    scope = set(targets)
    planned = _planned_for_targets(plan, Path(ctx.repo_root), scope)
    summary = parse_mutation_events(events, ctx.repo_root, _mutation_sources(ctx.repo_root, targets), scope)
    seen = summary["total"]
    timing = _mutation_timing(elapsed, seen, _mutation_executed(summary["counts"]))
    if seen == 0:
        return {
            "status": "timeout",
            "reason": f"timeout after {budget}s with no partial result",
            "human_reason": f"{budget}초 예산을 넘겨 중단했습니다. 중간 결과가 남지 않아 변이를 하나도 재지 못했습니다.",
        }
    scope = f"계획된 변이 {planned}개 중 {seen}개까지" if planned else f"변이 {seen}개까지"
    score = summary["score"]
    score_text = (
        f"거기까지의 점수는 {score:.1f}% 입니다 (전체 점수가 아닙니다)"
        if score is not None else "거기까지는 점수를 낼 변이가 없었습니다"
    )
    return {
        "status": "timeout",
        "reason": f"timeout after {budget}s ({seen} of {planned or 'unknown'} mutants tested)",
        "human_reason": (
            f"{budget}초 예산을 넘겨 중단했습니다. {scope} 봤고 나머지는 재지 못했습니다. "
            f"{score_text}. {timing}"
        ),
        "findings": summary["survivors"],
    }


def _mutation_changed_files(ctx: GateContext) -> list:
    """C7 이 볼 변경 파일. 언어 판정을 다시 하는 이유는 확장자 목록이 다르기 때문이다.

    Stryker 10 은 .vue / .svelte / .html / .htm 도 스스로 파싱하는데, 공용 언어 판정이 쓰는
    JS_SUFFIXES 에는 그것들이 없다. 그대로 두면 그 파일들이 흔적 없이 빠져, 남은 파일의
    점수가 변경분 전체의 점수처럼 읽힌다. JS_SUFFIXES 를 넓히면 C2·C6 의 판정까지
    바뀌므로 여기서만 따로 고른다 (변경분의 단일 출처는 그대로 ctx.change.files 다).
    """
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_SUFFIXES]


def _mutation_preconditions(ctx: GateContext, js_files) -> dict | None:
    """재지 못할 사유가 있으면 그 결과를, 없으면 None. 사유는 전부 건너뜀으로 남긴다 (R4)."""
    config = ctx.config
    if not config.mutation_enabled:
        return _skip(
            "설정에서 뮤테이션을 꺼 두었습니다 (.code-gate.json 의 mutation.enabled). 이 항목은 재지 않았습니다.",
            "mutation disabled in config",
        )
    if not js_files:
        return _skip(
            "변경된 자바스크립트 계열 파일이 없습니다 (.vue / .svelte / .html 포함, "
            "파이썬 뮤테이션은 아직 없습니다).",
            "no changed javascript files",
        )
    if config.mutation_javascript != "stryker":
        return _skip(
            f"설정의 mutation.javascript 값 '{config.mutation_javascript}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported js mutation tool: {config.mutation_javascript}",
        )
    tool = _tool(ctx, "stryker")
    if not tool["available"]:
        return _skip("Stryker 가 설치돼 있지 않습니다.", "stryker missing", tool["install_hint"])
    return None


def _mutation_paths(ctx: GateContext) -> dict:
    """Stryker 의 산출물 자리 — 전부 게이트 임시 디렉토리 안이다 (D3).

    심링크를 푼 실제 경로로 넘긴다. macOS 의 임시 디렉토리는 /var/folders/... 처럼 심링크
    뒤에 있는데, 그 경로를 그대로 주면 Stryker 가 만든 사본 안에서 테스트 러너가 테스트를
    하나도 찾지 못하고 "No tests were executed" 로 종료한다 (실측). 러너가 보는 실제 경로와
    설정에 적힌 경로가 달라서 생기는 문제라 여기서 미리 풀어 준다.
    """
    work = ctx.tmpdir / "mutation"
    work.mkdir(parents=True, exist_ok=True)
    work = work.resolve()
    return {
        "config": work / "stryker.conf.mjs",
        "report": work / "mutation.json",
        "events": work / "events",
        "temp": work / "stryker-tmp",
    }


def _stryker_glob(rel: str) -> str:
    """`--mutate` 값은 글롭 패턴으로 읽힌다. 경로 안의 대괄호를 문자 그대로 만든다.

    `src/pages/[id].js` 를 그대로 넘기면 글롭이 "i 또는 d 한 글자" 로 읽어 그 파일이
    대상에서 통째로 빠진다. 역슬래시로는 안 풀리고 `[[]` / `[]]` 로 감싸야 한다 (실측).
    별표로 바꾸는 방법은 바뀌지 않은 다른 파일까지 함께 잡아 R3 를 깬다.
    한 번에 훑어 바꾼다 — `[` 를 먼저 바꾸면 그 결과에 들어간 `]` 를 다시 바꿔 망가진다.
    쉼표는 이 방법으로도 못 푼다. 목록 구분자와 갈라지지 않기 때문인데, 그 경우는
    실행 뒤 대조(`_mutation_gaps`)가 잡는다.
    """
    return "".join("[[]" if ch == "[" else "[]]" if ch == "]" else ch for ch in rel)


def _mutation_command(ctx: GateContext, paths: dict, targets) -> tuple:
    """(실행할 명령, 결과가 나온 뒤에 남길 안내).

    설정 파일은 위치 인자로 넘긴다 — 그래야 프로젝트가 자기 설정을 자동으로 물지 않는다.
    명령줄이 설정 파일보다 세므로, 명령줄에 있는 것만 여기에 둔다.
    안내를 여기서 바로 남기지 않고 돌려주는 이유는, 아무것도 재지 못하고 끝난 회차에도
    "이렇게 걸러서 점수를 냈다" 는 문장이 함께 나가 사용자를 원인에서 멀어지게 해서다.
    """
    cmd = [_tool(ctx, "stryker")["path"], "run", str(paths["config"]),
           "--mutate", ",".join(_stryker_glob(rel) for rel in targets),
           "--logLevel", "error", "--allowConsoleColors", "false"]
    notes = [
        f"뮤테이션은 변경된 파일 {len(targets)}개를 파일 단위로 변이시켰습니다. "
        "그 파일 안에서 이번에 바뀌지 않은 줄도 함께 변이됩니다. "
        "변경되지 않은 다른 파일은 대상이 아닙니다."
    ]
    state = mutation_state_file(ctx.repo_root, ctx.notes)
    if state is not None:
        cmd += ["--incremental", "--incrementalFile", str(state)]
        notes.append(
            "뮤테이션은 증분 실행입니다. 지난 회차 결과가 리포트에 섞여 들어오므로 이번 "
            "변경 파일 목록으로 걸러낸 뒤 점수를 냈습니다."
            if state.exists() else
            "뮤테이션 증분 상태 파일이 아직 없어 이번에는 전체를 돌렸습니다. "
            "다음 회차부터 지난 결과를 재사용합니다."
        )
    return cmd, notes


def _note_comma_paths(ctx: GateContext, targets) -> None:
    """경로에 쉼표가 든 파일을 알린다.

    `--mutate` 는 쉼표로 목록을 가르므로 경로 안의 쉼표와 구분되지 않는다. 이스케이프로도
    안 풀린다. 실제로 빠졌는지는 실행 뒤 대조(`_missing_target_note`)가 다시 잡는다.
    """
    commas = [rel for rel in targets if "," in rel]
    if commas:
        ctx.notes.append(
            f"경로에 쉼표가 든 파일 {len(commas)}개는 Stryker 에 목록으로 넘길 방법이 없어 "
            "재지 못할 수 있습니다: " + _sample_list(commas))


def _mutation_scope(ctx: GateContext, js_files) -> tuple:
    """변이시킬 파일 목록과, 남는 것이 없을 때의 건너뜀 결과. 뺀 파일은 사유와 함께 남긴다."""
    targets, dropped = _mutation_targets(ctx.repo_root, js_files)
    _note_comma_paths(ctx, targets)
    if dropped:
        ctx.notes.append(
            f"뮤테이션 대상에서 테스트·타입 선언·삭제된 파일 {len(dropped)}개를 뺐습니다: "
            + _sample_list(dropped)
        )
    if not targets:
        return (), _skip(
            f"변경된 자바스크립트 계열 파일 {len(js_files)}개가 모두 변이 대상이 아닙니다 "
            "(테스트·타입 선언·삭제된 파일).",
            "no mutable javascript targets",
        )
    return targets, None


def _stryker_setup(ctx: GateContext) -> tuple:
    """(프로젝트 설정, 러너, 건너뜀 결과).

    프로젝트 설정도 러너 플러그인도 없으면 Stryker 는 변이마다 `npm test` 를 통째로 돌리는
    러너로 떨어진다. 시간이 자릿수로 늘어나므로 재지 않고 설치 방법을 알린다.
    """
    project_config = _stryker_project_config(ctx.repo_root)
    runner = _stryker_runner(ctx.repo_root)
    if project_config is None and runner is None:
        return None, None, _skip(
            "Stryker 테스트 러너 플러그인을 찾지 못했습니다 (프로젝트 Stryker 설정도 없습니다).",
            "no stryker test runner plugin",
            "npm i -D @stryker-mutator/vitest-runner",
        )
    if project_config is not None:
        ctx.notes.append(
            f"프로젝트의 Stryker 설정({project_config.name})을 그대로 쓰고 출력 경로만 게이트 임시 "
            "디렉토리로 돌렸습니다. 프로젝트 설정 파일은 수정하지 않았습니다."
        )
    return project_config, runner, None


def _mutation_run(ctx: GateContext, paths: dict, cmd: list, targets, scope_notes: list) -> dict:
    """실행하고 결과를 만든다. 걸린 시간은 리포트를 다 읽은 뒤에 잰다.

    시간을 서브프로세스가 끝난 자리에서 재면 리포트를 읽고 옮기는 시간이 보고 밖으로 샌다.
    표의 초와 문장의 초가 어긋나고, 그 차이는 파일이 커질수록 벌어진다 (R1).
    예산을 넘겨 죽었더라도 리포트가 이미 다 쓰였으면 그것을 쓴다. 완성된 결과를 버리고
    "몇 개 중 몇 개까지 봤다" 고 말하면 앞뒤가 맞지 않는다.
    범위 안내는 실제로 잰 회차에만 남긴다.
    """
    budget = ctx.config.mutation_timeout_seconds
    started = time.perf_counter()
    proc = None
    timed_out = False
    try:
        proc = _run(cmd, cwd=ctx.repo_root, timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out = True

    report = _read_json_object(paths["report"])
    if not report:
        if not timed_out:
            return _mutation_no_report(proc, time.perf_counter() - started)
        outcome = _mutation_partial(ctx, paths, targets, time.perf_counter() - started, budget)
    else:
        summary = parse_mutation_report(report, set(targets))
        outcome = _mutation_outcome(ctx, summary, time.perf_counter() - started, targets)
    ctx.notes.extend(scope_notes)
    return outcome


def check_mutation(ctx: GateContext) -> dict:
    js_files = _mutation_changed_files(ctx)
    blocked = _mutation_preconditions(ctx, js_files)
    if blocked is not None:
        return blocked
    targets, blocked = _mutation_scope(ctx, js_files)
    if blocked is not None:
        return blocked
    project_config, runner, blocked = _stryker_setup(ctx)
    if blocked is not None:
        return blocked

    paths = _mutation_paths(ctx)
    _write_stryker_config(paths, project_config, runner)
    cmd, scope_notes = _mutation_command(ctx, paths, targets)
    return _mutation_run(ctx, paths, cmd, targets, scope_notes)


# ---------------------------------------------------------------------------
# 실행 루프
# ---------------------------------------------------------------------------

CHECKS = (
    ("C1", "tests", "테스트", check_tests),
    ("C2", "coverage", "커버리지", check_coverage),
    ("C3", "complexity", "복잡도", check_complexity),
    ("C4", "crap", "CRAP", check_crap),
    ("C5", "duplication", "중복", check_duplication),
    ("C6", "layers", "의존 방향", check_layers),
    ("C7", "mutation", "뮤테이션", check_mutation),
)


def run_checks(ctx: GateContext) -> list:
    """항목을 순차로 돈다. 병렬로 돌리면 항목별 시간 측정이 서로 오염된다.

    한 항목의 실패는 그 항목에만 가둔다 — 다음 항목은 계속 실행된다.
    `KeyboardInterrupt` 는 `BaseException` 이라 여기서 잡히지 않고 전파된다 (의도).
    """
    results = []
    for code, name, label, fn in CHECKS:
        started = time.perf_counter()
        try:
            if ctx.change.skip_reason:
                outcome = _skip(ctx.change.skip_reason, ctx.change.skip_reason_en)
            else:
                outcome = fn(ctx)
        except subprocess.TimeoutExpired as exc:
            limit = int(exc.timeout or 0)
            outcome = {"status": "timeout", "reason": f"timeout after {limit}s",
                       "human_reason": f"{limit}초를 넘어 중단했습니다."}
        except Exception as exc:  # noqa: BLE001 — 한 항목의 실패가 게이트 전체를 멈추지 않는다
            outcome = {"status": "error", "reason": f"{type(exc).__name__}: {exc}",
                       "human_reason": f"검사 중 오류가 났습니다 ({type(exc).__name__}: {exc})."}
        results.append(CheckResult(
            code=code, name=name, label=label,
            status=outcome.get("status", "error"),
            seconds=round(time.perf_counter() - started, 3),
            reason=outcome.get("reason", ""),
            human_reason=outcome.get("human_reason", ""),
            install_hint=outcome.get("install_hint"),
            findings=tuple(outcome.get("findings", ())),
        ))
    return results


def run_gate(args) -> dict:
    started = time.perf_counter()
    repo_root = _resolve_repo_root(args.repo_root)
    config_path = args.config if args.config is not None else repo_root / CONFIG_NAME
    config = load_config(Path(config_path))

    base, base_reason = resolve_base(repo_root, args.base)
    change = collect_changes(repo_root, base, base_reason, config.exclude)
    python_exe = resolve_python(repo_root)

    with tempfile.TemporaryDirectory(prefix="code-gate-") as tmp:
        ctx = GateContext(
            repo_root=repo_root,
            config=config,
            change=change,
            langs=detect_languages(change.files),
            tools=probe_tools(repo_root, python_exe),
            python_exe=python_exe,
            tmpdir=Path(tmp),
            notes=list(config.notes),
        )
        _prelude_notes(ctx, change)
        results = run_checks(ctx)
        if ctx.coverage_wrapped:
            ctx.notes.append(
                "테스트 시간에는 커버리지 계측 비용이 포함돼 있습니다 "
                "(커버리지 항목의 시간은 리포트 내보내기만 뜻합니다)."
            )
        notes = list(ctx.notes)

    return {
        "schema": 1,
        "exit_code": 0,
        "base": change.base,
        "base_reason": change.base_reason,
        "base_problem": change.base_problem,
        "repo_root": str(repo_root),
        "changed_files": list(change.files),
        "excluded_files": list(change.excluded),
        "pruned_files": list(change.pruned),
        "total_seconds": round(time.perf_counter() - started, 3),
        "config": _config_payload(config),
        "checks": [r.to_dict() for r in results],
        "notes": notes,
        "error": None,
    }


def _prelude_notes(ctx: GateContext, change: ChangeSet) -> None:
    """검사 전에 이미 정해진 사실을 리포트에 남긴다 — 무엇이 빠졌는지 보이게 (R4)."""
    if change.base_problem:
        ctx.notes.append(change.base_problem)
    if change.excluded:
        ctx.notes.append(f"exclude 설정으로 파일 {len(change.excluded)}개를 검사에서 뺐습니다.")
    if change.pruned:
        ctx.notes.append(
            f"의존성·빌드 디렉토리 안의 파일 {len(change.pruned)}개를 검사에서 뺐습니다 "
            "(node_modules / .venv / dist 등 — 설정과 무관한 고정 목록입니다)."
        )


def _config_payload(config: GateConfig | None) -> dict:
    """정상 경로와 오류 경로가 **같은** config 스키마를 내도록 한 곳에서 만든다.

    크래시했을 때만 키가 몇 개 빠지면, 게이트 출력을 JSON 으로 받아 쓰는 소비자가
    하필 그 순간 KeyError 로 같이 죽는다 — 종료 코드 0 으로 흐름을 안 끊겠다는
    R2 의 취지가 소비자 쪽에서 무너진다.
    """
    if config is None:
        return {
            "source": None,
            "crap_threshold": float(DEFAULT_CRAP_THRESHOLD),
            "complexity_threshold": DEFAULT_COMPLEXITY_THRESHOLD,
            "duplication": {"min_lines": DEFAULT_DUP_MIN_LINES, "min_tokens": DEFAULT_DUP_MIN_TOKENS},
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "timeout_seconds_tests": DEFAULT_TIMEOUT_SECONDS_TESTS,
            "layers_file": DEFAULT_LAYERS_FILE,
            "exclude": [],
            "mutation": {
                "enabled": DEFAULT_MUTATION_ENABLED,
                "score_threshold": DEFAULT_MUTATION_SCORE_THRESHOLD,
                "timeout_seconds": DEFAULT_MUTATION_TIMEOUT_SECONDS,
                "javascript": DEFAULT_MUTATION_JAVASCRIPT,
            },
        }
    return {
        "source": config.source,
        "crap_threshold": config.crap_threshold,
        "complexity_threshold": config.complexity_threshold,
        "duplication": {"min_lines": config.dup_min_lines, "min_tokens": config.dup_min_tokens},
        "timeout_seconds": config.timeout_seconds,
        "timeout_seconds_tests": config.timeout_seconds_tests,
        "layers_file": config.layers_file,
        "exclude": list(config.exclude),
        "mutation": {
            "enabled": config.mutation_enabled,
            "score_threshold": config.mutation_score_threshold,
            "timeout_seconds": config.mutation_timeout_seconds,
            "javascript": config.mutation_javascript,
        },
    }


def _resolve_repo_root(explicit) -> Path:
    if explicit is not None:
        return Path(explicit)
    if shutil.which("git"):
        try:
            proc = _run(["git", "rev-parse", "--show-toplevel"], cwd=Path.cwd(), timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    return Path.cwd()


def _error_payload(exc: BaseException, started: float) -> dict:
    """크래시해도 정상 스키마의 골격을 유지한 채 error 키만 채운다.

    소비자가 키 부재로 죽지 않게 하려는 것이다. 트레이스백은 stderr 가 아니라
    notes 에 문자열로 넣는다 — 종료 코드는 여전히 0 이다.
    """
    return {
        "schema": 1, "exit_code": 0, "base": None, "base_reason": "", "base_problem": "",
        "repo_root": None, "changed_files": [], "excluded_files": [], "pruned_files": [],
        "total_seconds": round(time.perf_counter() - started, 3),
        "config": _config_payload(None),
        "checks": [
            {"code": code, "name": name, "label": label, "status": "error", "seconds": 0.0,
             "reason": "gate crashed before this check ran",
             "human_reason": "게이트가 이 항목 전에 멈췄습니다.", "install_hint": None, "findings": []}
            for code, name, label, _ in CHECKS
        ],
        "notes": ["".join(traceback.format_exception(type(exc), exc, exc.__traceback__))],
        "error": f"{type(exc).__name__}: {exc}",
    }


# ---------------------------------------------------------------------------
# 리포트
# ---------------------------------------------------------------------------

def _width(text: str) -> int:
    """한글이 섞인 표를 맞추기 위한 표시 폭 (전각은 2칸)."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _pad(text: str, target: int) -> str:
    return text + " " * max(target - _width(text), 0)


def _status_word(check: dict) -> str:
    if check["code"] == "C2" and check["status"] == "ok":
        return "측정됨"
    return STATUS_KO.get(check["status"], check["status"])


def _shown_or(text, placeholder: str) -> str:
    """표에 넣을 문자열. 비어 있으면 그렇다고 적는다 — 빈칸은 정상 항목처럼 보인다.

    줄이는 일은 여기서만 한다. 기록에는 원문이 그대로 남아 있어야 한다 (D2).
    """
    return _compact(text or "") or placeholder


def _mutation_detail_where(finding: dict) -> str:
    """자리 표기. 줄이나 열이 비어 있으면 물음표로 적는다.

    빈칸으로 두면 정상 항목처럼 보여, 사용자가 없는 자리를 찾으러 간다.
    """
    line = finding.get("line")
    column = finding.get("column")
    return (f"{finding.get('file')}:"
            f"{line if line is not None else '?'}:"
            f"{column if column is not None else '?'}")


def _mutation_detail_tests(tests) -> str:
    """관련 테스트 꼬리말. 두 개까지만 적고 나머지는 개수로 줄인다."""
    if not tests:
        return "  (덮은 테스트 없음)"
    shown = ", ".join(tests[:2])
    return f"  (테스트 {len(tests)}개: {shown}{' 외' if len(tests) > 2 else ''})"


def _mutation_detail_line(finding: dict) -> str:
    """살아남은 변이 한 줄 — 이 줄만 보고 바로 고칠 수 있어야 한다 (D2·R9).

    관련 테스트를 함께 적는다. 그 테스트들이 이 줄을 실행하고도 못 잡았다는 뜻이라,
    어느 테스트의 확인문을 보강해야 하는지가 목록 자체에서 드러난다.
    """
    status = MUTANT_STATUS_KO.get(finding.get("status"), finding.get("status") or "")
    original = _shown_or(finding.get("original"), "(원본 자리를 알 수 없음)")
    replacement = _shown_or(finding.get("replacement"), "(바뀐 것이 비어 있음)")
    return (f"  {_mutation_detail_where(finding)}  [{finding.get('mutator')}] {status}  "
            f"{original} → {replacement}{_mutation_detail_tests(finding.get('tests') or [])}")


def _detail_lines(check: dict, limit: int = 15) -> list:
    code = check["code"]
    out = []
    for f in check["findings"][:limit]:
        if code == "C3":
            out.append(f"  {f['file']}:{f['line']}  {f['function']}  c={f['complexity']}")
        elif code == "C4":
            source = COVERAGE_SOURCE_KO.get(f.get("coverage_source"), f.get("coverage_source"))
            if f.get("crap") is None:
                out.append(f"  {f['file']}:{f['line']}  {f['function']}  c={f['complexity']}  CRAP 계산 실패 (커버리지: {source})")
            else:
                out.append(f"  {f['file']}:{f['line']}  {f['function']}  c={f['complexity']}  "
                           f"v={f['coverage']:.2f}  CRAP={f['crap']:.2f}  (커버리지: {source})")
        elif code == "C5":
            out.append(f"  {f['first_file']}:{f['first_start']}-{f['first_end']}  ↔  "
                       f"{f['second_file']}:{f['second_start']}-{f['second_end']}  ({f['lines']}줄)")
        elif code == "C6":
            out.append(f"  {f['from_file']}:{f['line']}  →  {f['to_file']}  "
                       f"[{f['from_layer']} → {f['to_layer']}] {f['reason']}")
        elif code == "C7":
            out.append(_mutation_detail_line(f))
        elif code == "C1":
            out.append(f"  {f.get('detail', '')}")
    remaining = len(check["findings"]) - limit
    if remaining > 0:
        out.append(f"  ... 외 {remaining}건")
    return out


DETAIL_TITLES = {
    "C1": "테스트 실패",
    "C3": "복잡도 기준 초과",
    "C4": "CRAP 기준 초과",
    "C5": "중복 발견",
    "C6": "의존 방향 위반",
    "C7": "잡히지 않은 변이",
}


def _render_header(payload: dict) -> list:
    """머리글. 시간은 R1 의 1순위 산출물이라 항목 합과 준비 구간을 함께 드러낸다."""
    lines = ["검사 게이트 0단계 — 리포트 전용 (항상 통과)"]
    if payload.get("error"):
        lines.append(f"게이트 내부 오류: {payload['error']}")
    if payload.get("base_problem"):
        lines.append(f"주의: {payload['base_problem']}")
    total = payload.get("total_seconds", 0) or 0.0
    prep = max(total - sum(c.get("seconds", 0.0) for c in (payload.get("checks") or [])), 0.0)
    excluded = len(payload.get("excluded_files") or []) + len(payload.get("pruned_files") or [])
    lines.append(
        f"기준: {payload.get('base') or '(없음)'}   "
        f"변경 파일 {len(payload.get('changed_files') or [])}개 "
        f"(제외 {excluded}개)   "
        f"전체 {total:.2f}초 (준비 {prep:.2f}초 + 항목 {total - prep:.2f}초)"
    )
    return lines + [""]


def _render_table(checks: list) -> list:
    """항목별 상태와 **시간**을 한 표로. 시간 열은 이 게이트의 주 산출물이라 늘 채운다."""
    label_w = max([_width("항목")] + [_width(c["label"]) for c in checks]) + 2
    status_w = max([_width("상태")] + [_width(_status_word(c)) for c in checks]) + 2
    time_w = 9
    lines = [f"{_pad('항목', label_w)}{_pad('상태', status_w)}{_pad('시간', time_w)}결과"]
    for check in checks:
        seconds = f"{check.get('seconds', 0.0):.2f}초"
        result = check.get("human_reason") or check.get("reason") or ""
        if check.get("install_hint"):
            result = f"{result} {check['install_hint']}"
        lines.append(f"{_pad(check['label'], label_w)}{_pad(_status_word(check), status_w)}"
                     f"{_pad(seconds, time_w)}{result}")
    return lines


def _render_details(checks: list) -> list:
    lines: list = []
    for check in checks:
        if not check.get("findings") or check["code"] == "C2":
            continue
        title = DETAIL_TITLES.get(check["code"])
        detail = _detail_lines(check)
        if title and detail:
            lines += ["", title, *detail]
    return lines


def render_human(payload: dict) -> str:
    checks = payload.get("checks") or []
    lines = _render_header(payload) + _render_table(checks) + _render_details(checks)
    notes = payload.get("notes") or []
    if notes:
        lines += ["", "참고"] + [f"  {note}" for note in notes]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """게이트의 인터페이스. 호출 흐름을 구분하는 인자는 의도적으로 없다.

    `--track` / `--mode` / `--flow` / `--stage` 같은 인자를 넣으면 게이트 안에
    "누가 불렀는지"를 아는 코드가 생긴다. 게이트는 코드를 검사하고 결과를 내놓기만
    하고, 언제 부를지는 각 흐름이 정한다. `--only` 와 `--fail-under` 도 같은
    이유로 없다 — 앞은 흐름 구분의 우회로가 되고, 뒤는 종료 코드 0 계약을 깬다.
    """
    parser = argparse.ArgumentParser(
        description="검사 게이트 0단계 — 변경분 코드 검사 리포트 (항상 종료 코드 0)",
    )
    parser.add_argument("--base", type=str, default=None, help="비교 기준 git ref (기본: main → origin/HEAD → HEAD~1 → 빈 트리)")
    parser.add_argument("--config", type=Path, default=None, help=f"기준값 설정 파일 (기본: <저장소 루트>/{CONFIG_NAME})")
    parser.add_argument("--repo-root", type=Path, default=None, help="저장소 루트 (기본: git rev-parse --show-toplevel)")
    parser.add_argument("--json", action="store_true", help="기계용 JSON 출력 (기본은 사람용 한국어 표)")
    return parser


def _emit(payload: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    try:
        print(render_human(payload))
    except Exception as exc:  # noqa: BLE001 — 렌더링이 실패해도 결과는 내놓는다
        print(f"리포트 렌더링에 실패해 JSON 으로 대신 출력합니다 ({type(exc).__name__}).")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv=None) -> int:
    """항상 0 을 돌려준다 — 인자 오류까지 포함해서다.

    `parse_args` 는 모르는 인자를 만나면 `SystemExit(2)` 를 던지는데, 그것은
    `BaseException` 이라 아래 `except Exception` 에 걸리지 않는다. 게이트를 루프로
    걸어 쓰는 흐름에서 커맨드 본문의 오타 하나가 비-0 종료로 흐름을 멈추게 되므로,
    모르는 인자는 무시하고 참고란에 적는다 (R2). 흐름 구분 인자를 받아들이는 것이
    아니라 **무시**한다는 점에서 R5 와도 충돌하지 않는다.
    """
    started = time.perf_counter()
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args, unknown = build_parser().parse_known_args(raw)
    except SystemExit as exc:
        if exc.code in (0, None):
            raise                       # --help 는 argparse 가 이미 출력했다
        broken = ValueError(f"명령줄 인자를 해석하지 못했습니다 (argparse 종료 코드 {exc.code}).")
        _emit(_error_payload(broken, started), as_json="--json" in raw)
        return 0

    try:
        payload = run_gate(args)
    except KeyboardInterrupt:
        raise  # 사용자의 명시적 중단은 삼키지 않는다 — 삼키면 Ctrl-C 로 못 죽는다
    except Exception as exc:  # noqa: BLE001 — 트레이스백 대신 리포트로 알린다
        payload = _error_payload(exc, started)
    if unknown:
        payload["notes"].append("알 수 없는 인자라 무시했습니다: " + " ".join(unknown))

    _emit(payload, as_json=args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
