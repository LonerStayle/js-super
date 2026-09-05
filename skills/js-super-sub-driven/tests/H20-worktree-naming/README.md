# H20 — worktree naming (재분기 `부모__자식` 제안)

`setting-up-worktrees` Step 1 (이름 해석) 의 수동 dogfood 시나리오. 판별 기준은 브랜치 비교 (`BASE_BRANCH` ≠ `MAIN_BRANCH` = 재분기) — tech-design D-2.

## 시나리오

| # | 상황 | 입력 | 기대 |
|---|---|---|---|
| 1 | `feat/scheduled-tasks` 워크트리 안 | "알림 기능 워크트리" (설명만) | `feat/scheduled-tasks__<자식이름>` 형식 제안. 자식 부분에 `__`/`/` 없음 |
| 2 | 아무 위치 | `/worktree hotfix-x` (이름 명시) | `hotfix-x` 그대로 생성 — 제안 · 개명 없음 |
| 3 | `a__b` 워크트리 안 | 설명만 | `a__b__<자식이름>` — 누적 |
| 4 | 메인 워크트리, 메인 브랜치 | 설명만 | 제안 이름에 `__` 없음 (접두어 미부착). `/` 는 저장소 관례가 슬래시 접두어일 때만 허용 — 본 저장소 관례는 평평한 이름이라 없음이 기대. 관례 부합은 사람 눈 판정 보조 |
| 5 | detached HEAD | 설명만 | 접두어 생략 + 안내 한 줄 |
| 6 | 임의 워크트리 안 | 설명만 | Step 0 의 도구 결과에 `REBRANCH=yes (접두어: <BASE_BRANCH>__)` 줄이 **먼저** 찍히고, 제안 이름의 접두어가 그 줄의 문자열과 일치. Step 0 을 출력 없이 (변수 대입만) 돌린 뒤 판별한 흔적이 있으면 실패 |

시나리오 1·3·5 에서 AI 제안 후 기본 확정은 `AskUserQuestion` 게이트, 속행 신호를 이미 준 경우엔 즉시 생성 + 결과 이름 알림 (D-5).

시나리오 6 은 2026-09-05 사용자 catch 의 재현이다. Step 0 이 값을 출력하지 않던 본문에서는 재분기 판별의 근거가 대화 기록에 없었고, 값을 못 본 모델이 detached 갈래 (접두어 생략) 나 메인 기준 이름으로 빠져 접두어가 간헐적으로 누락됐다.

## 회귀 catch

```bash
grep -cF "부모브랜치__자식이름" skills/setting-up-worktrees/SKILL.md commands/worktree.md
# expected: 각 1 이상
grep -c "Parse branch names" skills/setting-up-worktrees/SKILL.md
# expected: 0
awk '/\*\*Step 0/,/\*\*Step 1/' skills/setting-up-worktrees/SKILL.md | grep -c 'echo "REBRANCH='
# expected: 2
grep -cF "REBRANCH=" skills/setting-up-worktrees/SKILL.md
# expected: >= 8
```
