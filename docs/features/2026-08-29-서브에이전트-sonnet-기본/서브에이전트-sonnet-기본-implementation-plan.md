---
commit_policy: per-task
---

# 구현계획서: 서브에이전트 sonnet 기본 (haiku 사용 금지)

> **입력**: `서브에이전트-sonnet-기본-requirements.md` (FR-1..5) + `서브에이전트-sonnet-기본-tech-design.md` (D1~D5)
> **실행**: Task 1~8 은 서로 다른 파일만 만져 wave-parallel 가능. Task 9 (검증) 는 Task 1~8 완료 후.

## §1 Tasks

### Task 1: writing-plans — Model 필드 enum 축소 + 판정표 sonnet 흡수

**Files:**
- Modify: `skills/writing-plans/SKILL.md:201-247`

**Model**: sonnet

**검증**: 수정 후 `grep -ni "haiku" skills/writing-plans/SKILL.md` 0건 + `grep -cF "sonnet | opus"` 1건 이상. 템플릿 예시가 sonnet.

- [ ] **Step 1: 템플릿 예시 모델 교체**

**원본** (`skills/writing-plans/SKILL.md:201-203`):
```markdown
**Model**: haiku

**검증**: <이 task 의 테스트가 무엇을 검증하는지 + 성공 기준 — 자연어 1~2줄. 테스트 코드는 싣지 않는다 (v2.9+)>
```

**수정 후**:
```markdown
**Model**: sonnet

**검증**: <이 task 의 테스트가 무엇을 검증하는지 + 성공 기준 — 자연어 1~2줄. 테스트 코드는 싣지 않는다 (v2.9+)>
```

- [ ] **Step 2: Task Model Hint 서두 문단 교체 (enum 2값)**

**원본** (`skills/writing-plans/SKILL.md:234`):
```markdown
Each task block MAY include `**Model**: haiku | sonnet | opus`. v2.9+ 부터 이 필드는 신규 테스트 작성이 포함된 task 에 한해 dispatch 에 직접 쓰인다: `js-super-sub-driven` 은 **신규 테스트 작성 포함 task** (`**검증**:` 필드 + `Test:` 경로 존재 + 테스트 코드 블록 없음) 의 implementer 를 이 필드 값 (**최소 sonnet floor**) 으로 dispatch 하고, 순수 byte-copy task 는 haiku 고정을 유지한다. Spec-reviewer is always sonnet. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch.
```

**수정 후**:
```markdown
Each task block MAY include `**Model**: sonnet | opus`. 이보다 낮은 모델 값은 쓰지 않는다 (sonnet 하한). 이 필드는 `js-super-sub-driven` 의 implementer dispatch 모델로 직접 쓰인다 — 필드 생략 시 sonnet 기본값. Spec-reviewer is always sonnet. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch.
```

- [ ] **Step 3: 값 산정 판정표 교체 (haiku 행 흡수)**

**원본** (`skills/writing-plans/SKILL.md:238-245`):
```markdown
| 신호 | Model 값 |
|---|---|
| 1-2 파일 + mechanical implementation + 명확 spec (신규 테스트 없음) | haiku |
| 다중 파일 통합 / 디버깅 / 패턴 매칭 | sonnet |
| Korean prose 조작 (skill 본문 / MD 편집) | sonnet |
| 신규 테스트 작성 포함 (`**검증**:` + `Test:` 경로) | 최소 sonnet (floor) |
| 설계 / 광범위 코드베이스 이해 | opus |
| 누락 / 모호 | sonnet |
```

**수정 후**:
```markdown
| 신호 | Model 값 |
|---|---|
| 1-2 파일 + mechanical implementation + 명확 spec | sonnet |
| 다중 파일 통합 / 디버깅 / 패턴 매칭 | sonnet |
| Korean prose 조작 (skill 본문 / MD 편집) | sonnet |
| 신규 테스트 작성 포함 (`**검증**:` + `Test:` 경로) | sonnet (하한) |
| 설계 / 광범위 코드베이스 이해 | opus |
| 누락 / 모호 | sonnet |
```

- [ ] **Step 4: Backward compat 문단 교체 (격상은 실행 층 위임)**

**원본** (`skills/writing-plans/SKILL.md:247`):
```markdown
Backward compat: 필드 생략 시 — 신규 테스트 포함 task 는 sonnet floor, 그 외 haiku. 테스트 코드 블록이 있는 기존 계획서 (v2.8 이전) 는 기존 룰 (테스트 포함 전체 byte-copy + haiku) 그대로.
```

**수정 후**:
```markdown
Backward compat: 필드 생략 시 sonnet. 금지된 옛 하위 모델 값이 남은 기존 계획서는 실행 층이 sonnet 으로 격상해 dispatch 한다 (`js-super-sub-driven` Model Selection 참조 — 계획서 수정을 요구하지 않는다). 테스트 코드 블록이 있는 기존 계획서 (v2.8 이전) 는 테스트 포함 전체 byte-copy 룰 그대로 (모델은 sonnet 하한).
```

### Task 2: auto-writing-plans — Model 힌트 자동 룰 동기 (페어 atomic)

**Files:**
- Modify: `skills/auto-writing-plans/SKILL.md:31`

**Model**: sonnet

**검증**: 수정 후 `grep -ni "haiku" skills/auto-writing-plans/SKILL.md` 0건.

- [ ] **Step 1: Model 힌트 자동 룰 교체**

**원본** (`skills/auto-writing-plans/SKILL.md:31`):
```markdown
- Model 힌트 자동: 1-2 파일 mechanical → haiku / 다중 파일 + 통합 → sonnet / 설계 + 광범위 → opus / Korean prose 조작 → sonnet (Haiku rephrasing 위험) / 신규 테스트 작성 포함 task → 최소 sonnet (v2.9+ floor)
```

**수정 후**:
```markdown
- Model 힌트 자동: 기본 sonnet (sonnet 하한 — 이보다 낮은 모델 값 금지) / 설계 + 광범위 → opus / 필드 생략 시 sonnet. mechanical · Korean prose 조작 · 신규 테스트 포함 모두 sonnet
```

### Task 3: js-super-sub-driven — dispatch 단일 룰 (11개 지점)

**Files:**
- Modify: `skills/js-super-sub-driven/SKILL.md:91-524`

**Model**: sonnet

**검증**: 수정 후 `grep -n 'model: "haiku"' skills/js-super-sub-driven/SKILL.md` 0건 + `grep -n "model='haiku'"` 0건 + `grep -cF "haiku 격상"` 1건 이상 + `grep -cF "하한 sonnet"` 1건 이상.

- [ ] **Step 1: DAG 예시 모델 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:91-92`):
```python
    Task(id=1, name='Foo', files=['scripts/dag_builder.py'], deps=[], model='haiku'),
    Task(id=2, name='Bar', files=['scripts/dag_builder.py'], deps=[1], model='haiku'),
```

**수정 후**:
```python
    Task(id=1, name='Foo', files=['scripts/dag_builder.py'], deps=[], model='sonnet'),
    Task(id=2, name='Bar', files=['scripts/dag_builder.py'], deps=[1], model='sonnet'),
```

- [ ] **Step 2: Model Selection 본문 단일 룰 재작성**

**원본** (`skills/js-super-sub-driven/SKILL.md:112`):
```markdown
**Implementer dispatch 모델은 조건부 (v2.9+)** — 순수 byte-copy task (`**원본**`/`**수정 후**` 블록만, 신규 테스트 작성 없음) 는 **`haiku` 고정** (v2.0.0 byte-copy — 기계적 복사라 추론 모델 불필요). **신규 테스트 작성 포함 task** (`**검증**:` 필드 + `Files:` 의 `Test:` 경로 존재 + 테스트 코드 블록 없음) 는 plan 의 `**Model**:` 값 (**최소 sonnet floor**) 으로 dispatch — 자연어 검증 설명만으로 테스트 코드를 작성해야 하기 때문. 하위 호환: task 에 테스트 코드 블록이 있으면 (v2.8 이전 형식) 기존 룰 (전체 byte-copy + haiku) 우선. 구현 코드의 STRICT BYTE-COPY 는 dispatch 모델과 무관하게 적용. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch (아래 W-2 Stage 1/2/3 참조).
```

**수정 후**:
```markdown
**Implementer dispatch 모델은 단일 룰 — haiku 사용 금지, 하한 sonnet.** implementer 는 항상 plan 의 `**Model**:` 값으로 dispatch 한다. 필드 생략 시 sonnet 기본값 (dispatch log 판정 근거 예: "Task 1 model: sonnet (기본값)"). 옛 계획서에 haiku 값이 남아 있으면 sonnet 으로 격상해 dispatch 하고 판정 근거에 격상 사실을 표기한다 (예: "Task 1 model: sonnet (haiku 격상)") — 계획서 수정을 요구하지 않는다. 테스트 소스 분기 (v2.9+) 는 dispatch 모델과 분리되어 그대로 유지된다 — task 에 테스트 코드 블록이 있으면 (v2.8 이전 형식) 테스트도 byte-copy 우선 (implementer-prompt Test Authoring 참조). 구현 코드의 STRICT BYTE-COPY 는 dispatch 모델과 무관하게 적용 (sonnet implementer 도 구현 코드는 byte-copy). task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch (아래 W-2 Stage 1/2/3 참조).
```

- [ ] **Step 3: 복잡도 참고 문장 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:116`):
```markdown
참고 — plan 의 `**Model**:` 값이 나타내는 task 복잡도 (신규 테스트 포함 task 는 dispatch 모델로도 사용, v2.9+):
```

**수정 후**:
```markdown
참고 — plan 의 `**Model**:` 값 (implementer dispatch 모델로 사용):
```

- [ ] **Step 4: 복잡도 표 haiku 행 제거**

**원본** (`skills/js-super-sub-driven/SKILL.md:118-122`):
```markdown
| Task 신호 | 복잡도 힌트 |
|---|---|
| 1-2 파일 + 명확한 spec, 기계적 구현 | **haiku** |
| 다중 파일 통합 / 패턴 매칭 / 디버깅 | **sonnet** |
| 설계 판단 / 광범위 코드베이스 이해 / 리뷰 | **opus** |
```

**수정 후**:
```markdown
| Task 신호 | Model 값 |
|---|---|
| 기계적 구현 / 다중 파일 통합 / 패턴 매칭 / 디버깅 | **sonnet** |
| 설계 판단 / 광범위 코드베이스 이해 / 리뷰 | **opus** |
```

- [ ] **Step 5: dispatch 예시 모델 라인 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:127`):
```text
  model: "haiku"   # 순수 byte-copy task 는 haiku / 신규 테스트 포함 task 는 plan **Model**: 값 (최소 sonnet) — v2.9+
```

**수정 후**:
```text
  model: "sonnet"   # plan **Model**: 값 (생략 시 sonnet 기본, 하한 sonnet)
```

- [ ] **Step 6: W-2 implementer 라인 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:153`):
```markdown
- Implementer (`./implementer-prompt.md`, 순수 byte-copy task 는 `model: "haiku"` / 신규 테스트 포함 task 는 plan `**Model**:` 값 (최소 sonnet) — v2.9+)
```

**수정 후**:
```markdown
- Implementer (`./implementer-prompt.md`, plan `**Model**:` 값 — 생략 시 sonnet, 하한 sonnet)
```

- [ ] **Step 7: Stage 1 dispatch 라인 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:163`):
```markdown
   Dispatch via `./implementer-prompt.md` (순수 byte-copy=haiku / 신규 테스트 포함=plan `**Model**:` 값, 최소 sonnet — v2.9+).
```

**수정 후**:
```markdown
   Dispatch via `./implementer-prompt.md` (plan `**Model**:` 값 — 생략 시 sonnet, 하한 sonnet).
```

- [ ] **Step 8: Stage 1/2/3 마무리 문단 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:179-181`):
```markdown
NEEDS_USER → main agent gate. Plan's `**Model**:` value drives Stage 1 dispatch
ONLY for tasks that author new tests (v2.9+, min sonnet floor); pure byte-copy
tasks stay haiku. Spec reviewer remains sonnet (D11/D-T2 PRD).
```

**수정 후**:
```markdown
NEEDS_USER → main agent gate. Plan's `**Model**:` value drives Stage 1 dispatch
for every task (min sonnet floor). Spec reviewer remains sonnet (D11/D-T2 PRD).
```

- [ ] **Step 9: dispatch log 예시 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:350-351`):
```text
  - Implementer task 1 (model: haiku)
  - Implementer task 2 (model: haiku)]   # 두 task 모두 순수 byte-copy → haiku (신규 테스트 포함 task 면 plan **Model**: 값 — v2.9+)
```

**수정 후**:
```text
  - Implementer task 1 (model: sonnet)
  - Implementer task 2 (model: sonnet)]   # 두 task 모두 plan **Model**: 값 — 생략 시 sonnet 기본 (하한 sonnet)
```

- [ ] **Step 10: 핵심 패턴 1번 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:396`):
```markdown
1. dispatch 는 항상 **명시 모델 주입** (implementer=조건부: 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan **Model**: 값 (최소 sonnet), spec-reviewer=sonnet 고정) — 부모 모델 상속 회피
```

**수정 후**:
```markdown
1. dispatch 는 항상 **명시 모델 주입** (implementer=plan **Model**: 값 (생략 시 sonnet, 하한 sonnet), spec-reviewer=sonnet 고정) — 부모 모델 상속 회피
```

- [ ] **Step 11: 자동 판정 표 + Anti-Pattern 표 교체**

**원본** (`skills/js-super-sub-driven/SKILL.md:482`):
```markdown
| implementer dispatch model | v2.9+ 조건부 자동 판정 — 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan `**Model**:` 값 (최소 sonnet). 게이트 없이 자동 |
```

**수정 후**:
```markdown
| implementer dispatch model | plan `**Model**:` 값 자동 적용 — 생략 시 sonnet, 하한 sonnet. 게이트 없이 자동 |
```

**원본** (`skills/js-super-sub-driven/SKILL.md:524`):
```markdown
| implementer model 변경 시 게이트 | 룰 2 위반. v2.9+ 조건부 룰 (순수 byte-copy=haiku / 신규 테스트 포함=plan **Model**: 값) 로 자동 판정. |
```

**수정 후**:
```markdown
| implementer model 변경 시 게이트 | 룰 2 위반. plan **Model**: 값 (생략 시 sonnet, 하한 sonnet) 으로 자동 판정. |
```

### Task 4: implementer-prompt — 기본 모델 sonnet

**Files:**
- Modify: `skills/js-super-sub-driven/implementer-prompt.md:7`

**Model**: sonnet

**검증**: 수정 후 `grep -n 'model: "haiku"' skills/js-super-sub-driven/implementer-prompt.md` 0건 + 격상 문구 존재.

- [ ] **Step 1: 헤더 모델 주석 교체**

**원본** (`skills/js-super-sub-driven/implementer-prompt.md:7`):
```text
  model: "haiku"   # v2.0.0+ 기본 haiku (순수 byte-copy task). v2.9+: 신규 테스트 작성 포함 task (`**검증**:` 필드 + Test: 경로 + 테스트 코드 블록 없음) 는 plan 의 `**Model**:` 값 (최소 sonnet) 으로 dispatch. (See CLAUDE.md "plan 테스트 자연어 축약 결합" + "implementer-prompt + reorder-prompt + plan_byte_check" sections.)
```

**수정 후**:
```text
  model: "sonnet"   # 기본 sonnet — plan 의 `**Model**:` 값으로 dispatch (생략 시 sonnet, 하한 sonnet). 옛 계획서의 haiku 값은 sonnet 으로 격상. (See CLAUDE.md "plan 테스트 자연어 축약 결합" + "implementer-prompt + reorder-prompt + plan_byte_check" sections.)
```

### Task 5: reorder-prompt — implementer 서술 정정

**Files:**
- Modify: `skills/js-super-sub-driven/reorder-prompt.md:15`

**Model**: sonnet

**검증**: 수정 후 L15 에 haiku 서술 없음. L10 의 "NOT haiku." 금지-언급은 유지.

- [ ] **Step 1: BLOCKED 배경 서술 교체**

**원본** (`skills/js-super-sub-driven/reorder-prompt.md:15`):
```text
    The implementer (haiku, byte-copy mode) reported BLOCKED because
```

**수정 후**:
```text
    The implementer (byte-copy mode) reported BLOCKED because
```

### Task 6: executing-plans — 룰 2 dispatch row 단일 룰 서술

**Files:**
- Modify: `skills/executing-plans/SKILL.md:329-381`

**Model**: sonnet

**검증**: 수정 후 `grep -ni "haiku" skills/executing-plans/SKILL.md` 0건 + `grep -cF "하한 sonnet"` 1건 이상.

- [ ] **Step 1: 룰 2 자동 판정 row 교체**

**원본** (`skills/executing-plans/SKILL.md:329`):
```markdown
| dispatch model 선택 | (subagent 모드) v2.9+ 조건부 자동 판정 — 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan 의 `**Model**:` 값 (최소 sonnet). 게이트 없이 자동 |
```

**수정 후**:
```markdown
| dispatch model 선택 | (subagent 모드) plan 의 `**Model**:` 값 자동 적용 — 생략 시 sonnet, 하한 sonnet (`js-super-sub-driven` Model Selection 참조). 게이트 없이 자동 |
```

- [ ] **Step 2: Anti-Pattern row 교체**

**원본** (`skills/executing-plans/SKILL.md:381`):
```markdown
| dispatch model 변경 시 게이트 | 룰 2 위반. (subagent 모드) v2.9+ 조건부 룰 (순수 byte-copy=haiku / 신규 테스트 포함=plan **Model**: 값) 로 자동 판정. |
```

**수정 후**:
```markdown
| dispatch model 변경 시 게이트 | 룰 2 위반. (subagent 모드) plan **Model**: 값 (생략 시 sonnet, 하한 sonnet) 으로 자동 판정. |
```

### Task 7: fixture 6파일 — 기대값 sonnet 동기

**Files:**
- Modify: `skills/js-super-sub-driven/tests/G5-model-haiku/README.md:1-5`
- Modify: `skills/js-super-sub-driven/tests/G6-no-model-default/README.md:5`
- Modify: `skills/js-super-sub-driven/tests/G8-reviewer-sonnet/README.md:3-6`
- Modify: `skills/js-super-sub-driven/tests/H11-user-edit-reorder/README.md:8`
- Modify: `skills/js-super-sub-driven/tests/H15-natural-lang-verify/README.md:20`
- Modify: `skills/js-super-sub-driven/tests/README.md:21-24`

**Model**: sonnet

**검증**: G5 가 격상 (하위 호환) positive 시나리오로 재목적화, 나머지 5파일의 dispatch 기대 모델이 전부 sonnet. `grep -rn "implementer haiku" skills/js-super-sub-driven/tests/` 0건.

- [ ] **Step 1: G5 재목적화 (격상 검증)**

**원본** (`skills/js-super-sub-driven/tests/G5-model-haiku/README.md:1-5`):
```markdown
# G5: Model Hint = haiku

**Scenario:** plan 의 task 1 에 `**Model**: haiku` 명시.

**Expected:** task 1 은 신규 테스트 작성 없음 (`**검증**:` 필드/`Test:` 경로 기반 판정) → 메인이 implementer dispatch 시 `model: "haiku"` 로 호출 (v2.9+ 조건부 룰의 순수 byte-copy 분기). spec-reviewer 는 sonnet.
```

**수정 후**:
```markdown
# G5: Model Hint = haiku (sonnet 격상)

**Scenario:** 옛 plan 의 task 1 에 `**Model**: haiku` 잔존 (하위 호환 시뮬레이션).

**Expected:** haiku 는 사용 금지 — 메인이 implementer dispatch 시 `model: "sonnet"` 으로 격상 호출하고, dispatch log 판정 근거에 격상 사실을 표기 (예: "Task 1 model: sonnet (haiku 격상)"). 계획서 수정 요구 없음. spec-reviewer 는 sonnet.
```

- [ ] **Step 2: G6 기대값 단일 룰**

**원본** (`skills/js-super-sub-driven/tests/G6-no-model-default/README.md:5`):
```markdown
**Expected:** DAG 표시 default 는 sonnet 유지. dispatch 는 v2.9+ 조건부 룰 — 신규 테스트 작성 포함 task 면 sonnet (floor), 아니면 haiku. 한 줄 dispatch log 로 판정 근거 표기 (예: "Task 1 model: haiku (순수 byte-copy)").
```

**수정 후**:
```markdown
**Expected:** DAG 표시 default 는 sonnet 유지. dispatch 는 단일 룰 — plan `**Model**:` 값, 생략 시 sonnet 기본 (haiku 사용 금지, 하한 sonnet). 한 줄 dispatch log 로 판정 근거 표기 (예: "Task 1 model: sonnet (기본값)").
```

- [ ] **Step 3: G8 시나리오 격상 반영**

**원본** (`skills/js-super-sub-driven/tests/G8-reviewer-sonnet/README.md:3-6`):
```markdown
**Scenario:** plan task 1 에 `**Model**: haiku` 박힘 (implementer 는 haiku). 동시에 spec-reviewer dispatch 가 sonnet 인지 검증. G5 plan 재사용.

**Expected dispatch:**
- Implementer: `model: "haiku"` (Task 1 의 hint)
```

**수정 후**:
```markdown
**Scenario:** plan task 1 에 `**Model**: haiku` 박힘 (implementer 는 sonnet 으로 격상). 동시에 spec-reviewer dispatch 가 sonnet 인지 검증. G5 plan 재사용.

**Expected dispatch:**
- Implementer: `model: "sonnet"` (Task 1 hint 는 금지된 값 → 격상)
```

- [ ] **Step 4: H11 implementer 모델 서술 동기**

**원본** (`skills/js-super-sub-driven/tests/H11-user-edit-reorder/README.md:8`):
```markdown
4. Wave 진입 → Implementer (haiku, byte-copy) 시도.
```

**수정 후**:
```markdown
4. Wave 진입 → Implementer (sonnet, byte-copy) 시도.
```

- [ ] **Step 5: H15 기대 모델 동기**

**원본** (`skills/js-super-sub-driven/tests/H15-natural-lang-verify/README.md:20`):
```markdown
- implementer dispatch 모델 = haiku (byte-copy)
```

**수정 후**:
```markdown
- implementer dispatch 모델 = sonnet (byte-copy — haiku 사용 금지)
```

- [ ] **Step 6: tests/README 인덱스 2행 갱신**

**원본** (`skills/js-super-sub-driven/tests/README.md:21`):
```markdown
| G5-model-haiku | `**Model**: haiku` → implementer haiku dispatch | AC-4 | (수동 dogfood) |
```

**수정 후**:
```markdown
| G5-model-haiku | `**Model**: haiku` 잔존 → sonnet 격상 dispatch | AC-4 | (수동 dogfood) |
```

**원본** (`skills/js-super-sub-driven/tests/README.md:24`):
```markdown
| G8-reviewer-sonnet | implementer haiku 시에도 reviewer sonnet 고정 | AC-6 | (수동 dogfood) |
```

**수정 후**:
```markdown
| G8-reviewer-sonnet | implementer 격상 케이스에도 reviewer sonnet 고정 | AC-6 | (수동 dogfood) |
```

### Task 8: CLAUDE.md — 결합 메모 갱신 + 신규 결합 섹션

**Files:**
- Modify: `CLAUDE.md:148-253` + 파일 끝 신규 섹션 append

**Model**: sonnet

**검증**: 신규 섹션의 bash 블록이 eval 러너 파싱 계약 (읽기 전용 명령 + `# expected:`) 을 지키고, `grep -cF "## 서브에이전트 sonnet 하한 결합 (haiku 사용 금지)" CLAUDE.md` 1건.

- [ ] **Step 1: v1.1.14 결합 메모 라인 갱신**

**원본** (`CLAUDE.md:148`):
```markdown
- writing-plans 의 평가 룰 (haiku/sonnet/opus 분기) 변경 시 `js-super-sub-driven` 의 dispatch 단계도 동시 수정
```

**수정 후**:
```markdown
- writing-plans 의 평가 룰 (sonnet/opus 분기) 변경 시 `js-super-sub-driven` 의 dispatch 단계도 동시 수정
```

- [ ] **Step 2: v2.9 결합 메모 항목 4 갱신**

**원본** (`CLAUDE.md:253`):
```markdown
4. `skills/js-super-sub-driven/SKILL.md` — 조건부 dispatch (신규 테스트 포함 task = `**Model**:` 값, 최소 sonnet / 순수 byte-copy = haiku)
```

**수정 후**:
```markdown
4. `skills/js-super-sub-driven/SKILL.md` — dispatch 모델 단일 룰 (plan `**Model**:` 값, 하한 sonnet — "서브에이전트 sonnet 하한 결합" 섹션으로 조건부 분기 폐지)
```

- [ ] **Step 3: 신규 결합 섹션 append (파일 끝)**

**append 내용**:

````markdown
## 서브에이전트 sonnet 하한 결합 (haiku 사용 금지)

서브에이전트 dispatch 전 경로에서 haiku 사용 금지. implementer dispatch = plan `**Model**:` 값 (생략 시 sonnet, 하한 sonnet). 계획서 작성 층의 `**Model**:` 필드는 `sonnet | opus` 2값. 옛 계획서에 남은 haiku 값은 실행 층이 sonnet 으로 격상해 dispatch (계획서 수정 요구 없음, dispatch log 에 격상 표기). v2.9 의 조건부 분기 (순수 byte-copy = haiku) 는 폐지. spec: `docs/features/2026-08-29-서브에이전트-sonnet-기본/`.

### 핵심 룰

- **작성 층 (writing-plans / auto-writing-plans) 본문에서 haiku 단어 소멸** — enum 2값 + 판정표 sonnet 흡수. executing-plans 룰 2 row 도 haiku 단어 없이 js-super-sub-driven 참조로 위임
- **실행 층 (js-super-sub-driven SKILL.md + implementer-prompt.md) 만 격상 문구에서 haiku 언급 허용** — dispatch 패턴 (`model: "haiku"` / `model='haiku'`) 은 0
- **금지-언급 무변경 — spec-reviewer-prompt / code-pretty / glossary 3파일 + reorder-prompt L10 의 "NOT haiku." 주석** — "Haiku 쓰지 마라" 류 문구는 새 룰과 정합이라 잔존 허용
- **STRICT BYTE-COPY 룰은 모델 무관 유지** — sonnet implementer 도 구현 코드는 byte-copy

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| 작성 층만 변경 (실행 층 미동기) | 실행 층이 옛 조건부 룰로 haiku dispatch 부활 |
| 실행 층만 변경 (작성 층 미동기) | 계획서에 haiku 값 재유입 — plan 모델 ↔ dispatch 모델 불일치 (v1.1.14 결합 회귀) |
| 격상 룰 제거 | 옛 계획서 (`**Model**: haiku` 잔존) 실행 시 금지 값 그대로 dispatch |
| 판정표에 haiku 행 부활 | 금지 무력화 — 작성 세션이 다시 haiku 배정 |

### 회귀 catch grep

```bash
grep -ni "haiku" skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md skills/executing-plans/SKILL.md
# expected: 0

grep -n 'model: "haiku"' skills/js-super-sub-driven/SKILL.md skills/js-super-sub-driven/implementer-prompt.md
# expected: 0

grep -n "model='haiku'" skills/js-super-sub-driven/SKILL.md
# expected: 0

grep -cF "haiku 격상" skills/js-super-sub-driven/SKILL.md
# expected: >= 1

grep -cF "하한 sonnet" skills/js-super-sub-driven/SKILL.md skills/executing-plans/SKILL.md
# expected: 각 >= 1

grep -cF "sonnet | opus" skills/writing-plans/SKILL.md
# expected: >= 1
```

### 영향 범위

- 스킬 본문 6 (writing-plans / auto-writing-plans / js-super-sub-driven SKILL+implementer+reorder / executing-plans) + fixture 6 + CLAUDE.md. `scripts/` / `hooks/` / og-* / `auto-executing-plans` (dispatch 룰을 js-super-sub-driven 에 위임) 영향 0
- reorder / spec-reviewer / code-pretty / glossary 의 sonnet 고정 — 동작 변경 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
````

### Task 9: [검증] 회귀 grep 전수 + eval 러너 수집 확인

**Files:** (읽기 전용 — 코드 변경 없음)

**Model**: sonnet

**Depends**: Task 1~8

**검증**: Task 8 의 회귀 catch grep 6종 전부 기대값 통과 + `evals.runner.coupling.collect_rules` 수집 룰 수 = 151 (실행 전 실측 145 + Task 8 신규 bash 룰 6) + `grep -rn "implementer haiku" skills/` 0건.

- [ ] **Step 1: 회귀 grep 6종 실행** — Task 8 신규 섹션의 bash 블록 그대로 실행, 기대값 대조
- [ ] **Step 2: eval 러너 수집 확인** — `python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"` 출력 = 151 (실행 전 실측 145 + 신규 6건). 151 이 아니면 Task 8 신규 섹션의 bash 블록 형식 (펜스 언어 bash / `# expected:` 주석 위치) 을 재점검
- [ ] **Step 3: 전수 스윕** — `grep -rni "haiku" skills/ commands/ scripts/ CLAUDE.md` 결과가 (a) 실행 층 격상 문구, (b) 금지-언급 3파일, (c) fixture 시나리오, (d) CLAUDE.md 결합 메모, (e) reorder-prompt L10 금지-언급 외 0건인지 확인

## §2 위험 코드 지점

| ID | 위험 | 지점 | 완화 |
|---|---|---|---|
| R-1 | 결합 회귀 — 작성 층/실행 층 한쪽만 수정 시 plan↔dispatch 모델 불일치 | Task 1·2 ↔ Task 3·4 | Task 1~8 같은 브랜치 atomic + Task 8 결합 메모 + Task 9 grep |
| R-2 | 격상 문구의 haiku 단어 잔존으로 전수 0건 grep 불가 | Task 3 Step 2, Task 4 | 파일별 기대값 세분화 (Task 8 grep 설계) — 작성 층 3파일만 0건, 실행 층은 패턴 grep |
| R-3 | CLAUDE.md 신규 bash 블록이 eval 러너 파싱 계약 위반 시 룰 조용히 누락 | Task 8 Step 3 | 읽기 전용 명령 + `# expected:` 형식 준수 + Task 9 Step 2 수집 수 확인 |
| R-4 | byte-copy task 비용·대기 시간 증가 | 전체 dispatch | 수용된 트레이드오프 (requirements 우려/해결) — 완화 없음, 기록만 |
| R-5 | 워크트리 버전 bump 금지 위반 | 6 manifest | 어떤 task 도 manifest 미접촉 (Task 8 영향 범위에 명시) |

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 09:18] [구현계획서-수정]
- **id**: CH-20260829-003
- **이유**: auto-writing-plans 자동 작성 + plan_byte_check 통과 (원본 블록 21개, 1회차) + verifying-spec 지적 3건 반영 (테스트 소스 분기 유지 문장 / 금지-언급 목록에 reorder-prompt L10 / eval 기준선 145→151 명시)
- **무엇이**: 서브에이전트-sonnet-기본-implementation-plan.md 전체 (Task 1~9 + §2 위험 코드 지점 R-1~R-5)
- **영향범위**: 실행 단계 (auto-executing-plans / js-super-sub-driven) — Task 1~8 wave-parallel + Task 9 검증
- **연관 항목**: CH-20260829-002

### [2026-08-29 09:30] [코드-수정] (batch: tasks 1..8)
- **id**: CH-20260829-004
- **이유**: 서브에이전트 dispatch 에서 haiku 사용 금지 + 하한 sonnet 단일 룰 적용 (FR-1~FR-5). 계획서 작성 층 enum 2값 축소 + 실행 층 조건부 분기 폐지 + 옛 계획서 haiku 값 실행 시점 격상 + fixture / 결합 메모 동기
- **무엇이**: skills/writing-plans/SKILL.md, skills/auto-writing-plans/SKILL.md, skills/js-super-sub-driven/SKILL.md, skills/js-super-sub-driven/implementer-prompt.md, skills/js-super-sub-driven/reorder-prompt.md, skills/executing-plans/SKILL.md, skills/js-super-sub-driven/tests/{G5-model-haiku,G6-no-model-default,G8-reviewer-sonnet,H11-user-edit-reorder,H15-natural-lang-verify}/README.md, skills/js-super-sub-driven/tests/README.md, CLAUDE.md
- **영향범위**: 계획서 작성 두 경로 (정식 / auto) 의 Model 필드 산정 + 서브에이전트 실행 경로의 implementer dispatch 모델. scripts / hooks / og-* / auto-executing-plans / spec-reviewer / code-pretty / glossary 영향 0 (금지-언급 문구는 새 룰과 정합이라 무변경)
- **위험 카테고리**: none (전 파일 마크다운 룰 문서 — 실행 코드 변경 0건, 3-checklist 트리거 없음)
- **task별 세부 (9건)**:
  - Task 1: `skills/writing-plans/SKILL.md:201-247` — Model enum sonnet|opus 축소 + 판정표 haiku 행 sonnet 흡수 + backward compat 격상 위임 (none) — commits: `56f0191`
  - Task 2: `skills/auto-writing-plans/SKILL.md:31` — Model 힌트 자동 룰 sonnet 하한 동기 (none) — commits: `f4e03d4`
  - Task 3: `skills/js-super-sub-driven/SKILL.md:91-533` — dispatch 조건부 분기 폐지, 단일 룰 + 격상 표기 (12지점) (none) — commits: `2bba50f`
  - Task 4: `skills/js-super-sub-driven/implementer-prompt.md:7` — 기본 모델 sonnet + 격상 룰 (none) — commits: `d40501b`
  - Task 5: `skills/js-super-sub-driven/reorder-prompt.md:15` — implementer 서술에서 모델 표기 제거 (L10 금지-언급 보존) (none) — commits: `27d2c11`
  - Task 6: `skills/executing-plans/SKILL.md:329,381` — dispatch row 2곳 단일 룰 서술 (none) — commits: `b44bdc8`
  - Task 7: `skills/js-super-sub-driven/tests/` 6파일 — G5 격상 positive 재목적화 + 기대 모델 sonnet 동기 (none) — commits: `e81724a`
  - Task 8: `CLAUDE.md:148,253` + 신규 섹션 — 결합 메모 갱신 + "서브에이전트 sonnet 하한 결합" 섹션 (회귀 grep 6종) (none) — commits: `eaa872f`
  - Task 3 follow-up (계획 범위 초과): `skills/js-super-sub-driven/SKILL.md:84,161` — spec reviewer 가 짚은 계획서 누락 2지점의 옛 조건부 서술 정정 (none) — commits: `38a5785`
- **연관 commits**: `8cd80bd..HEAD` (9 commits)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260829-003

### [2026-08-29 09:30] [검증] (task: Task 9 — 회귀 grep 전수 + eval 러너 수집 확인)
- **id**: CH-20260829-005
- **이유**: 새 단일 룰의 회귀 방지 장치가 실제로 작동하는지 정적 검증 (코드 변경 0건)
- **무엇이**: 회귀 catch grep 6종 + eval 러너 수집 룰 수 + 저장소 전수 haiku 스윕
- **결과**: PASS — 작성 층 3파일 haiku 0건 / dispatch 패턴 (`model: "haiku"`, `model='haiku'`) 0건 / 격상 문구 1건 / 하한 sonnet 표기 (sub-driven 9, executing-plans 2) / enum `sonnet | opus` 1건 / eval 수집 룰 145→151 (신규 6건 정확히 반영) / `implementer haiku` 0건. 전수 스윕 잔존 29건은 전부 허용 범주 — 실행 층 격상 문구 2, 금지-언급 4 (reorder L10 / spec-reviewer / code-pretty 2 / glossary), fixture 시나리오 8 (G5 plan.md 의 `**Model**: haiku` 는 격상 시나리오 입력), CLAUDE.md 결합 메모 14
- **연관 commit**: `38a5785`
- **연관 항목**: CH-20260829-004
