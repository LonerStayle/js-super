"""C7 뮤테이션 — 자바스크립트 어댑터 (Stryker).

이 어댑터의 사실관계는 Stryker 10 을 실물로 돌려 확인한 것이다. 특히 두 가지가
구현을 좌우한다.
  - JSON 리포트 경로를 바꾸는 명령줄 옵션이 없다. 설정 파일이 한 개 반드시 필요하고,
    그 파일을 게이트 임시 디렉토리에 두면 대상 프로젝트에는 아무것도 안 남는다.
  - 증분 실행을 켜면 지난 회차에 돌린 파일이 이번 리포트에 섞여 들어온다.
    이번 변경분 목록으로 걸러내지 않으면 R3(변경분만 검사)이 깨진다.

서브프로세스는 뼈대의 `gate._run` 만 쓴다 — `_FORBIDDEN_SUBPROCESS_ARGS` 보호(R2)가
어댑터마다 갈리면 안 된다. 형제 어댑터(python)는 import 하지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from scripts import code_gate as gate
from scripts.mutation import score as score_mod

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
MUTATION_SUFFIXES = frozenset(gate.JS_SUFFIXES | {".vue", ".svelte", ".html", ".htm"})

# "대상이 없다" 안내에 실을 대상 설명 (레지스트리가 읽는다). 확장자 목록을 사람 말로
# 옮기는 규칙은 선언부에 없어 모듈이 자기 몫을 신고한다.
MUTATION_TARGET_KO = "자바스크립트 계열 — .vue / .svelte / .html 포함"


# Stryker 어휘 → 게이트 어휘 변환표. 지금은 항등이다 — 철자가 같은 것은 게이트 어휘가
# 이 스키마에서 온 역사적 우연이고, 두 어휘가 같다는 보장은 없다. 표를 선언만 해 두고
# 변환하지 않으면 도구가 어휘를 바꾼 날 조용히 unknown 경로로 새 나가므로, 기록을 만들 때
# 반드시 이 표를 지난다(_gate_status). 표에 없는 상태는 원어 그대로 통과해 unknown 경로로
# 간다 (R4).
STRYKER_STATUS_TO_GATE = {
    "Killed": "Killed", "Timeout": "Timeout",
    "Survived": "Survived", "NoCoverage": "NoCoverage",
    "CompileError": "CompileError", "RuntimeError": "RuntimeError",
    "Ignored": "Ignored", "Pending": "Pending",
}


def _gate_status(word):
    """도구가 쓴 낱말을 게이트 어휘로. 표에 없으면 원어 그대로 (unknown 경로)."""
    return STRYKER_STATUS_TO_GATE.get(word, word)


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
        "status": _gate_status(mutant.get("status")),
        "tests": [str(t) for t in tests],
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
    lines = score_mod._split_source(entry.get("source") or "")
    records = []
    for mutant in entry.get("mutants") or []:
        if not isinstance(mutant, dict):
            continue
        tests = [index.get(str(t), str(t)) for t in (mutant.get("coveredBy") or [])]
        records.append(_mutant_record(rel, mutant, score_mod.slice_lines(lines, mutant.get("location")), tests))
    return records


def parse_mutation_report(report: dict, targets=None) -> dict:
    """Stryker JSON 리포트를 게이트 결과로 옮긴다 — 서브프로세스 없이 검증되는 순수 함수.

    `targets` 를 주면 그 파일들만 센다. 증분 실행을 켜면 지난 회차에 돌린 파일이 이번
    리포트에 그대로 섞이므로, 이번 변경분으로 걸러내지 않으면 점수가 변경분 밖의 코드까지
    반영한다 (R3).
    """
    files = report.get("files") if isinstance(report, dict) else None
    if not isinstance(files, dict):
        return score_mod.summarize_mutants([])
    index = _test_name_index(report)
    records: list = []
    for rel in sorted(files):
        if targets is None or rel in targets:
            records += _records_for_file(rel, files.get(rel), index)
    return score_mod.summarize_mutants(records)


def _cached_lines(cache: dict, rel: str, sources: dict) -> list:
    """파일 하나를 한 번만 쪼갠다. 변이마다 다시 쪼개면 파싱이 2차로 커진다 (R1)."""
    if rel not in cache:
        cache[rel] = score_mod._split_source(sources.get(rel, ""))
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
        rel = gate._rel_to_repo(Path(repo_root), raw)
        if targets is not None and rel not in targets:
            continue
        original = score_mod.slice_lines(_cached_lines(split, rel, sources), event.get("location"))
        records.append(_mutant_record(rel, event, original, event.get("coveredBy") or []))
    return score_mod.summarize_mutants(records)


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
            plan = gate._read_json_object(entry)
        elif entry.name.endswith("-onMutantTested.json"):
            data = gate._read_json_object(entry)
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
    return gate._rel_to_repo(repo_root, raw)


def _planned_for_targets(plan: dict, repo_root: Path, targets) -> int:
    """계획된 변이 중 이번 대상 파일의 것만 센다.

    증분 실행이면 계획에 지난 회차의 다른 파일까지 들어온다. 거르지 않으면 "몇 개 중 몇 개"
    의 앞 숫자만 모수가 달라져, 다 잰 회차가 덜 잰 것처럼 보고된다 (D4).
    """
    rels = (_plan_mutant_file(item, repo_root) for item in plan.get("mutantPlans") or [])
    return sum(1 for rel in rels if rel in targets)


def _mutation_partial(ctx: gate.GateContext, paths: dict, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단했을 때 — 본 만큼만 내고 못 본 것을 반드시 말한다 (D4·R4).

    JSON 리포트는 실행이 끝날 때 한 번에 쓰이므로 중간에 죽이면 남지 않는다. 그래서
    변이 하나가 끝날 때마다 파일 하나를 남기는 event-recorder 리포터를 함께 켜 둔다.
    """
    plan, events = _read_mutation_events(paths["events"])
    scope = set(targets)
    planned = _planned_for_targets(plan, Path(ctx.repo_root), scope)
    summary = parse_mutation_events(events, ctx.repo_root, _mutation_sources(ctx.repo_root, targets), scope)
    seen = summary["total"]
    timing = score_mod._mutation_timing(elapsed, seen, score_mod._mutation_executed(summary["counts"]))
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
    tail = score_mod._mutation_partial_gaps(summary, targets)
    return {
        "status": "timeout",
        "reason": f"timeout after {budget}s ({seen} of {planned or 'unknown'} mutants tested)",
        "human_reason": (
            f"{budget}초 예산을 넘겨 중단했습니다. {scope} 봤고 나머지는 재지 못했습니다. "
            f"{score_text}. {timing}{tail}"
        ),
        "findings": summary["survivors"],
    }


def _mutation_changed_javascript(ctx: gate.GateContext) -> list:
    """C7 이 볼 변경 파일. 언어 판정을 다시 하는 이유는 확장자 목록이 다르기 때문이다.

    Stryker 10 은 .vue / .svelte / .html / .htm 도 스스로 파싱하는데, 공용 언어 판정이 쓰는
    JS_SUFFIXES 에는 그것들이 없다. 그대로 두면 그 파일들이 흔적 없이 빠져, 남은 파일의
    점수가 변경분 전체의 점수처럼 읽힌다. JS_SUFFIXES 를 넓히면 C2·C6 의 판정까지
    바뀌므로 여기서만 따로 고른다 (변경분의 단일 출처는 그대로 ctx.change.files 다).
    """
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_SUFFIXES]


def _stryker_preconditions(ctx: gate.GateContext) -> dict | None:
    """자바스크립트 경로만의 사유. 있으면 그 결과를, 없으면 None.

    설정 자리와 다룰 줄 아는 도구 이름은 선언부(config_key / tool)에서 읽는다 — 같은
    사실을 여기 또 적으면 선언과 동작이 조용히 갈린다.
    """
    configured = ctx.config.mutation_tool(JAVASCRIPT_ADAPTER.language)
    if configured != JAVASCRIPT_ADAPTER.tool:
        return gate._skip(
            f"설정의 {JAVASCRIPT_ADAPTER.config_key} 값 '{configured}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported js mutation tool: {configured}",
        )
    tool = gate._tool(ctx, "stryker")
    if not tool["available"]:
        return gate._skip("Stryker 가 설치돼 있지 않습니다.", "stryker missing", tool["install_hint"])
    return None


def _mutation_paths(ctx: gate.GateContext) -> dict:
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


def _mutation_command(ctx: gate.GateContext, paths: dict, targets) -> tuple:
    """(실행할 명령, 결과가 나온 뒤에 남길 안내).

    설정 파일은 위치 인자로 넘긴다 — 그래야 프로젝트가 자기 설정을 자동으로 물지 않는다.
    명령줄이 설정 파일보다 세므로, 명령줄에 있는 것만 여기에 둔다.
    안내를 여기서 바로 남기지 않고 돌려주는 이유는, 아무것도 재지 못하고 끝난 회차에도
    "이렇게 걸러서 점수를 냈다" 는 문장이 함께 나가 사용자를 원인에서 멀어지게 해서다.
    """
    cmd = [gate._tool(ctx, "stryker")["path"], "run", str(paths["config"]),
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


def _note_comma_paths(ctx: gate.GateContext, targets) -> None:
    """경로에 쉼표가 든 파일을 알린다.

    `--mutate` 는 쉼표로 목록을 가르므로 경로 안의 쉼표와 구분되지 않는다. 이스케이프로도
    안 풀린다. 실제로 빠졌는지는 실행 뒤 대조(`_missing_target_note`)가 다시 잡는다.
    """
    commas = [rel for rel in targets if "," in rel]
    if commas:
        ctx.notes.append(
            f"경로에 쉼표가 든 파일 {len(commas)}개는 Stryker 에 목록으로 넘길 방법이 없어 "
            "재지 못할 수 있습니다: " + score_mod._sample_list(commas))


def _mutation_scope(ctx: gate.GateContext, js_files) -> tuple:
    """변이시킬 파일 목록과, 남는 것이 없을 때의 건너뜀 결과. 뺀 파일은 사유와 함께 남긴다."""
    targets, dropped = _mutation_targets(ctx.repo_root, js_files)
    _note_comma_paths(ctx, targets)
    if dropped:
        ctx.notes.append(
            f"뮤테이션 대상에서 테스트·타입 선언·삭제된 파일 {len(dropped)}개를 뺐습니다: "
            + score_mod._sample_list(dropped)
        )
    if not targets:
        return (), gate._skip(
            f"변경된 자바스크립트 계열 파일 {len(js_files)}개가 모두 변이 대상이 아닙니다 "
            "(테스트·타입 선언·삭제된 파일).",
            "no mutable javascript targets",
        )
    return targets, None


def _stryker_setup(ctx: gate.GateContext) -> tuple:
    """(프로젝트 설정, 러너, 건너뜀 결과).

    프로젝트 설정도 러너 플러그인도 없으면 Stryker 는 변이마다 `npm test` 를 통째로 돌리는
    러너로 떨어진다. 시간이 자릿수로 늘어나므로 재지 않고 설치 방법을 알린다.
    """
    project_config = _stryker_project_config(ctx.repo_root)
    runner = _stryker_runner(ctx.repo_root)
    if project_config is None and runner is None:
        return None, None, gate._skip(
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


def _mutation_run(ctx: gate.GateContext, paths: dict, cmd: list, targets, scope_notes: list) -> tuple:
    """실행하고 (결과, 요약) 을 만든다. 걸린 시간은 리포트를 다 읽은 뒤에 잰다.

    요약을 함께 돌려주는 이유는 언어가 둘일 때 점수를 개수부터 합쳐 한 번만 계산하기
    위해서다 (D1). 잰 것이 없으면 요약은 None 이다.

    시간을 서브프로세스가 끝난 자리에서 재면 리포트를 읽고 옮기는 시간이 보고 밖으로 샌다.
    표의 초와 문장의 초가 어긋나고, 그 차이는 파일이 커질수록 벌어진다 (R1).
    예산을 넘겨 죽었더라도 리포트가 이미 다 쓰였으면 그것을 쓴다. 완성된 결과를 버리고
    "몇 개 중 몇 개까지 봤다" 고 말하면 앞뒤가 맞지 않는다.
    범위 안내는 실제로 잰 회차에만 남긴다.
    예산은 항목 하나의 것이라 남은 만큼만 쓴다 — 두 언어가 각자 통째로 잡으면 C7 하나가
    설정값의 두 배까지 돈다 (확정 6).
    """
    budget = score_mod._mutation_budget(ctx)
    started = time.perf_counter()
    proc = None
    timed_out = False
    try:
        proc = gate._run(cmd, cwd=ctx.repo_root, timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out = True

    report = gate._read_json_object(paths["report"])
    summary = None
    if not report:
        if not timed_out:
            return _mutation_no_report(proc, time.perf_counter() - started), None
        outcome = _mutation_partial(ctx, paths, targets, time.perf_counter() - started, budget)
    else:
        summary = parse_mutation_report(report, set(targets))
        outcome = score_mod._mutation_outcome(ctx, summary, time.perf_counter() - started, targets)
    ctx.notes.extend(scope_notes)
    return outcome, summary


def _check_mutation_javascript(ctx: gate.GateContext, js_files) -> dict:
    """자바스크립트 경로 하나를 끝까지. 반환은 언어 한 조각(part)이다."""
    outcome, summary = _run_mutation_javascript(ctx, js_files)
    return {"language": "javascript", "label": "자바스크립트", "outcome": outcome, "summary": summary}


def _run_mutation_javascript(ctx: gate.GateContext, js_files) -> tuple:
    blocked = _stryker_preconditions(ctx)
    if blocked is not None:
        return blocked, None
    targets, blocked = _mutation_scope(ctx, js_files)
    if blocked is not None:
        return blocked, None
    project_config, runner, blocked = _stryker_setup(ctx)
    if blocked is not None:
        return blocked, None

    paths = _mutation_paths(ctx)
    _write_stryker_config(paths, project_config, runner)
    cmd, scope_notes = _mutation_command(ctx, paths, targets)
    return _mutation_run(ctx, paths, cmd, targets, scope_notes)


# ---------------------------------------------------------------------------
# 선언부 — 이 어댑터가 규격에 신고하는 사실 (계약 테스트가 동작과의 일치를 검사한다)
# ---------------------------------------------------------------------------

JAVASCRIPT_ADAPTER = score_mod.AdapterSpec(
    language="javascript",
    label="자바스크립트",
    tool="stryker",
    config_key="mutation.javascript",
    # 변환표 = STRYKER_STATUS_TO_GATE. 지금은 항등이고, 항등이어도 기록은 이 표를 지난다
    # (_gate_status) — 선언만 하고 안 쓰면 도구가 어휘를 바꾼 날 표가 아무것도 흡수하지
    # 못한다. 변환표 밖 상태는 원어 그대로 통과해 unknown 경로로 간다 (R4).
    status_map=STRYKER_STATUS_TO_GATE,
    measure_unit="expression",             # 파일 전체를 훑는다 — 건너뛰는 단위가 없다
    skip_report=None,
    incremental=True,
    incremental_triggers=("소스 변경", "테스트 변경"),  # 도구가 스스로 본다
    target_syntax=("명령줄 글롭. 이스케이프는 어댑터가 _stryker_glob 로 한다. "
                   "쉼표는 못 풀어 실행 뒤 대조(_mutation_gaps)가 잡는다"),
    field_confidence={"line": "tool", "column": "tool", "mutator": "tool",
                      "tests": "per-mutant"},
    requires=(),
    workspace=("게이트 임시 디렉토리(매 실행 삭제) + 캐시에 상태 파일 하나"
               "(mutation_state_file). 만료·정리 정책: 없음"),
    copy_limitations=(),                   # 사본을 만들지 않는다
)
