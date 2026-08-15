---
description: 현재 워크트리 정리 — 워크트리 제거 + 브랜치 안전 삭제 (worktree-only)
---

Skill 도구로 `js-super:worktree-remove` skill 호출 (슬래시 이름과 skill 이름이 다릅니다 — 겹치면 커맨드가 skill 을 가려서 호출이 실패합니다). feature 워크트리 안에서만 작동, main / non-worktree 차단.

v2.5.1+ 신규 슬래시 명령:
- 한 슬래시로 `git worktree remove` + `git branch -d` 묶음
- safe (-d) default — 머지 안 된 브랜치는 차단 (데이터 손실 보호)
- `--force` 옵트인 — 머지 안 된 브랜치도 강제 삭제 (데이터 손실 위험, 사용자 명시 의사만)
- chain X — `worktree-merge-back` 와 별개. 사용자 명시 호출만

사용 예시:
- `/remove-worktree` — safe 삭제 (default, 머지 안 됐으면 안내 후 종료)
- `/remove-worktree --force` — 머지 안 된 브랜치도 강제 삭제(`-D`). (미커밋 변경사항이 있으면 `--force` 여도 Step 1 에서 종료됩니다 — 먼저 commit/stash/discard 후 재호출.)
