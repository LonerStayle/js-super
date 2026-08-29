---
commit_policy: per-task
---

# 워크트리-재분기-네이밍 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** `/worktree` 에서 이름 없이 작업 설명만 주면 AI 가 브랜치 이름을 지어 제안한다. 재분기 (분기 기준 브랜치 ≠ 메인 브랜치) 면 `<부모브랜치>__<자식이름>` 형식으로 부모 관계가 이름에 남고 다단계는 누적된다. 사용자가 명시한 이름은 그대로 존중한다.

**Architecture:** `setting-up-worktrees` 스킬의 Step 1 (이름 추출) 을 "이름 해석" 단계로 확장한다 — 명시 이름 / AI 제안 분기 + `부모브랜치__자식이름` 규칙 + 확정 휴리스틱. 재분기 판별은 Step 0 이 이미 캡처하는 두 값 (`BASE_BRANCH` / `MAIN_BRANCH`) 의 비교로 한다 (스택 안내와 동일 기준). 새 스크립트 · 훅 변경 없음.

**Tech Stack:** 마크다운 skill/command 본문 + CLAUDE.md 결합 메모 + fixture README

**Spec inputs:**
- 워크트리-재분기-네이밍-requirements.md — FR-1 AI 제안 (양쪽 시점) / FR-2 `부모__자식` / FR-3 누적 / FR-4 명시 이름 존중 / FR-5 확정 재량 / FR-6 저장소 관례
- 워크트리-재분기-네이밍-tech-design.md — D-1 (LLM 판단, 스킬 본문) / D-2 (브랜치 비교 판별) / D-3 (폴더 = 브랜치명 그대로, 변경 0) / D-4 (자식 이름 제약) / D-5 (확정 휴리스틱) / D-6 (detached HEAD fallback)

> **슬림 plan 관례** (v2.5.1 선례): 대상이 한국어 skill/command 본문이라 `**원본**` 라벨 블록은 의도적 생략 (내부 코드 펜스가 plan_byte_check 파서와 충돌). 각 task 의 `**수정 후**` 블록이 최종 상태의 완전한 본문이며, 실행자는 그 내용을 그대로 (재작성 없이) 배치한다. 앵커는 라인 번호 대신 고유 텍스트로 지정한다.

---

## 1. 단계별 작업

### Task 1: 스킬 본문 — Step 1 이름 해석 개편 + 규칙 반영

**Files:**
- Modify: `skills/setting-up-worktrees/SKILL.md`

**Model**: sonnet

**검증**: `grep -cF "부모브랜치__자식이름" skills/setting-up-worktrees/SKILL.md` ≥ 1, `grep -c "Parse branch names" skills/setting-up-worktrees/SKILL.md` = 0, 기존 v2.9.0 grep (`MAIN_ROOT` ≥ 3 / `Step 3.5` ≥ 2 / Step 4 안 for-loop add 0) 무손상.

같은 파일의 mechanical 본문 수정 5건 — same-file 묶음 룰 (같은 파일 + 테스트 경계 없음 + mechanical) 로 1 task multi-step.

- [ ] **Step 1: `**Step 1 — Parse branch names from user's message**` 로 시작하는 섹션 (해당 헤더 + 바로 아래 문단 1개) 을 다음으로 교체**

**수정 후** (`skills/setting-up-worktrees/SKILL.md` Step 1 섹션):

```markdown
**Step 1 — 이름 해석 (명시 이름 / AI 제안 분기)**

사용자 메시지에서 브랜치 이름 또는 작업 설명을 추출해 `BRANCHES=(...)` 를 확정한다. Korean ticket-style names like `<TICKET>-<번호>-<설명>` are fine (UTF-8 OK). Do NOT ask about env files — those are auto-detected.

1. **이름 명시** — 사용자가 브랜치 이름을 줬으면 그대로 쓴다. 네이밍 규칙을 덮어씌우거나 "더 좋은 이름" 을 제안하지 않는다.
2. **설명만 있고 이름 없음** — 메인이 이름을 생성해 제안한다. **부모브랜치__자식이름 규칙**:
   - `BASE_BRANCH` ≠ `MAIN_BRANCH` (재분기) → `<BASE_BRANCH>__<자식이름>`. 구분자는 밑줄 두 개 (`__`). 부모 이름에 이미 `__` 가 있으면 그대로 누적된다 (`a__b` 에서 분기 → `a__b__c`).
   - `BASE_BRANCH` = `MAIN_BRANCH` → 접두어 없이, 저장소의 기존 브랜치 관례 (언어 · 스타일 · 접두어 유무) 를 참고해 짓는다.
   - `BASE_BRANCH` 가 비어 있으면 (detached HEAD) → 접두어 생략 + 한 줄 안내: "부모 브랜치를 알 수 없어 접두어를 생략했습니다".
   - AI 가 새로 짓는 부분 (재분기면 자식 이름, 메인 기준이면 이름 전체) 에는 `__` 를 넣지 않는다 — 부모 구분자로 예약 (공백 → 하이픈). `/` 는 자식 이름에 넣지 않는다 (새 폴더 중첩 층 방지 — 부모에게서 물려받은 `/` 는 그대로 수용). 메인 기준 이름은 저장소 관례가 슬래시 접두어를 쓰는 경우에만 `/` 허용.
   - AI 가 짓는 이름의 언어 · 스타일은 저장소의 기존 브랜치 관례를 따른다 (재분기 자식 부분 포함).
3. **확정** — AI 가 이름을 생성한 경우 기본은 `AskUserQuestion` 으로 제안 이름 (후보 1~3개) 을 확인받고 생성한다. 사용자가 "바로 만들어 / 알아서 해줘" 류 속행 신호를 이미 준 상황이면 확인 없이 생성하고 결과 이름을 알린다. 명시 이름은 질문 없이 그대로.
```

- [ ] **Step 2: Defaults 표의 `| Branch creation |` 행 바로 아래에 다음 행 추가**

**수정 후** (`skills/setting-up-worktrees/SKILL.md` Defaults 표 추가 행):

```markdown
| 브랜치 네이밍 제안 | 이름 미지정 (설명만) 시 메인이 이름 생성 제안 — 재분기 (`BASE_BRANCH` ≠ `MAIN_BRANCH`) 면 `<부모>__<자식>` (누적), 메인 기준이면 접두어 없이 저장소 관례. 사용자 명시 이름은 그대로 (Step 1) |
```

- [ ] **Step 3: frontmatter description 끝에 문장 추가**

description 의 마지막 문장 `Invoked from inside a worktree, ... branches from the invoking worktree's current HEAD.` 뒤에 이어붙인다 (한 줄 유지):

```markdown
 이름 없이 작업 설명만 주면 브랜치 이름을 AI 가 제안한다 — 재분기 시 `<부모브랜치>__<자식이름>` 형식 (누적 가능), 사용자가 명시한 이름은 그대로 존중.
```

- [ ] **Step 4: Anti-Patterns 표 끝에 2행 + Red Flags 표 끝에 1행 추가**

**수정 후** (`skills/setting-up-worktrees/SKILL.md` Anti-Patterns 추가 행):

```markdown
| 사용자가 명시한 브랜치 이름을 개명하거나 "더 좋은 이름" 을 제안 | 명시 이름은 그대로 쓴다. 제안은 이름 미지정 (설명만) 일 때만. |
| AI 제안 자식 이름에 `__` 또는 `/` 포함 | `__` 는 부모 구분자로 예약. `/` 는 새 폴더 중첩 층 유발 (부모에게서 물려받은 `/` 는 수용). 공백은 하이픈으로. |
```

**수정 후** (`skills/setting-up-worktrees/SKILL.md` Red Flags 추가 행):

```markdown
| "사용자가 준 이름이 아쉽다 — 더 좋은 이름을 제안하자" | 명시 이름은 그대로 쓴다. 제안은 이름 미지정일 때만 (Step 1). |
```

- [ ] **Step 5: Acceptance 목록 끝에 항목 추가**

**수정 후** (`skills/setting-up-worktrees/SKILL.md` Acceptance 추가 항목):

```markdown
11. 이름 미지정 호출에서는 AI 이름 제안이 이뤄졌고 (재분기면 `<부모>__<자식>` 형식), 사용자가 명시한 이름은 개명 없이 그대로 쓰였다.
```

- [ ] **Step 6: 검증 grep 실행 + Commit**

Run: `grep -cF "부모브랜치__자식이름" skills/setting-up-worktrees/SKILL.md; grep -c "Parse branch names" skills/setting-up-worktrees/SKILL.md; grep -cF "MAIN_ROOT" skills/setting-up-worktrees/SKILL.md; grep -cF "Step 3.5" skills/setting-up-worktrees/SKILL.md`
Expected: 1 이상 / 0 / 3 이상 / 2 이상

```bash
git add skills/setting-up-worktrees/SKILL.md
git commit -m "feat(worktree): 이름 해석 단계 — AI 네이밍 제안 + 부모브랜치__자식이름 규칙"
```

### Task 2: 커맨드 안내 동기 (`commands/worktree.md`)

**Files:**
- Modify: `commands/worktree.md`

**Model**: sonnet

**검증**: `grep -cF "부모브랜치__자식이름" commands/worktree.md` ≥ 1, 설명만 주는 사용 예 블록 존재.

- [ ] **Step 1: frontmatter description 끝에 문장 추가**

기존 `... 단수/복수 모두 지원.` 뒤에 이어붙인다:

```markdown
 이름 없이 설명만 주면 브랜치 이름을 AI 가 제안합니다 (재분기 시 `부모__자식` 형식).
```

- [ ] **Step 2: `## 사용 예` 의 자연어 예시 뒤에 사용 예 1개 추가**

**수정 후** (`commands/worktree.md` 사용 예 추가 블록):

````markdown
**이름 없이 설명만 (AI 가 이름 제안):**
```
/worktree
알림 기능 작업할 워크트리 하나 파줘
```
````

- [ ] **Step 3: `## 동작` 의 분기 기준 bullet 바로 아래에 bullet 추가**

**수정 후** (`commands/worktree.md` 동작 추가 bullet):

```markdown
- **브랜치 네이밍 제안 (부모브랜치__자식이름 규칙)**: 이름 없이 작업 설명만 주면 AI 가 이름을 지어 제안. 재분기 (분기 기준 브랜치 ≠ 메인 브랜치) 면 `<부모브랜치>__<자식이름>` 형식으로 부모 관계가 이름에 남고, 다단계 재분기는 `a__b__c` 처럼 누적. 메인 기준이면 접두어 없이 저장소 관례를 따름. 사용자가 명시한 이름은 그대로 존중 (개명 제안 없음).
```

- [ ] **Step 4: 검증 grep + Commit**

Run: `grep -cF "부모브랜치__자식이름" commands/worktree.md`
Expected: 1 이상

```bash
git add commands/worktree.md
git commit -m "docs(worktree): 커맨드 안내에 AI 네이밍 제안 + 부모__자식 규칙 동기"
```

### Task 3: fixture H20 신규 + 인덱스 등록

**Files:**
- Create: `skills/js-super-sub-driven/tests/H20-worktree-naming/README.md`
- Modify: `skills/js-super-sub-driven/tests/README.md`

**Model**: sonnet

**검증**: fixture 파일 존재 (`test -f` OK), `tests/README.md` 인덱스에 H20 행 1개 + 섹션 헤더가 H20 까지 포함.

- [ ] **Step 1: fixture README 작성**

**수정 후** (`skills/js-super-sub-driven/tests/H20-worktree-naming/README.md` 전체, 신규):

````markdown
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
````

- [ ] **Step 2: `skills/js-super-sub-driven/tests/README.md` 인덱스 등록**

`## v2.9.0 이후 fixtures (H14~H19)` 헤더를 `(H14~H20)` 으로 갱신하고, 그 표의 H19 행 아래에 다음 행 추가:

```markdown
| H20-worktree-naming | `/worktree` 이름 해석 — AI 네이밍 제안 + 재분기 `부모__자식` 누적 / 명시 이름 존중 / detached HEAD fallback 5 시나리오 |
```

- [ ] **Step 3: 검증 + Commit**

Run: `test -f skills/js-super-sub-driven/tests/H20-worktree-naming/README.md && grep -c "H20-worktree-naming" skills/js-super-sub-driven/tests/README.md`
Expected: 1 이상

```bash
git add skills/js-super-sub-driven/tests/H20-worktree-naming/README.md skills/js-super-sub-driven/tests/README.md
git commit -m "test(worktree): H20 재분기 네이밍 fixture + 인덱스 등록"
```

### Task 4: CLAUDE.md 결합 메모

**Files:**
- Modify: `CLAUDE.md`

**Model**: sonnet

**검증**: `grep -cF "## 워크트리 브랜치 네이밍 제안 결합" CLAUDE.md` ≥ 1, 신규 bash 블록이 eval 러너 파싱 형식 (`bash` 펜스 + `# expected:`) 을 따름.

- [ ] **Step 1: CLAUDE.md 맨 끝 (마지막 섹션 뒤) 에 신규 섹션 추가**

**수정 후** (`CLAUDE.md` 추가 섹션 전체):

````markdown
## 워크트리 브랜치 네이밍 제안 결합 (재분기 `부모__자식`)

`/worktree` 에서 이름 없이 작업 설명만 주면 AI 가 브랜치 이름을 제안한다. 재분기 판별은 브랜치 비교 (`BASE_BRANCH` ≠ `MAIN_BRANCH`) — 스택 구조 안내 (v2.9.0+) 와 동일 기준. 재분기면 `<부모브랜치>__<자식이름>` 형식으로 누적되고, 사용자 명시 이름은 그대로 존중한다. spec: `docs/features/2026-08-29-워크트리-재분기-네이밍/`.

### 핵심 룰

- **N-1 명시 이름 존중** — 사용자가 이름을 주면 개명 · 제안 없이 그대로 (FR-4). 제안은 이름 미지정일 때만
- **N-2 판별 = 브랜치 비교** — 경로 (워크트리 안인지) 가 아니라 분기 기준 브랜치 ≠ 메인 브랜치. 메인 워크트리에서 feature 브랜치 체크아웃 상태로 분기해도 접두어가 붙는다 (의도)
- **N-3 생성 이름 제약** — AI 가 새로 짓는 부분에 `__` 금지 (구분자 예약). `/` 는 자식 이름에 금지 (새 중첩 층 방지 — 부모에게서 물려받은 `/` 는 수용), 메인 기준 이름은 저장소 관례를 따름. 명시 이름에는 미적용
- **N-4 skill ↔ commands 동기** — 마커 리터럴 `부모브랜치__자식이름` 이 양쪽에 존재해야 함. 한쪽만 고치면 안내와 동작이 어긋남
- **N-5 훅 · Step 4 불변** — 이름 해석은 Step 1 에서 끝난다. `git worktree add ` 개별 호출 규칙 (v2.9.0) 과 `hooks/worktree-memory-symlink` 변경 0

### 회귀 catch grep

```bash
grep -cF "부모브랜치__자식이름" skills/setting-up-worktrees/SKILL.md commands/worktree.md
# expected: 각 1 이상

grep -c "Parse branch names" skills/setting-up-worktrees/SKILL.md
# expected: 0

test -f skills/js-super-sub-driven/tests/H20-worktree-naming/README.md && echo OK
# expected: OK
```

### 영향 범위

- skill 본문 1 + commands 1 + fixture 2 (신규 README + 인덱스) + CLAUDE.md. 버전 bump 는 main 전용 룰에 따라 main 에서
- `worktree-merge-back` / `worktree-remove` — 변경 0 (`__` 파싱 부모 판별은 범위 밖, tech-design §2 승계)
- `hooks/` / `scripts/` / og-* / auto-* 영향 0. 기존 워크트리 · 브랜치 이름 소급 변경 없음
````

- [ ] **Step 2: 검증 + Commit**

Run: `grep -cF "## 워크트리 브랜치 네이밍 제안 결합" CLAUDE.md`
Expected: 1

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): 워크트리 브랜치 네이밍 제안 결합 메모 + 회귀 grep"
```

### Task 5: 전체 회귀 검증 (코드 변경 없음)

**Files:** 없음 (읽기 전용)

**Model**: haiku

**검증**: 신규 grep 전부 기대값 일치 + 기존 v2.9.0 grep 무손상 + eval 러너 룰 수집 ≥ 100.

- [ ] **Step 1: 신규 + 기존 회귀 grep 일괄 실행**

Run:
```bash
grep -cF "부모브랜치__자식이름" skills/setting-up-worktrees/SKILL.md commands/worktree.md
grep -c "Parse branch names" skills/setting-up-worktrees/SKILL.md
test -f skills/js-super-sub-driven/tests/H20-worktree-naming/README.md && echo OK
grep -cF "MAIN_ROOT" skills/setting-up-worktrees/SKILL.md
grep -cF "Step 3.5" skills/setting-up-worktrees/SKILL.md
awk '/\*\*Step 4/,/\*\*Step 5/' skills/setting-up-worktrees/SKILL.md | grep -c "for BR in" || true
```
Expected: 각 1 이상 / 0 / OK / 3 이상 / 2 이상 / 0

- [ ] **Step 2: eval 러너 룰 수집 확인**

Run: `python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"`
Expected: 100 이상 (직전 실행 대비 감소 없음)

- [ ] **Step 3: 본 task 는 실행 모드의 변경이력 규칙에 따라 [검증] entry 로 기록 — 계획서 footer append 만 발생 (코드 파일 변경 없음), 커밋은 end-of-run [log] 묶음에 포함**

## 2. 위험 코드 지점

| R | 위치 | 위험 | 완화 |
|---|---|---|---|
| R-1 | plan 전체 | 이름 길이 누적 (다단계) | 수용 — FR-3 사용자 명시 선택. 코드 지점 없음 |
| R-2 | Task 1 ↔ Task 2 | skill ↔ commands 미동기 회귀 | 마커 리터럴 `부모브랜치__자식이름` 양쪽 grep (Task 4 결합 메모 + Task 5 일괄 실행) |
| R-3 | Task 1 Step 1 | Step 4 의 `git worktree add ` 개별 호출 규칙 훼손 → 훅 미발화 | Task 1 은 Step 1 섹션만 수정. Task 5 에서 v2.9.0 awk grep 재실행으로 확인 |
| R-4 | Task 1 Step 4 | 명시 이름 개명 제안 (FR-4 위반) 재발 | Anti-Patterns 2행 + Acceptance 11 로 본문 고정 |

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 09:13] [구현계획서-수정]
- **id**: CH-20260829-003
- **이유**: 신규 피처 구현계획서 (auto-flow) + verifying-spec 무맥락 검증 채택 지적 5건 반영 (Red Flags 갱신 Step 추가 / 재분기 자식 이름 관례 문구 승계 / `__`·`/` 금지 범위 정밀화 2건 / Task 5 [검증] 문구 모순 해소)
- **무엇이**: 워크트리-재분기-네이밍-implementation-plan.md 전체 (Task 1~5 + §2 위험 코드 지점)
- **영향범위**: 없음 (최초 생성). plan_byte_check PASS (슬림 plan 관례 — 원본 블록 0건). verifying-spec — A축 D-1~D-6/R 4건/FR-1~6 매핑 완료, 모순 0
- **연관 항목**: CH-20260829-002

### [2026-08-29 09:20] [코드-수정] (batch: tasks 1..4)
- **id**: CH-20260829-004
- **이유**: `/worktree` AI 브랜치 네이밍 제안 + 재분기 `부모__자식` 규칙 구현 (wave-parallel 실행, spec reviewer 4/4 ✅)
- **무엇이**: skills/setting-up-worktrees/SKILL.md, commands/worktree.md, skills/js-super-sub-driven/tests/H20-worktree-naming/README.md (신규), skills/js-super-sub-driven/tests/README.md, CLAUDE.md
- **영향범위**: 워크트리 생성 흐름의 이름 결정 단계만. hooks / scripts / worktree-merge-back / worktree-remove / og-* / auto-* 영향 0
- **위험 카테고리**: none (마크다운 본문 수정만 — 3-checklist 트리거 0)
- **task별 세부 (4건)**:
  - Task 1: `skills/setting-up-worktrees/SKILL.md` — Step 1 이름 해석 개편 + Defaults/description/Anti-Patterns/Red Flags/Acceptance (`none`) — commits: `0da39f6`
  - Task 2: `commands/worktree.md` — 안내 동기 (description + 사용 예 + 동작 bullet) (`none`) — commits: `406e8e1`
  - Task 3: `skills/js-super-sub-driven/tests/{H20-worktree-naming/README.md,README.md}` — fixture 신규 + 인덱스 (`none`) — commits: `241667c`
  - Task 4: `CLAUDE.md` — 결합 메모 + 회귀 grep (`none`) — commits: `73169e1`
- **연관 commits**: 8cd80bd..73169e1
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260829-003

### [2026-08-29 09:20] [검증] (task: Task 5 — 전체 회귀 검증)
- **id**: CH-20260829-005
- **이유**: 신규 규칙 반영 + 기존 v2.9.0 결합 무손상 확인 (릴리즈 전 sanity)
- **무엇이**: 마커 grep (skill/commands 각 1) / 옛 Step 1 헤더 잔존 0 / H20 존재 OK / MAIN_ROOT 17 / Step 3.5 4 / Step 4 for-loop 0 / eval 룰 수집 150건
- **결과**: PASS — 7/7 기대값 일치
- **연관 항목**: CH-20260829-004
