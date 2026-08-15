---
commit_policy: per-task
---

# audit-risk 과장 줄이기 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** `/audit-risk` 가 HTML 대신 마크다운 한 장을 내고, 점수 대신 세어 확인 가능한 건수만 보고하며, 문제가 없으면 없다고 명시하고, 작은 프로젝트에서는 보조 에이전트 1개로 끝나게 한다.

**Architecture:** 커맨드 본문(`commands/audit-risk.md`)이 규모 판정 단계를 갖고 축소/전체 모드로 갈린다. 축소 모드는 보조 에이전트 1개가 다섯 영역을 순회하고, 전체 모드는 기존처럼 5개가 병렬로 나눠 본다. 보고서 생성 전용 에이전트(F)와 HTML 검증·복구 절차는 제거하고, 메인이 결과를 받아 마크다운을 직접 쓴다.

**Tech Stack:** 마크다운 지시문 (슬래시 커맨드 본문), 보조 에이전트 dispatch, 셸 기반 규모 측정

**Spec inputs:**
- audit-risk-과장줄이기-requirements.md — 핵심 결정 6건 (마크다운 단일 산출물 / 점수 폐지 / 규모별 에이전트 수 / 문제 없음 명시 / 메인 직접 작성 / 확인·추정 분리)
- audit-risk-과장줄이기-tech-design.md — §1 흐름, §4 산출물 계약, §5 결정 6건, §6 위험 6건, §7 테스트 전략

---

## 1. 단계별 작업

### Task 1: `commands/audit-risk.md` 재작성

**Files:**
- Modify: `commands/audit-risk.md` (전면 재작성)

**Model**: opus

**검증**: 커맨드 본문에서 HTML 관련 표현과 `score` 필드가 사라지고, 규모 판정 단계·축소 모드 프롬프트·`clean` 상태·심각도 3단계 정의가 모두 존재하는지 grep 으로 확인한다. `disable-model-invocation: true` 는 그대로 1건 유지되어야 한다.

- [ ] **Step 1: 확인 기준 먼저 세우고 현재 상태가 FAIL 임을 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계가 grep 확인 명령을 작성한다. 재작성 전에는 HTML 참조와 `score` 가 남아 있어 FAIL 이어야 한다.

- [ ] **Step 2: frontmatter 와 도입부 갱신**

`description` 을 마크다운 산출물 기준으로 고치고, `disable-model-invocation: true` 는 유지한다. 도입부의 "HTML 보고서 1개" 표현을 "마크다운 보고서 1개" 로, 산출물 경로를 `docs/audit/<timestamp>-audit-risk.md` 로 바꾼다. 1회 비용 안내의 "보조 에이전트 6개" 를 "축소 모드 1개 / 전체 모드 5개" 로 고친다.

- [ ] **Step 3: Step 1 에 규모 판정 추가**

`mkdir -p docs/audit/` 다음에 코드 규모 측정을 넣는다. git 저장소면 `git ls-files`, 아니면 `find` 로 소스 확장자만 추려 파일 수와 총 줄 수를 센다. 소스 파일 40개 미만 **그리고** 총 줄 수 8,000 미만이면 축소 모드, 아니면 전체 모드. 판정 결과를 사용자에게 한 줄 알린다 (예: `점검 대상 27개 파일 / 4,100줄 — 간단 모드로 진행합니다.`).

- [ ] **Step 4: Step 2 를 모드 분기로 재구성**

축소 모드: 보조 에이전트 1개(`general-purpose`, sonnet, read-only)가 다섯 영역 체크리스트를 순서대로 훑고 하나의 결과를 반환한다. 영역을 생략하지 않는다.
전체 모드: 기존처럼 5개를 한 메시지에 병렬 dispatch 한다.

- [ ] **Step 5: 다섯 영역 프롬프트의 반환 형식 개정**

각 영역 프롬프트에서 `score` 필드를 제거하고 `status` (`clean` / `findings` / `skipped` / `failed`) 를 필수로 만든다. `clean` 일 때는 `checked` 배열(무엇을 어떤 기준으로 봤는지 1~3항목)을 반드시 채우게 한다. 발견 항목은 `evidence` (코드에서 확인한 사실) 와 `impact` (그로 인해 일어나는 일) 를 분리해 적는다. 실행 경로를 확인하지 못한 항목은 `unverified` 배열로 보내고 심각도를 붙이지 않는다. 형식은 개발방향 문서 §4-2, §4-3 을 그대로 따른다.

- [ ] **Step 6: 심각도 정의를 3단계로 교체**

각 영역의 위험도 매트릭스를 심각 / 높음 / 보통 3단계로 바꾸고, 셋 다 "실행 경로 확인됨" 을 전제로 한다는 문장을 넣는다. Low 단계는 없애고 그 자리를 `unverified` 가 대신한다.

- [ ] **Step 7: 표현 규칙 명시**

다섯 영역 프롬프트와 보고서 작성 지침 양쪽에 같은 규칙 4줄을 넣는다 — 확인한 사실과 영향 분리 / 근거 댈 수 있을 때만 비용 추정 / 형용사·부사 금지 / 없으면 만들어내지 말고 `clean` 반환.

- [ ] **Step 8: Step 4 를 메인 직접 작성으로 교체하고 Step 4.5 제거**

보조 에이전트 F dispatch 절, `commands/audit-report-prompt.md` 참조(264·271·297행 부근), Step 4.5 검증표와 인계 절차를 통째로 삭제한다. 대신 메인이 개발방향 문서 §5 결정 3 의 마크다운 구조로 보고서를 직접 쓰는 절을 넣는다.

- [ ] **Step 9: Step 5 사용자 요약 갱신**

점수 줄을 없애고 심각도별 건수 + 영역별 상태 + 어느 모드였는지를 알린다.

- [ ] **Step 10: Non-goals 갱신**

"차분 감사", "5 영역 외 추가 영역", "`.auditignore`" 는 유지하고, HTML 관련 항목이 남아 있으면 정리한다.

- [ ] **Step 11: 확인 명령 실행 → PASS**

```bash
grep -n '"score"' commands/audit-risk.md                         # 기대: 0
grep -c '"clean"' commands/audit-risk.md                         # 기대: 1 이상
grep -rn "audit-risk.html\|audit-report-prompt" commands/audit-risk.md  # 기대: 0
grep -c "disable-model-invocation: true" commands/audit-risk.md  # 기대: 1
```

- [ ] **Step 12: Commit**

```bash
git add commands/audit-risk.md
git commit -m "feat(audit-risk): 마크다운 단일 산출물 + 규모별 모드 + 심각도 3단계로 재작성"
```

---

### Task 2: `commands/audit-report-prompt.md` 삭제

**Files:**
- Delete: `commands/audit-report-prompt.md`

**Model**: haiku

**검증**: 파일이 사라지고, 현행 커맨드·스킬 본문에서 이 파일을 참조하는 곳이 남아 있지 않은지 확인한다 (과거 spec 과 백로그의 언급은 기록이므로 제외).

- [ ] **Step 1: 참조가 남아 있는지 먼저 확인 (실행 단계 수행)**

Task 1 이 끝난 뒤라 `commands/audit-risk.md` 에는 참조가 없어야 한다. fixture 는 Task 3 에서 처리하므로 이 시점에는 남아 있을 수 있다.

- [ ] **Step 2: 파일 삭제**

```bash
git rm commands/audit-report-prompt.md
```

- [ ] **Step 3: 확인 → PASS**

```bash
test ! -f commands/audit-report-prompt.md && echo OK
```

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(audit-risk): HTML 보고서 전용 프롬프트 파일 삭제"
```

---

### Task 3: H23 fixture 개정

**Files:**
- Modify: `commands/audit-risk-tests/H23-e2e/README.md`
- Modify: `commands/audit-risk-tests/H23-e2e/expected-mock-findings.md`

**Model**: sonnet

**검증**: fixture 두 파일에서 HTML 전제(파일 확장자, 외부 URL 확인, 영역별 점수)가 사라지고, 개발방향 §7-2 의 6개 시나리오(간단 모드 / 전체 모드 / 문제 없음 / 비밀값 마스킹 / 영역 1개 실패 / 에이전트 영역 미해당)가 모두 들어 있는지 확인한다.

- [ ] **Step 1: 현재 상태가 FAIL 임을 확인 (실행 단계 수행)**

`grep -c "html" commands/audit-risk-tests/H23-e2e/*.md` 가 0 이 아니어야 한다 (개정 전).

- [ ] **Step 2: README.md 의 목적·시나리오 개정**

"5+1 subagent 패턴" 설명을 규모별 모드 설명으로 바꾼다. 6개 시나리오를 개발방향 §7-2 기준으로 다시 쓴다. 확인 명령의 `docs/audit/*.html` 을 `docs/audit/*.md` 로 바꾸고, 외부 URL 확인처럼 HTML 에만 해당하는 항목은 뺀다. 153·158행의 `audit-report-prompt.md` 참조를 제거한다.

- [ ] **Step 3: expected-mock-findings.md 개정**

기대값에서 영역별 점수를 빼고 심각도 3단계 + 확인 필요 구조로 바꾼다. `status` 필드(`clean` / `findings` / `skipped` / `failed`)와 `checked` 배열을 반영한다.

- [ ] **Step 4: 확인 → PASS**

```bash
grep -rn "\.html\|score" commands/audit-risk-tests/H23-e2e/   # 기대: 0
grep -c "clean" commands/audit-risk-tests/H23-e2e/README.md   # 기대: 1 이상
```

- [ ] **Step 5: Commit**

```bash
git add commands/audit-risk-tests/H23-e2e/
git commit -m "test(audit-risk): H23 시나리오를 마크다운 산출물 + 규모별 모드 기준으로 개정"
```

---

### Task 4: `README.md` 안내 갱신

**Files:**
- Modify: `README.md:430`, `README.md:434-451`, `README.md:455`, `README.md:516`

**Model**: sonnet

**검증**: README 에서 audit-risk 를 HTML 보고서로 소개하는 문장과 흐름도의 보고서 생성 노드가 사라지고, 마크다운 산출물 + 규모별 모드 설명으로 바뀌었는지 확인한다.

- [ ] **Step 1: 현재 상태가 FAIL 임을 확인 (실행 단계 수행)**

`sed -n '425,460p;514,518p' README.md` 로 HTML 표현이 남아 있음을 확인한다.

- [ ] **Step 2: 430행 소개 문장 교체**

**원본** (`README.md:430`)
```markdown
5 명의 AI 가 동시에 코드를 다른 각도로 훑고, 한 명이 그걸 모아 보기 좋은 HTML 보고서를 만들어 줍니다. 코드는 **건드리지 않아요**.
```

**수정 후**
```markdown
프로젝트 크기에 맞춰 AI 1 명 또는 5 명이 코드를 훑고, 결과를 마크다운 보고서 한 장으로 정리합니다. 코드는 **건드리지 않아요**.
```

- [ ] **Step 3: 434~451행 흐름도 교체**

mermaid 흐름도에서 보고서 생성 노드(`F["보고서 생성"]`)를 없애고, 다섯 영역이 메인으로 돌아와 메인이 보고서를 쓰는 형태로 바꾼다. 산출물 노드는 `docs/audit/...md` 로 고친다. 규모에 따라 영역 노드가 1개로 합쳐질 수 있다는 점을 흐름도 아래 한 줄로 덧붙인다.

- [ ] **Step 4: 455행 산출물 설명 교체**

**원본** (`README.md:455`)
```markdown
- 보고서는 `.html` 한 장 — gitignored, 사람만 보면 됩니다
```

**수정 후**
```markdown
- 보고서는 `.md` 한 장 — gitignored, 편집기에서 바로 읽고 이전 결과와 비교할 수 있습니다
```

- [ ] **Step 5: 516행 표 항목 교체**

**원본** (`README.md:516`)
```markdown
| `/audit-risk` | 5+1 AI 가 보안·거버넌스 동시 점검 → HTML 보고서 |
```

**수정 후**
```markdown
| `/audit-risk` | 규모에 맞춰 AI 1~5 명이 보안·거버넌스 점검 → 마크다운 보고서 |
```

- [ ] **Step 6: 확인 → PASS**

```bash
sed -n '425,460p;514,518p' README.md | grep -c "HTML\|\.html"   # 기대: 0
```

835행 버전 이력표는 과거 기록이므로 손대지 않는다.

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs(README): audit-risk 안내를 마크다운 산출물 + 규모별 모드로 갱신"
```

---

### Task 5: `skills/generating-html/SKILL.md` 예시에서 audit-risk 제외

**Files:**
- Modify: `skills/generating-html/SKILL.md:183`

**Model**: haiku

**검증**: 183행의 호출자 예시에서 `/audit-risk` 가 빠지고 `/sync-html` 만 남는지 확인한다. 이 파일의 다른 룰은 건드리지 않는다.

- [ ] **Step 1: 현재 상태가 FAIL 임을 확인 (실행 단계 수행)**

`grep -c "/audit-risk" skills/generating-html/SKILL.md` 가 1 이어야 한다 (수정 전).

- [ ] **Step 2: 183행 교체**

**원본** (`skills/generating-html/SKILL.md:183`)
```markdown
`generating-html` 백그라운드 호출이 처음 `.md` 생성 시 가끔 실패하던 회귀를 해결한 룰. 호출자 측 (`/sync-html` / `/audit-risk` 등 명시 호출 경로) 이 같이 답습.
```

**수정 후**
```markdown
`generating-html` 백그라운드 호출이 처음 `.md` 생성 시 가끔 실패하던 회귀를 해결한 룰. 호출자 측 (`/sync-html` 등 명시 호출 경로) 이 같이 답습.
```

- [ ] **Step 3: 확인 → PASS**

```bash
grep -c "/audit-risk" skills/generating-html/SKILL.md   # 기대: 0
```

- [ ] **Step 4: Commit**

```bash
git add skills/generating-html/SKILL.md
git commit -m "docs(generating-html): audit-risk 를 HTML 호출자 예시에서 제외"
```

---

### Task 6: `CLAUDE.md` 결합 메모 추가

**Files:**
- Modify: `CLAUDE.md`

**Model**: sonnet

**검증**: audit-risk 구성 결합 메모 섹션이 새로 생기고, 회귀 확인 grep 과 한쪽만 고쳤을 때의 증상 표가 들어 있는지 확인한다.

- [ ] **Step 1: 현재 상태가 FAIL 임을 확인 (실행 단계 수행)**

`grep -c "audit-risk 구성 결합" CLAUDE.md` 가 0 이어야 한다 (추가 전).

- [ ] **Step 2: 결합 메모 섹션 추가**

파일 끝에 섹션을 추가한다. 담을 내용:
- 산출물은 마크다운 하나, HTML 생성 경로 없음
- 규모 판정 두 조건 AND (파일 40 / 줄 8,000), 애매하면 전체 모드
- 심각도 3단계 + 확인 필요 분리, 점수 없음
- `clean` 반환 시 `checked` 필수
- 커맨드 본문과 H23 fixture 는 함께 고칠 것 (한쪽만 고치면 시나리오와 동작이 어긋남)
- 회귀 확인 grep (아래 Step 4 의 명령)

- [ ] **Step 3: 758행·1391행 언급 점검**

두 곳의 `/audit-risk` 언급이 HTML 생성 경로를 전제하는지 확인한다. 758행은 비동기 신뢰성 룰의 적용 범위, 1391행은 v2.8.2 영향 범위 서술이다. 사실과 어긋나면 고치고, 과거 기록 서술이면 그대로 둔다.

- [ ] **Step 4: 확인 → PASS**

```bash
grep -c "audit-risk 구성 결합" CLAUDE.md   # 기대: 1 이상
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): audit-risk 구성 결합 메모 추가"
```

---

### Task 7: 전체 회귀 확인

**Files:**
- Test: 확인 전용 (파일 변경 없음)

**Model**: haiku

**검증**: 개발방향 §7-1 의 회귀 확인 명령을 모두 돌려 기대값과 맞는지 본다. 하나라도 어긋나면 어느 Task 로 되돌아가야 하는지 보고한다.

- [ ] **Step 1: 회귀 확인 명령 실행**

```bash
grep -rn "audit-risk.html\|audit-report-prompt" commands/ README.md skills/   # 기대: 0
test ! -f commands/audit-report-prompt.md && echo OK                          # 기대: OK
grep -n '"score"' commands/audit-risk.md                                      # 기대: 0
grep -c '"clean"' commands/audit-risk.md                                      # 기대: 1 이상
grep -c "disable-model-invocation: true" commands/audit-risk.md               # 기대: 1
grep -c "audit-risk 구성 결합" CLAUDE.md                                       # 기대: 1 이상
```

- [ ] **Step 2: 결과 보고**

어긋난 항목이 있으면 해당 Task 번호와 함께 보고한다. 없으면 통과로 기록한다.

---

## 2. 위험 코드 지점

- `commands/audit-risk.md` (Task 1 재작성 전체): breaking | 산출물 확장자가 `.html` 에서 `.md` 로 바뀌어 사용자가 기대하는 파일이 달라진다. 기존 `.html` 파일은 삭제하지 않고 남겨 공존시킨다. 첫 실행 시 사용자 요약에 새 경로를 명시한다.
- `commands/audit-risk.md` Step 3~4 (규모 판정 + 모드 분기): side-effect | 축소 모드에서 놓치는 항목이 생길 수 있다. 두 조건 AND 로 경계를 보수적으로 잡고, 보고서 머리말에 어느 모드였는지와 대상 규모를 남겨 사용자가 다시 판단할 수 있게 한다.
- `commands/audit-risk.md` Step 5 (`clean` 상태 도입): side-effect | 문제 없음을 허용하면 대충 훑고 넘어갈 여지가 생긴다. `clean` 반환 시 `checked` 배열을 필수로 만들어, 무엇을 봤는지 없으면 형식 위반으로 잡는다.
- `commands/audit-risk-tests/H23-e2e/` 2파일 (Task 3): side-effect | 커맨드만 고치고 fixture 를 두면 시나리오와 실제 동작이 어긋난다. 같은 변경에 반드시 포함한다.
- `README.md` 4곳 (Task 4): side-effect | 안내가 HTML 을 소개한 채로 남으면 사용자가 없는 산출물을 기대한다. 같은 변경에 포함한다.
- `skills/generating-html/SKILL.md:183` (Task 5): side-effect | 이 파일의 다른 룰(백그라운드 호출 신뢰성, 커맨드 강등)은 건드리지 않는다. 한 줄만 교체한다.
- 다섯 영역 프롬프트의 비용 추정 규칙 (Task 1 Step 7): side-effect | 근거를 못 대면 아예 안 적게 되어 정보량이 줄어든다. 의도된 결과이며, 근거가 있으면 그대로 적힌다.

## 3. 롤백 전략

각 Task 가 별도 commit 이므로 문제가 생긴 Task 만 되돌린다.

- 특정 Task 되돌리기: `git revert <해당 commit SHA>`
- 전체 되돌리기: 이 작업 시작 시점 SHA 로 `git reset --hard <BASE_SHA>` (워크트리 안에서만)
- `commands/audit-report-prompt.md` 삭제 되돌리기: `git checkout <BASE_SHA> -- commands/audit-report-prompt.md`
- 이미 생성된 `docs/audit/` 산출물은 git 추적 대상이 아니므로 되돌릴 대상이 없다

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-15 09:03] [구현계획서-수정]
- **id**: CH-20260815-003
- **이유**: 개발방향의 결정 6건을 실행 가능한 작업 7개로 분해
- **무엇이**: audit-risk-과장줄이기-implementation-plan.md 전체 (§1 Task 1~7 / §2 위험 지점 7건 / §3 롤백 전략)
- **영향범위**: `commands/audit-risk.md` 재작성(Task 1), `commands/audit-report-prompt.md` 삭제(Task 2), H23 fixture 2파일(Task 3), `README.md` 4곳(Task 4), `skills/generating-html/SKILL.md:183`(Task 5), `CLAUDE.md`(Task 6), 회귀 확인(Task 7). plan_byte_check 통과 — 원본 블록 3개 모두 실제 파일과 일치. 버전 bump 작업은 포함하지 않음 (워크트리에서 manifest 수정 금지 룰)
- **연관 항목**: CH-20260815-001, CH-20260815-002

### [2026-08-15 09:28] [코드-수정] (batch: tasks 1..6)
- **id**: CH-20260815-004
- **이유**: `/audit-risk` 를 마크다운 단일 산출물 + 규모별 모드 + 심각도 3단계로 개편. 근거 없는 점수·비용 추정·형용사를 걷어내고, 문제가 없으면 확인 범위와 함께 없다고 명시하도록 변경
- **무엇이**: `commands/audit-risk.md`, `commands/audit-report-prompt.md`(삭제), `commands/audit-risk-tests/H23-e2e/README.md`, `commands/audit-risk-tests/H23-e2e/expected-mock-findings.md`, `README.md`, `skills/generating-html/SKILL.md`, `CLAUDE.md`
- **영향범위**: `/audit-risk` 산출물 형식이 `.html` 에서 `.md` 로 바뀜 (기존 `.html` 파일은 그대로 두어 공존). 보고서 생성 전용 보조 에이전트와 결과 검증·인계 절차 제거로 커맨드 흐름이 5단계에서 5단계(규모 판정 포함)로 재편. `generating-html` 의 비동기 신뢰성 규칙 적용 경로에서 audit-risk 제외. 다른 skill / commands / scripts / hooks 영향 없음
- **위험 카테고리**: breaking (산출물 확장자 변경), side-effect (커맨드 본문과 fixture·README 동기 필요)
- **task별 세부 (6건)**:
  - Task 1: `commands/audit-risk.md:1-447` — 전면 재작성. 규모 판정(파일 40 미만 그리고 8,000줄 미만), 축소·전체 모드 분기, status/checked/evidence/impact/unverified 형식, 심각도 3단계, 표현 규칙 4줄, 메인 직접 보고서 작성 (`breaking`) — commit: `1781a94`
  - Task 2: `commands/audit-report-prompt.md` — 삭제 (`breaking`) — commit: `5f24098`
  - Task 3: `commands/audit-risk-tests/H23-e2e/` 2파일 — 6개 시나리오 개정 + 기대값 구조 교체. 검토 지적 3건(sdks_detected 누락, redact_secret 누락, 멱등성 항목 심각도) 메인이 직접 정정 (`none`) — commit: `09c8572`
  - Task 4: `README.md:430,434-453,455,516` — 소개 문장 / 흐름도 / 산출물 설명 / 명령 목록 표 (`side-effect`) — commit: `a836991`
  - Task 5: `skills/generating-html/SKILL.md:183,203` — 호출자 예시에서 audit-risk 제외. 검토에서 203행이 추가 발견되어 메인이 함께 정정 (`none`) — commit: `3f97798`
  - Task 6: `CLAUDE.md` — audit-risk 구성 결합 메모 신규 + 758행 적용 경로 예시 정정 (`none`) — commit: `39a0f4f`
- **연관 commits**: `6c3191d..39a0f4f` (6건)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260815-003

### [2026-08-15 09:28] [검증] (task: Task 7 — 전체 회귀 확인)
- **id**: CH-20260815-005
- **이유**: 개발방향 §7-1 의 회귀 확인 명령으로 개편 결과 점검
- **무엇이**: HTML 경로 잔존 / 삭제 대상 파일 부재 / score 필드 / clean 상태 / 모델 자동 호출 차단 / 결합 메모 / fixture 잔존 / manifest 버전 무변경 8개 항목
- **결과**: PASS — 8개 모두 기대값과 일치 (HTML 참조 0, 파일 삭제 확인, score 0, clean 3건, disable-model-invocation 1건, 결합 메모 2건, fixture 잔존 0, 버전 파일 무변경)
- **연관 commit**: `6c3191d..39a0f4f`
- **연관 항목**: CH-20260815-004

### [2026-08-15 09:43] [코드-수정] (trivial)
- **id**: CH-20260815-006
- **이유**: 실제 호출 테스트 결과 보고서에 영어 표현이 많다는 사용자 지적. 한국어로 쓰는 규칙을 커맨드 본문에 추가
- **무엇이**: `commands/audit-risk.md` 공통 지시문 + Step 4 보고서 작성 지침 양쪽에 "한국어로 쓰기" 규칙 추가 (사람이 읽는 값은 한국어, 파일 경로·함수 이름·명령어·라이브러리 이름만 영어, 영어 약어는 처음 등장 시 한국어 설명 병기), `CLAUDE.md` 결합 메모에 같은 규칙 한 줄
