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

- Use `superpowers:writing-skills` to develop and test changes
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

## generating-html ↔ change-history 결합

`generating-html` skill은 "doc이 still 초안 단계인지" 판정하는 신호로 **`## 변경이력` footer가 비어 있는지 여부**를 직접 사용한다 (`skills/generating-html/SKILL.md` 의 HARD-GATE / When-to-Use 표 / preflight 검사 / dot 다이어그램 4개 판정 지점). 즉:

- footer entry 0건 → 초안 → generating-html 발동
- footer entry 1건 이상 → live doc → generating-html skip

이 결합 때문에 `change-history` skill의 "doc 최초 생성 시 자동으로 boilerplate entry를 logging하는 룰"을 제거하려면 **반드시 generating-html의 발동/중단 신호도 동시에 교체**해야 한다 (예: frontmatter `status` 플래그 / 첫 git commit 존재 여부 / 자동 발동 자체 폐지). 한쪽만 건드리면 다음 회귀가 발생한다:

- footer가 영구적으로 빈 채로 남음 → 이후 사용자가 부분 수정을 요청할 때마다 generating-html가 재발동 (의도와 반대)

요약: 이 두 skill의 룰 변경은 atomic하게 묶어 처리할 것.

### v2.8.2+ 분기 — 자동 발동 폐지로 결합 해소

v2.8.2 에서 위 옵션 중 "자동 발동 자체 폐지" 를 채택. generating-html 은 커맨드 전용 (`disable-model-invocation: true`) 이 됐고 어떤 skill 흐름도 자동 invoke 하지 않는다. footer empty 신호는 이제 "발동 트리거" 가 아니라 명시 호출 시 preflight 의 draft/live 경계 검사 (draft → 본 skill / live → `/sync-html` 안내) 로만 쓰인다. change-history 의 boilerplate entry 룰은 그대로 — 향후 그 룰을 바꿔도 generating-html 재발동 회귀는 더 이상 발생하지 않는다 (자동 발동 경로 부재). 자세한 내용은 "generating-html 커맨드 강등 (v2.8.2+)" 섹션.

## writing-plans `**Model**:` 필드 ↔ js-super-sub-driven 결합

`writing-plans` 의 task block 신규 `**Model**:` 필드 (v1.1.14+) 는 `js-super-sub-driven` 의 implementer dispatch model 결정에 직접 사용된다 (`skills/js-super-sub-driven/SKILL.md` Plan Analysis & Wave Build 단계). 즉:

- writing-plans 의 평가 룰 (haiku/sonnet/opus 분기) 변경 시 `js-super-sub-driven` 의 dispatch 단계도 동시 수정
- 한쪽만 건드리면 다음 회귀 발생: plan 작성 시 의도한 모델과 실제 dispatch 모델 불일치

요약: 이 두 skill 의 `**Model**:` 룰 변경은 atomic 하게 묶어 처리할 것.

## scripts/preflight.py ↔ 4 skill Pre-flight 결합

v1.1.14+ 에서 `scripts/preflight.py` 가 generating-html / code-pretty / executing-plans / js-super-sub-driven 4 skill 의 Pre-flight 검사를 deterministic 코드로 통합. 즉:

- `scripts/preflight.py` 의 함수 시그니처 (반환값 형식 / exit code 룰) 변경 시 4 skill 본문의 bash one-liner 도 동시 수정
- helper 의 매개변수 추가 시 모든 caller 의 호출 라인 동기화 필요

요약: 이 helper 와 4 skill 의 Pre-flight 섹션 변경은 atomic 하게 묶어 처리할 것.

### v1.1.15+ — `human_reason` 필드 + 사용자 게이트 결합

`scripts/preflight.py` 의 `PreflightResult.human_reason` 필드 추가 (v1.1.15+) 와 4 skill 의 user-gate boilerplate (FR-4) 는 결합되어 있다:

- helper 의 `human_reason` 필드 시그니처 변경 시 4 skill bash one-liner 의 `result.human_reason` 출력 표현식도 동시 수정
- user-gate boilerplate 의 AskUserQuestion choices 변경 시 4 skill 동시 적용 (한 군데만 누락 시 사용자 마찰 일관성 깨짐)

요약: helper schema + user-gate boilerplate 변경은 atomic 하게 묶어 처리할 것. 5 파일 (preflight.py + 4 skill SKILL.md) 동시 push.

## TaskCreate 명칭 룰 (v1.1.15+, FR-6)

js-super 자체 skill 의 Checklist 본문에 박힌 task 명칭은 **사용자 시야 (TaskCreate UI) 에 직접 노출**됨. 다음 룰 적용:

- **사용자 친화 한국어 표현 사용** — 내부 용어 (`Invoke ... skill`, `Gate #N`, `CH-id`, `verifying-spec`, `generating-html` 등 영어 식별자) 미노출
- **본문의 다른 부분 (Process Flow, Detailed Step) 의 영어 식별자는 유지** — 메인 에이전트가 정확한 skill 호출에 필요
- **upstream og-* skill 들 (verbatim)** — 손대지 않음
- **변경이력 footer 의 entry tag** (`[요구사항-수정]` 등) — schema 매직 키워드라 유지

신규 skill 작성 시도 본 룰 따를 것. 회귀 시 `grep -nE "Invoke .* skill|Gate #|CH-[0-9]" <skill 본문 Checklist>` 로 catch.

## auto-flow ↔ 기존 4 skill mirror 결합 (v1.1.17+)

`auto-flow` 4 신규 skill (skills/auto-{brainstorming,tech-design,writing-plans,executing-plans}/) 은 기존 4 skill 의 핵심 로직을 mirror 한 패턴 (og-* 와 동일). 다음 룰 적용:

- **기존 4 skill body 변경 0** — auto-* 본문은 self-contained mirror. 본 4 skill 어떤 라인도 손대지 않음. 회귀 catch: `git diff HEAD~1 HEAD -- skills/{brainstorming,tech-design,writing-plans,executing-plans}/SKILL.md` empty 보장.
- **Gate #14 (실행 모드 선택) override 명시** — v1.1.12+ "자동승인 절대 X" 룰을 auto-executing-plans 가 명시 override. 일반 `/execute-plan` 영향 0 (게이트 그대로). auto-* 명시적 invoke 시에만 작동.
- **generating-html fire-and-forget dispatch — v2.8.2 에서 폐지** (v2.3.2+ 도입 → v2.8.2 반전) — auto-brainstorming Step 4.5 / auto-tech-design Step 4.5 / auto-writing-plans Step 4.6 의 `run_in_background: true` dispatch 는 v2.8.2 커맨드 강등에서 제거됨. 회귀 catch 반전: 3 skill 본문에 `generating-html` dispatch 매치 0 이어야 함 (`grep -n "generating-html.*dispatch" skills/auto-{brainstorming,tech-design,writing-plans}/SKILL.md` → 안티 패턴 표의 금지 라인 외 0). 자세한 내용은 "generating-html 커맨드 강등 (v2.8.2+)" 섹션.
- **AskUserQuestion 호출 부재** — auto-* 본문 어디에도 AskUserQuestion 호출 X. clarifying Q 는 메인 turn 의 일반 prose 질의로 처리.
- **Visual Companion / 카테고리 미니질문 / question plan 동의 등 PRD-mode 분기 부재** — Socratic only (D3).

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

### 적용 8 영역 (atomic)

1. `skills/writing-plans/SKILL.md` — 검증 필드 스키마 + 템플릿 + placeholder 룰 반전 + Model sonnet floor
2. `skills/auto-writing-plans/SKILL.md` — mirror 3곳 동기 (페어 atomic)
3. `skills/js-super-sub-driven/implementer-prompt.md` — 구현=byte-copy / 테스트=자체 작성 분리 + 하위 호환 분기
4. `skills/js-super-sub-driven/SKILL.md` — 조건부 dispatch (신규 테스트 포함 task = `**Model**:` 값, 최소 sonnet / 순수 byte-copy = haiku)
5. `skills/executing-plans/SKILL.md` — 테스트 소스 분기 섹션 + 룰 2 dispatch row
6. `PROMPT_KO.md` — writing-plans 한국어 mirror
7. `CLAUDE.md` — v2.0.0 결합 메모 갱신 + 본 섹션
8. fixtures — H12 갱신 + H15 신규 (H15-natural-lang-verify — H14 는 depth-select 가 선점) + G5/G6 기대값 갱신

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
grep -c "Other / 모호 응답 처리 (v2.1.1+)" \
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

## generating-html `.html` companion 결합 (v2.2.0 → v2.2.2+)

**v2.2.0**: `generating-html` 가 두 subagent 병렬 dispatch (A `.md` format-only + B `.html` 시각화).
**v2.2.1+**: A 제거 + B fire-and-forget — 메인 latency 거의 0 + 비용 절반. 신규 `/sync-html` slash command + `change-propagation` 자동 호출 + 디바운스 3초 + silent log.

AI 흐름 영향 0 (v2.2.0 답습 — 모든 skill `.md` 만 읽음).

다음 5 파일 결합 변경 atomic patch 룰 (v2.2.1+):

1. `skills/generating-html/SKILL.md` — Procedure Step 2 (병렬 두 dispatch → 단일 fire-and-forget) + Step 3 (A+B reconcile 제거 → 즉시 return + silent log) + Anti-Patterns 갱신
2. `skills/generating-html/html-companion-prompt.md` — Subagent B prompt 그대로 보존 (v2.2.0 룰)
3. `skills/change-propagation/SKILL.md` — Acceptance 5번 + Related Skills 끝에 `/sync-html` 라인 추가
4. `commands/sync-html.md` — 신규 slash command (fire-and-forget B dispatch 명시 호출)
5. CLAUDE.md — 본 섹션

`.gitignore` 변경 X (v2.2.0 의 `docs/features/**/*.html` 그대로 + `.js-super/html-regen.log` 는 기존 `.js-super/` glob 흡수).

### 회귀 패턴 (안전성 손상 시)

| 안티 패턴 | 증상 |
|---|---|
| 외부 CDN 참조 (`https://cdn.jsdelivr.net/...`) | `.html` offline 깨짐, D4 self-contained 위반 |
| AI 가 `.html` 읽기 (`Read *.html` / `read_file *.html`) | 의미 drift 흐름 진입 위험, `.md` source-of-truth 손상 |
| `.html` git commit | `.gitignore` 차단 — repo 무게 ↑, 변경이력 polution |
| B 의 `.md` 의역 / 요약 / 재구조화 | D3 semantic 1:1 룰 위반, `.html` 가 source-of-truth 와 diverge |
| live doc 진입 후 `.html` 강제 재생성 (`/sync-html` 우회) | `change-propagation` 마지막 단계 또는 사용자 수동만 허용 |
| 메인이 fire-and-forget 결과 대기 (v2.2.1+) | latency 의도 무화 — `run_in_background=true` 강제 |
| A (`.md` format-only) 부활 시도 (v2.2.1+) | v2.2.1 의 단순화 무화 — RAW `.md` 가 사용자 리뷰 surface |
| 디바운스 skip (연속 fix 매번 dispatch) (v2.2.1+) | 비용 누적 — 3초 디바운스 + 이전 cancel 강제 |
| `change-propagation` 마지막 단계 `/sync-html` 누락 (v2.2.1+) | live doc `.html` 영구 stale — Acceptance 5번 룰 위반 |

### 영향 범위

- `generating-html` Procedure + `change-propagation` Acceptance + 신규 `/sync-html` command 만 영향
- `code-pretty` / 4 워크플로 skill (brainstorming/tech-design/writing-plans/executing-plans) / `change-history` / `auto-*` / `og-*` 영향 0
- AI 흐름 모든 skill `.md` 만 읽음 (영향 0 보장)
- `.html` 은 사람 전용 derived view, gitignored
- silent log (`.js-super/html-regen.log`) — gitignored, debug 용

### Regression catch grep

```bash
# Anti-Pattern: 외부 CDN / .html 의존성
grep -nE "https?://.*\.(css|js)|read_file.*\.html|Read.*\.html" \
  skills/generating-html/SKILL.md skills/generating-html/html-companion-prompt.md
# expected: 0 (Anti-Pattern catch 라인만 허용)

# Anti-Pattern: 다른 skill 본문에 .html 참조
grep -rn "\.html" \
  skills/{brainstorming,tech-design,writing-plans,executing-plans,auto-*,og-*}/SKILL.md
# expected: 0 (.html 흐름은 generating-html 전용)

# v2.2.1+ Anti-Pattern: 메인이 결과 대기 (fire-and-forget 위반)
grep -nE "await.*Task|sync.*dispatch.*\.html" skills/generating-html/SKILL.md
# expected: 0

# v2.2.1+ Anti-Pattern: A (.md format-only) 부활
grep -nE "format-only pass on .*\.md|Subagent A" skills/generating-html/SKILL.md
# expected: 0

# v2.2.1+ change-propagation 자동 호출 보장
grep -c "/sync-html" skills/change-propagation/SKILL.md
# expected: ≥ 1
```

요약: 5 파일 (generating-html/SKILL.md + html-companion-prompt.md 보존 + change-propagation/SKILL.md + commands/sync-html.md + CLAUDE.md) + H17 patch + H18 신규 + 6 manifest 변경은 atomic patch.

## generating-html 디자인 톤 자유 + 인터랙션 허용 (v2.2.4+)

v2.2.4+ 에서 `skills/generating-html/html-companion-prompt.md` 본문 재작성 — "사무 / 회의록 / 보고서 톤 금지" 명시 + 톤 inspiration 6종 (docs portal / dashboard / editorial / playful / brutalist / experimental) 매 호출 자유 선택 + 인터랙션 허용 (기존 "정적 페이지만" 룰 해제). 적극 시각 요소 (hero / glassmorphism / aurora bg / card grid / animated typography) + 인터랙션 (`<details>` / tab / sticky TOC / copy 버튼 / smooth scroll / scroll-spy) 명시.

핵심: **고정 톤 없음, 매번 다르게 = variety as feature**.

보존 룰: self-contained (inline only) / 의미 1:1 / offline 렌더 / 헤더·코드 블록 count 검증. AI 흐름 / skill schema / fire-and-forget 모드 변경 0.

회귀 catch grep:
```bash
grep -c "Wow first\|variety = feature\|사무 / 회의록 / 보고서 톤" skills/generating-html/html-companion-prompt.md
# expected: ≥ 3
```

요약: html-companion-prompt.md 만 변경. atomic patch 1 파일 + CLAUDE.md 결합 메모 + 6 manifest bump.

## generating-html Visual heuristics 적극 시각화 (v2.2.3+)

v2.2.3+ 에서 `skills/generating-html/html-companion-prompt.md` 의 Visual heuristics 룰 강화 — 보수적 (typography + color) → 적극 시각화 (비교 카드 / 콘셉트 도식 / 위험 카테고리 색깔 / stepper / 체크박스). `.md` 본문 패턴 ↔ `.html` 시각 표현 매핑 12 항목 표 + Anti-Patterns "typography + color 만 = 회귀" 명시.

영향: html-companion-prompt.md 본문만. AI 흐름 + skill schema / 발동 boundary / fire-and-forget 모드 모두 변경 X.

회귀 catch grep:
```bash
grep -c "적극 시각화 v2.2.3" skills/generating-html/html-companion-prompt.md
# expected: ≥ 1
```

요약: html-companion-prompt.md 만 변경. atomic patch 1 파일 + CLAUDE.md 결합 메모 + 6 manifest bump.

## generating-html naming 일관성 결합 (v2.2.2+)

v2.2.2+ 에서 `docs-pretty` → `generating-html` skill 명칭 + `/regen-html` → `/sync-html` slash command 명칭 일괄 교체. 다음 룰 atomic patch:

- **5 항목 atomic** — skill 디렉토리 rename + slash command rename + 13 파일 단어 swap + CLAUDE.md 결합 메모 + manifest 항목
- **단어 grep 0 검증** — `grep -rn "docs-pretty\|regen-html" skills/ commands/ CLAUDE.md README.md --exclude-dir=og-* --exclude-dir=H4-preflight-fail --exclude-dir=H5-docs-pretty-pre-review --exclude-dir=H6-task-name-friendly` → 0
- **Acceptance 5번 자동→안내** — `change-propagation` 마지막 단계의 `/sync-html` 자동 호출 → 사용자 안내로 완화 (auto-fire X). 사용자가 명시 호출
- **commands/regen-html.md 삭제** — old slash command 제거 (sync-html.md 신규 생성으로 대체)

## AskUserQuestion 도구 우선 (v2.3.5+)

메인 에이전트가 사용자에게 **결정 / 선택 / 동의** 를 요청하는 모든 경우 → **AskUserQuestion 도구 호출** default. skill body 외 ad-hoc 결정에도 동일 적용.

### 적용 대상

- 모든 skill body 안 게이트 (기존 v2.0.3+ 8 skill boilerplate)
- 메인 turn 의 ad-hoc 결정 요청 (skill body 무관)
- v2.3.5+ execute-plan 룰 1 (critical 7 케이스) 재질문
- 사용자가 모호 응답 시 재질문 (v2.1.1+ Other 룰)
- 모드 선택 게이트 진입 시점
- BLOCKED → self-correct / reorder 도 실패 시 사용자 개입

### prose 예외 (좁게)

- 자유 텍스트 / 긴 응답 요구 (open brainstorming question 등)
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

## 비동기 .html 신뢰성 룰 (v2.4+)

`generating-html` 백그라운드 호출이 처음 .md 생성 시 가끔 실패하던 회귀를 해결한 4 룰입니다.

- **B-1 dispatch 결과 verify**: 호출 직후 메인이 id 를 받았는지 확인하고, 시간 경과 후 `.html` 파일 존재를 확인.
- **B-2 race condition 해결**: dispatch 후 5초 delay 를 두고 그 다음 change-history footer 를 추가. background subagent 가 footer 0건 시점에 .md 를 읽도록 보장.
- **B-3 silent log monitor**: `.js-super/html-regen.log` 에 호출 / 성공 / 실패 entry 를 자동 append. `/sync-html --check` 으로 사용자 조회 가능.
- **B-4 메인 응답에 dispatch 결과 명시**: transition notice 시점에 "백그라운드 호출 완료 (N KB)" 또는 "실패 — 사용자가 `/sync-html` 으로 재시도 필요" 를 함께 알림.

자동 retry 는 도입하지 않습니다 (사용자 의도 외 비용 누적 위험). 사용자가 명시 호출 (`/sync-html`) 으로 재시도. 자동 retry 는 v2.4.x 후속 후보.

회귀 catch grep:

```bash
grep -c "silent log monitor (v2.4+)" skills/generating-html/SKILL.md
# expected: ≥ 1
```

요약: v2.4 메이저 — A 광범위 (10+ skill + 10+ commands + README + CLAUDE.md) + B 4 룰 (generating-html + auto-* 3 race delay + `/sync-html --check`). atomic 처리.

### v2.8.2+ 분기 — B-2 폐지 + B-1/B-4 적용 범위 축소

v2.8.2 커맨드 강등으로 auto-* 3 skill 의 자동 dispatch 가 사라지면서:

- **B-2 (5초 race delay) 폐지** — race 자체가 자동 발동 (dispatch 직후 change-history 가 footer 를 채우던 시점) 전용이었음. 옛 grep (`grep -c "5초 delay" skills/auto-*/SKILL.md` 각 ≥ 1) 은 반전 — 이제 0 이어야 함.
- **B-1 / B-4 는 명시 호출 경로만** — `/sync-html` / `/audit-risk` 등. B-3 silent log 는 그대로.

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
  skills/og-brainstorming/SKILL.md \
  skills/og-writing-plans/SKILL.md \
  skills/og-executing-plans/SKILL.md \
  commands/fast-tasks.md \
  skills/worktree-merge-back/SKILL.md 2>/dev/null
# expected: empty
```

요약: 8 skill body 분기 + 8 commands 안내 + CLAUDE.md 결합 메모 + 6 manifest bump = 23 파일 atomic patch.

## worktree cleanup 자동화 결합 (v2.5.1+)

v2.5.1+ 에서 `worktree-merge-back` 자동화 강화 + `worktree-remove` 신규 슬래시 명령 도입.

### 적용 범위 (5 본문 + 6 manifest = 11 파일)

- `skills/worktree-merge-back/SKILL.md` — Step 3 머지 대상 변경 (origin → 로컬) + 충돌 처리 완화 (재귀 머지 자동) + Step 4.5 신규 (env 동기화) + Step 5 보강
- `commands/worktree-merge-back.md` — 안내 동기화
- `skills/worktree-remove/SKILL.md` — 신규
- `commands/worktree-remove.md` — 신규
- `CLAUDE.md` — v2.0.4+ Anti-Pattern 표 v2.5.1+ 분기 + 본 섹션
- 6 manifest — 버전 2.5.1

### 핵심 룰

- **D-1 머지 대상** = parent 워크트리의 로컬 브랜치 (origin 자동 fetch X). 사용자가 remote 동기화 원하면 진입 전 별도 `git fetch` + pull
- **D-2 충돌 처리** = git default 재귀 머지 자동 + 실제 conflict marker 만 사용자 prose 안내. `--strategy ours/theirs` 자동 적용 절대 X (v2.0.4+ 안전성 유지)
- **D-3 env 파일 동기화** = LLM 변경 의미 판단 + 각 파일 1줄 prose 보고 + 선택적 cp (`cp -P` symlink 보존). silent cp 절대 X
- **D-4 worktree-remove** = 독립 슬래시 명령 (chain X). worktree-merge-back 의 Step 5 종료 메시지에 호출 안내만
- **D-5 HARD-GATE worktree-only** = 두 skill 모두 유지 (main 워크트리 차단). 안전성 핵심
- **D-6 worktree-remove 브랜치 삭제 default** = safe (-d). `--force` 옵트인 플래그 명시 시만 force (-D)

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
test -f skills/worktree-remove/SKILL.md && test -f commands/worktree-remove.md
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
| skill body 만 변경 | `/worktree-merge-back` 슬래시 명령 본문이 옛 표현 유지 → 사용자 혼란 |
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
- 1회성 / 메타 skill — `change-history`, `risk-annotation`, `generating-html`, `verifying-spec`, `using-superpowers`, `writing-skills` 등 (task 분해 의미 없음)

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
         skills/js-super-sub-driven/SKILL.md skills/og-writing-plans/SKILL.md \
         skills/og-executing-plans/SKILL.md; do
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
  skills/js-super-sub-driven/SKILL.md \
  skills/og-writing-plans/SKILL.md \
  skills/og-executing-plans/SKILL.md
# expected: 9 lines (모두 매치)

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

- **D-1 마커 = 출처 표식** — frontmatter 필드(로더 호환 리스크) / 중앙 manifest(desync + FR-2 "다른 프로젝트 안 보임" 충돌) 대신 디렉토리 안 마커 파일 채택. `test -f` 만으로 deterministic 판별
- **D-2 생성 스코프 미지정 시 질문** — 조용한 기본값 없음 (사용자가 매번 프로젝트/전체 선택)
- **D-3 조회/삭제 범위 = 현재 프로젝트 cwd `.claude/skills` + 전체** — 다른 프로젝트 스캔 X (중앙 레지스트리 없음)
- **D-4 삭제 차단은 `--force` 로도 우회 X** — 마커 부재 = 무조건 차단 (핵심 안전 게이트)
- **D-5 빌더 3종 모두 command** — `skills/` 아래 변환 X (자동 발동 사고 방지, META-BUILDER 룰 답습)
- **D-6 마커는 신뢰 신호일 뿐 보안 경계 아님** — 수동 복사 위조 가능, 낮은 빈도 수용

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| new-skill 마커 작성 누락 | 생성한 skill 이 `/list-skills` 에 안 뜨고 `/remove-skill` 로도 못 지움 |
| remove-skill § 4-0 차단 게이트 약화 | 비-js-super skill 삭제 가능 → v2.7 핵심 안전성 손상 |
| `--force` 가 마커 게이트 우회 | 동일 — 안전성 손상 |
| list-skills 다른 프로젝트 스캔 추가 | FR-2 "다른 프로젝트 안 보임" 위반 + 빌더 단순성 손상 |
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
- 범위 밖: 비-js-super 강제 삭제 우회 / 옛 마커 없는 skill 마이그레이션 / 다른 프로젝트 조회·삭제

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
- `subagent-driven-development`/`finishing-a-development-branch`/`using-git-worktrees` (upstream untouched) 는 og 커맨드가 그대로 참조 — 영향 0.
- tests fixture (`skills/js-super-sub-driven/tests/H1/H2/H13`) 는 옛 라우팅 명칭 참조 — 실행 무관 문서, 후속 정리 대상.
- 실행 기록: `docs/og-커맨드전용화-실행기록.md`

### auto-* 확장 (같은 배치) — 체인 안전 문구 필수

같은 원리를 auto-* 4종에도 적용. 단 og-* 와 **결정적 차이 하나**: auto-* 는 서로를 자동 호출하는 **체인**이다 (auto-brainstorming → auto-tech-design → auto-writing-plans → auto-executing-plans).

- **체인은 스킬 이름으로 호출** (`js-super:auto-tech-design` invoke 등, `auto-brainstorming:93` / `auto-tech-design:69` / `auto-writing-plans:95`). SlashCommand 아님. → **커맨드에 `disable-model-invocation: true` 걸어도 체인 안 끊김.** (안전)
- **커맨드 4종** → `disable-model-invocation: true`. auto-flow 는 승인 게이트 자동 통과 + subagent 강제 실행이라, 모델 자동 발동 차단이 og-* 보다 더 중요.
- **스킬 4종 description** → 진입 제약 문구. **체인 스킬(2~4단계)은 반드시 "커맨드 또는 앞 단계의 명시 invoke 로만 진입, 자유 요청에서 자동 선택 금지"** 로 써야 한다. 그냥 "do NOT auto-select" 만 쓰면 체인 invoke 시 모델이 주저할 수 있음.
- **auto-* 는 upstream mirror 아님** (js-super 자작 self-contained mirror, v1.1.17+). og-* 의 mirror 룰 예외 논리 불필요 — description 자유 수정 OK.
- **본문 룰 보존**: auto-* 의 "AskUserQuestion 호출 X / Socratic prose-default / Step 4.5·4.6 fire-and-forget" 등 기존 결합 룰은 description 만 바꿨으니 영향 0.

#### auto-* 회귀 catch grep

```bash
# 커맨드 4종 플래그
grep -lF "disable-model-invocation: true" commands/auto-brainstorm.md commands/auto-tech-design.md commands/auto-write-plan.md commands/auto-execute-plan.md
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

## generating-html 커맨드 강등 (v2.8.2+)

v2.8.2 에서 `generating-html` 을 기본 플로우에서 완전히 제거하고 명시 호출 전용으로 강등. 배경: 백그라운드 자동 발동이 간헐적으로 누락되던 문제 (사용자 catch) + og/auto 커맨드 전용화 (v2.8.1) 와 같은 컨텍스트 절감 원리.

### og-* (v2.8.1) 와 다른 점 — 스킬 삭제가 아니라 플래그 강등

og-* 는 스킬을 삭제하고 커맨드에 인라인했지만, generating-html 은 **스킬 유지 + frontmatter `disable-model-invocation: true`**. 이유: (1) `html-companion-prompt.md` 자산을 `/sync-html` 이 그대로 공유 — 스킬 디렉토리가 자산의 집, (2) preflight user-gate / 디바운스 / silent log 등 절차가 커맨드 인라인엔 과함, (3) `disable-model-invocation: true` 만으로 description 컨텍스트 상주 제거 + 모델 자동 발동 차단이 동시에 해결됨.

### 실제 변경 (10 본문 + 6 manifest)

1. `skills/generating-html/SKILL.md` — frontmatter 플래그 + description 재작성 + HARD-GATE / When-to-Use / dot / Related Skills / B-2 를 명시 호출 전용으로 정리
2. `skills/brainstorming/SKILL.md` — Checklist 항목 6 삭제 + dot 노드 + Process detail step 6 + Gate #8 문구
3. `skills/tech-design/SKILL.md` — Checklist 항목 6 삭제 + dot + Process detail step 6 + Gate #11 문구 + After Save 재구성
4. `skills/writing-plans/SKILL.md` — Checklist 항목 8 삭제 + dot + After Save step 3 삭제 (code-pretty 는 유지)
5. `skills/code-pretty/SKILL.md` — "BEFORE generating-html" 타이밍 표현을 "before user review" 로 교체 (플로우 위치 불변)
6. auto-* 3 (`auto-brainstorming`/`auto-tech-design`/`auto-writing-plans`) — Step 4.5/4.6 섹션 + Checklist 항목 + description 문구 삭제, 안티 패턴 표를 "호출 (모든 형태) NEVER" 로 강화
7. `README.md` — 스킬 분류에 명시 호출 전용 표기
8. `CLAUDE.md` — 본 섹션 + 기존 3 섹션 (change-history 결합 / auto-flow mirror / 비동기 신뢰성) 분기 노트

### 유지된 것 (변경 0)

- `/sync-html` 커맨드 — live doc `.html` sync 의 정본 경로. `html-companion-prompt.md` 직접 사용 (스킬 안 거침 → 플래그 영향 0)
- `html-companion-prompt.md` — 그대로 보존 (v2.2.4 디자인 톤 자유 룰 포함)
- `scripts/preflight.py:docs_pretty_check` — 명시 호출 시 여전히 사용
- `change-propagation` 의 `/sync-html` 안내 / `fast-tasks` 의 금지 목록 / `auto-executing-plans` 의 "호출 X" — 이미 미호출이라 그대로
- AI 흐름은 `.md` 만 읽음 / `.html` gitignore — 모두 유지

### 회귀 패턴

| 안티 패턴 | 증상 |
|---|---|
| 기본 플로우 skill 이 generating-html 을 다시 invoke | 간헐적 미발동 문제 재발 + 컨텍스트 낭비 |
| frontmatter `disable-model-invocation: true` 제거 | description 상주 부활 + 모델 자동 발동 부활 |
| auto-* 에 Step 4.5/4.6 dispatch 부활 | v2.8.2 강등 무화 |
| 5초 race delay 재도입 | 폐지된 B-2 부활 — 자동 발동 없인 무의미 |

### 회귀 catch grep

```bash
# 스킬 플래그 유지
grep -F "disable-model-invocation: true" skills/generating-html/SKILL.md
# expected: 1

# 기본 플로우 + auto-* 본문에 generating-html 발화 잔존 X (안티 패턴 표의 금지 라인 제외)
grep -rn "generating-html" skills/{brainstorming,tech-design,writing-plans}/SKILL.md
# expected: 0
grep -n "generating-html" skills/auto-{brainstorming,tech-design,writing-plans,executing-plans}/SKILL.md | grep -v "NEVER\|호출 X"
# expected: 0

# 5초 delay 폐지 확인
grep -c "5초 delay" skills/auto-brainstorming/SKILL.md skills/auto-tech-design/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: 각 0
```

### 영향 범위

- 스킬 8 본문 + README + CLAUDE.md + 6 manifest. commands / scripts / hooks 변경 0.
- 기본 플로우의 사용자 리뷰는 이제 RAW `.md` 만 (`.html` 은 사용자가 원할 때 명시 생성).
- `/sync-html` / `/audit-risk` 명시 호출 경로 영향 0. og-* / worktree 계열 영향 0.
- tests fixture 의 옛 발화 시나리오 (H5 등) 는 실행 무관 문서 — 후속 정리 대상.

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

- 3 본문 + 6 manifest. `setup-memory-symlinks.sh` / `worktree-merge-back` / `worktree-remove` / `using-git-worktrees` (upstream) / og-* / auto-* 영향 0
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

- skill 본문 9 + commands 4 + `scripts/preflight.py` + fixture H14 + CLAUDE.md. 버전 bump 는 main 전용 룰에 따라 main 에서. og-* / fast-tasks / worktree 계열 / generating-html 구조 영향 0
- executing-plans / js-super-sub-driven skill 본문 변경 0 — plan 부재 안내 보강은 preflight `human_reason` 안에서
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0
