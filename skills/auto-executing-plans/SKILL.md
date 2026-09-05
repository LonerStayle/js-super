---
name: auto-executing-plans
description: auto-flow 4단계 (마지막) — /auto-execute-plan 커맨드 또는 앞 단계 auto-writing-plans 의 명시 invoke 로만 진입, 사용자 자유 요청에서 자동 선택 금지. implementation-plan.md 읽기 + Entry Guard (preflight.subagent_task_entry_check) + DAG 자동 build + 무조건 wave-parallel subagent 강제 (Gate #14 override) + failure isolation 그대로 + End-of-run consolidator 자동 + finishing-a-development-branch 자동 호출. AskUserQuestion 호출 X.
user-invocable: false
---

# Auto Executing Plans → wave-parallel + finishing (auto)

## Checklist

- [ ] Step 1 — Entry Guard (preflight.subagent_task_entry_check)
- [ ] Step 2 — slug 추론
- [ ] Step 3 — wave-parallel subagent 강제 invoke (Gate 자동 통과)
- [ ] Step 4 — failure isolation (D6)
- [ ] Step 5 — End-of-run consolidator 자동
- [ ] Step 6 — finishing-a-development-branch 자동 호출
- [ ] Step 7 — auto-flow 완료 메시지

## Process

### Step 1 — Entry Guard

`scripts.preflight.subagent_task_entry_check` 호출 (기존 helper 재활용, D-T6). plan 존재 + commit_policy=per-task 검사. fail 시 v1.1.15 user-gate 발화 (3 choice — 단 auto-flow 의도상 "스킵 (이번만)" 선택지가 자연스러운 종료 경로).

### Step 2 — slug 추론

인자 누락 시 `scripts/auto_flow.find_latest_slug` 호출. 추론된 slug 1줄 노출 (R8 mitigation): `⚙️ <slug> 자동 선택. 다른 폴더면 'stop' 후 인자 명시.`

### Step 3 — wave-parallel subagent 강제 invoke

무조건 `js-super:js-super-sub-driven` skill invoke (D5, Gate #14 override). plan 의 task 수 무관 — 1개 task plan 도 subagent 패턴.

### Step 4 — failure isolation 그대로 (D6)

기존 wave-parallel skill 의 failure isolation 패턴 그대로:
- spec-reviewer ❌ retry 후 ❌ → 격리 (working tree 변경 폐기 + manifest 삭제)
- 후행 (deps 포함) blocked 마킹 → 다음 wave dispatch 제외
- 다른 task 정상 진행 + commit
- end-of-run consolidator 가 blocked list 노출

### Step 5 — End-of-run consolidator 자동

기존 v1.1.7+ End-of-Run Consolidator 패턴 그대로 — manifest 종합 → 구현 요약 메시지 → footer batch entry append → [log] commit + buffer cleanup.

### Step 6 — finishing-a-development-branch 자동 호출

`js-super:finishing-a-development-branch` skill invoke. 슬림 75줄 본문이 테스트 게이트 + 종료 메시지 자동 노출 (D-T10).

### Step 7 — auto-flow 완료 메시지

```
ℹ️ ✅ 자동 흐름이 끝났습니다. 총 N 개의 commit 이 쌓였고, 멈춘 task 는 <list 또는 "없음"> 입니다.
```

→ 사용자가 catch + 다음 액션 (push / merge / discard) 직접 결정.

## --no-ask 플래그 (v2.5+) — 짧은 reference

본 skill 흐름은 `AskUserQuestion` 호출이 본문에 명시 X (clarifying Q 자체가 prose default). `--no-ask` 플래그 진입 시 추가 분기 없음 — 본문 그대로 도구 호출 0 보장.

단 내부 escalation (BLOCKED 자가복구 실패 / critical 7 재질문 / Other 모호 응답) 에서도 도구 호출 0 보장. 자세한 룰은 `skills/brainstorming/SKILL.md` 의 `### 예외 — \`--no-ask\` 플래그 (v2.5+)` 답습.

## Anti-Patterns

| Wrong | Right |
|---|---|
| `executing-plans` (inline) 호출 | NEVER. D5 — 무조건 wave-parallel subagent. |
| Gate #14 게이트 발화 | NEVER. D5 — auto-flow 가 명시 override. |
| AskUserQuestion 호출 | NEVER. |
| failure 1건 시 종료 | NEVER. D6 — 격리 후 계속. |

## Related Skills

- `js-super-sub-driven` — wave-parallel 본 skill (호출 대상)
- `finishing-a-development-branch` — 끝에 자동 호출
- `scripts/preflight.subagent_task_entry_check` — Entry Guard
- `scripts/auto_flow.find_latest_slug` — slug 추론
