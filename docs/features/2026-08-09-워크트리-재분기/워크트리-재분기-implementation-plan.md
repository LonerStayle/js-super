---
commit_policy: per-task
---

# 워크트리-재분기 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 워크트리 안에서 `/worktree` 를 호출해도 중첩 없이 메인 루트 `.worktrees/` 아래에, 호출 위치 HEAD 를 시작점으로 새 워크트리를 자동 생성한다 (기존 메인 루트 호출 동작은 그대로 보존).

**Architecture:** `setting-up-worktrees` 스킬의 루트 해석을 이원화한다 — 배치 기준은 `git worktree list` 첫 entry (메인 루트), 분기 기준은 호출 위치의 HEAD. `worktree-memory-symlink` 훅도 같은 해석으로 교체해 워크트리 안 호출 시 심링크가 조용히 생략되던 기존 버그를 수정한다.

**Tech Stack:** 마크다운 skill/command 본문 + bash 훅 + bash E2E 테스트

**Spec inputs:**
- 워크트리-재분기-requirements.md — FR-1 중첩 방지 / FR-2 HEAD 분기 / FR-3 dirty 게이트 / FR-4 보고 확장 / FR-5 기존 동작 보존 / FR-6 E2E / FR-7 훅·스크립트 검토
- 워크트리-재분기-tech-design.md — D-1 (worktree list 첫 entry) / D-2 (호출 cwd HEAD) / D-3 (dirty 게이트) / D-4 (훅 수정) / D-5 (add 프리픽스 보존) / D-6 (.gitignore 메인 루트) / D-7 (env 소스 호출 위치 우선) / D-8 (스택 안내)

> **슬림 plan 관례** (v2.5.1 선례): 대상이 한국어 skill 본문 + bash 훅이라 `**원본**` 라벨 블록은 의도적 생략 (내부 코드 펜스가 plan_byte_check 파서와 충돌). 실행은 인라인 모드 — 메인이 파일을 직접 Read 후 Edit. 각 task 의 "수정 내용" 블록이 최종 상태의 완전한 코드다.

---

## 1. 단계별 작업

### Task 1: 훅 ROOT 해석 교체 (워크트리 안 호출 시 심링크 생략 버그 수정)

**Files:**
- Modify: `hooks/worktree-memory-symlink:58-66`

**Model**: sonnet

- [ ] **Step 1: ROOT 해석을 메인 워크트리로 교체**

`hooks/worktree-memory-symlink` 의 58-66행 (`# We're committed; resolve repo root from cwd.` 부터 `fi` 까지) 을 다음으로 교체:

```bash
# We're committed; resolve the MAIN worktree root (v2.9.0+). `git worktree
# list` prints the main worktree first, so `git worktree add` issued from
# inside a linked worktree still resolves to the main repo root — matching
# the skill's placement rule (<main-root>/.worktrees/).
CWD="$(extract '.cwd')"
[ -n "$CWD" ] || CWD="$PWD"

ROOT="$(git -C "$CWD" worktree list --porcelain 2>/dev/null | head -1 | sed 's/^worktree //' || true)"
if [ -z "$ROOT" ]; then
    echo "[worktree-memory-symlink] could not resolve main worktree root from cwd=$CWD" >&2
    exit 0
fi
```

- [ ] **Step 2: 문법 + 회귀 grep 검증**

Run: `bash -n hooks/worktree-memory-symlink && grep -c "show-toplevel" hooks/worktree-memory-symlink; grep -c "worktree list --porcelain" hooks/worktree-memory-symlink`
Expected: 문법 에러 없음, `show-toplevel` 0건, `worktree list --porcelain` 1건 이상

- [ ] **Step 3: Commit**

```bash
git add hooks/worktree-memory-symlink
git commit -m "fix(hook): 워크트리 안 호출 시 심링크 생략 버그 — ROOT 를 메인 워크트리로 해석"
```

### Task 2: SKILL.md Step 0 루트 해석 이원화 + Defaults 표

**Files:**
- Modify: `skills/setting-up-worktrees/SKILL.md:26-34` (Defaults 표), `:69-76` (Step 0)

**Model**: sonnet

- [ ] **Step 1: Step 0 을 루트 해석 이원화 버전으로 교체**

기존 Step 0 (`**Step 0 — Verify git context**` 섹션 전체) 을 다음으로 교체:

````markdown
**Step 0 — Verify git context + 루트 해석 이원화 (v2.9.0+)**

```bash
git rev-parse --is-inside-work-tree   # must print "true"

# 배치 기준 = 메인 저장소 루트. git worktree list 는 메인 워크트리를 항상 첫 줄에
# 출력하므로, 워크트리 안에서 호출해도 메인 루트가 잡힌다 (중첩 생성 방지).
MAIN_ROOT=$(git worktree list --porcelain | head -1 | sed 's/^worktree //')

# 분기 기준 = 호출 위치의 현재 HEAD (워크트리 A 안에서 호출하면 A 의 커밋)
BASE_SHA=$(git rev-parse HEAD)
BASE_BRANCH=$(git branch --show-current)
MAIN_BRANCH=$(git -C "$MAIN_ROOT" branch --show-current)
```

If not in a repo, abort with: "현재 디렉터리가 git repo 아닙니다. `git init` 후 다시 호출해주세요."

호출 위치가 워크트리 안이어도 (`git rev-parse --show-toplevel` ≠ `$MAIN_ROOT`) 새 워크트리는 항상 **메인 루트의 `.worktrees/`** 아래에 생성된다 (중첩 금지). 사용자가 위치를 신경 쓰거나 별도 지시할 필요 없다 — 자동 판정.
````

- [ ] **Step 2: Defaults 표의 두 행 교체 + 한 행 추가**

| Knob | Default behavior |
|---|---|
| Worktree root | `<메인 저장소 루트>/.worktrees/` — 워크트리 안에서 호출해도 메인 루트 기준, 중첩 생성 금지 (override only if user explicitly asks) |
| Branch creation | If branch missing → `-b <name>` from **호출 위치 HEAD** (워크트리 안이면 그 워크트리의 커밋이 시작점; 사용자가 베이스 명시 시 그 브랜치). Existing local → use as-is. Remote-only → `-B <name> origin/<name>` |
| Dirty 워크트리에서 분기 (신규) | Step 3.5 게이트 — "WIP 커밋 후 분기" / "마지막 커밋 시점 기준 분기" 선택. stash 금지 |

- [ ] **Step 3: 검증 grep**

Run: `grep -c "MAIN_ROOT" skills/setting-up-worktrees/SKILL.md; grep -n "ROOT=\$(git rev-parse --show-toplevel)" skills/setting-up-worktrees/SKILL.md`
Expected: `MAIN_ROOT` 다수 매치, 옛 `ROOT=$(git rev-parse --show-toplevel)` 0건

- [ ] **Step 4: Commit**

```bash
git add skills/setting-up-worktrees/SKILL.md
git commit -m "feat(worktree): Step 0 루트 해석 이원화 — 배치=메인 루트 / 분기=호출 위치 HEAD"
```

### Task 3: SKILL.md Step 3 메인 루트 기준 + Step 3.5 dirty 게이트 신설

**Files:**
- Modify: `skills/setting-up-worktrees/SKILL.md:107-115` (Step 3) + 직후 Step 3.5 삽입

**Model**: sonnet

- [ ] **Step 1: Step 3 을 메인 루트 기준으로 교체하고 Step 3.5 를 신설**

기존 Step 3 섹션을 다음으로 교체 (Step 3.5 는 신규 삽입):

````markdown
**Step 3 — Ensure `.worktrees/` exists and is gitignored (메인 루트 기준)**

```bash
mkdir -p "$MAIN_ROOT/.worktrees"

if ! grep -qE '^\.worktrees/?$' "$MAIN_ROOT/.gitignore" 2>/dev/null; then
    echo ".worktrees/" >> "$MAIN_ROOT/.gitignore"
fi
```

워크트리 안에서 호출했고 위 append 가 실제로 일어났다면 한 줄 알림: "ℹ️ 메인 루트 `.gitignore` 에 `.worktrees/` 를 추가했습니다 (메인 워크트리에 커밋 안 된 변경 1건이 생겼습니다)."

**Step 3.5 — 분기 전 dirty 확인 (v2.9.0+)**

호출 위치에 커밋 안 된 변경이 있는지 확인한다:

```bash
git status --porcelain   # 출력이 있으면 dirty
```

dirty 면 `AskUserQuestion` 으로 선택받는다 (stash 로 변경을 넘기는 방식 금지):

- **"WIP 커밋 후 분기"** — `git add -A` 후 커밋. 커밋 메시지는 `git diff HEAD` 요약으로 자동 생성 (고정 문구 금지). 새 브랜치가 WIP 내용을 포함한다.
- **"마지막 커밋 시점 기준 분기"** — 커밋하지 않고 현재 HEAD 커밋에서만 분기. 커밋 안 된 변경은 호출 위치 워크트리에 그대로 남는다.

clean 이면 질문 없이 다음 Step 으로 진행.
````

- [ ] **Step 2: 검증 grep**

Run: `grep -F "Step 3.5" skills/setting-up-worktrees/SKILL.md | head -2; grep -F "stash" skills/setting-up-worktrees/SKILL.md`
Expected: `Step 3.5` 1건 이상, stash 금지 문구 존재

- [ ] **Step 3: Commit**

```bash
git add skills/setting-up-worktrees/SKILL.md
git commit -m "feat(worktree): Step 3.5 dirty 게이트 신설 + Step 3 메인 루트 기준"
```

### Task 4: SKILL.md Step 4 개별 add 호출 재구성 (훅 프리픽스 보존)

**Files:**
- Modify: `skills/setting-up-worktrees/SKILL.md:117-140` (Step 4) + Process dot 다이어그램 노드 동기

**Model**: sonnet

- [ ] **Step 1: Step 4 를 브랜치별 개별 Bash 호출 방식으로 교체**

기존 Step 4 (for-loop 한 방) 를 다음으로 교체:

````markdown
**Step 4 — For each branch, create or attach the worktree (개별 Bash 호출, v2.9.0+)**

`worktree-memory-symlink` 훅은 Bash 명령 문자열이 `git worktree add ` 로 **시작**할 때만 발화한다. 브랜치·디렉토리 존재 판정과 변수 계산은 별도 선행 Bash 호출로 끝내고, 워크트리 생성은 브랜치마다 **`git worktree add` 로 시작하는 개별 Bash 호출** 로 실행한다 (for-loop 한 방에 묶으면 훅이 발화하지 않는다):

```bash
# 선행 판정 (별도 Bash 호출):
#   [ -d "$MAIN_ROOT/.worktrees/<BR>" ]                    # 이미 존재 → skip + notice (덮어쓰기 X)
#   git show-ref --verify --quiet refs/heads/<BR>          # 로컬 브랜치 존재?
#   git show-ref --verify --quiet refs/remotes/origin/<BR> # remote 브랜치 존재?

# 생성 — 경로·브랜치명을 실제 값으로 치환한 개별 호출 (아래 중 케이스에 맞는 1줄):
git worktree add <MAIN_ROOT>/.worktrees/<BR> <BR>                  # 로컬 브랜치 존재 → attach
git worktree add -B <BR> <MAIN_ROOT>/.worktrees/<BR> origin/<BR>   # remote-only
git worktree add -b <BR> <MAIN_ROOT>/.worktrees/<BR> HEAD          # 신규 (분기 기준 = 호출 위치 HEAD)
git worktree add -b <BR> <MAIN_ROOT>/.worktrees/<BR> <BASE>        # 사용자가 베이스 명시 시 (예: "dev 기준으로")
```

신규 브랜치 생성 직전 `BASE_SHA` / `BASE_BRANCH` (Step 0 캡처값) 를 그대로 두고, 생성 후 Step 6 보고에 사용한다.
````

- [ ] **Step 2: Process dot 다이어그램의 add 노드 라벨 동기** — `"git worktree add <path> <branch>"` / `"git worktree add -b <branch> <path>"` 노드는 유지하되, `-b` 노드 라벨을 `"git worktree add -b <branch> <path> HEAD"` 로 갱신

- [ ] **Step 3: 검증 grep**

Run: `grep -F "개별 Bash 호출" skills/setting-up-worktrees/SKILL.md; grep -nF "for BR in" skills/setting-up-worktrees/SKILL.md`
Expected: `개별 Bash 호출` 1건 이상. `for BR in` 은 Step 4 에서 제거 (Step 5 복사 루프에는 남아 있어도 됨 — worktree add 가 포함되지 않은 루프만 허용)

- [ ] **Step 4: Commit**

```bash
git add skills/setting-up-worktrees/SKILL.md
git commit -m "feat(worktree): Step 4 브랜치별 개별 add 호출 — 훅 프리픽스 발화 보장"
```

### Task 5: SKILL.md Step 5 복사 소스 + Step 6 보고 확장 + description·Anti-Patterns 갱신

**Files:**
- Modify: `skills/setting-up-worktrees/SKILL.md:3` (frontmatter description), `:142-153` (Step 5), `:166-182` (Step 6), Anti-Patterns 표, Acceptance

**Model**: sonnet

- [ ] **Step 1: Step 5 복사 소스를 호출 위치 우선으로 교체**

````markdown
**Step 5 — Copy ALL detected env files into each worktree (no prompts)**

복사 소스는 **호출 위치 워크트리 루트 우선** (base 워크트리에서 갱신된 env 가 최신일 가능성이 높다), 후보 파일이 호출 위치에 없으면 메인 루트에서 fallback:

```bash
SRC_ROOT=$(git rev-parse --show-toplevel)   # 호출 위치 루트 (메인 루트에서 호출하면 = MAIN_ROOT)
for BR in "${BRANCHES[@]}"; do
    WT_PATH="$MAIN_ROOT/.worktrees/$BR"
    [ -d "$WT_PATH" ] || continue   # was skipped earlier
    for EF in "${ENV_FILES[@]}"; do
        if [ -f "$SRC_ROOT/$EF" ]; then
            cp "$SRC_ROOT/$EF" "$WT_PATH/$EF" && echo "📋 $BR ← $EF 복사 완료"
        elif [ -f "$MAIN_ROOT/$EF" ]; then
            cp "$MAIN_ROOT/$EF" "$WT_PATH/$EF" && echo "📋 $BR ← $EF 복사 완료 (메인 루트 fallback)"
        fi
    done
done
```
````

- [ ] **Step 2: Step 6 보고에 분기 기준 + 스택 안내 추가**

Step 6 요약 템플릿에 다음 두 요소를 추가:

````markdown
각 워크트리 항목 밑에 분기 기준 한 줄:

```
- <새브랜치>   → .worktrees/<새브랜치>   (.env ✓ | 🔗 memory)
  분기 기준: <BASE_BRANCH> @ <BASE_SHA 앞 7자리>
```

분기 베이스가 메인 브랜치가 아니면 (`BASE_BRANCH` ≠ `MAIN_BRANCH`) 다음 주의를 함께 출력:

```
ℹ️ 머지 경로가 스택 구조입니다: <새브랜치> → <BASE_BRANCH> → <MAIN_BRANCH>
   <BASE_BRANCH> 가 <MAIN_BRANCH> 에 리베이스되면 <새브랜치> 도 리베이스가 필요합니다.
```
````

- [ ] **Step 3: frontmatter description 에 재분기 문구 추가** — 기존 description 끝에 "Invoked from inside a worktree, it places the new worktree under the MAIN repo root's .worktrees/ (no nesting) and branches from the invoking worktree's current HEAD." 를 덧붙인다

- [ ] **Step 4: Anti-Patterns 표에 3행 추가**

| Wrong | Right |
|---|---|
| 워크트리 안에서 호출 시 호출 위치 루트 아래 `.worktrees/` 중첩 생성 | 항상 `MAIN_ROOT` (worktree list 첫 entry) 기준 배치 |
| for-loop 한 방에 `git worktree add` 묶기 | 훅 프리픽스 미매치 → 심링크 미생성. 브랜치별 개별 Bash 호출 |
| dirty 워크트리에서 말없이 분기 (또는 stash 로 넘기기) | Step 3.5 게이트 — WIP 커밋 / 커밋 시점 분기 선택. stash 금지 |

- [ ] **Step 5: Acceptance 에 3항 추가** — (8) 워크트리 안 호출 시 중첩 생성 0 + 메인 루트 배치, (9) 보고에 분기 기준 커밋 해시 포함 + 베이스가 메인 브랜치 아니면 스택 주의 출력, (10) dirty 시 Step 3.5 게이트 발화

- [ ] **Step 6: 검증 grep**

Run: `grep -F "분기 기준:" skills/setting-up-worktrees/SKILL.md; grep -F "스택 구조" skills/setting-up-worktrees/SKILL.md; grep -F "MAIN repo root" skills/setting-up-worktrees/SKILL.md`
Expected: 각 1건 이상

- [ ] **Step 7: Commit**

```bash
git add skills/setting-up-worktrees/SKILL.md
git commit -m "feat(worktree): 보고 확장 (분기 기준 + 스택 안내) + env 소스 호출 위치 우선"
```

### Task 6: commands/worktree.md 동기화

**Files:**
- Modify: `commands/worktree.md:29-36` (동작 섹션)

**Model**: sonnet

- [ ] **Step 1: 동작 섹션 갱신** — 다음 4개 불릿을 추가/교체:

```markdown
- 위치: `<메인 저장소 루트>/.worktrees/<브랜치명>/` — **워크트리 안에서 호출해도 중첩 없이 메인 루트 아래에 생성** (v2.9.0+)
- 분기 기준: **호출 위치의 현재 HEAD** — 워크트리 A 안에서 호출하면 A 의 커밋이 시작점 (재분기). "dev 기준으로" 처럼 베이스를 명시하면 그 브랜치에서 분기
- 분기 전 dirty 확인: 커밋 안 된 변경이 있으면 "WIP 커밋 후 분기 / 마지막 커밋 시점 기준 분기" 선택 (stash 없음)
- 생성 보고에 분기 기준 커밋 해시 포함. 베이스가 메인 브랜치가 아니면 스택 구조 (새브랜치 → 베이스 → 메인) 머지 경로 주의를 함께 안내
```

- [ ] **Step 2: 검증 grep**

Run: `grep -F "재분기" commands/worktree.md; grep -F "스택 구조" commands/worktree.md`
Expected: 각 1건 이상

- [ ] **Step 3: Commit**

```bash
git add commands/worktree.md
git commit -m "docs(worktree): /worktree 안내 동기화 — 재분기 + dirty 게이트 + 스택 안내"
```

### Task 7: CLAUDE.md 결합 메모 신설

**Files:**
- Modify: `CLAUDE.md` (새 섹션 추가)

**Model**: sonnet

- [ ] **Step 1: `## 워크트리-재분기 결합 (v2.9.0+)` 섹션 추가** — 3 파일 atomic 룰 (SKILL.md + commands/worktree.md + hooks/worktree-memory-symlink), 회귀 패턴 표 (한쪽만 변경 시 증상), 회귀 catch grep (`MAIN_ROOT` / `worktree list --porcelain` / `Step 3.5` / for-loop add 금지), 영향 범위 (setup-memory-symlinks.sh 무변경 / og-* / auto-* / worktree-merge-back 영향 0)

- [ ] **Step 2: 검증 grep**

Run: `grep -cF "## 워크트리-재분기 결합 (v2.9.0+)" CLAUDE.md`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: 워크트리-재분기 결합 메모 (3 파일 atomic + 회귀 catch)"
```

### Task 8: 6 manifest 버전 bump

**Files:**
- Modify: `.version-bump.json` 이 선언한 manifest 전체 (`scripts/bump-version.sh` 사용)

**Model**: haiku

- [ ] **Step 1: 버전 충돌 확인** — 다른 브랜치가 2.9.0 을 선점했는지 확인:

Run: `for b in $(git branch --format='%(refname:short)'); do git show $b:.claude-plugin/plugin.json 2>/dev/null | grep -m1 '"version"'; done | sort -u`
Expected: 전부 2.8.1 이면 2.9.0 사용. 2.9.0 선점 브랜치가 보이면 2.10.0 으로 상향

- [ ] **Step 2: bump 실행**

Run: `bash scripts/bump-version.sh 2.9.0 && bash scripts/bump-version.sh --check`
Expected: 선언된 manifest 전체 2.9.0 (또는 Step 1 판정값), drift 0

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(v2.9.0): 6 manifest 2.8.1 → 2.9.0"
```

### Task 9: Bash E2E 테스트 (FR-6 — 기존 + 신규 시나리오 전체)

**Files:**
- Test: scratchpad 임시 디렉토리 (`e2e-worktree-rebranch.sh` — 저장소에 커밋하지 않음, 검증 기록만 변경이력에 [검증] entry)

**Model**: sonnet

- [ ] **Step 1: E2E 스크립트 작성** — scratchpad 에 임시 git 저장소를 만들고 다음 시나리오를 assert (각 시나리오 실패 시 exit 1 + 시나리오명 출력):

- (a) **기존 동작**: 메인 루트에서 `git worktree add -b feature-a .worktrees/feature-a HEAD` → 워크트리가 `<메인루트>/.worktrees/feature-a` 에 존재 + HEAD == dev HEAD (FR-5)
- (b) **재분기**: feature-a 워크트리 안에서 (커밋 1개 추가 후) `MAIN_ROOT` 를 `git worktree list --porcelain | head -1 | sed 's/^worktree //'` 로 해석 → 메인 루트와 일치 assert → `git worktree add -b sub "$MAIN_ROOT/.worktrees/sub" HEAD` → (1) `<feature-a>/.worktrees` 미존재 (중첩 0), (2) sub 의 HEAD == feature-a 의 HEAD (FR-1, FR-2)
- (c) **dirty 분기 양 경로**: feature-a 에 uncommitted 파일 → 경로 1: `git add -A && git commit` 후 분기 → 새 브랜치에 WIP 포함 assert. 경로 2: 커밋 없이 분기 → 새 브랜치 HEAD == 직전 커밋 && dirty 파일이 feature-a 에 잔존 assert (FR-3)
- (d) **기존 브랜치 attach**: 로컬 존재 브랜치 attach + bare 저장소를 origin 으로 등록해 remote-only 브랜치 `-B` attach (기존 로직 회귀 확인)
- (e) **훅 단독 시뮬레이션**: `HOME=$TMP_HOME` 격리 후 가짜 메모리 폴더 생성 → 훅에 JSON stdin (`tool_name: Bash`, `command: "git worktree add ..."`, `cwd`) 을 (e-1) 메인 루트 cwd, (e-2) 워크트리 cwd 두 케이스로 주입 → 양쪽 모두 심링크 생성 assert. (e-3) `git worktree add` 로 시작하지 않는 command → 무동작 assert (FR-7)

- [ ] **Step 2: E2E 실행**

Run: `bash <scratchpad>/e2e-worktree-rebranch.sh`
Expected: `E2E ALL PASS (a b c d e)` — 실패 시 해당 시나리오 수정 후 재실행

- [ ] **Step 3: [검증] 변경이력 기록** — 결과 PASS/FAIL 를 [검증] entry 로 plan 변경이력에 기록 (end-of-run [log] 커밋에 포함)

## 2. 위험 코드 지점

- `hooks/worktree-memory-symlink:62` — breaking: ROOT 해석 교체 실패 시 기존 메인 루트 케이스의 심링크까지 깨짐 (mitigation: Task 1 Step 2 `bash -n` + Task 9 (e-1)/(e-2) 양 케이스 시뮬레이션)
- `skills/setting-up-worktrees/SKILL.md` Step 0 — breaking: `MAIN_ROOT` 오해석 시 기존 메인 루트 호출 회귀 (mitigation: 메인 루트에서 worktree list 첫 entry = 자기 자신 — Task 9 (a) 로 검증)
- `skills/setting-up-worktrees/SKILL.md` Step 3 — side-effect: 워크트리 안 호출 시 메인 루트 `.gitignore` append 로 메인 워크트리 dirty (mitigation: 실제 append 발생 시 한 줄 알림 문구를 본문에 명시)
- `skills/setting-up-worktrees/SKILL.md` Step 4 — side-effect: for-loop 제거를 빼먹으면 훅 미발화 지속 (mitigation: Task 4 Step 3 회귀 grep + Task 9 (e))

## 3. 롤백 전략

- Code: task 별 commit 을 역순 revert (`git revert <SHA>`) — 문서 + 훅뿐이라 DB/flag 없음
- 훅만 긴급 롤백: `git checkout <직전 SHA> -- hooks/worktree-memory-symlink`
- manifest: `bash scripts/bump-version.sh 2.8.1` 로 원복

---
## 변경이력

### [2026-08-09 20:55] [구현계획서-수정]
- **id**: CH-20260809-003
- **이유**: 신규 구현 계획 (verifying-spec gap/conflict 0건 + plan_byte_check PASS — 슬림 plan, `**원본**` 블록 의도적 생략. 사용자 auto 진행 지시로 게이트 자동 통과)
- **무엇이**: 워크트리-재분기-implementation-plan.md 전체 (Task 1~9)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260809-001, CH-20260809-002

### [2026-08-09 21:02] [코드-수정] (batch: tasks 1..8)
- **id**: CH-20260809-004
- **이유**: 워크트리 안 재분기 지원 — 루트 해석 이원화 (배치=메인 루트 / 분기=호출 위치 HEAD) + 훅 심링크 버그 수정
- **무엇이**: hooks/worktree-memory-symlink, skills/setting-up-worktrees/SKILL.md, commands/worktree.md, CLAUDE.md, 6 manifest
- **영향범위**: setting-up-worktrees 생성 흐름 + worktree-memory-symlink 훅 전체 경로. setup-memory-symlinks.sh / worktree-merge-back / worktree-remove / og-* / auto-* 영향 0
- **위험 카테고리**: side-effect (훅 ROOT 해석 변경 — 전 worktree add 경로 영향)
- **task별 세부 (8건)**:
  - Task 1: `hooks/worktree-memory-symlink:58-70` — ROOT 를 메인 워크트리 (worktree list 첫 entry) 로 해석 (`side-effect`) — commits: `b6331c2`
  - Task 2: `skills/setting-up-worktrees/SKILL.md` — Step 0 루트 해석 이원화 + Defaults 표 (none) — commits: `c9b1482`
  - Task 3: `skills/setting-up-worktrees/SKILL.md` — Step 3 메인 루트 기준 + Step 3.5 dirty 게이트 신설 (none) — commits: `b63c6cd`
  - Task 4: `skills/setting-up-worktrees/SKILL.md` — Step 4 브랜치별 개별 add 호출 + dot 노드 동기 (none) — commits: `a3bcdef`
  - Task 5: `skills/setting-up-worktrees/SKILL.md` — Step 5 복사 소스 우선순위 + Step 6 보고 확장 + description·Anti-Patterns·Acceptance (none) — commits: `b40d86c`
  - Task 6: `commands/worktree.md:29-34` — 안내 동기화 (none) — commits: `e71d563`
  - Task 7: `CLAUDE.md` — 워크트리-재분기 결합 메모 신설 (none) — commits: `72c7f24`
  - Task 8: 6 manifest — 2.8.1 → 2.9.0 (none) — commits: `e833230`
- **연관 commits**: b6331c2..e833230
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260809-003

### [2026-08-09 21:02] [검증] (task: Task 9 — E2E 테스트 실행)
- **id**: CH-20260809-005
- **이유**: FR-6 — 구현 완료 후 Bash E2E (기존 동작 회귀 + 신규 재분기 + 훅 시뮬레이션)
- **무엇이**: 시나리오 (a) 메인 루트 신규 분기 / (b) 워크트리 안 재분기 (중첩 0 + HEAD 일치) / (c) dirty 양 경로 (WIP 커밋·커밋 시점) / (d) 로컬·remote-only attach / (e) 훅 시뮬레이션 3종 (메인 cwd·워크트리 cwd·프리픽스 미매치)
- **결과**: PASS — `E2E ALL PASS (a b c d e)` (scratchpad 임시 저장소 + HOME 격리, 저장소 커밋 X)
- **연관 항목**: CH-20260809-004

### [2026-08-09 21:10] [코드-수정] (batch: manifest revert)
- **id**: CH-20260809-006
- **이유**: 사용자 지시 — manifest 버전 bump 는 dev 브랜치에서 판단해서 올림 (피처 브랜치에서 선반영 X)
- **무엇이**: 6 manifest 2.9.0 → 2.8.1 복원 (Task 8 커밋 `e833230` revert)
- **영향범위**: manifest 만. 본문의 "(v2.9.0+)" 표기는 유지 — dev 에서 최종 버전 확정 시 다르면 일괄 치환 필요
- **위험 카테고리**: 없음 (기계적 버전 문자열 복원)
- **연관 commits**: `ec7e6f2`
- **연관 항목**: CH-20260809-004
