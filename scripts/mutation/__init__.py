"""C7 뮤테이션 — 합치는 층.

언어 어댑터가 낸 네 칸 사전 `{"language", "label", "summary", "outcome"}` 을 받아
하나의 항목 결과로 병합한다. 이 층은 그 네 칸만 읽는다 — 두 도구를 붙여 보고 실제로
버틴 유일한 계약이라, 칸을 늘리지 않는다.

어댑터 호출 순서와 시간 예산 분배도 여기서 정한다. 점수 합산은 언어 중립층
(`score.mutation_score`) 하나만 거친다 (D1).
"""

from __future__ import annotations

import time

def _mutation_preconditions(ctx: gate.GateContext, js_files, py_files) -> dict | None:
    """두 언어 모두에 걸리는 사유. 있으면 그 결과를, 없으면 None (R4).

    언어별 사유(도구 부재·설정 값 불일치)는 각 언어 경로가 따로 본다 — 한쪽이 없다고
    다른 쪽까지 건너뛰면 잰 것을 안 낸 것이 된다.
    """
    if not ctx.config.mutation_enabled:
        return gate._skip(
            "설정에서 뮤테이션을 꺼 두었습니다 (.code-gate.json 의 mutation.enabled). 이 항목은 재지 않았습니다.",
            "mutation disabled in config",
        )
    if not js_files and not py_files:
        return gate._skip(
            "변경된 파일 중 뮤테이션 대상이 없습니다 (자바스크립트 계열 — .vue / .svelte / .html 포함 — 과 파이썬).",
            "no changed mutable files",
        )
    return None


def _mutation_language_score(parts) -> tuple:
    """언어별 개수를 합친 (개수, 언어별 점수 문장). 잰 것이 없는 언어는 빠진다."""
    counts: dict = {}
    per_language: list = []
    for part in parts:
        summary = part.get("summary")
        if not summary:
            continue
        for name, value in summary["counts"].items():
            counts[name] = counts.get(name, 0) + int(value)
        score = summary["score"]
        per_language.append(
            f"{part['label']} {score:.1f}%" if score is not None else f"{part['label']} 점수 없음")
    return counts, per_language


def _mutation_unmeasured(parts) -> list:
    """점수를 내지 못한 언어 이름. 그 언어는 합산 안에 없다."""
    return [part["label"] for part in parts if not part.get("summary")]


def _mutation_below(ctx: gate.GateContext, parts) -> list:
    """기준에 못 미친 언어 이름. 합산이 기준을 넘겨도 이 목록이 비어 있지 않을 수 있다."""
    threshold = ctx.config.mutation_score_threshold
    below = []
    for part in parts:
        summary = part.get("summary")
        score = summary["score"] if summary else None
        if score is not None and score < threshold:
            below.append(part["label"])
    return below


def _mutation_merged_caveats(ctx: gate.GateContext, parts) -> str:
    """합산 점수만 읽으면 놓치는 것 — 재지 못한 언어와 기준 미달 언어."""
    text = ""
    unmeasured = ", ".join(_mutation_unmeasured(parts))
    if unmeasured:
        text += f". {unmeasured}{score_mod._ko_topic(unmeasured)} 재지 못해 이 점수에 들어 있지 않습니다"
    below = ", ".join(_mutation_below(ctx, parts))
    if below:
        text += f". {below}{score_mod._ko_topic(below)} 기준에 못 미칩니다"
    return text


def _mutation_merged_head(ctx: gate.GateContext, parts, counts: dict, per_language) -> str:
    """합산 머리말. 점수는 반드시 mutation_score 하나를 거친다 (D1).

    합산 점수는 두 언어 비율 사이의 값이라, 한쪽이 기준에 못 미쳐도 합산은 기준을 넘길 수
    있다. 기준과의 비교가 나오는 자리는 이 머리말 하나뿐인데 그 비교가 통과를 가리키면서
    항목 판정은 발견이 되는 어긋남이 실제로 나왔다 (실측). 그래서 미달 언어와 재지 못한
    언어를 머리말 안에서 함께 말한다. 한 언어만 쟀으면 "합산" 이라고 부르지 않는다.
    """
    score = score_mod.mutation_score(counts)
    if score is None:
        return "두 언어를 합쳐도 점수를 낼 변이가 없습니다."
    measured = [part["label"] for part in parts if part.get("summary")]
    lead = "합산 점수" if len(measured) > 1 else f"{measured[0]} 점수"
    text = (f"{lead} {score:.1f}% (기준 {ctx.config.mutation_score_threshold:g}%), "
            f"변이 {sum(counts.values())}개 — {score_mod._mutation_distribution(counts)} "
            f"(언어별 {' / '.join(per_language)})")
    return text + _mutation_merged_caveats(ctx, parts)


def _mutation_merged_findings(outcomes) -> tuple:
    """(합친 목록, 설치 방법 하나). 목록은 두 언어를 그대로 이어 붙인다."""
    findings: list = []
    hints: list = []
    for outcome in outcomes:
        findings += list(outcome.get("findings", ()))
        if outcome.get("install_hint"):
            hints.append(outcome["install_hint"])
    return findings, (hints[0] if hints else None)


def _mutation_merged_sentences(parts) -> tuple:
    """(영어 사유, 언어별 한국어 문장). 언어 이름을 앞에 붙여 어느 쪽 말인지 드러낸다."""
    reason = " | ".join(f"{p['language']}: {p['outcome'].get('reason', '')}" for p in parts)
    sentences = [f"{p['label']}: {p['outcome'].get('human_reason', '')}" for p in parts]
    return reason, sentences


def _merge_mutation_languages(ctx: gate.GateContext, parts: list) -> dict:
    """언어별 결과를 항목 하나로. 점수는 개수를 합쳐 **한 번만** 계산한다 (D1).

    합산만 내면 어디가 약한지 알 수 없어 언어별 점수와 문장을 함께 싣는다. 시간도 언어마다
    자릿수가 달라 각 문장이 자기 초를 갖고 있다 (R1).
    가장 나쁜 상태가 이긴다 — 합산 점수는 두 언어 비율 사이의 값이라, 둘 다 기준을 넘으면
    합산도 넘는다. 따로 판정할 것이 없다.
    """
    if len(parts) == 1:
        return parts[0]["outcome"]
    order = {"ok": 0, "skipped": 1, "findings": 2, "error": 3, "timeout": 4}
    outcomes = [part["outcome"] for part in parts]
    worst = max(outcomes, key=lambda o: order.get(o.get("status"), 0))
    counts, per_language = _mutation_language_score(parts)
    findings, hint = _mutation_merged_findings(outcomes)
    reason, sentences = _mutation_merged_sentences(parts)
    return {
        "status": worst.get("status", "error"),
        "reason": reason,
        "human_reason": " · ".join([_mutation_merged_head(ctx, parts, counts, per_language), *sentences]),
        "install_hint": hint,
        "findings": findings,
    }


def check_mutation(ctx: gate.GateContext) -> dict:
    """변경분에 든 언어만 잰다. 둘 다 있으면 둘 다 재고 점수를 합쳐 한 번 낸다.

    예산은 **항목 하나의 것**이다. 언어마다 설정값을 통째로 잡으면 C7 하나가 설정값의 두 배까지
    돈다 — 여기서 마감 시각을 한 번 정해 두 언어가 나눠 쓰게 한다 (확정 6).
    """
    js_files = javascript._mutation_changed_files(ctx)
    py_files = python._mutation_changed_python_files(ctx)
    blocked = _mutation_preconditions(ctx, js_files, py_files)
    if blocked is not None:
        return blocked
    budget = ctx.config.mutation_timeout_seconds
    ctx.mutation_deadline = time.perf_counter() + budget
    parts = []
    if js_files:
        parts.append(javascript._check_mutation_javascript(ctx, js_files))
    if py_files:
        parts.append(python._check_mutation_python(ctx, py_files) if score_mod._mutation_budget(ctx) > 0
                     else score_mod._mutation_out_of_budget("python", "파이썬", budget))
    return _merge_mutation_languages(ctx, parts)


# import 는 정의가 모두 끝난 뒤에 한다. 어댑터·중립층은 뼈대(code_gate)를 import 하고,
# 뼈대는 하단에서 이 패키지의 check_mutation 을 도로 import 한다 — 이 순환은 어느 쪽이
# 먼저 import 되든 "이름 정의를 끝낸 뒤 상대를 부른다" 로만 풀린다. 함수 본문의
# gate.* / score_mod.* / javascript.* / python.* 참조는 호출 시점 조회라 이 위치로 충분하다.
from scripts import code_gate as gate  # noqa: E402
from scripts.mutation import score as score_mod  # noqa: E402
from scripts.mutation import javascript  # noqa: E402
from scripts.mutation import python  # noqa: E402
