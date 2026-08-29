# H18 — 직계 부모 판별 (기록 기반 머지 대상, 시나리오 6종)

## Scenario 개요

Step 2 (직계 부모 판별 — 검증 4건 + 판별 실패 게이트) 와 Step 5 (스택 안내) 를 시나리오 6종으로 검증한다. 관련 파일: `skills/worktree-merge-back/SKILL.md` Step 2 / Step 5.

## 공통 구조 (scratchpad 임시 저장소)

1. 최상위 main 워크트리 (임시 저장소 루트) — 최초 commit 1개
2. main 워크트리에서 `/worktree feature-a` (또는 `git worktree add ../feature-a -b feature-a`) → 워크트리 A 생성. `setting-up-worktrees` 가 `branch.feature-a.js-super-parent=main` + `branch.feature-a.js-super-parent-base=<main 당시 HEAD SHA>` 기록
3. A 워크트리 **안에서** `/worktree feature-b` (재분기 — A 안에서 호출) → B 는 최상위 저장소 루트의 `.worktrees/feature-b` 아래 생성 (A 아래 중첩 아님). 분기 기준은 호출 위치인 A 의 현재 HEAD → `branch.feature-b.js-super-parent=feature-a` + `branch.feature-b.js-super-parent-base=<A 당시 HEAD SHA>` 기록

아래 6개 시나리오는 이 공통 구조를 전제로 한다. 상태를 되돌릴 수 없게 바꾸는 시나리오 ((c)(d)(f)) 는 각자 필요한 변형을 별도로 명시한다 — 순서대로 실행하면 뒤 시나리오가 앞 시나리오의 부모 워크트리를 지워버리므로, 시나리오 간에는 임시 저장소를 새로 파거나 공통 구조를 그때그때 재현한다.

---

### (a) 재분기 기록 있음 → 부모(A)로 머지 + 스택 안내

**셋업 명령**

- 공통 구조 그대로 재현
- B 워크트리에서 파일 수정 + commit (예: `src/foo.js` 신규)
- A 워크트리에서 별도 파일 수정 + commit (충돌 안 나는 파일, 예: `README.md`)

**실행**

- B 워크트리 안에서 `/merge-back-worktree` 호출

**기대 결과**

1. Guard 통과 (feature 워크트리 확인)
2. Step 1 — working tree clean → Step 2 자동 진행
3. Step 2 — `PARENT_BRANCH=feature-a`. 검증 4건 모두 통과 (① 기록 존재 + 자기 자신 아님 ② 로컬 실존 ③ A 워크트리에 체크아웃 ④ 분기점이 조상) → 판별 성공, 게이트 발동 없음
4. Step 3 — `git merge feature-a` 자동 흡수, 충돌 0
5. Step 4 — `PARENT_PATH` 는 **A 의 워크트리 경로** (main 워크트리 경로 아님). `git -C <A-path> merge --no-ff feature-b -m "Merge branch 'feature-b' into feature-a"` 실행
6. Step 4.5 — 대상 파일 0건 → "🔧 동기화할 환경 파일 없음. Step 5 진행." 안내
7. Step 5 — 종료 메시지 노출 후, `$PARENT_BRANCH`(`feature-a`) 가 `$TOP_BRANCH`(`main`) 와 다르므로 스택 안내가 추가로 노출된다:

   ```
   ℹ️ 이 머지는 직계 부모 (feature-a) 까지입니다. 최상위 (main) 반영은 부모 워크트리에서 `/merge-back-worktree` 를 다시 실행해주세요.
   ```

**확인 명령**

```bash
git -C <main-path> log --oneline -1   # 머지 전후 SHA 동일 — 최상위 브랜치가 안 바뀌었는지 확인
git -C <A-path> log --oneline -1      # feature-b 머지 커밋이 A 에 생성됐는지 확인
```

---

### (b) 기록 없음 → 판별 실패 게이트

**셋업 명령**

- 공통 구조 그대로 재현
- B 워크트리에서 `git config --unset branch.feature-b.js-super-parent` (기록 제거)

**실행**

- B 워크트리 안에서 `/merge-back-worktree` 호출

**기대 결과**

1. Guard 통과, Step 1 — clean → Step 2
2. Step 2 검증 ① 실패 (`PARENT_BRANCH` 가 비어있음) → **판별 실패 게이트** (`AskUserQuestion`) 발동. 실패 사유 "기록 없음" 이 질문 본문에 포함
3. options = 최상위 브랜치(`main`) + 다른 워크트리에 체크아웃된 브랜치들(`feature-a`, 자기 자신 제외) + "중단"
4. 조용한 최상위 자동 머지 없음 — Step 3/4 로 자동 진행하지 않고 사용자 응답을 기다린다

**확인 명령**

```bash
git config branch.feature-b.js-super-parent   # 출력 없음 (unset 확인)
```

- `AskUserQuestion` 호출 1건 발생, 그 전에 Step 3(`git merge`) 자동 진행 흔적이 없는지 확인

---

### (c) 기록 있음 + 부모 브랜치 삭제 → 게이트 (사유: 부모 브랜치 삭제됨)

**셋업 명령**

- 공통 구조 그대로 재현
- A 워크트리를 스킬 밖 raw git 으로 완전히 제거: `git worktree remove <A-path>` 후 `git branch -D feature-a` (브랜치 자체를 삭제 — B 의 `js-super-parent` 기록은 여전히 `feature-a` 를 가리킨다)

**실행**

- B 워크트리 안에서 `/merge-back-worktree` 호출

**기대 결과**

1. Guard 통과, Step 1 — clean → Step 2
2. Step 2 검증 ② 실패 (`git show-ref --verify --quiet refs/heads/feature-a` 실패 — 브랜치가 로컬에 실존하지 않음) → 판별 실패 게이트. 실패 사유 "부모 브랜치 삭제됨"
3. options = 최상위 브랜치(`main`) + 다른 워크트리에 체크아웃된 브랜치들(자기 자신 제외, 이 시점엔 없음) + "중단"
4. 조용한 최상위 자동 머지 없음

**확인 명령**

```bash
git show-ref --verify --quiet refs/heads/feature-a; echo $?   # 1 (브랜치 없음)
```

---

### (d) 기록 있음 + 부모 워크트리만 제거 (브랜치는 존속) → 게이트 (사유: 부모 미체크아웃)

**셋업 명령**

- 공통 구조 그대로 재현
- A 워크트리만 스킬 밖 raw git 으로 제거하고 브랜치는 남긴다: `git worktree remove <A-path>` (브랜치 삭제는 하지 않음 — `feature-a` ref 는 로컬에 그대로 있지만 어떤 워크트리에도 체크아웃돼 있지 않다)

**실행**

- B 워크트리 안에서 `/merge-back-worktree` 호출

**기대 결과**

1. Guard 통과, Step 1 — clean → Step 2
2. Step 2 검증 ①② 는 통과(기록 있음, 브랜치 로컬 실존) 하지만 검증 ③ 실패 (`PARENT_PATH` 를 못 찾음 — 어떤 워크트리에도 `feature-a` 가 체크아웃돼 있지 않음) → 판별 실패 게이트. 실패 사유 "부모 미체크아웃"
3. options = 최상위 브랜치(`main`) + 다른 워크트리에 체크아웃된 브랜치들(자기 자신 제외, 이 시점엔 없음) + "중단"
4. **"중단" 선택 시** 안내 1줄 출력 후 종료: "부모 워크트리를 먼저 만들고 (`/worktree <부모브랜치>`) 본 skill 을 재호출해주세요." — 실제 노출 시 `<부모브랜치>` 자리에 `feature-a` 가 채워진다

**확인 명령**

```bash
git worktree list | grep feature-a   # 출력 없음 (워크트리 제거됨)
git show-ref --verify --quiet refs/heads/feature-a; echo $?   # 0 (브랜치는 존속)
```

- "중단" 선택 직후 skill 이 즉시 종료하고, 위 안내 문구가 그대로 노출되는지 확인

---

### (e) 최상위 직계 워크트리 (main 에서 바로 분기) + 기록 있음 → 최상위로 머지, 스택 안내 없음

**셋업 명령**

- main 워크트리 **안에서** `/worktree feature-c` (재분기 아님 — main 에서 직접 호출) → `branch.feature-c.js-super-parent=main` + `branch.feature-c.js-super-parent-base=<main 당시 HEAD SHA>` 기록
- feature-c 안에서 파일 수정 + commit

**실행**

- feature-c 워크트리 안에서 `/merge-back-worktree` 호출

**기대 결과**

1. Guard 통과, Step 1 — clean → Step 2
2. Step 2 — `PARENT_BRANCH=main`. 검증 4건 모두 통과 → 판별 성공, 게이트 발동 없음
3. Step 3~4 정상 진행 — `PARENT_PATH` 는 main 워크트리 경로. `git -C <main-path> merge --no-ff feature-c -m "Merge branch 'feature-c' into main"` 실행 (최상위로 직접 머지)
4. Step 5 — `$PARENT_BRANCH`(`main`) 와 `$TOP_BRANCH`(`main`) 가 같으므로 스택 안내 문구가 노출되지 않는다 (재분기 이전의 기존 동작 그대로 보존)

**확인 명령**

```bash
git -C <main-path> log --oneline -1   # feature-c 머지 커밋이 main 에 직접 생성됐는지 확인
```

- 종료 메시지에 "이 머지는 직계 부모 (...) 까지입니다" 문구가 없는지 확인

---

### (f) 스킬 밖에서 브랜치를 옮겨 기록이 낡음 → 검증 4번이 게이트로 떨어뜨림

**셋업 명령**

- 공통 구조 그대로 재현 (A 존속) + A 워크트리 안에서 `/worktree feature-d` (재분기) → `branch.feature-d.js-super-parent=feature-a` + `branch.feature-d.js-super-parent-base=<SHA_X>` (당시 A 의 HEAD) 기록
- 스킬 밖 raw git 으로 feature-d 의 히스토리를 갈아엎는다: feature-d 워크트리 안에서 `git reset --hard <SHA_X 보다 훨씬 이전 커밋>` (예: 저장소 최초 commit). 브랜치를 지운 게 아니라 옮긴 것이므로 `branch.feature-d.*` 기록은 그대로 남고, 이제 `SHA_X` 는 현재 히스토리의 조상이 아니다

> 브랜치를 `git branch -D` 로 지웠다가 같은 이름으로 다시 만드는 방식으로는 이 상황이 만들어지지 않는다. git 은 브랜치를 삭제할 때 `branch.<이름>.*` 설정도 함께 지우므로 새 브랜치가 물려받을 기록이 남지 않는다. 기록을 남긴 채 낡게 만들려면 위처럼 브랜치를 옮겨야 한다.

**실행**

- 새 feature-d 워크트리 안에서 `/merge-back-worktree` 호출

**기대 결과**

1. Guard 통과, Step 1 — clean → Step 2
2. Step 2 검증 ①②③ 은 통과 (기록 있음: `PARENT_BRANCH=feature-a` / 로컬 실존 / A 에 체크아웃됨) 하지만 검증 ④ 실패 — `git merge-base --is-ancestor "$SHA_X" HEAD` 가 실패 (새 feature-d 의 HEAD 는 SHA_X 보다 훨씬 이전 커밋에서 분기했으므로 SHA_X 가 현재 히스토리의 조상이 아님) → 판별 실패 게이트. 실패 사유 "분기점이 조상이 아님"
3. 조용한 최상위 자동 머지 없음 — stale 기록을 신뢰해 `feature-a` 로 조용히 진행하지 않는다

**확인 명령**

```bash
git merge-base --is-ancestor <SHA_X> HEAD; echo $?   # 1 (조상 아님)
```

- `AskUserQuestion` 게이트가 발동하고, 조용히 `feature-a` 로 머지가 진행되지 않는지 확인

---

## Catch (공통)

- 6개 시나리오 모두에서 판별 실패 시 "조용한 최상위 fallback" 0건 (히스토리 추정으로 자동 진행 0건)
- (b)(c)(d)(f) 는 모두 `AskUserQuestion` 판별 실패 게이트가 발동하고 자동 진행하지 않음
- (a) 에서만 스택 안내 노출, (e) 에서는 스택 안내 노출 0건
- 판별 실패 게이트의 "중단" 선택 시 항상 동일 안내 문구: "부모 워크트리를 먼저 만들고 (`/worktree <부모브랜치>`) 본 skill 을 재호출해주세요."
- 머지 대상 결정에 `git worktree list` 순서나 커밋 히스토리 추정이 쓰이지 않음 — 기록(`js-super-parent` / `js-super-parent-base`) + 검증 4건만 신뢰
