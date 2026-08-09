---
commit_policy: per-task
---

# plan-test-자연어축약 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 구현계획서에서 테스트 코드 블록을 없애고 task 헤더 `**검증**:` 필드 (자연어 1~2줄) 로 대체 — 실제 테스트 작성·실행은 실행 단계에서 TDD 순서 그대로 수행.

**Architecture:** 세 층 동시 개정 — (1) 계획서 작성 층 (writing-plans / auto-writing-plans 페어) 에 `**검증**:` 필드 스키마 + 템플릿 도입, (2) 실행 층 (executing-plans / implementer-prompt) 에 "자연어 설명 → 테스트 작성" 절차 + 하위 호환 분기, (3) dispatch 층 (js-super-sub-driven) 에 조건부 모델 룰 (신규 테스트 포함 task = `**Model**:` 값, 최소 sonnet / 순수 byte-copy = haiku).

**Tech Stack:** markdown skill 본문 편집 (byte-copy 페어 33곳 + 코드펜스 포함 영역 2곳은 라벨 면제), grep 회귀 검증.

**Spec inputs:**
- plan-test-자연어축약-requirements.md — 결정 1~3 (자연어 축약 / TDD 실행 유지 / 하위 호환), 요구 항목 1~6
- plan-test-자연어축약-tech-design.md — D1 (검증 필드), D2 (조건부 Model 승격), D3 (task 단위 하위 호환), D4 (same-file step 재서술), D5 (8 파일 atomic)

---

## 0. Wave / byte-copy 개요

| Wave | Task | 파일 | Model | byte-copy |
|---|---|---|---|---|
| 1 | T1 — writing-plans 본문 개정 (검증 필드 도입) | skills/writing-plans/SKILL.md | haiku | 페어 8 + 면제 1 (템플릿, 펜스 포함) |
| 1 | T2 — auto-writing-plans mirror 동기 | skills/auto-writing-plans/SKILL.md | haiku | 페어 3 |
| 1 | T3 — implementer-prompt 테스트 분리 룰 | skills/js-super-sub-driven/implementer-prompt.md | haiku | 페어 3 |
| 1 | T4 — sub-driven dispatch 조건부 룰 | skills/js-super-sub-driven/SKILL.md | haiku | 페어 11 |
| 1 | T5 — executing-plans 테스트 소스 분기 | skills/executing-plans/SKILL.md | haiku | 페어 3 |
| 1 | T6 — PROMPT_KO mirror 동기 | PROMPT_KO.md | haiku | 페어 1 + 면제 1 (템플릿, 펜스 포함) |
| 1 | T7 — CLAUDE.md 결합 메모 | CLAUDE.md | haiku | 페어 2 |
| 1 | T8 — fixture 갱신 + H14 신규 | tests/H12·G5·G6·H14 | haiku | 페어 3 + Create 1 |
| 2 | T9 — 회귀 grep 일괄 검증 | (검증 전용, 코드 변경 없음) | haiku | N/A |

**byte-copy 면제 2곳의 근거**: `plan_byte_check` 의 `**원본**` 정규식은 블록 내부의 ``` 중첩 펜스를 다루지 못한다 (첫 ``` 에서 매치가 끊김). 따라서 코드펜스가 든 템플릿 재작성 2곳 (T1 step 6, T6 step 3) 은 라벨 없는 블록 A/B (old_string/new_string 그대로 사용) + grep 검증으로 처리한다 — v2.4 계획서의 면제 선례 답습. 면제 블록도 본 계획서에 전문이 실려 있어 실행은 그대로 verbatim copy 다.

**주의**: 6 manifest 버전 bump 는 본 계획 범위 밖 — dev 가 직접 진행한다.

## 1. 단계별 작업

### Task 1: writing-plans 본문 개정 — 검증 필드 도입

**Files:**
- Modify: `skills/writing-plans/SKILL.md`

**Model**: haiku

**검증**: writing-plans 본문에서 옛 "테스트 코드 강제" 문구가 모두 사라지고 (`without actual test code` 0 매치, 템플릿 Step 1 테스트 코드 블록 제거), `**검증**:` 필드 룰 + 템플릿의 `**Model**:` 줄 / `Test:` 경로가 보존됐는지 grep 으로 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF '계획서에는 테스트 코드를 싣지 않는다' skills/writing-plans/SKILL.md`
Expected: 0 매치 (exit 1) — 변경 전이므로 실패가 정상

- [ ] **Step 2: Checklist 항목 3 문구 교체**

**원본** (`skills/writing-plans/SKILL.md:65`):
```
3. **구현계획서 task 목록 작성** — each task = one TDD cycle (test → fail → impl → pass → commit), 2-5 minutes per step
```

**수정 후**:
```
3. **구현계획서 task 목록 작성** — each task = one TDD cycle (계획서에는 `**검증**:` 자연어 설명만, 실행 단계에서 test → fail → impl → pass → commit), 2-5 minutes per step
```

- [ ] **Step 3: Schema 블록에 검증 필드 추가**

**원본** (`skills/writing-plans/SKILL.md:98-99`):
```
   ### Task 1: <Component>
   **Files:** Create/Modify/Test
```

**수정 후**:
```
   ### Task 1: <Component>
   **Files:** Create/Modify/Test
   **검증**: <무엇을 검증하는지 + 성공 기준 (자연어 1~2줄)>
```

- [ ] **Step 4: Bite-Sized Granularity 재서술**

**원본** (`skills/writing-plans/SKILL.md:127-132`):
```
Each step is one action (2-5 minutes):
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step (skip if git is not initialized)
```

**수정 후**:
```
Each step is one action (2-5 minutes):
- "`**검증**:` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인 (테스트 코드는 실행 단계가 작성)" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step (skip if git is not initialized)

**계획서에는 테스트 코드를 싣지 않는다 (v2.9+)** — task 헤더의 `**검증**:` 필드 (자연어 1~2줄) 가 "무엇을 검증하는지 + 어떤 기준으로 성공인지" 를 정의하고, 실제 테스트 코드 작성·실행은 실행 단계 (executing-plans / js-super-sub-driven) 가 담당한다. TDD 순서 (테스트 먼저 → 구현) 는 실행 단계에서 그대로 유지된다.
```

- [ ] **Step 5: same-file 묶음 step 구조 재서술**

**원본** (`skills/writing-plans/SKILL.md:147-152`):
```
세 조건 중 하나라도 어기면 분리. 묶을 때 task 안 step 구조:

- step 1: 통합 test 작성 (한 번)
- step 2~N: 각 변경의 byte-copy Edit (`**원본**` / `**수정 후**` 페어)
- step N+1: test 실행 → pass 확인
- step N+2: self-review
```

**수정 후**:
```
세 조건 중 하나라도 어기면 분리. 묶을 때 task 안 step 구조:

- step 1: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 한 번)
- step 2~N: 각 변경의 byte-copy Edit (`**원본**` / `**수정 후**` 페어)
- step N+1: test 실행 → pass 확인
- step N+2: self-review
```

- [ ] **Step 6: Task Structure 템플릿 재작성 (byte-copy 면제 — 펜스 포함)**

Edit 도구로 old_string = 아래 블록 A 전문 (writing-plans SKILL.md L182-223), new_string = 아래 블록 B 전문. 두 블록 모두 그대로 verbatim 사용 — 의역/재포맷 금지.

블록 A (기존 본문):

`````
````markdown
### Task N: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Model**: haiku

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit (skip if no git)**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````
`````

블록 B (새 본문):

`````
````markdown
### Task N: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Model**: haiku

**검증**: <이 task 의 테스트가 무엇을 검증하는지 + 성공 기준 — 자연어 1~2줄. 테스트 코드는 싣지 않는다 (v2.9+)>

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계 (executing-plans / js-super-sub-driven) 가 테스트 코드를 직접 작성한다. 계획서에는 코드를 싣지 않는다.

Run: `pytest tests/path/test.py -v`
Expected: FAIL (구현 전)

- [ ] **Step 2: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/path/test.py -v`
Expected: PASS

- [ ] **Step 4: Commit (skip if no git)**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````
`````

- [ ] **Step 7: Task Model Hint 섹션 재작성 — dispatch 결합 복원**

**원본** (`skills/writing-plans/SKILL.md:225-241`):
```
## Task Model Hint (v1.1.14+, 정보용)

Each task block MAY include `**Model**: haiku | sonnet | opus` as an **informational complexity hint**. Under v2.0.0 byte-copy, `js-super-sub-driven` dispatches the implementer with **haiku FIXED** (기계적 byte-copy 라 추론 모델 불필요) — the `**Model**:` field does NOT change the implementer dispatch model. Spec-reviewer is always sonnet. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch.

값은 task 복잡도를 나타내는 힌트일 뿐이다 (사람이 plan 을 읽거나 DAG 요약을 볼 때 참고):

| 신호 | 복잡도 힌트 |
|---|---|
| 1-2 파일 + mechanical implementation + 명확 spec | haiku |
| 다중 파일 통합 / 디버깅 / 패턴 매칭 | sonnet |
| Korean prose 조작 (skill 본문 / MD 편집) | sonnet |
| 설계 / 광범위 코드베이스 이해 | opus |
| 누락 / 모호 | sonnet |

Backward compat: 필드는 선택이라 생략해도 된다. Existing plans (v1.1.13 and earlier) work as-is.

Note: implementer 는 항상 haiku 라 한국어 prose 를 만지는 task 는 전반적으로 haiku 의 rephrasing 위험을 가진다 (`**Model**:` 값으로 회피되지 않음). 그런 task 는 byte-copy 정확성(`**원본**`/`**수정 후**` 페어)에 특히 의존하며, byte-copy 로 감당 안 되면 BLOCKED → reorder(sonnet) 로 처리된다.
```

**수정 후**:
```
## Task Model Hint (v1.1.14+ · v2.9+ dispatch 결합 복원)

Each task block MAY include `**Model**: haiku | sonnet | opus`. v2.9+ 부터 이 필드는 신규 테스트 작성이 포함된 task 에 한해 dispatch 에 직접 쓰인다: `js-super-sub-driven` 은 **신규 테스트 작성 포함 task** (`**검증**:` 필드 + `Test:` 경로 존재 + 테스트 코드 블록 없음) 의 implementer 를 이 필드 값 (**최소 sonnet floor**) 으로 dispatch 하고, 순수 byte-copy task 는 haiku 고정을 유지한다. Spec-reviewer is always sonnet. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch.

값 산정 기준:

| 신호 | Model 값 |
|---|---|
| 1-2 파일 + mechanical implementation + 명확 spec (신규 테스트 없음) | haiku |
| 다중 파일 통합 / 디버깅 / 패턴 매칭 | sonnet |
| Korean prose 조작 (skill 본문 / MD 편집) | sonnet |
| 신규 테스트 작성 포함 (`**검증**:` + `Test:` 경로) | 최소 sonnet (floor) |
| 설계 / 광범위 코드베이스 이해 | opus |
| 누락 / 모호 | sonnet |

Backward compat: 필드 생략 시 — 신규 테스트 포함 task 는 sonnet floor, 그 외 haiku. 테스트 코드 블록이 있는 기존 계획서 (v2.8 이전) 는 기존 룰 (테스트 포함 전체 byte-copy + haiku) 그대로.

Note: 구현 코드 블록의 STRICT BYTE-COPY 룰은 dispatch 모델과 무관하게 적용된다 (sonnet implementer 도 구현 코드는 byte-copy). 한국어 prose 를 만지는 task 는 byte-copy 정확성 (`**원본**`/`**수정 후**` 페어) 에 특히 의존하며, byte-copy 로 감당 안 되면 BLOCKED → reorder(sonnet) 로 처리된다.
```

- [ ] **Step 8: Code Block Convention 에 룰 6 추가**

**원본** (`skills/writing-plans/SKILL.md:263-265`):
```
3. For tasks that CREATE a new file, the "원본" block is OMITTED — only "수정 후" block is shown (with `(new file: <path>)` annotation).
4. Both blocks MUST use the same fenced-code language identifier.
5. The `code-pretty` skill targets ONLY "수정 후" blocks. "원본" blocks are byte-immutable.
```

**수정 후**:
```
3. For tasks that CREATE a new file, the "원본" block is OMITTED — only "수정 후" block is shown (with `(new file: <path>)` annotation).
4. Both blocks MUST use the same fenced-code language identifier.
5. The `code-pretty` skill targets ONLY "수정 후" blocks. "원본" blocks are byte-immutable.
6. **테스트 파일 내용은 코드 블록으로 싣지 않는다 (v2.9+)** — 신규 테스트든 기존 테스트 수정이든 계획서에는 task 헤더의 `**검증**:` 자연어 설명으로만 적는다. Before/After 페어는 구현 코드 전용이다.
```

- [ ] **Step 9: No Placeholders 룰 반전**

**원본** (`skills/writing-plans/SKILL.md:336-338`):
```
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
```

**수정 후**:
```
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- 동어반복 `**검증**:` 필드 — "테스트를 작성한다" 처럼 무엇을/어떤 기준인지 없는 설명 (v2.9+ 테스트 코드 블록 대신 쓰는 필드라 구체성이 생명)
- 테스트 코드 블록을 계획서에 싣는 것 (v2.9+ — `**검증**:` 자연어 설명으로 대체. 기존 계획서의 테스트 코드 블록은 하위 호환으로 실행만 지원)
```

- [ ] **Step 10: Self-Review 항목 6 추가**

**원본** (`skills/writing-plans/SKILL.md:358`):
```
5. **same-file 묶음 룰 위반 검사**: task 들 중 같은 파일만 만지는 chain 이 2건 이상 있는지 확인. 있으면 D1 의 3 조건 (같은 파일 / test 경계 X / mechanical) 재검토 → 묶을지 결정. (v2.0.1+)
```

**수정 후**:
```
5. **same-file 묶음 룰 위반 검사**: task 들 중 같은 파일만 만지는 chain 이 2건 이상 있는지 확인. 있으면 D1 의 3 조건 (같은 파일 / test 경계 X / mechanical) 재검토 → 묶을지 결정. (v2.0.1+)
6. **검증 필드 구체성 (v2.9+)**: 코드 변경 task 마다 `**검증**:` 필드가 있고 "무엇을 + 어떤 기준" 을 담았는지 확인. 동어반복 ("테스트 작성" 한 줄) 이나 테스트 코드 블록이 남아 있으면 수정.
```

- [ ] **Step 11: PASS 확인**

Run:
```bash
grep -cF '계획서에는 테스트 코드를 싣지 않는다' skills/writing-plans/SKILL.md   # expected: 1
grep -n 'without actual test code' skills/writing-plans/SKILL.md               # expected: 0 매치
grep -n '항상 haiku' skills/writing-plans/SKILL.md                              # expected: 0 매치
grep -cF '**Model**: haiku' skills/writing-plans/SKILL.md                       # expected: >= 1 (템플릿 Model 줄 보존)
grep -cF 'Test: `tests/exact/path/to/test.py`' skills/writing-plans/SKILL.md    # expected: 1 (Test 경로 보존)
```

- [ ] **Step 12: self-review**

### Task 2: auto-writing-plans mirror 동기

**Files:**
- Modify: `skills/auto-writing-plans/SKILL.md`

**Model**: haiku

**검증**: mirror 3곳 (Model 힌트 룰 / Before-After 컨벤션 / same-file step 구조) 이 writing-plans 의 새 표현과 동기됐는지 — `**검증**` 필드 언급이 각 지점에 실렸는지 grep 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF '검증' skills/auto-writing-plans/SKILL.md`
Expected: 0 매치 (exit 1)

- [ ] **Step 2: Model 힌트 자동 룰에 sonnet floor 추가**

**원본** (`skills/auto-writing-plans/SKILL.md:30`):
```
- Model 힌트 자동: 1-2 파일 mechanical → haiku / 다중 파일 + 통합 → sonnet / 설계 + 광범위 → opus / Korean prose 조작 → sonnet (Haiku rephrasing 위험)
```

**수정 후**:
```
- Model 힌트 자동: 1-2 파일 mechanical → haiku / 다중 파일 + 통합 → sonnet / 설계 + 광범위 → opus / Korean prose 조작 → sonnet (Haiku rephrasing 위험) / 신규 테스트 작성 포함 task → 최소 sonnet (v2.9+ floor)
```

- [ ] **Step 3: Before/After 컨벤션 줄에 테스트 제외 명시**

**원본** (`skills/auto-writing-plans/SKILL.md:31`):
```
- Before/After 코드블록 (`**원본**` / `**수정 후**`) 컨벤션
```

**수정 후**:
```
- Before/After 코드블록 (`**원본**` / `**수정 후**`) 컨벤션 — 구현 코드 전용. 테스트 코드 블록은 싣지 않고 task 헤더 `**검증**:` 필드 (자연어 1~2줄, 무엇을 + 성공 기준) 로 대체 (v2.9+)
```

- [ ] **Step 4: same-file step 구조 동기**

**원본** (`skills/auto-writing-plans/SKILL.md:39`):
```
세 조건 중 하나라도 어기면 분리. multi-step task 안 step 구조: test (1회) → byte-copy Edit (N회) → test pass → self-review. 애매하면 분리 (보수적 default).
```

**수정 후**:
```
세 조건 중 하나라도 어기면 분리. multi-step task 안 step 구조: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 1회) → byte-copy Edit (N회) → test pass → self-review. 애매하면 분리 (보수적 default).
```

- [ ] **Step 5: PASS 확인**

Run:
```bash
grep -cF '**검증**' skills/auto-writing-plans/SKILL.md                           # expected: >= 2
grep -cF 'Same-file mechanical 묶음 룰 (v2.0.1+)' skills/auto-writing-plans/SKILL.md skills/writing-plans/SKILL.md  # expected: 각 1 (기존 페어 grep 유지 확인)
```

- [ ] **Step 6: self-review**

### Task 3: implementer-prompt 테스트 분리 룰 — 구현 byte-copy / 테스트 자체 작성

**Files:**
- Modify: `skills/js-super-sub-driven/implementer-prompt.md`

**Model**: haiku

**검증**: "same byte-copy rule" (테스트도 byte-copy 하라는 옛 룰) 이 0 매치가 되고, Test Authoring 분리 섹션 (구현=byte-copy 불변 / 테스트=검증 설명 기반 자체 작성 / 블록 존재 시 하위 호환 byte-copy) 이 1 매치인지 grep 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF 'Test Authoring (v2.9+' skills/js-super-sub-driven/implementer-prompt.md`
Expected: 0 매치 (exit 1)

- [ ] **Step 2: dispatch 모델 주석 갱신**

**원본** (`skills/js-super-sub-driven/implementer-prompt.md:7`):
```
  model: "haiku"   # v2.0.0+ HAIKU FIXED — byte-copy mode does not need LLM transcription. plan's `**Model**:` hint is ignored under subagent-driven-development. (See CLAUDE.md "implementer-prompt + reorder-prompt + plan_byte_check" section.)
```

**수정 후**:
```
  model: "haiku"   # v2.0.0+ 기본 haiku (순수 byte-copy task). v2.9+: 신규 테스트 작성 포함 task (`**검증**:` 필드 + Test: 경로 + 테스트 코드 블록 없음) 는 plan 의 `**Model**:` 값 (최소 sonnet) 으로 dispatch. (See CLAUDE.md "plan 테스트 자연어 축약 결합" + "implementer-prompt + reorder-prompt + plan_byte_check" sections.)
```

- [ ] **Step 3: Your Job 재서술 + Test Authoring 분리 섹션 신설**

**원본** (`skills/js-super-sub-driven/implementer-prompt.md:72-80`):
```
    ## Your Job

    Once you're clear on requirements:
    1. Implement exactly what the task specifies — byte-copy the blocks
    2. Write tests (following TDD if task says to) — same byte-copy rule
    3. Verify implementation works (run tests in working tree, no commit)
    4. **DO NOT git commit** — main agent commits at wave end in plan order
    5. Self-review (see below)
    6. Report back
```

**수정 후**:
```
    ## Your Job

    Once you're clear on requirements:
    1. Write tests FIRST per the Test Authoring rule below (TDD) — run them, confirm FAIL
    2. Implement exactly what the task specifies — byte-copy the blocks
    3. Verify implementation works (run tests in working tree, no commit)
    4. **DO NOT git commit** — main agent commits at wave end in plan order
    5. Self-review (see below)
    6. Report back

    ## Test Authoring (v2.9+ split rule)

    구현 코드와 테스트 코드는 다르게 다룬다:

    - **구현 코드 = STRICT BYTE-COPY (불변)** — 위 byte-copy 룰 그대로. 약화 금지.
    - **테스트 코드 = 자연어 설명 기반 자체 작성** — task 헤더의 `**검증**:` 필드
      (무엇을 검증하는지 + 성공 기준) 를 읽고 네가 테스트 코드를 직접 작성한다.
      테스트 먼저 작성 → 실행해 FAIL 확인 → 구현 byte-copy → PASS 확인 (TDD 순서 유지).
    - **하위 호환**: task 에 테스트 코드 블록이 이미 있으면 (v2.8 이전 형식) 그 블록을
      byte-copy 한다 — 자체 작성 금지. 블록 존재 = 기존 룰 우선.
```

- [ ] **Step 4: Self-Review Testing 항목 보강**

**원본** (`skills/js-super-sub-driven/implementer-prompt.md:144-147`):
```
    **Testing:**
    - Do tests actually verify behavior (not just mock behavior)?
    - Did I follow TDD if required?
    - Are tests comprehensive?
```

**수정 후**:
```
    **Testing:**
    - Do tests actually verify behavior (not just mock behavior)?
    - Did I follow TDD if required?
    - Are tests comprehensive?
    - (v2.9+) 자체 작성한 테스트가 `**검증**:` 필드의 "무엇을 + 기준" 을 그대로 커버하는가?
    - (v2.9+) task 에 테스트 코드 블록이 있었는데 자체 작성으로 대체하지 않았는가? (블록 존재 = byte-copy 우선)
```

- [ ] **Step 5: PASS 확인**

Run:
```bash
grep -n 'same byte-copy rule' skills/js-super-sub-driven/implementer-prompt.md  # expected: 0 매치
grep -cF 'Test Authoring (v2.9+' skills/js-super-sub-driven/implementer-prompt.md  # expected: 1
grep -n 'HAIKU FIXED' skills/js-super-sub-driven/implementer-prompt.md          # expected: 0 매치
grep -cF 'STRICT BYTE-COPY (v2.0.0+)' skills/js-super-sub-driven/implementer-prompt.md  # expected: 1 (구현 byte-copy 룰 보존)
```

- [ ] **Step 6: self-review**

### Task 4: sub-driven dispatch 조건부 룰 — 11곳 일괄 개정

**Files:**
- Modify: `skills/js-super-sub-driven/SKILL.md`

**Model**: haiku

**검증**: "항상 haiku 고정" 표현이 본문에서 0 매치가 되고, 조건부 룰 (순수 byte-copy=haiku / 신규 테스트 포함=`**Model**:` 값 최소 sonnet) 이 Model Selection·W-2·룰 2 표·핵심 패턴에 일관되게 실렸는지 grep 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -n '항상 haiku 고정' skills/js-super-sub-driven/SKILL.md | wc -l`
Expected: 7 (변경 전 잔존 확인 — 0 이면 이미 반영된 것이니 BLOCKED 보고)

- [ ] **Step 2: Plan Analysis 2·3번 — Test 경로 유지 + Model 파싱 겸용**

**원본** (`skills/js-super-sub-driven/SKILL.md:83-84`):
```
2. **Parse files + deps** — 각 task block 의 `**Files:**` (Create/Modify/Test) 섹션 + step 본문에서 task ID 참조 추출 (예: "Task 1 의 helper 사용" → deps=[1]).
3. **Parse model hint (informational)** — task block 의 `**Model**:` 줄을 DAG 복잡도 표시용으로만 파싱 (implementer 는 항상 haiku 고정 — Model Selection 참조). 없으면 DAG 표시상 `sonnet` (`scripts/dag_builder.py` 의 `Task.model` 기본값 — 복잡도 힌트일 뿐, 실제 implementer dispatch 는 항상 haiku).
```

**수정 후**:
```
2. **Parse files + deps** — 각 task block 의 `**Files:**` (Create/Modify/Test) 섹션 + step 본문에서 task ID 참조 추출 (예: "Task 1 의 helper 사용" → deps=[1]). `Test:` 경로도 files 집합에 포함 — wave file-disjoint 판정이 테스트 파일 충돌까지 커버한다 (v2.9+ 계획서에 테스트 코드 블록이 없어도 `Test:` 경로 줄을 유지하는 이유).
3. **Parse model hint** — task block 의 `**Model**:` 줄 파싱. DAG 복잡도 표시 + v2.9+ 조건부 dispatch 판정에 사용 (신규 테스트 작성 포함 task 는 이 값으로 dispatch, 최소 sonnet — Model Selection 참조). 없으면 DAG 표시상 `sonnet` (`scripts/dag_builder.py` 의 `Task.model` 기본값).
```

- [ ] **Step 3: Model Selection 본문 조건부 룰로 재작성**

**원본** (`skills/js-super-sub-driven/SKILL.md:112`):
```
**Implementer 서브에이전트는 항상 `haiku` 고정** (v2.0.0 byte-copy — 구현은 plan 의 `**수정 후**` 블록을 기계적으로 byte-copy 하는 작업이라 추론 모델이 불필요). plan 의 `**Model**:` 필드는 v1.1.14(byte-copy 이전)의 잔재로 **implementer dispatch 모델을 바꾸지 않는다** — DAG 표시용 복잡도 힌트로만 파싱한다. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch (아래 W-2 Stage 1/2/3 참조).
```

**수정 후**:
```
**Implementer dispatch 모델은 조건부 (v2.9+)** — 순수 byte-copy task (`**원본**`/`**수정 후**` 블록만, 신규 테스트 작성 없음) 는 **`haiku` 고정** (v2.0.0 byte-copy — 기계적 복사라 추론 모델 불필요). **신규 테스트 작성 포함 task** (`**검증**:` 필드 + `Files:` 의 `Test:` 경로 존재 + 테스트 코드 블록 없음) 는 plan 의 `**Model**:` 값 (**최소 sonnet floor**) 으로 dispatch — 자연어 검증 설명만으로 테스트 코드를 작성해야 하기 때문. 하위 호환: task 에 테스트 코드 블록이 있으면 (v2.8 이전 형식) 기존 룰 (전체 byte-copy + haiku) 우선. 구현 코드의 STRICT BYTE-COPY 는 dispatch 모델과 무관하게 적용. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch (아래 W-2 Stage 1/2/3 참조).
```

- [ ] **Step 4: Model 힌트 참고 문구 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:116`):
```
참고 — plan 의 `**Model**:` 힌트가 나타내는 task 복잡도 (dispatch 모델은 바꾸지 않음):
```

**수정 후**:
```
참고 — plan 의 `**Model**:` 값이 나타내는 task 복잡도 (신규 테스트 포함 task 는 dispatch 모델로도 사용, v2.9+):
```

- [ ] **Step 5: dispatch 예시 주석 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:127`):
```
  model: "haiku"   # implementer 는 항상 haiku 고정 (byte-copy)
```

**수정 후**:
```
  model: "haiku"   # 순수 byte-copy task 는 haiku / 신규 테스트 포함 task 는 plan **Model**: 값 (최소 sonnet) — v2.9+
```

- [ ] **Step 6: W-2 pair-parallel 서술 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:153`):
```
- Implementer (`./implementer-prompt.md`, `model: "haiku"` 고정 — byte-copy)
```

**수정 후**:
```
- Implementer (`./implementer-prompt.md`, 순수 byte-copy task 는 `model: "haiku"` / 신규 테스트 포함 task 는 plan `**Model**:` 값 (최소 sonnet) — v2.9+)
```

- [ ] **Step 7: W-2 Stage 1 서술 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:162-163`):
```
1. **Stage 1 — Implementer** (haiku, byte-copy)
   Dispatch via `./implementer-prompt.md` (model="haiku" fixed).
```

**수정 후**:
```
1. **Stage 1 — Implementer** (조건부 모델, byte-copy + 테스트 자체 작성)
   Dispatch via `./implementer-prompt.md` (순수 byte-copy=haiku / 신규 테스트 포함=plan `**Model**:` 값, 최소 sonnet — v2.9+).
```

- [ ] **Step 8: Stage 분기 마무리 문단 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:178-180`):
```
Stage 1 BLOCKED → Stage 2 dispatch is automatic (no user gate). Stage 2
NEEDS_USER → main agent gate. Plan's `**Model**:` hint is IGNORED for
Stage 1 (haiku fixed); spec reviewer remains sonnet (D11/D-T2 PRD).
```

**수정 후**:
```
Stage 1 BLOCKED → Stage 2 dispatch is automatic (no user gate). Stage 2
NEEDS_USER → main agent gate. Plan's `**Model**:` value drives Stage 1 dispatch
ONLY for tasks that author new tests (v2.9+, min sonnet floor); pure byte-copy
tasks stay haiku. Spec reviewer remains sonnet (D11/D-T2 PRD).
```

- [ ] **Step 9: 예시 시나리오 주석 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:349-350`):
```
  - Implementer task 1 (model: haiku)
  - Implementer task 2 (model: haiku)]   # implementer 는 항상 haiku 고정
```

**수정 후**:
```
  - Implementer task 1 (model: haiku)
  - Implementer task 2 (model: haiku)]   # 두 task 모두 순수 byte-copy → haiku (신규 테스트 포함 task 면 plan **Model**: 값 — v2.9+)
```

- [ ] **Step 10: 핵심 패턴 1번 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:395`):
```
1. dispatch 는 항상 **명시 모델 주입** (implementer=haiku 고정, spec-reviewer=sonnet 고정) — 부모 모델 상속 회피
```

**수정 후**:
```
1. dispatch 는 항상 **명시 모델 주입** (implementer=조건부: 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan **Model**: 값 (최소 sonnet), spec-reviewer=sonnet 고정) — 부모 모델 상속 회피
```

- [ ] **Step 11: 룰 2 표 dispatch row 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:481`):
```
| implementer dispatch model | 항상 haiku 고정 (byte-copy) — plan 의 `**Model**:` 필드로 바뀌지 않음 |
```

**수정 후**:
```
| implementer dispatch model | v2.9+ 조건부 자동 판정 — 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan `**Model**:` 값 (최소 sonnet). 게이트 없이 자동 |
```

- [ ] **Step 12: Anti-Pattern row 갱신**

**원본** (`skills/js-super-sub-driven/SKILL.md:523`):
```
| implementer model 변경 시 게이트 | 룰 2 위반. implementer 는 haiku 고정 (byte-copy). |
```

**수정 후**:
```
| implementer model 변경 시 게이트 | 룰 2 위반. v2.9+ 조건부 룰 (순수 byte-copy=haiku / 신규 테스트 포함=plan **Model**: 값) 로 자동 판정. |
```

- [ ] **Step 13: PASS 확인**

Run:
```bash
grep -n '항상 haiku 고정' skills/js-super-sub-driven/SKILL.md   # expected: 0 매치
grep -cF '최소 sonnet' skills/js-super-sub-driven/SKILL.md      # expected: >= 5
grep -cF 'Stage 1/2/3' skills/js-super-sub-driven/SKILL.md      # expected: >= 1 (W-2 분기 보존)
```

- [ ] **Step 14: self-review**

### Task 5: executing-plans 테스트 소스 분기 — inline 모드 절차

**Files:**
- Modify: `skills/executing-plans/SKILL.md`

**Model**: haiku

**검증**: "테스트 소스 분기 (v2.9+" 섹션 1 매치 (새 형식=검증 필드 기반 작성 / 기존 형식=블록 사용 / 혼재 plan task 단위 분기), 룰 2 표와 Anti-Pattern 의 옛 "haiku 고정" 표현 0 매치.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF '테스트 소스 분기 (v2.9+' skills/executing-plans/SKILL.md`
Expected: 0 매치 (exit 1)

- [ ] **Step 2: 테스트 소스 분기 섹션 신설**

**원본** (`skills/executing-plans/SKILL.md:162-164`):
```
<HARD-GATE>
Triviality is determined ONLY by the three criteria above. Logic changes — even one-line ones — are NOT trivial. When in doubt, take the safe path.
</HARD-GATE>
```

**수정 후**:
```
<HARD-GATE>
Triviality is determined ONLY by the three criteria above. Logic changes — even one-line ones — are NOT trivial. When in doubt, take the safe path.
</HARD-GATE>

## 테스트 소스 분기 (v2.9+ — 계획서 테스트 자연어 축약)

task 의 "실패 테스트 작성" step 에서 테스트 코드의 소스는 task 형식에 따라 갈린다:

- **새 형식** (task 헤더에 `**검증**:` 필드, 테스트 코드 블록 없음) — `**검증**:` 의 자연어 설명 (무엇을 + 성공 기준) 을 읽고 실행 단계가 테스트 코드를 직접 작성한다. TDD 순서 (작성 → FAIL 확인 → 구현 → PASS) 는 그대로.
- **기존 형식** (task 에 테스트 코드 블록 존재) — 블록의 코드를 그대로 사용한다 (하위 호환. 블록 존재 = 기존 룰 우선).

두 형식이 한 plan 에 섞여 있어도 task 단위로 분기한다.
```

- [ ] **Step 3: 룰 2 표 dispatch row 갱신**

**원본** (`skills/executing-plans/SKILL.md:320`):
```
| dispatch model 선택 | (subagent 모드) implementer 는 haiku 고정 (byte-copy) — plan 의 `**Model**:` 필드로 바뀌지 않음 |
```

**수정 후**:
```
| dispatch model 선택 | (subagent 모드) v2.9+ 조건부 자동 판정 — 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan 의 `**Model**:` 값 (최소 sonnet). 게이트 없이 자동 |
```

- [ ] **Step 4: Anti-Pattern row 갱신**

**원본** (`skills/executing-plans/SKILL.md:372`):
```
| dispatch model 변경 시 게이트 | 룰 2 위반. (subagent 모드) implementer 는 haiku 고정 (byte-copy). |
```

**수정 후**:
```
| dispatch model 변경 시 게이트 | 룰 2 위반. (subagent 모드) v2.9+ 조건부 룰 (순수 byte-copy=haiku / 신규 테스트 포함=plan **Model**: 값) 로 자동 판정. |
```

- [ ] **Step 5: PASS 확인**

Run:
```bash
grep -cF '테스트 소스 분기 (v2.9+' skills/executing-plans/SKILL.md   # expected: 1
grep -n 'haiku 고정 (byte-copy) — plan' skills/executing-plans/SKILL.md  # expected: 0 매치
```

- [ ] **Step 6: self-review**

### Task 6: PROMPT_KO mirror 동기

**Files:**
- Modify: `PROMPT_KO.md`

**Model**: haiku

**검증**: 한국어 mirror 의 작업 구조 템플릿에서 테스트 코드 블록이 사라지고 `**검증**:` 필드가 실렸는지, placeholder 금지 목록이 새 룰로 반전됐는지 grep 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF '**검증**' PROMPT_KO.md`
Expected: 0 매치 (exit 1)

- [ ] **Step 2: placeholder 금지 목록 반전**

**원본** (`PROMPT_KO.md:324`):
```
- "위 항목에 테스트 작성" (실제 테스트 코드 없이)
```

**수정 후**:
```
- 동어반복 "검증" 필드 ("테스트를 작성한다" 처럼 무엇을/기준 없는 설명 — v2.9+)
- 테스트 코드 블록을 계획서에 싣는 것 (v2.9+ — `**검증**:` 자연어 설명으로 대체)
```

- [ ] **Step 3: 작업 구조 템플릿 재작성 (byte-copy 면제 — 펜스 포함)**

Edit 도구로 old_string = 아래 블록 A 전문 (PROMPT_KO.md L294-318), new_string = 아래 블록 B 전문. verbatim 사용.

블록 A (기존 본문):

`````
````markdown
### Task N: [컴포넌트 이름]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: 테스트 실행해 실패 검증**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: 최소 구현**
- [ ] **Step 4: 통과 검증**
- [ ] **Step 5: 커밋**
````
`````

블록 B (새 본문):

`````
````markdown
### Task N: [컴포넌트 이름]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**검증**: [이 task 의 테스트가 무엇을 검증하는지 + 성공 기준 — 자연어 1~2줄. 테스트 코드는 싣지 않음 (v2.9+)]

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계가 검증 설명 기반으로 코드 작성)**

Run: `pytest tests/path/test.py -v`
Expected: FAIL (구현 전)

- [ ] **Step 2: 최소 구현**
- [ ] **Step 3: 통과 검증**
- [ ] **Step 4: 커밋**
````
`````

- [ ] **Step 4: PASS 확인**

Run:
```bash
grep -cF '**검증**' PROMPT_KO.md                          # expected: >= 2
grep -n '위 항목에 테스트 작성' PROMPT_KO.md               # expected: 0 매치
```

- [ ] **Step 5: self-review**

### Task 7: CLAUDE.md 결합 메모 — v2.0.0 갱신 + 신규 섹션

**Files:**
- Modify: `CLAUDE.md`

**Model**: haiku

**검증**: v2.0.0 결합 메모의 implementer-prompt 항목이 테스트 분리 룰을 반영하고, 신규 결합 섹션 "plan 테스트 자연어 축약 결합 (v2.9+)" (8 파일 atomic + 회귀 패턴 + 회귀 catch grep) 이 1 매치인지 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `grep -cF 'plan 테스트 자연어 축약 결합 (v2.9+)' CLAUDE.md`
Expected: 0 매치 (exit 1)

- [ ] **Step 2: v2.0.0 결합 메모 항목 1 갱신**

**원본** (`CLAUDE.md:216`):
```
1. `skills/js-super-sub-driven/implementer-prompt.md` — STRICT BYTE-COPY 룰 + haiku 고정 + Status enum BLOCKED
```

**수정 후**:
```
1. `skills/js-super-sub-driven/implementer-prompt.md` — STRICT BYTE-COPY 룰 (구현 코드) + 테스트 자연어 자체 작성 분리 (v2.9+) + 조건부 dispatch 모델 + Status enum BLOCKED
```

- [ ] **Step 3: 신규 결합 섹션 추가 (v2.0.1 섹션 뒤에 삽입)**

**원본** (`CLAUDE.md:259-261`):
```
`skills/js-super-sub-driven/tests/H12-same-file-merge/README.md` — 같은 파일 4 mechanical 변경 plan → 1 task multi-step 묶음 검증 (positive + negative).

요약: 2 skill + fixture + CLAUDE.md 변경은 묶어서 처리.
```

**수정 후**:

````
`skills/js-super-sub-driven/tests/H12-same-file-merge/README.md` — 같은 파일 4 mechanical 변경 plan → 1 task multi-step 묶음 검증 (positive + negative).

요약: 2 skill + fixture + CLAUDE.md 변경은 묶어서 처리.

## plan 테스트 자연어 축약 결합 (v2.9+)

구현계획서에서 테스트 코드 블록을 없애고 task 헤더 `**검증**:` 필드 (자연어 1~2줄 — 무엇을 + 성공 기준) 로 대체. 실제 테스트 작성·실행은 실행 단계가 TDD 순서 그대로 수행. 하위 호환 — task 에 테스트 코드 블록이 있으면 기존 룰 (byte-copy) 우선, task 단위 분기. spec: `docs/features/2026-08-09-plan-test-자연어축약/`.

### 적용 8 영역 (atomic)

1. `skills/writing-plans/SKILL.md` — 검증 필드 스키마 + 템플릿 + placeholder 룰 반전 + Model sonnet floor
2. `skills/auto-writing-plans/SKILL.md` — mirror 3곳 동기 (페어 atomic)
3. `skills/js-super-sub-driven/implementer-prompt.md` — 구현=byte-copy / 테스트=자체 작성 분리 + 하위 호환 분기
4. `skills/js-super-sub-driven/SKILL.md` — 조건부 dispatch (신규 테스트 포함 task = `**Model**:` 값, 최소 sonnet / 순수 byte-copy = haiku)
5. `skills/executing-plans/SKILL.md` — 테스트 소스 분기 섹션 + 룰 2 dispatch row
6. `PROMPT_KO.md` — writing-plans 한국어 mirror
7. `CLAUDE.md` — v2.0.0 결합 메모 갱신 + 본 섹션
8. fixtures — H12 갱신 + H14 신규 + G5/G6 기대값 갱신

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| implementer-prompt 하위 호환 분기 누락 | 기존 계획서 (테스트 코드 블록) 실행 시 자체 작성으로 drift |
| sub-driven dispatch 조건부 룰 한쪽만 변경 | plan Model 값과 실제 dispatch 모델 불일치 (v1.1.14 결합 회귀) |
| writing-plans 만 변경 (auto 미동기) | auto-flow plan 에 테스트 코드 블록 잔존 |
| 템플릿에서 `Test:` 경로 제거 | wave 병렬 테스트 파일 충돌 감지 손실 |
| 구현 코드 byte-copy 룰 약화 | v2.0.0 drift 회귀 — 절대 금지 |

### 회귀 catch grep

```bash
grep -cF '계획서에는 테스트 코드를 싣지 않는다' skills/writing-plans/SKILL.md
# expected: 1
grep -n 'without actual test code' skills/writing-plans/SKILL.md
# expected: 0
grep -n 'same byte-copy rule' skills/js-super-sub-driven/implementer-prompt.md
# expected: 0 (테스트 byte-copy 룰 제거)
grep -cF 'Test Authoring (v2.9+' skills/js-super-sub-driven/implementer-prompt.md
# expected: 1
grep -n '항상 haiku 고정' skills/js-super-sub-driven/SKILL.md
# expected: 0 (조건부 룰로 대체)
grep -cF '테스트 소스 분기 (v2.9+' skills/executing-plans/SKILL.md
# expected: 1
grep -cF '**검증**' skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md PROMPT_KO.md
# expected: 각 >= 2
```

### 영향 범위

- plan 작성 (writing-plans / auto-writing-plans) + 실행 (executing-plans / js-super-sub-driven) 만.
- og-* / code-pretty / plan_byte_check / verifying-spec / test-driven-development 영향 0 — 테스트 블록은 원래 라벨이 없어 검사 대상 밖.
- 6 manifest bump — dev 직접 (에이전트 임의 bump 금지).
````

- [ ] **Step 4: PASS 확인**

Run:
```bash
grep -cF 'plan 테스트 자연어 축약 결합 (v2.9+)' CLAUDE.md   # expected: >= 1
grep -cF '테스트 자연어 자체 작성 분리 (v2.9+)' CLAUDE.md    # expected: 1
```

- [ ] **Step 5: self-review**

### Task 8: fixture 갱신 — H12 동기 + G5/G6 기대값 + H14 신규

**Files:**
- Modify: `skills/js-super-sub-driven/tests/H12-same-file-merge/README.md`
- Modify: `skills/js-super-sub-driven/tests/G5-model-haiku/README.md`
- Modify: `skills/js-super-sub-driven/tests/G6-no-model-default/README.md`
- Create: `skills/js-super-sub-driven/tests/H14-natural-lang-verify/README.md`

**Model**: haiku

**검증**: H12 의 step 1 기대값이 새 표현으로 바뀌고, G5/G6 기대값이 v2.9+ 조건부 dispatch 룰을 반영하며, H14 신규 fixture (새 형식 / 기존 형식 / 혼재 3 시나리오) 가 존재하는지 판정.

- [ ] **Step 1: 변경 전 FAIL 확인**

Run: `test -f skills/js-super-sub-driven/tests/H14-natural-lang-verify/README.md && echo EXISTS || echo MISSING`
Expected: MISSING (변경 전)

- [ ] **Step 2: H12 step 1 기대값 동기**

**원본** (`skills/js-super-sub-driven/tests/H12-same-file-merge/README.md:26`):
```
  - step 1: 통합 UI preview test 작성
```

**수정 후**:
```
  - step 1: 검증 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, v2.9+)
```

- [ ] **Step 3: G5 기대값 갱신**

**원본** (`skills/js-super-sub-driven/tests/G5-model-haiku/README.md:5`):
```
**Expected:** 메인이 implementer dispatch 시 `model: "haiku"` 로 호출. spec-reviewer 는 sonnet.
```

**수정 후**:
```
**Expected:** task 1 은 신규 테스트 작성 없음 (`**검증**:` 필드/`Test:` 경로 기반 판정) → 메인이 implementer dispatch 시 `model: "haiku"` 로 호출 (v2.9+ 조건부 룰의 순수 byte-copy 분기). spec-reviewer 는 sonnet.
```

- [ ] **Step 4: G6 기대값 갱신**

**원본** (`skills/js-super-sub-driven/tests/G6-no-model-default/README.md:5`):
```
**Expected:** 메인이 implementer dispatch 시 `model: "sonnet"` (디폴트) + 한 줄 dispatch log: "Task 1 model: sonnet (default)".
```

**수정 후**:
```
**Expected:** DAG 표시 default 는 sonnet 유지. dispatch 는 v2.9+ 조건부 룰 — 신규 테스트 작성 포함 task 면 sonnet (floor), 아니면 haiku. 한 줄 dispatch log 로 판정 근거 표기 (예: "Task 1 model: haiku (순수 byte-copy)").
```

- [ ] **Step 5: H14 신규 fixture 작성**

**수정 후** (new file: `skills/js-super-sub-driven/tests/H14-natural-lang-verify/README.md`):
```
# H14 — 계획서 테스트 자연어 축약 (v2.9+)

**검증 필드 기반 실행 분기 + dispatch 모델 판정 dogfood**

## 시나리오 A (새 형식)

plan 의 task 에 테스트 코드 블록 없음 + 헤더에 `**검증**: 잔액 0 미만 출금 시 예외 발생 + 잔액 불변` + `Files: Test: tests/test_wallet.py` + `**Model**: sonnet`.

**기대:**
- implementer dispatch 모델 = plan `**Model**:` 값 (최소 sonnet) — 신규 테스트 작성 포함 판정
- implementer 가 검증 설명 기반 테스트 코드 자체 작성 → FAIL 확인 → 구현 byte-copy → PASS
- 구현 코드 블록은 STRICT BYTE-COPY 유지

## 시나리오 B (기존 형식 — 하위 호환)

plan 의 task 에 테스트 코드 블록 존재 (v2.8 이전 형식).

**기대:**
- 블록 존재 = 기존 룰 우선 — 테스트도 byte-copy, 자체 작성 금지
- implementer dispatch 모델 = haiku (byte-copy)

## 시나리오 C (혼재 plan)

task 1 은 새 형식, task 2 는 기존 형식.

**기대:** task 단위 분기 — 한 plan 안에서 두 룰이 task 별로 독립 적용.

## 연결 위험

- 하위 호환 분기 누락 → 시나리오 B 에서 자체 작성 drift (implementer-prompt "Test Authoring (v2.9+ split rule)" 가 catch)
- `Test:` 경로 제거 → wave 충돌 감지 손실 (writing-plans 템플릿의 Test: 경로 유지 룰이 catch)
```

- [ ] **Step 6: PASS 확인**

Run:
```bash
test -f skills/js-super-sub-driven/tests/H14-natural-lang-verify/README.md && echo OK   # expected: OK
grep -n '통합 UI preview test 작성' skills/js-super-sub-driven/tests/H12-same-file-merge/README.md  # expected: 0 매치
grep -cF 'v2.9+' skills/js-super-sub-driven/tests/G5-model-haiku/README.md skills/js-super-sub-driven/tests/G6-no-model-default/README.md  # expected: 각 1
```

- [ ] **Step 7: self-review**

### Task 9: 회귀 grep 일괄 검증 (코드 변경 없음 — 검증 전용)

**Files:**
- (없음 — 검증 전용)

**Model**: haiku

**검증**: T1~T8 의 결과물 전체에 대해 CLAUDE.md 신규 섹션의 회귀 catch grep 스위트가 전부 기대값과 일치하고, 범위 밖 파일 (og-* / plan_byte_check.py / code-pretty / test-driven-development) 이 미변경인지 판정.

deps: Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8

- [ ] **Step 1: 회귀 grep 스위트 일괄 실행**

Run:
```bash
grep -cF '계획서에는 테스트 코드를 싣지 않는다' skills/writing-plans/SKILL.md          # expected: 1
grep -n 'without actual test code' skills/writing-plans/SKILL.md                      # expected: 0 매치
grep -n '항상 haiku' skills/writing-plans/SKILL.md                                     # expected: 0 매치
grep -n 'same byte-copy rule' skills/js-super-sub-driven/implementer-prompt.md        # expected: 0 매치
grep -cF 'Test Authoring (v2.9+' skills/js-super-sub-driven/implementer-prompt.md     # expected: 1
grep -n '항상 haiku 고정' skills/js-super-sub-driven/SKILL.md                          # expected: 0 매치
grep -cF '테스트 소스 분기 (v2.9+' skills/executing-plans/SKILL.md                     # expected: 1
grep -cF '**검증**' skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md PROMPT_KO.md  # expected: 각 >= 2
grep -cF 'plan 테스트 자연어 축약 결합 (v2.9+)' CLAUDE.md                              # expected: >= 1
grep -cF 'Same-file mechanical 묶음 룰 (v2.0.1+)' skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md  # expected: 각 1
grep -cF 'STRICT BYTE-COPY' skills/js-super-sub-driven/implementer-prompt.md          # expected: >= 2 (구현 byte-copy 룰 보존)
```

- [ ] **Step 2: 범위 밖 파일 미변경 확인**

Run: `git status --porcelain scripts/plan_byte_check.py skills/code-pretty/ skills/test-driven-development/ skills/js-super-sub-driven/reorder-prompt.md commands/og-brainstorm.md commands/og-write-plan.md commands/og-execute-plan.md`
Expected: 출력 없음 (미변경)

- [ ] **Step 3: 검증 결과 보고**

전체 PASS 시 [검증] entry 대상으로 결과 기록 (end-of-run consolidator 가 처리). FAIL 항목 발견 시 해당 task 로 되돌아가 수정.

## 2. 위험 코드 지점

- `skills/js-super-sub-driven/implementer-prompt.md:76` — breaking: 테스트 byte-copy 룰 제거 시 하위 호환 분기가 없으면 기존 형식 plan 실행이 drift (mitigation: T3 Test Authoring 섹션의 "블록 존재 = byte-copy 우선" 분기 + H14 시나리오 B)
- `skills/js-super-sub-driven/SKILL.md:112` — side-effect: dispatch 룰 개정이 W-2 Stage/reorder 서술과 얽혀 있어 과수정 시 BLOCKED→reorder 경로 훼손 (mitigation: T4 를 11개 byte-copy 페어로 고정 — 자율 rewriting 금지, Step 13 grep 으로 Stage 1/2/3 보존 확인)
- `skills/writing-plans/SKILL.md:182-223` — breaking: 템플릿 재작성 시 `**Model**:` 줄 / `Test:` 경로 누락하면 sub-driven Plan Analysis 파싱 + wave 충돌 감지 깨짐 (mitigation: 블록 B 에 두 줄 보존 + T1 Step 11 grep)
- `skills/writing-plans/SKILL.md:336-338` — side-effect: placeholder 룰 반전 누락 시 새 형식 plan 이 Self-Review 에서 false-fail (mitigation: T1 Step 9 페어 교체 + 동어반복 금지 신설)
- `skills/writing-plans/SKILL.md` ↔ `skills/auto-writing-plans/SKILL.md` — side-effect: 페어 한쪽만 수정 시 auto-flow 회귀 (mitigation: T1+T2 같은 wave + T9 페어 grep)
- `skills/executing-plans/SKILL.md:320` — breaking: inline 모드 룰 2 표가 옛 "haiku 고정" 을 유지하면 sub-driven 과 dispatch 서술 모순 (mitigation: T5 Step 3/4 페어 + T9 grep)

## 3. 롤백 전략

- Code: task 별 commit 을 역순 revert (`git log --oneline` 에서 `task N:` 프리픽스로 식별, `git revert <SHA>`)
- 문서 (skill 본문 / CLAUDE.md / fixture): 코드와 동일 — revert 로 원복. gitignored 산출물 없음
- feature flag 없음 (문서 룰 변경) — 커밋 revert 로 충분. 6 manifest 는 본 계획이 건드리지 않으므로 롤백 대상 아님

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-09 21:38] [구현계획서-수정]
- **id**: CH-20260809-003
- **이유**: 신규 피처 writing-plans (auto-flow) — tech-design D1~D5 를 9 task / 2 wave 로 분해
- **무엇이**: plan-test-자연어축약-implementation-plan.md 전체 (T1~T9, byte-copy 페어 33 + 면제 2, §2 위험 6 entry, §3 롤백)
- **영향범위**: verifying-spec 4축 통과 (gap 0, conflict 0), plan_byte_check 1회차 전부 통과. 본 계획서 자체가 새 형식 dogfood (**검증** 필드, 테스트 코드 블록 없음)
- **연관 항목**: CH-20260809-001, CH-20260809-002

### [2026-08-09 21:55] [코드-수정] (batch: tasks 1..8)
- **id**: CH-20260809-004
- **이유**: 구현계획서 테스트 자연어 축약 (v2.9+) — 계획서에서 테스트 코드 블록 제거, `**검증**:` 필드 도입, 실행 단계 TDD 유지 + 하위 호환 분기, 조건부 dispatch 모델
- **무엇이**: skills/writing-plans/SKILL.md, skills/auto-writing-plans/SKILL.md, skills/js-super-sub-driven/implementer-prompt.md, skills/js-super-sub-driven/SKILL.md, skills/executing-plans/SKILL.md, PROMPT_KO.md, CLAUDE.md, tests fixture 4건 (H12/G5/G6 갱신 + H14 신규)
- **영향범위**: plan 작성 층 + 실행 층 + dispatch 층. og-* / plan_byte_check / code-pretty / verifying-spec / test-driven-development 영향 없음 (Task 9 grep 확인)
- **위험 카테고리**: breaking (implementer-prompt 하위 호환 분기, executing-plans 룰 표), side-effect (sub-driven dispatch 11곳)
- **task별 세부 (8건)**:
  - Task 1: `skills/writing-plans/SKILL.md:65-362` — 검증 필드 스키마/템플릿/placeholder/Model floor (`none`) — commits: `35dbbf9`
  - Task 2: `skills/auto-writing-plans/SKILL.md:30-39` — mirror 3곳 동기 (`none`) — commits: `5d85df2`
  - Task 3: `skills/js-super-sub-driven/implementer-prompt.md:7-160` — 구현 byte-copy / 테스트 자체 작성 분리 + 하위 호환 (`breaking`) — commits: `0692f71`
  - Task 4: `skills/js-super-sub-driven/SKILL.md:83-523` — 조건부 dispatch 11곳 (`side-effect`) — commits: `2fdaa98`
  - Task 5: `skills/executing-plans/SKILL.md:165-381` — 테스트 소스 분기 (`breaking`) — commits: `669595a`
  - Task 6: `PROMPT_KO.md:294-325` — 한국어 mirror 동기 (`none`) — commits: `684fc2b`
  - Task 7: `CLAUDE.md:216-315` — 결합 메모 v2.0.0 갱신 + v2.9+ 신규 섹션 (`none`) — commits: `6037421`
  - Task 8: `skills/js-super-sub-driven/tests/*` — fixture 3 갱신 + H14 신규 (`none`) — commits: `341956b`
- **연관 commits**: 35dbbf9..341956b (task 8건) + 사전 분리 커밋 29cca77 (본 세션 이전 CLAUDE.md 변경)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260809-003

### [2026-08-09 21:55] [검증] (task: Task 9 — 회귀 grep 일괄 검증)
- **id**: CH-20260809-005
- **이유**: v2.9+ 회귀 catch grep 스위트 통과 확인 + 범위 밖 파일 미변경 검증
- **무엇이**: 회귀 grep 11개 (Task 9 Step 1 스위트) + og-* / plan_byte_check.py / code-pretty / test-driven-development / reorder-prompt 미변경 확인 + 메인 독립 spot-check 3건
- **결과**: PASS — grep 11개 전부 기대값 일치, 범위 밖 파일 변경 없음
- **연관 항목**: CH-20260809-004
