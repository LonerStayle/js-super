# H15 — Step 3 conflict (v2.5.1+ 갱신)

## Scenario

Step 3 (parent 흡수 단계) 에서 main + feature 가 동일 파일 동일 라인 수정 → git default 재귀 머지 자동 시도 → semantic conflict marker 발생 → 사용자 prose 안내 + 수동 해결 → 정상 진행.

v2.0.5 의 AskUserQuestion 게이트는 v2.5.1+ 에서 prose 안내로 대체됨 (도구 호출 X). 안전성 핵심 (`--strategy ours/theirs` 자동 적용 X) 은 그대로 유지.

## Setup

1. `git worktree add ../feature-y -b feature-y`
2. feature-y 에서 `README.md` 라인 1 수정 ("from feature") + commit
3. parent 워크트리에서 같은 `README.md` 라인 1 수정 ("from main") + commit (parent 의 로컬 commit 만, push 불필요)

v2.5.1+ 의 Step 3 가 `git merge $MAIN_BRANCH` (로컬) 패턴이라 origin push 불필요. parent 워크트리의 로컬 commit 만 있으면 됨.

## Trigger

feature-y 에서 `/merge-back-worktree` 호출.

## Expected

1. Guard 통과
2. Step 1 — clean (이미 commit 됨)
3. Step 2 — parent 추론
4. Step 3 — `git merge main` (로컬) → git default 3-way merge 자동 시도 → **충돌 marker 발생** (`<<<<<<< HEAD ... ======= ... >>>>>>>`). 메인 에이전트가 자동 해결 시도 X (`--strategy ours/theirs` 자동 적용 X).
5. **AskUserQuestion 호출 X** (v2.5.1+) — 대신 prose 안내:

   ```
   ❌ Step 3 머지 충돌이 발생했습니다.
      다음 파일에 conflict marker 가 남았습니다: README.md
      1. 충돌 파일을 수동 편집 + git add README.md + git commit 후
      2. 본 skill 을 재호출해주세요.
      (또는 git merge --abort 로 되돌리기)
   ```

6. 사용자가 수동 marker 처리 후 `git add README.md && git commit` → 본 skill 재호출
7. Step 3 재진입 → working tree clean → Step 4 자동 진행
8. Step 4 — merge-base 검증 통과 → merge commit 메시지 → 머지 실행
9. **Step 4.5 신규 (v2.5.1+)** — env 파일 동기화 검토 (본 시나리오에선 env 파일 0건 → "동기화할 환경 파일 없음" 안내 후 자동 진행)
10. Step 5 — 사후 처리 안내 (`/remove-worktree` 호출 안내 + remote 동기화 안내 포함)

## Catch

- 충돌 노출 시점 메인 에이전트가 `git checkout --ours` / `--theirs` / `git merge --strategy` / 임의 Edit 시도 0건 (v2.0.4+ 안전성 핵심 유지)
- **AskUserQuestion 호출 0** (v2.5.1+ 변경 — prose 안내만)
- 사용자가 `git merge --abort` 선택 시 본 skill 재호출 X 가정 (자동 abort 안 함)
- Step 4.5 env 동기화 자동 진행 (대상 0건이면 한 줄 안내, 대상 ≥ 1 면 각 파일 1줄 prose 보고)
- Step 5 종료 메시지에 `/remove-worktree` 호출 안내 1줄 포함 (자동 chain X — 사용자 명시 호출만)
