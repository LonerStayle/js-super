# H16 — Worktree-only guard

## Scenario

main 워크트리 (또는 git 저장소 아닌 디렉토리) 에서 invoke → HARD-GATE 차단.

## Setup (variant A: main 워크트리)

main 워크트리에서 `/merge-back-worktree` 호출.

## Setup (variant B: non-git directory)

`/tmp` 등 git 저장소 아닌 곳에서 호출.

## Expected (variant A)

```
❌ 이 skill 은 worktree 안에서만 사용 가능합니다.
   현재: /Users/.../js-super (main 워크트리)
   먼저 /worktree <feature-name> 으로 워크트리 진입 후 재호출하세요.
```

skill 즉시 종료. Step 1 이후 진행 X.

## Expected (variant B)

```
❌ git 저장소가 아닙니다.
```

skill 즉시 종료.

## Catch

- Guard 차단 메시지 노출
- 다음 단계 (Step 1~5) 진행 0건
- 사용자에게 안내 후 skill 종료 — 추가 AskUserQuestion 발화 0건
- main 워크트리 git state 변경 0건 (read-only)
