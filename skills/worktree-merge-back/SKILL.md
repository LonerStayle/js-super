---
name: worktree-merge-back
description: 커맨드 /merge-back-worktree 명시 호출로만 진입 — 자유 요청에서 자동 선택 금지. feature 워크트리 안에서 생성 시 기록된 직계 부모 브랜치를 먼저 흡수해 충돌을 sandbox 에서 해소한 뒤 그 부모로 안전 머지 + env 동기화. worktree-only (main 에서 호출 시 차단).
user-invocable: false
---

# Worktree Merge-Back (v2.5.2 — auto)

워크트리에서 진행한 feature 작업을 직계 부모 워크트리로 안전하게 머지 + 환경 파일 동기화. "Merge down before merging up" 패턴 — 충돌 해결은 feature sandbox 에서만, parent 워크트리는 항상 깨끗. v2.5.1+ 에서 자동화 강화 (parent 로컬 흡수 + 재귀 머지 자동 + env LLM 판단 + `/remove-worktree` 안내). v2.5.2+ 에서 dirty working tree 자동 커밋 추가 (커밋 안 된 변경이 있으면 묻지 않고 자동 커밋 후 진행 — 사용자 명시 요청). 머지 대상은 워크트리 생성 시 기록된 직계 부모 브랜치다 — 재분기 워크트리는 최상위가 아니라 자기를 분기시킨 브랜치로 머지된다. 판별이 불확실하면 자동 진행하지 않고 사용자에게 확인한다.

**Announce at start:** "I'm using the worktree-merge-back skill — feature → parent merge with sandbox conflict resolution + env sync."

## Other / 모호 응답 처리 (v2.1.1+)

본 skill 은 Step 2 판별 실패 시 머지 대상 확인 게이트 1건을 갖는다 (부모브랜치기준 개선으로 재도입). 사용자가 "Other" 자유 응답 또는 "모르겠음 / 이해 안 됨" 류 답변 catch 시 → 그 질문만 단독 재호출 + prose 설명 추가. 자동 진행 X.

## When to Use

- 사용자가 명시적으로 `/merge-back-worktree` 또는 본 skill 호출 시에만
- 자동 발동 경로 없음 — `finishing-a-development-branch` 등 다른 skill 의 자동 호출 X
- 의도 명확 분기점 (사용자가 머지 의사 결정 완료한 시점)

## HARD-GATE — Worktree-Only

이 skill 은 **feature worktree 안에서만 사용 가능**. main 워크트리 또는 일반 작업트리에서 호출 시 즉시 차단.

```bash
# Guard 검출 (deterministic)
CURRENT_PATH=$(pwd)
MAIN_WORKTREE=$(git worktree list --porcelain | awk '/^worktree / {print $2; exit}')
if [ "$CURRENT_PATH" = "$MAIN_WORKTREE" ]; then
  echo "❌ 이 skill 은 worktree 안에서만 사용 가능합니다."
  echo "   현재: $CURRENT_PATH (main 워크트리)"
  echo "   먼저 \`/worktree <feature-name>\` 으로 워크트리 진입 후 재호출하세요."
  exit 1
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "❌ git 저장소가 아닙니다."
  exit 1
}
```

추가로 `git worktree list` 결과가 1개 (main 만 존재) 면 차단 — feature 워크트리 없음.

## Process (v2.5.2+ — 게이트 1건: Step 2 판별 실패 시, prose 보고 + 자동 진행)

v2.0.5 의 Step 3 충돌 게이트 1건은 v2.5.1+ 에서 prose 안내로 대체 (재귀 머지 자동 + semantic conflict 만 prose 안내). 신규 Step 4.5 env 동기화 추가. v2.5.2+ 에서 Step 1 dirty 자동 커밋 추가 (즉시 종료 폐기 — 커밋 전 파일 목록 prose 알림). 부모브랜치기준 개선으로 Step 2 판별 실패 시에만 사용자 확인 게이트 1건이 재도입됐다 — 나머지 단계는 default 권장사항 자동 진행 + 안전성 안내문 그대로.

`Other / 모호 응답 처리 (v2.1.1+)` 섹션은 Step 2 판별 실패 게이트에 적용된다 — Step 4.5 env 동기화 prose 보고에 대한 사용자 자유 응답은 메인이 prose 로 follow-up.

### Step 1 — Working tree 검사 + 자동 커밋 (v2.5.2+ — 게이트 X, 알림 후 자동 진행)

v2.5.1 까지는 dirty working tree 시 즉시 종료 + 사용자 재호출 요구였음. v2.5.2+ 에서 **자동 커밋 후 진행**으로 전환 (사용자 명시 요청 — "커밋 안 되어 있으면 묻지 않고 알아서 커밋"). 게이트 없음 (사용자에게 진행 여부 묻지 않음). 단 커밋 전 파일 목록 + 생성 메시지 prose 알림 필수 (silent 금지 — 원치 않는 파일 섞임 catch).

```bash
git status --porcelain
```

- 비어있음 → Step 2 자동 진행
- 변경사항 있음 → 아래 자동 커밋 절차 후 Step 2 진행:

**1) 커밋 대상 파악** — 변경 의미를 알아야 메시지를 생성하므로 diff 를 읽는다:

```bash
git status --porcelain   # 파일 목록 + 상태 (M/A/D/??)
git diff HEAD            # tracked 변경 내용 (메시지 생성 근거)
```

**2) 커밋 메시지 자동 생성** — 위 diff + 파일 목록을 보고 의미 있는 한 줄 메시지를 LLM 이 작성 (conventional-commit 스타일 권장, 예: `feat: X 추가`, `fix: Y 수정`). 고정 문구 사용 X — 나중에 이력 추적 가능하게.

**3) 파일 목록 + 메시지 prose 알림** (묻지 않음, 알림만 — 사용자가 원치 않는 파일 catch + stop 가능):

```
🔧 커밋 안 된 변경 <N>개 발견 → 자동 커밋 후 머지백 진행합니다:
   - <file1> (수정)
   - <file2> (신규)
   - <file3> (삭제)
   커밋 메시지: "<생성된 메시지>"
   (원치 않는 파일이 보이면 지금 stop 하세요.)
```

**4) 커밋 실행:**

```bash
git add -A
git commit -m "<생성된 메시지>"
```

→ Step 2 자동 진행. 게이트 없음 (사용자에게 묻지 않음). 위 prose 알림이 유일한 안전장치 — 사용자가 목록 보고 stop 가능. 커밋은 로컬 이력 추가라 되돌리기 쉬움 (`git reset`) — destructive 아님.

### Step 2 — 직계 부모 판별 (기록 기반, 검증 4건)

머지 대상은 `git worktree list` 순서나 커밋 히스토리 추정이 아니라, 워크트리 생성 시 `setting-up-worktrees` 가 기록해 둔 직계 부모 브랜치다.

```bash
FEATURE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
PARENT_BRANCH=$(git config "branch.$FEATURE_BRANCH.js-super-parent" || true)
PARENT_BASE=$(git config "branch.$FEATURE_BRANCH.js-super-parent-base" || true)

# 검증 4건 — 하나라도 실패 시 판별 실패 → 사용자 확인 게이트
# 1) 기록 존재 + 자기 자신 아님
[ -n "$PARENT_BRANCH" ] && [ "$PARENT_BRANCH" != "$FEATURE_BRANCH" ]
# 2) 부모 브랜치가 로컬에 실존
git show-ref --verify --quiet "refs/heads/$PARENT_BRANCH"
# 3) 부모 브랜치가 어떤 워크트리에 체크아웃되어 있음 (머지를 실행할 경로 확보)
PARENT_PATH=$(git worktree list --porcelain \
  | awk -v b="refs/heads/$PARENT_BRANCH" '/^worktree /{p=$2} $0=="branch "b{print p; exit}')
[ -n "$PARENT_PATH" ]
# 4) 기록된 분기점이 현재 히스토리의 조상 — 스킬 밖 동명 재생성으로 물려받은 stale 기록 차단
[ -n "$PARENT_BASE" ] && git merge-base --is-ancestor "$PARENT_BASE" HEAD
```

```bash
WT_COUNT=$(git worktree list | wc -l)
if [ "$WT_COUNT" -lt 2 ]; then
  echo "❌ feature 워크트리 없음. 현재 main 워크트리 1개만 존재."
  exit 1
fi
```

최상위 브랜치 이름도 별도로 확보해둔다 — 아래 판별 실패 게이트의 선택지 나열과 Step 5 의 스택 안내 (부모 ≠ 최상위일 때) 에만 쓰고, 머지 대상 결정에는 쓰지 않는다.

```bash
TOP_BRANCH=$(git worktree list --porcelain | awk '/^branch /{print $2; exit}' | sed 's|refs/heads/||')
```

**판별 실패 게이트** — 검증 4건 중 하나라도 실패하면 조용한 fallback 없이 `AskUserQuestion` 으로 사용자에게 머지 대상을 확인한다:

- 실패 사유 1줄을 질문 본문에 포함: 기록 없음 / 부모 브랜치 삭제됨 / 부모 미체크아웃 / 분기점이 조상이 아님
- options = 최상위 브랜치 (`$TOP_BRANCH`) + 다른 워크트리에 체크아웃된 브랜치들 (자기 자신 제외, 4개 초과분은 Other 로 안내) + "중단" (항상 포함)
- **중단** 선택 시 안내 1줄 출력 후 종료: "부모 워크트리를 먼저 만들고 (`/worktree <부모브랜치>`) 본 skill 을 재호출해주세요."
- 사용자가 브랜치를 고르면 (Other 자유 응답 포함) 검증 ②③ (로컬 실존 + 워크트리 체크아웃) 을 그 브랜치에 재적용 — 실패하면 사유를 안내하고 게이트를 다시 연다 (탈출은 언제든 "중단")
- 조용한 최상위 fallback / 히스토리 추정으로 자동 진행하는 것은 금지

### Step 3 — Parent 변경사항 흡수 (feature 쪽으로, 로컬 브랜치) — v2.5.1+ 자동화

머지 대상은 직계 부모 브랜치 (Step 2 판별 결과) 의 로컬 워크트리다. 사용자가 진입 전 remote 동기화가 필요했으면 별도 `git fetch` + pull 후 본 skill 호출.

```bash
git merge $PARENT_BRANCH
```

**충돌 처리** — git default 재귀 머지 (3-way merge) 자동 시도. 결과는 두 가지:

1. **자동 머지 성공** (대부분 케이스) → Step 4 자동 진행
2. **실제 conflict marker 발생** (semantic conflict) → 사용자 prose 안내:

```
❌ Step 3 머지 충돌이 발생했습니다.
   다음 파일에 conflict marker 가 남았습니다: <FILES>
   1. 충돌 파일을 수동 편집 + `git add <FILES>` + `git commit` 후
   2. 본 skill 을 재호출해주세요.
   (또는 `git merge --abort` 로 되돌리기)
```

**절대 X**: `git merge --strategy ours` / `--strategy theirs` 자동 적용 (한쪽 임의 채택 = 데이터 손실). 사용자가 명시 `--strategy` 플래그 안 주면 위험 분기 진입 X.

자동 머지 성공 시 → Step 4 자동 진행.

### Step 4 — Parent 워크트리로 머지 (자동, default 기본 메시지)

Pre-check (R3 mitigation):

```bash
git merge-base --is-ancestor $PARENT_BRANCH HEAD || {
  echo "❌ Step 3 흡수 가정 깨짐. Step 3 중간 다른 작업 발생 의심. 수동 머지 필요."
  exit 1
}
```

검증 통과 시 default 기본 메시지로 자동 머지:

```bash
FEATURE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git -C "$PARENT_PATH" merge --no-ff "$FEATURE_BRANCH" \
  -m "Merge branch '$FEATURE_BRANCH' into $PARENT_BRANCH"
```

→ 게이트 없음. 메시지 customize 원하면 사용자가 직접 `git -C <parent-path> commit --amend` 로 수정 (Step 4 이후 자유).

### Step 4.5 — 환경 파일 동기화 (v2.5.1+ 신규)

`.env*` 같은 gitignored 로컬 빌드 환경 파일은 git 머지로 못 옮김. 워크트리에서 새 키 추가했으면 parent 가 stale 상태로 남음 — 환경 파일은 Step 2 에서 판별한 직계 부모 워크트리로 동기화한다. Step 4.5 에서 LLM 변경 의미 판단 후 선택적 cp.

**대상 파일 감지**:

- 후보 글롭: `.env*`, `local.properties`, `gradle-wrapper.properties`, 기타 플랫폼별 로컬 빌드 환경 파일 (`setting-up-worktrees` 의 LLM-judged Procedure 와 동일 룰)
- 실제 비교 대상: 워크트리에 존재하는 후보 파일 중 parent 와 내용이 다른 것 (대부분 gitignored 라 아래처럼 `--ignored` 로 스캔)

```bash
# 후보 catch (예시)
# .env* 등 로컬 빌드 환경 파일은 gitignored 라 기본 `git status` 출력엔 안 잡힘 → --ignored=matching 필수
CURRENT_PATH=$(git rev-parse --show-toplevel)
CANDIDATES=$(git -C "$CURRENT_PATH" status --porcelain --ignored=matching \
  | awk '{print $2}' \
  | grep -E "(^|/)\.env|local\.properties|gradle-wrapper\.properties" \
  | sort -u)
```

**LLM 판단** — 각 후보 파일의 변경 의미를 1줄 prose 보고:

- 새 환경 변수 키 추가 → cp 권장
- 임시 디버그 값 / 주석만 변경 → 제외 권장
- 기존 키의 값 변경 → 보고 + 사용자 선택 보존 (silent cp 절대 X)

prose 보고 예시:

```
🔧 환경 파일 동기화 검토:
   - .env.local: 새 키 NEW_API_KEY 추가됨 → parent 로 cp 권장
   - .env.development: DEBUG_MODE=true 임시 변경 → 제외 권장
   - local.properties: sdk.dir 경로 변경됨 → 사용자 확인 필요 (둘 다 유효 경로)
```

**cp 실행** — `cp -p` (permission 보존) + `-P` (symlink 보존) default:

```bash
cp -pP "$CURRENT_PATH/$FILE" "$PARENT_PATH/$FILE"
```

symlink 발견 시 별도 prose 보고 후 사용자 선택. silent cp 절대 X.

**절대 X**: prose 보고 없이 (silent) cp 실행 (R-2 — LLM 오판 시 secret 노출). 명확한 케이스(새 키 추가 등)의 cp 는 prose 보고 후 자동 진행하되 사용자가 언제든 stop 가능. **단 "기존 키의 값 변경"처럼 판단이 애매한 케이스는 위 룰대로 실제 사용자 응답을 기다린다** (자동 진행 X — 한쪽 값 임의 채택 방지).

대상 파일 0건이면 한 줄 안내 후 Step 5 자동 진행:

```
🔧 동기화할 환경 파일 없음. Step 5 진행.
```

### Step 5 — 사후 처리 안내 (자동, 게이트 X)

사후 처리 (worktree 제거 / 브랜치 삭제 / remote push) 는 모두 default no — skill 이 자동 실행하지 않음. 종료 메시지 한 줄로 안내:

```
✅ Merge 완료. Feature 워크트리: <FEATURE_BRANCH> → <PARENT_BRANCH> (commit: <merge-sha>)

다음 단계 (필요 시 직접 실행):
  - 워크트리 + 브랜치 정리: /remove-worktree   (v2.5.1+ 신규 슬래시 명령, 단독 호출)
  - Remote 동기화:         git -C <parent-path> pull   (parent 로컬 stale 시)
  - Remote push:           git -C <parent-path> push origin <parent-branch>
```

`$PARENT_BRANCH` 가 `$TOP_BRANCH` 와 다르면 (재분기 워크트리) 종료 메시지에 스택 안내를 추가한다:

```
ℹ️ 이 머지는 직계 부모 (<PARENT_BRANCH>) 까지입니다. 최상위 (<TOP_BRANCH>) 반영은 부모 워크트리에서 `/merge-back-worktree` 를 다시 실행해주세요.
```

→ 사용자가 의도에 맞게 직접 선택. `setting-up-worktrees` 의 "keep worktree" / "discard" 자유 결정 보존. v2.5.1+ 에서 `/remove-worktree` 가 워크트리 + 브랜치 정리를 한 슬래시로 묶음 (chain X — 명시 호출만).

## Anti-Patterns

| Wrong | Right |
|---|---|
| main 워크트리에서 invoke 후 그대로 진행 | HARD-GATE 차단. feature worktree 안에서만. |
| 기록 없을 때 조용히 최상위로 머지 | NEVER — 판별 실패 게이트로 사용자 확인. |
| 커밋 히스토리 추정으로 부모 자동 선택 | NEVER — 기록 + 검증 4건만 신뢰. |
| 게이트에서 사용자가 고른 대상을 재검증 없이 머지 | 검증 ②③ 재적용 후 진행. |
| Step 3 충돌을 자동 해결 (`--strategy ours` / `theirs`) | NEVER. 안전성 핵심. 사용자가 명시 플래그 안 주면 자동 적용 X. (v2.0.4+ 룰 v2.5.1+ 유지) |
| Step 3 git default 재귀 머지 자체를 차단 | OK. git default 3-way merge 는 안전 (conflict marker 발생 시 자동 stop). v2.5.1+ 자동화 정상 흐름. |
| 머지 대상을 remote (origin) 로 잡기 | 로컬 직계 부모 브랜치로 머지. remote 동기화 원하면 사용자가 진입 전 별도 fetch + pull. |
| Step 4 를 Step 3 흡수 검증 없이 진행 | merge-base 검증 필수 (R3). |
| Step 4.5 env cp 를 silent 로 실행 | NEVER. 각 파일 1줄 prose 보고 + 사용자 stop 가능 시점 보장 (R-2). |
| Step 4.5 env LLM 판단 없이 모든 파일 자동 cp | 변경 의미 판단 후 선택적 cp. 임시 디버그 / 주석만 변경 제외. |
| Step 4.5 symlink 를 `cp -L` (dereference) 로 따라가서 복사 | `-P` (보존) default. symlink 발견 시 별도 prose 보고. |
| `git push --force` 사용 | NEVER. push 자체를 skill 이 하지 않음 (Step 5 안내만). |
| `cd <parent-path> && git ...` 패턴 | `git -C <parent-path>` 사용. cwd 변경 X. |
| 사후 처리 자동 실행 (worktree 제거 / push) | 모두 안내만. 사용자가 직접 (v2.5.1+ 에서 `/remove-worktree` 단독 슬래시 명령). |
| Step 1 dirty 시 즉시 종료 + 사용자 재호출 요구 | (v2.5.2+ 폐기) 자동 커밋 후 진행. 사용자 명시 요청 — 묻지 않고 알아서 커밋. |
| Step 1 자동 커밋을 silent (파일 목록·메시지 안 알림) 로 실행 | NEVER. 커밋 전 파일 목록 + 생성 메시지 prose 알림 필수 (원치 않는 파일 섞임 catch). |
| Step 1 커밋 메시지를 고정 문구로 생성 | 변경 내용 요약해서 의미 있는 한 줄 메시지 (사용자 이력 추적 가능하게). |
| Step 1 자동 커밋 후 진행 여부 재질문 | 묻지 않음. prose 알림 후 자동 진행 (게이트 X — 사용자 명시 요청). |

## Why v2.0.5 slim

- v2.0.4 출시 후 사용자 dogfood 결과 게이트 4건이 마찰 → 1건으로 축소.
- 안전성 핵심 (Step 3 충돌 자동 해결 금지) 은 게이트 유지.
- 나머지 3건은 "default 권장사항" 자동 진행 + 안내문 (사용자 의도 보존 + 마찰 ↓).

## Why v2.5.1

- v2.0.5 출시 후 사용자 dogfood 결과 4 가지 마찰 catch:
  1. 머지 대상이 `origin/<메인 브랜치>` (remote) 라 parent 워크트리의 로컬 commit 이 머지 흐름에 자동 반영 X — 사용자가 별도 push 필요.
  2. Step 3 충돌 게이트가 모든 충돌에서 사용자 응답 wait — 자동화 의도와 충돌.
  3. `.env*` 같은 gitignored 환경 파일이 git 머지로 못 옮겨짐 — 새 키 추가하면 parent stale.
  4. 사후 처리 안내가 한 줄 안내만 — 사용자가 매번 `git worktree remove` + `git branch -d` 수동 입력.
- 해결:
  1. **D-1** Step 3 머지 대상 `origin/<메인 브랜치>` → 로컬 `<메인 브랜치>` (사용자 의도 그대로)
  2. **D-2** 충돌 처리 = git default 재귀 머지 자동 + semantic conflict 만 prose 안내 (자동화 ↑, 안전성 유지)
  3. **D-3** Step 4.5 신규 — env 파일 LLM 판단 + 선택적 cp (silent 절대 X)
  4. **D-4** `/remove-worktree` 신규 슬래시 명령 (독립, chain X) — Step 5 안내에 호출 추가
- 안전성 핵심 (HARD-GATE worktree-only / `--strategy ours/theirs` 자동 차단) 모두 유지.

## Why v2.5.2

- v2.5.1 출시 후 사용자 dogfood 결과 마찰 1건 catch: Step 1 이 dirty working tree 시 즉시 종료 + 사용자가 직접 commit 후 재호출 요구 → 워크트리에서 작업하다 커밋을 깜빡하면 머지백이 매번 중단됨.
- 사용자 명시 요청: "커밋 안 되어 있으면 묻지 않고 알아서 커밋하게끔 진행".
- 해결:
  1. **E-1** Step 1 dirty 시 자동 커밋 후 진행 (즉시 종료 폐기). 게이트 없음 (진행 여부 안 물음).
  2. **E-2** 커밋 메시지 = `git diff HEAD` 요약 LLM 자동 생성 (고정 문구 X — 이력 추적).
  3. **E-3** 안전장치 = 커밋 전 파일 목록 + 생성 메시지 prose 알림 (silent 금지 — 원치 않는 파일 섞임 catch, 사용자 stop 가능).
- 안전성 판단: 자동 커밋은 destructive 아님 (로컬 이력 추가, `git reset` 으로 되돌리기 쉬움). `git push --force` / `rm` / `--strategy ours/theirs` 같은 데이터 손실 계열과 다름 — v2.0.4+ / v2.5.1+ 안전성 핵심과 충돌 X. HARD-GATE worktree-only / 충돌 자동 해결 금지 모두 유지.

## Why 부모브랜치 기준

- 재분기 워크트리에서 머지 대상을 `git worktree list` 첫 entry (최상위) 로 고정했던 게 문제 — 모델이 상황을 보고 우연히 막아주던 상태였을 뿐, 구조적 보장이 없었다.
- 해결: 워크트리 생성 시 기록해 둔 직계 부모 (`js-super-parent` / `js-super-parent-base`) 를 판별 근거로 삼고, 검증 4건 + 판별 실패 게이트로 대체했다.
- 조용한 최상위 fallback 은 금지 — 판별이 불확실하면 항상 사용자에게 확인한다 (사용자 결정).

## Related Skills

- `setting-up-worktrees` — 워크트리 생성 페어 — 분기 부모 기록 (`js-super-parent` / `js-super-parent-base`) 을 이 skill 이 판독
- `finishing-a-development-branch` — 테스트 게이트 + 종료 메시지 (자동 호출 X)
- `change-history` — 본 skill 영향 0 (git 조작만, MD 안 건드림)
