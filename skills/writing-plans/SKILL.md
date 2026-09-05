---
name: writing-plans
description: Use when <slug>-requirements.md and <slug>-tech-design.md exist for a feature, before touching code. Reads both, produces <slug>-implementation-plan.md (단계별 plan with bite-sized TDD tasks). Ends with the main agent's spec verification gate (verifying-spec) — covers 요구사항 + 개발방향 ↔ 구현계획서 consistency + code impact.
user-invocable: false
---

# Writing Plans → <slug>-implementation-plan.md

## 사용자 질문 룰 (v2.0.3+) — 항상 AskUserQuestion

이 skill 흐름 안에서 사용자에게 질문할 일이 생기면 **반드시** `AskUserQuestion`
도구로 호출한다. 산문으로 "~ 할까요?" 한 줄 던지지 마라.

### Why

Notification 훅 (`elicitation_dialog` 매처) 이 알람을 발화하려면 도구 호출이
실제로 일어나야 함. 산문 질문은 훅이 못 잡아서 사용자가 놓침 (v1.1.8 신고 재발).

### How to apply

- clarifying / Socratic / 모호점 확인 / 게이트 / 모드 선택 — 모두 포함
- 단답 yes/no 도 prose X → `AskUserQuestion` options `[yes, no]` 사용
- 다중 선택은 enum options 또는 multi-question batching (의미 결합 시 max 4 questions[])
- **Socratic 자유 응답**: AskUserQuestion 의 question 본문에 "자유롭게 답해주세요. 별도 옵션 선택 불필요" + dummy option `[알겠음]` 1개 → 트리거만 발화, 응답은 다음 turn prose
- **예외**: 본문 자체의 알람-friendly 안내문 (`ℹ️ Auto-proceeding ...`) 는 질문 아니라 안내 — 도구 호출 불필요

### Other / 모호 응답 처리 (v2.1.1+)

사용자가 "Other" 자유 응답 또는 "모르겠음 / 이해 안 됨" 류 답변 catch 시 → **그 질문만 단독 재호출 + prose 설명 추가**. 다음 단계 자동 진행 X (anchor 질문 강제 X 룰은 명확 yes/no 답변에만 적용).

Take <slug>-requirements.md + <slug>-tech-design.md as inputs and produce a comprehensive implementation plan (`<slug>-implementation-plan.md`) decomposed into bite-sized tasks. The upstream superpowers patterns (exact file paths, complete code in every step, 테스트 → 구현 순서, no placeholders, frequent commits) are inherited as-is. js-superpowers extends them with: change-history footer, structured "위험 코드 지점" section, and a verification gate after save.

<HARD-GATE>
Both <slug>-requirements.md and <slug>-tech-design.md must exist in the current feature folder. If either is missing, instruct the user to run /brainstorm or /design-tech first.
</HARD-GATE>

### 2-doc → 3-doc 승격 (산출물 깊이 선택)

`<slug>-tech-design.md` frontmatter 가 `depth: 2` (2-doc 확정 트랙) 인 피처에서 본 skill 이 명시 실행되면 승격으로 간주한다:

1. `ℹ️ 2개 확정 트랙 피처입니다. /write-plan 실행으로 3개 트랙으로 승격합니다.` 한 줄 안내 (질문 아님 — 사용자가 명시 실행했으므로 재확인 게이트 없음)
2. frontmatter 를 `depth: 3` 으로 갱신 + `depth_reason` 을 승격 사유로 교체
3. `change-history` 로 tech-design 에 [개발방향-수정] entry (이유: 2-doc → 3-doc 승격) 기록
4. 이후 본 skill 의 기존 흐름 그대로 진행

### 예외 — `--no-ask` 플래그 (v2.5+)

사용자가 슬래시 명령에 `--no-ask` 토큰을 **명시** 한 경우에만 진입. 메인 자체 판단으로 활성화 X.

- 모든 사용자 질문을 prose (메인 turn 자유 텍스트) 로 처리
- `AskUserQuestion` 도구 호출 **0 보장**
- 게이트 자체는 살아 있음 — 사용자 prose 응답 기다림
- 알람 fire X (사용자가 명시 invoke 했으니 인지 가정)

#### skill 진입 시 1회 boilerplate

skill 진입 직후 다음 한 줄을 prose 로 출력:

> ℹ️ `--no-ask` 모드 진입 — AskUserQuestion 도구 호출 X, 응답 알람 X. 백그라운드 작업 중이면 응답 시점을 직접 체크해주세요.

#### 위험 명령 진입 직전 보강

critical 7 케이스 (파일 삭제 / `git push --force` / DB migration / mass commit / 외부 메시지 등) 실행 직전에는 다음 한 줄을 prose 로 출력:

> ⚠️ 위험 명령 진입 — 응답 기다림. 백그라운드 작업 중이면 직접 catch 해주세요.

`⚠️` 마커 + 별도 줄로 일반 prose 보다 두드러지게.

## Checklist

You MUST create a TaskCreate task for each of these items and complete them in order:

1. **입력 확인** — confirm both <slug>-requirements.md and <slug>-tech-design.md exist (HARD-GATE if either missing)
2. **파일 구조 윤곽 잡기** — which files are created/modified, with single-responsibility boundaries
3. **구현계획서 task 목록 작성** — each task = 검증 한 단위 (계획서에는 `**검증**:` 자연어 설명만, 실행 단계에서 test → fail → impl → pass → commit)
4. **위험 코드 지점 (§2) 채우기** — every risk category from <slug>-tech-design.md §6 mapped to a concrete location + mitigation
5. **자체 점검** — spec coverage / placeholder scan / type consistency / 위험 coverage
5.5. **문서 구조 확정 + 코드 강제 검사** — task 수를 세고, 10개 이상이면 인덱스 + `plan/` 하위 문서로 나눈다 (Plan Split 섹션). 그런 다음 `plan_guard` 검사를 돌려 코드 블록 부재 / 축약 마커 / 구조 위반을 확인한다. 위반이 하나라도 있으면 계획서는 저장되지 않는다.
6. **코드 정리** — dispatch `code-pretty` (Sonnet subagent, prettifies `**수정 후**` blocks). It runs BEFORE verifying-spec and stops once the first change-history entry is logged.
7. **사양 정합성 검증** — main agent runs A+C verification on the prettified plan via `verifying-spec` (Tolerance for missing skill)
8. **사용자 검토 (구현계획서)** — show the plan (code-pretty applied) + verifying-spec report + code-pretty diff summary; get approval (loop until OK; on changes → revise → back to step 6 코드 정리)
9. **변경이력 기록** — append first `[구현계획서-수정]` entry via `change-history` skill
10. **구현 단계 핸드오프** — count tasks first, then offer the choice using the Execution Handoff message below (`executing-plans` or `js-super-sub-driven`). Upstream `subagent-driven-development` is NOT offered here; only invoke it if the user explicitly asks for the upstream original.

If you find yourself skipping ahead, stop and create the missing task.

**Before invoking the next skill via Skill tool, mark ALL checklist TaskCreate items as completed (in_progress → completed). The Skill tool transition does NOT auto-complete prior tasks. (v1.1.15+, FR-2)**

## Inputs

- `docs/features/<date>-<slug>/<slug>-requirements.md`
- `docs/features/<date>-<slug>/<slug>-tech-design.md`

## Output

- `docs/features/<date>-<slug>/<slug>-implementation-plan.md` — 정본 산출물

계획서를 처음 읽는 사람을 위한 용어집이 필요하면 이 흐름과 별개로 `/glossary` 를 직접 부릅니다. 자동으로 만들어지지 않습니다.

## Schema (<slug>-implementation-plan.md)

```markdown
---
commit_policy: per-task
---

# 구현계획서: <feature-name>

## 1. 단계별 작업
   ### Task 1: <Component>
   **Files:** Create/Modify/Test
   **검증**: <무엇을 검증하는지 + 성공 기준 (자연어 1~2줄)>
   - [ ] Step 1: <action>
   - [ ] Step 2: <action>
   ...
## 2. 위험 코드 지점
   - <file:line>: <category> | <mitigation>
## 3. 롤백 전략

---
## 변경이력
```

### Frontmatter — `commit_policy` field

This field tells `/execute-plan` how to commit work between tasks. It is the **single source of truth** for commit policy; do NOT scatter "no commits" or "single commit" instructions in prose.

| Value | Meaning | executing-plans mode |
|---|---|---|
| `per-task` (**default**) | code-only commit per task; plan log 는 end-of-run `[log] all tasks` 커밋 1회 | git-fast (if git repo present) |
| `single` | All tasks accumulated into ONE commit at the very end of `/execute-plan` | memory-fallback |
| `none` | No commits during `/execute-plan` (user commits manually after) | memory-fallback |

If the field is omitted, `/execute-plan` assumes `per-task`.

If the user explicitly requests `single` or `none` during planning, set the field accordingly and warn them once: "이 모드에서는 변경이력의 변경 전 코드를 in-memory로 보관해야 해서 토큰 비용이 큽니다. 가능하면 per-task를 권장합니다."

## Task Granularity

Task 하나는 `**검증**:` 한두 줄로 덮이는 단위다. 시간 상한이나 단언 개수 상한은 두지 않는다 — 그 보폭 제한은 사람의 작업 기억을 위한 장치였고, 실행 주체가 에이전트인 지금은 근거가 없다. Each task has four steps:
- "`**검증**:` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인 (테스트 코드는 실행 단계가 작성)" — step
- "구현 코드 작성 (계획서의 수정 후 블록 그대로)" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step (skip if git is not initialized)

**계획서에는 테스트 코드를 싣지 않는다 (v2.9+)** — task 헤더의 `**검증**:` 필드 (자연어 1~2줄) 가 "무엇을 검증하는지 + 어떤 기준으로 성공인지" 를 정의하고, 실제 테스트 코드 작성·실행은 실행 단계 (executing-plans / js-super-sub-driven) 가 담당한다. TDD 순서 (테스트 먼저 → 구현) 는 실행 단계에서 그대로 유지된다.

## Same-file mechanical 묶음 룰 (v2.0.1+)

둘 이상의 logical change 가 다음 **세 조건 모두** 만족하면 1 task 의 multi-step 으로 묶는다:

1. **같은 파일** — Files 목록 동일 (Modify 대상 path 동일)
2. **테스트 경계 없음** — 한 통합 test 또는 UI preview 로 같이 검증 가능
3. **mechanical** — 다음 패턴에 해당. 알고리즘 변경 X.
   - modifier / annotation 추가 (예: `Modifier.padding(...)`)
   - handler 등록 (예: `BackHandler { ... }`, click listener)
   - container 옵션 (예: `Scaffold(contentWindowInsets = ...)`)
   - placeholder text / static UI element 추가
   - import / using 추가

세 조건 중 하나라도 어기면 분리. 묶을 때 task 안 step 구조:

- step 1: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 한 번)
- step 2~N: 각 변경의 byte-copy Edit (`**원본**` / `**수정 후**` 페어)
- step N+1: test 실행 → pass 확인
- step N+2: self-review

(애매하면 분리 — false negative 회복 비용 < false positive)

**multi-step task 의 byte-copy 정합성 (v2.0.0 D3 가정)**: 각 step 의 `**원본**` 블록은 직전 step 적용 후 파일 상태 기준이지만, mechanical 변경은 대부분 file 의 다른 위치 (independent insertions) 라 자연 byte-equal. 가정 깨지면 implementer Stage 1 BLOCKED → Stage 2 reorder dispatch 가 처리.

## Plan Document Header (REQUIRED)

Every implementation plan MUST start with:

```markdown
# <Feature Name> 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** <one sentence>

**Architecture:** <2-3 sentences from <slug>-tech-design.md §1>

**Tech Stack:** <key technologies>

**Spec inputs:**
- <slug>-requirements.md — <key FRs touched>
- <slug>-tech-design.md — <key decisions/architecture>

---
```

## Plan Split — 인덱스 + 하위 문서

task 가 **10개 이상**이면 계획서를 나눈다. 미만이면 단일 문서 그대로다. 미만이어도 코드량이 많다고 판단되면 나눠도 된다 — 재량은 나누는 방향으로만 열려 있다.

```
docs/features/<date>-<slug>/
├── <slug>-implementation-plan.md     ← 인덱스 (이름 그대로)
└── plan/
    ├── tasks-01-03.md
    ├── tasks-04-06.md
    └── tasks-07.md
```

하위 문서 이름은 `plan/tasks-NN.md` 또는 `plan/tasks-NN-MM.md` (2자리, 연속 범위). task 번호는 문서를 가로질러 1부터 이어지는 전역 연번이고, 연관된 task 가 인접 번호가 되도록 정렬한다. **하위 문서 하나에 task 는 최대 3개**까지다.

인덱스의 task 블록은 헤더 필드만 남긴다 — `**상세**` 링크 / `**Files:**` / `**Model**` / `**검증**`. step 목록과 코드 블록은 하위 문서에 둔다. 실행 단계가 인덱스만 읽고 DAG 를 짤 수 있어야 하기 때문이다.

```markdown
### Task 4: 결제 검증 helper

**상세**: plan/tasks-04-06.md
**Files:**
- Modify: `src/pay/verify.py:40-88`
- Test: `tests/pay/test_verify.py`
**Model**: sonnet
**검증**: <자연어 1~2줄>
```

하위 문서는 인덱스와 같은 헤더 필드 + step 목록 + 코드 블록을 담는다. **변경이력 footer 는 두지 않는다** — 계획서의 변경이력은 인덱스 한 곳으로 모은다.

## Task Structure (inherited)

````markdown
### Task N: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Model**: sonnet

**검증**: <이 task 의 테스트가 무엇을 검증하는지 + 성공 기준 — 자연어 1~2줄. 테스트 코드는 싣지 않는다 (v2.9+)>

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계 (executing-plans / js-super-sub-driven) 가 테스트 코드를 직접 작성한다. 계획서에는 코드를 싣지 않는다.

Run: `pytest tests/path/test.py -v`
Expected: FAIL (구현 전)

- [ ] **Step 2: 구현 코드 작성**

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

## Task Model Hint (v1.1.14+ · v2.9+ dispatch 결합 복원)

Each task block MAY include `**Model**: sonnet | opus`. 이보다 낮은 모델 값은 쓰지 않는다 (sonnet 하한). 이 필드는 `js-super-sub-driven` 의 implementer dispatch 모델로 직접 쓰인다 — 필드 생략 시 sonnet 기본값. Spec-reviewer is always sonnet. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch.

값 산정 기준:

| 신호 | Model 값 |
|---|---|
| 1-2 파일 + mechanical implementation + 명확 spec | sonnet |
| 다중 파일 통합 / 디버깅 / 패턴 매칭 | sonnet |
| Korean prose 조작 (skill 본문 / MD 편집) | sonnet |
| 신규 테스트 작성 포함 (`**검증**:` + `Test:` 경로) | sonnet (하한) |
| 설계 / 광범위 코드베이스 이해 | opus |
| 누락 / 모호 | sonnet |

Backward compat: 필드 생략 시 sonnet. 금지된 옛 하위 모델 값이 남은 기존 계획서는 실행 층이 sonnet 으로 격상해 dispatch 한다 (`js-super-sub-driven` Model Selection 참조 — 계획서 수정을 요구하지 않는다). 테스트 코드 블록이 있는 기존 계획서 (v2.8 이전) 는 테스트 포함 전체 byte-copy 룰 그대로 (모델은 sonnet 하한).

Note: 구현 코드 블록의 STRICT BYTE-COPY 룰은 dispatch 모델과 무관하게 적용된다 (sonnet implementer 도 구현 코드는 byte-copy). 한국어 prose 를 만지는 task 는 byte-copy 정확성 (`**원본**`/`**수정 후**` 페어) 에 특히 의존하며, byte-copy 로 감당 안 되면 BLOCKED → reorder(sonnet) 로 처리된다.

## Code Block Convention (Before/After labels) — required for tasks that modify existing code

When a task changes existing code (Modify), use the **Before/After label pair**:

````markdown
**원본** (`<file>:<line-range>`):
```<lang>
<original code, byte-equal to current source>
```

**수정 후**:
```<lang>
<new code>
```
````

Rules:

1. The "원본" label MUST start with exactly `**원본**` (markdown bold). The `(file:line-range)` annotation is **REQUIRED for Modify tasks** (v2.0.1+) so that `plan_byte_check` helper can verify the block byte-equal against the actual file at that range. Without a line range, the helper falls back to whole-file compare which fails for partial-file edits.
2. The "수정 후" label MUST start with exactly `**수정 후**` (markdown bold).
3. For tasks that CREATE a new file, the "원본" block is OMITTED — only "수정 후" block is shown (with `(new file: <path>)` annotation).
4. Both blocks MUST use the same fenced-code language identifier.
5. The `code-pretty` skill targets ONLY "수정 후" blocks. "원본" blocks are byte-immutable.
6. **테스트 파일 내용은 코드 블록으로 싣지 않는다 (v2.9+)** — 신규 테스트든 기존 테스트 수정이든 계획서에는 task 헤더의 `**검증**:` 자연어 설명으로만 적는다. Before/After 페어는 구현 코드 전용이다.

This convention is required so that:
- Reviewers can compare before/after at a glance.
- The `code-pretty` skill can identify which blocks to prettify (수정 후) and which to leave untouched (원본).

Anti-pattern: showing only the modified code without the original. Reviewers cannot tell what changed.

## Process Flow

```dot
digraph plan_flow {
    "Read <slug>-requirements.md + <slug>-tech-design.md" [shape=box];
    "File structure outline" [shape=box];
    "Decompose into bite-sized tasks" [shape=box];
    "Self-review (internal)" [shape=box];
    "Split if 10+ tasks\n+ plan_guard code check" [shape=box];
    "Dispatch code-pretty" [shape=box];
    "Run verifying-spec\n(on the prettified plan)" [shape=box];
    "Single combined approval gate\n(plan + verify + code-pretty diff)" [shape=diamond];
    "Invoke change-history" [shape=box];
    "Hand off to /execute-plan" [shape=doublecircle];

    "Read <slug>-requirements.md + <slug>-tech-design.md" -> "File structure outline";
    "File structure outline" -> "Decompose into bite-sized tasks";
    "Decompose into bite-sized tasks" -> "Self-review (internal)";
    "Self-review (internal)" -> "Split if 10+ tasks\n+ plan_guard code check";
    "Split if 10+ tasks\n+ plan_guard code check" -> "Dispatch code-pretty";
    "Dispatch code-pretty" -> "Run verifying-spec\n(on the prettified plan)";
    "Run verifying-spec\n(on the prettified plan)" -> "Single combined approval gate\n(plan + verify + code-pretty diff)";
    "Single combined approval gate\n(plan + verify + code-pretty diff)" -> "Self-review (internal)" [label="no — re-prettify + re-verify"];
    "Single combined approval gate\n(plan + verify + code-pretty diff)" -> "Invoke change-history" [label="approve"];
    "Invoke change-history" -> "Hand off to /execute-plan";
}
```

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- Smaller, focused files beat large files that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. Don't restructure unless an unwieldy file actively blocks the work.

## §2 위험 코드 지점

After tasks are written, fill `## 2. 위험 코드 지점` with concrete entries:

```markdown
## 2. 위험 코드 지점

- `src/wallet/service.py:42-58` — side-effect: 잔액이 -로 갈 수 있음 (mitigation: amount 검증 + 트랜잭션)
- `src/api/wallet_routes.py:withdraw` — breaking: 응답 스키마에 transaction_id 추가 (mitigation: 클라이언트 호환성 확인)
```

Categories MUST come from risk-annotation taxonomy: `side-effect | breaking | race`. Each entry pairs a location with a mitigation strategy.

## §3 롤백 전략

```markdown
## 3. 롤백 전략

- Code: revert commits SHA-A..SHA-B (or stash + reset)
- DB: migration <name> has down(), run `alembic downgrade -1`
- Config: feature flag `wallet.withdraw.v2` defaults off
```

## No Placeholders (inherited)

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- 동어반복 `**검증**:` 필드 — "테스트를 작성한다" 처럼 무엇을/어떤 기준인지 없는 설명 (v2.9+ 테스트 코드 블록 대신 쓰는 필드라 구체성이 생명)
- 테스트 코드 블록을 계획서에 싣는 것 (v2.9+ — `**검증**:` 자연어 설명으로 대체. 기존 계획서의 테스트 코드 블록은 하위 호환으로 실행만 지원)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how
- References to types, functions, or methods not defined in any task

## Remember

- **Exact file paths always** — `src/wallet/service.py:42-58`, never "the wallet service"
- **Complete code in every step** — if a step changes code, show the code in a code block
- **Exact commands with expected output** — never "run the tests" without the command + expected outcome
- **DRY, YAGNI, 테스트 → 구현 순서, frequent commits** — these aren't slogans, they're rules

## Self-Review

After writing the complete plan, look at it with fresh eyes:

1. **Spec coverage**: Skim each 요구 항목 and key decision in <slug>-requirements.md and <slug>-tech-design.md. Can you point to a task that implements it? List any gaps. (요구 항목 번호는 현행 `**요구 N**:`, 옛 문서는 `FR-N` — 둘 다 같은 항목으로 센다.)
2. **Placeholder scan**: Search for any of the patterns from "No Placeholders" above. Fix them.
3. **Type consistency**: Function names, signatures, and property names must match across tasks (e.g., `clearLayers()` in Task 3 vs `clearFullLayers()` in Task 7 is a bug).
4. **위험 코드 지점 coverage**: Every category in <slug>-tech-design.md §6 has at least one corresponding entry in §2.
5. **same-file 묶음 룰 위반 검사**: task 들 중 같은 파일만 만지는 chain 이 2건 이상 있는지 확인. 있으면 D1 의 3 조건 (같은 파일 / test 경계 X / mechanical) 재검토 → 묶을지 결정. (v2.0.1+)
6. **검증 필드 구체성 (v2.9+)**: 코드 변경 task 마다 `**검증**:` 필드가 있고 "무엇을 + 어떤 기준" 을 담았는지 확인. 동어반복 ("테스트 작성" 한 줄) 이나 테스트 코드 블록이 남아 있으면 수정.
7. **구현 코드 존재 확인**: 파일을 만들거나 고치는 task 마다 코드 블록이 실제로 있는지 확인. 자연어 설명만 남은 task, 코드 블록 안의 생략 표현 (`... 생략`, `기존 코드 유지`, `이하 동일`) 은 그 자리에서 실제 코드로 채운다. 계획서가 길어질수록 이 항목이 무너지기 쉬우니 task 를 하나씩 짚어가며 본다.
8. **문서 구조 확인**: task 가 10개 이상이면 인덱스 + `plan/` 하위 문서로 나뉘어 있는지, 하위 문서마다 task 가 3개 이하인지, 인덱스 링크와 실제 파일이 맞는지 확인.

If you find issues, fix them inline. If you find a spec requirement with no task, add the task.

### plan_guard + plan_byte_check helper

After all tasks are written and self-review checks pass, run the guard. It
covers code presence (G1), elision markers (G2), split structure (G3~G5),
and byte-equality across the whole document set (G6):

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_guard import check_plan, verify_documents_byte_equal
index = Path('docs/features/<date>-<slug>/<slug>-implementation-plan.md')
violations = check_plan(index)
mismatches = verify_documents_byte_equal(index, Path('.'))
for v in violations:
    print(f'{v.code} — {v.human_reason}')
    print(f'  문서: {v.doc_path}')
for m in mismatches:
    print(f'G6 — {m.reason}')
    print(f'  파일: {m.file_path}')
if violations or mismatches:
    sys.exit(1)
print('plan_guard ✅ 코드 블록 / 구조 / byte-equal 모두 통과')
sys.exit(0)
" 2>&1
```

If exit 1:
- The violation list is shown to the user.
- **Plan is NOT saved.** Fix and re-run:
  - G1 — the task changes files but carries no code. Write the actual
    `**원본**` / `**수정 후**` blocks. A natural-language description is
    not a substitute, no matter how long the plan already is.
  - G2 — a code block contains an elision marker. Replace it with the real code.
  - G3~G5 — split the plan (10+ tasks), keep sub-documents to 3 tasks, fix
    broken links / duplicate task numbers / field mismatches.
  - G6 — the `**원본**` block is not byte-identical to the current file.
- This enforces the byte-copy implementer's precondition (fail-fast, no LLM
  fuzzy match fallback) AND the code-presence rule that the fuzzy path used
  to let through.

## Anti-Patterns

| Wrong | Right |
|---|---|
| Steps that say "implement X" without code | Show the actual code in a code block. |
| TODO / TBD / "later" markers | Forbidden. Resolve before saving. |
| Task 하나를 `**검증**:` 한두 줄로 못 덮음 | Decompose further. 검증 한 단위 = task 하나. |
| Skipping §2 위험 코드 지점 | Required. Every risk category from <slug>-tech-design.md §6 must appear here. |

## Red Flags

| Thought | Reality |
|---|---|
| "The engineer can figure out the details" | They can't, and shouldn't have to. Spell it out. |
| "Skip `**검증**:` for trivial tasks" | 검증이 없으면 실행 단계가 테스트를 못 쓴다. 한 줄이라도 적는다. |
| "Plan is too long" | Length is fine if every step is concrete. Vague brevity is worse. |

## After Save — single approval gate, then execution-mode choice

This summarizes the corrected order (matches Checklist + Process Flow above):

1. **Dispatch code-pretty FIRST** (before verifying-spec, before any user prompt):
   - `code-pretty` → Target: `<slug>-implementation-plan.md` (only `**수정 후**`-labeled blocks). Output: diff summary text (preserved for the approval gate).
   - **분할한 경우 (`plan/` 하위 문서)**: 코드 블록은 인덱스가 아니라 하위 문서에 있다. `**수정 후**` 블록을 가진 문서마다 `code-pretty` 를 하나씩, **같은 메시지에 실어 병렬로** 호출한다 (각 호출은 자기 대상 파일 하나만 만진다). 인덱스만 대상으로 잡으면 하위 문서의 코드가 한 번도 정리되지 않는다.
   - **Why this order**: verifying-spec then runs against the code blocks the user will actually read, and it doubles as a safety net for anything code-pretty disturbed. Running verify first meant re-verifying nothing after the prettify pass.
   - **Tolerance**: if `code-pretty` is not installed, skip it and emit "ℹ️ code-pretty 가 설치되지 않았습니다. 코드 블록은 그대로 표시됩니다."
   - **용어집은 여기서 만들지 않습니다.** 사용자가 원할 때 `/glossary` 커맨드로 직접 부릅니다.

2. **Run verifying-spec** (after every dispatched `code-pretty` returns):
   - Target: `<slug>-implementation-plan.md` (post-prettify state)
   - Upstream: `[<slug>-requirements.md, <slug>-tech-design.md]`
   - Procedure: consistency (요구 항목 + key decisions covered as tasks) + code impact (files/functions referenced exist or are explicitly created)
   - **Tolerance**: if verifying-spec skill is not installed, skip and emit the notice ("ℹ️ verify-gate 가 설치되지 않았습니다. Phase 2 이후 활성화되며, 지금은 검증 없이 진행합니다.")

3. **Single combined approval gate** — present in ONE message:
   - The full `<slug>-implementation-plan.md` (code-pretty applied to code blocks) (or summary if very long, with link)
   - The verify-spec 4-axis report
   - The code-pretty diff summary
   - **Gate #13 — plan + verify 결합 승인**

     **Tool form (preferred)**

     Call `AskUserQuestion`:

     ```json
     {
       "question": "<slug>-implementation-plan.md (+ verify-spec 보고서) 승인하고 진행? (plan + 4축 보고서 한 메시지로 노출)",
       "header": "구현계획서 승인",
       "multiSelect": false,
       "options": [
         {"label": "예 — 승인", "description": "승인하고 change-history + 실행 모드 선택"},
         {"label": "아니오 — 수정", "description": "사용자 피드백 받아 수정 후 재제시"}
       ]
     }
     ```

     **Prose fallback**

     > Approve `<slug>-implementation-plan.md` and proceed? — `yes` / `no`
   - DO NOT split into "approve plan" → "approve verify report". One gate, one decision.
   - On `no` → 피드백 받아 수정 후 재제시. anchor 질문 강제 X.

4. On `yes` → invoke change-history (`[구현계획서-수정]` entry) → continue to Execution Handoff below.
   On `no` → 피드백 받아 수정 후 재제시. anchor 질문 강제 X.

## Execution Handoff

After verification passes and the entry is logged, count plan tasks and offer execution choice:

**Gate #14 — 실행 모드 선택**

**Tool form (preferred)**

Call `AskUserQuestion`:

```json
{
  "question": "Plan에 <N>개 task. 어느 실행 방식?",
  "header": "실행 방식",
  "multiSelect": false,
  "options": [
    {"label": "인라인", "description": "메인 에이전트가 executing-plans 로 직접 실행 (≤12 task 권장)"},
    {"label": "서브에이전트", "description": "implementer + spec reviewer 디스패치 (13+ task 권장)"}
  ]
}
```

**Prose fallback**

> "Plan complete and saved to `docs/features/<date>-<slug>/<slug>-implementation-plan.md`. Two execution options:
>
> 1. **Inline** (recommended for medium plans, ≤ 12 tasks) — main agent edits directly via `executing-plans`; fast, fewer total tokens; main context accumulates with task count
> 2. **Subagent** (recommended for large plans, 13+ tasks) — implementer + spec reviewer subagents via `js-super-sub-driven`; preserves main context; adds dispatch cost
>
> Plan has <N> tasks. Which approach?"

If Inline chosen → REQUIRED SUB-SKILL: `executing-plans`
If Subagent chosen → REQUIRED SUB-SKILL: `js-super-sub-driven`

The upstream `subagent-driven-development` is NOT offered in this handoff. Invoke it only when the user explicitly requests the upstream original.

## Related Skills

- `brainstorming` — upstream input (<slug>-requirements.md)
- `tech-design` — upstream input (<slug>-tech-design.md)
- `code-pretty` — prettifies `수정 후` blocks; dispatched before verifying-spec
- `verifying-spec` — verification gate (active from Phase 2), runs on the prettified plan
- `change-history` — entry recording on save
- `executing-plans` / `js-super-sub-driven` — downstream execution (js-super-sub-driven 이 권장 subagent 모드; upstream `subagent-driven-development` 는 사용자가 명시 요청할 때만)
- `risk-annotation` — taxonomy used in §2 위험 코드 지점

## 승인 게이트 / multi-choice 결정 = AskUserQuestion 도구 (v2.3.6+)

산출물 (요구사항 / tech-design / impl-plan) 작성 완료 후 사용자에게 **승인 / 수정 / 다른 방향** 류 multi-choice 결정을 요청할 때 → **반드시 `AskUserQuestion` 도구로 호출**. prose 자연어 멀티 옵션 금지.

### Why

- `Notification.elicitation_dialog` 매처 fire → OS 알람 (사용자 백그라운드 작업 시 catch)
- prose multi-choice 는 알람 X → 응답 멈춤
- "Other" / 자유 응답 / multiSelect / preview 등 도구 기능 활용

### 적용 케이스

- 산출물 ("이대로 진행 / 수정 필요 / 다른 방향") 게이트
- alternatives 2-3 안 사용자 선택
- partial 수정 후 재승인

기존 v2.0.3+ Socratic clarifying Q boilerplate + v2.1.1+ Other / 모호 응답 처리 룰 보존 (변경 X). 본 룰은 그 위에 multi-choice 결정 게이트 시점 명시 보강. CLAUDE.md "AskUserQuestion 도구 우선 (v2.3.5+)" 글로벌 룰의 요구사항 흐름 측 boilerplate.

### Anti-Patterns

| 안티 패턴 | 이유 |
|---|---|
| "승인 / 수정 / 다른 방향 — 어느 쪽이신지 알려주십시오." prose | AskUserQuestion options 사용. |
| 마크다운 numbered list (`1. ... 2. ... 3. ...`) 로 선택 유도 | AskUserQuestion options 사용. |
| "Y/N?" / "yes/no?" 한 글자 응답 유도 prose | AskUserQuestion (yes/no) 사용. |
| "어느 쪽?" / "어떤 안?" prose 멀티 옵션 | AskUserQuestion options 사용. |
| 산출물 작성 후 prose "검토 부탁" 만 던지고 응답 대기 | multi-choice 있으면 도구. 단순 보고는 OK. |
