"""C7 뮤테이션 — C# 어댑터 (Stryker.NET).

**미검증 어댑터다.** 이 기계에 .NET 이 없어 한 회차도 돌려 보지 못했다. 아래 사실은
Stryker.NET `dotnet-stryker@4.16.0` 태그의 **소스를 직접 읽어** 확인한 것과, 공식
문서를 읽은 것, 그리고 아직 확인하지 못한 것 셋으로 갈라 적는다.

  - [소스 확인] 상태 낱말 여덟 (`src/Stryker.Abstractions/MutantStatus.cs`):
    Pending / Killed / Survived / Timeout / CompileError / Ignored / NoCoverage /
    RuntimeError. `JsonMutant` 이 `ResultStatus.ToString()` 을 그대로 싣는다.
    **게이트 어휘 여덟과 철자까지 같다** — 게이트 어휘가 이 스키마에서 왔으니 당연하다.
  - [소스 확인] 결과 JSON 은 camelCase (`JsonReportSerialization` 의
    `PropertyNamingPolicy = CamelCase`): `files` / `source` / `mutants` /
    `location.start.line|column` / `status` / `mutatorName` / `coveredBy` / `killedBy`.
    자바스크립트 리포트와 같은 스키마 2 다.
  - [소스 확인] `files` 의 키는 **절대 경로**다 (`JsonReport` 이 `fileComponent.FullPath`
    를 쓴다). 자바스크립트 쪽은 상대 경로라 여기서 갈린다 — 되돌려서 맞춘다.
  - [소스 확인] 리포트 자리 = `<--output>/reports/mutation-report.json`
    (`StrykerOptions.ReportPath` = `Path.Combine(OutputPath, "reports")`,
    `ReportFileNameInput.Default` = `mutation-report`). `--output` 은 **이미 있는
    디렉토리여야** 한다 (`OutputPathInput.Validate` 가 없으면 거절한다).
  - [소스 확인] 명령줄 이름 (`CommandLineConfigReader`): `--output`, `--reporter`,
    `--break-at`, `--solution`, `--mutate`, `--since`. `--since` 는 값이 선택이라
    **`--since:<ref>` 처럼 콜론으로 붙여야** 한다.
  - [소스 확인] 오염 없음 (`docs/technical-reference/mutant-schemata.md`): 변이를 모두
    조건문으로 감싸 한 어셈블리에 함께 컴파일하고 환경변수로 하나씩 켠다. 소스를
    다시 쓰는 단계가 없다. 단 `--output` 을 안 주면 프로젝트 안에 `StrykerOutput/` 이 쌓인다.
  - [미확인] 실행 파일 이름. 전역 도구(`dotnet tool install -g dotnet-stryker`)가 만드는
    `dotnet-stryker` 셸을 직접 부른다고 보고 그 이름을 찾는다. 문서의 표기는 `dotnet stryker` 다.
  - [미확인] 명령줄이 프로젝트 설정 파일(`stryker-config.json`)의 `thresholds.break` 를
    이기는지. 못 이기면 점수가 낮은 회차에서 종료 코드가 비-0 이 될 수 있다 — 그래서
    종료 코드가 아니라 리포트 유무로 판정한다.
  - [미확인] `testFiles` 블록의 정확한 모양, 실행 시간, 중단 시 잔류물, 여러 프로젝트 배치.

증분(`--with-baseline`)은 문서가 실험 기능이라고 표시해 켜지 않는다. 대상 한정은
`--since:<기준 ref>` 로 하고, 점수를 낼 때 이번 변경분 목록으로 한 번 더 거른다.

서브프로세스는 뼈대의 `gate._run` 만 쓴다. 형제 어댑터는 import 하지 않는다.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from scripts import code_gate as gate
from scripts.mutation import score as score_mod

MUTATION_CSHARP_SUFFIXES = frozenset({".cs"})

# "대상이 없다" 안내에 실을 대상 설명 (레지스트리가 읽는다).
MUTATION_TARGET_KO = "C#"

# Stryker.NET 어휘 → 게이트 어휘. 여덟 낱말 모두 4.16.0 소스의 `MutantStatus` 에서
# 철자를 옮겼다 [소스 확인]. 지금은 항등이다 — 게이트 어휘가 이 스키마에서 온 것이라
# 그렇다. 항등이어도 기록은 반드시 이 표를 지난다(_gate_status): 선언만 하고 안 쓰면
# 도구가 어휘를 바꾼 날 표가 아무것도 흡수하지 못한다. 표 밖 낱말은 원어 그대로
# 통과해 unknown 경로가 잡고 분모에서 뺀다 (R4).
STRYKER_NET_STATUS_TO_GATE = {
    "Pending": "Pending", "Killed": "Killed", "Survived": "Survived",
    "Timeout": "Timeout", "CompileError": "CompileError", "Ignored": "Ignored",
    "NoCoverage": "NoCoverage", "RuntimeError": "RuntimeError",
}

_INSTALL_HINT = "Stryker.NET 을 설치하십시오 (dotnet tool install -g dotnet-stryker)."

# 변이 대상에서 빼는 자리와 이름 — 테스트 코드, 빌드 산출물, 생성된 코드.
_CS_TEST_DIRS = frozenset({"test", "tests"})
_CS_TEST_STEMS = ("Test", "Tests", "Spec", "Specs")
_CS_SKIP_DIRS = frozenset({"obj", "bin"})
_CS_GENERATED_SUFFIXES = (".designer.cs", ".g.cs", ".g.i.cs", ".generated.cs")

# `--output` 아래의 리포트 자리 [소스 확인].
_CS_REPORT_TAIL = ("reports", "mutation-report.json")


def _gate_status(word):
    """도구가 쓴 낱말을 게이트 어휘로. 표에 없으면 원어 그대로 (unknown 경로)."""
    return STRYKER_NET_STATUS_TO_GATE.get(word, word)


def _csharp_is_test(rel: str) -> bool:
    """테스트 파일인가. 자리(test/tests 디렉토리)와 이름(…Tests.cs) 둘 다 본다."""
    path = Path(rel)
    stem = path.stem
    return (any(p.lower() in _CS_TEST_DIRS for p in path.parts[:-1])
            or any(stem.endswith(s) for s in _CS_TEST_STEMS))


def _csharp_skipped(repo_root: Path, rel: str) -> bool:
    """대상에서 빼는가. 테스트·빌드 산출물·생성된 코드·삭제된 파일이면 뺀다."""
    path = Path(rel)
    return (_csharp_is_test(rel)
            or any(p.lower() in _CS_SKIP_DIRS for p in path.parts[:-1])
            or path.name.lower().endswith(_CS_GENERATED_SUFFIXES)
            or not (repo_root / rel).is_file())


def _csharp_targets(repo_root: Path, files) -> tuple:
    """(대상, 뺀 것). 뺀 것은 사유와 함께 호출자가 리포트에 남긴다 (R4)."""
    targets: list = []
    dropped: list = []
    for rel in files:
        (dropped if _csharp_skipped(repo_root, rel) else targets).append(rel)
    return tuple(targets), tuple(dropped)


def _cs_tests_of(entry) -> list:
    """테스트 파일 하나가 신고한 테스트. 블록의 모양이 어긋나면 빈 목록이다."""
    tests = entry.get("tests") if isinstance(entry, dict) else None
    return [t for t in (tests or []) if isinstance(t, dict) and t.get("id") is not None]


def _cs_test_index(report: dict, repo_root: Path) -> dict:
    """테스트 id → 사람이 읽는 이름. 블록의 모양은 확인하지 못해 어긋나면 조용히 비운다.

    변이의 coveredBy / killedBy 에는 id 만 들어 있다. 사전을 못 만들면 id 를 그대로
    보여 준다 — 읽기는 나쁘지만 없는 이름을 지어내는 것보다 낫다.
    `testFiles` 의 키도 `files` 와 같은 절대 경로다. 되돌리지 않으면 살아남은 변이 한 줄에
    이 기계의 전체 경로가 실려 표가 깨진다 (실측). 소스 쪽만 되돌리고 여기를 빠뜨렸었다.
    """
    files = report.get("testFiles")
    if not isinstance(files, dict):
        return {}
    return {str(test["id"]): f"{gate._rel_to_repo(repo_root, path)} > {test.get('name') or test['id']}"
            for path, entry in files.items() for test in _cs_tests_of(entry)}


def _cs_record(rel: str, mutant: dict, original: str, tests) -> dict:
    """변이 하나를 게이트 기록으로. 자바스크립트 리포트와 같은 칸을 읽는다."""
    start = (mutant.get("location") or {}).get("start") or {}
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


def _cs_mutants(entry) -> list:
    """파일 하나의 변이 목록 원문. 모양이 어긋나면 빈 목록이다."""
    mutants = entry.get("mutants") if isinstance(entry, dict) else None
    return [m for m in (mutants or []) if isinstance(m, dict)]


def _cs_source_lines(entry) -> list:
    """파일 원본을 줄 목록으로. 변이 자리를 잘라내는 데 쓴다."""
    source = entry.get("source") if isinstance(entry, dict) else ""
    return score_mod._split_source(source or "")


def _cs_named_tests(mutant: dict, index: dict) -> list:
    """변이를 덮은 테스트 이름. 사전에 없는 id 는 그대로 보여 준다."""
    return [index.get(str(t), str(t)) for t in (mutant.get("coveredBy") or [])]


def _cs_records_for_file(rel: str, entry, index: dict) -> list:
    """파일 하나의 변이 목록. 리포트가 어그러져 있어도 그 파일만 비운다."""
    lines = _cs_source_lines(entry)
    return [_cs_record(rel, mutant, score_mod.slice_lines(lines, mutant.get("location")),
                       _cs_named_tests(mutant, index))
            for mutant in _cs_mutants(entry)]


def parse_stryker_net_report(report: dict, repo_root: Path, targets) -> dict:
    """Stryker.NET JSON 을 게이트 결과로 — 서브프로세스 없이 검증되는 순수 함수.

    키가 절대 경로라 저장소 상대로 되돌린 뒤 이번 대상만 센다 (R3).
    """
    files = report.get("files") if isinstance(report, dict) else None
    if not isinstance(files, dict):
        return score_mod.summarize_mutants([])
    index = _cs_test_index(report, Path(repo_root))
    records: list = []
    for raw in sorted(files):
        rel = gate._rel_to_repo(Path(repo_root), raw)
        if targets is None or rel in targets:
            records += _cs_records_for_file(rel, files.get(raw), index)
    return score_mod.summarize_mutants(records)


def _csharp_solution(repo_root: Path) -> Path | None:
    """저장소 최상위의 솔루션 파일. 없으면 None (프로젝트 하나짜리 배치)."""
    for pattern in ("*.sln", "*.slnx"):
        found = sorted(repo_root.glob(pattern))
        if found:
            return found[0]
    return None


def _csharp_has_project(repo_root: Path) -> bool:
    """C# 프로젝트가 있는가. 깊이 셋까지만 본다 — 더 깊이 훑으면 R1 을 깎는다."""
    if _csharp_solution(repo_root) is not None:
        return True
    # `any(글롭 제너레이터 …)` 로 쓰면 제너레이터 객체 자체가 늘 참이라 언제나 True 가 된다.
    return any(any(repo_root.glob(pattern))
               for pattern in ("*.csproj", "*/*.csproj", "*/*/*.csproj"))


def _csharp_preconditions(ctx: gate.GateContext) -> dict | None:
    """C# 경로만의 사유. 있으면 그 결과를, 없으면 None (R4)."""
    configured = ctx.config.mutation_tool(CSHARP_ADAPTER.language)
    if configured != CSHARP_ADAPTER.tool:
        return gate._skip(
            f"설정의 {CSHARP_ADAPTER.config_key} 값 '{configured}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported csharp mutation tool: {configured}",
        )
    tool = gate._tool(ctx, "dotnet-stryker")
    if not tool["available"]:
        # 뼈대의 도구 표에는 설치 문구가 없다 (PATH 조회만 한다). 어댑터가 자기 것을 낸다.
        return gate._skip("Stryker.NET 이 설치돼 있지 않습니다.", "dotnet-stryker missing",
                          tool["install_hint"] or _INSTALL_HINT)
    if not _csharp_has_project(ctx.repo_root):
        return gate._skip(
            "C# 프로젝트 파일(.sln / .csproj)을 찾지 못해 C# 뮤테이션을 재지 않았습니다.",
            "no csharp project file")
    return None


def _csharp_scope(ctx: gate.GateContext, cs_files) -> tuple:
    """변이시킬 파일 목록과, 남는 것이 없을 때의 건너뜀 결과."""
    targets, dropped = _csharp_targets(ctx.repo_root, cs_files)
    if dropped:
        ctx.notes.append(
            f"C# 뮤테이션 대상에서 테스트·빌드 산출물·생성된 코드·삭제된 파일 {len(dropped)}개를 뺐습니다: "
            + score_mod._sample_list(list(dropped)))
    if not targets:
        return (), gate._skip(
            f"변경된 C# 파일 {len(cs_files)}개가 모두 변이 대상이 아닙니다 "
            "(테스트·빌드 산출물·생성된 코드·삭제된 파일).",
            "no mutable csharp targets")
    return targets, None


def _csharp_command(ctx: gate.GateContext, out_dir: Path, targets) -> tuple:
    """(실행할 명령, 결과가 나온 뒤에 남길 안내).

    `--break-at 0` 을 명시한다 — 프로젝트 설정에 임계값이 있으면 점수가 낮을 때
    종료 코드가 비-0 이 되어 R2 가 깨진다. 명령줄이 설정 파일을 이기는지는 확인하지
    못해, 판정은 종료 코드가 아니라 리포트 유무로 한다.
    """
    cmd = [gate._tool(ctx, "dotnet-stryker")["path"],
           "--output", str(out_dir), "--reporter", "json", "--break-at", "0"]
    solution = _csharp_solution(ctx.repo_root)
    if solution is not None:
        cmd += ["--solution", str(solution)]
    notes = [
        f"C# 뮤테이션은 변경된 파일 {len(targets)}개를 파일 단위로 변이시켰습니다. "
        "그 파일 안에서 이번에 바뀌지 않은 줄도 함께 변이됩니다. "
        "산출물은 게이트 임시 디렉토리로 돌려 프로젝트에 StrykerOutput 이 쌓이지 않게 했습니다.",
        "C# 어댑터는 실물로 검증하지 않았습니다 (이 기계에 .NET 이 없습니다). "
        "결과가 이상하면 Stryker.NET 을 직접 돌린 값과 맞대 보십시오.",
    ]
    base = getattr(ctx.change, "base", "") or ""
    if base and base != gate.EMPTY_TREE:
        # 값이 선택인 옵션이라 콜론으로 붙여야 한다 [소스 확인].
        cmd.append(f"--since:{base}")
        notes.append(f"변경분 한정은 Stryker.NET 의 --since:{base} 로 넘겼고, 점수는 게이트의 변경분 목록으로 한 번 더 걸렀습니다.")
    else:
        notes.append("비교 기준이 없어 프로젝트 전체를 돌렸고, 점수만 이번 변경분으로 걸렀습니다.")
    return cmd, notes


def _csharp_tail(proc) -> str:
    """사람용 표에 실을 실패 원문 꼬리. 줄바꿈과 연속 공백을 한 칸으로 접는다.

    표는 항목 하나가 한 줄이라는 전제 위에 있다. 여러 줄인 원문을 그대로 실으면 그
    전제가 깨지고 JSON 의 human_reason 에도 개행이 들어간다.
    """
    detail = ((proc.stdout or "") + (proc.stderr or "")) if proc is not None else ""
    return " ".join(detail.split())[-500:]


def _csharp_no_report(proc, elapsed: float) -> dict:
    """리포트가 없으면 통과가 아니라 오류다 (R4)."""
    code = proc.returncode if proc is not None else "?"
    return {
        "status": "error",
        "reason": f"stryker.net produced no report (exit {code})",
        "human_reason": (f"C# 뮤테이션 리포트가 나오지 않았습니다 (종료 코드 {code}). "
                         f"실행 {elapsed:.1f}초  {_csharp_tail(proc)}"),
        "findings": [],
    }


def _csharp_timed_out(summary: dict, targets, budget: int) -> dict:
    """예산을 넘겨 중단됐을 때 — 본 만큼만 낸다 (D4)."""
    total = summary["total"] if summary else 0
    return {
        "status": "timeout",
        "reason": f"csharp mutation timed out after {budget}s ({total} mutants seen)",
        "human_reason": (f"{budget}초 예산을 넘겨 중단했습니다. 대상 파일 {len(targets)}개 중 "
                         f"변이 {total}개까지만 결과에 남았습니다. "
                         "예산을 늘리거나(.code-gate.json 의 mutation.timeout_seconds) 대상을 좁히십시오."),
        "findings": summary["survivors"] if summary else [],
    }


def _csharp_run(ctx: gate.GateContext, out_dir: Path, cmd: list, targets, scope_notes: list) -> tuple:
    """실행하고 (결과, 요약) 을 만든다. 걸린 시간은 리포트를 다 읽은 뒤에 잰다."""
    budget = score_mod._mutation_budget(ctx)
    # 범위 안내는 실행 **전에** 남긴다. 완주 분기에만 두었더니 중단·리포트 없음 회차에서
    # "이 어댑터는 실물로 검증하지 않았다" 는 경고가 통째로 사라졌다 (실측). 그 경고가
    # 가장 필요한 순간이 바로 실패한 회차다 (R4).
    ctx.notes.extend(scope_notes)
    started = time.perf_counter()
    proc = None
    timed_out = False
    try:
        proc = gate._run(cmd, cwd=ctx.repo_root, timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out = True

    payload = gate._read_json_object(out_dir.joinpath(*_CS_REPORT_TAIL))
    summary = parse_stryker_net_report(payload, ctx.repo_root, set(targets)) if payload else None
    elapsed = time.perf_counter() - started
    if timed_out:
        return _csharp_timed_out(summary, targets, budget), summary
    if summary is None:
        return _csharp_no_report(proc, elapsed), None
    return score_mod._mutation_outcome(ctx, summary, elapsed, targets), summary


def _check_mutation_csharp(ctx: gate.GateContext, cs_files) -> dict:
    """C# 경로 하나를 끝까지. 반환은 언어 한 조각(part)이다."""
    outcome, summary = _run_mutation_csharp(ctx, cs_files)
    return {"language": "csharp", "label": "C#", "outcome": outcome, "summary": summary}


def _run_mutation_csharp(ctx: gate.GateContext, cs_files) -> tuple:
    blocked = _csharp_preconditions(ctx)
    if blocked is not None:
        return blocked, None
    targets, blocked = _csharp_scope(ctx, cs_files)
    if blocked is not None:
        return blocked, None

    out_dir = (ctx.tmpdir / "mutation" / "csharp")
    out_dir.mkdir(parents=True, exist_ok=True)   # --output 은 이미 있는 디렉토리여야 한다
    out_dir = out_dir.resolve()
    cmd, scope_notes = _csharp_command(ctx, out_dir, targets)
    return _csharp_run(ctx, out_dir, cmd, targets, scope_notes)


def _mutation_changed_csharp(ctx: gate.GateContext) -> list:
    """C7 이 볼 C# 변경 파일. 변경분의 단일 출처는 그대로 ctx.change.files 다."""
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_CSHARP_SUFFIXES]


# ---------------------------------------------------------------------------
# 선언부 — 이 어댑터가 규격에 신고하는 사실 (계약 테스트가 동작과의 일치를 검사한다)
# ---------------------------------------------------------------------------

CSHARP_ADAPTER = score_mod.AdapterSpec(
    language="csharp",                     # 파일 이름과 함수 이름이 이 값을 따라 `c#` 은 못 쓴다
    label="C#",
    tool="dotnet-stryker",                 # 전역 도구가 만드는 실행 파일 이름 [미확인]
    config_key="mutation.csharp",
    # 변환표 = STRYKER_NET_STATUS_TO_GATE. 철자는 4.16.0 소스에서 옮겼다 [소스 확인].
    # 항등이라 적용을 지워도 출력이 같다 — 자바스크립트 어댑터와 같은 빈틈이다.
    status_map=STRYKER_NET_STATUS_TO_GATE,
    measure_unit="expression",             # 구문 트리 노드 단위로 바꾼다 [문서]
    skip_report=("Ignored 상태로 결과에 실린다 (`ignore-mutations` 설정과 mutate 필터) "
                 "[문서]. 실물로 확인하지 못했다 [미확인]"),
    incremental=False,                     # --with-baseline 은 문서가 실험 기능이라 켜지 않는다
    incremental_triggers=(),
    target_syntax=("`--since:<ref>` 로 범위를 좁힌다 (값이 선택인 옵션이라 콜론으로 붙인다). "
                   "파일별 지정은 `--mutate <글롭>` 이지만 글롭 이스케이프 규칙을 확인하지 "
                   "못해 쓰지 않는다 — 대괄호가 든 경로가 조용히 빠지는 자리다. "
                   "점수의 범위는 게이트가 리포트를 걸러 정한다"),
    field_confidence={"line": "tool", "column": "tool", "mutator": "tool",
                      "tests": "per-mutant"},
    requires=(),                           # 게이트에 C# 테스트 항목이 없다
    workspace=("게이트 임시 디렉토리의 `--output` 아래(매 실행 삭제). `--output` 을 안 주면 "
               "프로젝트 안 StrykerOutput/ 에 쌓이므로 반드시 준다. 어댑터는 사본을 만들지 "
               "않는다 — 도구가 변이를 한 어셈블리에 함께 컴파일한다. 만료·정리 정책: 없음"),
    copy_limitations=(),                   # 사본을 만들지 않는다
)
