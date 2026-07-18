---
commit_policy: per-task
---

# /update-claude-md 커맨드 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `executing-plans` (인라인 모드, 권장 — task 2개) 또는 `js-super-sub-driven` (보조 에이전트 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 기존 CLAUDE.md 의 구체값(경로·구조·포트·파일명·함수/클래스명)만 실제 프로젝트와 대조해 갱신하고 본문 규약은 보존하는 instruction-only 슬래시 커맨드 `commands/update-claude-md.md` 를 작성한다.

**Architecture:** instruction-only 슬래시 커맨드 1 파일. 메인 에이전트가 본문 instruction 을 따라 Read/Grep/Glob/Bash(탐색) + AskUserQuestion + Edit 로 동작 (`new-skill.md` 패턴). bash 스크립트·외부 의존 없음.

**Tech Stack:** Markdown (frontmatter + 본문 instruction). Claude Code slash command.

**Spec inputs:**
- update-claude-md-requirements.md — FR-1..FR-12 (명시 호출 / 탐색 / 0건 중단 / 대상 선택 / 검증 기반 갱신 / 승인 게이트 / 본문 보존 / 버전 히스토리)
- update-claude-md-tech-design.md — 검증 기반 판별(결정 1), instruction-only(결정 2), 신뢰도 gradient(결정 3), 대상 범위(결정 4), 승인 granularity(결정 5), 버전 히스토리(결정 6)

**범위:** 커맨드 파일 1개만. manifest 버전 bump / CLAUDE.md 결합 메모 / README 소개는 이번 범위 밖 (사용자 결정).

**Frontmatter 결정 — `disable-model-invocation: true`:** 이 커맨드는 사용자 명시 호출 전용(FR-1)이라 frontmatter 에 `disable-model-invocation: true` 를 넣는다. 이걸 켜면 Claude Code 가 커맨드를 SlashCommand 도구 자동 호출 후보에서 제외하고, 그 결과 **description 이 세션 컨텍스트 윈도우에 실리지 않아 토큰을 아낀다**. 오직 사용자가 `/update-claude-md` 를 직접 입력할 때만 실행된다. description 도 "명시 호출 시 발동" 같은 군더더기 없이 사람용 짧은 설명으로 유지.

---

## 1. 단계별 작업

### Task 1: commands/update-claude-md.md 작성

**Files:**
- Create: `commands/update-claude-md.md`

**Model**: sonnet

- [ ] **Step 1: 커맨드 파일 전체 작성**

아래 내용을 그대로 `commands/update-claude-md.md` 로 작성한다.

**수정 후** (`new file: commands/update-claude-md.md`):

````markdown
---
description: "기존 CLAUDE.md 의 구체값(경로·구조·포트·파일명·함수/클래스명)만 실제 프로젝트와 대조해 갱신. 본문 규약은 미변경, 변경 전 구버전은 히스토리 보관."
argument-hint: "[<CLAUDE.md 경로>] [\"포트는 8444로\" 같은 지정 값...]"
disable-model-invocation: true
---

# /update-claude-md — CLAUDE.md 구체값 동기화

기존 `CLAUDE.md` 안의 **프로젝트마다 달라지는 구체값**(파일·폴더 경로, 폴더·파일 구조, 포트 번호, 파일명, 함수·클래스명)만 실제 프로젝트와 대조해 갱신합니다. 워크플로우 룰·톤 규칙·안전성 원칙·버전 태그·결합 메모 같은 **본문 규약은 절대 건드리지 않습니다**. 변경 직전에는 구버전을 히스토리로 보관해 나중에 열람할 수 있게 합니다.

핵심 원칙: **실제 프로젝트와 대조 가능한 사실만 후보로 삼고, 확인된 불일치만, 사용자 승인 후에만 반영합니다.** 애매하면 건드리지 않습니다.

## 1. 대상 CLAUDE.md 탐색

현재 프로젝트 루트부터 하위까지 `CLAUDE.md` 파일들을 Glob 으로 수집합니다.

- 탐색 루트: 현재 작업 디렉토리(프로젝트 루트)
- 제외 디렉토리: `node_modules`, `.git`, `vendor`, `dist`, `build`, `.worktrees`, 플러그인 cache 등 빌드·의존·격리 폴더
- 제외 대상: 글로벌 `~/.claude/CLAUDE.md`(사용자 개인 지침), `AGENTS.md` / `GEMINI.md`(범위 밖)

### 대상 0건 처리 (절대 새로 만들지 않음)

수집 결과가 0건이면 다음을 안내하고 **중단**합니다. `CLAUDE.md` 를 새로 생성하지 않습니다.

> 이 프로젝트에서 수정할 CLAUDE.md 를 찾지 못했습니다. 이 커맨드는 이미 있는 CLAUDE.md 만 갱신하며, 새로 만들지 않습니다.

## 2. 대상 선택 (AskUserQuestion)

수집된 CLAUDE.md 후보를 목록으로 보여주고, `AskUserQuestion` 도구로 **어느 파일(들)을 갱신할지** 사용자에게 물어봅니다. 후보가 하나뿐이어도 확인합니다.

- 각 후보는 프로젝트 루트 기준 상대 경로로 표시
- 여러 개 선택 가능 (multiSelect)

## 3. 구체값 후보 추출 (검증 기반)

선택된 각 CLAUDE.md 를 Read 하고, **실제 프로젝트와 대조 가능한 사실**만 변경 후보로 뽑습니다:

- 파일·폴더 경로 (예: `src/wallet/service.py`)
- 폴더·파일 구조 (디렉토리 트리 서술)
- 포트 번호 (예: 백엔드 로컬 8000)
- 파일명
- 함수명 / 클래스명

다음은 **후보에서 제외**합니다 (대조 가능한 사실이 아님):

- 워크플로우 룰 / 절차 설명 산문
- 톤 규칙 / 안전성 원칙
- 버전 태그(vX.Y.Z) / 결합 메모 / 회귀 catch grep
- 예시·설명 목적의 값

## 4. 실제 프로젝트 대조 검증

각 후보를 실제 프로젝트와 대조합니다:

- 경로/파일: Glob/LS 로 실제 존재 여부 확인. 없으면 실제 존재하는 대응 경로를 탐색
- 포트: 설정 파일(`.env`, `docker-compose*`, 서버·프레임워크 설정 등)에서 실제 포트를 Grep 으로 확인
- 함수명/클래스명: 코드에서 Grep 으로 확인

### 신뢰도 라벨 (모호하면 자동 변경 X)

- **높은 신뢰도** (경로·폴더구조·포트·파일명): 실제와 명확히 대조됨 → 변경 후보로
- **낮은 신뢰도** (함수명·클래스명, 또는 실제값이 여러 개라 모호): "확인 필요(불확실)"로 라벨링하고 **자동 제안하지 않음**. 사용자에게 판단을 넘김

### 사용자 지정 값 반영

사용자가 인자나 대화로 직접 알려준 값(예: "포트는 8444로")이 있으면 함께 반영 후보로 넣습니다.

## 5. 변경 제안 + 승인 게이트 (AskUserQuestion)

파일별로, 확인된 불일치를 **변경 전 / 변경 후** 형태로 보여주고 근거(어디서 실제값을 찾았는지)를 함께 표시합니다. 그 뒤 `AskUserQuestion` 으로 파일 단위 승인을 받습니다.

- 승인 없이 자동 반영 금지
- 낮은 신뢰도 항목은 "확인 필요"로 따로 묶어 사용자가 개별 판단
- 사용자가 특정 항목만 빼길 원하면 자유 응답으로 조정

## 6. 히스토리 보관 (반영 직전)

승인된 뒤, 실제로 파일을 바꾸기 **직전에** 구버전을 보관합니다:

- 각 대상 CLAUDE.md 와 같은 디렉토리에 `.claude-md-history/` 폴더를 만듭니다 (없으면)
- 구버전을 `CLAUDE.md.<YYYYMMDDHHMMSS>` 파일명으로 저장합니다 (덮어쓰지 않고 누적)
- 프로젝트 `.gitignore` 에 `.claude-md-history/` 항목이 없으면 추가하고, 추가 사실을 보고합니다
- 자동 복원 기능은 제공하지 않습니다 (열람 용도). 되돌리기는 사용자가 히스토리 파일을 수동으로 복사합니다

## 7. 반영 (본문 보존)

승인된 항목만 Edit 로 반영합니다:

- **문맥 단위로만** 교체합니다. 같은 문자열이 본문과 구체값에 함께 있을 수 있으므로 **전역 치환(replace_all) 금지**
- 각 변경은 해당 줄·맥락을 특정해 반영합니다
- 본문 규약(룰/톤/버전 태그/결합 메모)은 건드리지 않습니다

## 8. 보고 양식

반영 후 한국어로 보고합니다:

- 갱신된 항목 (파일별, 무엇을 무엇으로)
- 보류된 항목 (낮은 신뢰도 "확인 필요")
- 미갱신 대상 파일 (사용자가 선택 안 함)
- 히스토리 저장 위치 + `.gitignore` 처리 여부

## 9. 금지

- **없는 CLAUDE.md 새로 생성 금지** — 대상 0건이면 안내 후 중단 (§1)
- **본문 규약 변경 금지** — 룰/톤/원칙/버전 태그/결합 메모/설명 산문 (§3 후보 제외 + §7 문맥 단위)
- **승인 없는 자동 반영 금지** — 항상 §5 게이트
- **전역 치환(replace_all) 금지** — §7 문맥 단위만
- **모호 항목 자동 변경 금지** — 낮은 신뢰도는 사용자 확인 (§4)
- **글로벌 `~/.claude/CLAUDE.md` / 다른 프로젝트 / `AGENTS.md`·`GEMINI.md` 대상 금지** (§1)
- **히스토리 자동 복원·정리 금지** — 열람 용도, 수동 (§6)
````

- [ ] **Step 2: 커밋 (git-fast per-task)**

```bash
git add commands/update-claude-md.md
git commit -m "feat: /update-claude-md 커맨드 추가 — CLAUDE.md 구체값 검증 갱신 + 버전 히스토리"
```

### Task 2: 구조 검증 (grep)

**Files:**
- Test: `commands/update-claude-md.md` (구조 grep 검증, 코드 변경 없음)

**Model**: haiku

- [ ] **Step 1: 필수 섹션·안전장치 존재 확인**

Run:
```bash
f=commands/update-claude-md.md
grep -c "^## 1. 대상 CLAUDE.md 탐색" "$f" && \
grep -c "대상이 하나도 없으면\|찾지 못했습니다" "$f" && \
grep -c "AskUserQuestion" "$f" && \
grep -c "검증 기반\|실제 프로젝트와 대조 가능한 사실" "$f" && \
grep -c "\.claude-md-history/" "$f" && \
grep -c "전역 치환(replace_all) 금지\|replace_all" "$f" && \
grep -c "본문 규약" "$f"
```
Expected: 각 라인 ≥ 1 (모든 필수 요소 존재)

- [ ] **Step 2: frontmatter 유효성 확인**

Run:
```bash
head -5 commands/update-claude-md.md && grep -c "disable-model-invocation: true" commands/update-claude-md.md
```
Expected: `---` / `description:` (1줄) / `argument-hint:` / `disable-model-invocation: true` / `---` 형식 + 마지막 라인 `1` (자동 호출 비활성 확인)

## 2. 위험 코드 지점

instruction-only 커맨드라 실행 코드 라인이 아니라, 커맨드 본문의 안전장치 섹션으로 위험을 완화한다.

- `commands/update-claude-md.md §7 (반영)` — **breaking**: 본문 규약을 구체값으로 오판 시 룰 손상 (mitigation: §3 후보 제외 + §7 문맥 단위 + §5 승인 게이트)
- `commands/update-claude-md.md §7 (반영)` — **side-effect**: 같은 문자열 공존 시 전역 치환하면 본문 오염 (mitigation: `replace_all` 금지, 문맥 단위만 — §9 금지 명시)
- `commands/update-claude-md.md §4 (검증)` — **side-effect**: 프로젝트 스캔 오탐(포트 여러 개 등)으로 잘못된 실제값 추론 (mitigation: §5 에서 근거 표시 + 사용자 승인)
- `commands/update-claude-md.md §6 (히스토리)` — **side-effect**: 히스토리 누적으로 디스크·폴더 증가 (mitigation: gitignore + 위치 보고, 수동 정리 — 자동 정리 안 함)

## 3. 롤백 전략

- Code: `commands/update-claude-md.md` 는 신규 파일이므로 Task 1 커밋 revert 또는 파일 삭제로 완전 롤백
- DB / Config: 해당 없음 (파일 1개 추가, 영구 저장소·설정 변경 없음)

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-07-18 19:22] [구현계획서-수정]
- **id**: CH-20260718-004
- **이유**: 신규 구현계획서 최초 작성 — `commands/update-claude-md.md` 작성(Task 1) + 구조 검증(Task 2)
- **무엇이**: update-claude-md-implementation-plan.md 전체 (Task 1~2, §2 위험 코드 지점 4건, §3 롤백). frontmatter `disable-model-invocation: true` + description 정리 반영
- **영향범위**: 없음 (최초 생성) — 실제 산출물은 commands/update-claude-md.md 신규 1 파일
- **연관 항목**: CH-20260718-003

### [2026-07-18 19:26] [코드-수정] (batch: tasks 1..1)
- **id**: CH-20260718-005
- **이유**: Task 1 — `/update-claude-md` 커맨드 파일 신규 작성 (CLAUDE.md 구체값 검증 갱신 + 버전 히스토리)
- **무엇이**: `commands/update-claude-md.md` (신규 1 파일, frontmatter + §1~§9)
- **영향범위**: 신규 파일 1개. 기존 skill / command / scripts / hooks 영향 없음
- **위험 카테고리**: none (instruction-only 마크다운, 실행 코드 아님 — side-effect/breaking/race 0/3)
- **task별 세부 (1건)**:
  - Task 1: `commands/update-claude-md.md` — 커맨드 본문 작성 (`disable-model-invocation: true` 포함) (none) — commit: `c7f67b7`
- **연관 commits**: `c7f67b7`
- **변경 전/후 코드**: 생략 — `git show c7f67b7` 로 조회
- **연관 항목**: CH-20260718-004

### [2026-07-18 19:26] [검증] (task: Task 2 — 구조 검증)
- **id**: CH-20260718-006
- **이유**: 커맨드 파일 구조·안전장치·frontmatter 정적 grep 검증
- **무엇이**: 필수 섹션(탐색/0건중단/AskUserQuestion/검증기반/히스토리/전역치환금지/본문규약) + frontmatter `disable-model-invocation: true`
- **결과**: PASS — 모든 grep 항목 ≥ 1, frontmatter 정상
- **연관 commit**: `c7f67b7`
- **연관 항목**: CH-20260718-005
