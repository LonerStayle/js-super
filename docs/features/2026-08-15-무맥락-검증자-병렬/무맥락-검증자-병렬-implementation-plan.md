---
commit_policy: per-task
---

# 무맥락 검증자 병렬 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** `verifying-spec` 이 메인 자체 검증과 동시에 맥락 없는 보조 에이전트 둘을 병렬로 띄우고, 결과를 메인이 중재해 하나의 보고서로 낸다.

**Architecture:** dispatch 와 중재 절차가 전부 `skills/verifying-spec/` 안에 갇힌다 (커맨드 4개의 플래그 안내, `CLAUDE.md` 결합 메모, fixture 는 별개로 추가된다). 호출 지점 4곳(`tech-design` / `writing-plans` / `auto-tech-design` / `auto-writing-plans`)은 `verifying-spec` 을 이름으로만 부르므로 본문 변경 0. 검증자는 단독(대상 문서 경로만)과 대조(대상 + 상위 문서 경로) 둘로 나뉘며, 단독 쪽에 상위 문서 경로를 주지 않는 것으로 읽기 순서를 물리적으로 보장한다.

**Tech Stack:** Markdown 스킬 본문 + 프롬프트 템플릿. 실행 코드 없음. 검증은 grep 기반 정적 확인 + fixture 시나리오.

**Spec inputs:**
- 무맥락-검증자-병렬-requirements.md — FR-1(병렬 실행) / FR-2(주입 경계) / FR-3(2단계 순서) / FR-4(판정 축) / FR-5(통합·중재) / FR-6(게이팅) / FR-7(모델) / FR-8(HARD-GATE 예외)
- 무맥락-검증자-병렬-tech-design.md — D1(두 에이전트 분리) / D2(`verifying-spec` 본문 집중) / D3(슬래시 원문 인식 플래그) / D5(실패 시 명시 후 진행) / D6(4축 보존 + 섹션 추가) / D7(모델 미지정 상속)

---

## 1. 단계별 작업

### Task 1: 단독 검증자 프롬프트

**Files:**
- Create: `skills/verifying-spec/clean-solo-prompt.md`

**Model**: sonnet

**검증**: 파일이 생성되고, 상위 문서 경로 플레이스홀더(`<UPSTREAM_PATHS>`)가 0건이며, 읽기 전용 지시와 판정 축 6종(ambiguity / undecided / contradiction / unverifiable / unbuildable / dead-weight)이 모두 본문에 있으면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계가 확인 명령을 직접 구성한다. 계획서에는 명령을 싣지 않는다.

Expected: 파일 부재 — FAIL

- [ ] **Step 2: 파일 작성**

**수정 후** (`skills/verifying-spec/clean-solo-prompt.md` 전체):

````markdown
# Clean Solo Verifier Prompt Template

Use this template when dispatching the **solo** clean-context verifier from `verifying-spec`.

**Purpose:** Read the target document COLD — no upstream spec, no conversation history, no author narrative — and report what is wrong with the document *on its own terms*. This catches the failure class that requirement-matching cannot: a document that satisfies every upstream item and is still unbuildable.

**Injection rule (HARD):** substitute ONLY `<TARGET_PATH>`. Never add upstream paths, the author's reasoning, the conversation, or the doc's `## 변경이력` footer. The urge to "give it a little context" is exactly the bug this verifier exists to catch.

```
Agent tool (general-purpose):
  run_in_background: true
  # NO model argument — inherit the session model (D7)
  description: "Clean solo verify <target basename>"
  prompt: |
    You are reviewing a technical document you have never seen before.

    You have NO context about this project, this feature, or why this
    document was written. That is deliberate. Do not ask for context, and
    do not charitably reconstruct what the author probably meant.

    ## The document

    <TARGET_PATH>

    Read it with the Read tool. This is the ONLY file you may read.

    ## Your job

    Judge the document on its own terms. Someone is handed this file and
    told "build this." Can they?

    Report anything that would stop them.

    **Ambiguity** — a sentence readable two ways, where the two readings
    produce different implementations.

    **Undecided** — a decision the document defers or leaves implicit
    while later sections assume it was made.

    **Internal contradiction** — one section assumes the opposite of
    another. Quote both.

    **Unverifiable** — a success criterion nobody could check. "Works
    well", "is fast", "handles errors gracefully".

    **Unbuildable** — a step or component described too thinly to build,
    with no pointer to where the detail lives.

    **Dead weight** — content that contradicts nothing and adds nothing.
    A section restating another. A decision with no consequence.

    ## What you must NOT do

    - Do NOT guess what the upstream requirements probably said
    - Do NOT read any other file, including siblings in the same folder
    - Do NOT run code-impact analysis (file existence checks, caller
      searches, grep across the repo) — the main agent owns that axis
    - Do NOT edit anything — you are strictly read-only
    - Do NOT soften a finding because the author "probably meant" something
    - Do NOT report style or formatting preferences

    ## Calibration

    Do not manufacture findings. An empty report is a valid result and
    beats a padded one. But do not stay quiet about something that
    genuinely blocked you while reading.

    ## Report format

    Return exactly this, nothing else:

    FINDINGS: <count>
    - [<ambiguity|undecided|contradiction|unverifiable|unbuildable|dead-weight>] <section or line reference> — <what is wrong, one or two sentences>
    - ...

    If nothing: FINDINGS: 0
```
````

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/verifying-spec/clean-solo-prompt.md
git commit -m "feat(verifying-spec): 단독 무맥락 검증자 프롬프트 추가"
```

---

### Task 2: 대조 검증자 프롬프트

**Files:**
- Create: `skills/verifying-spec/clean-cross-prompt.md`

**Model**: sonnet

**검증**: 파일이 생성되고, 상위 문서 플레이스홀더(`<UPSTREAM_PATHS>`)와 대상 플레이스홀더(`<TARGET_PATH>`)가 모두 있으며, 읽기 전용 지시와 판정 축 2종(gap / conflict)이 본문에 있고, 문서 자체 문제를 보지 말라는 배제 지시가 있으면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: 파일 부재 — FAIL

- [ ] **Step 2: 파일 작성**

**수정 후** (`skills/verifying-spec/clean-cross-prompt.md` 전체):

````markdown
# Clean Cross Verifier Prompt Template

Use this template when dispatching the **cross** clean-context verifier from `verifying-spec`.

**Purpose:** Independently re-judge the axis the main agent also judges — coverage and contradiction between the target document and its upstream documents — but from a standing start, with no knowledge of how the author read those upstream items.

**Why duplicate the main agent's axis:** the duplication IS the value. Two judgements of the same question, one by the author and one by a stranger, can be compared. A single judgement cannot.

**Injection rule (HARD):** substitute `<TARGET_PATH>` and `<UPSTREAM_PATHS>` only. Never add the conversation, the author's reasoning, the main agent's in-progress findings, or the docs' `## 변경이력` footers.

```
Agent tool (general-purpose):
  run_in_background: true
  # NO model argument — inherit the session model (D7)
  description: "Clean cross verify <target basename>"
  prompt: |
    You are checking whether a downstream document faithfully carries its
    upstream specification.

    You have NO context beyond these files. You did not write them and you
    were not present for any discussion about them. Do not reconstruct the
    author's reasoning — read what is on the page.

    ## Upstream (the source of truth)

    <UPSTREAM_PATHS>

    ## Target (the document under review)

    <TARGET_PATH>

    Read all of them with the Read tool. Read nothing else.

    ## Your job

    Two failure modes, and only these two.

    **Gap** — an upstream item (FR-N, NFR, key decision, risk, constraint,
    explicit exclusion) that appears nowhere downstream. Name the upstream
    item and say where you looked.

    **Conflict** — the target contradicts an upstream constraint. This
    includes silently re-admitting something upstream placed out of scope.
    Quote both sides.

    Walk the upstream documents item by item. Do not sample.

    ## What you must NOT do

    - Do NOT accept "this is obviously covered by" without pointing at the covering text
    - Do NOT report problems internal to the target that no upstream item speaks to — a different verifier owns that axis
    - Do NOT read files outside the list above
    - Do NOT run code-impact analysis (file existence checks, caller
      searches, grep across the repo) — the main agent owns that axis
    - Do NOT edit anything — you are strictly read-only
    - Do NOT report style or formatting preferences

    ## Calibration

    Coverage can be indirect: an upstream item may be satisfied by a
    section that never quotes its ID. Look for the substance before
    calling a gap. Conversely, a section that names an item without
    addressing it is still a gap.

    ## Report format

    Return exactly this, nothing else:

    GAPS: <count>
    - <upstream item ID / title> — <where you looked, why it is not covered>
    CONFLICTS: <count>
    - <upstream item> says <X>; <target> §<section> says <Y>

    If none: GAPS: 0 and CONFLICTS: 0
```
````

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/verifying-spec/clean-cross-prompt.md
git commit -m "feat(verifying-spec): 대조 무맥락 검증자 프롬프트 추가"
```

---

### Task 3: verifying-spec 본문 개정

같은 파일 8개 지점의 독립 삽입·치환이라 1 task multi-step 으로 묶는다 (같은 파일 / 하나의 grep 검증 경계 / 서로 겹치지 않는 앵커). R-1(HARD-GATE)과 R-2(Acceptance)는 따로 반영하면 중간 상태가 자기모순이므로 반드시 이 task 안에서 함께 처리한다.

**Files:**
- Modify: `skills/verifying-spec/SKILL.md`

**Model**: sonnet

**검증**: 개정 후 다음이 모두 참이면 성공 — HARD-GATE 에 `EXCEPTION 2` 예외 조항 존재, `Clean-Context Verifiers` 섹션 존재, `--no-clean-verify` 문자열 존재, 기존 4축 헤더(`## A. Consistency` / `## C. Code Impact`)와 Acceptance 1번 문장이 그대로 보존, Acceptance 항목이 6개로 확장, 옛 금지 문구 `NEVER dispatch a code-reviewer subagent for this skill` 이 0건.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: 위 항목 대부분 미충족 — FAIL

- [ ] **Step 2: description 갱신**

**원본** (`skills/verifying-spec/SKILL.md:3`):

```
description: Use immediately after writing <slug>-tech-design.md (via tech-design) or <slug>-implementation-plan.md (via writing-plans), before final user handoff. Performs main-agent self-verification — A) consistency cross-check between target MD and all upstream MDs, plus C) code impact analysis (file existence, callers, side-effect candidates) — and produces a structured 4-axis report for user decision.
```

**수정 후**:

```
description: Use immediately after writing <slug>-tech-design.md (via tech-design) or <slug>-implementation-plan.md (via writing-plans), before final user handoff. Performs main-agent self-verification — A) consistency cross-check between target MD and all upstream MDs, plus C) code impact analysis (file existence, callers, side-effect candidates) — while dispatching two context-free verifier subagents in parallel, then arbitrates and emits one combined report (4 axes + clean-verify + arbitration) for user decision. Skip the parallel verifiers with an explicit --no-clean-verify.
```

- [ ] **Step 3: HARD-GATE 예외 조항 추가**

**원본** (`skills/verifying-spec/SKILL.md:10-13`):

```
<HARD-GATE>
You (main agent) execute this directly. NEVER dispatch a code-reviewer subagent for this skill — the user explicitly requires main-agent verification for context preservation.
EXCEPTION: If code impact analysis requires extensive grep across many files (≥10), you MAY dispatch ONE Explore subagent for read-only impact survey, then synthesize the report yourself.
</HARD-GATE>
```

**수정 후**:

```
<HARD-GATE>
You (main agent) execute the A + C verification yourself. NEVER let a subagent REPLACE that main-agent pass — the user explicitly requires main-agent verification for context preservation. The ban targets SUBSTITUTION, not the existence of subagents.
EXCEPTION 1: If code impact analysis requires extensive grep across many files (≥10), you MAY dispatch ONE Explore subagent for read-only impact survey, then synthesize the report yourself.
EXCEPTION 2 — clean-context verifiers: You MUST ALSO dispatch two context-free verifier subagents IN PARALLEL with your own pass (see "Clean-Context Verifiers"), unless the user explicitly passed --no-clean-verify. This is an ADDITION: the main-agent A + C pass still runs in full and the main agent still writes the report. Do NOT delete this exception on the grounds that the first line forbids subagents — that reading is the regression this sentence exists to prevent.
</HARD-GATE>
```

- [ ] **Step 4: Procedure 다이어그램 노드 확장**

**원본** (`skills/verifying-spec/SKILL.md:30-37`):

```
    "Read target MD + all upstream MDs" [shape=box];
    "A. Consistency check" [shape=box];
    "C. Code impact analysis" [shape=box];
    "Compose 4-axis report" [shape=box];
    "Present to user" [shape=diamond];
    "User decision:\nproceed / no" [shape=diamond];
    "Re-enter prior skill\n(tech-design or writing-plans)" [shape=box];
    "Proceed" [shape=doublecircle];
```

**수정 후**:

```
    "Read target MD + all upstream MDs" [shape=box];
    "--no-clean-verify given?" [shape=diamond];
    "Dispatch clean verifiers\n(solo + cross, ONE message, background)" [shape=box];
    "A. Consistency check" [shape=box];
    "C. Code impact analysis" [shape=box];
    "Collect verifier results\n(confirm BOTH before composing)" [shape=box];
    "Arbitrate\n(split by nature, log dismissals)" [shape=box];
    "Compose combined report\n(4 axes + clean-verify + arbitration)" [shape=box];
    "Compose 4-axis report" [shape=box];
    "Present to user" [shape=diamond];
    "User decision:\nproceed / no" [shape=diamond];
    "Re-enter prior skill\n(tech-design or writing-plans)" [shape=box];
    "Proceed" [shape=doublecircle];
```

- [ ] **Step 5: Procedure 다이어그램 간선 확장**

**원본** (`skills/verifying-spec/SKILL.md:39-46`):

```
    "Read target MD + all upstream MDs" -> "A. Consistency check";
    "Read target MD + all upstream MDs" -> "C. Code impact analysis";
    "A. Consistency check" -> "Compose 4-axis report";
    "C. Code impact analysis" -> "Compose 4-axis report";
    "Compose 4-axis report" -> "Present to user";
    "Present to user" -> "User decision:\nproceed / no";
    "User decision:\nproceed / no" -> "Re-enter prior skill\n(tech-design or writing-plans)" [label="no"];
    "User decision:\nproceed / no" -> "Proceed" [label="proceed"];
```

**수정 후**:

```
    "Read target MD + all upstream MDs" -> "--no-clean-verify given?";
    "--no-clean-verify given?" -> "Dispatch clean verifiers\n(solo + cross, ONE message, background)" [label="no (default)"];
    "--no-clean-verify given?" -> "A. Consistency check" [label="yes — skip"];
    "Dispatch clean verifiers\n(solo + cross, ONE message, background)" -> "A. Consistency check" [label="main does NOT wait"];
    "Read target MD + all upstream MDs" -> "C. Code impact analysis";
    "A. Consistency check" -> "Collect verifier results\n(confirm BOTH before composing)" [label="verifiers dispatched"];
    "C. Code impact analysis" -> "Collect verifier results\n(confirm BOTH before composing)" [label="verifiers dispatched"];
    "A. Consistency check" -> "Compose 4-axis report" [label="skipped"];
    "C. Code impact analysis" -> "Compose 4-axis report" [label="skipped"];
    "Collect verifier results\n(confirm BOTH before composing)" -> "Arbitrate\n(split by nature, log dismissals)";
    "Arbitrate\n(split by nature, log dismissals)" -> "Compose combined report\n(4 axes + clean-verify + arbitration)";
    "Compose combined report\n(4 axes + clean-verify + arbitration)" -> "Present to user";
    "Compose 4-axis report" -> "Present to user";
    "Present to user" -> "User decision:\nproceed / no";
    "User decision:\nproceed / no" -> "Re-enter prior skill\n(tech-design or writing-plans)" [label="no"];
    "User decision:\nproceed / no" -> "Proceed" [label="proceed"];
```

- [ ] **Step 6: Clean-Context Verifiers 섹션 신설**

**원본** (`skills/verifying-spec/SKILL.md:50`):

```
## A. Consistency Check
```

**수정 후**:

```
## Clean-Context Verifiers (무맥락 검증자 병렬)

메인의 A + C 검증과 **동시에** 맥락 없는 보조 에이전트 둘을 백그라운드로 띄운다. 메인은 이들을 기다리지 않고 자기 검증을 계속한다.

### 왜 둘인가

| 검증자 | 받는 것 | 보는 것 |
|---|---|---|
| **단독 (solo)** | 대상 MD 경로 **하나만** | 문서 자체의 문제 — 모호 / 미결정 / 내부 모순 / 검증 불가능한 서술 / 이 문서만으로 구현 불가한 지점 |
| **대조 (cross)** | 대상 MD + 모든 upstream MD 경로 | 상위 대비 누락 / 모순 (메인 A축의 독립 재판정) |

단독 검증자에게 upstream 경로를 **주지 않는 것**이 이 설계의 핵심이다. 프롬프트로 "먼저 대상 문서만 읽어라" 라고 지시하면 지켰는지 확인할 방법이 없다 — 지시 위반이 결과물에 흔적을 남기지 않는다. 경로가 없으면 그 위반이 애초에 성립하지 않는다.

대조 검증자가 메인 A축과 겹치는 것은 의도된 중복이다. 같은 질문에 대한 두 판정(작성자의 판정과 낯선 이의 판정)이 있어야 대조가 가능하다.

### Dispatch 규칙

- **두 `Agent` 호출을 한 메시지에 묶는다.** 순차 dispatch 는 대기 시간이 합산되어 병렬 설계가 무의미해진다
- `run_in_background: true`
- **`model` 인자를 넘기지 않는다.** 메인 세션 모델을 상속한다. 고정 모델 상수를 두지 않는 이유는 판정이 갈렸을 때 모델 등급 차이를 변명으로 쓸 수 없게 하기 위함이다
- 프롬프트 템플릿: `./clean-solo-prompt.md` / `./clean-cross-prompt.md`
- **주입 금지** — 대화 이력 / 메인의 중간 검증 결과 / 각 결정의 배경 서술 / 대상 문서의 `## 변경이력` footer. 전달하는 것은 파일 경로뿐이다
- dispatch 직후 사용자에게 한 줄 안내를 출력한다: `ℹ️ 무맥락 검증자 2개를 백그라운드로 띄웠습니다. 끄려면 --no-clean-verify 를 붙여주세요.`

### `--no-clean-verify` 플래그

사용자가 이번 슬래시 호출(`/tech-design`, `/write-plan`, `/auto-tech-design`, `/auto-write-plan`)에 `--no-clean-verify` 토큰을 **명시**한 경우에만 건너뛴다. 메인 자체 판단으로 끄지 않는다.

변경 규모나 복잡도를 보고 알아서 켜고 끄는 조건부 게이팅은 도입하지 않는다 — 판정이 틀리면 건너뛴 사실이 사용자에게 보이지 않는다.

플래그가 있으면 dispatch 를 생략하고 기존 4축 보고서만 낸다. 보고서의 무맥락 검증 섹션에는 건너뛴 사실을 한 줄로 남긴다.

### 결과 수합과 중재

메인 A + C 검증이 끝나면 두 검증자 결과를 수합한다. **보고서 작성 전에 두 검증자의 상태를 각각 확인한다** — 한쪽만 받은 상태로 보고서를 내지 않는다.

실패했거나 응답이 오지 않은 검증자는 **보고서에 실패로 표기하고 진행한다**. 조용히 건너뛰면 사용자가 "무맥락 검증까지 돌았다" 고 오인한다. 반대로 검증자 실패로 흐름 전체를 막는 것도 과잉이다.

지적의 **성격에 따라** 처리를 나눈다.

| 지적 성격 | 처리 |
|---|---|
| 상위 문서 대비 누락 / 모순 | 문서 수정 사유. `## 권장` 에 수정 권고로 올린다 |
| 상위 문서와 무관한 문서 자체 문제 | 수정 사유 아님. 무맥락 검증 섹션에 남기고 진행한다 |

메인이 무맥락 검증자의 지적을 기각하면 **기각 사유를 보고서에 남긴다**. 조용히 버리면 무맥락 검증자를 돌린 의미가 사라진다.

판정이 엇갈릴 때마다 사용자에게 묻지 않는다. 사용자가 이 흐름에 진입한 시점부터 진행은 위임된 것으로 보고, 메인이 판정해 보고서에 반영한다.

## A. Consistency Check
```

- [ ] **Step 7: Report Format 확장**

**원본** (`skills/verifying-spec/SKILL.md:93-103`):

```
## C. Code Impact
- Impacted files: <list> (<count>)
- Callers: <function> referenced in <count> places (<list>)
- Risk candidates: <category-counts> (e.g., side-effect: 2, breaking: 1)
- Test coverage: <existing test files / coverage gaps>

## 권장 (recommendation)
- <gap or conflict> → suggest <action>
- <risk candidate> → suggest <mitigation or §6 augmentation>

진행 / 수정 중 선택해주세요.
```

**수정 후**:

```
## C. Code Impact
- Impacted files: <list> (<count>)
- Callers: <function> referenced in <count> places (<list>)
- Risk candidates: <category-counts> (e.g., side-effect: 2, breaking: 1)
- Test coverage: <existing test files / coverage gaps>

## 무맥락 검증 (clean-context)
- 단독 검증자: <완료 | 실패 — 사유> / 지적 <count>건
   - [<category>] <section> — <내용>
- 대조 검증자: <완료 | 실패 — 사유> / 누락 <count>건, 모순 <count>건
   - <upstream item> — <내용>
(건너뛴 경우 이 섹션은 한 줄: `--no-clean-verify 로 건너뜀`)

## 중재 (arbitration)
- 채택: <지적> → `## 권장` 으로 올림
- 기각: <지적> → <기각 사유>
- 기록만: <지적> → 상위 문서와 무관, 수정 사유 아님

## 권장 (recommendation)
- <gap or conflict> → suggest <action>
- <risk candidate> → suggest <mitigation or §6 augmentation>

진행 / 수정 중 선택해주세요.
```

- [ ] **Step 8: Anti-Patterns 확장**

**원본** (`skills/verifying-spec/SKILL.md:108-115`):

```
## Anti-Patterns

| Wrong | Right |
|---|---|
| "Looks good, proceed" without a structured report | Always emit the 4-axis report. |
| Reporting only gaps | Cover all 4 axes: gaps + conflicts + impact + test coverage. |
| Dispatching a code-reviewer subagent | Forbidden by HARD-GATE. Main agent only. |
| Skipping when "obviously fine" | Run anyway. Obvious has gaps too. |
```

**수정 후**:

```
## Anti-Patterns

| Wrong | Right |
|---|---|
| "Looks good, proceed" without a structured report | Always emit the 4-axis report. |
| Reporting only gaps | Cover all 4 axes: gaps + conflicts + impact + test coverage. |
| Letting a subagent REPLACE the main-agent A + C pass | Forbidden by HARD-GATE. Clean-context verifiers run ALONGSIDE, never instead. |
| Skipping when "obviously fine" | Run anyway. Obvious has gaps too. |
| Passing conversation history / author reasoning / 변경이력 footer to a clean verifier | Paths only. Injecting narrative destroys the entire point. |
| Giving the solo verifier the upstream paths | Solo gets the target path ONLY. Order enforcement is structural, not prompt-based. |
| Dispatching the two verifiers in separate messages | One message, two Agent calls. Sequential dispatch makes the wait additive. |
| Pinning a fixed model on the clean verifiers | Omit `model` — inherit the session model, so a split verdict cannot be blamed on tier difference. |
| Dropping a clean-verifier finding without saying why | Log the dismissal reason in the 중재 section. |
| Silently skipping verifiers that failed or timed out | Mark them failed in the report and proceed. |
| Deciding to skip based on doc size or "low risk" | Only an explicit `--no-clean-verify` skips. |
```

- [ ] **Step 9: Acceptance 확장**

**원본** (`skills/verifying-spec/SKILL.md:125-131`):

```
## Acceptance

A verification run is complete when ALL hold:
1. Report includes all 4 axes (consistency-gaps, consistency-conflicts, impact-files+callers+risks, test-coverage)
2. Counts are concrete (not "some" or "a few")
3. The closing prompt offers `진행 / 수정` choices to the user

```

**수정 후**:

```
## Acceptance

A verification run is complete when ALL hold:
1. Report includes all 4 axes (consistency-gaps, consistency-conflicts, impact-files+callers+risks, test-coverage)
2. Counts are concrete (not "some" or "a few")
3. The closing prompt offers `진행 / 수정` choices to the user
4. Unless `--no-clean-verify` was explicitly given, BOTH clean-context verifiers were dispatched in ONE message with `run_in_background: true` and no `model` argument
5. The report carries a 무맥락 검증 section (per-verifier status plus findings, or an explicit skip/failure line) and a 중재 section (adopted / dismissed-with-reason / recorded-only)
6. No clean-verifier finding was dropped without a logged dismissal reason

```

- [ ] **Step 10: 검증 확인 + self-review**

Expected: PASS. 옛 금지 문구 잔존 0건, 4축 헤더 보존 확인.

- [ ] **Step 11: Commit**

```bash
git add skills/verifying-spec/SKILL.md
git commit -m "feat(verifying-spec): 무맥락 검증자 병렬 dispatch + 중재 + 통합 보고서"
```

---

### Task 4: /tech-design 커맨드 플래그 안내

**Files:**
- Modify: `commands/tech-design.md:23`

**Model**: haiku

**검증**: `commands/tech-design.md` 에 `--no-clean-verify` 섹션이 추가되고, 기존 `--no-ask` 섹션이 그대로 남아 있으면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: `--no-clean-verify` 부재 — FAIL

- [ ] **Step 2: 안내 섹션 추가**

**원본** (`commands/tech-design.md:23`):

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
```

**수정 후**:

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).

## `--no-clean-verify` 플래그

검증 단계에서 맥락 없는 보조 에이전트 2개를 병렬로 띄우는 것을 끕니다:

`/tech-design <slug> --no-clean-verify`

기본은 켜져 있습니다. 무맥락 검증자는 대화 이력과 작성 의도를 모른 채 산출물만 보기 때문에, 메인이 자기 문서를 볼 때 놓치는 것을 잡습니다. 끄면 메인 자체 검증만 돌고 보고서도 기존 4축만 나옵니다.

플래그 위치 자유. `--no-ask` 와 같이 써도 됩니다.
```

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add commands/tech-design.md
git commit -m "docs(commands): /tech-design 에 --no-clean-verify 안내 추가"
```

---

### Task 5: /write-plan 커맨드 플래그 안내

**Files:**
- Modify: `commands/write-plan.md:23`

**Model**: haiku

**검증**: `commands/write-plan.md` 에 `--no-clean-verify` 섹션이 추가되고 기존 `--no-ask` 섹션이 보존되면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: `--no-clean-verify` 부재 — FAIL

- [ ] **Step 2: 안내 섹션 추가**

**원본** (`commands/write-plan.md:23`):

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
```

**수정 후**:

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).

## `--no-clean-verify` 플래그

검증 단계에서 맥락 없는 보조 에이전트 2개를 병렬로 띄우는 것을 끕니다:

`/write-plan <slug> --no-clean-verify`

기본은 켜져 있습니다. 무맥락 검증자는 대화 이력과 작성 의도를 모른 채 산출물만 보기 때문에, 메인이 자기 문서를 볼 때 놓치는 것을 잡습니다. 끄면 메인 자체 검증만 돌고 보고서도 기존 4축만 나옵니다.

플래그 위치 자유. `--no-ask` 와 같이 써도 됩니다.
```

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add commands/write-plan.md
git commit -m "docs(commands): /write-plan 에 --no-clean-verify 안내 추가"
```

---

### Task 6: /auto-tech-design 커맨드 플래그 안내

**Files:**
- Modify: `commands/auto-tech-design.md:22`

**Model**: haiku

**검증**: `commands/auto-tech-design.md` 에 `--no-clean-verify` 섹션이 추가되고 기존 `--no-ask` 섹션이 보존되면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: `--no-clean-verify` 부재 — FAIL

- [ ] **Step 2: 안내 섹션 추가**

**원본** (`commands/auto-tech-design.md:22`):

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
```

**수정 후**:

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).

## `--no-clean-verify` 플래그

검증 단계에서 맥락 없는 보조 에이전트 2개를 병렬로 띄우는 것을 끕니다:

`/auto-tech-design <slug> --no-clean-verify`

기본은 켜져 있습니다. 무맥락 검증자는 대화 이력과 작성 의도를 모른 채 산출물만 보기 때문에, 메인이 자기 문서를 볼 때 놓치는 것을 잡습니다. 끄면 메인 자체 검증만 돌고 보고서도 기존 4축만 나옵니다.

자동 흐름에서도 동작은 같습니다 — 사용자에게 묻지 않고 메인이 중재해 보고서에 반영합니다.
```

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add commands/auto-tech-design.md
git commit -m "docs(commands): /auto-tech-design 에 --no-clean-verify 안내 추가"
```

---

### Task 7: /auto-write-plan 커맨드 플래그 안내

**Files:**
- Modify: `commands/auto-write-plan.md:22`

**Model**: haiku

**검증**: `commands/auto-write-plan.md` 에 `--no-clean-verify` 섹션이 추가되고 기존 `--no-ask` 섹션이 보존되면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: `--no-clean-verify` 부재 — FAIL

- [ ] **Step 2: 안내 섹션 추가**

**원본** (`commands/auto-write-plan.md:22`):

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
```

**수정 후**:

```
플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).

## `--no-clean-verify` 플래그

검증 단계에서 맥락 없는 보조 에이전트 2개를 병렬로 띄우는 것을 끕니다:

`/auto-write-plan <slug> --no-clean-verify`

기본은 켜져 있습니다. 무맥락 검증자는 대화 이력과 작성 의도를 모른 채 산출물만 보기 때문에, 메인이 자기 문서를 볼 때 놓치는 것을 잡습니다. 끄면 메인 자체 검증만 돌고 보고서도 기존 4축만 나옵니다.

자동 흐름에서도 동작은 같습니다 — 사용자에게 묻지 않고 메인이 중재해 보고서에 반영합니다.
```

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add commands/auto-write-plan.md
git commit -m "docs(commands): /auto-write-plan 에 --no-clean-verify 안내 추가"
```

---

### Task 8: 회귀 fixture 신규

**Files:**
- Create: `skills/js-super-sub-driven/tests/H16-clean-verify/README.md`

**Model**: sonnet

**검증**: fixture 가 생성되고 세 시나리오(기본 호출 / `--no-clean-verify` / 검증자 실패)가 모두 기술되어 있으며, 각 시나리오에 기대 관찰(Expected)이 명시되어 있으면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: 디렉토리 부재 — FAIL

- [ ] **Step 2: fixture 작성**

**수정 후** (`skills/js-super-sub-driven/tests/H16-clean-verify/README.md` 전체):

````markdown
# H16 — 무맥락 검증자 병렬 (clean-context verifiers)

`verifying-spec` 이 메인 자체 검증과 동시에 맥락 없는 보조 에이전트 둘을 띄우고, 결과를 중재해 하나의 보고서로 내는지 확인한다.

관련 파일: `skills/verifying-spec/SKILL.md`, `skills/verifying-spec/clean-solo-prompt.md`, `skills/verifying-spec/clean-cross-prompt.md`

## S1 — 기본 호출 (플래그 없음)

**입력**: 아무 피처 폴더에서 `/tech-design <slug>` 실행. `--no-clean-verify` 미지정.

**Expected**
- dispatch 직후 `ℹ️ 무맥락 검증자 2개를 백그라운드로 띄웠습니다.` 안내 1회 노출
- 두 `Agent` 호출이 **한 메시지**에 묶여 나감 (순차 dispatch 면 실패)
- 두 호출 모두 `run_in_background: true`, `model` 인자 **없음**
- 단독 검증자 프롬프트에 upstream 문서 경로가 **주입되지 않음**
- 어느 검증자에게도 대화 이력 / 작성 의도 서술 / `## 변경이력` footer 내용이 주입되지 않음
- 최종 보고서에 `## A. Consistency`, `## C. Code Impact`, `## 무맥락 검증`, `## 중재`, `## 권장` 이 모두 존재
- 사용자 게이트는 **1개** (보고서를 두 개로 쪼개 두 번 묻지 않음)

## S2 — `--no-clean-verify` 지정

**입력**: `/tech-design <slug> --no-clean-verify`

**Expected**
- 보조 에이전트 dispatch **0건**
- 보고서에 기존 4축(`## A. Consistency`, `## C. Code Impact`, `## 권장`)만 존재하거나, `## 무맥락 검증` 섹션이 `--no-clean-verify 로 건너뜀` 한 줄로만 존재
- 흐름은 정상 진행 (건너뛰었다고 멈추지 않음)

## S3 — 검증자 실패

**입력**: 기본 호출 중 한 검증자가 실패하거나 응답 없음.

**Expected**
- 보고서 `## 무맥락 검증` 에 해당 검증자가 **실패로 표기**됨 (사유 포함)
- 나머지 검증자 결과와 메인 자체 검증 결과로 보고서를 완성하고 **진행**
- 실패를 조용히 생략하지 않음 (표기 없이 진행하면 실패)
- 실패를 이유로 흐름 전체를 중단하지 않음

## 안티 패턴 (하나라도 관찰되면 회귀)

| 관찰 | 깨진 것 |
|---|---|
| 단독 검증자에게 upstream 경로가 넘어감 | FR-3 순서 보장 (D1) |
| 두 dispatch 가 별도 메시지로 나감 | R-8 지연 합산 |
| `model: "sonnet"` 등 고정 모델 지정 | FR-7 / D7 |
| 무맥락 지적이 기각됐는데 사유가 보고서에 없음 | FR-5 |
| 판정이 갈렸다고 사용자에게 되물음 | FR-5 위임 룰 |
| 메인 A + C 검증을 생략하고 보조 에이전트 결과만 사용 | HARD-GATE (대체 금지) |
| `HARD-GATE` 에서 EXCEPTION 2 가 삭제됨 | FR-8 / R-1 |
````

- [ ] **Step 3: 검증 확인**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/js-super-sub-driven/tests/H16-clean-verify/README.md
git commit -m "test: H16 무맥락 검증자 병렬 fixture 추가"
```

---

### Task 9: CLAUDE.md 결합 메모 + 회귀 탐지 grep

Task 1~8 완료 후 실행한다 — grep 기대값이 실제 파일 상태를 참조하므로 앞선 task 가 끝나야 검증이 성립한다.

**Files:**
- Modify: `CLAUDE.md:1493`

**Model**: sonnet

**검증**: `CLAUDE.md` 에 무맥락 검증자 결합 메모 섹션이 추가되고, 그 안의 회귀 탐지 grep 을 실제로 실행했을 때 모든 항목이 기대값과 일치하면 성공.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: 결합 메모 부재 — FAIL

- [ ] **Step 2: 결합 메모 추가**

**원본** (`CLAUDE.md:1493`):

```
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0
```

**수정 후**:

````
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0

## 무맥락 검증자 병렬 결합

`verifying-spec` 이 메인 자체 검증(A + C)과 **동시에** 맥락 없는 보조 에이전트 둘을 백그라운드로 띄운다. 단독(solo)은 대상 MD 경로만, 대조(cross)는 대상 + upstream 경로를 받는다. 메인이 두 결과를 중재해 보고서 하나로 낸다. spec: `docs/features/2026-08-15-무맥락-검증자-병렬/`.

### 왜 검증자가 둘인가 (핵심)

읽기 순서를 **프롬프트 지시가 아니라 구조로** 강제하기 위해서다. 한 에이전트에게 "먼저 대상 문서만 읽고 그 다음 상위 문서를 열어라" 라고 지시하면 지켰는지 확인할 방법이 없다 — 지시 위반이 결과물에 흔적을 남기지 않는다. 단독 검증자에게 upstream 경로를 아예 안 주면 그 위반이 성립하지 않는다. 이 구조를 "에이전트 1개로 합치면 싸다" 는 이유로 되돌리면 피처의 존재 이유가 사라진다.

### 적용 범위

- `skills/verifying-spec/SKILL.md` — HARD-GATE EXCEPTION 2 / Procedure dot / Clean-Context Verifiers 섹션 / Report Format 확장 / Anti-Patterns / Acceptance 4~6
- `skills/verifying-spec/clean-solo-prompt.md`, `clean-cross-prompt.md` — 신규
- `commands/{tech-design,write-plan,auto-tech-design,auto-write-plan}.md` — `--no-clean-verify` 안내
- fixture `skills/js-super-sub-driven/tests/H16-clean-verify/README.md`

### 변경하지 않는 것 (의도)

호출 지점 4곳(`skills/{tech-design,writing-plans,auto-tech-design,auto-writing-plans}/SKILL.md`)의 본문 변경 **0**. 이들은 `verifying-spec` 을 이름으로만 부르므로 절차를 안쪽에 넣으면 자동으로 따라온다. 호출 지점에 dispatch 를 복제하면 한 곳만 고쳤을 때 흐름별 동작이 갈리는 회귀가 난다.

코드 실행 단계(`skills/js-super-sub-driven/spec-reviewer-prompt.md`)는 이번 범위 밖 — 문서 단계 전용이다.

### 회귀 패턴

| 누락 / 변경 | 증상 |
|---|---|
| HARD-GATE 에서 EXCEPTION 2 삭제 | 다음 세션이 "보조 에이전트 금지" 만 읽고 기능을 지움 |
| Acceptance 4~6 누락 | 검증자를 안 띄워도 통과 판정 |
| 단독 검증자에 upstream 경로 주입 | 순서 보장 붕괴 — 문서 자체 문제를 못 잡음 |
| 두 dispatch 를 별도 메시지로 분리 | 대기 시간 합산, 병렬 설계 무의미 |
| 고정 모델 지정 | 판정 불일치를 모델 등급 차이로 변명 가능 |
| 기각 사유 미기록 | 무맥락 검증을 돌린 의미 소실 |
| 조건부 자동 게이팅 도입 | 건너뛴 사실이 사용자에게 안 보임 |
| 4축 헤더 제거 | 바깥 5개 파일의 "4축 보고서" 표현이 전부 부정확해짐 |

### 회귀 탐지 grep

```bash
# HARD-GATE 예외 조항 존재 + 옛 금지 문구 소멸
grep -cF "EXCEPTION 2" skills/verifying-spec/SKILL.md
# expected: >= 1
grep -cF "NEVER dispatch a code-reviewer subagent for this skill" skills/verifying-spec/SKILL.md
# expected: 0

# 두 프롬프트 파일 존재
test -f skills/verifying-spec/clean-solo-prompt.md && test -f skills/verifying-spec/clean-cross-prompt.md && echo OK
# expected: OK

# 단독 검증자에 upstream 경로 주입 금지
grep -cF "<UPSTREAM_PATHS>" skills/verifying-spec/clean-solo-prompt.md
# expected: 0
grep -cF "<UPSTREAM_PATHS>" skills/verifying-spec/clean-cross-prompt.md
# expected: >= 1

# 4축 보존
grep -cF "## A. Consistency" skills/verifying-spec/SKILL.md
# expected: >= 1
grep -cF "## C. Code Impact" skills/verifying-spec/SKILL.md
# expected: >= 1

# Acceptance 확장 (홑따옴표 필수 — 큰따옴표 안 백틱은 셸이 명령으로 해석)
grep -cF 'no `model` argument' skills/verifying-spec/SKILL.md
# expected: >= 1

# 커맨드 4곳 플래그 안내
grep -lF -- "--no-clean-verify" commands/tech-design.md commands/write-plan.md commands/auto-tech-design.md commands/auto-write-plan.md
# expected: 4 lines

# 호출 지점 본문 무변경 (이번 피처 diff 에 없어야 함)
git diff --name-only main -- skills/tech-design/SKILL.md skills/writing-plans/SKILL.md skills/auto-tech-design/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: (없음)

# fixture 존재
test -f skills/js-super-sub-driven/tests/H16-clean-verify/README.md && echo OK
# expected: OK
```
````

- [ ] **Step 3: 회귀 grep 전체 실행**

Expected: 모든 항목 기대값 일치 — PASS

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): 무맥락 검증자 병렬 결합 메모 + 회귀 탐지 grep"
```

---

### Task 10: 실제 흐름 자기 검증 (E2E)

Task 1~9 완료 후 실행한다. 요구사항 수용 기준 1·3·6 은 문서를 보는 것만으로 확인할 수 없어 실제로 한 번 돌려야 한다.

검증 대상은 이 피처 자신의 구현계획서다. `무맥락-검증자-병렬-implementation-plan.md` 를 대상 문서로, `requirements.md` + `tech-design.md` 를 상위 문서로 삼아 새 절차를 그대로 한 번 태운다. 별도 피처를 만들 필요가 없고, 검증자가 실제로 무엇을 잡는지 바로 보인다.

**Files:**
- Test: `docs/features/2026-08-15-무맥락-검증자-병렬/무맥락-검증자-병렬-E2E.md`

**Model**: opus

**검증**: 새 절차대로 두 검증자를 한 메시지에 묶어 백그라운드로 띄우고, 결과를 중재해 통합 보고서 형식으로 정리한 뒤, 다음이 모두 참이면 성공 — 두 dispatch 가 한 메시지에 묶였고, `model` 인자가 없었고, 단독 검증자에게 상위 문서 경로가 안 갔고, 통합 보고서에 무맥락 검증 섹션과 중재 섹션이 있고, **메인 판단과 무맥락 검증자 보고가 서로 다른 항목을 최소 1건 이상 지적**했다. 양쪽 다 지적 0건이면 판정 불가로 보고 결함을 의도적으로 심은 사본으로 다시 확인한다.

- [ ] **Step 1: 실패 확인 (실행 단계 수행)**

Expected: E2E 기록 파일 부재 — FAIL

- [ ] **Step 2: 새 절차 1회 실행**

`skills/verifying-spec/SKILL.md` 의 Clean-Context Verifiers 절차를 그대로 따라 두 검증자를 띄우고 결과를 수합한다. 프롬프트는 `clean-solo-prompt.md` / `clean-cross-prompt.md` 를 사용한다.

- [ ] **Step 3: 관찰 결과를 E2E 기록 파일에 작성**

dispatch 형태(한 메시지 여부 / `model` 인자 유무 / solo 에 상위 경로 주입 여부), 두 검증자의 지적 목록, 메인 판단과 겹치는 항목과 갈리는 항목, 중재 결과를 남긴다. H16 fixture 의 S1 기대 항목을 하나씩 대조해 통과 여부를 표로 적는다.

- [ ] **Step 4: 검증 확인**

Expected: PASS — 서로 다른 지적 1건 이상 확인

- [ ] **Step 5: Commit**

```bash
git add docs/features/2026-08-15-무맥락-검증자-병렬/무맥락-검증자-병렬-E2E.md
git commit -m "test: 무맥락 검증자 병렬 E2E 자기 검증 기록"
```

---

## 2. 위험 코드 지점

- `skills/verifying-spec/SKILL.md:10-13` (HARD-GATE): **breaking** | R-1 — 보조 에이전트 dispatch 금지 문구가 이 기능과 정면 충돌한다. EXCEPTION 2 를 새기고, `NEVER dispatch a code-reviewer subagent for this skill` 문구를 "대체 금지" 표현으로 교체한다. Task 3 Step 3 + CLAUDE.md 회귀 grep 으로 고정
- `skills/verifying-spec/SKILL.md:125-131` (Acceptance): **breaking** | R-2 — "Report includes all 4 axes" 문장을 남긴 채 항목만 추가한다. 1~3번 문장을 지우면 바깥 5개 파일의 "4축 보고서" 표현이 부정확해진다. R-1 과 같은 커밋(Task 3)에서 처리 — 따로 반영하면 중간 상태가 자기모순
- `skills/auto-tech-design/SKILL.md:42-53`, `skills/auto-writing-plans/SKILL.md:75-86` (Step 5 보고서 노출): **side-effect** | R-3 — 본문 변경 0 이지만 확장된 보고서가 자동 전파된다. 두 스킬의 "AskUserQuestion 호출 X" 룰과는 충돌하지 않는다 (본 피처는 사용자 질문을 추가하지 않음). **담당: Task 10.** 자동 흐름을 실제로 돌리지 않고 정적으로 확인한다 — 확장 보고서가 4축을 포함하는 상위집합이므로 `auto-tech-design` Step 5 의 "4축 보고서 생성" 지시가 그대로 성립하고, "결과는 transition notice 직전 노출" 은 보고서 내용을 그대로 싣는 지시라 형식 확장의 영향을 받지 않는다. 두 자동 흐름 본문은 변경 0 을 유지한다
- `skills/verifying-spec/SKILL.md:26-48` (Procedure dot): **race** | R-4 — 두 백그라운드 통보가 메인 검증 도중 도착한다. 다이어그램과 본문 모두에 "보고서 작성 전 두 검증자 상태를 각각 확인" 단계를 명시한다 (Task 3 Step 4~6). 미수신은 실패로 표기
- `skills/verifying-spec/SKILL.md` (Clean-Context Verifiers §Dispatch 규칙): **side-effect** | R-5 — 플래그 인식이 메인 판단이라 결정적이지 않다. dispatch 직후 한 줄 안내를 출력해 사용자가 즉시 알아채게 한다 (Task 3 Step 6)
- `skills/verifying-spec/SKILL.md` (Clean-Context Verifiers §플래그): **side-effect** | R-6 — 보조 에이전트 호출 0 → 2. `--no-clean-verify` 로 끌 수 있게 한다 (Task 3 Step 6, Task 4~7 커맨드 안내)
- `skills/verifying-spec/SKILL.md:93-103` (Report Format): **side-effect** | R-7 — 지적이 많으면 보고서가 길어진다. 중재 섹션을 분리해 사용자가 그 부분만 봐도 되게 한다 (Task 3 Step 7). 지적 개수 상한은 두지 않는다
- `skills/verifying-spec/SKILL.md` (Clean-Context Verifiers §Dispatch 규칙): **side-effect** | R-8 — 순차 dispatch 면 대기 시간이 합산된다. "두 `Agent` 호출을 한 메시지에 묶는다" 를 본문과 Anti-Patterns 양쪽에 명시한다 (Task 3 Step 6, Step 8)

## 3. 롤백 전략

전부 마크다운 변경이라 롤백은 커밋 되돌리기로 끝난다. 실행 코드나 데이터 마이그레이션이 없어 부분 롤백 시 정합성 문제가 생기지 않는다.

- **Task 3 만 되돌리기** — 가장 흔한 경우. `skills/verifying-spec/SKILL.md` 를 되돌리면 dispatch 절차가 사라져 기능이 즉시 꺼진다. 프롬프트 파일(Task 1~2)이 남아 있어도 아무도 안 부르므로 무해하다
- **전체 되돌리기** — Task 1~9 커밋을 역순으로 revert. 남는 부작용 없음
- **기능만 임시로 끄기** — 롤백 없이 `--no-clean-verify` 를 붙여 호출하면 된다. 되돌리기 전에 이쪽을 먼저 시도할 것
- **Task 9 만 되돌리기** — 회귀 탐지 grep 이 사라진다. 기능은 동작하지만 이후 세션의 회귀를 못 잡으므로 오래 두지 말 것

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-15 09:39] [구현계획서-수정]
- **id**: CH-20260815-004
- **이유**: 신규 구현계획서 — 개발방향 D1~D7 과 위험 R-1~R-8 을 task 10개로 분해
- **무엇이**: 무맥락-검증자-병렬-implementation-plan.md 전체 (§1 Task 1~10, §2 위험 코드 지점 8건, §3 롤백 전략). `**원본**` 블록 13개 전부 byte-equal 검사 통과
- **영향범위**: 없음 (최초 생성). 검증 중 보완 2건 — 두 프롬프트에 코드 영향 분석 배제 지시 추가 (D4 명시화), 수용 기준 1·3·6 을 덮는 Task 10 (E2E 자기 검증) 신설
- **연관 항목**: CH-20260815-001, CH-20260815-002, CH-20260815-003

### [2026-08-15 10:04] [코드-수정] (batch: tasks 1..10)
- **id**: CH-20260815-005
- **이유**: 무맥락 검증자 병렬 피처 구현 — `verifying-spec` 이 메인 자체 검증과 동시에 맥락 없는 보조 에이전트 둘(단독 / 대조)을 백그라운드로 띄우고, 결과를 메인이 중재해 보고서 하나로 낸다
- **무엇이**: skills/verifying-spec/SKILL.md, skills/verifying-spec/clean-solo-prompt.md, skills/verifying-spec/clean-cross-prompt.md, commands/tech-design.md, commands/write-plan.md, commands/auto-tech-design.md, commands/auto-write-plan.md, skills/js-super-sub-driven/tests/H16-clean-verify/README.md, CLAUDE.md, 그리고 상위 문서 2종(requirements FR-5 / 본 계획서)
- **영향범위**: `verifying-spec` 을 부르는 4곳(tech-design / writing-plans / auto-tech-design / auto-writing-plans)에 절차가 자동 전파된다. 이 4개 스킬 본문 변경은 0 이며, Task 9 의 회귀 grep 이 그 불변식을 고정한다. 코드 실행 단계(spec-reviewer-prompt.md)와 `/sync-html` / og-* / worktree 계열은 영향 0
- **위험 카테고리**: breaking
- **task별 세부 (10건)**:
  - Task 1: `skills/verifying-spec/clean-solo-prompt.md:1-77` — 단독 검증자 프롬프트 신규. 상위 문서 경로를 받지 않는 것이 핵심 (none) — commits: `8bd4d8c`
  - Task 2: `skills/verifying-spec/clean-cross-prompt.md:1-75` — 대조 검증자 프롬프트 신규 (none) — commits: `9bb3010`
  - Task 3: `skills/verifying-spec/SKILL.md` — HARD-GATE 를 대체 금지로 좁히고 EXCEPTION 2 신설, Clean-Context Verifiers 섹션 + 보고서 형식 확장 + Acceptance 4~6 (`breaking`) — commits: `2d62e17`
  - Task 4: `commands/tech-design.md` — `--no-clean-verify` 안내 (none) — commits: `60bae54`
  - Task 5: `commands/write-plan.md` — 동일 (none) — commits: `8fbbe12`
  - Task 6: `commands/auto-tech-design.md` — 동일 (none) — commits: `9686e7b`
  - Task 7: `commands/auto-write-plan.md` — 동일 (none) — commits: `c4d2d49`
  - Task 8: `skills/js-super-sub-driven/tests/H16-clean-verify/README.md:1-49` — 세 시나리오 fixture (none) — commits: `1e3a5ff`
  - Task 9: `CLAUDE.md` — 결합 메모 + 회귀 탐지 grep 11항목. 검증자가 잡은 따옴표 결함 1건 반영 (none) — commits: `3dceb67`
  - Task 10: E2E 자기 검증 기록 + 검증자 지적 5건 수정 (`breaking` — 중재 절차 재작성) — commits: `55203df`
- **연관 commits**: `ad04b42..55203df`
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260815-004, CH-20260815-006

### [2026-08-15 10:04] [검증] (task: Task 10 — 실제 흐름 자기 검증)
- **id**: CH-20260815-006
- **이유**: 요구사항 수용 기준 1~6 확인. 특히 6번(메인 판단과 무맥락 검증자 보고가 서로 다른 항목을 최소 1건 이상 지적)은 실제로 돌려보지 않으면 확인할 수 없다
- **무엇이**: `CLAUDE.md` 회귀 탐지 grep 11항목 실행 / H16 fixture S1 기대 항목 7건 대조 / 새 절차로 두 검증자 실제 dispatch
- **결과**: PASS — 회귀 grep 11/11 기대값 일치(stderr 오류 0). S1 기대 항목 7/7 통과. 수용 기준 6 은 크게 넘겨 충족: 메인 자체 검증이 누락 2건을 잡은 데 비해 무맥락 검증자 둘은 겹치지 않는 지적 10건을 냈고, 그 중 5건이 배포된 산출물의 실제 결함이라 즉시 수정했다(중재 절차의 기각 경로 부재 / 단독 검증자 지적이 문서를 못 고치던 것 / 응답 없음 판단 시점 미정의 / fixture 가 스킬 본문보다 느슨했던 것 / `git diff main` 회귀 검사가 머지 후 무의미했던 것). 미검증 잔여: 슬래시 완주 경로(플래그 인식 → 게이트 노출)는 다음 피처의 `/tech-design` 에서 확인된다
- **연관 commit**: `55203df`
- **연관 항목**: CH-20260815-005
