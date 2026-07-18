---
description: upstream superpowers 원본 executing-plans 흐름. /og-write-plan 으로 만든 implementation plan 을 task-by-task 로 실행. /og-execute-plan 명시 호출 전용.
disable-model-invocation: true
---

# /og-execute-plan — 원본 executing-plans (upstream superpowers 5.0.7)

이 커맨드는 **upstream superpowers 5.0.7 의 원본 executing-plans 흐름**을 그대로 재현합니다. 아래 절차를 따르세요.

전제: `/og-write-plan` 으로 작성된 plan 이 `docs/superpowers/plans/` 아래에 존재.

## Overview

Load plan, review critically, execute all tasks, report when complete.

**시작 안내:** "og 원본 executing-plans 흐름으로 이 plan 을 구현하겠습니다."

**Note:** Tell your human partner that Superpowers works much better with access to subagents. The quality of its work will be significantly higher if run on a platform with subagent support (such as Claude Code or Codex). If subagents are available, use superpowers:subagent-driven-development instead of this flow (untouched-upstream, no og- variant needed — js-super did not modify it).

## Checklist

- [ ] Step 1 — Plan 로드 + 비판적 검토 (Load and Review Plan)
- [ ] Step 2 — Task 실행 (Execute Tasks)
- [ ] Step 3 — Complete Development

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **superpowers:using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **`/og-write-plan`** - Creates the plan this flow executes
- **superpowers:finishing-a-development-branch** - Complete development after all tasks

---

## js-super 정식 흐름과의 차이

| 항목 | `/execute-plan` (js-super 확장) | `/og-execute-plan` (upstream 원본) |
|---|---|---|
| 모드 분기 | Inline (executing-plans) / Subagent (js-super-sub-driven) 양자택일 | Inline 단일 (Subagent 원하면 `subagent-driven-development` 직접 호출) |
| 실행 모드 | git-fast / memory-fallback (commit_policy 기준) | upstream 단일 모드 — 그냥 plan 따라 실행 |
| 변경이력 [코드-수정] entry 자동 기록 | 있음 (task당 1번 batched) | 없음 |
| risk-annotation 3-checklist + RISK 주석 | 자동 | 없음 |
| 코드 주석 plan-측 식별자 금지 룰 | 적용 | 적용 안 됨 |

## Subagent 모드를 원할 때

`og-` 흐름 안에서 subagent 실행을 원한다면 `subagent-driven-development` 를 직접 호출하세요. js-super 가 손대지 않은 untouched-upstream 그대로라 별도의 og- 사본은 없습니다.

## 주의

`/og-*` 흐름과 js-super 정식 흐름을 한 피처에서 섞지 마세요.
