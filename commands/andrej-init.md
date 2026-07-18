---
description: "현재 프로젝트 루트에 Andrej Karpathy 스타일 행동 지침 CLAUDE.md 를 원본 그대로 생성."
argument-hint: ""
disable-model-invocation: true
---

# Andrej Init (행동 지침 CLAUDE.md 생성)

현재 프로젝트 루트에 LLM 코딩 실수를 줄이는 행동 지침 `CLAUDE.md` 를 생성합니다. 아래 § 3 의 내용을 **한 글자도 바꾸지 않고 그대로** 씁니다 (번역 / 요약 / 재구조화 절대 금지).

## 1. 대상 경로 확정

- 대상 파일 = `<project-root>/CLAUDE.md` (현재 작업 디렉토리 기준 프로젝트 루트)

## 2. 기존 파일 검사 (덮어쓰기 게이트)

`CLAUDE.md` 가 이미 존재하면 **조용히 덮어쓰지 않습니다**. AskUserQuestion 도구로 다음 중 하나를 선택받은 뒤 진행:

- **끝에 추가** — 기존 내용 유지 + 빈 줄 구분 후 § 3 내용을 끝에 append
- **덮어쓰기** — 기존 내용을 § 3 내용으로 교체 (교체 전 기존 파일을 Read 해서 `CLAUDE.md.bak-<YYYYMMDDHHMMSS>` 로 백업 Write)
- **중단** — 아무것도 변경하지 않음

파일이 없으면 게이트 없이 바로 § 3 내용으로 Write 합니다.

## 3. CLAUDE.md 내용 (원본 그대로 보존 — 수정 금지)

아래 블록 내부를 byte 그대로 씁니다:

````markdown
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
````

## 4. 완료 보고

Write 후 사용자에게 한국어로 짧게 보고:

- 생성 시: "프로젝트 루트에 CLAUDE.md 를 만들었습니다. 다음 세션부터 이 지침이 자동으로 적용됩니다."
- 추가 시: "기존 CLAUDE.md 끝에 행동 지침을 추가했습니다."
- 덮어쓰기 시: "기존 CLAUDE.md 를 백업 (`CLAUDE.md.bak-<timestamp>`) 하고 새 지침으로 교체했습니다."
