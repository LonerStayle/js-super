---
name: change-propagation
description: Use whenever the user expresses a change to existing 요구사항/개발방향/구현계획서/code in a feature folder (natural language like "X 바꿔/추가해/빼" or explicit edit-skill invocation). Identifies the change level, applies the impact matrix to surface affected downstream artifacts, gates user approval, then performs cascading updates and writes change-history entries with cross-linked CH-ids.
---

# Change Propagation (Cascading Update)

After the initial 3-MD set is in place, any modification request must check for cascading impact across downstream MDs and code. This skill is the dispatcher for those follow-up edits — it keeps the upstream → downstream chain consistent and writes cross-linked change-history entries.

<HARD-GATE>
NEVER silently update downstream MDs or code without first surfacing the impact list and asking the user to approve scope. Cascading without consent is a data-integrity bug.
</HARD-GATE>

## Trigger Detection

Two ways to enter this skill:

1. **Natural language change request** — the user says something like "요구 3 한도 바꿔", "개발방향 §5 결정 다시", "Task 4 단계 추가". The main agent recognizes the intent and invokes this skill. Older docs number the same items `FR-N`, so a request naming "FR-3" points at the same thing — recognize both.
2. **Explicit override** — the user says "요구사항만 고쳐, 하위는 건드리지 마". This phrase forces partial-scope behavior; the skill applies the upstream edit but skips the cascading step.

## Change Level Identification

| Phrase signals | Change level |
|---|---|
| FR / NFR / 사용자 시나리오 / 수용 기준 | 요구사항 |
| 아키텍처 / 컴포넌트 / 데이터 모델 / 결정 / 외부 IF / 위험 / 테스트 전략 | 개발방향 |
| Task 추가/순서/단계 코드/롤백 | 구현계획서 |
| 함수 본문 / 버그 수정 / 코드 리팩터 | 코드 |

If the request is ambiguous, ask the user once: "이건 요구사항 변경인가요, 개발방향 변경인가요?" Do NOT guess silently.

## Impact Matrix

| Change at | Auto-cascade targets |
|---|---|
| <slug>-requirements.md | <slug>-tech-design.md + <slug>-implementation-plan.md + code (if implemented) |
| <slug>-tech-design.md | <slug>-implementation-plan.md + code |
| <slug>-implementation-plan.md | code |
| code (direct edit) | <slug>-implementation-plan.md `## 변경이력` only (reverse-direction record) |

Code edits never cascade upward to 요구사항 or 개발방향. The reasoning is unchanged; only the implementation moved.

### 2-doc 트랙 분기 (산출물 깊이 선택)

피처의 tech-design frontmatter 가 `depth: 2` (2-doc 확정 트랙) 이면 위 matrix 를 다음과 같이 적용한다:

- `<slug>-implementation-plan.md` 행 (변경 지점·cascade 대상 양쪽) 은 무효 — 문서가 존재하지 않는다.
- `<slug>-requirements.md` / `<slug>-tech-design.md` 행의 cascade 대상에서 `<slug>-implementation-plan.md` 를 제외한다.
- `code (direct edit)` 행의 기록 목적지는 `<slug>-tech-design.md` `## 변경이력` 으로 대체한다 (footer append 는 본문 수정이 아님 — Acceptance 4 참조).
- 구현이 필요해진 변경이면 `/write-plan` 승격을 안내한다 (frontmatter `depth: 3` 갱신 후 기존 matrix 복귀).

## Checklist

- [ ] Trigger Detection — 변경 신호 catch
- [ ] Change Level Identification — 어느 레벨 변경 (요구사항 / 개발방향 / 구현계획서 / 코드)
- [ ] Impact Matrix 적용 — 영향 받는 downstream MD 식별
- [ ] Process Flow — cascading 갱신 실행
- [ ] User Approval — 사용자 게이트
- [ ] After Approval — change-history cross-linked entry append

## Process Flow

```dot
digraph propagation {
    "Detect change request" [shape=box];
    "Identify change level" [shape=diamond];
    "Apply impact matrix" [shape=box];
    "Compose impact list" [shape=box];
    "Show user: 'These will be touched'" [shape=box];
    "User approves scope?" [shape=diamond];
    "Apply edits to all approved targets" [shape=box];
    "Cross-link CH-ids\n(연관 항목)" [shape=box];
    "Done" [shape=doublecircle];

    "Detect change request" -> "Identify change level";
    "Identify change level" -> "Apply impact matrix";
    "Apply impact matrix" -> "Compose impact list";
    "Compose impact list" -> "Show user: 'These will be touched'";
    "Show user: 'These will be touched'" -> "User approves scope?";
    "User approves scope?" -> "Apply edits to all approved targets" [label="approved"];
    "User approves scope?" -> "Apply edits to all approved targets" [label="partial → narrowed"];
    "User approves scope?" -> "Done" [label="cancel"];
    "Apply edits to all approved targets" -> "Cross-link CH-ids\n(연관 항목)";
    "Cross-link CH-ids\n(연관 항목)" -> "Done";
}
```

## User Approval Format

먼저 영향 목록을 prose 로 노출 (사용자가 읽는 display):

```
변경 요청 감지: <change level> 변경 ("<short summary of the change>")

영향 매트릭스 적용 결과 — 함께 갱신될 항목:
1. <slug>-requirements.md 요구 항목 요구 3 (직접 변경)
2. <slug>-tech-design.md §6 위험 (한도 증가에 따른 잔액 검증 강도 재평가)
3. <slug>-implementation-plan.md Task 4 (한도 검증 로직)
4. 코드 src/wallet/service.py:withdraw() (한도 상수)
```

그다음 **`AskUserQuestion` 도구로 진행 여부를 묻습니다** (응답 전 편집 X — HARD-GATE):

```json
{
  "questions": [
    {
      "question": "위 영향 항목들을 어떻게 갱신할까요?",
      "header": "전파 승인",
      "multiSelect": false,
      "options": [
        {"label": "전체 진행", "description": "모든 영향 항목을 갱신"},
        {"label": "부분 진행", "description": "일부만 선택 — 다음 질문에서 번호로 고름"},
        {"label": "취소", "description": "아무것도 갱신하지 않음"}
      ]
    }
  ]
}
```

"부분 진행" 선택 시 → **두 번째 `AskUserQuestion` (`multiSelect: true`)** 로 위 번호 항목들을 옵션으로 제시하고 갱신할 것만 고르게 합니다. `AskUserQuestion` 이 없는 하네스면 위 목록 + "진행 / 부분 진행(번호 선택) / 취소" 를 prose 로 대체 (마지막 줄은 한국어 그대로 — 사용자가 읽는 문구).

## After Approval

For each approved target:

1. Apply the edit (directly via Edit, or by re-entering the relevant skill — `brainstorming` for 요구사항, `tech-design` for 개발방향, `writing-plans` for 구현계획서)
2. Invoke `change-history` to append the entry
3. Cross-link: every entry from the same propagation batch shares the **연관 항목** field listing the other CH-ids in the batch

Example entry skeleton (one of N in a batch):
```markdown
### [2026-05-02 14:30] [요구사항-수정]
- **id**: CH-20260502-007
- **이유**: 사용자 요청, 한도 5만 → 10만
- **무엇이**: <slug>-requirements.md 요구 항목 요구 3
- **영향범위**: <slug>-tech-design.md §6 (위험 재평가), <slug>-implementation-plan.md Task 4 (검증 로직)
- **연관 항목**: CH-20260502-008 (개발방향), CH-20260502-009 (구현계획서), CH-20260502-010 (코드)
```

## Anti-Patterns

| Wrong | Right |
|---|---|
| Skipping cascading because "user only mentioned 요구사항" | Apply impact matrix → show downstream → let user decide scope. |
| Guessing change level on ambiguous request | Ask once. Don't silently pick. |
| Editing code directly without <slug>-implementation-plan.md entry | Code edits always log to <slug>-implementation-plan.md (reverse direction; 2-doc 트랙은 <slug>-tech-design.md footer). |
| Forgetting to cross-link CH-ids | Cross-link is the audit chain. Every propagation batch shares **연관 항목**. |

## Red Flags

| Thought | Reality |
|---|---|
| "It's a tiny FR tweak, no downstream impact" | Run the matrix anyway. The user can decline cascading. |
| "User said 'just fix the bug'" | Even bug fixes get a [코드-수정] entry in <slug>-implementation-plan.md (2-doc 트랙은 <slug>-tech-design.md footer). |
| "Cross-linking is overkill for 2 entries" | Two entries today, twenty linked entries six months from now. Always link. |

## Acceptance

A propagation run is correct when ALL hold:
1. The user saw the impact list before any downstream edit
2. Every approved target produced a change-history entry
3. All entries in the batch share **연관 항목** with the other CH-ids in the batch
4. Code-only edits did not modify the BODY of <slug>-requirements.md or <slug>-tech-design.md (reverse-cascade is forbidden — 단 2-doc 트랙의 `## 변경이력` footer append 는 본문 수정이 아니므로 예외)

## Related Skills

- `change-history` — entry recording (called for each target)
- `brainstorming` / `tech-design` / `writing-plans` — re-entered when an upstream MD edit needs a re-dialogue
- `verifying-spec` — re-runs after upstream MD changes if scope is non-trivial
- `risk-annotation` — invoked again if cascading touches code
