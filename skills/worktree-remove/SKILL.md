---
name: worktree-remove
description: 커맨드 /worktree-remove 명시 호출로만 진입 — 자유 요청에서 자동 선택 금지. 현재 feature 워크트리를 정리 (git worktree remove + 브랜치 안전 삭제 -d, --force 옵트인 시 -D). worktree-only (main 에서 호출 시 차단).
---

# Worktree Remove (v2.5.1+)

현재 feature 워크트리를 정리 — `git worktree remove` + `git branch -d` 를 한 슬래시로 묶음. `worktree-merge-back` 직후 정리 흐름의 사용자 편의 명령. chain 없음 — 사용자가 `/worktree-remove` 명시 호출.

**Announce at start:** "I'm using the worktree-remove skill — cleanup current worktree + branch (worktree-only)."

## HARD-GATE — Worktree-Only

이 skill 은 **feature worktree 안에서만 사용 가능**. main 워크트리 또는 일반 작업트리에서 호출 시 즉시 차단 (자기 자신 정리 시 데이터 손실 위험).

```bash
CURRENT_PATH=$(pwd)
MAIN_WORKTREE=$(git worktree list --porcelain | awk '/^worktree / {print $2; exit}')
if [ "$CURRENT_PATH" = "$MAIN_WORKTREE" ]; then
  echo "❌ 이 skill 은 worktree 안에서만 사용 가능합니다."
  echo "   현재: $CURRENT_PATH (main 워크트리)"
  echo "   main 워크트리 자체는 /worktree-remove 로 제거할 수 없습니다."
  exit 1
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "❌ git 저장소가 아닙니다."
  exit 1
}
```

## When to Use

- 사용자가 명시적으로 `/worktree-remove` 호출 시에만
- 자동 발동 경로 없음 — `worktree-merge-back` 의 자동 chain X
- 명시 invoke 시점: feature 작업 완료 + `worktree-merge-back` 끝난 후 (또는 워크트리 단독 폐기 의도)

## Process (v2.5.1+ — 게이트 0건, prose 보고 + 자동 진행)

### Step 1 — Working tree 검사 (자동, dirty 시 종료)

```bash
git status --porcelain
```

- 비어있음 → Step 2 자동 진행
- 변경사항 있음 → **즉시 종료 + 안내**:

```
❌ Working tree 에 변경사항이 있습니다.
   먼저 수동으로 commit / stash / discard 한 뒤 본 skill 을 재호출하세요.
   (skill 이 임의 commit 메시지를 생성하지 않습니다 — 사용자 의도 보존)
```

→ 게이트 없음. 사용자가 직접 처리 후 재호출.

### Step 2 — Parent / 현재 워크트리 / 현재 브랜치 캡쳐 (자동)

```bash
MAIN_PATH=$(git worktree list --porcelain | awk '/^worktree / {print $2; exit}')
CURRENT_PATH=$(pwd)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

WT_COUNT=$(git worktree list | wc -l)
if [ "$WT_COUNT" -lt 2 ]; then
  echo "❌ feature 워크트리 없음. 현재 main 워크트리 1개만 존재."
  exit 1
fi
```

MAIN_PATH 는 `git worktree list` 의 첫 항목(main)으로 추론한다. nested / multi-parent 등 비표준 구성이면 이 추론이 부정확할 수 있으니, Step 4 종료 메시지의 경로를 반드시 확인할 것.

> ⚠️ **Step 2–3 의 bash 는 하나의 Bash 호출로 이어서 실행할 것.** 셸 변수(`MAIN_PATH` / `CURRENT_PATH` / `CURRENT_BRANCH`)는 Bash 도구 호출 간 유지되지 않는다 — 별도 호출로 나누면 Step 3 이 빈 값으로 깨진 명령을 실행한다.

### Step 3 — 워크트리 제거 + 브랜치 안전 삭제 (자동)

**safe (-d) default** — 머지 안 된 브랜치는 차단 (데이터 손실 보호):

```bash
# 워크트리 제거 (작업 디렉토리만)
git -C "$MAIN_PATH" worktree remove "$CURRENT_PATH"

# 브랜치 안전 삭제 (머지 안 됐으면 차단)
git -C "$MAIN_PATH" branch -d "$CURRENT_BRANCH"
```

브랜치 삭제 실패 시 prose 안내:

```
⚠️ 브랜치 "$CURRENT_BRANCH" 가 parent 로 머지되지 않아 안전 삭제(-d) 차단되었습니다.
   1. 머지 후 재호출 — /worktree-merge-back 먼저 실행 후 /worktree-remove
   2. 또는 강제 삭제 — /worktree-remove --force 명시 호출 (데이터 손실 위험)
   (워크트리는 이미 제거됨 — Step 4 안내 그대로 진행)
```

**`--force` 옵트인 분기 (D-6)** — 사용자가 `/worktree-remove --force` 명시 시에만 진입:

```bash
git -C "$MAIN_PATH" worktree remove --force "$CURRENT_PATH"
git -C "$MAIN_PATH" branch -D "$CURRENT_BRANCH"
```

- safe (-d) default — 머지 안 된 브랜치는 차단 (head 변경 보호)
- `--force` 옵트인 — 머지 안 된 브랜치도 강제 삭제(`-D`) + gitignored 빌드 산출물/lock 때문에 `git worktree remove` 가 막히면 `--force` 로 진행. **단 미커밋 변경사항(tracked/untracked 불문 — `git status --porcelain` 이 non-empty)은 `--force` 여도 Step 1 에서 종료** (데이터 손실 방지 — 사용자 명시 의사만)

### Step 4 — 종료 메시지 (자동, 게이트 X)

워크트리 + 브랜치 정리 완료 후 종료 메시지. **R-4 핵심**: 현재 cwd 가 사라졌으므로 사용자가 어디로 이동해야 하는지 안내.

```
✅ 워크트리 정리 완료.
   - 제거된 워크트리: <CURRENT_PATH>
   - 삭제된 브랜치:   <CURRENT_BRANCH>

⚠️ 현재 디렉토리가 사라졌습니다. parent 워크트리로 이동해주세요:
   cd <MAIN_PATH>
```

→ skill 내부에서 자동 `cd` 하지 않음 (사용자 shell 영향 X). 사용자가 직접 명령 실행.

## Anti-Patterns

| Wrong | Right |
|---|---|
| main 워크트리에서 invoke 후 그대로 진행 | HARD-GATE 차단. main 자체는 본 skill 으로 제거 X (자기 자신 정리 위험). |
| `--force` 자동 적용 (사용자 명시 없이) | NEVER. safe (-d) default. 사용자가 명시 `--force` 플래그 시만. |
| `cd <parent-path> && git ...` 패턴 | `git -C <parent-path>` 사용. cwd 변경 X. |
| skill 내부 자동 `cd` 실행 | NEVER. 사용자 shell 영향 X. 종료 메시지로 안내만. |
| Step 1 dirty 시 임의 commit / discard | NEVER. 즉시 종료 + 사용자 재호출 안내. |
| worktree-merge-back 자동 chain (Step 5 끝나면 본 skill 자동 호출) | NEVER. 사용자 명시 호출만. 안전성 핵심. |
| 브랜치 삭제 실패 시 즉시 `--force` 재시도 | NEVER. 사용자 prose 안내 후 사용자가 명시 `--force` 호출. |

## Why v2.5.1

- v2.0.5 의 `worktree-merge-back` Step 5 종료 메시지에 `git worktree remove` + `git branch -d` 안내만 있어서, 사용자가 매번 수동 입력 — 마찰.
- 한 슬래시 명령으로 묶어서 사용자 편의 ↑.
- chain X — 사용자가 명시 의사 표현한 시점에만 destructive 작업 진행. 데이터 손실 위험 최소.
- safe (-d) default + `--force` 옵트인 — 머지 안 된 브랜치 보호. 사용자 강력 의사 표현 시만 force.

## Related Skills

- `worktree-merge-back` — 머지 페어. 종료 메시지에 본 skill 호출 안내 (chain X)
- `setting-up-worktrees` — 워크트리 생성 페어 (영향 0)
- `finishing-a-development-branch` — 테스트 게이트 + 종료 메시지 (자동 호출 X)
