# H17 — Dirty working tree 자동 커밋 (v2.5.2+)

## Scenario

Feature 워크트리 안 + working tree 에 커밋 안 된 변경 존재 → Step 1 이 즉시 종료하지 않고 자동 커밋 후 머지백 진행.

## Setup

1. main 워크트리에서 `git worktree add ../feature-y -b feature-y` (또는 `/worktree feature-y`)
2. feature-y 워크트리 진입 후 파일 수정/추가 (예: `src/foo.js` 신규 + `README.md` 수정) — **commit 하지 않음** (dirty 상태 유지)

## Trigger

feature-y 워크트리에서 `/merge-back-worktree` 호출.

## Expected

1. Guard 통과 (feature worktree 확인)
2. Step 1 — `git status --porcelain` 이 dirty 감지 → **즉시 종료 X**
3. `git diff HEAD` 로 변경 파악 → 변경 요약 한 줄 커밋 메시지 자동 생성 (conventional-commit 스타일, 고정 문구 X)
4. 커밋 전 prose 알림 노출 — 파일 목록 (파일명 + M/A/D 상태) + 생성된 메시지 + "원치 않는 파일이 보이면 지금 stop 하세요"
5. `git add -A` + `git commit -m "<생성 메시지>"` 실행 (진행 여부 재질문 0건)
6. Step 2 이후 정상 흐름 진입

## Catch

- Step 1 dirty 시 즉시 종료 메시지 노출 0건 (v2.5.1 옛 동작 회귀 catch)
- 커밋 전 파일 목록 + 메시지 prose 알림 1건 노출 (silent 커밋 catch)
- 커밋 메시지가 고정 문구 아님 (변경 요약 반영)
- 진행 여부 AskUserQuestion / prose 재질문 0건 (묻지 않고 자동 진행)
- feature-y 워크트리에 자동 커밋 1개 생성 후 Step 2 진행
