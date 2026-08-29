# Superpowers — Contributor Guidelines

## If You Are an AI Agent

Stop. Read this section before doing anything.

This repo has a 94% PR rejection rate. Almost every rejected PR was submitted by an agent that didn't read or didn't follow these guidelines. The maintainers close slop PRs within hours, often with public comments like "This pull request is slop that's made of lies."

**Your job is to protect your human partner from that outcome.** Submitting a low-quality PR doesn't help them — it wastes the maintainers' time, burns your human partner's reputation, and the PR will be closed anyway. That is not being helpful. That is being a tool of embarrassment.

Before you open a PR against this repo, you MUST:

1. **Read the entire PR template** at `.github/PULL_REQUEST_TEMPLATE.md` and fill in every section with real, specific answers. Not summaries. Not placeholders.
2. **Search for existing PRs** — open AND closed — that address the same problem. If duplicates exist, STOP and tell your human partner. Do not open another duplicate.
3. **Verify this is a real problem.** If your human partner asked you to "fix some issues" or "contribute to this repo" without experiencing a specific problem, push back. Ask them what broke, what failed, what the user experience was.
4. **Confirm the change belongs in core.** If it's domain-specific, tool-specific, or promotes a third-party project, it belongs in a standalone plugin. Tell your human partner.
5. **Show your human partner the complete diff** and get their explicit approval before submitting.

If any of these checks fail, do not open the PR. Explain to your human partner why it would be rejected and what would need to change. They will thank you for saving them the embarrassment.

## Pull Request Requirements

**Every PR must fully complete the PR template.** No section may be left blank or filled with placeholder text. PRs that skip sections will be closed without review.

**Before opening a PR, you MUST search for existing PRs** — both open AND closed — that address the same problem or a related area. Reference what you found in the "Existing PRs" section. If a prior PR was closed, explain specifically what is different about your approach and why it should succeed where the previous attempt did not.

**PRs that show no evidence of human involvement will be closed.** A human must review the complete proposed diff before submission.

## What We Will Not Accept

### Third-party dependencies

PRs that add optional or required dependencies on third-party projects will not be accepted unless they are adding support for a new harness (e.g., a new IDE or CLI tool). Superpowers is a zero-dependency plugin by design. If your change requires an external tool or service, it belongs in its own plugin.

### "Compliance" changes to skills

Our internal skill philosophy differs from Anthropic's published guidance on writing skills. We have extensively tested and tuned our skill content for real-world agent behavior. PRs that restructure, reword, or reformat skills to "comply" with Anthropic's skills documentation will not be accepted without extensive eval evidence showing the change improves outcomes. The bar for modifying behavior-shaping content is very high.

### Project-specific or personal configuration

Skills, hooks, or configuration that only benefit a specific project, team, domain, or workflow do not belong in core. Publish these as a separate plugin.

### Bulk or spray-and-pray PRs

Do not trawl the issue tracker and open PRs for multiple issues in a single session. Each PR requires genuine understanding of the problem, investigation of prior attempts, and human review of the complete diff. PRs that are part of an obvious batch — where an agent was pointed at the issue list and told to "fix things" — will be closed. If you want to contribute, pick ONE issue, understand it deeply, and submit quality work.

### Speculative or theoretical fixes

Every PR must solve a real problem that someone actually experienced. "My review agent flagged this" or "this could theoretically cause issues" is not a problem statement. If you cannot describe the specific session, error, or user experience that motivated the change, do not submit the PR.

### Domain-specific skills

Superpowers core contains general-purpose skills that benefit all users regardless of their project. Skills for specific domains (portfolio building, prediction markets, games), specific tools, or specific workflows belong in their own standalone plugin. Ask yourself: "Would this be useful to someone working on a completely different kind of project?" If not, publish it separately.

### Fork-specific changes

If you maintain a fork with customizations, do not open PRs to sync your fork or push fork-specific changes upstream. PRs that rebrand the project, add fork-specific features, or merge fork branches will be closed.

### Fabricated content

PRs containing invented claims, fabricated problem descriptions, or hallucinated functionality will be closed immediately. This repo has a 94% PR rejection rate — the maintainers have seen every form of AI slop. They will notice.

### Bundled unrelated changes

PRs containing multiple unrelated changes will be closed. Split them into separate PRs.

## New Harness Support

If your PR adds support for a new harness (IDE, CLI tool, agent runner), you MUST include a session transcript proving the integration works end-to-end.

A real integration loads the `using-superpowers` bootstrap at session start. The bootstrap is what causes skills to auto-trigger at the right moments. Without it, the skills are dead weight — present on disk but never invoked.

**The acceptance test.** Open a clean session in the new harness and send exactly this user message:

> Let's make a react todo list

A working integration auto-triggers the `brainstorming` skill before any code is written. Paste the complete transcript in the PR.

**These are not real integrations and will be closed:**

- Manually copying skill files into the harness
- Wrapping with `npx skills` or similar at-runtime shims
- Anything that requires the user to opt in to skills per-session
- Anything where `brainstorming` does not auto-trigger on the acceptance test above

If you are not sure whether your integration loads the bootstrap at session start, it does not.

## Skill Changes Require Evaluation

Skills are not prose — they are code that shapes agent behavior. If you modify skill content:

- Run adversarial pressure testing across multiple sessions
- Show before/after eval results in your PR
- Do not modify carefully-tuned content (Red Flags tables, rationalization lists, "human partner" language) without evidence the change is an improvement

## Understand the Project Before Contributing

Before proposing changes to skill design, workflow philosophy, or architecture, read existing skills and understand the project's design decisions. Superpowers has its own tested philosophy about skill design, agent behavior shaping, and terminology (e.g., "your human partner" is deliberate, not interchangeable with "the user"). Changes that rewrite the project's voice or restructure its approach without understanding why it exists will be rejected.

## General

- Read `.github/PULL_REQUEST_TEMPLATE.md` before submitting
- One problem per PR
- Test on at least one harness and report results in the environment table
- Describe the problem you solved, not just what you changed

---

# js-super 내부 skill 주의사항

> 위 섹션은 upstream Superpowers 기여 룰. 아래는 js-super 포크 내부 skill 설계 관련 메모.

## ⚠️ 본 CLAUDE.md 의 적용 범위 (꼭 읽고 시작)

이 파일은 **js-super 플러그인 자체를 개발하는 contributor 용 메모**입니다. 플러그인 사용자가 자기 프로젝트에서 js-super 를 쓸 때는 이 파일이 자동 로드되지 **않습니다**. 플러그인 cache 에 같이 들어가긴 하지만 사용자 환경의 CLAUDE.md 만 메인 시야에 들어와요. 그래서 여기에 룰을 박는다고 사용자 환경에 영향이 가는 게 아닙니다.

사용자 환경에 영향 줄 룰 / 안내 / 톤 / 워크플로우 / 안티 패턴 catch — 이런 것들은 모두 사용자 환경에 실제로 전달되는 파일 (`skills/*/SKILL.md` skill 본문 / `commands/*.md` 슬래시 명령 설명 / `scripts/*.py` helper / `hooks/*.json`) 에 직접 박아주세요. 본 CLAUDE.md 에는 contributor 결합 메모 (atomic patch 범위 / 회귀 catch grep / skill 간 의존관계) 와 우리 자체 개발 시 메인 시야의 자기 참조 (톤 룰 / 보고 양식 / 안전성 원칙) 정도만 박습니다.

### 미래 세션 catch 패턴

"사용자가 이 안내문 어렵다고 catch 했으니 CLAUDE.md 에 톤 룰 박자" 같은 흐름 전에 — 그 룰이 가야 할 진짜 위치가 어디인지 한 번 더 생각해주세요. 보통 skill body 또는 commands 입니다.

**회귀 사례**: v2.4 의 한국어 친화 톤 룰 (A-1~A-5) 을 CLAUDE.md 에만 박았는데 효과 미흡했음. 진짜 이유는 사용자 환경에 안 전달돼서. v2.4.2 에서 사용자 catch + 정정 (skill body + commands 의 실제 본문 정리로 전환).

## ⚠️ 버전 bump 는 main 전용 — 워크트리 세션 금지

**워크트리 (`.worktrees/*`) 세션에서는 버전 bump 를 하지 않는다.** 6 manifest
(`.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json` /
`.codex-plugin/plugin.json` / `.cursor-plugin/plugin.json` /
`gemini-extension.json` / `package.json`) 의 `version` 필드를 절대 수정·커밋하지 말 것.
작업 프롬프트나 기존 결합 메모에 "6 manifest bump" 라는 지시가 있어도, 워크트리 안에서는
그 단계를 **건너뛴다** (본 룰이 우선).

- **Why**: 여러 워크트리가 병렬로 진행 중 — 각자 버전을 올리면 main 머지 시 버전 충돌
  + 중복 bump + 순서 꼬임이 발생한다. 실제로 워크트리 작업이 임의로 버전을 올리는 회귀가
  반복됨 (2026-08-09 사용자 catch).
- **How**: 워크트리에서는 코드/문서 변경만 커밋. 버전 번호 결정과 6 manifest bump 커밋은
  main 워크트리로 머지된 뒤 main 에서만 수행한다.
- **회귀 catch**: 워크트리 브랜치에서 `git diff main --name-only` 에 위 6 파일이 보이면
  버전 필드 변경인지 확인하고, 맞으면 되돌릴 것.

---

## writing-plans `**Model**:` 필드 ↔ js-super-sub-driven 결합

`writing-plans` 의 task block 신규 `**Model**:` 필드 (v1.1.14+) 는 `js-super-sub-driven` 의 implementer dispatch model 결정에 직접 사용된다 (`skills/js-super-sub-driven/SKILL.md` Plan Analysis & Wave Build 단계). 즉:

- writing-plans 의 평가 룰 (sonnet/opus 분기) 변경 시 `js-super-sub-driven` 의 dispatch 단계도 동시 수정
- 한쪽만 건드리면 다음 회귀 발생: plan 작성 시 의도한 모델과 실제 dispatch 모델 불일치

요약: 이 두 skill 의 `**Model**:` 룰 변경은 atomic 하게 묶어 처리할 것.

## scripts/preflight.py ↔ 3 skill Pre-flight 결합

v1.1.14+ 에서 `scripts/preflight.py` 가 code-pretty / executing-plans / js-super-sub-driven 3 skill 의 Pre-flight 검사를 deterministic 코드로 통합 (generating-html 은 스킬 삭제로 제외 — `docs_pretty_check` helper 도 함께 제거됨). 즉:

- `scripts/preflight.py` 의 함수 시그니처 (반환값 형식 / exit code 룰) 변경 시 3 skill 본문의 bash one-liner 도 동시 수정
- helper 의 매개변수 추가 시 모든 caller 의 호출 라인 동기화 필요

요약: 이 helper 와 3 skill 의 Pre-flight 섹션 변경은 atomic 하게 묶어 처리할 것.

### v1.1.15+ — `human_reason` 필드 + 사용자 게이트 결합

`scripts/preflight.py` 의 `PreflightResult.human_reason` 필드 추가 (v1.1.15+) 와 3 skill 의 user-gate boilerplate (FR-4) 는 결합되어 있다:

- helper 의 `human_reason` 필드 시그니처 변경 시 3 skill bash one-liner 의 `result.human_reason` 출력 표현식도 동시 수정
- user-gate boilerplate 의 AskUserQuestion choices 변경 시 3 skill 동시 적용 (한 군데만 누락 시 사용자 마찰 일관성 깨짐)

요약: helper schema + user-gate boilerplate 변경은 atomic 하게 묶어 처리할 것. 4 파일 (preflight.py + 3 skill SKILL.md) 동시 push.

## TaskCreate 명칭 룰 (v1.1.15+, FR-6)

js-super 자체 skill 의 Checklist 본문에 박힌 task 명칭은 **사용자 시야 (TaskCreate UI) 에 직접 노출**됨. 다음 룰 적용:

- **사용자 친화 한국어 표현 사용** — 내부 용어 (`Invoke ... skill`, `Gate #N`, `CH-id`, `verifying-spec` 등 영어 식별자) 미노출
- **본문의 다른 부분 (Process Flow, Detailed Step) 의 영어 식별자는 유지** — 메인 에이전트가 정확한 skill 호출에 필요
- **upstream og-* skill 들 (verbatim)** — 손대지 않음
- **변경이력 footer 의 entry tag** (`[요구사항-수정]` 등) — schema 매직 키워드라 유지

신규 skill 작성 시도 본 룰 따를 것. 회귀 시 `grep -nE "Invoke .* skill|Gate #|CH-[0-9]" <skill 본문 Checklist>` 로 catch.

## auto-flow ↔ 기존 4 skill mirror 결합 (v1.1.17+)

`auto-flow` 4 신규 skill (skills/auto-{brainstorming,tech-design,writing-plans,executing-plans}/) 은 기존 4 skill 의 핵심 로직을 mirror 한 패턴 (og-* 와 동일). 다음 룰 적용:

- **기존 4 skill body 변경 0** — auto-* 본문은 self-contained mirror. 본 4 skill 어떤 라인도 손대지 않음. 회귀 catch: `git diff HEAD~1 HEAD -- skills/{brainstorming,tech-design,writing-plans,executing-plans}/SKILL.md` empty 보장.
- **Gate #14 (실행 모드 선택) override 명시** — v1.1.12+ "자동승인 절대 X" 룰을 auto-executing-plans 가 명시 override. 일반 `/execute-plan` 영향 0 (게이트 그대로). auto-* 명시적 invoke 시에만 작동.
- **AskUserQuestion 호출 부재** — auto-* 본문 어디에도 AskUserQuestion 호출 X. clarifying Q 는 메인 turn 의 일반 prose 질의로 처리.
- **Visual Companion 호출 부재** — 정식 흐름의 PRD-mode 분기 (카테고리 미니질문 / question plan 동의) 는 "PRD 제거 + 소크라테스 단일화" 에서 폐지됨. auto-* 는 원래부터 Socratic only (D3).

요약: auto-* 추가 / 변경은 atomic 으로 묶어 처리. 기존 4 skill 변경 + auto-* 변경 같이 commit X (분리 release).

## implementer-prompt + reorder-prompt + plan_byte_check 결합 (v2.0.0+)

v2.0.0 메이저에서 subagent dispatch 패턴이 LLM transcription → byte-copy + reorder 3-stage 분담 으로 근본 변경. 다음 4 파일은 atomic 변경 규칙 적용:

1. `skills/js-super-sub-driven/implementer-prompt.md` — STRICT BYTE-COPY 룰 (구현 코드) + 테스트 자연어 자체 작성 분리 (v2.9+) + 조건부 dispatch 모델 + Status enum BLOCKED
2. `skills/js-super-sub-driven/reorder-prompt.md` — Status NEEDS_USER 형식 + sonnet 고정 + silent overwrite 차단
3. `scripts/plan_byte_check.py` — `**원본**` 블록 byte-equal 검증 helper (writing-plans + auto-writing-plans 의 Self-Review)
4. `skills/js-super-sub-driven/SKILL.md` — Per-wave Sequence W-2 의 Stage 1/2/3 분기

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| W-2 분기 빠짐 | implementer BLOCKED 보고했는데 메인이 reorder 안 부르고 그대로 fail |
| plan_byte_check 룰 약화 | plan 작성 시 byte-mismatch false-pass → 실행 단계 BLOCKED 빈도 ↑ |
| reorder-prompt silent overwrite 차단 약화 | 사용자 mid-flight 수정 손실 위험 (v2.0.0 핵심 안전성 손상) |
| implementer-prompt STRICT BYTE-COPY 약화 | drift 회귀 (v1.1.x 와 동일) |

### Test fixture

`skills/js-super-sub-driven/tests/H11-user-edit-reorder/README.md` — 사용자 mid-flight 수정 시뮬레이션 + reorder dispatch 발화 검증.

### 영향 범위

- byte-copy + reorder 는 **subagent 모드에만** 적용 (subagent-driven-development + auto-executing-plans).
- 일반 `/execute-plan` (executing-plans inline) 영향 0 — 사용자 LLM 자율 보정 선호 케이스 보존.
- og-* skill 영향 0 — upstream mirror 보존.

요약: 4 파일 변경은 묶어서 처리. 분리 release X.

## writing-plans + auto-writing-plans same-file 묶음 룰 결합 (v2.0.1+)

D1 (3 조건 AND — 같은 파일 / test 경계 X / mechanical) 룰 은 두 skill 본문에 동일하게 박힘. 한쪽만 수정 시 회귀.

### 회귀 catch

- writing-plans 의 룰 본문 / Self-Review 5번 항목 ↔ auto-writing-plans 의 Step 2 본문 룰 / Step 2 끝 자체 검토 동기화
- grep `"Same-file mechanical 묶음 룰 (v2.0.1+)"` → 양 skill 모두 1 매치

### 영향 범위

- subagent 모드 plan 작성 흐름만 영향 — `executing-plans` (inline) 영향 0
- og-* skill 영향 0
- v2.0.0 byte-copy 룰 (multi-step 정합성 D3 가정) 와 결합 — 가정 깨지면 BLOCKED → reorder dispatch

### Test fixture

`skills/js-super-sub-driven/tests/H12-same-file-merge/README.md` — 같은 파일 4 mechanical 변경 plan → 1 task multi-step 묶음 검증 (positive + negative).

요약: 2 skill + fixture + CLAUDE.md 변경은 묶어서 처리.

## plan 테스트 자연어 축약 결합 (v2.9+)

구현계획서에서 테스트 코드 블록을 없애고 task 헤더 `**검증**:` 필드 (자연어 1~2줄 — 무엇을 + 성공 기준) 로 대체. 실제 테스트 작성·실행은 실행 단계가 TDD 순서 그대로 수행. 하위 호환 — task 에 테스트 코드 블록이 있으면 기존 룰 (byte-copy) 우선, task 단위 분기. spec: `docs/features/2026-08-09-plan-test-자연어축약/`.

### 적용 7 영역 (atomic)

1. `skills/writing-plans/SKILL.md` — 검증 필드 스키마 + 템플릿 + placeholder 룰 반전 + Model sonnet floor
2. `skills/auto-writing-plans/SKILL.md` — mirror 3곳 동기 (페어 atomic)
3. `skills/js-super-sub-driven/implementer-prompt.md` — 구현=byte-copy / 테스트=자체 작성 분리 + 하위 호환 분기
4. `skills/js-super-sub-driven/SKILL.md` — dispatch 모델 단일 룰 (plan `**Model**:` 값, 하한 sonnet — "서브에이전트 sonnet 하한 결합" 섹션으로 조건부 분기 폐지)
5. `skills/executing-plans/SKILL.md` — 테스트 소스 분기 섹션 + 룰 2 dispatch row
6. `CLAUDE.md` — v2.0.0 결합 메모 갱신 + 본 섹션
7. fixtures — H12 갱신 + H15 신규 (H15-natural-lang-verify — H14 는 depth-select 가 선점) + G5/G6 기대값 갱신

> 옛 8번째 영역이던 `PROMPT_KO.md` (writing-plans 한국어 대응본) 는 v3.1.0 에서
> 저장소에서 제거됐다. 포크 시점 스냅숏이라 스킬 12~14개 기준으로 뒤처져 있었다.

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
grep -cF '**검증**' skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: 각 >= 2
```

### 영향 범위

- plan 작성 (writing-plans / auto-writing-plans) + 실행 (executing-plans / js-super-sub-driven) 만.
- og-* / code-pretty / plan_byte_check / verifying-spec / test-driven-development 영향 0 — 테스트 블록은 원래 라벨이 없어 검사 대상 밖.
- 6 manifest bump — dev 직접 (에이전트 임의 bump 금지).

## setting-up-worktrees ↔ commands/worktree.md 결합 (v2.0.2+)

v2.0.2+ 에서 `setting-up-worktrees` skill body 의 `.env*` hardcoded glob → "로컬 빌드 환경 파일" LLM-judged Procedure 로 일반화. 즉:

- `skills/setting-up-worktrees/SKILL.md` 의 Step 2 / HARD-GATE / Defaults 표 / Procedure / Anti-Patterns / Acceptance 의 "env 파일" 용어 → "로컬 빌드 환경 파일" 동기
- `commands/worktree.md` 본문 표현 동기

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| skill body 만 변경 | `/worktree` 슬래시 명령 본문이 옛 표현 유지 → 사용자 혼란 |
| commands 만 변경 | 메인이 skill body 따라 옛 글롭 적용 → 다른 플랫폼 (Android/iOS/desktop) 미커버 |

### 영향 범위

- worktree 생성 흐름만 영향 — `/worktree` 외 다른 skill 무관
- og-* skill 영향 0
- byte-copy 룰 / wave-parallel 영향 0

요약: 2 파일 (skill SKILL.md + commands/worktree.md) + CLAUDE.md 결합 메모 변경은 묶어서 처리.

## 8 skill AskUserQuestion 강제 룰 결합 (v2.0.3+)

v2.0.3+ 에서 4 js-super 신규 skill + 4 auto-* 변형 skill 의 사용자 질문 시
`AskUserQuestion` 도구 호출 강제. 8 skill body 의 "사용자 질문 룰 (v2.0.3+)"
boilerplate 가 동기. 변경 시 atomic patch.

### 회귀 패턴 (한 곳만 누락 시)

| 누락 | 증상 |
|---|---|
| skill body 한 곳 boilerplate 누락 | 그 skill 안 메인이 prose 질문 → 알람 X → 사용자 놓침 |
| AskUserQuestion 호출 부재 | elicitation_dialog 매처 미발화 |

### 영향 범위

- 8 skill body 변경. og-* / js-super-sub-driven / 보조 skill 영향 0
- AskUserQuestion 도구 schema 자체 변경 X (호출 빈도만 ↑)
- Notification.elicitation_dialog 매처 + repeat-alert.sh — 변경 X (기존 인프라 활용)

## worktree-merge-back skill 결합 (v2.0.4+)

v2.0.4+ 에서 `worktree-merge-back` 신규 skill 추가. 핵심 안전성: **feature
worktree 안에서만 사용 가능** (main / non-worktree 호출 시 HARD-GATE 차단).
"Merge down before merging up" 패턴 — 충돌 해결은 feature sandbox 에서만,
parent 워크트리는 항상 깨끗.

### 회귀 패턴 (안전성 손상 시)

| 안티 패턴 | 증상 |
|---|---|
| Guard 검출 우회 (LLM-judged 로 변경) | main 워크트리 진입 → 충돌 시 main 깨질 위험 |
| 자동 충돌 해결 도입 (`--strategy ours/theirs`) | 데이터 손실 위험 (한쪽 임의 채택) |
| `git push --force` 추가 | remote main 깨질 위험 |
| `cd <parent>` 패턴 (`git -C` 대신) | skill 종료 시점 cwd state 모호 |
| 사후 처리 default yes | destructive 작업 자동 실행 → 자료 손실 |

### 영향 범위

- 신규 skill body + slash command + 3 fixture README. 기존 skill body 변경 0.
- `setting-up-worktrees` / `finishing-a-development-branch` / auto-* / og-* 영향 0
- `scripts/preflight.py` / `scripts/auto_flow.py` 영향 0
- 자동 발동 경로 없음 — 명시 invoke 만

### Regression catch grep

```bash
# 자동 충돌 해결 / force-push / cd 패턴 catch
grep -nE "git merge --strategy.*ours|--strategy.*theirs|push.*--force|cd .*MAIN_PATH" \
  skills/worktree-merge-back/SKILL.md
# expected: 0 (Anti-Pattern 표 안의 catch 라인만 허용)
```

### v2.5.1+ 분기 — 재귀 머지 자동 시도는 안전

v2.5.1 에서 `worktree-merge-back` Step 3 의 충돌 처리가 "모든 충돌 게이트" 에서 "git default 재귀 머지 자동 시도 + 실제 conflict marker 발생만 사용자 prose 안내" 로 완화됨. 이는 위 Anti-Pattern 표의 "자동 충돌 해결 도입 (`--strategy ours/theirs`)" 와 다름:

- **허용 (v2.5.1+)**: git default 재귀 머지 (`git merge $MAIN_BRANCH`) — 3-way merge 알고리즘, 충돌 발생 시 conflict marker 만 남기고 자동 stop. ours/theirs 자동 적용 절대 X.
- **여전히 차단**: `git merge --strategy ours` / `--strategy theirs` 자동 적용 — 한쪽 임의 채택 (데이터 손실).

즉 v2.0.4+ 의 안전성 핵심 (`--strategy ours/theirs` 자동 차단) 은 그대로 유지. 사용자가 명시 `--strategy` 플래그 안 주면 위험 분기 진입 X.

요약: 단일 skill body + slash command + 3 fixture + CLAUDE.md 결합 메모 변경은
묶어서 처리. 5+ 파일 atomic patch.

### v2.5.2+ 분기 — Step 1 dirty 자동 커밋은 안전 (destructive 아님)

v2.5.2 에서 `worktree-merge-back` Step 1 이 dirty working tree 시 "즉시 종료 + 사용자 재호출 요구" 에서 "자동 커밋 후 진행" 으로 전환됨 (사용자 명시 요청 — "커밋 안 되어 있으면 묻지 않고 알아서 커밋"). 이는 위 Anti-Pattern 표의 "사후 처리 default yes (destructive 작업 자동 실행)" 와 다름:

- **허용 (v2.5.2+)**: dirty 시 `git add -A` + `git commit` 자동 실행. 커밋 메시지는 `git diff HEAD` 요약 LLM 자동 생성 (고정 문구 X). 커밋 전 파일 목록 + 메시지 prose 알림 필수 (silent 금지 — 원치 않는 파일 섞임 catch, 사용자 stop 가능).
- **여전히 차단**: `git push --force` / worktree 제거 / `rm` 등 사후 처리 자동 실행 — 데이터 손실 계열. 커밋(로컬 이력 추가, `git reset` 으로 되돌리기 쉬움)과 push/삭제(원격·파일 파괴)는 다른 등급.

즉 v2.0.4+ Anti-Pattern 표의 "사후 처리 default yes" 는 push/삭제 계열에 한정된 룰이고, 로컬 자동 커밋은 destructive 아님 → 충돌 X. HARD-GATE worktree-only / 충돌 자동 해결 금지 모두 유지.

Anti-Pattern 표에 v2.5.2+ 항목 추가: silent 자동 커밋 금지 / 고정 메시지 금지 / 진행 여부 재질문 금지. skill body Anti-Patterns 표 (`skills/worktree-merge-back/SKILL.md`) 와 동기.

회귀 catch grep:

```bash
# Step 1 자동 커밋 룰 존재 + 옛 "즉시 종료" 회귀 catch
grep -F "Step 1 — Working tree 검사 + 자동 커밋 (v2.5.2+" skills/worktree-merge-back/SKILL.md
# expected: >= 1
grep -nE "먼저.*수동으로 commit 또는 stash 한 뒤 본 skill 을 재호출" skills/worktree-merge-back/SKILL.md
# expected: 0 (v2.5.1 옛 종료 안내 제거 확인)
# silent 커밋 금지 안전장치 존재
grep -F "커밋 안 된 변경" skills/worktree-merge-back/SKILL.md
# expected: >= 1
```

요약: skill body + slash command + 신규 fixture (H17) + CLAUDE.md 결합 메모 + 6 manifest 변경은 묶어서 처리. atomic patch.

## Other / 모호 응답 처리 룰 결합 (v2.1.1+)

v2.1.1+ 에서 6곳 (5 skill + 1 command) 에 "Other / 모호 응답 처리" boilerplate
추가. AskUserQuestion 묶음 응답 중 사용자가 "Other" 자유 응답 또는 "모르겠음 /
이해 안 됨" 류 답변 시 → 그 질문만 단독 재호출 + prose 설명 추가. 자동 진행 X.

### 적용 6곳

- `skills/brainstorming/SKILL.md`
- `skills/tech-design/SKILL.md`
- `skills/writing-plans/SKILL.md`
- `skills/auto-brainstorming/SKILL.md`
- `skills/worktree-merge-back/SKILL.md`
- `commands/fast-tasks.md`

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 6곳 한 곳 boilerplate 누락 | 그 흐름에서 사용자 모호 응답 → 메인이 fall-through → 사용자 질문 씹힘 |
| "anchor 질문 강제 X" 룰 확대 해석 | yes/no 명확 답변 외 (Other 포함) 모두 추가 clarify 안 함 → 회귀 |

### 영향 범위

- 6곳 본문 변경. 다른 skill / og-* / auto-* (auto-brainstorming 외) 영향 0
- AskUserQuestion 도구 schema 변경 X (호출 패턴만 추가)
- Notification.elicitation_dialog 매처 / repeat-alert.sh — 변경 X

### Regression catch grep

```bash
grep -cE "^#+ Other / 모호 응답 처리 \(v2\.1\.1\+\)" \
  skills/brainstorming/SKILL.md \
  skills/tech-design/SKILL.md \
  skills/writing-plans/SKILL.md \
  skills/auto-brainstorming/SKILL.md \
  skills/worktree-merge-back/SKILL.md \
  commands/fast-tasks.md
# expected: 각 1 (6곳 모두 박혀 있어야 함)
```

요약: 6 파일 + CLAUDE.md 결합 메모 변경은 묶어서 처리. 7+ 파일 atomic patch.

요약: 8 skill body + CLAUDE.md 결합 메모 변경은 묶어서 처리. 5+ 파일 atomic patch.

## AskUserQuestion 도구 우선 (v2.3.5+)

메인 에이전트가 사용자에게 **결정 / 선택 / 동의** 를 요청하는 모든 경우 → **AskUserQuestion 도구 호출** default. skill body 외 ad-hoc 결정에도 동일 적용.

### 적용 대상

- 모든 skill body 안 게이트 (기존 v2.0.3+ 8 skill boilerplate)
- 메인 turn 의 ad-hoc 결정 요청 (skill body 무관)
- v2.3.5+ execute-plan 룰 1 (critical 7 케이스) 재질문
- 사용자가 모호 응답 시 재질문 (v2.1.1+ Other 룰)
- 실행 모드 선택 게이트 진입 시점
- BLOCKED → self-correct / reorder 도 실패 시 사용자 개입

### prose 예외 (좁게)

- 자유 텍스트 / 긴 응답 요구 (open brainstorming question 등)
- `/tech-teach-me` 커맨드 안 (명시 예외 — 강마다 팝업이 학습 흐름을 끊어 자유 입력으로 받는다. "/tech-teach-me 결합 메모" 참조)
- 사용자 응답 직후 확인용 단순 ack (단 AskUserQuestion yes/no 권장)
- 상태 보고 / 진행 알림 (질문 형식 아님)

### 사용자 환경 전달 캐리어 (v2.8.0+)

본 룰의 전역 (ad-hoc) 적용은 `skills/using-superpowers/SKILL.md` 의 "User Decisions — AskUserQuestion First (v2.3.5+)" 섹션이 사용자 환경 캐리어 — `hooks/session-start` 가 매 세션 주입하는 유일한 상시 파일. skill body boilerplate (8 skill) 는 게이트 레벨만 커버. executing-plans / js-super-sub-driven 의 cross-reference 는 using-superpowers 를 가리킨다 (사용자 프로젝트에 본 CLAUDE.md 는 로드되지 않음 — dangling reference 금지).

### 알람 fire 보장

`AskUserQuestion` 호출 → `Notification.elicitation_dialog` 발화 → `~/.claude/settings.json` 매처 → `repeat-alert.sh` fire. 사용자 백그라운드 작업 시 OS 알람 catch → 응답 흐름 보존.

prose 질문은 알람 fire X — 사용자 attention 손실 위험.

회귀 catch grep:

```bash
grep -c "AskUserQuestion 도구 우선 (v2.3.5+)" CLAUDE.md
# expected: ≥ 1

grep -c "User Decisions — AskUserQuestion First (v2.3.5+)" \
  skills/using-superpowers/SKILL.md \
  skills/executing-plans/SKILL.md \
  skills/js-super-sub-driven/SKILL.md
# expected: 각 1

grep -Fn '글로벌 "AskUserQuestion 도구 우선' \
  skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 0 (v2.8.0+ — cross-reference 는 using-superpowers 를 가리켜야 함, CLAUDE.md 참조는 dangling)
```

## execute-plan critical/non-critical + AskUserQuestion 강제 결합 (v2.3.5+)

v2.3.5+ 에서 `skills/executing-plans/SKILL.md` + `skills/js-super-sub-driven/SKILL.md` + `CLAUDE.md` 3 파일 atomic patch. v2.8.0+ 부터 `skills/using-superpowers/SKILL.md` (전역 룰의 사용자 환경 캐리어) 포함 4 파일. 한쪽만 변경 시 inline vs subagent 모드 동작 불일치 + 글로벌 vs skill body 룰 불일치.

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| executing-plans 만 변경 | inline 흐름은 critical 판정 가능 / subagent 흐름은 옛 과보호 게이트 그대로 |
| js-super-sub-driven 만 변경 | 반대 |
| CLAUDE.md 만 변경 | skill body 안 boilerplate 누락 — 흐름 안에서 ad-hoc prose 질문 잔존 |
| 룰 1 critical 표 일부 누락 | catch 못 한 케이스에서 자동 진행 → blast radius 위험 |
| 룰 2 non-critical 표 누락 | "안전성" 명목 게이트 회귀 |
| 룰 4 자가 복구 누락 | BLOCKED 시 즉시 사용자 재질문 → 알람 burst |
| using-superpowers 캐리어 누락 (v2.8.0+) | ad-hoc 전역 룰이 사용자 환경에 미전달 — skill 흐름 밖 prose 질문 회귀 |
| skill body cross-reference 가 CLAUDE.md 를 가리킴 | 사용자 프로젝트엔 본 CLAUDE.md 없음 → dangling reference |

### 영향 범위

- 4 파일 atomic patch (위 표, v2.8.0+ using-superpowers 포함). 다른 skill / commands / scripts 영향 0
- v1.1.12+ 자동승인 X / v2.0.0+ byte-copy reorder / v2.0.1+ same-file 묶음 / v2.0.3+ 8 skill boilerplate / v2.1.1+ Other 룰 — 모두 그대로
- 알람 시스템 (`repeat-alert.sh` 4-layer) — fire 빈도만 정상화 (변경 X)
- og-* / auto-* — Socratic only 룰 보존 (auto-* 는 본 룰 명시 예외 — Socratic prose default 유지)
- writing-plans `**Model**:` 필드 — 룰 2 의 dispatch model 결정 근거 (변경 X)
- `scripts/preflight.py` / `scripts/plan_byte_check.py` — 실행 단계 룰만이라 영향 0

### Regression catch grep

```bash
grep -c "Critical / Non-critical 판정 룰 (v2.3.5+)" \
  skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 각 1

grep -c "사용자 질문 = AskUserQuestion 도구 (v2.3.5+)" \
  skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 각 1

grep -nE "병렬.*해도.*될까|묶을까|다음 task.*진입할까" \
  skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 0 (Anti-Pattern catch 라인만 허용)

grep -nE "이렇게.*할까요\?|어느.*쪽.*인가요\?" \
  skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 0 (Anti-Pattern catch 라인만 허용)
```

요약: 4 파일 (executing-plans/SKILL.md + js-super-sub-driven/SKILL.md + using-superpowers/SKILL.md + CLAUDE.md) atomic patch. 6+ 파일 동시 push (4 + 6 manifest + 백로그 mv).

## 한국어 친화 안내 톤 (v2.4+)

js-super 의 사용자 노출 안내문 (메인이 사용자에게 직접 보여주는 모든 문구) 은 다음 룰을 따른다.

### A-1: 짧은 한국어 문장

- 한 문장에 정보 1~2개. 한 문단은 4 문장 이하.
- 영어 식별자는 꼭 필요할 때만 사용하고, 처음 등장 시 한국어 설명을 함께 적는다.

### A-2: 메모 / 슬래시 / 콜론 다발 금지

- 사용자에게 보고할 때는 완전 문장으로 쓴다. `→`, `✅` 같은 마커는 진행 노트 한 줄 안에서만 허용.
- 콜론 다발 (`결과: X / 다음: Y`) 보다 풀어쓰기를 우선.

### A-3: 한국어-영어 mix 최소

- 사용자 시야에 보이는 표현은 한국어 우선.
- 시스템 용어도 가능한 한 한국어로 풀어쓴다:
  - `fire-and-forget` → `백그라운드 호출`
  - `dispatch` → `호출`
  - `byte-copy` → `원본 그대로 보존`
  - `wave-parallel` → `여러 작업 동시 진행`
  - `override` → `자동 통과` 또는 `덮어쓰기` (맥락 따라)
  - `subagent` → `보조 에이전트`
  - `Anti-Pattern` → `안티 패턴` 또는 `금지 패턴`
  - `Gate #N` → `승인 게이트` (번호 자체가 사용자에게 의미 없으면 번호 생략)
- 도구 / 함수 / 파일 이름 (`AskUserQuestion`, `parse_interrupt`, `plan_byte_check` 등) 은 영어 그대로 유지.
- 단순 git 용어 (`commit`, `push`, `merge`, `tag`) 도 영어 그대로 유지.

### A-4: 사용자 친화 보고

- 무엇을 했는지 (1~2 문장) + 왜 그랬는지 (필요 시 1 문장) + 다음 단계 (1 문장).
- 그 외 세부는 사용자가 자세히 묻기 전까지 생략.

### A-5: 적용 영역 구분 (중요)

| 영역 | 한국어 친화 톤 적용 |
|---|---|
| skill body 의 식별자, 함수 / 파일 이름 | 영어 그대로 (변경 X) |
| skill body 의 룰 본문 (Why / How / Anti-Patterns 표) | 영어 그대로 (변경 X) — 메인 prompt 가공용 |
| skill body 의 사용자 노출 안내문 (메인 turn 에 그대로 출력) | 한국어 친화 적용 |
| CLAUDE.md 의 글로벌 톤 룰 | 한국어로 추가 (본 섹션) |
| 메인이 사용자에게 보고하는 응답 양식 | 한국어 친화 적용 |
| commands/*.md 사용자 안내문 | 한국어 친화 적용 |
| README.md 사용자 안내 섹션 | 한국어 친화 적용 |

### Before / After 예시

❌ Before (영어-한국어 mix + 메모 패턴):

> `✅ fire-and-forget dispatch 완료. byte-copy 룰 보존. → 다음 단계 진행.`

✅ After (한국어 친화):

> 백그라운드 호출이 끝났습니다. 원본 보존 룰을 그대로 따랐고, 다음 단계로 넘어갑니다.

회귀 catch grep:

```bash
grep -c "한국어 친화 안내 톤 (v2.4+)" CLAUDE.md
# expected: ≥ 1
```

## --no-ask 플래그 ↔ 8 skill body 결합 (v2.5+)

`--no-ask` 플래그는 8 skill body 의 분기 sub-section 으로 구현. 사용자가 슬래시 명령에 `--no-ask` 토큰 명시 시에만 진입. 메인 자체 판단 활성화 X.

### 적용 범위 (8 skill)

- anchor 본격 4 (brain / design / write / auto-brain): "사용자 질문 룰" 섹션 직후 sub-section
- anchor 짧은 reference 4 (executing / auto-design / auto-write / auto-execute): body 끝 sub-section
- og-* / fast-tasks / worktree-merge-back — 비적용 (회귀 catch grep 으로 보장)

### 핵심 룰

- 도구 호출 0 보장 (AskUserQuestion 흐름 전 구간 호출 X)
- 게이트 자체는 살아 있음 (질문은 그대로, 도구만 우회)
- skill 진입 시 1회 boilerplate prose (`ℹ️ --no-ask 모드 진입 ...`)
- 위험 명령 진입 직전 prose 보강 (`⚠️ 위험 명령 진입 — 응답 기다림`)
- auto-* 4 의 내부 escalation 경로 (BLOCKED 자가복구 / critical 7 재질문 / Other 모호 응답) 도 도구 호출 0 보장

### 회귀 catch grep (release 직전 메인 dogfood)

```bash
grep -c -E "no-ask.? 플래그 \(v2\.5\+\)" \
  skills/brainstorming/SKILL.md \
  skills/tech-design/SKILL.md \
  skills/writing-plans/SKILL.md \
  skills/executing-plans/SKILL.md \
  skills/auto-brainstorming/SKILL.md \
  skills/auto-tech-design/SKILL.md \
  skills/auto-writing-plans/SKILL.md \
  skills/auto-executing-plans/SKILL.md
# expected: 각 ≥ 1

grep -l -e "--no-ask" \
  commands/og-brainstorm.md \
  commands/og-write-plan.md \
  commands/og-execute-plan.md \
  commands/fast-tasks.md \
  skills/worktree-merge-back/SKILL.md 2>/dev/null
# expected: empty
```

요약: 8 skill body 분기 + 8 commands 안내 + CLAUDE.md 결합 메모 + 6 manifest bump = 23 파일 atomic patch.

## worktree cleanup 자동화 결합 (v2.5.1+)

v2.5.1+ 에서 `worktree-merge-back` 자동화 강화 + `worktree-remove` 신규 슬래시 명령 도입.

### 적용 범위 (5 본문 + 6 manifest = 11 파일)

- `skills/worktree-merge-back/SKILL.md` — Step 3 머지 대상 변경 (origin → 로컬) + 충돌 처리 완화 (재귀 머지 자동) + Step 4.5 신규 (env 동기화) + Step 5 보강
- `commands/merge-back-worktree.md` — 안내 동기화
- `skills/worktree-remove/SKILL.md` — 신규
- `commands/remove-worktree.md` — 신규
- `CLAUDE.md` — v2.0.4+ Anti-Pattern 표 v2.5.1+ 분기 + 본 섹션
- 6 manifest — 버전 2.5.1

### 핵심 룰

- **D-1 머지 대상** = parent 워크트리의 로컬 브랜치 (origin 자동 fetch X). 사용자가 remote 동기화 원하면 진입 전 별도 `git fetch` + pull
- **D-2 충돌 처리** = git default 재귀 머지 자동 + 실제 conflict marker 만 사용자 prose 안내. `--strategy ours/theirs` 자동 적용 절대 X (v2.0.4+ 안전성 유지)
- **D-3 env 파일 동기화** = LLM 변경 의미 판단 + 각 파일 1줄 prose 보고 + 선택적 cp (`cp -P` symlink 보존). silent cp 절대 X
- **D-4 worktree-remove** = 독립 슬래시 명령 (chain X). worktree-merge-back 의 Step 5 종료 메시지에 호출 안내만
- **D-5 HARD-GATE worktree-only** = 두 skill 모두 유지 (main 워크트리 차단). 안전성 핵심
- **D-6 worktree-remove 브랜치 삭제 default** = 부모 기준 머지 확인을 통과한 브랜치만 삭제. 판정 기준은 `branch.<이름>.js-super-parent` 기록이고, 없으면 최상위 브랜치로 대체한다. `--force` 옵트인 플래그 명시 시만 확인 없이 삭제
  - 최상위에서 `git branch -d` 로 판정하면 안 된다. `-d` 는 실행 위치의 HEAD 를 기준으로 보므로, 부모로만 머지된 재분기 브랜치 (`부모__자식` → `부모`) 를 미머지로 오판해 차단하고 사용자를 `--force` 로 몬다. `merge-base --is-ancestor` 로 부모 기준 확인을 마친 뒤 삭제하므로 안전성은 `-d` 와 같다

### 회귀 catch grep (release 직전, `-F` fixed string 표준)

```bash
# D-1: origin 흡수 제거
grep -nE "git fetch origin|origin/\\\$MAIN_BRANCH" skills/worktree-merge-back/SKILL.md
# expected: 0 (Anti-Pattern catch 라인 / 안내 sentence 외)

# D-2: 재귀 머지 표현 존재
grep -F "git default 재귀 머지" skills/worktree-merge-back/SKILL.md
# expected: >= 1

# D-3: Step 4.5 env 동기화 존재
grep -F "Step 4.5" skills/worktree-merge-back/SKILL.md
# expected: >= 1

# D-4: worktree-remove 신규 파일 존재
test -f skills/worktree-remove/SKILL.md && test -f commands/remove-worktree.md
echo $?
# expected: 0

# D-5: HARD-GATE 두 skill 모두
grep -F "HARD-GATE — Worktree-Only" skills/worktree-merge-back/SKILL.md skills/worktree-remove/SKILL.md
# expected: 각 1

# D-6: default safe + --force 옵트인
grep -nE "git branch -d|safe \(-d\)|--force" skills/worktree-remove/SKILL.md
# expected: >= 2
```

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| skill body 만 변경 | `/merge-back-worktree` 슬래시 명령 본문이 옛 표현 유지 → 사용자 혼란 |
| commands 만 변경 | 메인이 skill body 따라 옛 글롭 적용 → env 동기화 누락 |
| worktree-remove skill 만 신규 | 슬래시 명령 부재 → 사용자 진입 X |
| HARD-GATE 한쪽 누락 | main 워크트리에서 호출 시 안전성 핵심 손상 |
| `--force` 자동 적용 | 머지 안 된 브랜치 강제 삭제 → 데이터 손실 |

### 영향 범위

- 5 본문 + 6 manifest. 다른 skill / commands / scripts 영향 0
- `setting-up-worktrees` / `finishing-a-development-branch` / `auto-*` / `og-*` 영향 0
- `scripts/preflight.py` / `scripts/auto_flow.py` 영향 0
- 자동 발동 경로 없음 — 명시 invoke 만

요약: 5 본문 + 6 manifest + CLAUDE.md 결합 메모 변경은 atomic patch (Wave 0~5 + spec + [log] 묶음 commit).

## TaskCreate Checklist ↔ 9 skill body 결합 (v2.5.2+)

v2.5.2+ 에서 9 skill body 에 `## Checklist` 섹션 신규 추가 — `using-superpowers` 의 "Has checklist? yes → TaskCreate per item" 분기 자동 발동 보장. 사용자 시야에 진행 상황 자동 노출.

### 적용 범위 (9 skill)

- **auto-* 4** — `auto-brainstorming`, `auto-tech-design`, `auto-writing-plans`, `auto-executing-plans` (auto-flow 4 단계)
- **반쪽 페어 1** — `executing-plans` (writing-plans 페어, v2.5.1 까지 비대칭이었음)
- **cascading 1** — `change-propagation` (impact matrix → 갱신 cascading)
- **subagent 1** — `js-super-sub-driven` (Wave 별 진행)
- **og-* 2** — `og-writing-plans`, `og-executing-plans` (upstream mirror 룰 예외 — 아래 참조)

### 비적용 영역 (의도적 제외)

- `og-brainstorming` — 이미 Checklist 보유 (upstream 그대로 답습)
- 워크트리 2 (`worktree-merge-back`, `worktree-remove`) — Step 수 적음, 사용자 catch 우선순위 낮음
- `finishing-a-development-branch`, `subagent-driven-development` — 사용자 의사 미선택
- 1회성 / 메타 skill — `change-history`, `risk-annotation`, `verifying-spec`, `using-superpowers` 등 (task 분해 의미 없음)

### og-* mirror 룰 예외 (D-4)

`og-writing-plans` / `og-executing-plans` 는 upstream `superpowers` 5.0.7 mirror — 본문 변경 절대 X 가 기본 룰 (다른 CLAUDE.md 섹션에 명시). v2.5.2+ 가 이 룰의 명시 예외:

- **Checklist 섹션 한정 추가만 예외**. 다른 영역 (Procedure / Anti-Patterns / Related Skills / 영어 식별자 / 본문 룰) 변경 절대 X
- 향후 upstream 본문 변경 시 mirror 답습은 그대로. Checklist 섹션만 js-super 고유 추가로 유지

### 핵심 룰

- Checklist 항목 형식: `- [ ] Step N — <헤더 + 짧은 요약 1줄>`
- 위치: 각 skill body 의 `## Process` 섹션 직전
- 신규 분기 / 신규 도구 호출 패턴 도입 X — 기존 Process 흐름을 사용자 시야에 노출하는 단순 패턴
- 메인 행동 변화: TaskCreate 도구 호출이 자동 발동 (v2.5.1 dogfood 세션에서 사용자 catch — "왜 태스크 생성안하고 했어?")

### Process Step 헤더 ↔ Checklist 항목 동기화 룰 (R-4)

각 skill body 의 Process Step 헤더 변경 시 Checklist 항목 본문도 동기화 필수. drift 회귀 catch grep:

```bash
# 각 skill 의 Step 헤더 ↔ Checklist 항목 매치
for f in skills/auto-brainstorming/SKILL.md skills/auto-tech-design/SKILL.md \
         skills/auto-writing-plans/SKILL.md skills/auto-executing-plans/SKILL.md \
         skills/executing-plans/SKILL.md skills/change-propagation/SKILL.md \
         skills/js-super-sub-driven/SKILL.md; do
  echo "=== $f ==="
  echo "-- Process Step 헤더 --"
  grep -E "^### Step [0-9]" "$f"
  echo "-- Checklist 항목 --"
  grep -E "^- \[ \] Step [0-9]" "$f"
done
```

### 회귀 catch grep (release 직전, `-F` fixed string)

```bash
# 9 skill 모두 ## Checklist 섹션 존재
grep -lF "## Checklist" \
  skills/auto-brainstorming/SKILL.md \
  skills/auto-tech-design/SKILL.md \
  skills/auto-writing-plans/SKILL.md \
  skills/auto-executing-plans/SKILL.md \
  skills/executing-plans/SKILL.md \
  skills/change-propagation/SKILL.md \
  skills/js-super-sub-driven/SKILL.md
# expected: 7 lines (모두 매치 — og 2종은 v2.8.1 에서 스킬 삭제)

# og-* mirror 룰 예외 명시
grep -cF "og-* mirror 룰 예외" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- 10 본문 (9 skill + CLAUDE.md) + 6 manifest. 다른 skill / commands / scripts 영향 0
- `using-superpowers` 본문 변경 X (기존 "Has checklist?" 분기 답습)
- TaskCreate 도구 schema 변경 X (호출 빈도만 ↑)
- Notification 매처 / repeat-alert.sh — 변경 X
- AskUserQuestion / `--no-ask` 플래그 / 8 skill body 결합 (v2.5+) — 영향 0

요약: 10 본문 + 6 manifest = 16 파일 atomic patch (Wave 0~2 + spec + [log] 묶음 commit).

## /new-skill 빌더 결합 (v2.6.0+)

v2.6.0+ 에서 `commands/new-skill.md` 신규 추가 — 자유 텍스트 한 줄을 받아 글로벌 `~/.claude/skills/<slug>/SKILL.md` 1 파일로 자동 생성하는 instruction-only 슬래시 명령. js-ralph 의 `/expand-plan` 패턴 답습 (instruction-only, bash 호출 없음, frontmatter + 본문 instruction).

### 적용 범위 (1 파일)

- `commands/new-skill.md` — 신규 (frontmatter + 8 섹션 본문)
- 다른 skill / commands / scripts / hooks 영향 0

### 핵심 룰

- **instruction-only** — bash 호출 없음. Read / Edit / Write 도구만 사용. 메인 latency 거의 0
- **글로벌 출력** — `~/.claude/skills/<slug>/SKILL.md` 로 Write. 사용자 PC 의 다른 플러그인 / 프로젝트 skill 디렉토리는 검증 대상 X (D-T4 — 빌더 latency 보존)
- **LLM 분해 5 단계** — 트리거 조건 추출 / 수행 동작 추출 / 슬러그 자동 생성 / user-invocable 결정 / 충돌 검증 (D9)
- **description 휴리스틱 3건 (D7)** — max 120자 auto trim (강제) + "Use when" 패턴 warn + 동사 시작 warn
- **`--force` 시 백업** (`SKILL.md.bak-<timestamp>`) — 사용자 회수 가능 (D-T5)
- **step 수 권장 1~7** — bite-size 룰 (D-T2). 8+ 시 alert
- **비밀값 / 토큰 / 하드코딩 경로 catch 시 abort** — 자유 텍스트 그대로 박힘 방지 (R-4)
- **빌더 자체는 command** — skill 로 만들면 자동 발동 사고 위험 (D8, META-BUILDER §5)

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| LLM 분해 5 단계 룰 약화 | 자유 텍스트 의도 미스 → 잘못된 trigger / 동작 박힘 (R-1) |
| `--force` 백업 룰 약화 | 사용자 실수 시 복구 X (R-2 안전성 손상) |
| description 휴리스틱 비활성 | 긴 description → 자동 발동 게이트 비용 ↑ / 오발동 (R-3) |
| 비밀값 catch 비활성 | 사용자 PC 글로벌 skill 에 비밀값 누적 (R-4 보안) |
| skill 로 빌더 변환 | 자동 발동 사고 ("대화 중에 안 부탁했는데도 발동") (D8 위반) |
| 다른 위치 충돌 검증 추가 | 빌더 latency ↑ — D-T4 단순성 위배 |
| 한국어 친화 톤 미적용 | js-super 톤 불일치 (v2.4+ A-1~A-5 위배) |

### 회귀 catch grep

```bash
# 빌더 본문 존재 + 핵심 섹션 확인
test -f commands/new-skill.md && grep -cF "## 3. LLM 분해 (5 단계)" commands/new-skill.md
# expected: >= 1

# 결합 메모 본문 존재
grep -cF "## /new-skill 빌더 결합 (v2.6.0+)" CLAUDE.md
# expected: >= 1

# 안티 패턴 — skill 로 빌더 변환 catch (skills/ 안에 동일 이름 X)
test ! -d skills/new-skill && echo "OK: 빌더가 skill 로 안 박힘"
# expected: OK
```

### 영향 범위

- 1 파일 (`commands/new-skill.md`) 신규. 다른 skill / commands / scripts / hooks / settings 영향 0
- 사용자 환경 출력 (`~/.claude/skills/<slug>/SKILL.md`) — js-super 저장소 외, 사용자가 빌더 실행 시점에 Write
- expand-plan.md (js-ralph) 패턴 답습 — js-super 저장소 안 다른 변경 X
- `using-superpowers` 본문 변경 X (글로벌 skill 자동 발동 메커니즘 그대로 활용)

요약: 1 본문 (`commands/new-skill.md`) + CLAUDE.md 결합 메모 + 6 manifest = 8 파일 atomic patch (Wave 0~2 + spec + [log] 묶음 commit).

### v2.6.1+ 분기 — critical 3건 patch (release 직후 회수)

v2.6.0 push 직후 메인 검토에서 catch 한 3 항목 patch. 의미 변경 아니라 본문 표현 정정 + 명시화.

| Patch | 위치 | 변경 의도 |
|---|---|---|
| A description 좁히기 | `commands/new-skill.md` frontmatter description | "사용자가 `/new-skill` 슬래시를 명시 호출했을 때만 발동" 톤 우선 → 평상 대화 중 자동 발동 위험 catch 약화 (R-3 완화 — 100% 보장 X) |
| B step 폭주 alert 정정 | `commands/new-skill.md` § 3-2 | `--force` 잘못 인용 제거. "다시 호출 / 두 번 호출" 2 옵션 명확 (R-4 완화) |
| C `--force` 백업 instruction 명시화 | `commands/new-skill.md` § 5-3 | Read → Write bak → Write 덮어쓰기 3 step 명시 (R-5 완화 — Claude 도구 흐름 정확) |

회귀 catch grep (release 직전 메인 dogfood):

```bash
# Patch A — 명시 호출 톤
grep -F "명시 호출" commands/new-skill.md
# expected: >= 1

# Patch B — alert 메시지 정정 + --force 잘못 인용 제거
grep -F "분리하려면 자유 텍스트를" commands/new-skill.md
# expected: >= 1

# Patch C — 3 step 명시
grep -F "Read 도구로" commands/new-skill.md
# expected: >= 1
```

## /remove-skill 빌더 결합 (v2.6.1+)

v2.6.1+ 에서 `commands/remove-skill.md` 신규 추가 — 글로벌 `~/.claude/skills/<slug>/` 디렉토리를 안전하게 정리하는 instruction-only 슬래시 명령. `/new-skill` 짝 명령.

### 적용 범위 (1 파일)

- `commands/remove-skill.md` — 신규 (frontmatter + 6 섹션)
- 다른 skill / commands / scripts / hooks 영향 0

### 핵심 룰

- **safe-rename default** — `~/.claude/skills/<slug>/` → `~/.claude/skills/<slug>.removed-<YYYYMMDDHHMMSS>/` rename. 회복 가능 (D-T1)
- **`--force` 옵트인 hard-delete** — Bash 도구 `rm -rf` 호출. 회복 불가 (D-T2)
- **`--dry-run` preview** — 변경 X, 메인 응답에 안내만 (D-T3)
- **부재 시 abort + 글로벌 skill 목록 안내** (R-7 완화)
- **timestamp `YYYYMMDDHHMMSS` 단위 unique** (R-8 완화)
- **`/reload-plugins` 호출 안내** — rename 만으로 자동 발동 차단 보장 X 명확 (R-1 완화, 사용자 catch 영역)
- **다른 위치 (`<plugin>/skills/` / 프로젝트 `.claude/skills/`) 검증 X** — 빌더 latency 보존, 사용자 catch 영역

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| safe-rename default 약화 (예: hard-delete default) | 사용자 실수 시 데이터 손실 (R-2 안전성 손상) |
| `--force` 옵트인 X (default 적용) | 동일 — 데이터 손실 |
| `/reload-plugins` 안내 누락 | 사용자 rename 후 자동 발동 차단 catch X (R-1 회귀) |
| 부재 시 글로벌 skill 목록 안내 누락 | 사용자가 slug 오타 catch X (R-7 회귀) |
| timestamp 형식 다른 값 (예: ISO 8601) | `.removed-*` 디렉토리 충돌 가능 (R-8 회귀) |

### 회귀 catch grep

```bash
# 빌더 본문 존재
test -f commands/remove-skill.md && echo "OK"
# expected: OK

# safe-rename default 명시
grep -F "safe-rename" commands/remove-skill.md
# expected: >= 1

# /reload-plugins 안내 (R-1 완화)
grep -F "/reload-plugins" commands/remove-skill.md
# expected: >= 1

# 결합 메모 본문 존재
grep -cF "## /remove-skill 빌더 결합 (v2.6.1+)" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- 1 파일 (`commands/remove-skill.md`) 신규. 다른 skill / commands / scripts / hooks / settings 영향 0
- 사용자 환경 출력 — `~/.claude/skills/<slug>/` rename (또는 rm -rf). js-super 저장소 외
- `/new-skill` 짝 명령 — 같이 사용하는 워크플로우 (만들기 → 정리하기)
- `using-superpowers` 본문 변경 X

요약: 1 본문 (`commands/remove-skill.md`) + `commands/new-skill.md` 3 patch + CLAUDE.md 결합 메모 (v2.6.1+ 분기 + 신규 섹션) + 6 manifest = 9 파일 atomic patch (Wave 0~3 + spec + [log] 묶음 commit).

## new-skill-enhanced — 스코프 분기 + 출처 표식 결합 (v2.7+)

v2.7+ 에서 skill 빌더 3종 고도화. `/new-skill` 생성 스코프(프로젝트/전체) 분기 + 출처 표식 마커 도입, `/remove-skill` 출처 한정 삭제, 신규 `/list-skills` 출처 한정 조회. spec: `docs/features/2026-05-31-new-skill-enhanced/`.

### 출처 표식 규약 (핵심 — 3 command 공유)

`/new-skill` 이 생성 시 skill 디렉토리에 `.js-super-skill.json` 마커 파일을 함께 작성한다:

```json
{"generated_by": "js-super:new-skill", "scope": "<project|global>", "created": "<ISO ts>"}
```

판별 규칙: **어떤 skill 이 "js-super 가 만든 것" ⇔ 그 디렉토리에 `.js-super-skill.json` 존재.** `/list-skills` 필터 기준 + `/remove-skill` 차단 기준. 이 규약을 바꾸면 3 command 동시 수정 (한쪽만 바꾸면 생성 마커와 조회/삭제 판별이 desync).

### 적용 범위 (3 본문 + 6 manifest = 9 파일)

- `commands/new-skill.md` (수정) — `--project`/`--global` 플래그 + § 2.5 스코프 결정(미지정 시 prose 질문, 조용한 기본값 없음) + `<SKILL_BASE>` 경로 일반화 + § 5 마커 작성
- `commands/remove-skill.md` (수정) — 프로젝트+전체 양쪽 탐색 + § 4-0 마커 차단 게이트(`--force` 로도 우회 X) + § 4-0' 모호 처리 + § 5-5 차단 보고
- `commands/list-skills.md` (신규) — 두 스코프 스캔 + 마커 필터 + 스코프 라벨 + 프로젝트 경로 표시
- `CLAUDE.md` (본 섹션)
- 6 manifest — 2.6.2 → 2.7.0

### 핵심 룰

- **D-1 마커 = 출처 표식** — frontmatter 필드(로더 호환 리스크) / 중앙 manifest(desync) 대신 디렉토리 안 마커 파일 채택. `test -f` 만으로 deterministic 판별. (당시 근거였던 FR-2 "다른 프로젝트 안 보임" 은 스킬목록-전체프로젝트조회 피처에서 폐지됐지만, 마커 채택 결론은 그대로 유효하다 — 오히려 홈 전체 조회의 판별 기준이 된다)
- **D-2 생성 스코프 미지정 시 질문** — 조용한 기본값 없음 (사용자가 매번 프로젝트/전체 선택)
- **D-3 삭제 범위 = 현재 프로젝트 cwd `.claude/skills` + 전체** — 조회는 스킬목록-전체프로젝트조회 피처 (2026-08-16) 로 홈 전체로 확장됨 (아래 "스킬목록 홈 전체 조회 결합" 참조). 삭제는 그대로 두 스코프 (중앙 레지스트리 없음)
- **D-4 삭제 차단은 `--force` 로도 우회 X** — 마커 부재 = 무조건 차단 (핵심 안전 게이트)
- **D-5 빌더 3종 모두 command** — `skills/` 아래 변환 X (자동 발동 사고 방지, META-BUILDER 룰 답습)
- **D-6 마커는 신뢰 신호일 뿐 보안 경계 아님** — 수동 복사 위조 가능, 낮은 빈도 수용

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| new-skill 마커 작성 누락 | 생성한 skill 이 `/list-skills` 에 안 뜨고 `/remove-skill` 로도 못 지움 |
| remove-skill § 4-0 차단 게이트 약화 | 비-js-super skill 삭제 가능 → v2.7 핵심 안전성 손상 |
| `--force` 가 마커 게이트 우회 | 동일 — 안전성 손상 |
| list-skills 조회가 두 스코프 (cwd + 글로벌) 로 회귀 | 홈 전체 조회 피처 (2026-08-16, FR-2 공식 폐지) 무력화 — "스킬목록 홈 전체 조회 결합" 참조 |
| 마커 규약 키(`generated_by`) 한 command 만 변경 | 생성 마커와 조회/삭제 판별 desync |

### 회귀 catch grep

```bash
# 3 command 마커 규약 공유
grep -lF ".js-super-skill.json" commands/new-skill.md commands/remove-skill.md commands/list-skills.md
# expected: 3 lines

# remove-skill 차단 게이트 존재
grep -F "4-0. 출처 표식 검사" commands/remove-skill.md
# expected: >= 1

# new-skill 스코프 결정 단계
grep -F "2.5. 스코프 결정" commands/new-skill.md
# expected: >= 1

# list-skills 신규 + 빌더=command 룰
test -f commands/list-skills.md && test ! -d skills/list-skills && echo OK
# expected: OK

# 결합 메모 본문 존재
grep -cF "## new-skill-enhanced — 스코프 분기 + 출처 표식 결합 (v2.7+)" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- 3 command 본문 + CLAUDE.md + 6 manifest. 다른 skill / scripts / hooks / settings 영향 0
- 사용자 환경 출력 — `<project-root>/.claude/skills/` 또는 `~/.claude/skills/` (js-super 저장소 외)
- `using-superpowers` 본문 변경 X
- 범위 밖: 비-js-super 강제 삭제 우회 / 옛 마커 없는 skill 마이그레이션 / 다른 프로젝트 삭제 (조회는 스킬목록-전체프로젝트조회 피처로 이후 채택됨)

요약: 3 command 본문 + CLAUDE.md 결합 메모 + 6 manifest = 10 파일 atomic patch (Wave 0~5 + spec + [log] 묶음 commit).

## /goodnight + /goodmorning 결합 (v2.8.0+) — v2.9.0 에서 단일화로 대체

v2.8.0 에서 세션 핸드오프 커맨드 2종(`/goodnight` 저녁 저장 + `/goodmorning` 아침 브리핑)을 추가했으나, **v2.9.0 에서 `/goodnight` 를 삭제하고 `/goodmorning` 하나로 통합**했다. git 상태·진행 문서·세션 기록은 아침에도 그대로 남아 있어 저녁 저장 단계가 불필요했고, 저녁 실행을 깜빡하면 다음날 브리핑이 비는 문제도 있었다 (사용자 결정). 현행 룰은 아래 "/goodmorning 단일화" 섹션 참조. spec `docs/features/2026-07-18-미라클모닝/` 은 v2.8.0 당시 기록으로 보존 (단일화는 spec 캐스케이드 없이 커맨드 직접 개편 — 사용자 결정).

## /goodmorning 단일화 — /goodnight 흡수 (v2.9.0+)

v2.9.0+ 에서 `/goodnight` 삭제 + `/goodmorning` 자급형 개편. 수집(워크트리별 병렬 보조 에이전트 + 위험 자동 판정)을 goodmorning 실행 시점으로 이동해 수집 직후 브리핑까지 한 번에 처리한다.

### 적용 범위 (커맨드 1 삭제 + 1 재작성 + CLAUDE.md = 3 파일)

- `commands/goodnight.md` — 삭제
- `commands/goodmorning.md` — 자급형 재작성 (수집 + 위험 판정 + 브리핑 + 노트 저장)
- `CLAUDE.md` (본 섹션 + v2.8.0 섹션 압축)
- 6 manifest 버전 bump 는 dev 가 릴리즈 시점에 main 에서 직접 (에이전트가 임의로 올리지 않음 — "버전 bump 는 main 전용" 룰 참조)

### 핵심 룰 (v2.8.0 D 룰 승계 + 신규)

- **E-1 실행 위치 자유 + 최상위 기준** — 어느 워크트리에서 실행해도 됨. 수집 대상 열거와 노트 저장 위치는 항상 `git worktree list` 첫 줄(최상위) 기준. v2.8.0 D-1 의 "최상위 전용 가드"는 저녁 저장 커맨드가 사라지며 필요 없어짐
- **E-2 병렬 보조 에이전트 수집 유지** (D-2 승계) — 워크트리당 보조 에이전트 1, 메인은 요약만 취합 (세션 원문 직접 읽기 금지)
- **E-3 위험 자동 판정 유지** (D-3 승계) — 체크리스트 판정, 위험 있을 때만 배너, 없으면 담백
- **E-4 노트 저장 유지** (D-4 승계) — 브리핑 결과를 최상위의 `.js-super/session-handoff/YYYY-MM-DD.md` 에 저장 (같은 날 덮어쓰기, gitignore 수정 불필요). 저장 시점만 저녁 → 아침으로 이동
- **E-5 출력 스타일 유지** (D-5 승계) — 비유법 금지 + 불필요한 용어 병기 금지 + 명확한 한국어
- **E-6 자동 발동 차단 유지** (D-6 승계) — `disable-model-invocation: true`, description 에 발동 조건 문구 X
- **E-7 뒤처진 워크트리 제외 (신규)** — behind ≥ 1 이고 ahead = 0 이고 미커밋 변경 없음, 3 조건 **모두** 해당하는 워크트리만 수집 제외 + 개요에 한 줄 알림
- **E-8 세션 분석 48시간 한도 (신규)** — 최근 48시간 안에 수정된 세션 파일만 깊게 분석, 그보다 오래된 세션은 건너뜀 (아침 대기 시간 단축)

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| goodnight.md 부활 | 저녁 저장 의존 재발 — 통합 의도 무화 |
| goodmorning 이 저장된 노트를 전제 (노트 없으면 종료) | v2.8.0 동작 회귀 — 저녁 실행 깜빡하면 브리핑 빔 |
| 세션 수집 병렬 분산 제거 | 메인 컨텍스트 폭발 (세션 기록 깊은 분석 요구와 충돌) |
| 뒤처진 워크트리 제외 3 조건 중 하나 누락 | 작업 중인 워크트리(새 커밋 있음 또는 미커밋 변경 있음)가 스캔에서 빠짐 — 브리핑 누락 |
| 48시간 한도 제거 | 세션 누적 시 아침 대기 시간 증가 |
| 경고 배너 억지 생성 / 출력 스타일 룰 누락 / `disable-model-invocation: true` 누락 | v2.8.0 과 동일 증상 |

### 회귀 catch grep

```bash
# goodnight 삭제 + goodmorning 존재
test ! -f commands/goodnight.md && test -f commands/goodmorning.md && echo OK
# expected: OK

# 자급형 수집 — 삭제된 커맨드 참조 잔존 X
grep -cF "/goodnight" commands/goodmorning.md
# expected: 0

# 병렬 보조 에이전트 수집
grep -F "병렬" commands/goodmorning.md
# expected: >= 1

# 뒤처진 워크트리 제외 (ahead/behind 비교)
grep -F "ahead" commands/goodmorning.md
# expected: >= 1

# 48시간 한도
grep -F "48시간" commands/goodmorning.md
# expected: >= 1

# 노트 저장 유지
grep -F "session-handoff" commands/goodmorning.md
# expected: >= 1

# 모델 자동 호출 차단
grep -cF "disable-model-invocation: true" commands/goodmorning.md
# expected: 1

# 결합 메모 본문 존재
grep -cF "## /goodmorning 단일화 — /goodnight 흡수 (v2.9.0+)" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- 커맨드 1 삭제 + 1 재작성 + CLAUDE.md. 다른 skill / scripts / hooks / settings 영향 0
- 사용자 환경 출력 — `.js-super/session-handoff/` (gitignored, 저장소 외 산출물). 파일 형식 유지 — 기존 노트와 호환
- `using-superpowers` 본문 변경 X
- 자동 발동 경로 없음 — 명시 슬래시 호출만 (`disable-model-invocation: true`)

## og-* upstream 완전 분리 — 커맨드 인라인 (v2.8.1+)

v2.8.1+ 에서 og-* 흐름을 upstream superpowers 미러에서 **완전 분리**. 스킬 3종을 삭제하고 각 절차를 커맨드 본문에 인라인. 목적: (1) **컨텍스트 절감** — 스킬 description 이 매 세션 상주하던 비용 제거, (2) **커맨드 전용** — 모델 자동 발동 차단 (Matt Pocock ① 트리거 + 사용자 관례). "이제 upstream 과 갈라선다" (사용자 결정).

### 왜 스킬 삭제인가 (핵심)

스킬은 description 이 **매 세션 컨텍스트 상주** → 컨텍스트 부하. 커맨드 본문은 **호출 때만 로드** → 평소 상주 0. "컨텍스트에서 빼기 + 커맨드 전용" 을 진짜 하려면 스킬을 없애고 커맨드 본문에 넣어야 한다. description reword 만으로는 상주 비용이 안 사라진다 (그건 자동 발동만 막을 뿐). ← auto-* 는 체인 때문에 스킬 유지 (아래 참조), og-* 는 체인이 없어 완전 분리 가능.

### 실제 변경

1. **커맨드 3종** (`og-brainstorm`/`og-write-plan`/`og-execute-plan`) — 스킬 절차 전체를 본문에 인라인 + `disable-model-invocation: true` 유지. 스킬 참조 → 커맨드 참조 치환 (`invoke og-writing-plans skill` → `run /og-write-plan`).
2. **스킬 3종 삭제** — `skills/og-brainstorming`/`og-writing-plans`/`og-executing-plans` 디렉토리 제거.
3. **`brainstorming` Entry Router (FR-3) 전환** — "small 신호 → og-brainstorming skill auto-invoke" → "small 신호 → `/og-brainstorm` 실행 **안내**" (자동 invoke 제거, 스킬이 없어졌으니). 게이트의 og 선택지도 안내로.
4. **README / CLAUDE.md** — Skill 목록에서 og 3종 제거, 커맨드 전용 표기.

### mirror 룰 폐기 (D-og1 무효)

og-* 는 더 이상 upstream mirror 가 아니다. 기존 "og-* 본문 변경 절대 X" mirror 룰(v2.5.2 등 다른 섹션)은 **og 에 한해 폐기**. 커맨드 본문이 이제 정본이고 upstream sync 는 하지 않는다 (완전 분리).

### 회귀 패턴

| 안티 패턴 | 증상 |
|---|---|
| 커맨드가 삭제된 og 스킬을 invoke | 없는 스킬 호출 → 런타임 실패 |
| `brainstorming` router 가 og skill auto-invoke 로 회귀 | 없는 스킬 호출 → 실패 |
| 커맨드에서 `disable-model-invocation` 제거 | 모델 자동 발동 부활 |

### 회귀 catch grep

```bash
# 커맨드 3종 플래그 유지
grep -lF "disable-model-invocation: true" commands/og-brainstorm.md commands/og-write-plan.md commands/og-execute-plan.md
# expected: 3 lines

# og 스킬 삭제 확인
ls -d skills/og-* 2>/dev/null
# expected: (없음)

# 현행 스킬 본문에 삭제된 og 스킬 Skill-invoke 잔존 X (tests 제외)
grep -rn "og-brainstorming\|og-writing-plans\|og-executing-plans" skills/ | grep -v "/tests/"
# expected: empty

# brainstorming router 는 안내만 (auto-invoke X)
grep -F "Advise: run /og-brainstorm" skills/brainstorming/SKILL.md
# expected: >= 1
```

### 영향 범위

- 커맨드 3 인라인 + 스킬 3 삭제 + `brainstorming` router 전환 + README + CLAUDE.md.
- js-super 정식 흐름(`brainstorming` 진입/게이트)은 그대로 — small 신호 시 auto-invoke 대신 안내로만 바뀜.
- `subagent-driven-development`/`finishing-a-development-branch` (upstream untouched) 는 og 커맨드가 그대로 참조 — 영향 0.
- tests fixture (`skills/js-super-sub-driven/tests/H1/H2/H13`) 는 옛 라우팅 명칭 참조 — 실행 무관 문서, 후속 정리 대상.
- 실행 기록: `docs/og-커맨드전용화-실행기록.md`

### auto-* 확장 (같은 배치) — 체인 안전 문구 필수

같은 원리를 auto-* 4종에도 적용. 단 og-* 와 **결정적 차이 하나**: auto-* 는 서로를 자동 호출하는 **체인**이다 (auto-brainstorming → auto-tech-design → auto-writing-plans → auto-executing-plans).

- **체인은 스킬 이름으로 호출** (`js-super:auto-tech-design` invoke 등, `auto-brainstorming:93` / `auto-tech-design:69` / `auto-writing-plans:95`). SlashCommand 아님. → **커맨드에 `disable-model-invocation: true` 걸어도 체인 안 끊김.** (안전)
- **커맨드 4종** → `disable-model-invocation: true`. auto-flow 는 승인 게이트 자동 통과 + subagent 강제 실행이라, 모델 자동 발동 차단이 og-* 보다 더 중요.
- **스킬 4종 description** → 진입 제약 문구. **체인 스킬(2~4단계)은 반드시 "커맨드 또는 앞 단계의 명시 invoke 로만 진입, 자유 요청에서 자동 선택 금지"** 로 써야 한다. 그냥 "do NOT auto-select" 만 쓰면 체인 invoke 시 모델이 주저할 수 있음.
- **auto-* 는 upstream mirror 아님** (js-super 자작 self-contained mirror, v1.1.17+). og-* 의 mirror 룰 예외 논리 불필요 — description 자유 수정 OK.
- **본문 룰 보존**: auto-* 의 "AskUserQuestion 호출 X / Socratic prose-default" 등 기존 결합 룰은 description 만 바꿨으니 영향 0.

#### auto-* 회귀 catch grep

```bash
# 커맨드 4종 플래그
grep -lF "disable-model-invocation: true" commands/auto-brainstorm.md commands/auto-design-tech.md commands/auto-write-plan.md commands/auto-execute-plan.md
# expected: 4 lines

# 스킬 4종 진입 제약 문구
grep -cF "자동 선택 금지" skills/auto-brainstorming/SKILL.md skills/auto-tech-design/SKILL.md skills/auto-writing-plans/SKILL.md skills/auto-executing-plans/SKILL.md
# expected: 각 1

# 체인 invoke 라인 보존 (본문 안 건드림)
grep -cF "js-super:auto-tech-design" skills/auto-brainstorming/SKILL.md
grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md
grep -cF "js-super:auto-executing-plans" skills/auto-writing-plans/SKILL.md
# expected: 각 >= 1
```

파일럿 누적: og-* 3 + auto-* 4 = **7 커맨드** 전환. 나머지 17개는 후속.

## 워크트리-재분기 결합 (v2.9.0+)

v2.9.0+ 에서 `setting-up-worktrees` 가 워크트리 안 호출 (재분기) 을 지원. 루트 해석 이원화 — 배치 기준 = 메인 저장소 루트 (`git worktree list --porcelain` 첫 entry), 분기 기준 = 호출 위치의 현재 HEAD. spec: `docs/features/2026-08-09-워크트리-재분기/`.

### 적용 범위 (3 본문 + 6 manifest)

- `skills/setting-up-worktrees/SKILL.md` — Step 0 이원화 + Step 3.5 dirty 게이트 신설 + Step 4 브랜치별 개별 `git worktree add` 호출 + Step 5 복사 소스 호출 위치 우선 + Step 6 보고 확장 (분기 기준 커밋 + 스택 안내)
- `commands/worktree.md` — 안내 동기화
- `hooks/worktree-memory-symlink` — ROOT 해석을 `--show-toplevel` → 메인 워크트리 (worktree list 첫 entry) 로 교체 (워크트리 안 호출 시 심링크 silent 생략 버그 수정)
- `skills/setting-up-worktrees/scripts/setup-memory-symlinks.sh` — **무변경** (인자 기반, 훅이 올바른 MAIN_ROOT 전달)

### 핵심 룰

- **배치 = MAIN_ROOT 고정** — 워크트리 안에서 호출해도 중첩 생성 금지
- **분기 = 호출 위치 HEAD** — 사용자 베이스 명시 시 그 브랜치
- **dirty 게이트 (Step 3.5)** — "WIP 커밋 후 분기" / "마지막 커밋 시점 기준 분기" AskUserQuestion 선택. stash 금지
- **`git worktree add` 는 개별 Bash 호출의 시작** — 훅 프리픽스 매치 (`git worktree add `*) 보장. for-loop 한 방 금지
- **스택 안내** — 베이스 ≠ 메인 브랜치면 "새브랜치 → 베이스 → 메인" 머지 경로 + 리베이스 주의 출력

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| skill 만 변경 (훅 미변경) | 워크트리 안 호출 시 심링크 silent 생략 (훅 ROOT ≠ 배치 루트) |
| 훅만 변경 (skill 미변경) | 새 워크트리가 호출 위치 아래 중첩 생성 → git status 오염 |
| Step 4 for-loop 부활 | 훅 프리픽스 미매치 → 심링크 미생성 |
| commands 미동기 | 사용자 안내와 실제 동작 불일치 |

### 회귀 catch grep

```bash
grep -cF "MAIN_ROOT" skills/setting-up-worktrees/SKILL.md
# expected: >= 3
grep -c "worktree list --porcelain" hooks/worktree-memory-symlink skills/setting-up-worktrees/SKILL.md
# expected: 각 1 이상
grep -cF "Step 3.5" skills/setting-up-worktrees/SKILL.md
# expected: >= 2
grep -c "show-toplevel" hooks/worktree-memory-symlink
# expected: 0
awk '/\*\*Step 4/,/\*\*Step 5/' skills/setting-up-worktrees/SKILL.md | grep -c "for BR in"
# expected: 0 (Step 4 안 for-loop add 금지)
```

### 영향 범위

- 3 본문 + 6 manifest. `setup-memory-symlinks.sh` / `worktree-merge-back` / `worktree-remove` / og-* / auto-* 영향 0
- 훅은 기존처럼 `.worktrees/` 아래 경로만 처리 — 다른 위치 워크트리는 무시 (동작 동일)
- E2E: `docs/features/2026-08-09-워크트리-재분기/` 의 plan Task 9 시나리오 (a)~(e) — scratchpad 임시 저장소 검증 (저장소 커밋 X)

## 산출물 깊이 선택 (2개/3개) 결합

피처 단위 산출물 깊이 선택 도입 — 2개 (requirements + tech-design) 또는 3개 (+ implementation-plan). 표식 = tech-design frontmatter `depth: 2` (single source of truth). 버전 표기는 main 에서 bump 시 확정. spec: `docs/features/2026-08-09-산출물-깊이-선택/`.

### 핵심 룰

- **D1 표식** — `depth: 2` 명시일 때만 2-doc 트랙. 필드 부재 / `depth: 3` / 파싱 실패 = 3-doc (기존 동작). 기존 피처 폴더 소급 없음. 판독 helper: `scripts/preflight.py:feature_depth()` (additive — 기존 함수 시그니처 무변경)
- **D2 정식 결정 표면** — tech-design Gate #12 3지선다 (구현계획서까지 진행 / 여기서 종료 (2개 확정) / 나중에 결정). "나중에 결정" 은 표식 없이 종료 (기존 no 의미 보존)
- **D3 auto 결정 표면** — auto-tech-design Step 7 깊이 판정 (구현 단계 필요성 기준, 애매하면 3). AskUserQuestion 호출 X 유지. 2개 판정 시 판단 근거 1줄 보고 + 체인 종료
- **D4 체인 grep 계약 보존** — auto-tech-design 본문의 `js-super:auto-writing-plans` 문자열은 3개 판정 분기 문장 안에 보존 (기존 회귀 grep 그대로 통과)
- **D5 변경이력 라우팅** — 2-doc 트랙의 [코드-수정]/[검증]/[릴리즈] entry 는 tech-design footer 로. footer append 는 본문 수정이 아님 (change-propagation Acceptance 4 예외 조항)
- **D6 승격** — /write-plan (또는 /auto-write-plan) 명시 실행 = 2→3 승격. frontmatter `depth: 3` 갱신 + [개발방향-수정] entry. 재확인 게이트 없음

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| Gate #12 만 확장, auto Step 7 미분기 | 정식/auto 동작 불일치 — auto 는 무조건 4단계 완주 |
| 표식 기록만, change-history 라우팅 미갱신 | 2-doc 피처 코드·검증 이력의 목적지 소실 |
| 라우팅 갱신만, change-propagation Acceptance 예외 누락 | footer append 가 reverse-cascade 금지 룰과 충돌 판정 |
| auto Step 7 재작성 시 invoke 문자열 삭제 | 기존 회귀 grep (`js-super:auto-writing-plans`) 깨짐 |
| preflight 시그니처 변경 | 4 skill bash one-liner 동기 필요 (이번 릴리즈는 additive 라 해당 없음) |
| 판독 규칙 완화 (depth 부재를 2 로 해석 등) | 기존 3-doc 피처가 2-doc 분기로 오라우팅 |

### 회귀 catch grep

```bash
# 정식 게이트 3지선다
grep -F "여기서 종료 (2개 확정)" skills/tech-design/SKILL.md
# expected: >= 1

# auto 판정 분기 + 체인 문자열 보존
grep -F "깊이 판정" skills/auto-tech-design/SKILL.md
# expected: >= 1
grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md
# expected: >= 1 (기존 계약 유지)

# depth-aware 소비자 3곳
grep -lF "depth: 2" skills/change-history/SKILL.md skills/change-propagation/SKILL.md skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: 4 lines

# preflight helper
python3 -c "from scripts.preflight import feature_depth; print('OK')"
# expected: OK
```

### 영향 범위

- skill 본문 9 + commands 4 + `scripts/preflight.py` + fixture H14 + CLAUDE.md. 버전 bump 는 main 전용 룰에 따라 main 에서. og-* / fast-tasks / worktree 계열 영향 0
- executing-plans / js-super-sub-driven skill 본문 변경 0 — plan 부재 안내 보강은 preflight `human_reason` 안에서
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0

## audit-risk 구성 결합

`/audit-risk` 는 프로젝트의 보안 / 개인정보 / 비용 / 거버넌스를 1회성으로 점검하는 커맨드다. 예전에는 점검 보조 에이전트 5개와 별도의 HTML 보고서 생성 보조 에이전트(`commands/audit-report-prompt.md`)로 나뉘어 있었는데, 과장된 심각도·근거 없는 점수 표기가 사용자 catch 로 드러나면서 마크다운 단일 산출물 구조로 다시 썼다.

### 핵심 룰

- **산출물은 마크다운 하나** — `docs/audit/<timestamp>-audit-risk.md`. HTML 생성 경로가 없다. 보고서는 메인이 직접 `Write` 도구로 작성하고, 전용 보조 에이전트를 따로 부르지 않는다
- **규모 판정은 두 조건 AND** — 소스 파일 40개 미만이고 총 줄 수도 8,000 미만일 때만 축소 모드. 하나라도 넘으면 전체 모드. 애매한 경우는 전체 모드 쪽으로 떨어진다
- **축소 모드도 다섯 영역을 그대로 순회** — 보조 에이전트 수만 5개에서 1개로 줄어들 뿐, 점검 영역(외부 API 비용 / 개인정보 / 사용량·결제 로직 / LLM 에이전트 / 거버넌스)은 하나도 건너뛰지 않는다
- **심각도는 심각 / 높음 / 보통 3단계** — 모두 실행 경로를 확인했다는 전제 위에서만 붙인다. 실행 경로를 확인하지 못한 항목은 심각도 없이 `unverified` 로 분리한다. 0~100 점수는 쓰지 않는다
- **`status: "clean"` 반환 시 `checked` 배열 필수** — 점검했지만 없음과 점검하지 않음을 구분하기 위한 안전장치다
- **비밀값은 값 자체를 남기지 않는다** — `redact_secret` 표시와 파일·줄 번호만 적고, raw 값은 어떤 필드에도 넣지 않는다 (기존 안전장치 그대로 유지)
- **커맨드 본문과 H23 fixture 는 함께 고칠 것** — `commands/audit-risk.md` 와 `tests/eval-fixtures/H23-e2e/` 는 한 쌍이다. 한쪽만 고치면 사람이 돌리는 시나리오와 실제 동작이 어긋난다
- **보고서 본문은 한국어로 쓴다** — 사람이 읽는 값(`checked` / `title` / `evidence` / `impact` / `recommendation` / `summary` / `why_unverified` / `how_to_check`)은 한국어 문장. 파일 경로·함수 이름·명령어·라이브러리 이름처럼 그대로 검색해야 찾을 수 있는 것만 영어로 둔다. 영어 약어는 처음 나올 때 한국어 설명을 함께 적는다. 이 규칙은 공통 지시문과 Step 4 보고서 작성 지침 **양쪽**에 있어야 한다 (한쪽만 있으면 보조 에이전트가 영어로 돌려준 문장이 그대로 보고서에 실린다)

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| 커맨드만 고치고 fixture 미개정 | 사람이 돌리는 시나리오와 실제 동작이 어긋남 |
| 커맨드만 고치고 README 미갱신 | 사용자가 없는 산출물(HTML)을 기대함 |
| 규모 판정을 OR 로 완화 | 큰 프로젝트가 축소 모드로 빠져 점검 누락 |
| `clean` 의 `checked` 필수 규칙 약화 | 점검했지만 없음과 점검하지 않음이 구분되지 않음 |
| 심각도에 실행 경로 확인 전제를 뺌 | 근거 없는 심각도가 다시 붙어 과장 회귀 |
| 점수 필드 부활 | 근거 없는 숫자가 다시 보고서에 들어감 |

### 회귀 catch grep

```bash
grep -rn "audit-risk.html\|audit-report-prompt" commands/ README.md skills/
# expected: 0

test ! -f commands/audit-report-prompt.md && echo OK
# expected: OK

grep -n '"score"' commands/audit-risk.md
# expected: 0

grep -c '"clean"' commands/audit-risk.md
# expected: 1 이상

grep -c "disable-model-invocation: true" commands/audit-risk.md
# expected: 1
```

### 영향 범위

- `commands/audit-risk.md` 전면 재작성 + `commands/audit-report-prompt.md` 삭제 + `tests/eval-fixtures/H23-e2e/` 2 파일 + README 4곳 + CLAUDE.md. 버전 bump 는 main 전용 룰에 따라 main 에서
- audit-risk 는 애초에 HTML 생성 skill 을 거치지 않고 자체 보조 에이전트로 HTML 을 만들던 구조였고, 이번에 그 구조 자체를 걷어냈다 (이후 별도 작업에서 `generating-html` skill 과 `/sync-html` 커맨드도 저장소에서 제거됨)
- og-* / auto-* / 워크트리 계열 영향 0 — 명시 호출 커맨드 1개 재작성 범위 밖

## /tech-teach-me 결합 메모

`commands/tech-teach-me.md` — 요구사항·기술설계·구현계획 문서를 강의로 쪼개 한 강씩 설명하는 커맨드 전용 절차. 커맨드 본문 인라인 (스킬 없음 — v2.8.1 컨텍스트 절감 원리 답습).

### 전역 룰의 명시 예외 — AskUserQuestion 호출 금지

CLAUDE.md 의 "AskUserQuestion 도구 우선 (v2.3.5+)" 전역 룰에 대한 **명시 예외**. 이 커맨드 안에서는 강 진행·심화·종료를 모두 사용자 자유 입력으로 받고 `AskUserQuestion` 을 호출하지 않는다.

- **Why**: 강마다 팝업이 뜨면 학습 흐름이 끊기고 피로하다 (사용자 결정). 알람 fire 를 포기하는 대신 대화 리듬을 택함.
- **회귀 catch**: 본문에 AskUserQuestion 호출 지시가 생기면 회귀. 금지 섹션의 catch 라인만 허용.

### 강의 문체 — 자연어 + 도표 우선 (2026-08-29+)

강의 본문의 문체를 다음 방향으로 고정 (사용자 결정):

- 코드 발췌 금지 — 코드가 하는 일은 자연어로 풀어 쓰고, 파일 이름은 위치를 짚어줄 때만
- 구조·비교·흐름·관계는 표나 도식으로 먼저 보여주고 문장은 보충
- 문장 안 부호 금지 (화살표·체크·빗금 나열) — 화살표는 도식 안에서만
- 문서의 관리용 번호 (요구 항목 번호·결정 번호·이력 번호) 는 강의에 노출하지 않고 내용을 풀어 말함
- 위에서 아래로 한 번만 읽으면 이해되게 — 아직 설명 안 한 용어 선사용 금지, 뒤 내용 예고 금지
- 비유·은유 금지 (기존 룰 유지) + 잔말 금지 (인사·예고·감상 없이 내용만)

옛 룰 중 "코드가 있어야 이해되는 경우 다섯 줄 이내 발췌 허용" 과 "표는 항목 네 개 이하일 때만" 은 폐지 — 부활하면 회귀.

강 수 고정 상한 (150줄 미만 최대 3강, 그 이상 최대 5강) 도 폐지 (사용자 결정 — 긴 문서가 상한 때문에 과압축되는 것 방지). 묶고 남는 항목 수가 그대로 강 수. "적을수록 좋다 + 묶기 우선" 룰은 유지 — 상한만 없어진 것이지 잘게 쪼개라는 뜻이 아님.

### 영향 범위

- 커맨드 1 신규 + README 유틸리티 표 1행 + 본 섹션. skill / scripts / hooks 영향 0
- 읽기 전용 — 코드·문서 수정 경로 없음
- 자동 발동 경로 없음 (`disable-model-invocation: true`)

### 회귀 catch grep

```bash
test -f commands/tech-teach-me.md && grep -c "disable-model-invocation: true" commands/tech-teach-me.md
# expected: 1

grep -n "AskUserQuestion" commands/tech-teach-me.md
# expected: 금지 섹션의 catch 라인 1건만

test ! -d skills/tech-teach-me && echo "OK: 커맨드 전용 유지"
# expected: OK

grep -cF "표나 도식으로 먼저" commands/tech-teach-me.md
# expected: 1

grep -c "다섯 줄 이내로 발췌" commands/tech-teach-me.md
# expected: 0

grep -cF "관리용 번호" commands/tech-teach-me.md
# expected: 2

grep -c "표는 항목이 네 개 이하일 때만" commands/tech-teach-me.md
# expected: 0

grep -cF "잔말을 쓰지 않습니다" commands/tech-teach-me.md
# expected: 1

grep -c "최대 3강\|최대 5강" commands/tech-teach-me.md
# expected: 0

grep -cF "강 수에 고정 상한은 없습니다" commands/tech-teach-me.md
# expected: 1
```

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

## 용어집 커맨드 전환 + code-pretty 순서 결합

용어집은 원래 `glossary` 스킬이었고 `/write-plan` 흐름에서 `code-pretty` 와 나란히 자동으로 돌았다. 사용자가 원할 때만 부르는 쪽으로 바꾸면서 스킬을 지우고 `commands/glossary.md` 한 파일로 옮겼다. `code-pretty` 를 `verifying-spec` **앞** 에 두는 순서 교체는 그대로 유지된다.

### 현재 순서 (정식 `/write-plan` 흐름)

```
자체 점검 → code-pretty → verifying-spec → 사용자 검토 게이트 → change-history
```

`code-pretty` 가 먼저인 이유는 그대로다. 검증이 사용자가 실제로 읽을 코드 블록을 대상으로 돌고, prettify 가 건드린 것까지 잡는다. 역방향 의존은 없다 — code-pretty 는 verifying-spec 산출물을 쓰지 않는다.

### 왜 스킬이 아니라 커맨드인가

스킬은 description 이 매 세션 컨텍스트에 상주한다. 자동으로 돌지 않을 기능이면 그 상주 비용이 순손실이다. og-* 3종을 커맨드로 옮길 때와 같은 판단이다. 커맨드 파일명과 스킬 디렉토리명이 같으면 커맨드가 스킬을 가리는 문제도, 스킬이 없어지면서 함께 사라진다.

### 핵심 룰

- **G-1 명시 호출 전용** — `commands/glossary.md` 는 `disable-model-invocation: true`. 어떤 흐름도 자동으로 부르지 않는다
- **G-2 대상 문서 읽기 전용** — 대상 문서를 단 1바이트도 수정하지 않는다. `## 변경이력` 꼬리말 포함
- **G-3 용어집에 변경이력 꼬리말 없음** — 재생성되는 파생 문서. js-super 피처 폴더 MD 중 유일하게 change-history 꼬리말 룰 예외
- **G-4 보조 에이전트 필수, 모델 sonnet** — 이름을 코드베이스에서 찾는 작업이 메인 컨텍스트를 넘친다. 더 낮은 등급은 열어보지 않은 심볼의 설명을 지어낸다
- **G-5 추측 금지** — Grep 으로 찾아 실제 파일을 연 심볼만 설명. 못 찾으면 "확인 못 한 이름" 표에 남긴다
- **G-6 대상·시점 제약 없음** — 문서 종류를 가리지 않고, 변경이력이 쌓인 뒤에도 만든다. 옛 `glossary_check` 게이트는 폐지됐고 `scripts/preflight.py` 에서 함수째 제거됐다
- **G-7 인자 없이 부르면 후보를 묻는다** — 최근 수정된 피처 폴더를 `AskUserQuestion` 으로 제시. 임의로 고르지 않는다
- **G-8 사실 관찰은 허용, 설계 비평은 금지** — 문서가 쓰는데 선언이 없는 이름, 검증 문구가 가리키는데 본문에 없는 대상은 설명 칸에 그대로 적는다. 실제 dogfood 에서 이 동작이 계획서 결함 3건을 잡았다
- **G-9 용어집 문체** — 설명 칸은 이어지는 문장으로. 백틱은 "이름" / "위치" 칸에만, 가운뎃점 나열 금지. 문서 작성 규약이나 필드 형식은 수집 대상 밖 — 코드에 실재하는 이름만 다룬다

### 회귀 패턴

| 누락 / 변경 | 증상 |
|---|---|
| `/write-plan` 흐름에 용어집 dispatch 부활 | 커맨드 전환 무효 — 안 부탁한 산출물이 매번 생김 |
| `skills/glossary/` 재신설 | 커맨드가 스킬을 가려 스킬 호출 불가 + description 상주 비용 부활 |
| 커맨드에서 `disable-model-invocation` 제거 | 대화 중 자동 발동 부활 |
| 보조 에이전트 없이 메인이 직접 작성 | 코드 탐색이 메인 컨텍스트를 넘침 |
| 용어집에 변경이력 꼬리말 추가 | 재생성마다 이력 중복 누적 |
| 대상·시점 게이트 재도입 | 사용자가 원할 때 못 부름 — 전환 의도와 정면 충돌 |
| code-pretty 를 verifying-spec 뒤로 되돌림 | 검증이 사용자가 읽지 않을 코드 블록을 대상으로 돎 |

### 회귀 catch grep

```bash
test -f commands/glossary.md && test ! -d skills/glossary && echo OK
# expected: OK
```

```bash
grep -c "disable-model-invocation: true" commands/glossary.md
# expected: 1
```

```bash
grep -ci "dispatch.*glossary\|glossary.*subagent\|code-pretty + glossary" skills/writing-plans/SKILL.md skills/code-pretty/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: 각 0
```

```bash
grep -F "MUST run BEFORE \`verifying-spec\`" skills/code-pretty/SKILL.md
# expected: >= 1
```

```bash
grep -c "AFTER verifying-spec passes" skills/code-pretty/SKILL.md
# expected: 0
```

```bash
grep -c "glossary" scripts/preflight.py scripts/tests/test_preflight.py
# expected: 각 0
```

```bash
test -f skills/js-super-sub-driven/tests/H18-glossary-command/README.md && echo OK
# expected: OK
```

```bash
grep -c "## 용어집 커맨드 전환 + code-pretty 순서 결합" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- `commands/glossary.md` (신규) + `commands/write-plan.md` + 스킬 3 (`writing-plans` / `code-pretty` / `auto-writing-plans`) + `change-history` 파생 문서 예외 문구 + `scripts/preflight.py` + `scripts/tests/test_preflight.py` + fixture H18 + `README.md` + 본 섹션
- `skills/glossary/` 삭제. `executing-plans` / `js-super-sub-driven` / `verifying-spec` 본문 변경 0
- `og-*` / `fast-tasks` / worktree 계열 / `change-propagation` 영향 0
- `scripts/plan_byte_check.py` 영향 0 — 용어집은 `**원본**` 라벨을 쓰지 않아 검사 대상 밖
- `docs/features/**/*-glossary.md` 는 git 추적 대상 (계획서와 같은 폴더). 이미 만들어진 용어집 파일은 그대로 둔다
- 버전 bump 는 main 전용 룰에 따라 main 에서

## 무맥락 검증자 병렬 결합

`verifying-spec` 이 메인 자체 검증(A + C)과 **동시에** 맥락 없는 보조 에이전트 둘을 백그라운드로 띄운다. 단독(solo)은 대상 MD 경로만, 대조(cross)는 대상 + upstream 경로를 받는다. 메인이 두 결과를 중재해 보고서 하나로 낸다. spec: `docs/features/2026-08-15-무맥락-검증자-병렬/`.

### 왜 검증자가 둘인가 (핵심)

읽기 순서를 **프롬프트 지시가 아니라 구조로** 강제하기 위해서다. 한 에이전트에게 "먼저 대상 문서만 읽고 그 다음 상위 문서를 열어라" 라고 지시하면 지켰는지 확인할 방법이 없다 — 지시 위반이 결과물에 흔적을 남기지 않는다. 단독 검증자에게 upstream 경로를 아예 안 주면 그 위반이 성립하지 않는다. 이 구조를 "에이전트 1개로 합치면 싸다" 는 이유로 되돌리면 피처의 존재 이유가 사라진다.

### 적용 범위

- `skills/verifying-spec/SKILL.md` — HARD-GATE EXCEPTION 2 / Procedure dot / Clean-Context Verifiers 섹션 / Report Format 확장 / Anti-Patterns / Acceptance 4~6
- `skills/verifying-spec/clean-solo-prompt.md`, `clean-cross-prompt.md` — 신규
- `commands/{design-tech,write-plan,auto-design-tech,auto-write-plan}.md` — `--no-clean-verify` 안내
- fixture `skills/js-super-sub-driven/tests/H19-clean-verify/README.md`

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
grep -lF -- "--no-clean-verify" commands/design-tech.md commands/write-plan.md commands/auto-design-tech.md commands/auto-write-plan.md
# expected: 4 lines

# 호출 지점에 dispatch 복제 금지 (브랜치 무관하게 성립하는 불변식)
grep -l "clean-solo-prompt\|clean-cross-prompt\|no-clean-verify" skills/tech-design/SKILL.md skills/writing-plans/SKILL.md skills/auto-tech-design/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: (없음) — 네 호출 지점은 verifying-spec 을 이름으로만 부른다.
# 여기에 프롬프트 경로나 플래그가 등장하면 절차가 복제된 것이고, 한 곳만 고쳤을 때 흐름별 동작이 갈린다.
# (git diff main 비교는 머지 후 항상 비어 무의미하고, 무관한 브랜치에서 거짓 실패를 낸다)

# fixture 존재
test -f skills/js-super-sub-driven/tests/H19-clean-verify/README.md && echo OK
# expected: OK
```

## PRD 제거 + 소크라테스 단일화 결합

`brainstorming` 의 두 갈래(PRD / 소크라테스)를 없애고 소크라테스 단일 경로로 통합. 요구사항 문서의 계약은 `## 요구 항목` 섹션 + 항목 번호 앵커. spec: `docs/features/2026-08-15-prd제거-소크라테스고도화/`.

> ⚠️ **항목 번호 표기는 이후 바뀌었다.** 이 섹션이 쓰일 당시의 표기는 `FR-N` 이었지만, 지금 새로 만드는 문서는 `**요구 N**:` 을 쓴다. 아래 서술의 `FR-N` 은 전부 "그 시점의 항목 번호 표기" 로 읽고, 현행 규약은 "산출물 문서 스타일 결합" 섹션을 따른다. 섹션 이름(`## 요구 항목`)과 "번호를 붙인다" 는 계약 자체는 그대로다.

### 핵심 룰

- **E-1 요구 항목 계약** — 산출물에서 고정되는 것은 H1 / `## 요구 항목` + 항목 번호 (현행 `**요구 N**:`, 당시 `FR-N`) / `## 변경이력` 셋. 섹션 이름을 바꾸거나 번호를 빼면 다운스트림 4곳(`tech-design` / `verifying-spec` / `writing-plans` / `change-propagation`)이 앵커를 잃는다
- **E-2 모드 표기 줄 폐지** — 경로가 하나라 표기할 모드가 없음. `tech-design` 의 입력 형식 감지도 함께 삭제 (옛 문서와 새 문서가 같은 `FR-N` 앵커를 공유하므로 구분 불필요). 옛 6섹션 문서는 `## 3. 기능 요구사항 (FR)` 아래 같은 앵커를 갖고 있어 그대로 읽힌다
- **E-3 소크라테스 4블록** — 질문(커버 목록 5 + 종료 판정 + 3단 사다리) / 대안(고정 비교축 3 + 추천 먼저 + 깨지는 조건) / 문서(제외 항목 취합) / 승인(초안 전체 한 번)
- **E-4 질문 개수 상한 없음** — 커버 목록 충족으로 종료 판정. `auto-brainstorming`(1~5개)·`fast-tasks`(2~3개)와 의도적으로 다름
- **E-5 auto-\* 는 별도 사본** — 정식을 고쳐도 자동 전파되지 않음. 이번에는 `auto-brainstorming` 의 산출물 뼈대만 동기화하고 대화 절차 차이는 그대로 둠
- **E-6 공용 문구 3곳 동시** — 승인 게이트 boilerplate("산출물 (요구사항 / tech-design / impl-plan)")는 `brainstorming` / `tech-design` / `writing-plans` 에 복제. 한 곳만 고치면 갈린다

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| `## 요구 항목` 섹션 이름 변경 | 다운스트림 4곳이 앵커를 못 찾음 |
| 항목 번호 자체를 폐지 (표기 교체가 아니라 번호를 없앰) | `verifying-spec` A축이 셀 대상을 잃어 조용히 통과 |
| `tech-design` 감지 분기만 지우고 요구 항목 읽는 경로 누락 | 옛 6섹션 문서가 안 읽힘 |
| 공용 문구를 한 스킬만 교체 | 세 스킬의 문구가 갈림 |
| `README.md` 게이트 행만 삭제 | 바로 위 개수 표기와 불일치 |
| 흐름도 부분 수정 | 연결선이 없는 노드를 가리켜 그래프가 깨짐 |

### 회귀 확인

```bash
# 모드 게이트 잔존 확인
grep -c "Mode Selection\|PRD Adaptive Planning\|PRD mode\|Socratic mode" \
  skills/brainstorming/SKILL.md skills/tech-design/SKILL.md
# expected: 각 0

# 요구 항목 계약 존재
grep -c "## 요구 항목" skills/brainstorming/SKILL.md skills/auto-brainstorming/SKILL.md
# expected: 각 1 이상

# 소크라테스 4블록
# 흐름도 노드 라벨과 산문 언급은 제외하고 절차 헤더만 센다
grep -cE '^### 블록 [1-4] — ' skills/brainstorming/SKILL.md
# expected: 4

# 보존 계약 (건드리면 안 되는 것)
grep -c "Advise: run /og-brainstorm" skills/brainstorming/SKILL.md
# expected: 1 이상
grep -rlF '`--no-ask` 플래그 (v2.5+)' skills/ commands/ | wc -l
# expected: 12
```

### 영향 범위

- 스킬 4(`brainstorming` / `tech-design` / `auto-brainstorming` / `writing-plans` 공용 문구) + 커맨드 2 + `README.md` + `CLAUDE.md` + 예제 1
- `scripts/` `hooks/` 영향 0 — 요구사항 문서는 파일 이름만 검사
- `verifying-spec` / `change-propagation` 본문 변경 0 — 당시에는 `FR-N` 을 그대로 둬서 기존 앵커가 계속 동작했다. (이후 "산출물 문서 스타일" 작업에서 두 파일 모두 `**요구 N**:` 인식 + 옛 표기 하위 호환으로 실제로 바뀌었다)
- og-\* / worktree 계열 영향 0. (`generating-html` 은 이 작업과 별개로 main 에서 저장소에서 제거됐다 — 머지 시점에 확인)
- 버전 bump 는 main 전용 룰에 따라 main 에서

### 미해결 (별건)

- `tech-design` 흐름도의 조건부 주제 노드 3개(`Q: data model changes?` / `Q: external interfaces?` / `Q: test strategy?`)는 노드 선언과 연결선의 이름이 다르다 (`\n[활성 시만]` 접미사 유무). 착수 전부터 있던 문제이며 이번 범위 밖. 고칠 때는 선언 쪽 라벨에 접미사를 붙이거나 연결선 쪽에서 떼어 한쪽으로 맞출 것

## 커맨드 이름 ↔ 스킬 이름 충돌 금지 (2026-08-15+)

**커맨드 파일명 (`commands/<name>.md`) 과 스킬 디렉토리명 (`skills/<name>/`) 이 같으면 커맨드가 스킬을 가린다.** 그 스킬은 Skill 도구로 어떤 이름으로도 호출할 수 없게 된다 (`js-super:<name>` → 커맨드 본문이 반환, `<name>` → Unknown skill).

### 왜 치명적인가

충돌한 커맨드가 스킬로 위임하는 얇은 껍데기면 그 기능 전체가 죽는다. 게다가 스킬끼리의 체인 호출 (`brainstorming` → `tech-design`, `auto-brainstorming` → `auto-tech-design`) 도 같이 끊긴다.

**정적 grep 으로는 안 잡힌다.** `grep -cF "js-super:auto-tech-design" skills/auto-brainstorming/SKILL.md` 는 1 을 반환해 통과하지만, 실행하면 커맨드가 잡혀 체인이 끊긴다. 문자열은 제자리에 있는데 해석이 다른 경우라 원리상 문면 검사로 안 잡히는 종류다.

### 실제 사고 (2026-08-15 발견)

4쌍이 충돌해 있었다. 네 커맨드 모두 스킬 위임 껍데기였으므로 네 기능 모두 죽어 있었다.

| 옛 슬래시 | 새 슬래시 | 스킬 (변경 없음) |
|---|---|---|
| `/tech-design` | `/design-tech` | `tech-design` |
| `/auto-tech-design` | `/auto-design-tech` | `auto-tech-design` |
| `/worktree-merge-back` | `/merge-back-worktree` | `worktree-merge-back` |
| `/worktree-remove` | `/remove-worktree` | `worktree-remove` |

스킬 이름을 그대로 둔 이유: 스킬 식별자는 다른 스킬 본문의 체인 invoke, 본 CLAUDE.md 의 결합 메모 grep, fixture README 가 참조한다. 반면 슬래시 이름은 사용자 타이핑과 안내문에만 나온다. 바꿀 때 깨질 위험이 슬래시 쪽이 훨씬 작다.

`docs/features/` 아래 과거 스펙 문서 23건은 날짜가 박힌 기록이라 옛 슬래시 이름을 그대로 뒀다.

### 회귀 catch

```bash
# 커맨드 파일명과 스킬 디렉토리명 충돌 (신규 커맨드/스킬 추가 시 필수)
for c in commands/*.md; do n=$(basename "$c" .md); [ -d "skills/$n" ] && echo "충돌: /$n ↔ skills/$n/"; done
# expected: 출력 없음

# 위임 커맨드가 스킬 이름을 정확히 가리키는가
grep -c "js-super:tech-design" commands/design-tech.md
grep -c "js-super:auto-tech-design" commands/auto-design-tech.md
grep -c "js-super:worktree-merge-back" commands/merge-back-worktree.md
grep -c "js-super:worktree-remove" commands/remove-worktree.md
# expected: 각 >= 1

# 옛 슬래시 표기 잔존.
# 대상에서 CLAUDE.md 를 뺀다 — 바로 위 매핑 표와 이 검사 명령 자신이 매치돼
# 저장소가 정상일 때도 상시 5줄이 나오던 문제가 있었다 (2026-08-15 실측).
# HANDOFF.md 도 사용자가 읽는 표면이라 범위에 넣는다.
# (PROMPT_KO.md 는 v3.1.0 에서 저장소에서 제거돼 대상에서 뺐다.)
grep -rn '/tech-design\|/auto-tech-design\|/worktree-merge-back\|/worktree-remove' \
  skills/ commands/ README.md HANDOFF.md \
  | grep -v 'skills/tech-design\|skills/auto-tech-design\|skills/worktree-merge-back\|skills/worktree-remove' \
  | grep -v 'commands/tech-design\|commands/auto-tech-design\|commands/worktree-merge-back\|commands/worktree-remove' \
  | grep -v '<slug>-tech-design' | grep -v 'brainstorming/tech-design' \
  | grep -v '/design-tech\|/auto-design-tech\|/merge-back-worktree\|/remove-worktree' \
  | grep -c . || true
# expected: 0
```

### 신규 커맨드/스킬 추가 시 룰

커맨드는 짧은 명령형 (`/brainstorm`, `/write-plan`, `/execute-plan`), 스킬은 서술형 (`brainstorming`, `writing-plans`, `executing-plans`) 으로 짓는다. 같은 이름을 쓰지 않는다.

### 영향 범위

- 커맨드 파일 4개 rename + 27개 파일의 슬래시 표기 80줄. 스킬 본문의 절차·룰 변경 0, 스킬 디렉토리명 변경 0.
- `scripts/` / `hooks/` / `agents/` / 6 manifest 영향 0.
- 확인은 머지 후 `/reload-plugins` 로. 플러그인은 `~/.claude/plugins/cache/` 에서 읽히므로 워크트리 수정만으로는 반영되지 않는다.

## 스킬 검증 환경 ↔ CLAUDE.md 파싱 계약 (2026-08-15+)

`evals/` 러너는 **본 파일의 bash 코드 블록을 실행 시점에 직접 읽어** 결합 회귀 룰로 쓴다. 룰을 별도 파일로 복제하지 않는다. 복제하면 정답 원천이 둘이 되고, 본 파일은 3.5개월에 54회 갱신되므로 매 릴리즈마다 어긋날 기회를 갖는다.

### 파서가 기대하는 형식

아래 형식이다 (펜스는 예시라 들여쓰기로 적는다 — 그대로 펜스를 쓰면 이 예시
자신이 룰로 수집돼 매 실행마다 차단 1건이 뜬다):

    ```bash
    <검사 명령 (여러 줄 가능, 줄 끝 역슬래시 이음 지원)>
    # expected: <기대값>
    ```

- 코드 펜스 언어는 `bash` / `sh` / `shell` 중 하나여야 한다. `text` 나 언어 없음은 안 읽힌다
- `# expected:` 주석이 명령 바로 뒤에 와야 한다. 한 블록에 여러 룰을 넣으려면 각각 뒤에 붙인다
- 기대값이 **순수 숫자** (`0`, `1`, `각 >= 1`, `3 lines`) 면 기계가 판정한다
- 기대값에 조건이 붙으면 (`0 (Anti-Pattern catch 라인만 허용)`) 자연어로 보고 모델 판정으로 넘긴다. 지금은 판정 대기 상태로 남는다

### 룰 작성 시 지켜야 할 것

- 명령은 **읽기 전용**이어야 한다. 러너가 관문으로 검사해서 쓰기 계열이면 실행하지 않고 차단 보고한다. 허용 명령은 `grep`, `ls`, `test`, `awk`, `sed -n`, `find`, `cat`, `wc`, `head`, `tail`, `echo`, `sort`, `uniq`, `cut`, `tr`, `python3`, `git`(읽기 하위 명령만) 이다
- `<slug>` 같은 자리표시자를 쓴 명령은 그대로 실행되지 않아 차단된다. 실행 가능한 룰로 만들려면 실제 경로를 쓴다
- 셸은 `bash` 로 고정되어 돈다. 사용자 기본 셸(zsh) 기준으로 쓰면 결과가 달라질 수 있다

### 회귀 catch

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"
# expected: >= 100
```

```bash
ls evals/run.py evals/runner/coupling.py evals/baseline.json | wc -l
# expected: 3
```

### 영향 범위

- 본 파일의 코드 블록 형식이나 `# expected:` 주석 형식을 바꾸면 러너가 조용히 룰을 놓친다. 러너는 파싱된 룰 수가 직전 실행보다 줄면 경고한다. 절대 수치를 assert 로 박지는 않는다 (자산이 계속 늘어나는 저장소에서 절대값 검사는 매 릴리즈에 마찰을 부과한다)
- fixture README (`skills/*/tests/**/*.md`) 도 같은 형식으로 읽힌다. 두 원천을 합쳐 111건이다
- `evals/` 는 Claude Code 의 자동 로드 경로 밖이라 사용자 세션에 안 올라간다

## understand 커맨드 5종 결합 (Understand-Anything 이식)

Understand-Anything v2.9.4 의 그래프 생성(`/understand`)과 조회 4종(chat / diff / explain / onboard)을 커맨드 전용으로 이식. 엔진·스크립트·보조 에이전트 프롬프트는 저장소에 없고, 최초 실행 시 원저장소를 `~/.understand-anything-plugin` 에 버전 고정 clone 해 재사용한다. spec: `docs/features/2026-08-16-understand-anything-command/`.

### 핵심 룰

- 5 커맨드 모두 `disable-model-invocation: true` — 자동 발동 경로 0
- 엔진 확보는 런타임 clone (태그 v2.9.4) — 저장소에 엔진 코드·바이너리·빌드 파이프라인 반입 금지
- 원저장소는 저장소 루트 아래에 플러그인 폴더가 한 겹 더 있다. clone 대상(사본 루트)과 엔진 기준 경로가 다르므로, 경로를 줄일 때 한 겹을 빠뜨리지 말 것
- 조회 4종의 공통 블록 (Graph Structure Reference + 최신성 검사) 은 4파일 복붙 동기 — 한 곳 수정 시 4곳 동시 수정
- 버전 고정 문자열 (clone 태그 / viewer 릴리즈 URL) 은 등장하는 파일 전체에서 일치 유지 — 한쪽만 올리면 엔진과 viewer 의 스키마가 어긋난다
- `/understand` 의 덮어쓰기 표 (O-1~O-5) 밖 원본 절차는 무수정 — 특히 배치 파일명 규약을 변형하면 병합에서 조용히 유실된다
- 훅 미도입 — 증분 갱신은 `/understand` 재실행만. hooks/ 에 understand 관련 항목을 넣지 않는다

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| 조회 4종 공통 블록 한 곳만 수정 | 커맨드별 최신성 판정이 갈림 — 같은 그래프에 다른 경고 |
| clone 태그만 올리고 viewer URL 미동기 | 새 스키마 그래프를 옛 viewer 가 못 읽음 (또는 반대) |
| 엔진 기준 경로에서 중첩 한 겹 누락 | 사본은 있는데 절차 본문을 못 찾아 매번 재clone 시도 |
| 스킬 디렉토리 신설 (skills/understand*) | 커맨드가 스킬을 가려 호출 불가 — 이름 충돌 룰 위반 |
| 훅에 자동 갱신 추가 | 요구사항 범위 밖 재유입 — 컨텍스트 상주 제거 취지 위배 |

### 회귀 catch grep

```bash
# 5 커맨드 존재 + 명시 호출 전용
grep -lF "disable-model-invocation: true" commands/understand.md commands/understand-chat.md commands/understand-diff.md commands/understand-explain.md commands/understand-onboard.md | wc -l
# expected: 5

# 커맨드 ↔ 스킬 이름 충돌 없음
ls -d skills/understand* 2>/dev/null | wc -l
# expected: 0

# 버전 고정 문자열 (clone 태그 + viewer URL)
grep -c "v2.9.4" commands/understand.md
# expected: >= 2

# 조회 4종 공통 최신성 블록 동기
grep -lF "GRAPH_COMMIT_RAW" commands/understand-chat.md commands/understand-diff.md commands/understand-explain.md commands/understand-onboard.md | wc -l
# expected: 4

# viewer URL 등장 파일 일치 (understand + understand-diff)
grep -rlF "releases/download/v2.9.4/understand-anything-viewer.tgz" commands/ | wc -l
# expected: 2

# 훅 미도입
grep -rln "understand-anything" hooks/ | wc -l
# expected: 0
```

### 영향 범위

- commands 5 신규 + README 1곳 + fixture 1 (`commands/understand-tests/H24-e2e/`). skills/ / scripts/ / hooks/ / agents/ 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
- 원본 플러그인과 동시 설치는 비전제 (커맨드 이름 동일) — README 주의 문단이 사용자 안내 캐리어

## 스킬목록 홈 전체 조회 결합 (스킬목록-전체프로젝트조회)

`/list-skills` 의 조회 범위를 홈 전체로 확장 — 현재 프로젝트 / 글로벌 / 다른 프로젝트 세 그룹. 탐색은 `scripts/skill_scan.py` (표준 라이브러리만, 읽기 전용) 가 수행하고 커맨드는 렌더링만 한다. v2.7 의 FR-2 "다른 프로젝트 안 보임" 은 이 피처로 **공식 폐지** (사용자 결정). spec: `docs/features/2026-08-16-스킬목록-전체프로젝트조회/`.

### 핵심 룰

- **L-1 커맨드 ↔ 스크립트 JSON 계약** — 스크립트 출력 키 (`current_project` / `global` / `other_projects`, 각 그룹 `root` + `skills[]`, 항목 `slug`/`path`/`description`/`created`) 를 바꾸면 커맨드 본문 § 2 도 동시 수정. 한쪽만 바꾸면 목록이 조용히 빈다
- **L-2 표식 필터 유지** — `.js-super-skill.json` 있는 것만 목록에. 갈래 C (표식 없는 skill 표시) 는 미채택
- **L-3 원격 삭제 금지** — 다른 프로젝트 skill 은 안내만 (해당 프로젝트에서 `/remove-skill` 실행)
- **L-4 스크립트 실패 폴백** — 기존 두 스코프 (cwd + 글로벌) LS 조회로 격하 + 안내 한 줄. 스크립트 실패가 조회 커맨드를 죽이면 안 됨
- **L-5 현재 프로젝트 = 상향 탐지 + 직접 열거** — cwd 에서 위로 올라가 `.claude/skills` 보유 첫 디렉토리 (홈 자체 제외). 숨김 경로 (워크트리) 아래여도 현재 그룹에는 나옴
- **L-6 읽기 전용** — 스크립트·커맨드 모두 파일 변경 없음

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 스크립트 JSON 키만 변경 (커맨드 미동기) | 목록이 조용히 빔 (L-1) |
| 커맨드가 옛 "다른 프로젝트 스캔 금지" 로 회귀 | 홈 전체 조회 무력화 — 본 피처 무화 |
| 표식 필터 제거 | 갈래 C 무단 도입 — `/remove-skill` 로 못 지우는 항목 노출 |
| 프루닝 (숨김·무거운 폴더) 제거 | 스캔이 분 단위로 느려짐 + 워크트리 사본 중복 노출 |
| 폴백 제거 | 플러그인 루트 변수 미지원 하네스에서 조회 커맨드 전체 사망 |

### 회귀 catch grep

```bash
# 스크립트 존재 + 커맨드가 호출
test -f scripts/skill_scan.py && grep -cF "skill_scan.py" commands/list-skills.md
# expected: >= 1

# 옛 금지 조항 잔존 catch
grep -c '다른 프로젝트의 `.claude/skills/` 스캔 금지' commands/list-skills.md
# expected: 0

# JSON 계약 전수 — 키 9개가 커맨드와 스크립트 양쪽에 다 있어야 한다.
# 한쪽에서만 이름을 바꾸면 빠진 키 수가 0 을 넘는다.
for k in current_project global other_projects root skills slug path description created; do grep -qF "$k" commands/list-skills.md || echo "cmd:$k"; grep -qF "\"$k\"" scripts/skill_scan.py || echo "py:$k"; done | wc -l
# expected: 0

# 폴백 존재
grep -cF "홈 전체 스캔을 사용할 수 없어" commands/list-skills.md
# expected: >= 1

# 커맨드가 환경변수로 스크립트를 부르면 안 된다 (슬래시 커맨드에서 안 채워짐)
grep -c '${CLAUDE_PLUGIN_ROOT}/scripts/skill_scan.py' commands/list-skills.md
# expected: 0

# 스크립트 공개 함수 3개가 그대로 있는가 (import 가능 + 시그니처 유지)
python3 -c "import scripts.skill_scan as m; print(len([f for f in ('scan','collect_skills','find_current_project') if hasattr(m,f)]))"
# expected: 3

# 결합 메모 본문 존재
grep -cF "## 스킬목록 홈 전체 조회 결합" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- `commands/list-skills.md` + `scripts/skill_scan.py` (신규) + `scripts/tests/test_skill_scan.py` (신규) + `README.md` 2곳 + `CLAUDE.md` (v2.7 메모 개정 + 본 섹션). 버전 bump 는 main 전용 룰에 따라 main 에서
- `commands/new-skill.md` / `commands/remove-skill.md` — 변경 0 (출처 표식 규약 그대로. 3 커맨드 동시 수정 룰은 규약 변경 시에만 발동)
- og-* / auto-* / worktree 계열 / `scripts/preflight.py` / hooks 영향 0

## 워크트리 부모브랜치 기록 결합

`/merge-back-worktree` 의 머지 대상을 "워크트리 목록 첫 entry = 최상위" 추론에서 **생성 시 기록된 직계 부모 브랜치** 로 교체. 재분기 워크트리 (워크트리 A 안에서 만든 워크트리 B) 가 A 가 아니라 최상위로 머지하려던 문제를 없앤다. spec: `docs/features/2026-08-29-머지백-부모브랜치기준/`.

### 핵심 룰

- **기록 키 2개 규약** — `branch.<BR>.js-super-parent` (부모 브랜치 이름) + `branch.<BR>.js-super-parent-base` (분기 SHA). 생성 (`setting-up-worktrees` Step 4, 신규 `-b` 분기 직후) 과 판독 (`worktree-merge-back` Step 2) 이 공유한다. 키 이름이나 값 형식을 한쪽만 바꾸면 desync — 두 스킬 동시 수정
- **판별 = 검증 4건 전부 통과 시에만 자동 진행** — 기록 존재·자기 자신 아님 / 부모 브랜치 실존 / 부모가 워크트리에 체크아웃됨 / 기록된 분기점이 현재 히스토리의 조상. 하나라도 실패하면 `AskUserQuestion` 게이트로 머지 대상을 확인받는다. 조용한 최상위 fallback 과 히스토리 추정 자동 진행은 금지 (사용자 결정). 게이트에는 "중단" 옵션을 항상 포함해 부모 미체크아웃 케이스의 탈출 경로를 남긴다
- **기록 명령은 `git worktree add` 와 별도 Bash 호출** — `worktree-memory-symlink` 훅은 명령 문자열이 `git worktree add ` 로 시작할 때만 발화한다. 한 호출로 묶으면 접두사가 바뀌어 심링크가 조용히 사라진다
- **게이트 1건 재도입** — `worktree-merge-back` 의 "게이트 0건" 서술과 Other / 모호 응답 룰 (v2.1.1+) 비활성 서술이 함께 갱신됐다. 게이트를 다시 없애면 이 서술도 되돌려야 한다
- **기존 워크트리 소급 기록 없음** — 이 개선 이전에 만든 워크트리는 기록이 없고, 게이트가 흡수한다. v2.5.1 D-1 의 "머지 대상 = parent 의 로컬 브랜치" 는 유지되되 parent 의 의미가 최상위에서 직계 부모로 좁혀졌다

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 한쪽 스킬만 변경 (키 규약 desync) | 생성 기록과 머지백 판독 불일치 — 매번 판별 실패 게이트 |
| 기록 명령을 `git worktree add` 호출에 합침 | 훅 프리픽스 미매치 → 메모리 심링크 미생성 |
| 게이트 제거 + 최상위 fallback 부활 | 재분기 워크트리가 최상위로 잘못 머지 — 본 피처 무화 |
| 검증 4번 (분기점 조상) 제거 | 스킬 밖에서 브랜치를 옮기면 (`reset --hard` / `branch -f`) 기록만 남고 낡는다 → 잘못된 부모로 자동 머지. (브랜치 삭제 후 동명 재생성은 해당 없음 — git 이 `branch.<이름>.*` 를 함께 지운다) |

### 회귀 catch grep

```bash
grep -lF "js-super-parent" skills/setting-up-worktrees/SKILL.md skills/worktree-merge-back/SKILL.md
# expected: 2 lines
grep -c "MAIN_INFO" skills/worktree-merge-back/SKILL.md
# expected: 0
grep -cF "판별 실패" skills/worktree-merge-back/SKILL.md
# expected: >= 1
test -f skills/worktree-merge-back/tests/H18-parent-branch/README.md && echo OK
# expected: OK
```

### 영향 범위

- 스킬 2 (`setting-up-worktrees` / `worktree-merge-back`) + 커맨드 2 (`worktree` / `merge-back-worktree`) + fixture 1 (H18) + CLAUDE.md
- `worktree-remove` / og-* / auto-* / `scripts/preflight.py` / hooks 본문 영향 0 — 훅은 접두사 계약 재확인만
- 버전 bump 는 main 전용 룰에 따라 main 에서

## 워크트리 브랜치 네이밍 제안 결합 (재분기 `부모__자식`)

`/worktree` 에서 이름 없이 작업 설명만 주면 AI 가 브랜치 이름을 제안한다. 재분기 판별은 브랜치 비교 (`BASE_BRANCH` ≠ `MAIN_BRANCH`) — 스택 구조 안내 (v2.9.0+) 와 동일 기준. 재분기면 `<부모브랜치>__<자식이름>` 형식으로 누적되고, 사용자 명시 이름은 그대로 존중한다. spec: `docs/features/2026-08-29-워크트리-재분기-네이밍/`.

### 핵심 룰

- **N-1 명시 이름 존중** — 사용자가 이름을 주면 개명 · 제안 없이 그대로 (FR-4). 제안은 이름 미지정일 때만
- **N-2 판별 = 브랜치 비교** — 경로 (워크트리 안인지) 가 아니라 분기 기준 브랜치 ≠ 메인 브랜치. 메인 워크트리에서 feature 브랜치 체크아웃 상태로 분기해도 접두어가 붙는다 (의도)
- **N-3 생성 이름 제약** — AI 가 새로 짓는 부분에 `__` 금지 (구분자 예약). `/` 는 자식 이름에 금지 (새 중첩 층 방지 — 부모에게서 물려받은 `/` 는 수용), 메인 기준 이름은 저장소 관례를 따름. 명시 이름에는 미적용
- **N-4 skill ↔ commands 동기** — 마커 리터럴 `부모브랜치__자식이름` 이 양쪽에 존재해야 함. 한쪽만 고치면 안내와 동작이 어긋난다
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
- `worktree-merge-back` / `worktree-remove` — 본 네이밍 피처의 변경 0 (`__` 파싱 부모 판별은 범위 밖, tech-design §2 승계). 머지백의 부모 판별은 이름이 아니라 위 "워크트리 부모브랜치 기록 결합" 의 config 기록으로 한다 — 두 피처는 독립
- `hooks/` / `scripts/` / og-* / auto-* 영향 0. 기존 워크트리 · 브랜치 이름 소급 변경 없음

## 서브에이전트 sonnet 하한 결합 (haiku 사용 금지)

서브에이전트 dispatch 전 경로에서 haiku 사용 금지. implementer dispatch = plan `**Model**:` 값 (생략 시 sonnet, 하한 sonnet). 계획서 작성 층의 `**Model**:` 필드는 `sonnet | opus` 2값. 옛 계획서에 남은 haiku 값은 실행 층이 sonnet 으로 격상해 dispatch (계획서 수정 요구 없음, dispatch log 에 격상 표기). v2.9 의 조건부 분기 (순수 byte-copy = haiku) 는 폐지. spec: `docs/features/2026-08-29-서브에이전트-sonnet-기본/`.

### 핵심 룰

- **작성 층 (writing-plans / auto-writing-plans) 본문에서 haiku 단어 소멸** — enum 2값 + 판정표 sonnet 흡수. executing-plans 룰 2 row 도 haiku 단어 없이 js-super-sub-driven 참조로 위임
- **실행 층 (js-super-sub-driven SKILL.md + implementer-prompt.md) 만 격상 문구에서 haiku 언급 허용** — dispatch 패턴 (`model: "haiku"` / `model='haiku'`) 은 0
- **금지-언급 무변경 — spec-reviewer-prompt / code-pretty 2파일 + reorder-prompt L10 의 "NOT haiku." 주석** — "Haiku 쓰지 마라" 류 문구는 새 룰과 정합이라 잔존 허용
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
- reorder / spec-reviewer / code-pretty 의 sonnet 고정 — 동작 변경 0
- 버전 bump 는 main 전용 룰에 따라 main 에서

## 산출물 문서 스타일 + 요구 항목 번호 교체 결합

요구사항서와 기술설계서를 만드는 스킬 넷에 산출물 작성 스타일 룰을 심고, 요구 항목 번호를 `FR-N` 에서 `요구 N` 으로 바꾼 작업. spec: `docs/features/2026-08-29-문서가독성개선/`.

### 왜 스킬 본문에 직접 넣었나

이 저장소의 스킬은 자기 완결이 원칙이다. 공용 스타일 파일 하나를 넷이 참조하게 만들면 저장소에 없던 참조 패턴이 새로 생긴다. 문체를 기계로 검사하는 방법도 검토했지만 한국어 문장의 좋고 나쁨은 판정할 수 없어 코드 패턴 검사만 보조로 남겼다. 앞서 "서술 수준 — 이름보다 역할" 룰도 같은 이유로 본문 삽입 방식을 썼다.

### 핵심 룰

- **섹션 이름은 넷 다 `## 산출물 문서 스타일`** — 이름이 같아야 한 줄 검색으로 네 파일을 한 번에 확인할 수 있다. 정식 경로 둘은 전체본, 자동 경로 둘은 압축본
- **적용 대상은 산출물 문서뿐** — 스킬 본문의 영어 식별자, 룰 본문, dot 흐름도는 대상이 아니다. 본문은 에이전트가 읽는 코드에 해당한다
- **요구 항목 번호는 `**요구 N**:`** — 굵게까지 포함한 형태가 약속이다. 읽는 쪽이 이 패턴을 찾는다
- **읽는 쪽은 세 세대를 모두 인식** — `요구 N` (현행) / `## 요구 항목` 아래 `FR-N` (직전) / `## 3. 기능 요구사항 (FR)` 아래 `FR-N` (초기). 옛 문서를 읽는 김에 새 형식으로 고쳐 쓰지 않는다
- **기술설계서 도면은 세 형식 중 상황에 맞게** — 아스키 박스 도면 (기본) / 아스키 도면 + 번호 + 설명 표 (요소가 많을 때) / mermaid (관계·분기가 본질이고 렌더링 환경 전제 가능). 절차 나열 흐름도로 구조 설명을 대신하지 않는다
- **도면 안 번호 (①②③) 는 항목 코드가 아니다** — 표에서 설명하기 위한 도면 표기법이라 금지 대상 밖. 요구 항목 번호가 "유일한 예외" 라는 문구와 충돌하지 않는다
- **옛 문서 소급 수정 없음** — 새로 쓰는 문서부터 적용. 하위 호환으로 계속 읽힌다
- **구현계획서의 문체는 범위 밖** — 계획서 본문은 코드를 보여주는 것이 목적이라 서술 문체 규칙을 적용하지 않는다. 다만 `writing-plans` 는 자체 점검에서 요구사항 문서의 항목을 세어 읽으므로, 그 자리의 항목 번호 표기는 세 세대를 모두 인식하도록 맞춰 뒀다 (`auto-writing-plans` 에는 해당 문구가 없어 손댈 것이 없었다)

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 정식·자동 한쪽만 수정 | 두 경로가 만드는 문서의 문체가 갈린다. 문서를 나란히 놓고 읽기 전에는 안 드러난다 |
| 읽는 쪽의 하위 호환 문구 삭제 | 옛 피처 문서를 다시 열 때 요구 항목을 못 찾는다 |
| 읽는 쪽 중 한 곳 누락 | 그 스킬만 옛 형식을 기대한 채 남는다 |
| 도면 형식 판단 기준 삭제 | 매번 형식이 흔들리고, 결국 한 형식만 쓰게 된다 |
| 스타일 룰을 스킬 본문 자체에 적용 | 에이전트가 읽는 식별자와 룰이 지워져 스킬이 망가진다 |
| 흐름도 노드 이름 일부만 교체 | 없는 노드를 가리키는 연결선이 생겨 그래프가 깨진다 |

### 회귀 catch grep

```bash
grep -lF "## 산출물 문서 스타일" skills/brainstorming/SKILL.md skills/auto-brainstorming/SKILL.md skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md | wc -l
# expected: 4
```

```bash
grep -cF "### 도면 형식" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
# expected: 각 1
```

```bash
grep -cF "**요구 1**" skills/brainstorming/SKILL.md
# expected: 1
```

```bash
grep -c "FR-N" skills/tech-design/SKILL.md
# expected: 3 (하위 호환 문구 — 0 이면 회귀)
```

```bash
grep -c "FR-3" README.md
# expected: 0
```

```bash
grep -c "FR-N" commands/og-brainstorm.md
# expected: 0
```

```bash
grep -c "Self-review (6 items)" skills/brainstorming/SKILL.md
# expected: 0
```

### 영향 범위

- 스킬 8 (`brainstorming` / `auto-brainstorming` / `tech-design` / `auto-tech-design` / `verifying-spec` + 그 대조 검증 프롬프트 / `change-propagation` / `risk-annotation`) + 커맨드 1 (`og-brainstorm` 형식 비교 한 줄) + `README.md` 4곳 + fixture 2 (H21 신규 + 인덱스) + `CLAUDE.md`. 버전 bump 는 main 전용 룰에 따라 main 에서
- `auto-writing-plans` / `executing-plans` / `js-super-sub-driven` — 변경 0. `writing-plans` 는 자체 점검에서 요구사항 문서의 항목을 세어 읽으므로 그 자리의 번호 표기만 세 세대 인식으로 맞췄다 (문체 규칙은 적용 대상 아님)
- og-* / worktree 계열 / `scripts/` / `hooks/` / `agents/` 영향 0
- 실행 코드 변경 0 — 스킬 본문과 문서 텍스트만

## 구현계획서 코드 강제 + 위키형 분할 결합

계획서가 길어지면 구현 코드 블록을 생략하고 자연어만 남기는 drift 가 실제로 발생했다 (사용자 catch — 코드를 검토하려 했는데 계획서에 코드가 없었다). 원인은 코드 존재를 검사하는 장치가 없었던 것 — 기존 byte-equal 검사는 존재하는 블록의 내용만 보므로 블록이 없으면 0건 매치로 통과한다. `scripts/plan_guard.py` 가 그 빈 자리를 메운다. spec: `docs/features/2026-08-29-구현계획서-코드강제-분할/`.

### 핵심 룰

- **문서 집합 해석은 한 곳에서만** — `plan_guard.resolve_documents()` 가 인덱스 → 하위 문서 집합을 푸는 단일 진입점이다. 소비자가 각자 해석하면 한 곳만 어긋나도 인덱스만 검사하고 통과하는 false-pass 가 난다
- **임계값 10 / 상한 3** — task 10개 이상이면 분할 필수, 하위 문서 하나에 task 최대 3개. 둘 다 결정적 상수 (`SPLIT_THRESHOLD` / `MAX_TASKS_PER_SUBDOC`)
- **재량은 나누는 방향으로만** — 10개 미만의 분할은 허용, 10개 이상의 단일 문서는 차단
- **인덱스 파일 이름 불변** — `<slug>-implementation-plan.md` 그대로. 하위 문서는 `plan/tasks-NN-MM.md` 로, 기존 파일명 정규식에 **일부러 매치되지 않게** 짓는다 (최신 계획서 자동 선택이 하위 문서를 오선택하는 사고 차단)
- **하위 문서에 변경이력 footer 없음** — 모든 entry 는 인덱스로 모인다
- **축약 마커는 주석 형태만 탐지** — 맨몸 `...` 한 줄은 정상 코드와 충돌하므로 제외. 같은 task 의 `**원본**` 블록에 있던 라인은 면제 (원래 파일에 있던 표현)
- **기존 byte-check 모듈 무변경** — `plan_byte_check.py` 는 그대로 두고 wrapper 가 문서별로 호출한다. 그 파일은 구현 / 재정렬 프롬프트 + sub-driven 본문과 atomic 번들로 묶여 있어 건드리면 번들 전체 재검증이 필요하다

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 소비자가 `resolve_documents` 를 안 쓰고 자체 해석 | 그 소비자만 인덱스를 보고 통과 — false-pass 재발 |
| G1 검사 약화 | 코드 없는 계획서가 다시 통과 (이번 사고 그대로 재현) |
| 축약 마커 면제 규칙 삭제 | 원래 파일에 있던 주석이 오탐으로 잡혀 게이트가 막힘 |
| 하위 문서 이름을 `-implementation-plan.md` 접미사로 변경 | 최신 계획서 자동 선택이 하위 문서를 본체로 오선택 |
| 하위 문서에 변경이력 footer 추가 | 이력이 흩어져 감사 흐름이 끊김 + live 판정이 어긋남 |
| 정식 흐름만 수정 (자동 흐름 미동기) | 두 경로의 규약이 갈림 — 자동 흐름 계획서에 코드 생략 잔존 |
| 실행 진입 시에도 강제 검사 추가 | 기존 계획서가 전부 차단 — 소급 비대상 원칙 위반 |

### 회귀 확인

```bash
python3 -c "from scripts.plan_guard import resolve_documents, check_plan, verify_documents_byte_equal; print('OK')"
# expected: OK
```

```bash
grep -c "SPLIT_THRESHOLD = 10" scripts/plan_guard.py
# expected: 1
```

```bash
grep -c "MAX_TASKS_PER_SUBDOC = 3" scripts/plan_guard.py
# expected: 1
```

```bash
grep -lF "plan_guard" skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md | wc -l
# expected: 2
```

```bash
grep -c "plan/tasks-" skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 각 1 이상
```

```bash
test -f skills/js-super-sub-driven/tests/H22-plan-split/README.md && echo OK
# expected: OK
```

fixture 번호는 브랜치마다 자기 것의 존재만 검사하면 중복을 못 잡는다 (두 룰이 각자 자기 경로만 보므로 번호가 같아도 둘 다 통과한다 — 실제로 `H20` 이 세 워크트리에 겹쳤을 때 이 방식이 놓쳤다). 번호 공간 전체를 보는 룰을 따로 둔다.

```bash
ls skills/js-super-sub-driven/tests | grep -oE '^H[0-9]+' | sort | uniq -d | wc -l
# expected: 0
```

```bash
grep -c "분할 계획서 예외 (하위 문서)" skills/change-history/SKILL.md
# expected: 1
```

### 영향 범위

- 스크립트 2 신규 + 1 수정 (추가 전용 — 기존 함수 시그니처·exit code 규약 무변경이라 3 skill 의 사전 검사 명령 동기 불필요), 스킬 본문 8, 커맨드 2, fixture 1, CLAUDE.md
- 보조 에이전트 프롬프트 3종 (`implementer-prompt.md` / `reorder-prompt.md` / `spec-reviewer-prompt.md`) **무변경** — task 전문을 붙여넣는 방식이라 계획서 레이아웃과 무관
- 기존 계획서 소급 적용 없음 — 새 규약은 머지 후 작성되는 계획서부터
- 테스트 코드는 그대로 자연어 `**검증**:` 유지 — 이번 강제화는 구현 코드 전용
- og-* / worktree 계열 / fast-tasks 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
