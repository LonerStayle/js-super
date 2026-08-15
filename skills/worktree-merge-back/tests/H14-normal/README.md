# H14 — Normal merge-back

## Scenario

Feature 워크트리 안 + working tree clean + Step 3 충돌 없음 → 1회 완주.

## Setup

1. main 워크트리에서 `git worktree add ../feature-x -b feature-x` (또는 `/worktree feature-x`)
2. feature-x 워크트리 진입 후 일부 파일 수정 + commit (예: README 한 줄 추가)
3. main 워크트리에서 다른 영역 파일 수정 + commit (충돌 안 나는 파일)

## Trigger

feature-x 워크트리에서 `/merge-back-worktree` 호출.

## Expected

1. Guard 통과 (feature worktree 확인)
2. Step 1 — working tree clean → 자동 Step 2
3. Step 2 — parent 추론 성공 (main 워크트리 path + branch 노출)
4. Step 3 — `git fetch origin` + `git merge origin/main` 충돌 0 → 자동 Step 4
5. Step 4 — merge commit 메시지 AskUserQuestion → 기본 선택 → `git -C <main-path> merge --no-ff feature-x` 실행
6. Step 5 — 사후 처리 3건 AskUserQuestion 묶음 → 모두 no → skill 종료

## Catch

- Step 3 자동 충돌 해결 시도 0건
- Step 4 후 cwd 여전히 feature-x 워크트리
- main 워크트리에 머지 commit 1개 생성
- 사후 처리 default no 적용
