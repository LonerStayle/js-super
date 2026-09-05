---
name: finishing-a-development-branch
description: Use when implementation is complete and tests pass. Runs the test gate one final time and emits a single termination message; user manually decides merge / PR / keep / discard. (v1.1.14 슬림화 — AskUserQuestion 게이트 + boilerplate 제거.) 큰 작업(에픽)에 속한 피처면 Step 3 에서 `epic-close` 로 위임해 다음 파트 워크트리와 인수인계를 잇는다 — 에픽이 없으면 그 단계는 무출력.
---

# Finishing a Development Branch (v1.1.14 slim)

implementation 완료 + 모든 테스트 통과 시점에 호출. 1인 개발자가 다음 행동 (merge / PR / keep / discard) 을 이미 알고 있다는 가정 하에, 추가 게이트는 두지 않고 **테스트 자동 실행 안전망 + 종료 메시지** 만 제공.

**Announce at start:** "I'm using the finishing-a-development-branch skill to verify tests then emit a termination summary."

## When to Use

- `executing-plans` / `js-super-sub-driven` 가 모든 task 완료 후 자동 호출
- 사용자가 명시적으로 마무리 단계 진입 시 호출

## Process

### Step 1 — 테스트 자동 실행 (필수 안전망)

자동으로 프로젝트 표준 테스트 명령 실행:

```bash
# Python (이 저장소 기본)
source .venv/bin/activate && pytest -v

# 다른 stack 의 경우 README / package.json scripts 확인
```

- 모든 테스트 PASS → Step 2 진행
- FAIL 1건 이상 → **즉시 STOP**. 실패한 테스트 출력을 사용자에게 노출 + 한 줄 안내: "❌ 테스트 실패. 마무리 진행 안 함. 실패 원인 확인 후 다시 호출."

이 단계는 **유일한 자동 게이트**. 깨진 코드가 main / PR 로 흘러 들어가는 것 방지.

### Step 2 — 완료 메시지 노출 (한 메시지, 게이트 X)

```
✅ 모든 task 완료 + 테스트 통과.
   - 변경 commit: <SHA list>
   - RISK 트리거: <카테고리 카운트>
   - 누락/초과: <list 또는 "없음">

마무리하세요. (예: git checkout main && git merge <branch>, 또는 PR 생성, 또는 그대로 두기)
```

→ AskUserQuestion 게이트 없음. 사용자가 직접 git/gh 명령 실행. boilerplate 자동 생성 X.

### Step 3 — 큰 작업 파트 마무리 (에픽이 있을 때만)

Step 2 의 메시지를 낸 뒤 `js-super:epic-close` 스킬을 Skill 도구로 부른다. 진행 중인 큰 작업이 없거나 이번 피처의 요구사항 문서에 소속 표식이 없으면 그 스킬은 아무 출력 없이 돌아온다 — 단발성 피처의 종료 메시지는 지금과 똑같다. 에픽이 있으면 그 스킬이 에픽 파일 갱신, 다음 파트 선택, 워크트리 생성, 자식 세션 인수인계까지 이어간다.

## Worktree Cleanup (manual)

워크트리 정리는 자동 안 함 (마무리 시점이라고 자동 정리하면 사용자가 "그대로 두기" 의도일 때 자료 손실 가능). 사용자가 직접 처리:

```bash
git worktree remove <path>
```

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 4-option 게이트 추가 | 게이트 X. 1인 개발자 마찰 회피. |
| base branch 자동 추정 | 사용자가 본인 브랜치 알고 있음. 추정 시간 낭비. |
| git/gh boilerplate 자동 생성 | 종료 메시지 한 줄 안내만. 명령 직접 실행. |
| Step 1 테스트 실패 시 무시 | NEVER. 유일한 안전망. STOP 강제. |

## Why slim (v1.1.14)

- 1인 개발 철학: 사전 verifying-spec + TDD + RISK + 변경이력으로 안전성 분산. 종료 게이트는 중복.
- v1.1.9~12 게이트 합리화 흐름의 자연스러운 연장 (partial 제거 / fix→no / #12 복원 같은 마찰 정리).
- discard 안전망 의도적 트레이드오프: 사용자가 직접 `git branch -D` 시 confirm 없음. 1인 개발자는 git 동작 알고 있음.

## Related Skills

- `executing-plans` — 인라인 모드 종료 시 호출
- `js-super-sub-driven` — 서브에이전트 모드 End-of-Run consolidator 끝 호출
- `setting-up-worktrees` — 워크트리 생성 페어 (cleanup 은 manual)
