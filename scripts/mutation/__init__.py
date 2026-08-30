"""C7 뮤테이션 — 합치는 층.

언어 어댑터가 낸 네 칸 사전 `{"language", "label", "summary", "outcome"}` 을 받아
하나의 항목 결과로 병합한다. 이 층은 그 네 칸만 읽는다 — 두 도구를 붙여 보고 실제로
버틴 유일한 계약이라, 칸을 늘리지 않는다.

어댑터 호출 순서와 시간 예산 분배도 여기서 정한다. 점수 합산은 언어 중립층
(`score.mutation_score`) 하나만 거친다 (D1).
"""

from __future__ import annotations

import importlib
import pkgutil
import time
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 레지스트리 — 등록된 어댑터 목록의 단일 출처
#
# 두 언어를 손으로 부르던 때는 세 번째 언어를 붙일 자리가 없었다. 뼈대의 설정 키
# (mutation.<언어>)까지 두 이름을 박아 두어, .code-gate.json 에 "go" 를 넣으면
# "알 수 없는 키" 로 버려졌다 (실측). 언어 목록의 출처를 여기 하나로 모은다.
# ---------------------------------------------------------------------------

_ADAPTER_SUFFIX = "_ADAPTER"

# 진입점 이름 규약 — 어댑터 모듈은 이 두 이름을 자기 언어 이름으로 갖는다
# (실행부 `_run_mutation_<언어>` 는 어댑터 안에서만 쓰여 여기서 부르지 않는다).
# 계약 테스트가 같은 규약을 검사한다. 손으로 쓰는 등록 목록은 두지 않는다 — 등록을
# 잊은 어댑터가 검사 0건으로 통과한 적이 있다.
_ENTRY_CHANGED = "_mutation_changed_{language}"
_ENTRY_CHECK = "_check_mutation_{language}"


@dataclass(frozen=True)
class Adapter:
    """등록된 어댑터 하나 — 선언부(AdapterSpec)와 그 모듈의 묶음.

    진입점은 함수 객체를 들고 있지 않고 부를 때마다 이름으로 찾는다. 값을 붙잡아 두면
    모듈 속성을 바꿔치기한 테스트가 옛 함수를 부르게 되고, 실행 중 교체가 조용히 무시된다.
    """

    spec: object
    module: object

    @property
    def language(self) -> str:
        return self.spec.language

    @property
    def label(self) -> str:
        return self.spec.label

    @property
    def config_leaf(self) -> str:
        """`.code-gate.json` 의 mutation 블록 안에서 이 어댑터의 도구 이름 자리.

        선언은 `mutation.<언어>` 형태다 (계약 테스트가 그 형태를 강제한다). 뼈대의 설정
        읽기가 이 값을 키로 쓰므로, 선언이 거짓이면 그 자리의 설정이 읽히지 않는다.
        """
        block, _, leaf = self.spec.config_key.partition(".")
        return leaf or block

    @property
    def target_note(self) -> str:
        """"대상이 없다" 안내에 실을 이 어댑터의 대상 설명. 없으면 이름표로 대신한다.

        확장자 목록을 사람 말로 옮기는 규칙은 선언부에 없다 (`.vue` 를 "자바스크립트 계열"
        이라고 부르는 것은 도구 사실이 아니라 문장이다). 그렇다고 안내문에 언어를 손으로
        적으면 어댑터를 더할 때마다 그 문장이 뒤처진다 — 어댑터 모듈이 자기 몫을 신고한다.
        """
        return getattr(self.module, "MUTATION_TARGET_KO", None) or self.label

    def changed_files(self, ctx) -> list:
        return getattr(self.module, _ENTRY_CHANGED.format(language=self.language))(ctx)

    def check(self, ctx, files) -> dict:
        return getattr(self.module, _ENTRY_CHECK.format(language=self.language))(ctx, files)


_registry: tuple = ()


def _module_adapters(module) -> list:
    """모듈 하나가 신고한 어댑터. 이름 규칙(`<언어대문자>_ADAPTER`)으로만 찾는다."""
    return [Adapter(spec=value, module=module) for name, value in vars(module).items()
            if name.endswith(_ADAPTER_SUFFIX) and isinstance(value, score_mod.AdapterSpec)]


def adapters() -> tuple:
    """등록된 어댑터 — 언어 이름 오름차순으로 고정한다.

    `scripts/mutation/` 안의 `<언어대문자>_ADAPTER` 상수를 훑어 찾는다. 파일을 놓으면
    등록되고, 그 밖에 손댈 목록이 없다.
    순서에는 뜻이 없다. 다만 뜻이 없다고 흔들리게 두면 출력 순서가 회차마다 달라져
    동등성을 기계로 확인할 수 없다 (1b 에서 실제로 그랬다).
    **이 순서는 출력 순서일 뿐 예산의 우선순위가 아니다.** 뜻 없는 값(언어 이름의
    알파벳순)이 "누가 예산을 다 쓰는가" 를 정하던 때, 뒤로 밀린 언어의 점수와 설치 안내가
    통째로 사라졌다 (실측). 예산은 `_mutation_share` 가 남은 어댑터 수로 나눠 준다.
    """
    global _registry
    if not _registry:
        found: list = []
        for info in pkgutil.iter_modules(__path__):
            found += _module_adapters(importlib.import_module(f"{__name__}.{info.name}"))
        _registry = tuple(sorted(found, key=lambda adapter: adapter.language))
    return _registry


def _mutation_preconditions(ctx: gate.GateContext, changed) -> dict | None:
    """어느 언어에도 걸리는 사유. 있으면 그 결과를, 없으면 None (R4).

    언어별 사유(도구 부재·설정 값 불일치)는 각 언어 경로가 따로 본다 — 한쪽이 없다고
    다른 쪽까지 건너뛰면 잰 것을 안 낸 것이 된다.
    """
    if not ctx.config.mutation_enabled:
        return gate._skip(
            "설정에서 뮤테이션을 꺼 두었습니다 (.code-gate.json 의 mutation.enabled). 이 항목은 재지 않았습니다.",
            "mutation disabled in config",
        )
    if not any(files for _adapter, files in changed):
        targets = ", ".join(adapter.target_note for adapter, _files in changed)
        return gate._skip(
            f"변경된 파일 중 뮤테이션 대상이 없습니다 (대상 언어: {targets}).",
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
        return _mutation_no_score_head(parts)
    measured = [part["label"] for part in parts if part.get("summary")]
    lead = "합산 점수" if len(measured) > 1 else f"{measured[0]} 점수"
    text = (f"{lead} {score:.1f}% (기준 {ctx.config.mutation_score_threshold:g}%), "
            f"변이 {sum(counts.values())}개 — {score_mod._mutation_distribution(counts)} "
            f"(언어별 {' / '.join(per_language)})")
    return text + _mutation_merged_caveats(ctx, parts)


def _mutation_no_score_head(parts) -> str:
    """점수가 없을 때의 머리말.

    "재려다 변이가 없었다" 와 "아예 재지 못했다" 는 사용자가 할 일이 다르다. 뒤쪽은
    대개 도구가 없는 경우라, 그렇게 말해야 바로 뒤에 붙는 설치 방법이 읽힌다 (R4).
    언어 수는 문장에 박지 않는다 — 어댑터가 셋을 넘으면 "두 언어" 가 거짓이 된다.
    """
    names = ", ".join(part["label"] for part in parts)
    if any(part.get("summary") for part in parts):
        return f"점수를 낼 변이가 없습니다 ({names})."
    return f"어느 언어도 재지 못했습니다 ({names})."


def _mutation_merged_findings(parts) -> tuple:
    """(합친 목록, 합친 설치 방법). 목록은 언어를 그대로 이어 붙인다.

    설치 방법을 하나만 남기던 때는, 두 언어의 도구가 **둘 다** 없을 때 뒤 언어의 안내가
    사라졌다. 세 언어가 넘어가면 대부분이 사라진다 — R4 의 "설치 방법을 반드시 보고" 가
    말없이 깎이는 자리라, 서로 다른 안내는 등록 순서대로 모두 싣는다. 하나뿐이면
    문자열이 그대로라 지금까지의 출력과 같다.
    여럿이면 **어느 언어의 안내인지 앞에 붙인다.** 그냥 이어 붙이면 안내 자체에 든 빗금
    (`@stryker-mutator/core`)과 구분이 안 되고, 복사해 붙여도 실행되지 않는 한 줄이 된다.
    """
    findings: list = []
    hints: list = []
    for part in parts:
        outcome = part["outcome"]
        findings += list(outcome.get("findings", ()))
        hint = outcome.get("install_hint")
        if hint and hint not in [text for _label, text in hints]:
            hints.append((part["label"], hint))
    return findings, _mutation_merged_hint(hints)


def _mutation_merged_hint(hints) -> str | None:
    """(언어 이름, 안내) 목록을 한 줄로. 없으면 None, 하나면 안내만 그대로."""
    if not hints:
        return None
    if len(hints) == 1:
        return hints[0][1]
    return " · ".join(f"{label}: {text}" for label, text in hints)


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
    findings, hint = _mutation_merged_findings(parts)
    reason, sentences = _mutation_merged_sentences(parts)
    return {
        "status": worst.get("status", "error"),
        "reason": reason,
        "human_reason": " · ".join([_mutation_merged_head(ctx, parts, counts, per_language), *sentences]),
        "install_hint": hint,
        "findings": findings,
    }


def _mutation_share(deadline: float, remaining: int) -> float:
    """이번 어댑터가 쓸 수 있는 초 — 남은 시간을 아직 안 돈 어댑터 수로 나눈 몫.

    앞 어댑터가 예산을 통째로 쓸 수 있던 때는, 등록 순서(언어 이름의 알파벳순)가 곧
    "누가 재고 누가 못 재는가" 였다. 자바가 예산을 다 써서 자바스크립트가 통째로
    빠지고, 그 점수와 살아남은 변이 목록과 설치 안내가 함께 사라졌다 (실측: 같은 입력에
    84.6% + 살아남음 2개 → "재지 못했습니다" + 목록 0개).
    나눠 주면 순서가 결과를 정하지 않는다. 앞이 자기 몫을 다 안 쓰면 남은 것이 그대로
    뒤로 흘러가므로, 한 언어만 도는 회차는 예전처럼 예산 전부를 쓴다.
    """
    return max(0.0, deadline - time.perf_counter()) / max(1, remaining)


def _mutation_part(ctx: gate.GateContext, adapter, files, order: int, budget: int) -> dict:
    """어댑터 하나의 조각. 자기 몫이 이미 ctx.mutation_deadline 에 들어 있다.

    첫 어댑터는 자기 앞에 아무도 없어 예산을 검사하지 않는다 — 검사하면 예산을 아주 작게
    잡은 회차에서 아무 언어도 돌지 않는다. 뒤 어댑터는 남은 시간이 0 이면 재지 않고 그
    사실을 남긴다. 조용히 빠지면 잰 것을 안 낸 것이 된다 (R4).
    """
    if order and score_mod._mutation_budget(ctx) <= 0:
        return score_mod._mutation_out_of_budget(adapter.language, adapter.label, budget)
    return adapter.check(ctx, files)


def _mutation_parts(ctx: gate.GateContext, running, deadline: float, budget: int) -> list:
    """도는 어댑터마다 자기 몫을 정해 부른다. 반환 순서는 등록 순서 그대로다.

    순서는 **실제로 도는 어댑터** 사이에서 매긴다. 등록 순서로 매기면, 앞에 등록됐지만
    이번에 변경분이 없어 돌지도 않은 어댑터 때문에 첫 주자가 "앞이 있다" 로 분류돼
    예산 검사에 걸린다 — 예산을 아주 작게 잡은 회차에서 아무 언어도 못 도는 그 실패다.
    """
    parts: list = []
    for order, (adapter, files) in enumerate(running):
        share = _mutation_share(deadline, len(running) - order)
        ctx.mutation_deadline = time.perf_counter() + share
        parts.append(_mutation_part(ctx, adapter, files, order, budget))
    return parts


def check_mutation(ctx: gate.GateContext) -> dict:
    """변경분에 든 언어만 잰다. 여럿이면 모두 재고 점수를 합쳐 한 번 낸다.

    예산은 **항목 하나의 것**이다. 언어마다 설정값을 통째로 잡으면 C7 하나가 설정값의 언어 수
    배까지 돈다 — 여기서 마감 시각을 한 번 정해 언어들이 나눠 쓰게 한다 (확정 6).
    """
    changed = [(adapter, adapter.changed_files(ctx)) for adapter in adapters()]
    blocked = _mutation_preconditions(ctx, changed)
    if blocked is not None:
        return blocked
    budget = ctx.config.mutation_timeout_seconds
    deadline = time.perf_counter() + budget
    running = [(adapter, files) for adapter, files in changed if files]
    parts = _mutation_parts(ctx, running, deadline, budget)
    return _merge_mutation_languages(ctx, parts)


# import 는 정의가 모두 끝난 뒤에 한다. 어댑터·중립층은 뼈대(code_gate)를 import 하고,
# 뼈대는 하단에서 이 패키지의 check_mutation 을 도로 import 한다 — 이 순환은 어느 쪽이
# 먼저 import 되든 "이름 정의를 끝낸 뒤 상대를 부른다" 로만 풀린다. 함수 본문의
# gate.* / score_mod.* 참조는 호출 시점 조회라 이 위치로 충분하다.
# 어댑터 모듈은 여기서 import 하지 않는다 — 이름을 적는 순간 그것이 곧 손으로 쓴 등록
# 목록이 된다. adapters() 가 첫 호출에서 패키지를 훑어 가져온다.
from scripts import code_gate as gate  # noqa: E402
from scripts.mutation import score as score_mod  # noqa: E402
