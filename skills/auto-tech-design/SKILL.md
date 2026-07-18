---
name: auto-tech-design
description: auto-flow 2단계 — requirements.md 읽기 + adaptive 7-topic 자동 판정 + design decision 자동 alternatives 비교 → recommendation 자동 선택 + verifying-spec 4축 보고서 transition 직전 노출 + auto-writing-plans 자동 invoke. AskUserQuestion 호출 X. generating-html 은 Step 4.5 에서 백그라운드(fire-and-forget) 호출.
---

# Auto Designing Direction → <slug>-tech-design.md (auto)

## Checklist

- [ ] Step 1 — 입력 확인 + slug 추론
- [ ] Step 2 — adaptive 7-topic 자동 판정
- [ ] Step 3 — AI 자동 design decision (각 활성 토픽)
- [ ] Step 4 — 산출물 자동 작성 (<slug>-tech-design.md)
- [ ] Step 4.5 — generating-html fire-and-forget dispatch + 5초 race delay
- [ ] Step 5 — verifying-spec 자동 실행 (4축 보고서)
- [ ] Step 6 — change-history 자동 ([개발방향-수정] entry)
- [ ] Step 7 — Transition notice + auto-writing-plans invoke

## Process

### Step 1 — 입력 확인 + slug 추론

`<slug>-requirements.md` 존재 확인. 인자 누락 시 `scripts/auto_flow.find_latest_slug(Path("docs/features"))` 호출.

### Step 2 — adaptive 7-topic 자동 판정

`<slug>-requirements.md` 본문 분석. 항상 활성 4 (1,2,5,6) + 조건부 3 (3,4,7). 메인이 본문 컨텍스트로 판단 + 한 줄 announce:

```
ℹ️ 활성 토픽은 ... 이고, 비활성 토픽은 ... 입니다 (이유: ...). 자동 흐름이라 사용자 응답 없이 다음 단계로 넘어갑니다.
```

→ 사용자 catch 가능 위치이지만 응답 wait X.

### Step 3 — AI 자동 design decision

각 활성 토픽에 대해 메인이 2-3 alternatives + recommendation 1개 자동 선택 (D-T3). reasoning 은 §5 결정+대안 비교 에 logged. 비활성 토픽은 N/A 한 줄.

### Step 4 — 산출물 자동 작성

`<slug>-tech-design.md` 7-section schema 따라 작성. RAW 본문.

### Step 4.5 — generating-html fire-and-forget dispatch (v2.3.2+)

`<slug>-tech-design.md` 작성 직후, **change-history entry 박히기 전** (footer 비어있음) 에 `generating-html` skill fire-and-forget dispatch (`run_in_background: true`). 메인 latency 거의 0. transition notice 시점에 사용자가 `.html` 검토 가능 (Type "stop" abort). v1.1.17 PRD D9 amend 반전 (v2.3.2+).

**v2.4+ race delay**: dispatch 후 **5초 delay** 후에 Step 5 (verifying-spec) 진행. background subagent 가 .md 의 footer 0건 시점에 읽도록 보장 (race condition 해결).

### Step 5 — verifying-spec 자동 실행

`verifying-spec` skill invoke (메인 자체 수행 또는 skill 호출). 4축 보고서 생성. 결과는 다음 단계 transition notice 직전 노출.

### Step 6 — change-history 자동

`change-history` skill invoke → 첫 `[개발방향-수정]` entry. CH-id 자동.

### Step 7 — Transition notice + auto-writing-plans invoke

```
🔍 verifying-spec 결과:
   - A1 consistency: ✅
   - A2 ...
   - C1 impact: ⚠️ 영향 N 컴포넌트
   - C2 ...

ℹ️ /write-plan 단계로 자동 넘어갑니다. 멈추려면 "stop" 입력해주세요.
```

`parse_interrupt` 매치 시 exit + `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` 안내. 매치 X → `js-super:auto-writing-plans` invoke.

## --no-ask 플래그 (v2.5+) — 짧은 reference

본 skill 흐름은 `AskUserQuestion` 호출이 본문에 명시 X (clarifying Q 자체가 prose default). `--no-ask` 플래그 진입 시 추가 분기 없음 — 본문 그대로 도구 호출 0 보장.

단 내부 escalation (BLOCKED 자가복구 실패 / critical 7 재질문 / Other 모호 응답) 에서도 도구 호출 0 보장. 자세한 룰은 `skills/brainstorming/SKILL.md` 의 `### 예외 — \`--no-ask\` 플래그 (v2.5+)` 답습.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. |
| generating-html 동기 호출 (sync wait) | NEVER. v2.3.2+ — Step 4.5 fire-and-forget 만. (v1.1.17 "호출 부재" 룰 v2.3.2 반전.) |
| 일반 tech-design skill body 호출 | NEVER. self-contained mirror (D-T1). |
| transition notice 후 wait sleep | NEVER. |

## Related Skills

- `auto-writing-plans` — 다음 단계
- `verifying-spec` — 4축 보고서 생성
- `change-history` — 첫 entry append
- `scripts/auto_flow.parse_interrupt`, `find_latest_slug`
