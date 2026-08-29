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

시나리오 1·3·5 에서 AI 제안 후 기본 확정은 `AskUserQuestion` 게이트, 속행 신호를 이미 준 경우엔 즉시 생성 + 결과 이름 알림 (D-5).

## 회귀 catch

```bash
grep -cF "부모브랜치__자식이름" skills/setting-up-worktrees/SKILL.md commands/worktree.md
# expected: 각 1 이상
grep -c "Parse branch names" skills/setting-up-worktrees/SKILL.md
# expected: 0
```
