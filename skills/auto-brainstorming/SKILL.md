---
name: auto-brainstorming
description: auto-flow 진입점. /auto-brainstorm 명시 호출 전용 — 대화 중 자동 선택 금지 (js-super 기본 진입은 brainstorming). Socratic clarifying Q (1~5개 적응) + AI 자동 approach 선택 + 자동 section 작성 + change-history 자동 + auto-tech-design 자동 invoke. 사용자 입력은 clarifying Q 답변에만. AskUserQuestion / Visual Companion / generating-html 호출 X.
---

# Auto Brainstorming → <slug>-requirements.md (Socratic auto)

js-super:auto-brainstorming 은 명시적 사용자 invoke (`/auto-brainstorm <피처명>`) 시에만 작동. `auto-flow-requirements.md` D1~D12 (D9 amend) + tech-design D-T1~D-T12 의 자동 흐름 본문.

**Announce at start:** "auto-brainstorming skill 로 자동 진행하겠습니다 (Socratic clarifying Q + AI 자동 chain)."

## 사용자 질문 룰 — Socratic prose only (auto-flow)

auto-flow 는 clarifying Q&A 구간을 제외하면 자동 진행이 핵심이다. 따라서 이 skill 흐름의 사용자 질문(clarifying / Socratic)은 **prose (메인 turn 자유 텍스트)** 로 처리하고 `AskUserQuestion` 도구는 호출하지 않는다.

- clarifying / Socratic 질문 — prose 로 한 번에 1개씩
- 자동 진행 안내 (`ℹ️ Auto-proceeding ...`) — 질문이 아니라 안내, 그대로 prose
- 일반 js-super `brainstorming` 의 v2.0.3+ "항상 AskUserQuestion" 룰은 **auto-flow 에는 적용되지 않는다** (사용자 결정 — `auto-executing-plans` 와 동일한 prose-default).

### Other / 모호 응답 처리 (v2.1.1+)

사용자가 "모르겠음 / 이해 안 됨" 류 답변 catch 시 → **그 질문만 prose 로 다시 던지고 설명 추가**. 다음 단계 자동 진행 X (명확한 답변에만 자동 진행).

### 예외 — `--no-ask` 플래그 (v2.5+)

auto-flow 는 이미 prose-default 라 `--no-ask` 는 **no-op** (추가 분기 없음). 사용자가 명시해도 동작은 동일하며, `AskUserQuestion` 호출 0 은 기본값으로 이미 보장된다.

## Checklist

- [ ] Step 1 — Slug 추론 + 폴더 생성
- [ ] Step 2 — Socratic clarifying questions (1~5개 적응)
- [ ] Step 3 — AI 자동 approach 선택
- [ ] Step 4 — 산출물 자동 작성 (<slug>-requirements.md)
- [ ] Step 5 — change-history 자동 (첫 [요구사항-수정] entry)
- [ ] Step 6 — Transition notice + auto-tech-design invoke

## Process

### Step 1 — Slug 추론 + 폴더 생성

`/auto-brainstorm <피처명>` 인자 → slug (공백 → 하이픈). 인자 누락 시 메인이 한 줄 묻고 진행.

```bash
mkdir -p docs/features/$(date +%Y-%m-%d)-<slug>/
```

### Step 2 — Socratic clarifying questions (1~5개 적응)

메인 에이전트가 사용자 첫 입력 + slug 으로 첫 질문 던짐. 한 번에 1개. 답변 충분히 명확하면 1개로 끝, 모호하면 최대 5개 (D-T2).

질문 패턴:
- 핵심 user story 한 줄?
- 가장 중요한 acceptance criterion?
- (필요 시) 명시적 범위 밖?
- (필요 시) 외부 의존성?
- (필요 시) 사용자가 우려하는 위험?

→ 사용자 답변 = 본 흐름의 유일한 사용자 입력 지점.

### Step 3 — AI 자동 approach 선택

메인이 2-3 approach + tradeoffs 자체 추론, recommendation 1개 자동 선택. 사용자에게 노출 X. 선택 reasoning 은 산출물 §핵심 결정 에 logged.

### Step 4 — 산출물 자동 작성

`<slug>-requirements.md` 작성 (자유 산문):
- H1 + 다음 단계 안내 배너 + 배경 + 핵심 결정 + `## 요구 항목` (FR-N) + 우려/해결 + 다음 단계 + 변경이력 footer
- `## 요구 항목` 과 `FR-N` 은 필수. 나머지 섹션은 대화에서 나온 대로. 모드 표기 줄은 쓰지 않는다.
- RAW 본문 그대로.

### Step 5 — change-history 자동

`change-history` skill invoke → 첫 `[요구사항-수정]` entry append. CH-id 자동 생성.

### Step 6 — Transition notice + auto-tech-design invoke

```
ℹ️ /tech-design 단계로 자동 넘어갑니다. 멈추려면 "stop" 입력해주세요.
```

다음 사용자 turn 의 입력에 `parse_interrupt` (scripts/auto_flow.py) 매치 시 cleanly exit + `ℹ️ 알겠습니다. /tech-design 은 나중에 직접 실행해주세요.` 안내. 매치 X 시 즉시 `js-super:auto-tech-design` skill invoke.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. auto-flow 의 사용자 입력은 clarifying Q 답변에만. |
| generating-html 호출 (모든 형태) | NEVER. v2.8.2+ 커맨드 강등 — 자동 발동 폐지 (v2.3.2 의 Step 4.5 dispatch 제거). `.html` 필요 시 사용자가 명시 호출. |
| Visual Companion offer | NEVER. D-T11. |
| 일반 brainstorming skill body 호출 | NEVER. self-contained mirror (D-T1). |
| transition notice 후 사용자 응답 wait sleep | NEVER. harness 모델은 자동 다음 turn — sleep X. |

## Related Skills

- `auto-tech-design` — 다음 단계
- `change-history` — 첫 entry append
- `scripts/auto_flow.parse_interrupt` — interrupt 키워드 catch
