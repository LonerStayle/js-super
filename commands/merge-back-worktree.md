---
description: 워크트리에서 parent 로 안전 머지 + env 동기화 (worktree-only)
---

Skill 도구로 `js-super:worktree-merge-back` skill 호출 (슬래시 이름과 skill 이름이 다릅니다 — 겹치면 커맨드가 skill 을 가려서 호출이 실패합니다). feature 워크트리 안에서만 작동, main / non-worktree 차단.

v2.5.2+ 자동화:
- 커밋 안 된 변경이 있으면 묻지 않고 자동 커밋 후 진행 (커밋 메시지는 변경 요약 자동 생성). 단 커밋 전 파일 목록 + 메시지를 한 번 알림 — 원치 않는 파일이 보이면 stop 가능 (silent 커밋 안 함)
- 머지 대상은 parent 워크트리의 **로컬** 브랜치 (origin 자동 fetch 안 함 — 사용자가 진입 전 별도 fetch + pull 필요 시 직접)
- 충돌은 git default 재귀 머지 자동 + 실제 conflict marker 발생만 prose 안내 (`--strategy ours/theirs` 자동 적용 절대 X)
- `.env*` 같은 환경 파일은 Step 4.5 에서 LLM 변경 의미 판단 + 각 파일 1줄 prose 보고 + 선택적 cp (silent 절대 X)
- 종료 후 워크트리 + 브랜치 정리는 `/remove-worktree` 단독 호출 (자동 chain 안 함)
