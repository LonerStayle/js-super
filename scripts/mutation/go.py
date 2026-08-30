"""C7 뮤테이션 — 고 어댑터 (gremlins).

**실물로 검증했다.** go 1.27.0 darwin/arm64 에 `go install
github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0` 으로 깐 바이너리를, 일부러 세
갈래(테스트가 값을 확인하는 함수 / 부르기만 하고 확인하지 않는 함수 / 테스트가 없는
함수)를 넣은 장난감 모듈에 돌려 아래를 하나씩 봤다. 직접 본 것은 [실측], 소스만 읽은
것은 [소스 확인], 아직 못 본 것은 [미확인] 으로 적는다.

  - [실측] 결과 JSON 의 모양: `{"go_module", "files":[{"file_name",
    "mutations":[{"type","status","line","column"}]}], "test_efficacy",
    "mutations_coverage", "mutants_total", "mutants_killed", "mutants_lived",
    "mutants_not_viable", "mutants_not_covered", "elapsed_time",
    "mutator_statistics"}. 게이트는 `files` 만 읽는다 — 도구의 합계는 NOT COVERED 를
    `mutants_total` 에서 빼는 등 셈법이 게이트와 달라, 개수는 게이트가 다시 센다.
  - [실측] `file_name` 은 **모듈 루트 기준 상대 경로**다 (`calc.go`,
    `pkg/util/util.go`). 절대 경로도, 도구가 만드는 임시 사본 안의 경로도 아니었고,
    gremlins 를 어느 디렉토리에서 부르든 같았다. 그래서 뼈대의 경로 정규화만으로
    대상과 맞는다 — `_go_report_path` 의 접미사 대조는 그 뒤에 남겨 둔 보호막이다.
  - [실측] 상태 낱말은 **공백이 든 철자**다 (밑줄이 아니다). 다섯은 직접 봤다:
    `KILLED` / `LIVED` / `NOT COVERED` / `SKIPPED` / `TIMED OUT`. `RUNNABLE` 은
    `--dry-run` 회차에서만 나왔다 [실측]. `NOT VIABLE` 은 만들어 보지 못해
    [소스 확인] 으로 남는다 (`internal/mutator/mutator.go` 의 `Status.String()`).
  - [실측] 명령줄: `unleash [path]`, `--output`, `--diff`, `--exclude-files`(파일 경로
    정규식. `--help` 상 stringArray 라 여러 번 줄 수 있다), `--threshold-efficacy`,
    `--threshold-mcover`, `--timeout-coefficient`, `--dry-run`.
  - [실측] 종료 코드: 정상 0 / 모듈이 아닌 경로 1 / 없는 `--diff` ref 1 /
    `.gremlins.yaml` 의 `unleash.threshold.efficacy` 미달 10 / `mutant-coverage`
    미달 11. `--config` 로 준 파일을 못 읽으면 1 [소스 확인]. 이름으로 찾아 읽는
    `.gremlins.yaml` 이 깨져 있으면 오류 없이 무시하고 그냥 돈다 [실측].
  - [실측] 임계값을 명령줄에 주면 **판정에 쓰이지 않는다.** v0.6.0 이 쓰는 viper 판이
    float64 플래그를 문자열로 돌려주고, 도구는 그것을 float64/int 로 단언해 읽어 둘 다
    0 이 된다 (0 은 "검사 안 함"). 그런데 플래그를 명시하면 그 값이 설정 파일 값을
    가려, 결과적으로 임계 검사가 꺼진다 — 아래 `_go_command` 가 0 을 박아 넣는 이유다.
    설정 파일에 임계값 90 을 두고 플래그 없이 돌리면 종료 코드 10, 같은 설정에
    `--threshold-efficacy 0 --threshold-mcover 0` 을 붙이면 0 이었다 [실측].
  - [실측] `--diff <ref>` 는 gremlins 가 **자기 현재 디렉토리에서**
    `git diff --merge-base <ref>` 를 돌려 만든다. 범위 계산이 거칠다: 헝크마다
    "새 위치 + 앞 문맥 줄 수" 부터 "추가된 줄 수" 만큼만 한 구간으로 본다
    (`internal/diff/diff.go` 의 `newChanges`). 추가된 줄이 문맥과 번갈아 나오면 뒤쪽
    변경이 구간 밖으로 떨어져 그 변이가 `SKIPPED` 로 실린다 — 장난감 모듈에서 변이
    4개 중 3개가 그렇게 빠졌다 [실측].
  - [실측] 오염 없음. 실행 전후로 프로젝트 안의 파일 목록이 같았다. 도구는 소스를
    `os.MkdirTemp(os.TempDir(), "gremlins-")` 아래로 복사해 그 안에서 변이하고 정상
    종료 시 지운다.
  - [실측] 강제 종료(SIGKILL) 하면 리포트가 없고 그 임시 폴더가 **남는다**. 변이 도중
    죽인 회차에서 22MB 였다 (Go 빌드 캐시 + 작업자별 소스 사본). 게이트의 예산 초과
    경로가 바로 이 강제 종료다.
  - [실측] 변이가 하나도 없으면 `--output` 파일을 **아예 만들지 않고** 종료 코드 0 으로
    끝난다 ("No results to report."). 구조체 선언만 든 파일을 바꿨을 때가 그렇다.
  - [실측] 변이 하나의 제한시간은 **커버리지 수집에 걸린 시간 × 계수(기본 3)** 다
    (`internal/engine/executor.go`). 빌드 캐시가 더워 커버리지가 100ms 에 끝나면
    제한시간이 0.3초가 되어 멀쩡한 변이도 `TIMED OUT` 으로 실린다 — 같은 모듈이 첫
    회차에 KILLED 1 / LIVED 2 였다가 다음 회차에 TIMED OUT 3 이 됐다. 게이트는
    Timeout 을 잡은 것으로 세므로 점수가 부풀 수 있다. `_go_note_timeouts` 가 그 사실을
    참고에 남긴다 (R4).
  - [실측] 시간: 장난감 모듈(변이 4개) 0.5초. 함수 40개짜리 모듈(변이 160개) 47.7초,
    변이당 0.30초. 준비 비용(커버리지 수집 한 번)이 앞에 얹힌다.
  - [실측] `go install` 은 바이너리를 `go env GOPATH`/bin 에 놓는다. 그 자리가 PATH 에
    없으면 뼈대의 PATH 조회가 도구를 못 찾아 이 언어가 통째로 건너뛰어진다 (러스트의
    `~/.cargo/bin` 과 같은 자리다). 설치 안내가 그 사실을 함께 말한다.
  - [미확인] `NOT VIABLE` 이 실제로 나오는 조건. 컴파일되지 않는 변이를 만드는 입력을
    찾지 못했다.

증분 실행은 없다 (회차를 넘겨 결과를 재사용하는 장치가 없다). 대상 한정은
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
# 철자를 옮겼고, 그중 여섯은 실물 리포트에서도 그대로 봤다 [실측 — NOT VIABLE 만 못 봤다].
# 뜻은 같은 파일의 주석과 실측을 근거로 짝지었다:
#   NotCovered "identified, but is not covered by tests"      → NoCoverage
#   Runnable   "covered by tests, which means it can be executed" (아직 안 돌았다) → Pending
#              — `--dry-run` 회차에서만 나온다 [실측]
#   Lived      "tested, but the tests did pass"               → Survived
#   Killed     "tested and the tests failed"                  → Killed
#   Skipped    `--diff` 로 좁힌 구간 밖의 변이 [실측]         → Ignored
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
                 "(go install github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0). "
                 "설치 자리는 `go env GOPATH`/bin 이라, 그 자리가 PATH 에 있어야 "
                 "게이트가 찾습니다.")

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

    리포트의 이름은 **모듈 루트 기준 상대 경로**였다 [실측: `calc.go`,
    `pkg/util/util.go`]. 도구가 소스를 임시 폴더로 복사해 그 안에서 변이하는데도 사본
    경로가 새 나오지 않았고, gremlins 를 어느 디렉토리에서 부르든 같았다. 그래서
    실무에서는 1단계에서 끝난다. 2단계는 남겨 둔 보호막이다 — 도구가 판을 올리며 이름
    형태를 바꾸면 여기서 흡수하고, 못 맞추면 조용히 세지 않는 대신 이름을 알린다.
      1) 뼈대의 경로 정규화를 그대로 지난다 — 저장소 안의 경로면 여기서 끝난다
      2) 그래도 이번 대상에 없으면, 대상 목록 중 **접미사가 일치하는 것이 하나뿐일 때만**
         그것으로 본다. 둘 이상이면 맞추지 않는다 — 잘못 맞추면 다른 파일의 점수가 된다
    맞추지 못한 변이는 세지 않고, 그 이름은 `_go_note_unmatched` 가 참고에 남긴다 (R4).
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

    Go 툴체인(`go`) 유무는 따로 묻지 않는다. gremlins 가 안에서 `go` 를 부르므로 없으면
    실행이 실패하고, 그 출력이 사유에 그대로 실린다 [실측: 종료 코드 1 과
    `failed to gather coverage: … exec: "go": executable file not found in $PATH` 가
    사람용 표에 그대로 나왔다].
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
    점수가 낮을 때 종료 코드가 10/11 이 되어 R2 가 깨진다 [실측: 설정만 두고 돌리니
    종료 코드 10]. 명령줄에 0 을 붙이면 그 값이 설정 파일 값을 가려 임계 검사가 꺼진다
    [실측: 같은 설정에 0 두 개를 붙이니 종료 코드 0]. 그래도 비-0 이 나오는 회차에
    대비해 판정은 종료 코드가 아니라 리포트로 한다.
    """
    cmd = [gate._tool(ctx, "gremlins")["path"], "unleash", str(ctx.repo_root),
           "--output", str(report),
           "--threshold-efficacy", "0", "--threshold-mcover", "0"]
    notes: list = []
    base = getattr(ctx.change, "base", "") or ""
    if base and base != gate.EMPTY_TREE:
        cmd += ["--diff", base]
        # gremlins 는 `--diff` 를 주면 **바뀐 줄 범위 안의 변이만** 돌린다. 그 범위를
        # 헝크마다 "앞 문맥 다음 줄부터 추가된 줄 수만큼" 한 구간으로 잡아, 추가된 줄이
        # 문맥과 번갈아 나오면 뒤쪽 변경이 구간 밖으로 떨어진다 [실측: 장난감 모듈에서
        # 변이 4개 중 3개가 SKIPPED]. 파일 단위라고 말하면 실제보다 넓게 쟀다고 알리는
        # 셈이고, 빠진 몫을 말하지 않으면 좁게 잰 점수가 변경분 전체처럼 읽힌다.
        notes.append(
            f"고 뮤테이션은 gremlins 의 --diff {base} 로 이번에 바뀐 줄 범위 안의 변이만 "
            f"돌렸습니다 (대상 파일 {len(targets)}개). gremlins 는 그 범위를 헝크마다 앞 "
            "문맥 다음 줄부터 추가된 줄 수만큼으로 잡아, 바뀐 줄이 흩어져 있으면 뒤쪽 "
            "변경이 범위 밖으로 떨어져 '제외됨' 으로 실립니다. 제외된 변이는 점수 분모에 "
            "없습니다. 점수는 게이트의 변경분 목록으로 한 번 더 걸렀습니다.")
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


def _go_no_report(proc, targets, elapsed: float) -> dict:
    """리포트 파일이 없을 때. 종료 코드 0 이면 오류가 아니라 "변이가 없었다" 다.

    gremlins 는 변이 목록이 비면 "No results to report." 만 찍고 `--output` 파일을
    아예 만들지 않은 채 0 으로 끝난다 [실측: 구조체 선언만 든 파일을 바꾼 회차].
    이것을 오류로 내던 동안, 멀쩡히 끝난 회차가 "리포트가 나오지 않았습니다 (종료 코드
    0)" 로 나갔다 — 진짜 실패(모듈이 아닌 경로·없는 diff ref, 둘 다 종료 코드 1 [실측])
    와 구분이 사라진다. 비-0 은 그대로 오류다. 통과로 내지는 않는다 (R4).
    """
    code = proc.returncode if proc is not None else None
    if code == 0:
        return gate._skip(
            f"대상 파일 {len(targets)}개에서 변이가 하나도 만들어지지 않아 gremlins 가 "
            f"리포트를 남기지 않았습니다. 실행 {elapsed:.1f}초",
            "no mutants for changed files")
    return {
        "status": "error",
        "reason": f"gremlins produced no report (exit {code if code is not None else '?'})",
        "human_reason": (f"고 뮤테이션 리포트가 나오지 않았습니다 "
                         f"(종료 코드 {code if code is not None else '?'}). "
                         f"실행 {elapsed:.1f}초  {_go_tail(proc)}"),
        "findings": [],
    }


def _go_timed_out(summary: dict, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단됐을 때. gremlins 는 끝에 한 번 쓰므로 리포트가 아예 없다 (D4).

    예산 초과는 `gate._run` 이 SIGKILL 로 끝낸다. 변이 도중 그렇게 죽인 회차에서
    리포트가 없었고, 도구가 쓰던 `$TMPDIR/gremlins-*` 는 남았다 [실측 — 22MB].
    """
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
    # 안내가 통째로 사라졌다 (실측). 무엇을 어디까지 재려 했는지가 가장 필요한 순간이
    # 바로 실패한 회차다 — 도구 문제인지 범위 문제인지 가를 단서가 그것뿐이다 (R4).
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
    _go_note_timeouts(ctx, summary)
    if timed_out:
        return _go_timed_out(summary, targets, elapsed, budget), summary
    if summary is None:
        return _go_no_report(proc, targets, elapsed), None
    return score_mod._mutation_outcome(ctx, summary, elapsed, targets), summary


def _go_note_timeouts(ctx: gate.GateContext, summary) -> None:
    """TIMED OUT 이 섞였으면 그 뜻을 적는다 — 게이트는 이것을 잡은 것으로 센다 (R4).

    gremlins 는 변이 하나의 제한시간을 커버리지 수집에 걸린 시간의 3배로 잡는다
    [실측]. 테스트가 빨리 끝나는 저장소에서는 그 3배가 컴파일 시간에도 못 미쳐, 멀쩡히
    살아남았어야 할 변이가 TIMED OUT 으로 실린다 — 같은 모듈이 회차에 따라 KILLED 1 /
    LIVED 2 에서 TIMED OUT 3 으로 바뀌었다 (점수 33% → 100%). 말하지 않으면 그 100% 가
    "다 잡았다" 로 읽힌다.
    """
    count = (summary or {}).get("counts", {}).get("Timeout", 0)
    if not count:
        return
    ctx.notes.append(
        f"고 변이 {count}개가 제한시간을 넘겨(TIMED OUT) 끝났고, 게이트는 이것을 잡은 "
        "것으로 셉니다. gremlins 는 변이 하나의 제한시간을 커버리지 수집에 걸린 시간의 "
        "3배로 잡아, 테스트가 빨리 끝나는 저장소에서는 멀쩡한 변이도 여기 걸립니다. "
        "점수가 실제보다 높을 수 있으니, 프로젝트의 .gremlins.yaml 에서 "
        "unleash.timeout-coefficient 를 올려 다시 재 보십시오.")


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
    # 변환표 = GREMLINS_STATUS_TO_GATE. 철자는 v0.6.0 소스에서 옮겼고 여섯은 실물
    # 리포트에서도 봤다 [실측]. 비항등이라 적용을 지우면 계약 테스트가 잡는다.
    status_map=GREMLINS_STATUS_TO_GATE,
    measure_unit="expression",             # 한 줄에서 여러 변이가 나온다 [실측: `return v > 0` 한 줄에 2개]
    skip_report=("SKIPPED 상태로 결과에 실린다 [실측]. `--diff` 로 좁혔을 때 그 구간 밖에 "
                 "있는 변이가 이 상태로 실리고, 게이트는 '제외됨' 으로 옮겨 점수 분모에서 "
                 "뺀다. `--diff` 를 주지 않은 회차에서는 SKIPPED 가 나오지 않았다 [실측]"),
    incremental=False,                     # 회차를 넘겨 재사용하는 장치가 없다
    incremental_triggers=(),
    target_syntax=("파일별 지정이 없다. 모듈 경로 하나를 위치 인자로 주고 `--diff <git ref>` "
                   "로 범위를 좁힌다 — diff 파일이 아니라 ref 이고, gremlins 가 자기 현재 "
                   "디렉토리에서 `git diff --merge-base <ref>` 를 직접 돌린다 [실측]. 빼는 "
                   "쪽은 `--exclude-files <정규식>` 이고 여러 번 줄 수 있다 [실측]. 글롭이 "
                   "아니라 이스케이프가 필요 없고, 점수의 범위는 게이트가 리포트를 걸러 정한다"),
    field_confidence={"line": "tool", "column": "tool", "mutator": "tool",
                      "tests": "absent"},
    requires=(),                           # 게이트에 고 테스트 항목이 없다
    workspace=("게이트 임시 디렉토리에 리포트 하나(매 실행 삭제). 어댑터는 사본을 만들지 "
               "않는다 — 도구가 스스로 `$TMPDIR/gremlins-*` 로 소스를 복사하고 정상 종료 "
               "시 지운다 [실측: 실행 전후로 그 자리에 아무것도 남지 않았다]. **강제 종료 "
               "시에는 남는다** [실측: 변이 도중 죽인 회차에서 22MB — Go 빌드 캐시와 "
               "작업자별 소스 사본]. 프로젝트 안에는 아무것도 쓰지 않는다 [실측: 실행 전후 "
               "파일 목록 동일]. 만료·정리 정책: 없음"),
    copy_limitations=(),                   # 어댑터가 만드는 사본이 없다 (도구 사본은 workspace 에)
)
