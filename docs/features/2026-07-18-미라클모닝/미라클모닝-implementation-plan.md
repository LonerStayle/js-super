---
commit_policy: per-task
---

# 미라클모닝 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `subagent-driven-development` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 여러 워크트리의 하루치 활동을 워크트리별로 파악해 저장하는 `/goodnight` 와, 아침에 그 노트를 브리핑으로 읽는 `/goodmorning` 두 슬래시 커맨드를 추가한다.

**Architecture:** 두 개의 instruction-only 슬래시 커맨드. `/goodnight` 는 최상위 워크트리에서만 실행되며, 워크트리마다 보조 에이전트를 병렬로 붙여 git 상태·진행 문서·세션 기록을 깊게 조사한 요약을 취합하고, 위험 자동 판정 후 `.js-super/session-handoff/YYYY-MM-DD.md` 에 저장한다. `/goodmorning` 은 최신 노트를 찾아 경고 배너 우선으로 브리핑한다.

**Tech Stack:** Markdown instruction 커맨드 (bash 실행 스크립트 없음), git worktree, Claude Code 보조 에이전트(Task 도구).

**Spec inputs:**
- 미라클모닝-requirements.md — FR-1~11 (두 커맨드, 워크트리별 파악, 최상위 전용, 자동 경고, 출력 스타일)
- 미라클모닝-tech-design.md — instruction-only + 병렬 보조 에이전트 수집 + 날짜별 누적 저장 + `git worktree list` 최상위 판별

---

## 1. 단계별 작업

### Task 1: `/goodnight` 저장 커맨드

**Files:**
- Create: `commands/goodnight.md`

**Model**: sonnet

- [ ] **Step 1: `commands/goodnight.md` 작성**

파일 전체 내용(new file):

````markdown
---
description: "최상위 워크트리에서 실행해 프로젝트의 모든 워크트리 활동을 워크트리별로 파악하고, 위험이 있으면 경고 배너와 함께 .js-super/session-handoff/YYYY-MM-DD.md 핸드오프 노트로 저장."
argument-hint: "[추가로 강조하고 싶은 내용 자유 텍스트]"
disable-model-invocation: true
---

# Goodnight — 하루 마무리 핸드오프 저장 (최상위 워크트리 전용)

여러 워크트리로 나눠 작업한 하루를 마무리하며, 각 워크트리가 어디까지 갔고 다음에 무엇을 해야 하는지를 하나의 노트로 저장합니다. 다음 날 아침 `/goodmorning` 으로 이 노트를 읽습니다.

## 1. 사전 검증 — 최상위 워크트리 확인

1. `git worktree list` 를 실행합니다. 출력 첫 줄의 경로가 최상위 워크트리(main working tree)입니다.
2. 현재 실행 위치(cwd)가 첫 줄 경로와 같은지 확인합니다.
3. 다르면 저장하지 않고 아래를 안내한 뒤 종료합니다.

> ⚠️ `/goodnight` 은 최상위 워크트리에서 실행해야 합니다. 최상위 경로: `<첫 줄 경로>`. 그 폴더에서 다시 실행해주세요.

4. 같으면 다음 단계로 넘어갑니다.

## 2. 워크트리 열거

1. `git worktree list` 결과에서 모든 워크트리의 경로·브랜치·HEAD 를 정리합니다.
2. 워크트리 개수 N 을 기록합니다.

## 3. 워크트리별 활동 수집 (병렬 보조 에이전트)

워크트리 하나당 보조 에이전트 하나를 한 메시지에서 병렬로 호출합니다. 각 보조 에이전트에 담당 워크트리 경로를 주고 아래를 조사시킨 뒤, "진행상황 / 다음 할 일 / 주의점 / 위험신호" 네 항목의 구조화 요약만 받습니다.

각 보조 에이전트가 조사할 것:
- git 상태: 현재 브랜치, 최근 커밋 5개, `git status` 로 본 미커밋 변경, 최상위 브랜치 대비 ahead/behind
- 진행 문서: 담당 워크트리의 `docs/features/` 아래 최신 폴더의 requirements/tech-design/implementation-plan 존재 여부와 각 문서 `## 변경이력` 의 최신 항목
- 세션 기록: `~/.claude/projects/` 아래에서 담당 워크트리에 해당하는 세션 폴더의 세션 파일(`.jsonl`)을 깊게 분석해 최근 작업 내용·결정·미완료 사항을 파악. 폴더 이름은 워크트리 경로가 `-` 로 치환돼 있어 한글 워크트리는 폴더명만으로 구분이 어렵습니다. 세션 파일 안의 실제 작업 경로(cwd) 정보로 담당 워크트리와 매칭하세요. 최신 세션을 우선 보고, 오래된 세션은 요약 위주로만 봅니다.

메인 에이전트는 세션 원문을 직접 읽지 말고 각 보조 에이전트의 요약만 취합합니다.

## 4. 위험 자동 판정 + 경고 배너 결정

취합한 요약을 아래 위험 신호 체크리스트로 점검합니다.
- 미커밋 대량 변경 (수십 개 파일 이상)
- 실패한 테스트 흔적 또는 빌드 깨짐
- 미완료 배포 또는 미완료 마이그레이션
- 해결되지 않은 머지 충돌
- 세션에서 사용자가 남긴 명시적 경고·리마인더 요청

하나라도 해당하면 경고 배너를 만듭니다. 없으면 배너를 만들지 않습니다. 사용자가 커맨드 인자로 강조할 내용을 줬으면 노트와 배너 판정에 반영합니다.

경고 배너는 위험이 실제로 있을 때만, 눈에 확 띄게(🚨 마커 + 강한 문장) 만듭니다. 위험이 없으면 배너를 억지로 만들지 않습니다.

## 5. 노트 작성 + 저장

1. `.js-super/session-handoff/` 디렉토리가 없으면 만듭니다.
2. `.js-super/session-handoff/YYYY-MM-DD.md` 에 저장합니다. 같은 날짜 파일이 이미 있으면 덮어써 최신 상태로 갱신합니다.
3. 파일 구조:

```markdown
# 미라클모닝 핸드오프 — YYYY-MM-DD HH:MM

🚨 (위험이 있을 때만) 경고 배너 본문

## 개요
- 최상위 워크트리: <경로>
- 워크트리 수: N

## 워크트리: <이름> [<브랜치>]
### 진행상황
### 다음 할 일
### 주의점
```

위험이 없으면 배너 줄 자체를 넣지 않습니다. 워크트리마다 위 섹션을 반복하되 서로 섞이지 않게 독립 섹션으로 씁니다.

## 6. 출력 스타일 룰 (반드시 지킴)

- 사람이 읽기 위한 명확한 한국어로 씁니다.
- 비유·은유로 설명하지 않습니다. 사실을 그대로 적습니다.
- 불필요한 용어 병기를 하지 않습니다 (예: `안녕(hi)` 처럼 원어를 괄호로 덧붙이지 않음).

## 7. 저장 후 보고

메인 응답에 한 줄로 보고합니다: 저장 완료, 워크트리 N개, 경고 있음/없음, 저장 경로. 아침에 `/goodmorning` 으로 확인할 수 있다고 안내합니다.

## 8. 금지

- 최상위가 아닌 워크트리에서 저장하지 않습니다.
- 세션 기록 원문을 노트에 그대로 옮기지 않습니다 (요약만).
- 위험이 없는데 경고 배너를 만들지 않습니다.
- 비유법을 쓰지 않습니다.
````

- [ ] **Step 2: 핵심 섹션 존재 검증**

Run: `grep -cE "^## [1-8]\." commands/goodnight.md`
Expected: `8` (섹션 1~8 모두 존재)

Run: `grep -F "최상위 워크트리에서 실행" commands/goodnight.md`
Expected: 1건 이상 (FR-5 최상위 전용 가드 존재)

Run: `grep -F "disable-model-invocation: true" commands/goodnight.md`
Expected: 1건 (모델 자동 호출 차단, 명시 슬래시 호출 전용)

- [ ] **Step 3: Commit**

```bash
git add commands/goodnight.md
git commit -m "feat: /goodnight 핸드오프 저장 커맨드 추가"
```

### Task 2: `/goodmorning` 읽기 커맨드

**Files:**
- Create: `commands/goodmorning.md`

**Model**: sonnet

- [ ] **Step 1: `commands/goodmorning.md` 작성**

파일 전체 내용(new file):

````markdown
---
description: "최상위 워크트리의 .js-super/session-handoff/ 에서 가장 최근 핸드오프 노트를 찾아 브리핑으로 출력. 경고 배너가 있으면 맨 앞에 크게 먼저 표시."
argument-hint: ""
disable-model-invocation: true
---

# Goodmorning — 아침 핸드오프 브리핑

어제 `/goodnight` 으로 저장한 핸드오프 노트를 읽어, 각 워크트리에서 어디까지 했고 다음에 무엇을 해야 하는지를 브리핑합니다.

## 1. 최신 노트 찾기

1. `git worktree list` 첫 줄에서 최상위 워크트리 경로를 얻습니다.
2. `<최상위>/.js-super/session-handoff/` 에서 가장 최근 날짜(`YYYY-MM-DD.md`)의 노트 파일을 찾습니다.
3. 읽기는 어느 워크트리에서 실행해도 최상위 노트를 대상으로 합니다 (읽기는 파괴적 동작이 아니므로 실행 위치를 막지 않습니다).

## 2. 노트가 없을 때

아래를 안내하고 종료합니다.

> 저장된 핸드오프 노트가 없습니다. 최상위 워크트리에서 `/goodnight` 을 먼저 실행해주세요.

## 3. 브리핑 출력

1. 노트에 경고 배너가 있으면 브리핑 맨 앞에 그대로 크게 먼저 출력합니다.
2. 이어서 워크트리별 "진행상황 / 다음 할 일 / 주의점" 을 순서대로 출력합니다.
3. 경고 배너가 없으면 워크트리별 요약만 담백하게 출력합니다.

## 4. 출력 스타일 룰

- 노트 내용을 사실 그대로 전달합니다. 비유·은유를 넣지 않고, 불필요한 용어 병기를 하지 않습니다.
- 읽기 쉽게 정리하되 원래 의미를 바꾸지 않습니다.

## 5. 금지

- 노트에 없는 내용을 지어내지 않습니다.
- 경고 배너를 임의로 줄이거나 삭제하지 않습니다.
````

- [ ] **Step 2: 핵심 섹션 존재 검증**

Run: `grep -cE "^## [1-5]\." commands/goodmorning.md`
Expected: `5` (섹션 1~5 모두 존재)

Run: `grep -F "경고 배너가 있으면" commands/goodmorning.md`
Expected: 1건 이상 (FR-10 배너 우선 출력 존재)

Run: `grep -F "disable-model-invocation: true" commands/goodmorning.md`
Expected: 1건 (모델 자동 호출 차단, 명시 슬래시 호출 전용)

- [ ] **Step 3: Commit**

```bash
git add commands/goodmorning.md
git commit -m "feat: /goodmorning 아침 핸드오프 브리핑 커맨드 추가"
```

### Task 3: CLAUDE.md 결합 메모 추가

**Files:**
- Modify: `CLAUDE.md` (파일 끝에 새 섹션 append)

**Model**: sonnet

- [ ] **Step 1: CLAUDE.md 끝에 결합 메모 섹션 추가**

CLAUDE.md 파일 맨 끝에 아래 섹션을 append 합니다(기존 내용은 건드리지 않고 끝에만 추가).

**수정 후** (append 내용):

````markdown

## /goodnight + /goodmorning 결합 (v2.8.0+)

v2.8.0+ 에서 세션 핸드오프 커맨드 2종 추가 — `/goodnight` (저녁 저장) + `/goodmorning` (아침 브리핑). instruction-only 커맨드이며 여러 워크트리를 한 번에 파악한다. spec: `docs/features/2026-07-18-미라클모닝/`.

### 적용 범위 (2 본문 + 6 manifest = 8 파일)

- `commands/goodnight.md` (신규) — 최상위 워크트리 전용 저장. 워크트리별 병렬 보조 에이전트 수집 + 위험 자동 판정 + `.js-super/session-handoff/YYYY-MM-DD.md` 저장
- `commands/goodmorning.md` (신규) — 최신 노트 브리핑. 경고 배너 우선 출력
- `CLAUDE.md` (본 섹션)
- 6 manifest — 2.7.0 → 2.8.0

### 핵심 룰

- **D-1 저장은 최상위 워크트리 전용** — `git worktree list` 첫 줄이 최상위. 하위 워크트리에서 `/goodnight` 실행 시 저장하지 않고 최상위 경로 안내. 읽기(`/goodmorning`)는 어느 워크트리에서도 최상위 노트를 대상으로 허용
- **D-2 데이터 소스 = git + 진행 문서 + 세션 기록 종합** — 세션 기록은 깊게 분석하되 워크트리별 병렬 보조 에이전트로 분산해 메인 컨텍스트를 보호. 메인은 원문을 직접 읽지 않고 요약만 취합
- **D-3 경고는 자동 판정** — 위험 신호 체크리스트(미커밋 대량 변경 / 실패한 테스트 / 미완료 배포 / 미해결 충돌 / 사용자 명시 경고 요청)로 판정. 위험 있을 때만 배너, 없으면 담백
- **D-4 저장 = 날짜별 누적** — `.js-super/session-handoff/YYYY-MM-DD.md`. 같은 날 재실행 시 덮어쓰기. `.js-super/` glob 에 흡수돼 gitignore 수정 불필요
- **D-5 출력 스타일** — 비유법 금지 + 불필요한 용어 병기 금지 + 사람이 읽기 위한 명확한 한국어. 두 커맨드 본문에 동일하게 박힘
- **D-6 자동 발동 차단 = `disable-model-invocation: true`** — 두 커맨드 frontmatter 에 명시. 모델이 대화 중 임의로 호출하지 못하고 사용자 슬래시 명시 호출만 발동. description 에는 발동 조건 문구를 넣지 않음 (frontmatter 필드가 보장하므로 불필요)

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| goodnight 최상위 가드 약화 | 하위 워크트리에서 저장 → 노트가 여러 위치에 흩어짐 |
| 세션 수집 병렬 분산 제거 | 메인 컨텍스트 폭발 (세션 기록 깊은 분석 요구와 충돌) |
| 경고 배너 억지 생성 | 위험 없는데 오버 배너 → 사용자 피로 (FR-8 위반) |
| 출력 스타일 룰 한쪽 누락 | 비유법·용어 병기 재발 (FR-11 위반) |
| `disable-model-invocation: true` 누락 | 모델이 대화 중 커맨드를 자동 호출 → 사용자 의도 없이 실행 |

### 회귀 catch grep

```bash
# 두 커맨드 존재
test -f commands/goodnight.md && test -f commands/goodmorning.md && echo OK
# expected: OK

# 최상위 전용 가드
grep -F "최상위 워크트리에서 실행" commands/goodnight.md
# expected: >= 1

# 출력 스타일 룰 (비유법 금지) 두 커맨드 모두
grep -lF "비유" commands/goodnight.md commands/goodmorning.md
# expected: 2 lines

# 모델 자동 호출 차단 두 커맨드 모두
grep -lF "disable-model-invocation: true" commands/goodnight.md commands/goodmorning.md
# expected: 2 lines

# 결합 메모 본문 존재
grep -cF "## /goodnight + /goodmorning 결합 (v2.8.0+)" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- 2 command 본문 + CLAUDE.md + 6 manifest. 다른 skill / scripts / hooks / settings 영향 0
- 사용자 환경 출력 — `.js-super/session-handoff/` (gitignored, 저장소 외 산출물)
- `using-superpowers` 본문 변경 X
- 자동 발동 경로 없음 — 명시 슬래시 호출만
````

- [ ] **Step 2: 결합 메모 존재 검증**

Run: `grep -cF "## /goodnight + /goodmorning 결합 (v2.8.0+)" CLAUDE.md`
Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 에 /goodnight + /goodmorning 결합 메모 추가"
```

### Task 4: 6 manifest 버전 bump + dogfood 검증

**Files:**
- Modify: `package.json`, `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `gemini-extension.json`

**Model**: haiku

- [ ] **Step 1: 6 manifest 버전 2.7.0 → 2.8.0 bump**

`scripts/bump-version.sh` 가 있으면 실행해 6개 파일을 일괄 갱신합니다.

Run: `bash scripts/bump-version.sh 2.8.0`

스크립트가 없거나 인자 형식이 다르면, 6개 파일의 version 필드(`.claude-plugin/marketplace.json` 은 `plugins[0].version`)를 각각 `2.8.0` 으로 직접 수정합니다. `.claude-plugin/plugin.json` 의 `upstream.version` 은 건드리지 않습니다.

- [ ] **Step 2: 버전 일괄 확인**

Run: `grep -RF '"version": "2.8.0"' package.json .claude-plugin/plugin.json .cursor-plugin/plugin.json .codex-plugin/plugin.json gemini-extension.json | wc -l`
Expected: `5` (marketplace.json 은 중첩 경로라 별도 확인)

Run: `grep -F '2.8.0' .claude-plugin/marketplace.json`
Expected: 1건 이상

- [ ] **Step 3: dogfood 수동 검증 시나리오 (실행자가 확인)**

아래는 커밋 후 사용자가 직접 돌려보는 시나리오입니다(자동 테스트 아님).
- S1: 최상위 워크트리에서 `/goodnight` → 모든 워크트리가 각각 진행/다음/주의 섹션으로 노트에 생성되는지
- S2: 하위 워크트리에서 `/goodnight` → 저장 안 하고 최상위 경로 안내하는지
- S3: 위험 상태 → 경고 배너 생성 / 깨끗한 상태 → 배너 없음
- S4: `/goodmorning` → 최신 노트 브리핑 + 배너 있으면 맨 앞
- S5: 노트·브리핑에 비유법·용어 병기 없음 육안 확인

- [ ] **Step 4: Commit**

```bash
git add package.json .claude-plugin/plugin.json .cursor-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json gemini-extension.json
git commit -m "chore: v2.8.0 — 미라클모닝 핸드오프 커맨드 릴리즈"
```

---

## 2. 위험 코드 지점

- `commands/goodnight.md` §3 (세션 기록 깊은 분석) — side-effect: 워크트리·세션이 많으면 실행 시간·토큰 급증 (mitigation: 워크트리별 병렬 보조 에이전트 분산 + "최신 세션 우선, 오래된 세션 요약" 지시를 본문에 명시)
- `commands/goodnight.md` §5 (저장) — side-effect: 같은 날짜 파일 덮어쓰기로 같은 날 이전 저장 소실 (mitigation: 하루 마무리 1회 실행 전제 + 재실행은 의도적 최신 갱신)
- `commands/goodnight.md` §4 (위험 판정) — side-effect: LLM 판정이 위험을 놓치거나 과하게 경고 (mitigation: 위험 신호 체크리스트를 본문에 명시)
- `commands/goodnight.md` §1 / `commands/goodmorning.md` §1 (동시 실행) — race: 여러 워크트리에서 동시 실행 시 노트 파일 경합 (mitigation: 1인 순차 실행 전제, 별도 잠금 없이 인지만)

## 3. 롤백 전략

- Code: Task 1~4 의 commit 을 `git revert` (또는 최근 4개 커밋 `git reset`). 신규 파일 2개(`commands/goodnight.md`, `commands/goodmorning.md`) 삭제, CLAUDE.md 섹션 revert, 6 manifest 를 2.7.0 으로 되돌림.
- 산출물: `.js-super/session-handoff/` 는 gitignored 라 삭제해도 저장소에 영향 없음.
- Config: 별도 feature flag 없음.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-07-18 20:31] [구현계획서-수정]
- **id**: CH-20260718-004
- **이유**: 신규 구현계획서 — 커맨드 2개 작성 + CLAUDE.md 결합 메모 + 6 manifest bump (총 4 task). 리뷰 중 `disable-model-invocation: true` 추가 및 저장 디렉토리명 session-handoff 반영
- **무엇이**: 미라클모닝-implementation-plan.md 전체 (Task 1~4, §2 위험 코드 지점, §3 롤백 전략)
- **영향범위**: 없음 (최초 생성). 연관 항목: CH-20260718-001, CH-20260718-003

### [2026-07-18 20:38] [코드-수정] (batch: tasks 1..4)
- **id**: CH-20260718-005
- **이유**: 미라클모닝 세션 핸드오프 커맨드 2종 + CLAUDE.md 결합 메모 + v2.8.0 릴리즈 구현 완료
- **무엇이**: commands/goodnight.md, commands/goodmorning.md, CLAUDE.md, package.json, .claude-plugin/plugin.json, .cursor-plugin/plugin.json, .codex-plugin/plugin.json, .claude-plugin/marketplace.json, gemini-extension.json
- **영향범위**: 신규 커맨드 2개 (기존 skill/command 동작 무변경), CLAUDE.md 결합 메모 섹션, 6 manifest 버전 필드
- **위험 카테고리**: none (전부 지시문 markdown + 버전 문자열, risk 3-checklist 0/3)
- **task별 세부 (4건)**:
  - Task 1: `commands/goodnight.md` — /goodnight 저장 커맨드 (none) — commit: `dadafdc`
  - Task 2: `commands/goodmorning.md` — /goodmorning 브리핑 커맨드 (none) — commit: `0fdae13`
  - Task 3: `CLAUDE.md` — /goodnight + /goodmorning 결합 메모 추가 (none) — commit: `174832a`
  - Task 4: 6 manifest — v2.8.0 bump (none) — commit: `ad09812`
- **연관 commits**: `dadafdc`, `0fdae13`, `174832a`, `ad09812`
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260718-004
