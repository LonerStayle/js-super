"""C7 뮤테이션 — 언어 중립층: 게이트 어휘, 점수 공식, 공용 문장.

커버리지는 "실행된 줄"만 세므로, 확인문이 하나도 없는 테스트도 100% 로 보인다.
뮤테이션은 코드를 일부러 바꿔 놓고 테스트가 실패하는지 본다 — 테스트가 잡아내는지를
재는 항목이다. 0단계에서는 점수를 내기만 하고 아무것도 막지 않는다 (R2).

이 모듈은 어댑터(javascript / python)와 합치는 층(__init__)을 import 하지 않는다.
본문에 도구 이름이 없다 — 도구별 사실은 전부 어댑터 소유다. 점수는 어디서든
`mutation_score` 하나만 거친다 (D1).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 게이트 어휘 — 이 여덟 이름은 게이트 자신의 상태 어휘다 (1c 에서 소유권 이전).
#
# 철자가 Stryker 의 mutation-testing-elements 스키마와 같은 것은 역사적 우연이다.
# 정의는 도구와 무관하다:
#   Killed        테스트가 변이를 잡았다                      → 분자·분모
#   Timeout       변이가 테스트를 끝나지 않게 만들었다 — 잡은 것으로 센다 → 분자·분모
#   Survived      테스트가 돌았는데 못 잡았다                 → 분모
#   NoCoverage    덮는 테스트가 없어 돌리지 않았다 — 못 잡은 것으로 센다 → 분모
#   CompileError  변이가 실행 가능한 프로그램을 만들지 못했다  → 제외
#   RuntimeError  테스트 밖 기반 오류                         → 제외
#   Ignored       도구나 설정이 의도적으로 뺐다               → 제외
#   Pending       아직 돌지 않았다                            → 제외
#
# 각 어댑터는 자기 어휘 → 게이트 어휘 변환표를 선언부(AdapterSpec.status_map)에 신고한다.
# 변환표에 없는 상태는 원어 철자 그대로 통과한다 — unknown_mutant_statuses 가 잡아
# 분포와 참고 문장에 싣고 분모에서 뺀다. 이것이 의도된 경로다 (R4): 이름을 지우는 코드가
# 어디에도 없어, 모르는 상태가 조용히 사라지는 일은 구조적으로 없다.
# 어휘를 늘릴 권리는 어댑터에 없다 — 늘리는 순간 이미 튜닝된 다른 언어의 판정이 함께
# 흔들린다. 어휘 확장은 중립층 변경 + 실증 + 자체 테스트를 요구하는 별도 작업이다.
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


@dataclass(frozen=True)
class AdapterSpec:
    """어댑터 선언부 — 두 사례(Stryker / mutmut)에서 실제로 갈린 항목만 담는다.

    각 어댑터 모듈이 자기 인스턴스를 모듈 상수(`<언어>_ADAPTER`)로 둔다. 계약 테스트는
    그 이름 규칙으로 어댑터를 스스로 찾는다 — 목록에 손으로 등록하는 방식은 등록을
    잊은 어댑터가 검사 0건으로 통과했다 (실측). 선언부는 런타임 분기를 새로 만들지
    않는다 (동작 불변). 선언이 거짓이면 계약 테스트(test_mutation_contract.py)가 잡는다.

    선언부의 런타임 소비는 둘뿐이다 — 자바스크립트의 status_map(기록을 만들 때 지난다)과
    파이썬의 실패 각인(자기 무효화 축을 여기 문서화한다). 둘 다 판정을 바꾸지 않는다.

    동작 불변의 경계: 어댑터가 자기 한계(copy_limitations)를 신고해 사유 문장이 더
    정확한 것으로 **대체**되는 것은 허용한다. 참고 문장이 하나 붙는 것도 마찬가지다.
    바뀌면 안 되는 것은 판정(status)이다.
    """

    language: str                          # 네 칸 계약의 language 와 일치해야 한다
    label: str                             # 네 칸 계약의 label 과 일치해야 한다
    tool: str                              # 도구 이름 (선행 조건 검사의 근거)
    config_key: str                        # .code-gate.json 안의 자리
    status_map: dict                       # 자기 어휘 → 게이트 어휘. 값은 여덟 이름 안이어야 한다
    measure_unit: str                      # 도구가 실제로 훑는 단위 (expression / function)
    skip_report: str | None                # 훑지 않고 건너뛴 단위의 신고 방법. 없으면 None
    incremental: bool                      # 회차를 넘겨 결과를 재사용하는가
    incremental_triggers: tuple            # 무엇이 바뀌면 그 재사용을 버리는가. incremental 이면 비면 안 된다
    target_syntax: str                     # 대상 목록 표기 규칙과 이스케이프 책임 (어댑터 소유)
    # 기록 칸별 신뢰도. 값은 tool / reconstructed / absent, 단 tests 칸만 단위로 답한다
    # (per-mutant / per-function / absent) — 옛 별도 필드(tests_granularity)와 이 칸이
    # 같은 열을 두 번 설명해 서로 모순될 수 있었다.
    field_confidence: dict
    requires: tuple                        # 요구하는 선행 항목 (예: "C1:python"). 없으면 빈 튜플
    workspace: str                         # 작업 공간의 경로·수명. 만료·정리 정책 선언 자리 포함
    copy_limitations: tuple                # 사본 방식이 원본과 다르게 만드는 실행 조건. 사본이 없으면 빈 튜플


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


def _ko_topic(word: str) -> str:
    """한국어 조사 은/는 을 앞 글자 받침에 맞춘다. 한글이 아니면 '은'."""
    last = word[-1] if word else ""
    if "가" <= last <= "힣":
        return "은" if (ord(last) - 0xAC00) % 28 else "는"
    return "은"


def _sample_list(items, limit: int = 5) -> str:
    """목록을 앞 몇 개만 적고 나머지는 "외" 로 줄인다 — 안내문 세 군데가 같이 쓴다."""
    return ", ".join(items[:limit]) + (" 외" if len(items) > limit else "")


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
    """상태별 개수 한 줄. 게이트 어휘 밖의 이름은 지어내지 않고 모르는 상태로 적는다.

    도구가 낸 이름을 그대로 실으면 한국어 문장 안에 영어 상태 이름이 섞여 정상 항목처럼
    읽힌다. 이름은 그대로 두되(짐작으로 번역하지 않는다) 모르는 것임을 함께 적는다 (R4).
    """
    return " / ".join(
        f"{MUTANT_STATUS_KO[k]} {v}" if k in MUTANT_STATUS_KO else f"모르는 상태 '{k}' {v}"
        for k, v in sorted(counts.items()))


def _mutation_budget(ctx: gate.GateContext) -> int:
    """이 언어에 남은 시간(초). 예산은 **항목 하나의 것**이라 두 언어가 나눠 쓴다.

    언어마다 설정값을 통째로 잡으면 C7 하나가 설정값의 두 배까지 돈다 (실측: 2초 설정에
    항목 4.04초). 마감 시각이 없으면(단일 언어 경로를 직접 부른 경우) 설정값 전부를 준다.
    """
    total = ctx.config.mutation_timeout_seconds
    if ctx.mutation_deadline is None:
        return total
    # 남은 시간은 **올림**한다. 버림하던 때는 0.99초가 0 이 되어, 아직 쓸 시간이 있는데도
    # 그 언어가 통째로 "앞 언어가 예산을 다 썼다" 로 빠졌다. 남은 것이 진짜 없을 때만
    # 0 이어야 그 문장이 사실이 된다. 대신 항목 전체가 설정값을 1초 미만씩 넘길 수 있다 —
    # 언어 하나를 통째로 잃는 것보다 낫다.
    return max(0, math.ceil(ctx.mutation_deadline - time.perf_counter()))


def _mutation_missing_targets(summary: dict, targets) -> list:
    """대상으로 넘겼는데 결과에 한 줄도 없는 파일. 완주·중단 두 안내가 함께 쓴다."""
    measured = set(summary.get("files") or ())
    return [rel for rel in targets if rel not in measured]


def _missing_target_note(summary: dict, targets) -> str:
    """대상으로 넘겼는데 리포트에 한 줄도 없는 파일. 없으면 빈 문자열.

    경로가 글롭 패턴에 안 맞았거나 Stryker 가 그 확장자를 다루지 못한 경우다. 말하지
    않으면 남은 파일의 점수가 변경분 전체의 점수처럼 읽히고 그 옆에서 "통과" 가 나간다.
    """
    missing = _mutation_missing_targets(summary, targets)
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


def _mutation_partial_gaps(summary: dict, targets) -> str:
    """중단된 회차가 못 본 것 — 한 줄도 못 본 파일과 모르는 상태 (D4·R4).

    완주한 회차의 안내(_mutation_gaps)와 문장이 다르다. 중단된 회차에서 결과에 없는 파일은
    "변이가 만들어지지 않은" 것이 아니라 차례가 오기 전에 멈춘 것이다. 어느 쪽이든 그 파일이
    점수에 없다는 사실은 같아서, 말하지 않으면 남은 파일의 점수가 변경분 전체처럼 읽힌다.
    """
    missing = _mutation_missing_targets(summary, targets)
    notes = []
    if missing:
        notes.append(f"대상 파일 {len(missing)}개는 한 줄도 재지 못했습니다: {_sample_list(missing)}")
    unknown = _unknown_status_note(summary)
    if unknown:
        notes.append(unknown)
    return "".join(f"  {note}" for note in notes)


def _mutation_out_of_budget(language: str, label: str, budget: int) -> dict:
    """앞 언어가 예산을 다 썼을 때의 조각. 조용히 빠지지 않게 사유를 남긴다 (R4).

    어댑터(파이썬)와 합치는 층이 함께 부른다 — 어댑터가 합치는 층을 import 하면
    순환이 생겨, 이 함수는 중립층 소유다.
    """
    return {
        "language": language, "label": label, "summary": None,
        "outcome": gate._skip(f"앞 언어가 뮤테이션 예산({budget}초)을 다 써 {label}{_ko_topic(label)} 재지 못했습니다. "
                         "예산을 늘리거나(.code-gate.json 의 mutation.timeout_seconds) 한 언어씩 재십시오.",
                         f"mutation budget exhausted before {language}"),
    }

def _mutation_outcome(ctx: gate.GateContext, summary: dict, elapsed: float, targets) -> dict:
    """점수를 사람이 읽는 문장으로. 기준 미달이면 발견, 아니면 통과 — 어느 쪽이든 막지 않는다.

    머리말에서 "살아남음" 이라는 말을 쓰지 않는다. 그 수(Survived + NoCoverage)는 바로 뒤
    분포의 "살아남음"(Survived 만)과 달라, 한 문장 안에서 같은 낱말이 두 수를 가리켰다.
    """
    total = summary["total"]
    timing = _mutation_timing(elapsed, total, _mutation_executed(summary["counts"]))
    if total == 0:
        return gate._skip(
            f"변경된 대상 파일 {len(targets)}개에서 변이가 하나도 만들어지지 않았습니다. {timing}",
            "no mutants for changed files",
        )
    distribution = _mutation_distribution(summary["counts"])
    tail = _mutation_gaps(summary, targets)
    if summary["score"] is None:
        return gate._skip(
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


# 뼈대 import 는 정의가 모두 끝난 뒤에 한다. 뼈대 하단이 이 모듈의 상수
# (MUTANT_STATUS_KO)를 가져가는데, 이 import 가 파일 위에 있으면 어댑터를 단독으로
# 먼저 import 하는 순서에서 상수가 정의되기 전에 뼈대 실행이 끼어들어 순환이 터진다.
# 함수 본문의 gate.* 참조는 호출 시점 조회라 이 위치로 충분하다.
from scripts import code_gate as gate  # noqa: E402
