"""C7 뮤테이션 — 러스트 어댑터 (cargo-mutants).

**실물로 돌려 확인한 어댑터다.** 이 기계에 러스트 툴체인(rustc 1.98.0 / cargo 1.98.0)이
있어 cargo-mutants 27.1.0 을 작은 크레이트에 여러 번 돌렸다. 아래 사실은 **직접 돌려
관측한 것**, cargo-mutants 27.1.0 태그의 **소스를 읽어** 확인한 것, 그리고 아직 확인하지
못한 것 셋으로 갈라 적는다. 확인 못 한 것은 그렇게 적었다 — 짐작으로 채운 파싱은
반드시 틀린다.

  - [실측] 결과 JSON 자리 = `<--output>/mutants.out/outcomes.json`. 모양은
    `{"outcomes":[{"scenario", "summary", "phase_results":[…]}], "total_mutants",
    "missed", "caught", "timeout", "unviable", "success", …}`.
  - [실측] `scenario` 는 기준 회차면 문자열 `"Baseline"`, 변이면
    `{"Mutant": {"name","package","file","function","span","replacement","genre"}}` 다.
    **기준 회차를 걸러내지 않으면 그 `Success` 가 변이 하나로 세어진다.**
  - [실측] `file` 은 **워크스페이스 최상위 기준 상대 경로**다 (가상 워크스페이스에서
    `crates/alpha/src/lib.rs` 로 나왔다). 소스의 `SourceFile.tree_relative_path`
    주석("Path of this source file relative to workspace")과 같다 [소스 확인].
  - [실측] `span` 의 줄·열은 **1부터 세는 문자(코드 포인트) 번호**이고 끝은 포함하지
    않는다. 이모지(비BMP)가 앞에 있는 줄에서도 파이썬 문자 슬라이스가 그대로 맞았다 —
    즉 UTF-16 이 아니다. 그래서 중립층의 `slice_lines`(Stryker 용 UTF-16 셈)를 쓰지
    않고 이 파일이 자기 슬라이스를 갖는다.
  - [소스 확인] 상태 낱말 여섯 (`src/outcome.rs` 의 `SummaryOutcome`):
    Success / CaughtMutant / MissedMutant / Unviable / Failure / Timeout.
    그중 **넷(Success·CaughtMutant·MissedMutant·Unviable)은 실물로 관측**했고
    Timeout·Failure 는 소스로만 봤다.
  - [소스 확인] 뜻은 같은 파일의 `summary()` 가 정한다: 변이 회차에서 빌드가 실패하면
    Unviable, 시간을 넘기면 Timeout, 테스트가 **실패**하면 CaughtMutant, 테스트가
    **성공**하면 MissedMutant, 그 밖은 Failure("should be rare or impossible").
  - [실측] 종료 코드: 잡히지 않은 변이가 있으면 2, 기준 테스트가 이미 실패하면 4
    (`cargo test failed in an unmutated tree, so no mutants were tested`),
    diff 파일을 못 읽으면 6, 잴 것이 없으면 0. **판정은 종료 코드가 아니라 리포트로
    한다** (R2 — 게이트는 무슨 일이 있어도 0 으로 끝난다).
  - [실측] `outcomes.json` 은 **회차 하나가 끝날 때마다 다시 쓰인다**
    (`OutputDir::add_scenario_outcome` → `write_lab_outcome` [소스 확인]).
    4초에 강제 종료했더니 그때까지의 7개가 든 온전한 JSON 이 남아 있었다 —
    예산을 넘겨 중단해도 본 만큼은 점수에 쓸 수 있다.
  - [실측] 오염 없음: 소스를 `$TMPDIR/cargo-mutants-<이름>-XXXX.tmp` 로 통째 복사해 그
    안에서 변이한다(`--in-place` 는 옵트인). 정상 종료 시 지운다. **강제 종료 시에는
    그 복사본이 남았다** (실측 1건).
  - [실측] `--output` 의 **부모** 디렉토리가 없으면 종료 코드 1 이다
    (`create output parent directory`). 대상 디렉토리 자체는 없으면 도구가 만든다 —
    `--output out4` 로 없던 자리를 줬더니 만들어 놓고 정상 실행했다.
    안 주면 프로젝트 안에 `mutants.out/` 이 쌓인다.
  - [실측] 직접 부를 때는 `cargo-mutants mutants …` 처럼 하위 명령 이름을 붙여야 한다
    (`cargo-mutants --list-files` 는 "unexpected argument" 로 거절당했다).
  - [미확인] Timeout / Failure 상태를 실물로 만들어 보지 못했다. 철자와 뜻은 소스에서
    옮겼다. 큰 저장소에서의 실행 시간, 여러 크레이트가 섞인 배치에서의 병렬 동작,
    윈도우에서의 글롭 이스케이프 규칙도 확인하지 못했다. 추적되지 않은 대상에 쓰는
    `--no-index -- /dev/null <경로>` 는 macOS 에서만 확인했다 — 윈도우에서 `os.devnull`
    ("nul") 을 git 이 어떻게 다루는지는 모른다.

## "덮은 테스트 없음" 을 구분하지 못한다 (이 어댑터의 핵심 한계)

cargo-mutants 에는 커버리지 단계가 없다. 변이마다 **테스트 스위트를 통째로 돌리고**,
그 결과가 성공이면 MissedMutant 다 (`mutant_missed` = 변이 + 마지막 단계가 Test +
그 단계가 성공 [소스 확인]). 그래서 "덮는 테스트가 아예 없는 코드" 와 "테스트는 도는데
확인문이 약한 코드" 가 같은 낱말 하나로 합쳐진다 — 실측으로 확인했다: 테스트가 전혀
없는 함수와, 호출만 하고 아무것도 확인하지 않는 테스트가 붙은 함수가 나란히 MISSED 로
나왔다.

**MissedMutant → Survived 로 보낸다.** 근거:
  1. 게이트 어휘의 Survived 정의는 "테스트가 돌았는데 못 잡았다" 이고, cargo-mutants 는
     실제로 스위트를 끝까지 돌린 뒤 그렇게 판정한다. 그 문장은 러스트에서 **참**이다.
     NoCoverage 의 정의는 "덮는 테스트가 없어 돌리지 않았다" 인데, 도구가 스위트를 돌린
     이상 그 문장은 **거짓**이 된다.
  2. 점수는 어느 쪽을 골라도 같다. Survived 와 NoCoverage 는 둘 다 분모에만 들어가고
     분자에는 없다 (`MUTATION_SURVIVING_STATUSES`). 즉 이 선택은 점수를 흔들지 않고
     사람이 읽는 분포와 목록 순서만 바꾼다 — 그래서 "참인 쪽" 을 고를 수 있었다.
  3. 대신 러스트 결과의 "덮은 테스트 없음" 칸은 **언제나 0** 이다. 그 0 을 "모든 코드가
     테스트에 덮여 있다" 로 읽으면 정반대의 결론이 된다. 그래서 점수 문장 바로 옆에
     한 줄로 그 사실을 싣는다 (`_RUST_BLIND_SPOT`) — 조용한 통과 금지(R4)의 요구다.

## 비용 (R1)

변이마다 사본 안에서 **다시 빌드하고** 스위트를 통째로 돈다. 실측: 함수 셋짜리
장난감 크레이트에서 변이 15개에 8.5초(변이당 0.56초)였고, 그중 빌드가 14회차에
2.61초, 테스트가 4.92초였다. 실제 크레이트에서는 빌드 한 번이 수 초라 이 값이
그대로 커진다. 그래서 **기본은 꺼짐**이다 (자바와 같은 이유, `default_enabled=False`).

## 증분을 쓰지 않는 이유 (실측)

`--iterate` 는 지난 회차에 잡힌 변이를 이번 회차에서 **빼 버린다**
(`load_previously_caught` → `remove_previously_caught` [소스 확인]). 같은 코드에 두 번
돌려 봤더니 1회차 18개(잡힘 5, 놓침 13, 27.8%)가 2회차에는 13개(잡힘 0, 놓침 13,
0.0%)가 됐다. 점수가 무너진다 — 잡힌 변이가 분자에서 사라지기 때문이다. 속도를 위해
점수를 거짓말하게 만드는 장치라 쓰지 않는다.

## 변경분 한정 (R3)

두 겹으로 좁힌다. `--file <경로>` 는 파일 단위, `--in-diff <diff 파일>` 은 바뀐 줄
단위다. `--in-diff` 는 **git ref 가 아니라 diff 파일**을 받으므로 [실측] 어댑터가
diff 를 떠서 임시 파일로 넘긴다.

**게이트가 리포트를 거르는 것은 파일 단위뿐이다.** `parse_cargo_mutants_report` 는
대상 목록에 없는 **파일**을 빼지만 줄 번호로는 거르지 않는다. 그래서 어긋남의 방향에
따라 결과가 다르다:

  - 도구가 게이트보다 **넓게** 보면 안전하다. 넘치는 파일은 게이트가 빼고, 같은 파일
    안에서 넘치는 줄은 느려질 뿐 점수를 흔들지 않는다 (그래서 글롭 특수문자가 든 경로가
    섞이면 파일 단위 좁히기를 통째로 포기한다 — 안 재는 것보다 넓게 재는 편이 낫다).
  - 도구가 게이트보다 **좁게** 보면 위험하다. 그 변이는 애초에 리포트에 실리지 않아
    게이트가 되살릴 방법이 없다. 조용히 빠지고, 대상이 그것뿐이면 회차 전체가
    "잴 것이 없었습니다" 로 나간다 — R3 와 R4 를 함께 깬다.

좁아지는 길이 셋이라 셋 다 막는다. 모두 실물로 재현한 뒤 고친 것이다:

  - [실측] `git diff <기준>` (두 점 비교) 은 **상대 브랜치가 바꾼 줄까지** 끌고 온다.
    서로 다른 함수를 고친 두 브랜치에서 변이 10개 중 5개가 이번 변경분 밖이었다.
    뼈대(`_raw_changed_lines`)와 같은 `--merge-base` 를 쓴다. 이 경우는 넓어지는
    쪽이라 점수만 부풀지만, 참고란의 "바뀐 줄 범위 안의 변이만" 이 거짓이 된다.
  - [실측] git 의 기본값(`core.quotepath=true`)은 비ASCII 경로를
    `"a/docs/\354\204\244..."` 로 이스케이프하고, cargo-mutants 의 diff 파서가
    그것을 거절한다 (`Failed to parse diff: invalid escaped character`, 종료 코드 6).
    한글 경로가 **하나만** 섞여도 러스트 측정이 통째로 사라진다. 뼈대의 `_git()` 과
    같이 `-c core.quotepath=false` 를 붙인다.
  - [실측] `git diff <기준>` 에는 **추적되지 않은 새 파일이 들어가지 않는다.** 게이트는
    그것을 변경분 네 갈래 중 하나로 세는데(`ls-files --others`), 도구 쪽에서 잘려 나가
    변이 8개짜리 회차가 "잴 것이 없었습니다" 로 나갔다. `git add` 한 번으로 판정이
    뒤집혔고 파일 내용은 한 글자도 안 바뀌었다. 그래서 게이트가 "파일 전체가 변경분"
    이라고 판정한 대상은 빈 파일과의 diff(`--no-index -- /dev/null <경로>`)를 만들어
    이어 붙인다.

`--file` 값은 globset 을 지난다 (`literal_separator(true)`, 백슬래시 이스케이프는
플랫폼마다 다르다) [소스 확인]. 그래서 글롭 특수문자가 든 경로는 `--file` 로 넘기지
않는다 — 잘못 이스케이프하면 다른 파일이 대상이 되거나 그 파일이 조용히 빠진다.

서브프로세스는 뼈대의 `gate._run` 만 쓴다. 형제 어댑터는 import 하지 않는다.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from scripts import code_gate as gate
from scripts.mutation import score as score_mod

MUTATION_RUST_SUFFIXES = frozenset({".rs"})

# "대상이 없다" 안내에 실을 대상 설명 (레지스트리가 읽는다).
MUTATION_TARGET_KO = "러스트 (Cargo 프로젝트만)"

# cargo-mutants 어휘 → 게이트 어휘. 여섯 낱말 모두 27.1.0 소스의 `SummaryOutcome` 에서
# 철자를 옮겼다 [소스 확인]. 뜻은 같은 파일 `summary()` 의 분기를 근거로 짝지었다.
#   CaughtMutant  변이 회차의 테스트가 실패했다                → Killed
#   MissedMutant  변이 회차의 테스트가 성공했다                → Survived (위 머리말 참조)
#   Unviable      변이가 빌드에 실패했다 (실측: Build 단계 Failure) → CompileError
#   Timeout       시간을 넘겼다                                → Timeout
#   Failure       테스트 밖의 정체불명 실패                    → RuntimeError
# `Success` 는 **일부러 넣지 않았다.** 실측에서 그 낱말은 기준(Baseline) 회차에만
# 나왔고, 기준 회차는 파싱이 먼저 걸러낸다. 변이 회차의 Success 는 소스가 스스로
# "should be rare or impossible" 이라고 적은 갈래라 뜻을 정하지 못했다 — 짐작으로
# 채우는 대신 원어 그대로 통과시켜 unknown 경로가 잡고 분모에서 빼게 둔다 (R4).
CARGO_MUTANTS_STATUS_TO_GATE = {
    "CaughtMutant": "Killed",
    "MissedMutant": "Survived",
    "Unviable": "CompileError",
    "Timeout": "Timeout",
    "Failure": "RuntimeError",
}

_INSTALL_HINT = "cargo-mutants 를 설치하십시오 (cargo install cargo-mutants)."

# 점수 옆에 반드시 붙는 한 줄. 러스트 결과의 "덮은 테스트 없음" 칸이 늘 0 이라,
# 말하지 않으면 그 0 이 "전부 덮여 있다" 로 읽힌다 (R4).
_RUST_BLIND_SPOT = ("러스트 도구는 두 종류의 살아남음을 구분하지 못합니다 — 덮는 테스트가 "
                    "아예 없는 코드와 확인문이 약한 코드가 모두 '살아남음' 으로 세어지고, "
                    "'덮은 테스트 없음' 칸은 언제나 0 입니다.")

# 실행 전에 남기는 참고. 실패한 회차에서도 남아야 하는 사실들이다.
_RUST_COST_NOTE = ("러스트 뮤테이션은 변이마다 사본 안에서 다시 빌드하고 테스트 스위트를 "
                   "통째로 돕니다 (실측: 장난감 크레이트에서 변이당 0.56초). 실제 크레이트에서는 "
                   "빌드 시간만큼 더 듭니다.")

# 변이 대상에서 빼는 자리 — 통합 테스트·벤치·예제·빌드 산출물.
# (`#[cfg(test)] mod tests` 안의 단위 테스트는 도구가 알아서 변이하지 않는다 — 실측:
#  테스트 함수 둘이 든 파일에서 변이가 하나도 나오지 않았다.)
_RUST_TEST_DIRS = frozenset({"tests", "benches", "examples"})
_RUST_SKIP_DIRS = frozenset({"target"})
# 위 둘을 합친 것 — 검사는 한 번에 한다 (같은 판정이라 두 번 훑을 이유가 없다).
_RUST_SKIP_PARENT_DIRS = _RUST_TEST_DIRS | _RUST_SKIP_DIRS
# 빌드 스크립트는 테스트가 도는 코드가 아니다 — 변이시켜도 잡힐 리가 없어 점수만 깎는다.
_RUST_SKIP_NAMES = frozenset({"build.rs"})

# `--file` 로 넘길 수 없는 글자. globset 이 이것들을 패턴으로 읽는다 [소스 확인].
_GLOB_META = frozenset("*?[]{}!\\")

# 사람용 표는 항목 하나가 한 줄이라는 전제 위에 있다. 함수 몸통 전체가 바뀌는 변이는
# 원본 자리가 수백 글자일 수 있어 여기서 자른다.
_ORIGINAL_MAX = 160

# 줄 단위 좁히기를 못 쓴 사유. 못 좁히는 것은 느려질 뿐이라 회차를 죽이지 않는다.
_DIFF_NO_GIT = "git diff 를 뜨지 못해 바뀐 줄 단위 좁히기는 쓰지 않았습니다."
_DIFF_EMPTY = "git diff 가 비어 있어 바뀐 줄 단위 좁히기는 쓰지 않았습니다."
_DIFF_UNWRITABLE = "diff 파일을 쓰지 못해 바뀐 줄 단위 좁히기는 쓰지 않았습니다."

# 리포트 자리 [실측].
_RUST_REPORT_TAIL = ("mutants.out", "outcomes.json")

# 실패 원문에서 알아볼 수 있는 사유 [실측 / 소스 확인].
_RUST_FAILURE_CAUSES = (
    ("cargo test failed in an unmutated tree",
     "변이를 넣기 전의 테스트가 이미 실패합니다. 먼저 테스트를 통과시키십시오 "
     "(사본에는 기본적으로 .git 이 들어가지 않아, git 에 기대는 테스트가 여기서 깨집니다)."),
    ("Failed to open diff file",
     "변경분 diff 파일을 열지 못했습니다."),
    ("Failed to read diff file",
     "변경분 diff 파일을 읽지 못했습니다."),
    ("does not match the source",
     "넘긴 diff 의 내용이 현재 소스와 달라 도구가 거절했습니다."),
    ("Failed to parse diff",
     "넘긴 변경분 diff 를 도구가 해석하지 못했습니다."),
    ("No such file or directory",
     "지정한 자리의 상위 디렉토리를 찾지 못했습니다."),
)


def _gate_status(word):
    """도구가 쓴 낱말을 게이트 어휘로. 표에 없으면 원어 그대로 (unknown 경로)."""
    return CARGO_MUTANTS_STATUS_TO_GATE.get(word, word)


def _rust_in_skipped_dir(path: Path) -> bool:
    """경로 중간에 통합 테스트·벤치·예제·빌드 산출물 디렉토리가 끼어 있는가."""
    return any(part.lower() in _RUST_SKIP_PARENT_DIRS for part in path.parts[:-1])


def _rust_skipped(repo_root: Path, rel: str) -> bool:
    """대상에서 빼는가. 통합 테스트·벤치·예제·빌드 산출물·빌드 스크립트·삭제된 파일이면 뺀다."""
    path = Path(rel)
    return (_rust_in_skipped_dir(path)
            or path.name.lower() in _RUST_SKIP_NAMES
            or not (repo_root / rel).is_file())


def _rust_targets(repo_root: Path, files) -> tuple:
    """(대상, 뺀 것). 뺀 것은 사유와 함께 호출자가 리포트에 남긴다 (R4)."""
    targets: list = []
    dropped: list = []
    for rel in files:
        (dropped if _rust_skipped(repo_root, rel) else targets).append(rel)
    return tuple(targets), tuple(dropped)


def _glob_safe(rel: str) -> bool:
    """이 경로를 `--file` 값으로 그대로 넘겨도 되는가.

    globset 은 값을 패턴으로 읽는다. 특수문자가 들어 있으면 다른 파일이 대상이 되거나
    이 파일이 조용히 빠진다. 이스케이프 규칙이 플랫폼마다 달라 [소스 확인] escaping 에
    기대지 않고, 안전한 것만 넘긴다.
    """
    return not (_GLOB_META & set(rel))


# ---------------------------------------------------------------------------
# 리포트 읽기 — 서브프로세스 없이 검증되는 순수 함수들
# ---------------------------------------------------------------------------

def _rust_mutant(entry) -> dict | None:
    """회차 하나가 가리키는 변이. 기준(Baseline) 회차면 None.

    기준 회차의 `scenario` 는 문자열 `"Baseline"` 이고 그 `summary` 는 Success 또는
    Failure 다 [실측]. 걸러내지 않으면 그 결과가 변이 하나로 세어져 점수가 흔들린다.
    """
    scenario = entry.get("scenario") if isinstance(entry, dict) else None
    if not isinstance(scenario, dict):
        return None
    mutant = scenario.get("Mutant")
    return mutant if isinstance(mutant, dict) else None


def _rust_baseline_summary(report) -> str | None:
    """기준 회차의 결과 낱말. 기준 회차가 없으면 None."""
    for entry in _rust_entries(report):
        if isinstance(entry, dict) and _rust_mutant(entry) is None:
            summary = entry.get("summary")
            if isinstance(summary, str):
                return summary
    return None


def _rust_entries(report) -> list:
    """리포트의 회차 목록. 모양이 어긋나면 빈 목록이다."""
    outcomes = report.get("outcomes") if isinstance(report, dict) else None
    return [e for e in (outcomes or []) if isinstance(e, dict)]


def _rust_span_point(point, key: str):
    """span 의 한 점에서 줄 또는 열 번호. 없거나 숫자가 아니면 None."""
    if not isinstance(point, dict):
        return None
    value = point.get(key)
    return value if isinstance(value, int) else None


def _rust_slice(lines, span) -> str:
    """변이가 앉은 원본 텍스트. 자리를 벗어나거나 모양이 어긋나면 빈 문자열.

    줄·열은 1부터 세는 **문자(코드 포인트)** 번호이고 끝은 포함하지 않는다 [실측].
    중립층의 `slice_lines` 는 Stryker 의 UTF-16 셈이라 여기 쓰면 이모지가 든 줄에서
    자리가 밀린다 — 그래서 이 파일이 자기 슬라이스를 갖는다.
    """
    if not isinstance(span, dict):
        return ""
    start, end = span.get("start"), span.get("end")
    s_line, s_col = _rust_span_point(start, "line"), _rust_span_point(start, "column")
    e_line, e_col = _rust_span_point(end, "line"), _rust_span_point(end, "column")
    if None in (s_line, s_col, e_line, e_col):
        return ""
    if min(s_col, e_col) < 1 or not 1 <= s_line <= e_line <= len(lines):
        return ""
    if s_line == e_line:
        picked = lines[s_line - 1][s_col - 1:e_col - 1]
    else:
        picked = "\n".join([lines[s_line - 1][s_col - 1:],
                            *lines[s_line:e_line - 1],
                            lines[e_line - 1][:e_col - 1]])
    return picked[:_ORIGINAL_MAX]


def _rust_sources(repo_root: Path, targets) -> dict:
    """대상 파일의 줄 목록. 원본 자리를 보여 주려면 파일을 직접 읽어야 한다.

    리포트에는 바뀐 것(replacement)만 있고 원본 텍스트를 담은 칸이 없다 [실측].
    """
    sources: dict = {}
    for rel in targets:
        try:
            sources[rel] = (repo_root / rel).read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
    return sources


def _rust_report_path(repo_root: Path, raw: str, targets) -> str | None:
    """리포트의 파일 이름을 저장소 상대 경로로. 못 맞추면 None.

    `file` 은 워크스페이스 최상위 기준이다 [실측]. 이 어댑터는 저장소 최상위에
    Cargo.toml 이 있을 때만 도므로 대개 그대로 맞는다. 그래도 두 단계를 둔다.
      1) 뼈대의 경로 정규화를 지난다 — 저장소 안의 경로면 여기서 끝난다
      2) 그래도 이번 대상에 없으면, 대상 목록 중 **접미사가 일치하는 것이 하나뿐일 때만**
         그것으로 본다. 둘 이상이면 맞추지 않는다 — 잘못 맞추면 다른 파일의 점수가 된다
    맞추지 못한 변이는 세지 않고, 그 이름을 참고에 남긴다 (R4).
    """
    rel = gate._rel_to_repo(Path(repo_root), raw)
    if rel in targets:
        return rel
    tail = raw.replace("\\", "/")
    matched = [t for t in targets if _path_tail_matches(tail, t)]
    return matched[0] if len(matched) == 1 else None


def _path_tail_matches(left: str, right: str) -> bool:
    """둘 중 하나가 다른 하나의 경로 접미사인가. 경로 구분자 경계에서만 맞춘다.

    구분자를 보지 않으면 `pkg/xa.rs` 가 `a.rs` 에 맞아 버린다.
    """
    return left == right or left.endswith("/" + right) or right.endswith("/" + left)


def _rust_record(rel: str, mutant: dict, summary, lines) -> dict:
    """변이 하나를 게이트 기록으로.

    `tests` 는 없다 — cargo-mutants 는 어느 테스트가 이 변이를 덮었는지 주지 않는다
    (애초에 커버리지를 재지 않는다). 없는 것을 지어내지 않고 비운다. 그러면 표가
    "도구가 덮은 테스트를 알려 주지 않습니다" 로 적어 준다 — "덮은 테스트 없음" 과
    다른 문장이다 (선언부의 `tests: absent` 와 짝이다).
    변이 종류는 `genre` 를 쓴다 (FnValue / BinaryOperator 같은 값) [실측].
    """
    span = mutant.get("span")
    start = span.get("start") if isinstance(span, dict) else None
    return {
        "file": rel,
        "line": _rust_span_point(start, "line"),
        "column": _rust_span_point(start, "column"),
        "mutator": mutant.get("genre"),
        "original": _rust_slice(lines, span),
        "replacement": mutant.get("replacement") or "",
        "status": _gate_status(summary),
        "tests": None,
    }


def _rust_report_file_names(report) -> list:
    """리포트에 실린 변이의 파일 이름 원문. 기준 회차는 파일이 없어 저절로 빠진다."""
    names: list = []
    for entry in _rust_entries(report):
        mutant = _rust_mutant(entry)
        raw = mutant.get("file") if mutant else None
        if isinstance(raw, str) and raw:
            names.append(raw)
    return names


def unmatched_report_files(report: dict, repo_root: Path, targets) -> list:
    """리포트에 있는데 이번 대상 어디에도 못 맞춘 파일 이름 — 서브프로세스 없이 검증된다.

    하나도 못 맞추면 요약이 통째로 비어, "변이가 하나도 만들어지지 않았습니다" 라는
    정상 종료 문장이 나간다. 살아남은 변이가 있었는데도 그렇다. 그래서 못 맞춘 이름을
    따로 세어 참고에 남긴다 (R4).
    """
    return sorted({name for name in _rust_report_file_names(report)
                   if _rust_report_path(repo_root, name, targets) is None})


def _rust_entry_path(entry, repo_root: Path, targets) -> str | None:
    """회차 하나가 가리키는 저장소 상대 경로. 기준 회차이거나 못 맞추면 None."""
    mutant = _rust_mutant(entry)
    raw = mutant.get("file") if mutant else None
    if not isinstance(raw, str) or not raw:
        return None
    return _rust_report_path(Path(repo_root), raw, targets)


def _rust_sort_key(record: dict) -> tuple:
    """살아남은 변이 목록의 고정 순서. 줄·열이 비어 있어도 정렬이 터지지 않게 0 으로 본다."""
    return (record["file"], record["line"] or 0, record["column"] or 0)


def parse_cargo_mutants_report(report: dict, repo_root: Path, targets) -> dict:
    """cargo-mutants JSON 을 게이트 결과로 — 서브프로세스 없이 검증되는 순수 함수.

    기준(Baseline) 회차를 걸러내고, `targets` 밖의 파일도 세지 않는다. `--file` 과
    `--in-diff` 를 줘도 도구의 대상 판정이 게이트의 변경분과 어긋날 수 있어, 점수의
    범위는 게이트가 정한다 (R3).
    """
    entries = _rust_entries(report)
    if not entries:
        return score_mod.summarize_mutants([])
    sources = _rust_sources(Path(repo_root), targets)
    records: list = []
    for entry in entries:
        rel = _rust_entry_path(entry, Path(repo_root), targets)
        if rel is None:
            continue                      # 기준 회차이거나 이번 대상 밖이다
        records.append(_rust_record(rel, _rust_mutant(entry), entry.get("summary"),
                                    sources.get(rel) or []))
    records.sort(key=_rust_sort_key)
    return score_mod.summarize_mutants(records)


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------

def _rust_preconditions(ctx: gate.GateContext) -> dict | None:
    """러스트 경로만의 사유. 있으면 그 결과를, 없으면 None (R4).

    cargo 자체의 유무는 따로 묻지 않는다. cargo-mutants 가 안에서 `cargo test` 를
    부르므로 없으면 실행이 실패하고, 그 출력이 사유에 그대로 실린다.
    """
    configured = ctx.config.mutation_tool(RUST_ADAPTER.language)
    if configured != RUST_ADAPTER.tool:
        return gate._skip(
            f"설정의 {RUST_ADAPTER.config_key} 값 '{configured}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported rust mutation tool: {configured}",
        )
    tool = gate._tool(ctx, "cargo-mutants")
    if not tool["available"]:
        # 뼈대의 도구 표에는 설치 문구가 없다 (PATH 조회만 한다). 어댑터가 자기 것을 낸다.
        return gate._skip("cargo-mutants 가 설치돼 있지 않습니다.", "cargo-mutants missing",
                          tool["install_hint"] or _INSTALL_HINT)
    if not (ctx.repo_root / "Cargo.toml").is_file():
        return gate._skip(
            "저장소 최상위에 Cargo.toml 이 없어 러스트 뮤테이션을 재지 않았습니다 "
            "(cargo-mutants 는 Cargo 워크스페이스 안에서만 돕니다).",
            "no Cargo.toml at repo root")
    return None


def _rust_scope(ctx: gate.GateContext, rs_files) -> tuple:
    """변이시킬 파일 목록과, 남는 것이 없을 때의 건너뜀 결과."""
    targets, dropped = _rust_targets(ctx.repo_root, rs_files)
    if dropped:
        ctx.notes.append(
            f"러스트 뮤테이션 대상에서 통합 테스트·벤치·예제·빌드 산출물·빌드 스크립트·"
            f"삭제된 파일 {len(dropped)}개를 뺐습니다: " + score_mod._sample_list(list(dropped)))
    if not targets:
        return (), gate._skip(
            f"변경된 러스트 파일 {len(rs_files)}개가 모두 변이 대상이 아닙니다 "
            "(통합 테스트·벤치·예제·빌드 산출물·빌드 스크립트·삭제된 파일).",
            "no mutable rust targets")
    return targets, None


def _rust_diff_base(ctx: gate.GateContext) -> str:
    """비교 기준 ref. 없거나 빈 트리면 빈 문자열 — 그러면 줄 단위 좁히기를 안 쓴다."""
    base = getattr(ctx.change, "base", "") or ""
    return "" if base == gate.EMPTY_TREE else base


def _rust_git_diff(ctx: gate.GateContext, args, ok_codes=(0,)) -> tuple:
    """(diff 원문, git 을 부르지 못했는가).

    `core.quotepath=false` 를 반드시 붙인다. git 의 기본값은 비ASCII 경로를
    `"a/docs/\\354\\204\\244..."` 로 이스케이프해 내보내고, cargo-mutants 의 diff
    파서는 그것을 거절한다 [실측: `Failed to parse diff: invalid escaped character`,
    종료 코드 6]. 한글 경로가 **하나만** 섞여도 러스트 측정이 통째로 사라진다.
    뼈대의 `_git()` 이 같은 이유로 같은 옵션을 붙인다 — 여기만 맨 `git diff` 를 쓰면
    두 곳의 동작이 갈린다.

    git 이 아예 없는 기계에서도 죽지 않아야 한다 — 여기서 터지면 항목 하나가 아니라
    게이트가 통째로 넘어간다 (R2).
    """
    try:
        proc = gate._run(["git", "-c", "core.quotepath=false", "diff", *args],
                         cwd=ctx.repo_root, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "", True
    return ((proc.stdout or "") if proc.returncode in ok_codes else ""), False


def _rust_tracked_diff(ctx: gate.GateContext, base: str) -> tuple:
    """(추적된 파일의 변경분, git 을 부르지 못했는가).

    게이트의 변경분 판정(`_raw_changed_lines`)과 **같은 기준**으로 뜬다. 두 점 비교
    (`git diff <기준>`)만 쓰면 분기한 브랜치에서 상대 브랜치가 바꾼 줄까지 변이 대상이
    된다 — 실측에서 분모의 절반이 이번 변경분 밖이었다 (R3 위반). 두 겹으로 시도하는
    까닭도 뼈대와 같다: `--merge-base` 는 기준이 커밋일 때만 되고, 그 밖에서는 두 점
    비교로 내려간다.
    """
    text, no_git = _rust_git_diff(ctx, ["--merge-base", base])
    if no_git or text:
        return text, no_git
    return _rust_git_diff(ctx, [base])


def _rust_whole_file_targets(ctx: gate.GateContext, targets) -> tuple:
    """변경분이 "파일 전체" 인 대상. 게이트가 그렇게 판정한 것만 고른다.

    `ctx.change.lines` 의 값이 None 이면 파일 전체가 변경분이라는 뜻이다 (추적되지
    않은 새 파일). 변경 범위의 단일 출처는 그대로 게이트다 — 여기서 다시 판정하지 않는다.
    """
    lines = getattr(ctx.change, "lines", None) or {}
    return tuple(rel for rel in targets if rel in lines and lines[rel] is None)


def _rust_untracked_diff(ctx: gate.GateContext, targets) -> str:
    """추적되지 않은 대상을 위한 합성 diff.

    `git diff <기준>` 에는 추적되지 않은 파일이 들어가지 않는다. 그대로 `--in-diff` 에
    넘기면 게이트가 대상으로 잡은 새 파일이 도구 쪽에서 통째로 잘려 나간다 — 변이가
    8개 있는 회차가 "잴 것이 없었습니다" 로 나갔다 [실측]. R3 의 변경분 판정과
    R4 의 조용한 통과 금지를 동시에 깨는 자리라, 빈 파일과의 diff 를 만들어 이어 붙인다.
    `--no-index` 는 내용이 다르면 종료 코드 1 이다 — 그것이 정상이다.
    """
    parts = []
    for rel in _rust_whole_file_targets(ctx, targets):
        text, _ = _rust_git_diff(ctx, ["--no-index", "--", os.devnull, rel], ok_codes=(0, 1))
        parts.append(text)
    return "".join(parts)


def _rust_write_diff(work: Path, text: str) -> tuple:
    """diff 원문을 파일로 남긴다. 못 쓰면 좁히기를 포기한다 (느려질 뿐이다)."""
    path = work / "changed.diff"
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        return None, _DIFF_UNWRITABLE
    return path, ""


def _rust_diff_file(ctx: gate.GateContext, work: Path, targets=()) -> tuple:
    """(diff 파일 경로 또는 None, 남길 안내 한 줄 또는 빈 문자열).

    `--in-diff` 는 git ref 가 아니라 **diff 파일**을 받는다 [실측]. 그래서 여기서
    diff 를 떠서 파일로 남긴다. 비교 기준이 없거나 git 이 없거나 diff 가 비어 있으면
    그냥 안 쓴다 — 못 좁히는 것은 느려질 뿐이고, 점수는 어차피 게이트가 대상 목록으로
    한 번 더 거른다 (R3).

    반대 방향은 그렇지 않다. diff 가 대상보다 **좁으면** 그 변이는 애초에 리포트에
    실리지 않아 게이트가 되살릴 수 없다. 그래서 추적되지 않은 대상은 합성 diff 로
    직접 채운다.
    """
    base = _rust_diff_base(ctx)
    if not base:
        return None, ""
    text, no_git = _rust_tracked_diff(ctx, base)
    if no_git:
        return None, _DIFF_NO_GIT
    text += _rust_untracked_diff(ctx, targets)
    if not text.strip():
        return None, _DIFF_EMPTY
    return _rust_write_diff(work, text)


def _rust_file_args(targets) -> tuple:
    """(`--file` 로 넘길 인자, 못 넘긴 경로).

    글롭 특수문자가 하나라도 있는 대상이 섞이면 **파일 단위 좁히기를 통째로 포기**한다.
    그 하나만 빼면 그 파일이 아예 안 재어지는데, 안 재는 것보다 넓게 재는 편이 낫다
    (점수 범위는 어차피 게이트가 대상 목록으로 거른다).
    """
    unsafe = [rel for rel in targets if not _glob_safe(rel)]
    if unsafe:
        return (), tuple(unsafe)
    args: list = []
    for rel in targets:
        args += ["--file", rel]
    return tuple(args), ()


def _rust_command(ctx: gate.GateContext, out_dir: Path, targets, diff_path) -> tuple:
    """(실행할 명령, 결과가 나온 뒤에 남길 안내).

    임계값을 0 으로 만드는 옵션은 없다 — cargo-mutants 는 잡히지 않은 변이가 있으면
    무조건 종료 코드 2 다 [실측]. 그래서 판정은 종료 코드가 아니라 리포트 유무로 한다
    (R2). `mutants` 하위 명령 이름을 반드시 붙인다 [실측].
    """
    cmd = [gate._tool(ctx, "cargo-mutants")["path"], "mutants",
           "--output", str(out_dir), "--no-times"]
    notes = [_RUST_COST_NOTE, _RUST_BLIND_SPOT]

    file_args, unsafe = _rust_file_args(targets)
    cmd += list(file_args)
    if unsafe:
        notes.append(
            f"경로에 글롭 특수문자가 들어 있어 파일 단위 좁히기를 쓰지 않습니다 "
            f"({score_mod._sample_list(list(unsafe))}). 프로젝트 전체를 변이시키고 점수만 "
            "이번 변경분으로 거릅니다.")
    if diff_path is not None:
        cmd += ["--in-diff", str(diff_path)]
        notes.append(
            f"러스트 뮤테이션은 --in-diff 로 이번에 바뀐 줄 범위 안의 변이만 돌립니다 "
            f"(대상 파일 {len(targets)}개). 같은 파일의 바뀌지 않은 줄은 재지 않습니다.")
    elif file_args:
        notes.append(
            f"변경된 러스트 파일 {len(targets)}개를 파일 단위로 변이시킵니다. "
            "그 파일 안에서 이번에 바뀌지 않은 줄도 함께 변이됩니다.")
    return cmd, notes


def _rust_tail(proc) -> str:
    """사람용 표에 실을 실패 원문 꼬리. 줄바꿈과 연속 공백을 한 칸으로 접는다.

    표는 항목 하나가 한 줄이라는 전제 위에 있다. 여러 줄인 원문을 그대로 실으면 그
    전제가 깨지고 JSON 의 human_reason 에도 개행이 들어간다.
    """
    detail = ((proc.stdout or "") + (proc.stderr or "")) if proc is not None else ""
    return " ".join(detail.split())[-500:]


def _rust_failure_cause(detail: str) -> str:
    """실패 원문에서 알아볼 수 있는 사유. 못 알아보면 빈 문자열.

    원문만 던지면 사용자가 무엇을 해야 하는지 알 수 없다. 알아본 것만 말하고,
    못 알아본 것을 지어내지 않는다.
    """
    for marker, sentence in _RUST_FAILURE_CAUSES:
        if marker in detail:
            return f" {sentence}"
    return ""


def _rust_no_report(proc, elapsed: float) -> dict:
    """리포트가 없을 때. 잴 것이 없었던 회차와 실패한 회차를 가른다.

    변경분 diff 안에 변이가 하나도 없으면 도구가 리포트를 아예 쓰지 않고 0 으로 끝난다
    [실측]. 그것을 오류로 내면 거짓 경보다. 반대로 비-0 으로 끝났는데 조용히 넘어가면
    R4 가 금지한 조용한 통과다.
    """
    code = proc.returncode if proc is not None else None
    if code == 0:
        return gate._skip(
            f"이번 변경분 안에 러스트 변이가 하나도 없어 잴 것이 없었습니다. 실행 {elapsed:.1f}초",
            "no rust mutants in change")
    detail = _rust_tail(proc)
    return {
        "status": "error",
        "reason": f"cargo-mutants produced no report (exit {code if code is not None else '?'})",
        "human_reason": (f"러스트 뮤테이션 리포트가 나오지 않았습니다 "
                         f"(종료 코드 {code if code is not None else '?'})."
                         f"{_rust_failure_cause(detail)} 실행 {elapsed:.1f}초  {detail}"),
        "findings": [],
    }


def _rust_baseline_failed(proc, elapsed: float) -> dict:
    """기준 회차가 실패했을 때 — 리포트는 있지만 변이는 하나도 돌지 않았다 [실측].

    이것을 "변이가 하나도 만들어지지 않았습니다" 로 내면 통과처럼 읽힌다. 실제로는
    프로젝트 테스트가 이미 빨간 상태라, 사용자가 할 일이 전혀 다르다 (R4).

    원인을 하나로 단정하지 않는다. 사본에 `.git` 이 없어 깨지는 경우도 있지만 [실측],
    그냥 빌드가 깨진 경우도 똑같이 여기로 온다 [실측: 타입 오류를 넣은 크레이트].
    단정하면 사용자가 있지도 않은 원인을 찾으러 간다. 그래서 형제 분기(`_rust_no_report`)
    와 같이 도구 원문 꼬리를 그대로 싣는다 — 실제 원인은 거기에 적혀 있다.
    """
    return {
        "status": "error",
        "reason": "cargo-mutants baseline failed",
        "human_reason": ("변이를 넣기 전의 러스트 테스트가 이미 실패해 변이를 하나도 돌리지 "
                         "못했습니다. 먼저 테스트를 통과시키십시오. 흔한 원인은 빌드 실패와, "
                         "도구가 만드는 사본에 기본적으로 .git 이 들어가지 않아 git 에 기대는 "
                         f"테스트가 깨지는 것입니다. 실행 {elapsed:.1f}초  {_rust_tail(proc)}"),
        "findings": [],
    }


def _rust_timed_out(summary: dict, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단됐을 때 — 본 만큼만 낸다.

    cargo-mutants 는 회차마다 리포트를 다시 쓰므로 중단돼도 그때까지의 결과가 남는다
    [실측]. gremlins 와 다른 점이다.
    """
    total = summary["total"] if summary else 0
    tail = score_mod._mutation_partial_gaps(summary, targets) if summary else ""
    return {
        "status": "timeout",
        "reason": f"rust mutation timed out after {budget}s ({total} mutants seen)",
        "human_reason": (f"{budget}초 예산을 넘겨 중단했습니다. 대상 파일 {len(targets)}개 중 "
                         f"변이 {total}개까지만 결과에 남았습니다. {_RUST_BLIND_SPOT} "
                         "예산을 늘리거나(.code-gate.json 의 mutation.timeout_seconds) 대상을 "
                         f"좁히십시오.{tail}"),
        "findings": summary["survivors"] if summary else [],
    }


def _rust_with_blind_spot(outcome: dict) -> dict:
    """점수 문장 바로 옆에 한계 한 줄을 싣는다 (R4).

    판정(status)은 건드리지 않는다. 선언부가 허용하는 것은 "사유 문장이 더 정확해지는
    것" 뿐이고, 여기서 붙이는 문장은 러스트 결과의 '덮은 테스트 없음 0' 이 무슨 뜻인지를
    말한다 — 없으면 그 0 이 "전부 덮여 있다" 로 읽힌다.
    """
    human = outcome.get("human_reason") or ""
    outcome["human_reason"] = f"{human}  {_RUST_BLIND_SPOT}".strip()
    return outcome


def _rust_note_unmatched(ctx: gate.GateContext, payload, targets) -> None:
    """리포트에 있는데 이번 대상에 못 맞춘 파일을 참고에 남긴다 (R4)."""
    unmatched = unmatched_report_files(payload, ctx.repo_root, targets) if payload else []
    if unmatched:
        ctx.notes.append(
            f"러스트 리포트의 파일 이름 {len(unmatched)}개를 이번 대상에 맞추지 못해 그 변이는 "
            f"세지 않았습니다: {score_mod._sample_list(unmatched)}")


def _rust_run(ctx: gate.GateContext, out_dir: Path, cmd: list, targets, scope_notes: list) -> tuple:
    """실행하고 (결과, 요약) 을 만든다. 걸린 시간은 리포트를 다 읽은 뒤에 잰다."""
    budget = score_mod._mutation_budget(ctx)
    # 범위 안내는 실행 **전에** 남긴다. 완주 분기에만 두면 중단·리포트 없음 회차에서
    # 비용 경고와 한계 안내가 통째로 사라진다 — 그 두 문장이 가장 필요한 순간이 바로
    # 실패한 회차다 (R4). 형제 어댑터가 같은 이유로 같은 자리에 둔다.
    ctx.notes.extend(scope_notes)
    started = time.perf_counter()
    proc = None
    timed_out = False
    try:
        proc = gate._run(cmd, cwd=ctx.repo_root, timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out = True

    payload = gate._read_json_object(out_dir.joinpath(*_RUST_REPORT_TAIL))
    summary = parse_cargo_mutants_report(payload, ctx.repo_root, set(targets)) if payload else None
    elapsed = time.perf_counter() - started
    _rust_note_unmatched(ctx, payload, set(targets))
    if timed_out:
        return _rust_timed_out(summary, targets, elapsed, budget), summary
    if summary is None:
        return _rust_no_report(proc, elapsed), None
    return _rust_completed(ctx, payload, summary, targets, elapsed, proc)


def _rust_completed(ctx: gate.GateContext, payload, summary: dict, targets,
                    elapsed: float, proc=None) -> tuple:
    """완주한 회차의 (결과, 요약) — 기준 회차 실패와 정상 채점을 가른다.

    기준 회차가 실패하면 리포트는 나오지만 변이가 하나도 돌지 않는다 [실측]. 그것을
    "변이가 하나도 만들어지지 않았습니다" 로 내면 통과처럼 읽힌다 (R4).
    그 회차의 요약은 **비운다**. 빈 요약을 그대로 넘기면 합치는 층이 러스트를 "잰
    언어" 로 세어, 여러 언어를 잰 회차에서 "러스트는 재지 못했습니다" 라는 문장이
    사라진다.
    """
    if summary["total"] == 0 and _rust_baseline_summary(payload) == "Failure":
        return _rust_baseline_failed(proc, elapsed), None
    return _rust_with_blind_spot(
        score_mod._mutation_outcome(ctx, summary, elapsed, targets)), summary


def _check_mutation_rust(ctx: gate.GateContext, rs_files) -> dict:
    """러스트 경로 하나를 끝까지. 반환은 언어 한 조각(part)이다."""
    outcome, summary = _run_mutation_rust(ctx, rs_files)
    return {"language": "rust", "label": "러스트", "outcome": outcome, "summary": summary}


def _run_mutation_rust(ctx: gate.GateContext, rs_files) -> tuple:
    blocked = _rust_preconditions(ctx)
    if blocked is not None:
        return blocked, None
    targets, blocked = _rust_scope(ctx, rs_files)
    if blocked is not None:
        return blocked, None

    work = (ctx.tmpdir / "mutation" / "rust")
    work.mkdir(parents=True, exist_ok=True)   # --output 의 부모가 없으면 종료 코드 1 이다
    work = work.resolve()
    diff_path, diff_note = _rust_diff_file(ctx, work, targets)
    cmd, scope_notes = _rust_command(ctx, work, targets, diff_path)
    if diff_note:
        scope_notes.append(diff_note)
    return _rust_run(ctx, work, cmd, targets, scope_notes)


def _mutation_changed_rust(ctx: gate.GateContext) -> list:
    """C7 이 볼 러스트 변경 파일. 변경분의 단일 출처는 그대로 ctx.change.files 다."""
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_RUST_SUFFIXES]


# ---------------------------------------------------------------------------
# 선언부 — 이 어댑터가 규격에 신고하는 사실 (계약 테스트가 동작과의 일치를 검사한다)
# ---------------------------------------------------------------------------

RUST_ADAPTER = score_mod.AdapterSpec(
    language="rust",
    label="러스트",
    tool="cargo-mutants",                  # 직접 부를 때는 `cargo-mutants mutants …` [실측]
    config_key="mutation.rust",
    # 변환표 = CARGO_MUTANTS_STATUS_TO_GATE. 철자는 27.1.0 소스의 `SummaryOutcome` 에서
    # 옮겼고 [소스 확인], 그중 넷은 실물로도 봤다. 비항등이라 적용을 지우면 계약 테스트가
    # 잡는다. `Success` 는 일부러 뺐다 — 표 밖 낱말은 원어 그대로 통과해 unknown 경로가
    # 잡고 분모에서 뺀다 (R4).
    status_map=CARGO_MUTANTS_STATUS_TO_GATE,
    measure_unit="expression",             # 한 줄에서 여러 변이가 나온다 [실측: `n > 100` 한 줄에 3개]
    skip_report=("보고하지 않는다. `skip_calls`(기본값 `with_capacity`) [소스 확인] 와 "
                 "`#[mutants::skip]` 로 빠진 자리는 리포트에 아예 실리지 않아, 무엇이 "
                 "빠졌는지 결과만 봐서는 알 수 없다 [미확인 — 빠진 목록을 내는 길을 찾지 못했다]"),
    # 증분은 있지만(`--iterate`) 쓰지 않는다. 지난 회차에 잡힌 변이를 이번 결과에서
    # 빼 버려 점수가 무너진다 — 실측으로 27.8% → 0.0% 가 됐다 (머리말 참조).
    incremental=False,
    incremental_triggers=(),
    target_syntax=("파일 단위는 `--file <경로>` (globset, `literal_separator(true)`), 줄 "
                   "단위는 `--in-diff <diff 파일>` — **git ref 가 아니라 diff 파일**이라 "
                   "어댑터가 diff 를 떠서 넘긴다 [실측]. 그 diff 는 뼈대와 같은 `--merge-base` "
                   "기준이고, `-c core.quotepath=false` 로 뜨며, 추적되지 않은 대상은 빈 "
                   "파일과의 `--no-index` diff 를 이어 붙인다 — 셋 다 빼면 도구가 게이트보다 "
                   "좁게 봐서 변이가 조용히 빠진다 [실측]. `--file` 값은 패턴으로 읽히고 "
                   "백슬래시 이스케이프가 플랫폼마다 달라, 글롭 특수문자가 든 경로가 섞이면 "
                   "파일 단위 좁히기를 통째로 포기한다 (좁게 재다 빠뜨리는 것보다 넓게 재는 "
                   "편이 낫다). 게이트가 리포트를 거르는 것은 **파일 단위뿐**이라, 넓어지는 "
                   "어긋남만 안전하다"),
    # tests 는 absent 다 — cargo-mutants 는 커버리지를 재지 않아 어느 테스트가 이 변이를
    # 덮었는지 줄 수가 없다. 그것이 이 어댑터의 핵심 한계이기도 하다 (머리말 참조).
    field_confidence={"line": "tool", "column": "tool", "mutator": "tool",
                      "tests": "absent"},
    requires=(),                           # 게이트에 러스트 테스트 항목이 없다
    workspace=("게이트 임시 디렉토리의 `--output` 아래에 리포트와 diff 파일(매 실행 삭제). "
               "`--output` 을 안 주면 프로젝트 안에 mutants.out/ 이 쌓이므로 반드시 준다. "
               "어댑터는 사본을 만들지 않는다 — 도구가 스스로 `$TMPDIR/cargo-mutants-*.tmp` "
               "로 소스를 복사하고 정상 종료 시 지운다 [실측]. **강제 종료 시에는 그 복사본이 "
               "남았다** [실측 1건]. 만료·정리 정책: 없음"),
    copy_limitations=(),                   # 어댑터가 만드는 사본이 없다 (도구 사본은 workspace 에)
    # 러스트도 자바처럼 기본이 꺼짐이다. cargo-mutants 는 커버리지 선별이 없어 변이마다
    # 사본 안에서 다시 빌드하고 테스트 스위트를 통째로 돈다. 장난감 크레이트에서도
    # 변이당 0.56초였고(실측), 실제 크레이트에서는 빌드 시간이 그대로 얹힌다.
    default_enabled=False,
    default_off_reason=("cargo-mutants 가 변이마다 다시 빌드하고 테스트 스위트를 통째로 돌아 "
                        "변경분이 작아도 빌드 시간만큼 듭니다"),
)
