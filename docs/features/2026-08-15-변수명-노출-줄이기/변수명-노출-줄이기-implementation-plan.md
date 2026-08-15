---
commit_policy: per-task
---

# 변수명-노출-줄이기 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 기술설계 문서의 서술 문단에서 코드 식별자 노출을 줄인다 — 기본은 역할 풀어쓰기, 예외는 "그 이름이 바뀌면 문서 밖이 깨지는 경우". 수동 경로와 자동 경로 두 스킬에 같은 룰을 심는다.

**Architecture:** 실행 코드 변경 0. 두 스킬 본문에 (1) 룰 전용 섹션 (판별 문장 + 예시 표 + 적용 부위), (2) 작성 후 점검 (수동은 Self-Review 항목, 자동은 문서 작성 단계 확장), (3) 금지 사례 표 행을 심는다. 결합 메모와 대조 사례 문서가 회귀를 잡는다.

**Tech Stack:** markdown 스킬 본문 편집 (byte-copy 페어 7곳 + 신규 파일 1 + 라벨 면제 1곳), grep 회귀 검증.

**Spec inputs:**
- 변수명-노출-줄이기-requirements.md — 핵심 결정 1~4, 범위 제외 3건, 수용 기준 5건
- 변수명-노출-줄이기-tech-design.md — D-1 (전용 섹션), D-2 (Self-Review 항목), D-2b (자동 경로 작성 단계 확장), D-3 (금지 사례 행), D-4 (자동 경로 압축본), D-5 (룰 존재 확인 + 대조 사례), D-6 (결합 메모), D-7 (버전 미변경)

---

## 0. Wave / byte-copy 개요

| Wave | Task | 파일 | Model | byte-copy |
|---|---|---|---|---|
| 1 | T1 — 수동 경로 룰 심기 | `skills/tech-design/SKILL.md` | sonnet | 페어 3 |
| 1 | T2 — 자동 경로 룰 심기 | `skills/auto-tech-design/SKILL.md` | sonnet | 페어 3 |
| 1 | T3 — 결합 메모 신설 | `CLAUDE.md` | sonnet | 페어 1 (수정 후 블록 4-backtick 면제) |
| 1 | T4 — 대조 사례 문서 신규 | `skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md` | sonnet | Create 1 |
| 2 | T5 — 회귀 grep 일괄 검증 | (검증 전용, 코드 변경 없음) | haiku | N/A |

**Model 이 전부 sonnet 인 근거**: 삽입 문구가 전부 한국어 산문이다. 한국어 문장은 재작성 위험이 있어 최소 sonnet 을 쓴다 (계획서 작성 룰의 한국어 산문 조항).

**T3 의 수정 후 블록 면제 근거**: 삽입할 결합 메모 안에 회귀 확인용 명령 블록이 들어 있어 코드펜스가 중첩된다. 계획서에서는 4-backtick 으로 감싸 전문을 그대로 싣고, 실행 시 안쪽 3-backtick 까지 포함해 그대로 복사한다. `**원본**` 블록에는 펜스가 없어 원본 인용 검사에는 영향이 없다.

**버전에 대한 주의**: 6 manifest 버전 bump 는 본 계획 범위 밖이다. 워크트리 세션에서는 버전을 올리지 않는다. 그래서 삽입하는 룰 섹션 제목에도 버전 표기를 넣지 않는다 — 릴리스 번호가 아직 정해지지 않았고, 잘못 박으면 나중에 고쳐야 한다.

## 1. 단계별 작업

### Task 1: 수동 경로 룰 심기

**Files:**
- Modify: `skills/tech-design/SKILL.md`

**Model**: sonnet

**검증**: 룰 섹션 제목, 판별 문장, 예시 표, 자체 점검 항목, 금지 사례 2행이 모두 파일에 있고, 기존 섹션 (Process Flow / Self-Review 기존 4항목 / Anti-Patterns 기존 4행) 이 하나도 사라지지 않았는지 grep 으로 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF "서술 수준 — 이름보다 역할" skills/tech-design/SKILL.md`
Expected: 0 매치 (exit 1) — 변경 전이므로 실패가 정상

- [ ] **Step 2: 룰 전용 섹션 신설 (문서 구조 설명 직후)**

**원본** (`skills/tech-design/SKILL.md:103`):
```
## Process Flow
```

**수정 후**:
```
## 서술 수준 — 이름보다 역할

`<slug>-tech-design.md` 의 **서술 문단** (줄글로 설명하는 부분) 에서는 코드 식별자를 기본적으로 쓰지 않는다. 이름을 쓰려는 자리마다 먼저 그 역할을 말로 풀어쓴다.

예외는 하나다 — **그 이름이 바뀌면 문서 밖의 무언가가 깨지는 경우**에만 실제 이름을 쓴다.

| 실제 이름을 쓴다 | 말로 풀어쓴다 |
|---|---|
| 사용자가 입력하는 명령어 | 내부 변수, 지역 변수 |
| 설정 파일의 키 이름 | 아직 없는 새 함수·클래스 이름 |
| 외부나 다른 팀이 호출하는 공개 함수 | 직접 지은 중간 계산값 |
| 저장소에 이미 있는 파일 경로 | 반복문 변수, 임시로 붙인 이름 |

왼쪽은 이름 자체가 약속이라 바꾸면 문서 밖이 깨진다. 오른쪽은 구현하면서 얼마든지 달라져 지금 적어봐야 문서만 먼저 낡는다.

**적용 부위는 서술 문단뿐이다.** §2 의 영향 파일 표, 코드 블록, 도식은 그대로 둔다 — 이름을 보여주는 것이 그 자리의 목적이다.

### Why

설계 문서는 구조·계약·결정을 담는 자리다. 구현 단계에서 바뀔 이름이 서술에 박히면 문서가 먼저 낡고, 정작 읽어야 할 결정이 이름 사이에 묻힌다. 기본 동작을 풀어쓰기로 두는 이유는 매번 판정을 통과시키는 방식으로는 결과가 달라지지 않기 때문이다.

## Process Flow
```

- [ ] **Step 3: 자체 점검 항목 추가**

**원본** (`skills/tech-design/SKILL.md:295`):
```
- §7 test strategy is consistent with §3 and §4 (DB changes → migration tests, APIs → integration/contract tests)
```

**수정 후**:
```
- §7 test strategy is consistent with §3 and §4 (DB changes → migration tests, APIs → integration/contract tests)
- 서술 문단에 남은 코드 식별자가 모두 "그 이름이 바뀌면 문서 밖이 깨지는" 예외에 해당한다 — 아니면 역할 서술로 교체 (표 / 코드 블록 / 도식은 대상 아님, "서술 수준 — 이름보다 역할" 섹션)
```

- [ ] **Step 4: 금지 사례 2행 추가**

**원본** (`skills/tech-design/SKILL.md:325`):
```
| "Be careful here" without a category | Force one of the three risk-annotation categories (`side-effect`, `breaking`, `race`). |
```

**수정 후**:
```
| "Be careful here" without a category | Force one of the three risk-annotation categories (`side-effect`, `breaking`, `race`). |
| 서술 문단에 내부 변수나 아직 없는 함수 이름을 그대로 박기 | 역할을 말로 풀어쓴다. 이름이 바뀌면 문서 밖이 깨지는 경우만 실제 이름. |
| 룰을 표나 코드 블록까지 확대 적용해 이름을 지우기 | 적용 부위는 서술 문단뿐. 표와 코드 블록은 이름을 보여주는 자리다. |
```

- [ ] **Step 5: 변경 후 PASS 확인**

Run: `grep -cF "서술 수준 — 이름보다 역할" skills/tech-design/SKILL.md && grep -cF "서술 문단에 남은 코드 식별자" skills/tech-design/SKILL.md && grep -c "^## Process Flow$" skills/tech-design/SKILL.md`
Expected: 각각 2 / 1 / 1 (섹션 제목 1 + 점검 항목 안 참조 1 = 2)

- [ ] **Step 6: 기존 내용 보존 확인**

Run: `grep -cE "^\| (Listing step-by-step tasks here|Missing FR mapping|One decision, no alternatives)" skills/tech-design/SKILL.md`
Expected: 3 — 기존 금지 사례 3행이 그대로 남아 있어야 함

### Task 2: 자동 경로 룰 심기

**Files:**
- Modify: `skills/auto-tech-design/SKILL.md`

**Model**: sonnet

**검증**: 압축본 룰 섹션과 판별 문장, 예시 표가 들어가고 문서 작성 단계가 점검까지 포함하도록 넓어졌는지, 진행 목록 항목 문구도 같이 바뀌었는지, 기존 단계 7개와 금지 사례 4행이 그대로인지 grep 으로 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF "서술 수준 — 이름보다 역할" skills/auto-tech-design/SKILL.md`
Expected: 0 매치 (exit 1) — 변경 전이므로 실패가 정상

- [ ] **Step 2: 진행 목록 항목 문구 확장**

**원본** (`skills/auto-tech-design/SKILL.md:13`):
```
- [ ] Step 4 — 산출물 자동 작성 (<slug>-tech-design.md)
```

**수정 후**:
```
- [ ] Step 4 — 산출물 자동 작성 + 서술 수준 점검 (<slug>-tech-design.md)
```

- [ ] **Step 3: 문서 작성 단계에 점검 포함**

**원본** (`skills/auto-tech-design/SKILL.md:38-40`):
```
### Step 4 — 산출물 자동 작성

`<slug>-tech-design.md` 7-section schema 따라 작성. RAW 본문.
```

**수정 후**:
```
### Step 4 — 산출물 자동 작성 + 서술 수준 점검

`<slug>-tech-design.md` 7-section schema 따라 작성. RAW 본문.

작성 직후 메인이 서술 문단을 한 번 훑는다 — 남아 있는 코드 식별자마다 "그 이름이 바뀌면 문서 밖의 무언가가 깨지는가" 를 판정하고, 아니면 역할 서술로 교체한다. 표 / 코드 블록 / 도식은 대상 아님. 룰은 아래 "서술 수준 — 이름보다 역할" 섹션. 사용자 응답 wait X (auto 모드).
```

- [ ] **Step 4: 압축본 룰 섹션 + 금지 사례 1행 추가**

**원본** (`skills/auto-tech-design/SKILL.md:80-82`):
```
| transition notice 후 wait sleep | NEVER. |

## Related Skills
```

**수정 후**:
```
| transition notice 후 wait sleep | NEVER. |
| 서술 문단에 내부 변수나 아직 없는 함수 이름 박기 | 역할을 말로 풀어쓴다. 아래 "서술 수준" 섹션 참조. |

## 서술 수준 — 이름보다 역할

`<slug>-tech-design.md` 의 **서술 문단** (줄글로 설명하는 부분) 에서는 코드 식별자를 기본적으로 쓰지 않는다. 이름을 쓰려는 자리마다 그 역할을 말로 풀어쓰고, **그 이름이 바뀌면 문서 밖의 무언가가 깨지는 경우**에만 실제 이름을 쓴다.

| 실제 이름을 쓴다 | 말로 풀어쓴다 |
|---|---|
| 사용자가 입력하는 명령어 | 내부 변수, 지역 변수 |
| 설정 파일의 키 이름 | 아직 없는 새 함수·클래스 이름 |
| 외부나 다른 팀이 호출하는 공개 함수 | 직접 지은 중간 계산값 |
| 저장소에 이미 있는 파일 경로 | 반복문 변수, 임시로 붙인 이름 |

적용 부위는 서술 문단뿐 — §2 영향 파일 표, 코드 블록, 도식은 그대로 둔다. 배경 설명은 `skills/tech-design/SKILL.md` 의 같은 이름 섹션 답습 (본 skill 은 판단에 필요한 부분만 보유).

## Related Skills
```

- [ ] **Step 5: 변경 후 PASS 확인**

Run: `grep -cF "서술 수준 — 이름보다 역할" skills/auto-tech-design/SKILL.md && grep -cF "산출물 자동 작성 + 서술 수준 점검" skills/auto-tech-design/SKILL.md`
Expected: 2 / 2 (섹션 제목 1 + 작성 단계 참조 1, 진행 목록 1 + 단계 제목 1)

- [ ] **Step 6: 기존 내용 보존 확인**

Run: `grep -cE "^- \[ \] Step [1-7] —" skills/auto-tech-design/SKILL.md && grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md`
Expected: 7 / 1 이상 — 기존 단계 7개와 다음 단계 연결이 그대로여야 함

### Task 3: 결합 메모 신설

**Files:**
- Modify: `CLAUDE.md`

**Model**: sonnet

**검증**: 결합 메모 섹션이 파일 끝에 추가되고 회귀 확인 명령 블록이 함께 들어갔는지, 직전 섹션의 마지막 줄이 그대로 남아 있는지 grep 으로 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF "기술설계 서술 수준 룰 결합" CLAUDE.md`
Expected: 0 매치 (exit 1) — 변경 전이므로 실패가 정상

- [ ] **Step 2: 파일 끝에 결합 메모 추가**

**원본** (`CLAUDE.md:1493`):
```
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0
```

**수정 후** (아래 4-backtick 안의 내용 전체를 그대로 복사 — 안쪽 3-backtick 포함):

````
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0

## 기술설계 서술 수준 룰 결합 (tech-design ↔ auto-tech-design)

기술설계 문서의 서술 문단에서 코드 식별자 노출을 줄이는 룰. 기본은 역할 풀어쓰기, 예외는 "그 이름이 바뀌면 문서 밖이 깨지는 경우". spec: `docs/features/2026-08-15-변수명-노출-줄이기/`.

### 적용 범위 (4 본문)

- `skills/tech-design/SKILL.md` — "서술 수준 — 이름보다 역할" 섹션 신설 + Self-Review 항목 1개 + Anti-Patterns 2행
- `skills/auto-tech-design/SKILL.md` — 같은 섹션 압축본 + Step 4 제목·본문 확장 + Checklist 항목 4 문구 + Anti-Patterns 1행
- `skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md` — 통과/위반 대조 사례
- `CLAUDE.md` — 본 섹션

### 핵심 룰

- 적용 부위는 **서술 문단만**. §2 영향 파일 표 / 코드 블록 / 도식은 대상 아님 (이름을 보여주는 것이 그 자리의 목적)
- 예외 판정은 한 문장 — "그 이름이 바뀌면 문서 밖의 무언가가 깨지는가"
- 예시 표 4행 (쓰는 경우 / 풀어쓰는 경우) 이 경계 사례를 잡는다 — 표를 지우면 룰이 흔들린다
- 두 스킬 **동시 수정**. 한쪽만 고치면 수동 경로와 자동 경로의 문서 문체가 갈리는데, 이 어긋남은 검색으로 잘 안 잡힌다
- 요구사항 문서 / 구현계획서 / verifying-spec 은 범위 밖 (요구사항 문서는 산출물 존치 미정, 구현계획서는 코드가 목적)
- 기존 문서 소급 수정 X — 새로 쓰는 문서부터 적용

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| 수동 경로만 변경 | 자동 흐름 문서에 식별자 노출 잔존 — 두 경로 문체 불일치 |
| 자동 경로만 변경 | 반대 |
| 예시 표 삭제 | 판별 문장만 남아 경계 사례에서 흔들림 (요구사항 "판별 질문 + 예시 표" 결정 위반) |
| "서술 문단만" 한정 문구 삭제 | 표·코드 블록까지 이름이 지워져 설계 근거 손실 |
| Self-Review 항목 / Step 4 점검 문장 삭제 | 작성 중 놓친 노출이 걸러지지 않음 |

### 회귀 catch grep

```bash
# 두 스킬 모두 룰 섹션 보유
grep -lF "서술 수준 — 이름보다 역할" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
# expected: 2 lines

# 판별 문장 (양쪽)
grep -cF "문서 밖의 무언가가 깨지는" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
# expected: 각 >= 1

# 적용 부위 한정 문구 (양쪽)
grep -cF "적용 부위는 서술 문단" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
# expected: 각 >= 1

# 점검 장치 — 수동은 Self-Review, 자동은 Step 4
grep -cF "서술 문단에 남은 코드 식별자" skills/tech-design/SKILL.md
# expected: 1
grep -cF "산출물 자동 작성 + 서술 수준 점검" skills/auto-tech-design/SKILL.md
# expected: 2

# 대조 사례 문서 존재
test -f skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md && echo OK
# expected: OK
```

### 영향 범위

- 스킬 본문 2 + 대조 사례 1 + CLAUDE.md. commands / scripts / hooks 변경 0 (두 커맨드 안내문은 진입·산출물·다음 단계만 다루고 문체는 다루지 않음)
- 두 스킬의 절차 / 게이트 / 다음 단계 연결 변경 0 — 추가되는 것은 문체 지침과 점검뿐
- `brainstorming` / `writing-plans` / `verifying-spec` / og-* / worktree 계열 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
````

- [ ] **Step 3: 변경 후 PASS 확인**

Run: `grep -cF "기술설계 서술 수준 룰 결합" CLAUDE.md && grep -cF "적용 부위는 서술 문단" CLAUDE.md`
Expected: 1 / 1

### Task 4: 대조 사례 문서 신규

**Files:**
- Create: `skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md`

**Model**: sonnet

**검증**: 새 문서가 생기고 위반 사례와 통과 사례가 짝으로 들어 있는지, 기존 시나리오 문서 번호와 겹치지 않는지 확인.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `test -f skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md`
Expected: 실패 (exit 1) — 아직 없어야 정상

- [ ] **Step 2: 대조 사례 문서 작성**

**수정 후** (신규 파일 전문):
```
# H16 — 기술설계 서술 수준 (이름보다 역할) 시나리오 fixture

기술설계 문서의 서술 문단에서 코드 식별자 노출을 줄이는 룰의 기대 동작 검증. spec: `docs/features/2026-08-15-변수명-노출-줄이기/`.

문체 룰이라 기계 판정이 어렵다. 아래는 같은 설계 내용을 두 가지로 쓴 대조 사례다 — 판단 기준을 맞춰보는 용도.

## 시나리오 A — 서술 문단에 내부 이름 (위반)

> 루트 해석은 resolve_root() 가 맡고, 결과를 MAIN_ROOT 변수에 담아 _setup_worktree() 에 넘긴다. 실패하면 RootError 를 던진다.

- 위반 이유: 세 이름 모두 구현 단계에서 바뀔 수 있고, 바뀌어도 문서 밖은 깨지지 않는다

## 시나리오 B — 같은 내용, 역할 서술 (통과)

> 루트 해석은 전용 단계가 맡고, 결과인 메인 저장소 루트를 워크트리 생성 단계에 넘긴다. 해석에 실패하면 생성 전에 중단한다.

- 통과 이유: 이름 없이도 구조와 흐름이 그대로 전달된다

## 시나리오 C — 이름 자체가 계약 (통과, 이름 유지)

> 사용자가 /worktree 를 실행하면 훅은 git worktree add 로 시작하는 명령만 잡아낸다. 세션 노트는 .js-super/session-handoff/ 아래에 쌓인다.

- 통과 이유: 명령어, 훅이 매칭하는 문자열, 저장 경로는 바뀌면 문서 밖이 깨진다

## 시나리오 D — 표와 코드 블록 (룰 대상 아님)

- §2 영향 파일 표의 경로, 설정 예시 코드 블록, 도식 안 이름은 그대로 둔다
- 기대: 룰을 표까지 확대 적용해 경로를 지우면 그것이 위반

## 시나리오 E — 두 경로 일치

- 같은 요구사항을 수동 경로 (/tech-design) 와 자동 흐름 (/auto-tech-design) 으로 각각 진행
- 기대: 두 산출물의 서술 문단 문체가 같다. 한쪽만 이름이 남으면 룰이 한 스킬에만 박힌 것

## 보조 검증

- 점검 장치 동작: 문서를 다 쓴 뒤 수동 경로는 자체 점검 목록에서, 자동 경로는 문서 작성 단계 안에서 서술 문단을 훑는지
- 범위 보존: 요구사항 문서 / 구현계획서 / 검증 스킬의 문체는 이번 룰의 대상이 아니다
```

- [ ] **Step 3: 변경 후 PASS 확인**

Run: `test -f skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md && grep -cF "시나리오 B" skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md`
Expected: 파일 존재 + 1

### Task 5: 회귀 grep 일괄 검증

**Files:**
- 없음 (검증 전용)

**Model**: haiku

**검증**: 결합 메모에 적힌 회귀 확인 명령을 모두 실행해 기대값과 맞는지, 그리고 두 스킬의 기존 절차가 손상되지 않았는지 한 번에 판정.

- [ ] **Step 1: 룰 존재 확인**

Run:
```
grep -lF "서술 수준 — 이름보다 역할" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
grep -cF "문서 밖의 무언가가 깨지는" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
grep -cF "적용 부위는 서술 문단" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
```
Expected: 첫 명령 2줄, 나머지는 각 파일 1 이상

- [ ] **Step 2: 점검 장치 확인**

Run:
```
grep -cF "서술 문단에 남은 코드 식별자" skills/tech-design/SKILL.md
grep -cF "산출물 자동 작성 + 서술 수준 점검" skills/auto-tech-design/SKILL.md
test -f skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md && echo OK
```
Expected: 1 / 2 / OK

- [ ] **Step 3: 범위 보존 확인**

Run:
```
git diff --name-only
grep -c "서술 수준" skills/brainstorming/SKILL.md skills/writing-plans/SKILL.md skills/verifying-spec/SKILL.md commands/tech-design.md commands/auto-tech-design.md
git diff --stat -- .claude-plugin/ .codex-plugin/ .cursor-plugin/ gemini-extension.json package.json
```
Expected: 변경 파일이 두 스킬 + CLAUDE.md + 신규 대조 사례 + 피처 문서로만 한정 / 범위 밖 5개 파일 모두 0 / 버전 관련 diff 없음

- [ ] **Step 4: 기존 절차 보존 확인**

Run:
```
grep -cF "Gate #11" skills/tech-design/SKILL.md
grep -cF "Gate #12" skills/tech-design/SKILL.md
grep -cE "^- \[ \] Step [1-7] —" skills/auto-tech-design/SKILL.md
```
Expected: Gate 문구가 그대로 남아 있고, 자동 경로 단계가 7개 유지

## 2. 위험 코드 지점

| 위험 | 위치 | 대응 |
|---|---|---|
| side-effect — 룰이 넓게 읽혀 표·코드 블록의 이름까지 지워짐 | `skills/tech-design/SKILL.md` 신설 섹션 / `skills/auto-tech-design/SKILL.md` 신설 섹션 | 두 섹션 모두 "적용 부위는 서술 문단뿐" 문장을 넣고, 수동 경로 금지 사례 표에 확대 적용을 위반으로 명시 (T1 Step 4) |
| side-effect — 룰이 약하게 읽혀 지금과 달라지지 않음 | 위와 같음 | 기본 동작을 풀어쓰기로 잡고 예시 표 오른쪽 열에 실제로 자주 나오는 사례를 담음 |
| side-effect — 한쪽 스킬만 고쳐져 두 경로 문체가 갈림 | `CLAUDE.md` 결합 메모 | 결합 메모의 회귀 확인 명령이 두 파일을 함께 검사 (T3 Step 2, T5 Step 1) |
| breaking — 삽입 과정에서 기존 절차·게이트가 손상 | 두 스킬 본문 | 각 task 마지막에 기존 내용 보존 확인 step (T1 Step 6, T2 Step 6, T5 Step 4) |
| 범위 이탈 — 버전 파일이나 범위 밖 스킬이 함께 수정됨 | 저장소 전체 | T5 Step 3 에서 변경 파일 목록과 버전 파일 diff 를 함께 확인 |

race 위험은 없다. 실행되는 코드 변경이 없고 모든 편집이 순차 적용된다.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-15 09:26] [구현계획서-수정]
- **id**: CH-20260815-003
- **이유**: 신규 구현 계획 (원본 인용 검사 통과, 검증 결과 누락 0건 / 모순 0건. 자동 흐름이라 사용자 게이트 없이 진행)
- **무엇이**: 변수명-노출-줄이기-implementation-plan.md 전체 (Task 1~5, 위험 코드 지점 5건)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260815-001, CH-20260815-002

### [2026-08-15 09:35] [코드-수정] (batch: tasks 1..4)
- **id**: CH-20260815-004
- **이유**: 기술설계 문서의 서술 문단에서 코드 식별자 노출을 줄이는 룰을 두 스킬에 심고, 결합 메모와 대조 사례 문서를 함께 추가
- **무엇이**: skills/tech-design/SKILL.md, skills/auto-tech-design/SKILL.md, CLAUDE.md, skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md
- **영향범위**: 두 스킬의 문서 작성 지침과 자체 점검만 확장. 절차 / 게이트 / 다음 단계 연결 변경 0. 실행되는 코드 변경 0. 범위 밖 스킬·커맨드 오염 0 (검색 확인), 버전 파일 변경 0
- **위험 카테고리**: none — 3항목 자체 점검 결과 복잡한 분기 추가 없음, 공개 시그니처·스키마 변경 없음, 공유 상태 접근 없음. 마크다운 문서라 위험 주석 부착 대상 아님
- **task별 세부 (4건)**:
  - Task 1: `skills/tech-design/SKILL.md:103-349` — 서술 수준 룰 섹션 신설 (판별 문장 + 예시 표 4행 + 적용 부위 + 배경) / 자체 점검 항목 1개 / 금지 사례 2행 (`none`) — commits: `ea3fdba`
  - Task 2: `skills/auto-tech-design/SKILL.md:13,38-42,83-96` — 같은 룰 압축본 + 문서 작성 단계에 점검 포함 + 진행 목록 문구 확장 + 금지 사례 1행 (`none`) — commits: `027aea4`
  - Task 3: `CLAUDE.md:1493-1556` — 두 스킬 동시 수정 결합 메모 신설 (핵심 룰 / 회귀 패턴 표 / 회귀 확인 명령 / 영향 범위) (`none`) — commits: `5aa4487`
  - Task 4: `skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md:1-38` — 통과·위반 대조 사례 5개 + 보조 검증 (`none`) — commits: `ef480ca`
- **연관 commits**: `6c3191d..HEAD` (task 4건 + spec `c76098a`)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260815-003

### [2026-08-15 09:35] [검증] (task: Task 5 — 회귀 grep 일괄 검증)
- **id**: CH-20260815-005
- **이유**: 룰이 두 스킬에 모두 남았는지, 기존 절차가 손상되지 않았는지, 변경이 계획 범위를 벗어나지 않았는지 일괄 확인
- **무엇이**: 룰 섹션·판별 문장·적용 부위 문구 존재 확인 / 점검 장치 2곳 + 대조 사례 문서 존재 확인 / 변경 파일 목록 + 범위 밖 스킬·커맨드 오염 + 버전 파일 확인 / 기존 승인 게이트 문구 + 자동 경로 단계 7개 보존 확인
- **결과**: PASS — 룰 섹션 두 파일 모두 존재, 판별 문장과 적용 부위 문구 각 1건 이상, 점검 장치 1/2, 대조 사례 문서 존재, 변경 파일 4개로 한정, 범위 밖 5개 파일 오염 0, 버전 파일 변경 0, 승인 게이트 문구와 자동 경로 단계 7개 모두 보존
- **연관 commit**: `ea3fdba`, `027aea4`, `5aa4487`, `ef480ca`
- **연관 항목**: CH-20260815-004
