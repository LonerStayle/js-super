---
name: setting-up-worktrees
description: Use when the user asks to create one or more git worktrees ("워크트리 만들어줘", "<티켓명> 워크트리"). Default location is <project-root>/.worktrees/<branch-name>; creates the branch from current HEAD if it doesn't exist, then auto-copies the project's 로컬 빌드 환경 파일 (LLM-judged per platform — Node `.env*`, Android `local.properties`/keystore, iOS `*.xcconfig`, etc.) AND symlinks the main repo's Claude Code memory folder so the worktree shares user/feedback/project memory from the start. NEVER asks the user which files to copy — detects candidates, notifies, and copies (honoring explicit excludes).
---

# Setting Up Worktrees (Quick Batch Creation)

User-personal workflow shortcut for spinning up multiple parallel work streams. Each worktree gets its own branch, an automatic copy of the project's 로컬 빌드 환경 파일 (LLM-judged per platform — Node `.env*`, Android `local.properties`, iOS `*.xcconfig`, etc.; so the user can build/run servers concurrently without env-loading fights), AND a symlink to the main repo's Claude Code memory folder (so user/feedback/project memory is immediately available in the worktree's first session).

<HARD-GATE>
This skill MUST be invoked from a git repository. If the current working directory is not inside a git repo (`git rev-parse --is-inside-work-tree` returns false), abort and tell the user to run `git init` first or switch to the target project.
</HARD-GATE>

<HARD-GATE>
NEVER ask the user which 로컬 빌드 환경 파일 to copy. 메인 에이전트가 프로젝트 컨텍스트 (Android / iOS / Node / Flutter / Rust / etc.) 를 읽고 적절한 후보를 판단 + 후보 list 사용자에게 노출 + 복사. The user only specifies branch names — 파일 선택은 LLM-judged. The single exception: if the user EXPLICITLY says "X 파일은 복사하지 마" (exclude pattern), honor that.
</HARD-GATE>

## Trigger Examples

- 단수: `/worktree feature-a`
- 복수: `/worktree feature-a feature-b feature-c`
- 자연어: "워크트리 3개 만들어줘. 브랜치는 feature-a, feature-b, feature-c."

> 사용자가 실제 티켓명(예: `TICKET-123-기능명`)으로 호출하면 그대로 브랜치명에 사용한다. 위 `feature-a` 등은 placeholder.

## Defaults (No User Prompt)

| Knob | Default behavior |
|---|---|
| Worktree root | `<메인 저장소 루트>/.worktrees/` — 워크트리 안에서 호출해도 메인 루트 기준, 중첩 생성 금지 (override only if user explicitly asks) |
| Branch creation | If branch missing → `-b <name>` from **호출 위치 HEAD** (워크트리 안이면 그 워크트리의 커밋이 시작점; 사용자가 베이스 명시 시 그 브랜치). Existing local → use as-is. Remote-only → `-B <name> origin/<name>` |
| Dirty 워크트리에서 분기 (v2.9.0+) | Step 3.5 게이트 — "WIP 커밋 후 분기" / "마지막 커밋 시점 기준 분기" 선택. stash 금지 |
| 로컬 빌드 환경 파일 복사 | **메인 에이전트가 프로젝트 컨텍스트 기반 후보 판단** (Node/Web → `.env*` / Android → `local.properties`, keystore 류 / iOS → `*.xcconfig` 등 / Desktop → `secrets.*`). 후보 list 사용자 노출 후 자동 복사. committed templates / build artifacts 자동 제외. |
| Claude memory folder | **Symlink handled by `worktree-memory-symlink` PostToolUse hook** — fires automatically on `git worktree add`. Skips if main has no memory yet or if worktree's memory dir already exists. The skill body does NOT perform this step. |
| `.worktrees/` in `.gitignore` | Auto-add if missing |

## Process

```dot
digraph wt_flow {
    "Verify git repo" [shape=box];
    "Parse branch list" [shape=box];
    "LLM-judged 로컬 빌드 환경 파일\n후보 결정 (no user prompt)" [shape=box];
    "Ensure .worktrees/ exists\n+ in .gitignore" [shape=box];
    "For each branch" [shape=box];
    "Branch exists?" [shape=diamond];
    "git worktree add <path> <branch>" [shape=box];
    "git worktree add -b <branch> <path> HEAD" [shape=box];
    "Copy ALL detected env files" [shape=box];
    "Symlink Claude memory folder\n(automatic via PostToolUse hook)" [shape=box];
    "Report summary" [shape=doublecircle];

    "Verify git repo" -> "Parse branch list";
    "Parse branch list" -> "LLM-judged 로컬 빌드 환경 파일\n후보 결정 (no user prompt)";
    "LLM-judged 로컬 빌드 환경 파일\n후보 결정 (no user prompt)" -> "Ensure .worktrees/ exists\n+ in .gitignore";
    "Ensure .worktrees/ exists\n+ in .gitignore" -> "For each branch";
    "For each branch" -> "Branch exists?";
    "Branch exists?" -> "git worktree add <path> <branch>" [label="local or remote"];
    "Branch exists?" -> "git worktree add -b <branch> <path> HEAD" [label="new"];
    "git worktree add <path> <branch>" -> "Copy ALL detected env files";
    "git worktree add -b <branch> <path> HEAD" -> "Copy ALL detected env files";
    "Copy ALL detected env files" -> "Symlink Claude memory folder\n(automatic via PostToolUse hook)";
    "Symlink Claude memory folder\n(automatic via PostToolUse hook)" -> "For each branch" [label="next"];
    "Symlink Claude memory folder\n(automatic via PostToolUse hook)" -> "Report summary" [label="done"];
}
```

## Procedure (Step-by-Step)

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

**Step 1 — Parse branch names from user's message**

Extract `BRANCHES=(...)` from the user's message. Korean ticket-style names like `<TICKET>-<번호>-<설명>` are fine (UTF-8 OK). Do NOT ask about env files — those are auto-detected.

**Step 2 — LLM-judged 로컬 빌드 환경 파일 후보 결정 (NO bash glob, NO user prompt)**

메인 에이전트가 프로젝트 루트 + 설정 파일 (예: `package.json`, `build.gradle`, `Podfile`, `pubspec.yaml`, `Cargo.toml`) 을 read → 프로젝트 종류 추론 → 다음 **레시피** 참고하여 후보 list 결정:

| 플랫폼 | 후보 (gitignored 인 경우 복사 대상) |
|---|---|
| Node / Web | `.env`, `.env.local`, `.env.production`, `.env.development`, `.envrc` (committed templates `.env.example` / `.env.sample` 제외) |
| Android | `local.properties` (SDK 경로), `keystore.properties`, `*.keystore`, `*.jks`, `google-services.json` (gitignored 인 경우) |
| iOS / macOS | `*.xcconfig` (local-only), `GoogleService-Info.plist` (gitignored 인 경우), `Secrets.swift` |
| Desktop / 기타 | `secrets.properties`, `secrets.json`, `config.local.*` |
| Flutter | `android/local.properties` + `android/key.properties` + iOS 항목 + `.env.*` |
| Rust | `.env*`, `.cargo/credentials` (gitignored 인 경우) |

**컨셉**: "로컬 빌드 환경 파일" = 빌드 / 실행 시 필요하지만 git committed 가 아닌 파일. build artifact (`dist/` / `build/` / `target/` / `.gradle/` / `node_modules/`) 와 IDE 디렉토리 (`.idea/` / `.vscode/local-state.json`) 와 OS 임시 파일 (`.DS_Store`) 은 **제외**.

**Procedure**:

1. 메인이 프로젝트 종류 추론 (위 레시피 기준)
2. 루트에서 후보 파일 존재 확인 (`ls` + `git ls-files --error-unmatch <path>` 로 gitignored 인지 판정 — committed 면 git checkout 자동 복원 가능하므로 복사 skip)
3. 후보 list 를 **통지** (응답 대기 아님): `ℹ️ 감지된 로컬 빌드 환경 파일: <list> — 그대로 복사합니다. 특정 파일 제외를 원하면 알려주세요.`
4. 기본 = 후보 전체 복사. blocking-wait 없이 바로 진행. 단 사용자가 명시적으로 "X 파일은 복사하지 마" (EXCLUDE) 라고 하면 그 파일만 제외 (기존 HARD-GATE 의 EXCLUDE 옵션 유지)
5. ENV_FILES (또는 LOCAL_BUILD_FILES) 배열에 최종 후보 저장 → 다음 Step 으로 전달

후보가 없으면 한 줄 안내 (`ℹ️ 프로젝트 루트에 로컬 빌드 환경 파일 후보 없음 — 복사 skip`) 후 다음 Step 진행. Don't abort.

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

**Step 5 — Copy ALL detected env files into each worktree (no prompts)**

```bash
for BR in "${BRANCHES[@]}"; do
    WT_PATH="$ROOT/.worktrees/$BR"
    [ -d "$WT_PATH" ] || continue   # was skipped earlier
    for EF in "${ENV_FILES[@]}"; do
        cp "$ROOT/$EF" "$WT_PATH/$EF"
        echo "📋 $BR ← $EF 복사 완료"
    done
done
```

**Step 5.5 — Memory symlink (handled automatically by hook)**

Memory-folder symlinking is performed by the `worktree-memory-symlink` PostToolUse hook (see `hooks/hooks.json` + `hooks/worktree-memory-symlink`). It fires automatically whenever any `git worktree add ...` command runs through the Bash tool, parses the worktree path from the command, and invokes `scripts/setup-memory-symlinks.sh`. **Do nothing here.** No mkdir, no ln, no sed — the hook owns this concern entirely. The script's output (e.g. `🔗 <branch> ← Claude 메모리 폴더 심링크 ...`) appears as hook stderr in your tool output and should be forwarded to the user as part of the Step 6 summary if visible.

Behavior summary:
- Main memory dir missing → skip with notice (first-run user, nothing to share yet).
- Worktree memory dir already exists → skip without clobbering (user already ran a session in that path).
- Otherwise → symlink. New memories saved in either side are visible from both.

⚠️ Cleanup note: when the user later removes a worktree, `git worktree remove` will not touch the symlink (lives outside the worktree dir) — no risk to main memory. But `rm -rf <worktree-path>` is also safe because the memory symlink is OUTSIDE the worktree directory (`~/.claude/projects/...`), not inside it. The only thing to watch is users manually `rm -rf $HOME/.claude/projects/<wt-encoded>/memory` — that would delete the LINK, not the target, so still safe; whereas `rm -rf $HOME/.claude/projects/<wt-encoded>/memory/` (with trailing slash on some shells) could traverse into the linked main memory. Add a tiny note in the report so the user knows.

**Step 6 — Report summary**

Print a Korean-friendly summary listing each worktree path + the env files copied:

```
✅ 워크트리 생성 완료 (n개)
감지된 .env* 파일: .env, .env.local, .env.production (3개)
Claude 메모리 폴더: 메인 → 워크트리 심링크 (n개)

- feature-a   → .worktrees/feature-a   (.env ✓ .env.local ✓ .env.production ✓ | 🔗 memory)
- feature-b   → .worktrees/feature-b   (.env ✓ .env.local ✓ .env.production ✓ | 🔗 memory)
- feature-c   → .worktrees/feature-c   (.env ✓ .env.local ✓ .env.production ✓ | 🔗 memory)

각 워크트리에서 바로 빌드·서버 실행 가능합니다.
워크트리 첫 세션부터 메인 레포의 Claude 메모리(user/feedback/project) 즉시 활용됩니다.
정리: `git worktree remove <path>` — 메모리 심링크는 워크트리 디렉터리 밖이라 메인 메모리에 영향 없음.
```

## Anti-Patterns

| Wrong | Right |
|---|---|
| Asking the user "which 로컬 빌드 환경 파일 to copy?" | Forbidden by HARD-GATE. 메인이 프로젝트 컨텍스트 보고 후보 자동 판단 + 노출 + 복사. |
| Skipping copy because user didn't mention it | 항상 메인이 감지된 후보 모두 복사 시도 (사용자 명시 exclude 만 예외). build-ready worktree 가 목적. |
| Hardcoded `.env*` glob 만 사용 (Android/iOS/desktop 미커버) | LLM-judged 레시피 적용. 새 플랫폼 (Flutter / RN / Rust) 도 컨텍스트 추론으로 cover. |
| Force-create when worktree path already exists | Detect + skip with notice. Don't clobber user's WIP. |
| Skip `.gitignore` update | Always add `.worktrees/` (idempotent check). |
| Use `git checkout -b` first then `worktree add` | Prefer `worktree add -b <branch> <path>` (atomic). |
| Copy `.env.example` (template, already in git) | Excluded from glob. |
| Performing the memory symlink yourself in this skill | Forbidden — handled by `worktree-memory-symlink` PostToolUse hook. The agent must not run any path-mutating shell command (directory creation, symlink, or string substitution) against the Claude memory location. Past versions failed because agents mentally simulated the encoding rule and produced folder names Claude Code never reads. |
| Clobber worktree's existing memory dir with a symlink | Forbidden. If `$WT_MEMORY` already exists, skip and tell user to migrate manually. |
| Skip the symlink because "user didn't ask for it" | Always attempt. The whole point is zero-friction worktree start. Only skip when main memory missing or WT memory already there. |

## Red Flags

| Thought | Reality |
|---|---|
| "Branch name has Korean — might break" | git handles UTF-8 branch names fine. Don't sanitize unless user asks. |
| "Should I confirm which env files?" | NO. HARD-GATE forbids it. Auto-glob always. |
| ".gitignore is annoying to update" | Idempotent: only append if not already there. One-time cost. |
| "User has secrets in .env, scary to copy automatically" | Files are already on disk; copying within the same machine doesn't expand exposure. The .worktrees/ folder is gitignored. |

## Cleanup (separate operation)

If the user later asks to remove a worktree:

```bash
git worktree remove "$ROOT/.worktrees/<branch>"
git branch -d <branch>   # only if no longer needed
```

This skill does NOT auto-remove. Removal is destructive and must be explicit.

## Acceptance

After running this skill:
1. Each requested branch has a worktree at `<root>/.worktrees/<branch>/`
2. Every detected 로컬 빌드 환경 파일 (Step 2 의 LLM-judged 후보 — 플랫폼별 `.env*` / `local.properties` / `*.xcconfig` 등, committed templates `.env.example`/`.env.sample`/`.env.template` 제외) is copied into each worktree
3. `.worktrees/` is in `.gitignore`
4. `git worktree list` shows all created worktrees
5. The `worktree-memory-symlink` PostToolUse hook fired for every `git worktree add` invocation issued by this skill. (The skill itself did NOT mkdir / ln any memory paths.)
6. User got a summary report listing each worktree's path + per-file copy status + memory symlink status (the latter coming from the hook's stderr output).
7. The user was NOT asked which env files to copy, NOR about the memory symlink.

## Related Skills

- `using-git-worktrees` (upstream, broader) — general guidance on worktree workflows
- `executing-plans` — often run inside a freshly-created worktree
