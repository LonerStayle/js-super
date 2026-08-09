---
name: auto-writing-plans
description: auto-flow 3단계 — /auto-write-plan 커맨드 또는 앞 단계 auto-tech-design 의 명시 invoke 로만 진입, 사용자 자유 요청에서 자동 선택 금지. requirements + tech-design 읽기 + AI 자동 task 분해 (TDD bite-sized + Model hint 자동) + RISK 코드 지점 §2 자동 + verifying-spec 자동 + code-pretty 호출 X (D-T12 와 일관) + change-history 자동 + auto-executing-plans 자동 invoke. AskUserQuestion 호출 X. generating-html 은 Step 4.6 에서 백그라운드(fire-and-forget) 호출.
---

# Auto Writing Plans → <slug>-implementation-plan.md (auto)

## Checklist

- [ ] Step 1 — 입력 확인 + slug 추론
- [ ] Step 2 — AI 자동 task 분해 (TDD bite-sized + Model hint 자동)
- [ ] Step 3 — §2 위험 코드 지점 자동 (R-N → file:line 매핑)
- [ ] Step 4 — 산출물 자동 작성 (<slug>-implementation-plan.md)
- [ ] Step 4.5 — plan_byte_check 자동 (3회 재시도)
- [ ] Step 4.6 — generating-html fire-and-forget dispatch + 5초 race delay
- [ ] Step 5 — verifying-spec 자동 실행 (4축 보고서)
- [ ] Step 6 — change-history 자동 ([구현계획서-수정] entry)
- [ ] Step 7 — Transition notice + auto-executing-plans invoke

## Process

### Step 1 — 입력 확인 + slug 추론

`<slug>-requirements.md` + `<slug>-tech-design.md` 모두 존재 확인. 누락 시 `ℹ️ 입력이 누락됐습니다 (<누락 파일>). /auto-brainstorm 또는 /auto-tech-design 부터 시작해주세요.` 안내 후 종료.

### Step 2 — AI 자동 task 분해

tech-design §1~§7 + R1~R10 분석. TDD bite-sized task 자동 생성:
- 각 task 의 Files / Model hint / TDD steps / RISK 자동 결정
- Model 힌트 자동: 1-2 파일 mechanical → haiku / 다중 파일 + 통합 → sonnet / 설계 + 광범위 → opus / Korean prose 조작 → sonnet (Haiku rephrasing 위험) / 신규 테스트 작성 포함 task → 최소 sonnet (v2.9+ floor)
- Before/After 코드블록 (`**원본**` / `**수정 후**`) 컨벤션 — 구현 코드 전용. 테스트 코드 블록은 싣지 않고 task 헤더 `**검증**:` 필드 (자연어 1~2줄, 무엇을 + 성공 기준) 로 대체 (v2.9+)

**Same-file mechanical 묶음 룰 (v2.0.1+)**: 둘 이상의 logical change 가 다음 **세 조건 모두** 만족하면 1 task 의 multi-step 으로 묶는다.

1. **같은 파일** — Files 목록 동일
2. **테스트 경계 없음** — 한 통합 test 또는 UI preview 로 같이 검증 가능
3. **mechanical** — modifier / handler / container 옵션 / placeholder / import 등 (= 알고리즘 변경 X)

세 조건 중 하나라도 어기면 분리. multi-step task 안 step 구조: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 1회) → byte-copy Edit (N회) → test pass → self-review. 애매하면 분리 (보수적 default).

**Step 2 끝 자체 검토 (same-file 묶음 자체 검토)**: 자동 분해 결과 같은 파일만 만지는 task chain ≥ 2건 있으면 메인이 직접 D1 의 3 조건 재검토 → 묶을지 결정. 사용자 응답 wait X (auto 모드).

### Step 3 — §2 위험 코드 지점 자동

tech-design §6 R-N → file:line + mitigation 매핑. 모든 R-N 이 §2 에 entry 갖도록 보장 (writing-plans Self-Review 룰).

### Step 4 — 산출물 자동 작성

`<slug>-implementation-plan.md` schema 따라 작성. frontmatter `commit_policy: per-task`. RAW 본문, code-pretty 호출 X (D-T12 일관). generating-html 은 plan_byte_check 통과 후 Step 4.6 에서 fire-and-forget dispatch.

### Step 4.5 — plan_byte_check 자동 (v2.0.0+)

Plan 본문 자동 작성 직후, 메인이 helper 자동 호출:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_byte_check import verify_plan_block_byte_equal
mismatches = verify_plan_block_byte_equal(
    Path('<PLAN_PATH>'),
    Path('.'),
)
if mismatches:
    for m in mismatches:
        print(f'MISMATCH #{m.block_index} — {m.reason}')
    sys.exit(1)
sys.exit(0)
"
```

미스매치 발견 시 메인이 즉시 plan 의 `**원본**` 블록 수정 후 재시도 (auto 모드 — 사용자 응답 wait X). 3회 재시도 후에도 실패 시 `ℹ️ plan_byte_check 가 3회 실패했습니다. 사용자가 직접 개입해주세요.` 안내 후 종료. byte-copy 정밀도 강제는 v2.0.0 구현계획서의 핵심 precondition.

### Step 4.6 — generating-html fire-and-forget dispatch (v2.3.2+)

plan_byte_check 통과 직후, **change-history entry 박히기 전** (footer 비어있음) 에 `generating-html` skill fire-and-forget dispatch (`run_in_background: true`). 메인 latency 거의 0. transition notice 시점에 사용자가 `.html` 검토 가능 (Type "stop" abort). v1.1.17 PRD D9 amend 반전 (v2.3.2+).

**v2.4+ race delay**: dispatch 후 **5초 delay** 후에 Step 5 (verifying-spec) 진행. background subagent 가 .md 의 footer 0건 시점에 읽도록 보장 (race condition 해결).

### Step 5 — verifying-spec 자동 실행

`verifying-spec` invoke. 4축 보고서 생성. 결과는 transition notice 직전 노출.

### Step 6 — change-history 자동

`change-history` invoke → 첫 `[구현계획서-수정]` entry. CH-id 자동.

### Step 7 — Transition notice + auto-executing-plans invoke

```
🔍 verifying-spec 결과: ...
ℹ️ /execute-plan 단계로 자동 넘어갑니다 (여러 작업을 보조 에이전트가 동시에 진행하고, 승인 게이트는 자동으로 통과합니다). 멈추려면 "stop" 입력해주세요.
```

`parse_interrupt` 매치 시 exit. 매치 X → `js-super:auto-executing-plans` invoke.

## --no-ask 플래그 (v2.5+) — 짧은 reference

본 skill 흐름은 `AskUserQuestion` 호출이 본문에 명시 X (clarifying Q 자체가 prose default). `--no-ask` 플래그 진입 시 추가 분기 없음 — 본문 그대로 도구 호출 0 보장.

단 내부 escalation (BLOCKED 자가복구 실패 / critical 7 재질문 / Other 모호 응답) 에서도 도구 호출 0 보장. 자세한 룰은 `skills/brainstorming/SKILL.md` 의 `### 예외 — \`--no-ask\` 플래그 (v2.5+)` 답습.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. |
| generating-html 동기 호출 (sync wait) | NEVER. v2.3.2+ — Step 4.6 fire-and-forget 만. (v1.1.17 "호출 부재" 룰 v2.3.2 반전.) |
| code-pretty 호출 | NEVER. D-T12 일관. |
| 일반 writing-plans skill body 호출 | NEVER. self-contained mirror (D-T1). |

## Related Skills

- `auto-executing-plans` — 다음 단계 (wave-parallel subagent 강제)
- `verifying-spec` / `change-history`
- `scripts/auto_flow.parse_interrupt`, `find_latest_slug`
