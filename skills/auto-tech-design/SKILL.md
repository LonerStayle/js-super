---
name: auto-tech-design
description: auto-flow 2단계 — /auto-design-tech 커맨드 또는 앞 단계 auto-brainstorming 의 명시 invoke 로만 진입, 사용자 자유 요청에서 자동 선택 금지. requirements.md 읽기 + adaptive 7-topic 자동 판정 + design decision 자동 alternatives 비교 → recommendation 자동 선택 + verifying-spec 4축 보고서 transition 직전 노출 + auto-writing-plans 자동 invoke. AskUserQuestion / generating-html 호출 X.
---

# Auto Designing Direction → <slug>-tech-design.md (auto)

## Checklist

- [ ] Step 1 — 입력 확인 + slug 추론
- [ ] Step 2 — adaptive 7-topic 자동 판정
- [ ] Step 3 — AI 자동 design decision (각 활성 토픽)
- [ ] Step 4 — 산출물 자동 작성 (<slug>-tech-design.md)
- [ ] Step 5 — verifying-spec 자동 실행 (4축 보고서)
- [ ] Step 6 — change-history 자동 ([개발방향-수정] entry)
- [ ] Step 7 — 깊이 판정 + Transition notice + (3개 판정 시) auto-writing-plans invoke

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

### Step 5 — verifying-spec 자동 실행

`verifying-spec` skill invoke (메인 자체 수행 또는 skill 호출). 4축 보고서 생성. 결과는 다음 단계 transition notice 직전 노출.

### Step 6 — change-history 자동

`change-history` skill invoke → 첫 `[개발방향-수정]` entry. CH-id 자동.

### Step 7 — 깊이 판정 + Transition notice + (3개 판정 시) auto-writing-plans invoke

```
🔍 verifying-spec 결과:
   - A1 consistency: ✅
   - A2 ...
   - C1 impact: ⚠️ 영향 N 컴포넌트
   - C2 ...

ℹ️ /write-plan 단계로 자동 넘어갑니다. 멈추려면 "stop" 입력해주세요.
```

**깊이 판정 (산출물 깊이 선택)**: transition notice 출력 전에 메인이 requirements + tech-design 내용으로 판정한다 — 코드 변경·구현 task 가 예상되는 피처면 **3개** (아래 invoke 진행), 순수 문서·설계·조사 성격 (산출물이 설계 문서 자체) 이면 **2개**. 애매하면 3개 (기존 동작 보존). 사용자에게 묻지 않는다 (AskUserQuestion 호출 X).

- **3개 판정**: 위 transition notice 출력. `parse_interrupt` 매치 시 exit + `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` 안내. 매치 X → `js-super:auto-writing-plans` invoke.
- **2개 판정**: tech-design frontmatter 에 `depth: 2` + `depth_reason: <판단 근거 1줄>` 기록 + `change-history` [개발방향-수정] entry 후, `ℹ️ 이 피처는 2개 문서 트랙으로 자동 확정했습니다 (판단 근거: <1줄>). 구현이 필요해지면 /write-plan 으로 승격하세요.` 출력하고 체인 종료. auto-writing-plans 미호출. transition notice 미출력.

## --no-ask 플래그 (v2.5+) — 짧은 reference

본 skill 흐름은 `AskUserQuestion` 호출이 본문에 명시 X (clarifying Q 자체가 prose default). `--no-ask` 플래그 진입 시 추가 분기 없음 — 본문 그대로 도구 호출 0 보장.

단 내부 escalation (BLOCKED 자가복구 실패 / critical 7 재질문 / Other 모호 응답) 에서도 도구 호출 0 보장. 자세한 룰은 `skills/brainstorming/SKILL.md` 의 `### 예외 — \`--no-ask\` 플래그 (v2.5+)` 답습.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. |
| generating-html 호출 (모든 형태) | NEVER. v2.8.2+ 커맨드 강등 — 자동 발동 폐지 (v2.3.2 의 Step 4.5 dispatch 제거). `.html` 필요 시 사용자가 명시 호출. |
| 일반 tech-design skill body 호출 | NEVER. self-contained mirror (D-T1). |
| transition notice 후 wait sleep | NEVER. |

## Related Skills

- `auto-writing-plans` — 다음 단계
- `verifying-spec` — 4축 보고서 생성
- `change-history` — 첫 entry append
- `scripts/auto_flow.parse_interrupt`, `find_latest_slug`
