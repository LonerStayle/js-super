"""C7 뮤테이션 — 고 어댑터 (gremlins).

**미검증 어댑터다.** 이 기계에 Go 툴체인이 없어 한 회차도 돌려 보지 못했다. 아래
사실은 gremlins v0.6.0 태그의 **소스를 직접 읽어** 확인한 것과, 공식 문서를 읽은 것,
그리고 아직 확인하지 못한 것 셋으로 갈라 적는다. 확인 못 한 것은 그렇게 적었다 —
짐작으로 채운 파싱은 반드시 틀린다.

  - [소스 확인] 결과 JSON 의 모양 (`internal/report/internal/structure.go`):
    `{"go_module", "files":[{"file_name", "mutations":[{"type","status","line","column"}]}], ...}`
  - [소스 확인] 상태 낱말 일곱 (`internal/mutator/mutator.go` 의 `Status.String()`):
    `NOT COVERED` / `RUNNABLE` / `SKIPPED` / `LIVED` / `KILLED` / `NOT VIABLE` / `TIMED OUT`.
    **공백이 든 철자다** — 밑줄이 아니다.
  - [소스 확인] 명령줄 이름 (`cmd/unleash.go`): `unleash [path]`, `--output`,
    `--diff`, `--exclude-files`(정규식), `--threshold-efficacy`, `--threshold-mcover`.
  - [소스 확인] 오염 없음 (`cmd/unleash.go:116`): 소스를 `os.MkdirTemp(os.TempDir(), …)`
    로 통째 복사해 그 안에서 변이하고 정상 종료 시 지운다. 사용자 소스를 여는 단계가 없다.
  - [미확인] `file_name` 이 어떤 형태인지 (임시 사본의 절대 경로인지 모듈 상대 경로인지).
    그래서 경로 되돌리기에 접미사 대조 폴백을 둔다 — 아래 `_go_report_path` 참조.
  - [미확인] 실제 실행 시간, 종료 코드, 중단 시 임시 폴더 잔류량, `RUNNABLE` 이 나오는 조건.

증분 실행은 없다 (문서에 회차를 넘겨 결과를 재사용하는 장치가 없다). 대상 한정은
`--diff <기준 ref>` 로 하고, 점수를 낼 때 이번 변경분 목록으로 한 번 더 거른다 —
도구의 대상 판정과 게이트의 변경분 판정이 어긋나도 점수는 R3 를 지킨다.

서브프로세스는 뼈대의 `gate._run` 만 쓴다. 형제 어댑터는 import 하지 않는다.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from scripts import code_gate as gate
from scripts.mutation import score as score_mod

MUTATION_GO_SUFFIXES = frozenset({".go"})

# "대상이 없다" 안내에 실을 대상 설명 (레지스트리가 읽는다).
MUTATION_TARGET_KO = "고 (Go 모듈만)"

# gremlins 어휘 → 게이트 어휘. 일곱 낱말 모두 v0.6.0 소스의 `Status.String()` 에서
# 철자를 그대로 옮겼다 [소스 확인]. 뜻은 같은 파일의 주석을 근거로 짝지었다:
#   NotCovered "identified, but is not covered by tests"      → NoCoverage
#   Runnable   "covered by tests, which means it can be executed" (아직 안 돌았다) → Pending
#   Lived      "tested, but the tests did pass"               → Survived
#   Killed     "tested and the tests failed"                  → Killed
# 표 밖 낱말은 원어 그대로 통과해 unknown 경로가 잡고 분모에서 뺀다 (R4).
GREMLINS_STATUS_TO_GATE = {
    "KILLED": "Killed",
    "LIVED": "Survived",
    "NOT COVERED": "NoCoverage",
    "TIMED OUT": "Timeout",
    "NOT VIABLE": "CompileError",
    "SKIPPED": "Ignored",
    "RUNNABLE": "Pending",
}

_INSTALL_HINT = ("gremlins 를 설치하십시오 "
                 "(go install github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0).")

# 변이 대상에서 빼는 이름 — 테스트 코드와 생성된 코드.
_GO_TEST_SUFFIX = "_test.go"
_GO_GENERATED_SUFFIXES = (".pb.go", "_generated.go", ".gen.go")


def _gate_status(word):
    """도구가 쓴 낱말을 게이트 어휘로. 표에 없으면 원어 그대로 (unknown 경로)."""
    return GREMLINS_STATUS_TO_GATE.get(word, word)


def _go_targets(repo_root: Path, files) -> tuple:
    """(대상, 뺀 것). 테스트 파일·생성된 코드·삭제된 파일은 뺀다."""
    targets: list = []
    dropped: list = []
    for rel in files:
        name = Path(rel).name
        skip = name.endswith(_GO_TEST_SUFFIX) or name.endswith(_GO_GENERATED_SUFFIXES)
        if skip or not (repo_root / rel).is_file():
            dropped.append(rel)
        else:
            targets.append(rel)
    return tuple(targets), tuple(dropped)


def _go_report_path(repo_root: Path, raw: str, targets) -> str | None:
    """리포트의 파일 이름을 저장소 상대 경로로. 못 맞추면 None.

    gremlins 는 소스를 임시 폴더로 복사해 그 안에서 파싱한다. 리포트에 실리는 이름이
    그 사본 안의 절대 경로인지 모듈 상대 경로인지 **확인하지 못했다.** 그래서 두 단계다.
      1) 뼈대의 경로 정규화를 그대로 지난다 — 저장소 안의 경로면 여기서 끝난다
      2) 그래도 이번 대상에 없으면, 대상 목록 중 **접미사가 일치하는 것이 하나뿐일 때만**
         그것으로 본다. 둘 이상이면 맞추지 않는다 — 잘못 맞추면 다른 파일의 점수가 된다
    맞추지 못한 변이는 세지 않고, 그 파일은 실행 뒤 대조(`_mutation_gaps`)가
    "한 줄도 재지 못한 파일" 로 잡아 사용자에게 보인다 (R4).
    """
    rel = gate._rel_to_repo(Path(repo_root), raw)
    if rel in targets:
        return rel
    tail = raw.replace("\\", "/")
    matched = [t for t in targets if _path_tail_matches(tail, t)]
    return matched[0] if len(matched) == 1 else None


def _path_tail_matches(left: str, right: str) -> bool:
    """둘 중 하나가 다른 하나의 경로 접미사인가. 경로 구분자 경계에서만 맞춘다.

    구분자를 보지 않으면 `pkg/xa.go` 가 `a.go` 에 맞아 버린다.
    """
    return left == right or left.endswith("/" + right) or right.endswith("/" + left)


def _go_source_line(lines, line) -> str:
    """변이가 앉은 소스 줄. 자리를 벗어나거나 파일을 못 읽었으면 빈 문자열."""
    if line is None or not 1 <= line <= len(lines):
        return ""
    return lines[line - 1].strip()


def _go_sources(repo_root: Path, targets) -> dict:
    """대상 파일의 줄 목록. 원본 자리를 보여 주려면 파일을 직접 읽어야 한다."""
    sources: dict = {}
    for rel in targets:
        try:
            sources[rel] = (repo_root / rel).read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
    return sources


def _go_record(rel: str, mutation: dict, lines) -> dict:
    """변이 하나를 게이트 기록으로.

    `tests` 는 없다 — gremlins 는 어느 테스트가 덮었는지 주지 않는다. 없는 것을
    지어내지 않고 비운다 (선언부의 `tests: absent` 와 짝이다).
    바꾼 텍스트도 주지 않아 그 칸은 빈다. 원본 자리는 도구가 주는 줄 번호로 파일에서
    읽어 채운다 — 살아남은 변이 한 줄만 보고 고치려면 어느 코드인지 보여야 한다 (R9).
    자바 어댑터가 같은 이유로 같은 방법을 쓴다.
    """
    return {
        "file": rel,
        "line": mutation.get("line"),
        "column": mutation.get("column"),
        "mutator": mutation.get("type"),
        "original": _go_source_line(lines, mutation.get("line")),
        "replacement": "",
        "status": _gate_status(mutation.get("status")),
        "tests": None,
    }


def _go_entry_path(entry, targets, repo_root: Path) -> str | None:
    """리포트 항목 하나가 가리키는 저장소 상대 경로. 못 맞추면 None."""
    raw = entry.get("file_name") if isinstance(entry, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    return _go_report_path(repo_root, raw, targets)


def _go_mutations(entry) -> list:
    """파일 하나의 변이 목록 원문. 모양이 어긋나면 빈 목록이다."""
    mutations = entry.get("mutations") if isinstance(entry, dict) else None
    return [m for m in (mutations or []) if isinstance(m, dict)]


def _go_records_for_file(entry, targets, repo_root: Path, sources: dict) -> list:
    """파일 하나의 변이 목록. 리포트가 어그러져 있어도 그 파일만 비운다."""
    rel = _go_entry_path(entry, targets, repo_root)
    if rel is None:
        return []
    lines = sources.get(rel) or []
    return [_go_record(rel, m, lines) for m in _go_mutations(entry)]


def unmatched_report_files(report: dict, repo_root: Path, targets) -> list:
    """리포트에 있는데 이번 대상 어디에도 못 맞춘 파일 이름 — 서브프로세스 없이 검증된다.

    하나도 못 맞추면 요약이 통째로 비어, 대조(`_mutation_gaps`)가 아니라 "변이가 하나도
    만들어지지 않았습니다" 라는 정상 종료 문장이 나간다 (실측). 살아남은 변이가 있었는데도
    그렇다. 그래서 못 맞춘 이름을 따로 세어 참고에 남긴다 (R4).
    """
    names = [str(entry.get("file_name")) for entry in _go_report_entries(report)
             if entry.get("file_name")]
    return sorted({name for name in names
                   if _go_report_path(repo_root, name, targets) is None})


def _go_report_entries(report) -> list:
    """변이를 하나라도 담은 리포트 항목. 모양이 어긋나면 빈 목록이다."""
    files = report.get("files") if isinstance(report, dict) else None
    if not isinstance(files, list):
        return []
    return [entry for entry in files if isinstance(entry, dict) and _go_mutations(entry)]


def parse_gremlins_report(report: dict, repo_root: Path, targets) -> dict:
    """gremlins JSON 을 게이트 결과로 — 서브프로세스 없이 검증되는 순수 함수.

    `targets` 밖의 파일은 세지 않는다. `--diff` 를 줘도 도구의 대상 판정이 게이트의
    변경분과 어긋날 수 있어, 점수의 범위는 게이트가 정한다 (R3).
    """
    files = report.get("files") if isinstance(report, dict) else None
    if not isinstance(files, list):
        return score_mod.summarize_mutants([])
    sources = _go_sources(Path(repo_root), targets)
    records: list = []
    for entry in files:
        records += _go_records_for_file(entry, targets, repo_root, sources)
    records.sort(key=lambda r: (r["file"], r["line"] or 0, r["column"] or 0))
    return score_mod.summarize_mutants(records)


def _go_preconditions(ctx: gate.GateContext) -> dict | None:
    """고 경로만의 사유. 있으면 그 결과를, 없으면 None (R4).

    Go 툴체인(`go`) 유무는 따로 묻지 않는다. gremlins 가 안에서 `go test` 를 부르므로
    없으면 실행이 실패하고, 그 출력이 사유에 그대로 실린다.
    """
    configured = ctx.config.mutation_tool(GO_ADAPTER.language)
    if configured != GO_ADAPTER.tool:
        return gate._skip(
            f"설정의 {GO_ADAPTER.config_key} 값 '{configured}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported go mutation tool: {configured}",
        )
    tool = gate._tool(ctx, "gremlins")
    if not tool["available"]:
        # 뼈대의 도구 표에는 설치 문구가 없다 (PATH 조회만 한다). 어댑터가 자기 것을 낸다.
        return gate._skip("gremlins 가 설치돼 있지 않습니다.", "gremlins missing",
                          tool["install_hint"] or _INSTALL_HINT)
    if not (ctx.repo_root / "go.mod").is_file():
        return gate._skip(
            "저장소 최상위에 go.mod 가 없어 고 뮤테이션을 재지 않았습니다 "
            "(gremlins 는 Go 모듈 안에서만 돕니다).",
            "no go.mod at repo root")
    return None


def _go_scope(ctx: gate.GateContext, go_files) -> tuple:
    """변이시킬 파일 목록과, 남는 것이 없을 때의 건너뜀 결과."""
    targets, dropped = _go_targets(ctx.repo_root, go_files)
    if dropped:
        ctx.notes.append(
            f"고 뮤테이션 대상에서 테스트·생성된 코드·삭제된 파일 {len(dropped)}개를 뺐습니다: "
            + score_mod._sample_list(list(dropped)))
    if not targets:
        return (), gate._skip(
            f"변경된 고 파일 {len(go_files)}개가 모두 변이 대상이 아닙니다 "
            "(테스트·생성된 코드·삭제된 파일).",
            "no mutable go targets")
    return targets, None


def _go_command(ctx: gate.GateContext, report: Path, targets) -> tuple:
    """(실행할 명령, 결과가 나온 뒤에 남길 안내).

    임계값 둘을 0 으로 명시한다 — 프로젝트의 `.gremlins.yaml` 에 임계값이 있으면
    점수가 낮을 때 종료 코드가 10/11 이 되어 R2 가 깨진다. 명령줄이 설정 파일보다
    세다는 것은 **[미확인]** 이라, 그래도 비-0 이 나오면 종료 코드 대신 리포트를 본다.
    """
    cmd = [gate._tool(ctx, "gremlins")["path"], "unleash", str(ctx.repo_root),
           "--output", str(report),
           "--threshold-efficacy", "0", "--threshold-mcover", "0"]
    notes = ["고 어댑터는 실물로 검증하지 않았습니다 (이 기계에 Go 툴체인이 없습니다). "
             "결과가 이상하면 gremlins 를 직접 돌린 값과 맞대 보십시오."]
    base = getattr(ctx.change, "base", "") or ""
    if base and base != gate.EMPTY_TREE:
        cmd += ["--diff", base]
        # gremlins 는 `--diff` 를 주면 **바뀐 줄 범위 안의 변이만** 돌린다
        # (v0.6.0 `internal/diff/diff.go` 의 IsChanged 를 `internal/engine` 이 변이마다
        # 묻는다) [소스 확인]. 여기서 파일 단위라고 말하면 실제보다 넓게 쟀다고 알리는
        # 셈이고, 사용자가 높은 점수를 "이 파일 전체가 잘 덮였다" 로 읽는다.
        notes.append(
            f"고 뮤테이션은 gremlins 의 --diff {base} 로 이번에 바뀐 줄 범위 안의 변이만 "
            f"돌렸습니다 (대상 파일 {len(targets)}개). 같은 파일의 바뀌지 않은 줄은 재지 "
            "않았습니다. 점수는 게이트의 변경분 목록으로 한 번 더 걸렀습니다.")
    else:
        notes.append(
            f"비교 기준이 없어 모듈 전체를 돌렸습니다. 대상 파일 {len(targets)}개는 파일 "
            "단위로 변이돼 그 안에서 이번에 바뀌지 않은 줄도 함께 변이됩니다. 점수만 이번 "
            "변경분으로 걸렀습니다.")
    return cmd, notes


def _go_tail(proc) -> str:
    """사람용 표에 실을 실패 원문 꼬리. 줄바꿈과 연속 공백을 한 칸으로 접는다.

    표는 항목 하나가 한 줄이라는 전제 위에 있다. 여러 줄인 원문을 그대로 실으면 그
    전제가 깨지고 JSON 의 human_reason 에도 개행이 들어간다.
    """
    detail = ((proc.stdout or "") + (proc.stderr or "")) if proc is not None else ""
    return " ".join(detail.split())[-500:]


def _go_no_report(proc, elapsed: float) -> dict:
    """리포트가 없으면 통과가 아니라 오류다 (R4)."""
    code = proc.returncode if proc is not None else "?"
    return {
        "status": "error",
        "reason": f"gremlins produced no report (exit {code})",
        "human_reason": (f"고 뮤테이션 리포트가 나오지 않았습니다 (종료 코드 {code}). "
                         f"실행 {elapsed:.1f}초  {_go_tail(proc)}"),
        "findings": [],
    }


def _go_timed_out(summary: dict, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단됐을 때. gremlins 는 끝에 한 번 쓰므로 대개 리포트가 아예 없다 (D4)."""
    total = summary["total"] if summary else 0
    return {
        "status": "timeout",
        "reason": f"go mutation timed out after {budget}s ({total} mutants seen)",
        "human_reason": (f"{budget}초 예산을 넘겨 중단했습니다. 대상 파일 {len(targets)}개 중 "
                         f"변이 {total}개까지만 결과에 남았습니다. "
                         "예산을 늘리거나(.code-gate.json 의 mutation.timeout_seconds) 대상을 좁히십시오."),
        "findings": summary["survivors"] if summary else [],
    }


def _go_run(ctx: gate.GateContext, report: Path, cmd: list, targets, scope_notes: list) -> tuple:
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

    payload = gate._read_json_object(report)
    summary = parse_gremlins_report(payload, ctx.repo_root, set(targets)) if payload else None
    elapsed = time.perf_counter() - started
    _go_note_unmatched(ctx, payload, set(targets))
    if timed_out:
        return _go_timed_out(summary, targets, elapsed, budget), summary
    if summary is None:
        return _go_no_report(proc, elapsed), None
    return score_mod._mutation_outcome(ctx, summary, elapsed, targets), summary


def _go_note_unmatched(ctx: gate.GateContext, payload, targets) -> None:
    """리포트에 있는데 이번 대상에 못 맞춘 파일을 참고에 남긴다 (R4)."""
    unmatched = unmatched_report_files(payload, ctx.repo_root, targets) if payload else []
    if unmatched:
        ctx.notes.append(
            f"고 리포트의 파일 이름 {len(unmatched)}개를 이번 대상에 맞추지 못해 그 변이는 "
            f"세지 않았습니다: {score_mod._sample_list(unmatched)}")


def _check_mutation_go(ctx: gate.GateContext, go_files) -> dict:
    """고 경로 하나를 끝까지. 반환은 언어 한 조각(part)이다."""
    outcome, summary = _run_mutation_go(ctx, go_files)
    return {"language": "go", "label": "고", "outcome": outcome, "summary": summary}


def _run_mutation_go(ctx: gate.GateContext, go_files) -> tuple:
    blocked = _go_preconditions(ctx)
    if blocked is not None:
        return blocked, None
    targets, blocked = _go_scope(ctx, go_files)
    if blocked is not None:
        return blocked, None

    work = (ctx.tmpdir / "mutation" / "go")
    work.mkdir(parents=True, exist_ok=True)
    report = work.resolve() / "gremlins.json"
    cmd, scope_notes = _go_command(ctx, report, targets)
    return _go_run(ctx, report, cmd, targets, scope_notes)


def _mutation_changed_go(ctx: gate.GateContext) -> list:
    """C7 이 볼 고 변경 파일. 변경분의 단일 출처는 그대로 ctx.change.files 다."""
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_GO_SUFFIXES]


# ---------------------------------------------------------------------------
# 선언부 — 이 어댑터가 규격에 신고하는 사실 (계약 테스트가 동작과의 일치를 검사한다)
# ---------------------------------------------------------------------------

GO_ADAPTER = score_mod.AdapterSpec(
    language="go",
    label="고",
    tool="gremlins",
    config_key="mutation.go",
    # 변환표 = GREMLINS_STATUS_TO_GATE. 철자는 v0.6.0 소스에서 옮겼다 [소스 확인].
    # 비항등이라 적용을 지우면 계약 테스트가 잡는다.
    status_map=GREMLINS_STATUS_TO_GATE,
    measure_unit="expression",             # 토큰 단위로 바꾼다 [문서]
    skip_report=("SKIPPED 상태로 결과에 실린다 [소스 확인]. 무엇이 왜 건너뛰어지는지는 "
                 "확인하지 못했다 [미확인]"),
    incremental=False,                     # 회차를 넘겨 재사용하는 장치가 문서에 없다
    incremental_triggers=(),
    target_syntax=("파일별 지정이 없다. 모듈 경로 하나를 위치 인자로 주고 `--diff <ref>` 로 "
                   "범위를 좁힌다 (`--exclude-files` 는 정규식). 글롭이 아니라 이스케이프가 "
                   "필요 없고, 점수의 범위는 게이트가 리포트를 걸러 정한다"),
    field_confidence={"line": "tool", "column": "tool", "mutator": "tool",
                      "tests": "absent"},
    requires=(),                           # 게이트에 고 테스트 항목이 없다
    workspace=("게이트 임시 디렉토리에 리포트 하나(매 실행 삭제). 어댑터는 사본을 만들지 "
               "않는다 — 도구가 스스로 `os.TempDir()/gremlins-*` 로 소스를 복사하고 정상 "
               "종료 시 지운다 [소스 확인]. 강제 종료 시 잔류량은 확인하지 못했다. "
               "만료·정리 정책: 없음"),
    copy_limitations=(),                   # 어댑터가 만드는 사본이 없다 (도구 사본은 workspace 에)
)
