# Superpowers (슈퍼파워즈) — 한국어 전체 가이드

> 코딩 에이전트를 위한 완전한 소프트웨어 개발 방법론. 조합 가능한 스킬(skill) 세트와 에이전트가 그 스킬들을 자동으로 사용하게 만드는 초기 지침으로 구성됩니다.
>
> **원본**: https://github.com/obra/superpowers — Jesse Vincent ([Prime Radiant](https://primeradiant.com))
>
> 본 문서는 프로젝트 최상위 README, CLAUDE.md, 그리고 `skills/` 하위 14개 스킬 SKILL.md 전체를 한국어로 정리한 것입니다.

---

## 목차

1. [Superpowers란?](#1-superpowers란)
2. [기본 워크플로우 7단계](#2-기본-워크플로우-7단계)
3. [철학](#3-철학)
4. [설치](#4-설치)
5. [스킬 라이브러리 (14개)](#5-스킬-라이브러리-14개)
   - [5.1 using-superpowers — 시스템 입문](#51-using-superpowers--시스템-입문)
   - [5.2 brainstorming — 아이디어를 디자인으로](#52-brainstorming--아이디어를-디자인으로)
   - [5.3 writing-plans — 구현 계획 작성](#53-writing-plans--구현-계획-작성)
   - [5.4 using-git-worktrees — 격리된 워크스페이스](#54-using-git-worktrees--격리된-워크스페이스)
   - [5.5 subagent-driven-development — 서브에이전트 주도 개발](#55-subagent-driven-development--서브에이전트-주도-개발)
   - [5.6 executing-plans — 인라인 계획 실행](#56-executing-plans--인라인-계획-실행)
   - [5.7 test-driven-development — TDD](#57-test-driven-development--tdd)
   - [5.8 systematic-debugging — 체계적 디버깅](#58-systematic-debugging--체계적-디버깅)
   - [5.9 verification-before-completion — 완료 전 검증](#59-verification-before-completion--완료-전-검증)
   - [5.10 requesting-code-review — 코드 리뷰 요청](#510-requesting-code-review--코드-리뷰-요청)
   - [5.11 receiving-code-review — 코드 리뷰 수용](#511-receiving-code-review--코드-리뷰-수용)
   - [5.12 dispatching-parallel-agents — 병렬 에이전트 디스패치](#512-dispatching-parallel-agents--병렬-에이전트-디스패치)
   - [5.13 finishing-a-development-branch — 개발 브랜치 마무리](#513-finishing-a-development-branch--개발-브랜치-마무리)
   - [5.14 writing-skills — 새 스킬 작성](#514-writing-skills--새-스킬-작성)
6. [기여 가이드라인 (CLAUDE.md)](#6-기여-가이드라인-claudemd)

---

## 1. Superpowers란?

코딩 에이전트를 켜는 순간부터 시작됩니다. 무언가를 만든다는 신호를 보면 에이전트는 **곧장 코드를 쓰지 않습니다**. 한 발 물러서서 "당신이 정말 만들고자 하는 것이 무엇이냐"고 묻습니다.

대화에서 스펙을 끌어내면, 사용자가 실제로 읽고 이해할 수 있는 짧은 청크 단위로 보여줍니다. 디자인 승인 후엔 **"열정은 있지만 안목·판단·프로젝트 컨텍스트는 없고 테스트는 싫어하는 주니어 엔지니어"** 도 따라할 수 있을 만큼 명확한 구현 계획을 세웁니다. 이 계획은 다음을 강조합니다:

- **진짜 RED/GREEN TDD**
- **YAGNI** (You Aren't Gonna Need It)
- **DRY**

"go" 신호가 떨어지면 **subagent-driven-development** 프로세스가 시작되어, 서브에이전트들이 각 엔지니어링 작업을 수행하고, 작업 결과를 검사·리뷰하고, 다음으로 진행합니다. Claude가 사용자가 만든 계획에서 이탈하지 않고 **몇 시간이고 자율적으로 작업하는 것이 흔합니다.**

스킬은 자동으로 트리거되므로 사용자는 특별히 할 일이 없습니다. **코딩 에이전트가 그냥 슈퍼파워를 가지게 됩니다.**

---

## 2. 기본 워크플로우 7단계

| 단계 | 스킬 | 트리거 | 산출물 |
|---|---|---|---|
| 1 | **brainstorming** | 코드 작성 전 | 디자인 문서(spec) |
| 2 | **using-git-worktrees** | 디자인 승인 후 | 격리된 브랜치 워크스페이스 + 깨끗한 테스트 베이스라인 |
| 3 | **writing-plans** | spec 확정 시 | 2~5분 단위 bite-sized 작업으로 분해된 구현 계획 |
| 4a | **subagent-driven-development** | 계획 실행 (권장) | 작업당 fresh 서브에이전트 + 2단계 리뷰 |
| 4b | **executing-plans** | 계획 실행 (대안) | 체크포인트 기반 일괄 실행 |
| 5 | **test-driven-development** | 구현 중 | RED-GREEN-REFACTOR — 실패 테스트 작성, 실패 확인, 최소 코드 작성, 통과 확인, 커밋 |
| 6 | **requesting-code-review** | 작업 사이 | 계획 대비 리뷰, 심각도별 이슈 보고 (Critical은 진행 차단) |
| 7 | **finishing-a-development-branch** | 모든 작업 완료 시 | 테스트 검증, 옵션 제시(merge/PR/유지/폐기), worktree 정리 |

> **에이전트는 어떤 작업에서든 시작 전 관련 스킬을 확인합니다.** 제안이 아니라 **필수** 워크플로우입니다.

---

## 3. 철학

- **테스트 주도 개발 (TDD)** — 항상 테스트 먼저
- **체계 > 즉흥** — 추측이 아니라 프로세스
- **복잡도 감소** — 단순함이 일차 목표
- **주장보다 증거** — 성공 선언 전에 검증

---

## 4. 설치

플랫폼별로 다릅니다.

### Claude Code 공식 마켓플레이스
```bash
/plugin install superpowers@claude-plugins-official
```

### Claude Code (Superpowers 마켓플레이스)
```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### OpenAI Codex CLI
```bash
/plugins
# "superpowers" 검색 → Install Plugin
```

### OpenAI Codex 앱
사이드바 Plugins → Coding 섹션 → Superpowers 옆 `+`

### Cursor
```text
/add-plugin superpowers
```

### OpenCode
```text
Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
```

### GitHub Copilot CLI
```bash
copilot plugin marketplace add obra/superpowers-marketplace
copilot plugin install superpowers@superpowers-marketplace
```

### Gemini CLI
```bash
gemini extensions install https://github.com/obra/superpowers
gemini extensions update superpowers   # 업데이트
```

---

## 5. 스킬 라이브러리 (14개)

### 5.1 `using-superpowers` — 시스템 입문

**언제 사용**: 모든 대화 시작 시. 어떤 응답(명확화 질문 포함)보다 먼저 Skill 도구를 호출하도록 강제.

#### 핵심 규칙
- **스킬이 1%라도 적용될 가능성이 있으면 반드시 호출.**
- 스킬이 작업에 적용되면 **선택의 여지가 없음. 반드시 사용해야 함.**
- 협상 불가, 합리화 불가.

#### 지시 우선순위
1. **사용자의 명시적 지시** (CLAUDE.md, GEMINI.md, AGENTS.md, 직접 요청) — 최우선
2. **슈퍼파워즈 스킬** — 충돌 시 기본 시스템 동작 오버라이드
3. **기본 시스템 프롬프트** — 최하위

CLAUDE.md가 "TDD 쓰지 마"라고 하고 스킬이 "항상 TDD"라고 하면 → **사용자 지시 우선**.

#### 스킬 접근 방법
- **Claude Code**: `Skill` 도구 사용. 스킬 파일에 Read 쓰지 말 것.
- **Copilot CLI**: `skill` 도구.
- **Gemini CLI**: `activate_skill` 도구.

#### 사용 흐름
1. 사용자 메시지 수신 → 어떤 스킬이라도 적용 가능한가? (1%라도 yes면 호출)
2. EnterPlanMode 직전이면 → brainstorming 스킬 먼저 (이미 했으면 건너뛰기)
3. Skill 도구 호출 → "Using [스킬] to [목적]" 알림
4. 체크리스트 있으면 → TodoWrite 항목별 todo 생성
5. 스킬 그대로 따르기
6. 응답 (명확화 포함)

#### 위험 신호 (합리화 중지!)

| 생각 | 현실 |
|---|---|
| "이건 그냥 단순한 질문이야" | 질문도 작업. 스킬 확인. |
| "먼저 컨텍스트가 필요해" | 스킬 확인이 명확화 질문보다 먼저. |
| "코드베이스 먼저 탐색" | 스킬이 *어떻게* 탐색할지 알려줌. 먼저 확인. |
| "git/파일을 빨리 확인" | 파일엔 대화 컨텍스트 없음. 스킬 확인. |
| "공식 스킬 필요 없어" | 스킬이 있으면 사용. |
| "이 스킬 기억나" | 스킬은 진화. 현재 버전 읽기. |
| "이건 작업이라고 할 수 없어" | 행동 = 작업. 확인. |
| "스킬이 과하다" | 단순한 게 복잡해짐. 사용. |
| "이거 하나만 먼저" | 어떤 것도 하기 *전에* 확인. |
| "이거 생산적이야" | 무규율 행동은 시간 낭비. 스킬이 방지. |
| "그게 뭔지 알아" | 개념 아는 것 ≠ 스킬 사용. 호출. |

#### 스킬 우선순위 (다중 적용 시)
1. **프로세스 스킬 먼저** (brainstorming, debugging) — 작업 *접근법* 결정
2. **구현 스킬 다음** (frontend-design, mcp-builder) — 실행 가이드

- "X 만들자" → brainstorming 먼저, 그 다음 구현
- "버그 고쳐" → debugging 먼저, 그 다음 도메인 스킬

#### 스킬 타입
- **Rigid (엄격)**: TDD, debugging — 정확히 따르기. 규율 적응 금지.
- **Flexible (유연)**: 패턴 — 컨텍스트에 맞게 원칙 적응.

> 사용자 지시는 WHAT일 뿐 HOW가 아님. "X 추가해"가 워크플로우 건너뛰라는 뜻은 아님.

---

### 5.2 `brainstorming` — 아이디어를 디자인으로

**언제 사용**: 어떤 창작 작업(기능 생성, 컴포넌트 빌드, 기능 추가, 동작 수정) 전에 **반드시**.

#### HARD-GATE
디자인을 제시하고 **사용자 승인 전엔** 어떤 구현 스킬 호출, 코드 작성, 프로젝트 스캐폴딩, 구현 행위도 금지. **모든 프로젝트에 적용** — 단순해 보여도 마찬가지.

#### Anti-Pattern: "이건 너무 단순해서 디자인 필요 없어"
모든 프로젝트가 이 프로세스를 거칩니다. 투두리스트, 단일 함수 유틸리티, 설정 변경 — 전부. "단순한" 프로젝트야말로 검토 안 된 가정이 가장 많은 낭비를 만들어내는 곳입니다. 디자인은 짧을 수 있지만(정말 단순하면 몇 문장), **반드시 제시하고 승인받아야** 합니다.

#### 체크리스트 (각 항목을 task로 만들고 순서대로 완료)
1. **프로젝트 컨텍스트 탐색** — 파일, 문서, 최근 커밋
2. **Visual Companion 제안** (시각적 질문 예상 시) — 자체 메시지로, 다른 내용과 결합 금지
3. **명확화 질문** — 한 번에 하나씩, 목적/제약/성공 기준 이해
4. **2~3개 접근법 제안** — 트레이드오프와 추천안 포함
5. **디자인 제시** — 복잡도에 비례한 섹션, 섹션마다 사용자 승인
6. **디자인 문서 작성** — `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`로 저장 후 커밋
7. **Spec 셀프 리뷰** — placeholder, 모순, 모호성, 스코프를 인라인으로 점검
8. **사용자가 작성된 spec 검토** — 진행 전 사용자에게 spec 파일 검토 요청
9. **구현으로 전환** — writing-plans 스킬 호출 (다른 구현 스킬 금지)

> 종료 상태는 **writing-plans 호출**. frontend-design, mcp-builder 같은 다른 구현 스킬 호출 금지.

#### 프로세스
- **이해 단계**: 한 번에 한 질문, 객관식 우선, 메시지당 질문 하나, 목적/제약/성공 기준 집중
- **스코프 체크**: 여러 독립 서브시스템이면 즉시 플래그 — 분해 안 한 프로젝트의 디테일에 질문 낭비 금지
- **접근법 탐색**: 2~3개 옵션 + 트레이드오프 + 추천 + 이유
- **디자인 제시**: 단순하면 몇 문장, 미묘하면 200~300단어. 섹션마다 "여기까지 맞아 보이나요?"
- **격리/명료성을 위한 디자인**: 시스템을 작은 단위로 분해 — 단일 책임, 잘 정의된 인터페이스, 독립 이해·테스트. 큰 파일은 너무 많은 일을 하고 있다는 신호.
- **기존 코드베이스**: 변경 제안 전 현재 구조 탐색, 기존 패턴 따르기. 작업에 영향을 주는 기존 문제(비대 파일, 흐릿한 경계, 책임 엉킴)는 디자인의 일부로 표적 개선 포함. 무관한 리팩토링 제안 금지.

#### 디자인 이후
- **문서화**: validated 디자인을 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`에 작성, git 커밋
- **Spec 셀프 리뷰**: ① placeholder/TBD/TODO 스캔 ② 내부 일관성(섹션 간 모순) ③ 스코프 체크(분해 필요?) ④ 모호성 체크(두 가지 해석 가능?) — 인라인으로 수정, 재리뷰 불필요
- **사용자 리뷰 게이트**: "Spec written and committed to `<path>`. Please review it..." 사용자 승인 전 진행 금지
- **구현**: writing-plans 호출 (다른 스킬 금지)

#### 핵심 원칙
- **한 번에 한 질문** — 여러 질문으로 압도하지 말 것
- **객관식 우선** — 답하기 더 쉬움
- **YAGNI 가차없이** — 모든 디자인에서 불필요 기능 제거
- **대안 탐색** — 결정 전 항상 2~3개
- **점진적 검증** — 디자인 제시, 승인 후 다음으로
- **유연하게** — 말이 안 되면 돌아가서 재명확화

#### Visual Companion
모킹/다이어그램/시각 옵션을 위한 브라우저 기반 도구. 모드가 아니라 도구 — 수락은 "필요할 때 사용 가능"이지, "모든 질문이 브라우저로 간다"가 아님.

**제안 시점**: 다가올 질문이 시각 콘텐츠를 포함할 것 같으면 한 번 동의 요청:
> "Some of what we're working on might be easier to explain if I can show it to you in a web browser..."

이 제안은 **반드시 자체 메시지**. 명확화 질문/컨텍스트 요약과 결합 금지. 사용자 응답 전엔 진행 금지. 거절 시 텍스트 전용 진행.

**질문별 결정**: 사용자 동의 후에도 *각 질문마다* 브라우저/터미널 결정. 테스트: **사용자가 읽기보다 보기로 더 잘 이해할까?**
- 브라우저: 모킹, 와이어프레임, 레이아웃 비교, 아키텍처 다이어그램, 사이드바이사이드 비주얼 디자인
- 터미널: 요구사항 질문, 개념적 선택, 트레이드오프 목록, A/B/C/D 텍스트 옵션, 스코프 결정

UI 주제 질문이라고 자동으로 시각 질문이 아님. "이 컨텍스트에서 personality가 뭐야?"는 개념적 — 터미널. "어느 마법사 레이아웃이 더 나아?"는 시각적 — 브라우저.

---

### 5.3 `writing-plans` — 구현 계획 작성

**언제 사용**: 다단계 작업의 spec/요구사항이 있고, 코드를 만지기 전.

#### 개요
**우리 코드베이스에 대한 컨텍스트가 0이고 안목이 의심스러운** 엔지니어를 가정하여 종합 구현 계획 작성. 각 작업에 어떤 파일을 만질지, 코드, 테스트, 확인할 문서, 테스트 방법까지 모두 문서화. **bite-sized 작업** 단위로. DRY, YAGNI, TDD, 잦은 커밋.

엔지니어는 숙련됐지만 우리 도구셋·문제 도메인은 거의 모름. 좋은 테스트 디자인도 잘 모른다고 가정.

> **저장 위치**: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
> (사용자 선호가 우선)

#### 스코프 체크
spec이 여러 독립 서브시스템을 다루면, brainstorming 단계에서 서브 프로젝트로 쪼개졌어야 함. 안 됐으면 별도 계획으로 분해 제안 — 각 계획은 독립적으로 작동·테스트 가능한 소프트웨어를 산출해야 함.

#### 파일 구조
작업 정의 전, 어떤 파일이 만들어지거나 수정되는지, 각각 무엇을 책임지는지 매핑. 분해 결정이 여기서 잠금됨.
- 명확한 경계와 잘 정의된 인터페이스. 한 파일 = 하나의 명확한 책임
- 한 번에 컨텍스트에 들고 있을 수 있는 코드에 대해 더 잘 추론. 작고 집중된 파일 선호
- 함께 변하는 파일은 함께. 책임 단위로 분리, 기술 레이어로 분리 X
- 기존 코드베이스에선 패턴 따르되, 비대해진 파일이라면 분리 포함이 합리적

#### Bite-Sized 작업 단위 (각 step = 한 행동, 2~5분)
- "실패 테스트 작성" — 1 step
- "실행해서 실패하는지 확인" — 1 step
- "테스트 통과 최소 코드 구현" — 1 step
- "테스트 실행해서 통과 확인" — 1 step
- "커밋" — 1 step

#### 계획 문서 헤더 (모든 계획 필수)

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [한 문장 — 무엇을 만드는지]
**Architecture:** [2~3 문장 — 접근법]
**Tech Stack:** [핵심 기술/라이브러리]

---
```

#### 작업 구조

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

#### Placeholder 금지 (모든 step은 엔지니어가 필요한 실제 내용 포함)
**계획 실패** — 절대 쓰지 말 것:
- "TBD", "TODO", "나중에 구현", "디테일 채우기"
- "적절한 에러 처리 추가" / "검증 추가" / "엣지 케이스 처리"
- 동어반복 "검증" 필드 ("테스트를 작성한다" 처럼 무엇을/기준 없는 설명 — v2.9+)
- 테스트 코드 블록을 계획서에 싣는 것 (v2.9+ — `**검증**:` 자연어 설명으로 대체)
- "Task N과 비슷" (코드 반복할 것 — 엔지니어가 순서대로 안 읽을 수 있음)
- 무엇을 할지만 설명하고 어떻게는 안 보여주는 step (코드 step엔 코드 블록 필수)
- 어디에도 정의 안 된 타입/함수/메서드 참조

#### 셀프 리뷰
계획 작성 후 스펙을 fresh 눈으로 검토:
1. **Spec 커버리지**: 각 요구사항을 구현하는 task 짚을 수 있나? 누락 나열.
2. **Placeholder 스캔**: 위 패턴 검색 → 수정.
3. **타입 일관성**: Task 3의 `clearLayers()`가 Task 7에선 `clearFullLayers()`? 버그.

발견된 이슈는 인라인 수정. 재리뷰 불필요.

#### 실행 핸드오프
계획 저장 후 실행 옵션 제시:

> "Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Two execution options:
> 1. **Subagent-Driven (recommended)** — fresh 서브에이전트 per task, 작업 사이 리뷰, 빠른 반복
> 2. **Inline Execution** — executing-plans로 이 세션에서 실행, 체크포인트 기반 일괄

선택에 따라 subagent-driven-development 또는 executing-plans 호출.

---

### 5.4 `using-git-worktrees` — 격리된 워크스페이스

**언제 사용**: 현재 워크스페이스로부터 격리가 필요한 기능 작업 시작 시, 또는 구현 계획 실행 전.

#### 디렉토리 선택 (우선순위)

1. **기존 디렉토리 확인**:
   ```bash
   ls -d .worktrees 2>/dev/null    # 선호 (숨김)
   ls -d worktrees 2>/dev/null     # 대안
   ```
   둘 다 있으면 `.worktrees` 승.

2. **CLAUDE.md 확인**:
   ```bash
   grep -i "worktree.*director" CLAUDE.md
   ```
   선호 명시되면 묻지 말고 사용.

3. **사용자에게 질문**:
   ```
   No worktree directory found. Where should I create worktrees?
   1. .worktrees/ (project-local, hidden)
   2. ~/.config/superpowers/worktrees/<project-name>/ (global)
   ```

#### 안전 검증

**프로젝트 로컬 디렉토리 (.worktrees/worktrees)**: worktree 생성 전 ignored 검증 필수:
```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```
ignored 안 되어 있으면: `.gitignore`에 추가 → 커밋 → worktree 생성. **worktree 콘텐츠가 실수로 리포에 커밋되는 것 방지**.

**글로벌 디렉토리** (`~/.config/superpowers/worktrees`): 프로젝트 외부이므로 .gitignore 검증 불필요.

#### 생성 단계
1. **프로젝트 이름 감지**: `project=$(basename "$(git rev-parse --show-toplevel)")`
2. **Worktree 생성**:
   ```bash
   git worktree add "$path" -b "$BRANCH_NAME"
   cd "$path"
   ```
3. **프로젝트 셋업 자동 감지·실행**:
   - Node: `npm install` (package.json)
   - Rust: `cargo build` (Cargo.toml)
   - Python: `pip install -r requirements.txt` 또는 `poetry install`
   - Go: `go mod download`
4. **깨끗한 베이스라인 검증** — 테스트 실행. 실패면 보고 + 진행 여부 질문.
5. **위치 보고**:
   ```
   Worktree ready at <full-path>
   Tests passing (<N> tests, 0 failures)
   ```

#### 위험 신호
**Never**: ignored 검증 없이 생성 / 베이스라인 테스트 검증 건너뛰기 / 실패 테스트로 진행 / 디렉토리 위치 가정 / CLAUDE.md 확인 건너뛰기

**Always**: 디렉토리 우선순위 따르기 / 프로젝트 로컬은 ignored 검증 / 셋업 자동 감지·실행 / 깨끗한 베이스라인 검증

---

### 5.5 `subagent-driven-development` — 서브에이전트 주도 개발

**언제 사용**: 현재 세션 내에서 독립적 작업이 있는 구현 계획 실행 시.

#### 핵심 원칙
**작업당 fresh 서브에이전트 + 2단계 리뷰 (spec 준수 → 코드 품질) = 고품질, 빠른 반복**

서브에이전트는 격리된 컨텍스트로 디스패치. 정확히 만든 지시·컨텍스트로 그들이 집중을 유지하고 작업에 성공하도록 함. 당신의 세션 컨텍스트나 히스토리를 절대 상속하지 않음 — 필요한 것만 정확히 구성. 자신의 컨텍스트도 코디네이션 작업용으로 보존.

#### vs Executing Plans (병렬 세션)
- 같은 세션 (컨텍스트 전환 없음)
- 작업당 fresh 서브에이전트 (컨텍스트 오염 없음)
- 작업 후 2단계 리뷰: spec 준수 → 코드 품질
- 더 빠른 반복 (작업 사이 human-in-loop 없음)

#### 프로세스
1. **계획 읽기** — 모든 task 추출 (전문 + 컨텍스트), TodoWrite 생성
2. **각 task마다**:
   - implementer 서브에이전트 디스패치 (`./implementer-prompt.md`)
   - 질문 있으면 답변 후 재디스패치
   - implementer가 구현, 테스트, 커밋, 셀프 리뷰
   - **spec reviewer 디스패치** (`./spec-reviewer-prompt.md`) — 코드가 spec과 일치?
     - 아니오 → implementer가 spec 갭 수정 → 재리뷰
   - **code quality reviewer 디스패치** (`./code-quality-reviewer-prompt.md`)
     - 아니오 → implementer가 품질 이슈 수정 → 재리뷰
   - TodoWrite에서 task 완료 마크
3. **모든 task 완료 후**: 전체 구현에 대한 final code reviewer 디스패치
4. **finishing-a-development-branch** 사용

#### 모델 선택 (비용/속도 절약)
- **기계적 구현** (격리된 함수, 명확한 spec, 1~2 파일): 빠른·저렴 모델
- **통합·판단** (다중 파일, 패턴 매칭, 디버깅): 표준 모델
- **아키텍처·디자인·리뷰**: 가장 강력한 모델

#### Implementer 상태 처리
4가지 상태:
- **DONE**: spec 준수 리뷰로 진행
- **DONE_WITH_CONCERNS**: 우려사항 읽기. 정확성/스코프 우려면 리뷰 전 해결. 관찰(예: "이 파일이 커지고 있음")이면 메모하고 진행.
- **NEEDS_CONTEXT**: 부족한 컨텍스트 제공 후 재디스패치
- **BLOCKED**: 블로커 평가 — 컨텍스트 문제? 더 강한 모델 필요? 작업이 너무 큼? 계획 자체가 틀림? → 사람에게 에스컬레이션

> **에스컬레이션을 무시하거나 변경 없이 같은 모델로 재시도하지 말 것.**

#### 위험 신호
**Never**:
- main/master에서 명시 동의 없이 구현 시작
- 리뷰 건너뛰기 (spec 준수 OR 코드 품질)
- 미해결 이슈로 진행
- 구현 서브에이전트 병렬 디스패치 (충돌)
- 서브에이전트에게 계획 파일 읽게 하기 (전문 직접 제공)
- 장면 설정 컨텍스트 건너뛰기
- 서브에이전트 질문 무시
- spec 준수에 "충분히 가깝다" 수용
- 리뷰 루프 건너뛰기
- implementer 셀프리뷰가 실제 리뷰 대체하게 하기
- **spec 준수 ✅ 전에 코드 품질 리뷰 시작** (잘못된 순서)
- 어느 한쪽 리뷰에 미해결 이슈 있는데 다음 task로 이동

---

### 5.6 `executing-plans` — 인라인 계획 실행

**언제 사용**: 별도 세션에서 리뷰 체크포인트와 함께 구현 계획 실행 시.

> **주의**: 슈퍼파워즈는 서브에이전트 접근권 있는 플랫폼(Claude Code, Codex)에서 훨씬 잘 작동. 가능하면 **subagent-driven-development** 사용.

#### 프로세스
1. **계획 로드 및 비판적 검토** — 우려사항이 있으면 시작 전 사람과 논의. 없으면 TodoWrite 생성.
2. **각 task 실행**:
   - in_progress 마크
   - 각 step 정확히 따르기 (계획에 bite-sized step 있음)
   - 명시된 검증 실행
   - completed 마크
3. **개발 완료**: finishing-a-development-branch 호출

#### 도움 요청 시점 (즉시 멈추기)
- 블로커 (의존성 누락, 테스트 실패, 지시 불명확)
- 계획에 시작을 막는 critical 갭
- 지시를 이해 못 함
- 검증이 반복 실패

→ **추측 대신 명확화 요청.**

#### 이전 단계 재방문
- 파트너가 피드백 기반으로 계획 갱신
- 근본적 접근 재고 필요

→ **블로커를 강행하지 말 것 — 멈추고 묻기.**

> **명시적 사용자 동의 없이 main/master 브랜치에서 구현 시작 금지.**

---

### 5.7 `test-driven-development` — TDD

**언제 사용**: 어떤 기능/버그픽스 구현 시, 구현 코드 작성 전에.

#### 핵심 원칙
**테스트 먼저. 실패 확인. 통과시킬 최소 코드.**
- 테스트가 실패하는 걸 직접 보지 못했다면, 그게 올바른 걸 테스트하는지 모름.
- **규칙의 문자를 어기는 것은 정신을 어기는 것.**

#### Iron Law
```
실패 테스트 없이는 프로덕션 코드 없음
```

테스트 전에 코드를 썼다? **삭제. 다시 시작.**
- "참고용으로" 보관 X
- 테스트 작성하면서 "적응" X
- 보지도 X
- 삭제는 삭제

테스트로부터 새로 구현. 끝.

#### Red-Green-Refactor

##### RED — 실패 테스트 작성
무엇이 일어나야 하는지 보여주는 최소 테스트 하나.
- 한 동작
- 명확한 이름
- 실제 코드 (불가피하지 않으면 모킹 X)

##### Verify RED — 실패 보기 (필수, 절대 건너뛰지 말 것)
```bash
npm test path/to/test.test.ts
```
확인:
- 테스트가 실패 (에러 X)
- 실패 메시지가 예상대로
- 기능 누락 때문에 실패 (오타 X)

테스트 통과? → 기존 동작 테스트 중. 테스트 수정.
테스트 에러? → 에러 수정 후 올바르게 실패할 때까지 재실행.

##### GREEN — 최소 코드
테스트 통과시킬 가장 단순한 코드. 기능 추가, 다른 코드 리팩토링, 테스트 너머 "개선" 금지.

##### Verify GREEN — 통과 보기 (필수)
- 테스트 통과
- 다른 테스트도 여전히 통과
- 출력이 깨끗 (에러/경고 없음)

##### REFACTOR — 정리
green 후에만:
- 중복 제거
- 이름 개선
- 헬퍼 추출

테스트 green 유지. 동작 추가 X.

#### 좋은 테스트
| 품질 | Good | Bad |
|---|---|---|
| **최소** | 한 가지. 이름에 "and"? 분할. | `test('validates email and domain and whitespace')` |
| **명확** | 동작 설명 이름 | `test('test1')` |
| **의도 표현** | 원하는 API 시연 | 코드가 무엇을 해야 하는지 흐림 |

#### 합리화 (모두 "코드 삭제, TDD로 다시 시작" 의미)
| 변명 | 현실 |
|---|---|
| "테스트하기엔 너무 단순" | 단순 코드도 깨짐. 테스트 30초. |
| "나중에 테스트할게" | 즉시 통과 = 아무것도 증명 못 함 |
| "이미 수동 테스트함" | 임시방편 ≠ 체계적 |
| "X시간 삭제 낭비" | 매몰 비용 오류. 검증 안 된 코드 보관이 기술 부채 |
| "참고용으로 보관, 테스트 먼저" | 적응할 거잖음. 그게 사후 테스트. 삭제는 삭제. |
| "탐색 먼저 필요" | 좋아. 탐색 버리고 TDD로 시작 |
| "테스트 어려움 = 디자인 불명확" | 테스트 들어. 테스트 어려움 = 사용 어려움 |
| "TDD는 느려" | TDD가 디버깅보다 빠름 |
| "기존 코드는 테스트 없음" | 개선 중. 기존 코드용 테스트 추가 |

#### Red Flags — 멈추고 다시 시작
- 테스트 전 코드
- 구현 후 테스트
- 테스트 즉시 통과
- 왜 실패했는지 설명 못 함
- 테스트 "나중에" 추가
- "한 번만" 합리화
- "이건 다르니까..."

#### 검증 체크리스트 (작업 완료 마크 전)
- [ ] 모든 새 함수/메서드에 테스트
- [ ] 구현 전 각 테스트 실패 확인
- [ ] 각 테스트가 예상 이유로 실패 (기능 누락, 오타 X)
- [ ] 통과시킬 최소 코드
- [ ] 모든 테스트 통과
- [ ] 출력 깨끗
- [ ] 테스트가 실제 코드 사용 (불가피하면만 모킹)
- [ ] 엣지 케이스/에러 커버

체크 못 하면 → TDD 건너뛴 것. 다시 시작.

#### Final Rule
```
프로덕션 코드 → 테스트가 존재하고 먼저 실패함
그 외 → TDD 아님
```

사람의 허락 없는 예외 없음.

---

### 5.8 `systematic-debugging` — 체계적 디버깅

**언제 사용**: 어떤 버그, 테스트 실패, 예상치 못한 동작이든 — 수정 제안 전.

#### 핵심 원칙
랜덤 수정은 시간 낭비 + 새 버그. 빠른 패치는 근본 문제 가림.

**수정 시도 전에 ALWAYS 근본 원인 발견. 증상 수정은 실패.**

#### Iron Law
```
근본 원인 조사 없이는 수정 없음
```

Phase 1을 완료하지 않았다면 수정 제안 불가.

#### 4단계 (각 단계 완료 후 다음으로)

##### Phase 1: 근본 원인 조사
1. **에러 메시지 주의 깊게 읽기** — 종종 정확한 솔루션 포함. 스택 트레이스 완전히 읽기.
2. **일관되게 재현** — 매번 발생? 안 되면 추측 대신 데이터 더 모으기.
3. **최근 변경 확인** — git diff, 최근 커밋, 새 의존성, 환경 차이.
4. **다중 컴포넌트 시스템에서 증거 수집** — 컴포넌트 경계마다 진단 계측 추가:
   - 들어오는 데이터 로그
   - 나가는 데이터 로그
   - 환경/설정 전파 검증
   - 각 레이어 상태 확인
   → **어디서 깨지는지** 보여주는 증거 수집 → **그 컴포넌트** 분석.
5. **데이터 흐름 추적** — 호출 스택 깊은 곳의 에러는 잘못된 값의 출처를 거꾸로 추적. **출처에서 수정, 증상에서 X.**

##### Phase 2: 패턴 분석
1. 같은 코드베이스에서 비슷한 작동하는 예제 찾기
2. 참조 구현이 있으면 **완전히** 읽기 (대충 보기 X)
3. 작동 vs 깨짐 차이를 모두 나열 (작아 보여도 무시 금지)
4. 의존성 이해 — 다른 어떤 컴포넌트, 설정, 환경 필요?

##### Phase 3: 가설과 테스트
1. **단일 가설 형성**: "X가 근본 원인이라고 생각하는 이유는 Y" — 명확히 적기
2. **최소 테스트** — 가설 검증할 가장 작은 변경. 한 변수씩.
3. **계속 전 검증** — 작동? Phase 4. 안 됨? **새 가설** (위에 더 쌓지 말기).
4. **모를 때**: "X를 이해 못 함" 인정. 척하지 말 것. 도움 요청. 더 조사.

##### Phase 4: 구현
1. **실패 테스트 케이스 생성** — 가장 단순한 재현. 자동화 테스트가 가능하면. 수정 전 **반드시** 보유. (test-driven-development 스킬 사용)
2. **단일 수정 구현** — 식별된 근본 원인. 한 번에 한 변경. "겸사겸사" 개선 금지. 번들 리팩토링 금지.
3. **수정 검증** — 테스트 통과? 다른 테스트 안 깨짐? 실제 해결?
4. **수정 안 됨**: 멈추기. 시도 횟수 세기. <3이면 Phase 1로 — 새 정보로 재분석. **≥3이면 멈추고 아키텍처 의심**.
5. **3+ 수정 실패 시 아키텍처 의심**:
   - 각 수정이 새로운 공유 상태/결합/문제를 다른 곳에서 드러냄
   - 수정에 "대규모 리팩토링" 필요
   - 각 수정이 다른 곳에서 새 증상 생성

   **근본을 의심하라**: 이 패턴이 근본적으로 건전한가? "관성으로 그냥 유지" 중인가? 증상 수정 계속 vs 아키텍처 리팩토링?

   **추가 수정 시도 전 사람과 논의.** 이건 실패한 가설이 아니라 **잘못된 아키텍처**.

#### Red Flags — 멈추고 프로세스 따르기
이런 생각이 들면:
- "지금은 빠른 수정, 나중에 조사"
- "X 바꿔보고 작동하는지 보자"
- "여러 변경 한꺼번에, 테스트 실행"
- "테스트 건너뛰고 수동 검증"
- "아마 X일 거야, 그거 수정"
- "완전히 이해 못 하지만 작동할 수도"
- "패턴은 X지만 다르게 적응"
- "주요 문제: [조사 없이 수정 나열]"
- 데이터 흐름 추적 전에 솔루션 제안
- **"한 번만 더 시도" (이미 2+ 시도했는데)**
- **각 수정이 다른 곳에서 새 문제 드러냄**

→ 모두 **Phase 1으로 돌아가기**.

#### 사람의 신호
- "그게 안 일어나고 있나?" — 검증 없이 가정함
- "보여줄까?" — 증거 수집 추가했어야 함
- "추측 그만" — 이해 없이 수정 제안 중
- "Ultrathink" — 증상이 아니라 근본 의심
- "막혔어?" (좌절) — 접근법이 안 통함

→ **멈추고 Phase 1으로**.

#### 합리화
| 변명 | 현실 |
|---|---|
| "이슈가 단순함, 프로세스 불필요" | 단순 이슈도 근본 원인 있음. 단순 버그엔 프로세스가 빠름. |
| "비상사태, 시간 없음" | 체계적 디버깅이 추측-검증 헤매기보다 빠름 |
| "일단 시도, 그 후 조사" | 첫 수정이 패턴 설정. 처음부터 제대로. |
| "수정 후 테스트 작성" | 테스트 없는 수정은 안 굳음. 먼저 테스트가 증명. |
| "한꺼번에 여러 수정 = 시간 절약" | 무엇이 작동했는지 격리 불가. 새 버그. |
| "참조 길어, 패턴 적응" | 부분 이해 = 보장된 버그. 완전히 읽기. |
| "문제 보임, 수정" | 증상 보기 ≠ 근본 원인 이해 |
| "한 번만 더 시도 (2+ 실패 후)" | 3+ 실패 = 아키텍처 문제. 패턴 의심. |

#### "근본 원인 없음"이 드러날 때
체계적 조사가 진짜 환경/타이밍/외부 이슈를 드러내면:
1. 프로세스 완료
2. 조사 내용 문서화
3. 적절한 처리 구현 (재시도, 타임아웃, 에러 메시지)
4. 미래 조사용 모니터링/로깅 추가

**그러나**: "근본 원인 없음" 케이스의 95%는 불완전한 조사.

#### 보조 기법 (`skills/systematic-debugging/` 디렉토리)
- `root-cause-tracing.md` — 호출 스택을 거꾸로 추적해 원래 트리거 찾기
- `defense-in-depth.md` — 근본 원인 발견 후 다중 레이어에 검증 추가
- `condition-based-waiting.md` — 임의 타임아웃을 조건 폴링으로 교체

#### 실측 임팩트
- 체계적: 15~30분 수정 / 랜덤: 2~3시간 헤매기
- 첫 수정 성공률: 95% vs 40%
- 새 버그 도입: 거의 0 vs 흔함

---

### 5.9 `verification-before-completion` — 완료 전 검증

**언제 사용**: 작업이 완료/수정/통과됐다고 주장 직전, 커밋이나 PR 만들기 전.

#### 핵심 원칙
**검증 없이 완료 주장 = 효율이 아니라 부정직.**
**증거가 주장보다 먼저, 항상.**
규칙 문자를 어기는 것은 정신을 어기는 것.

#### Iron Law
```
새로 검증한 증거 없이는 완료 주장 없음
```

이 메시지에서 검증 명령을 안 돌렸다면, 통과한다고 주장 불가.

#### Gate Function
```
어떤 상태/만족 표현 전에:

1. IDENTIFY: 이 주장을 증명할 명령은?
2. RUN: 전체 명령 실행 (새로, 완전히)
3. READ: 전체 출력, exit code 확인, 실패 카운트
4. VERIFY: 출력이 주장 확정?
   - NO: 실제 상태 + 증거
   - YES: 주장 + 증거
5. ONLY THEN: 주장하기

어느 단계든 건너뛰면 = 검증이 아니라 거짓말
```

#### 흔한 실패
| 주장 | 필요 | 불충분 |
|---|---|---|
| 테스트 통과 | 테스트 명령 출력: 0 실패 | 이전 실행, "통과해야 함" |
| 린터 깨끗 | 린터 출력: 0 에러 | 부분 체크, 추정 |
| 빌드 성공 | 빌드 명령: exit 0 | 린터 통과, 로그 좋아 보임 |
| 버그 수정 | 원래 증상 테스트 통과 | 코드 변경, 수정됐다 가정 |
| 회귀 테스트 작동 | red-green 사이클 검증 | 한 번 통과 |
| 에이전트 완료 | VCS diff 변경 표시 | 에이전트 "성공" 보고 |
| 요구사항 충족 | 라인별 체크리스트 | 테스트 통과 |

#### Red Flags — 멈추기
- "should", "probably", "seems to" 사용
- 검증 전 만족 표현 ("Great!", "Perfect!", "Done!")
- 검증 없이 commit/push/PR 직전
- 에이전트 성공 보고 신뢰
- 부분 검증 의존
- "한 번만" 사고
- 피곤해서 작업 끝내고 싶음
- **검증 안 돌리고 성공 함의하는 어떤 표현**

#### 합리화 방지
| 변명 | 현실 |
|---|---|
| "이제 작동할 거야" | 검증 실행 |
| "확신함" | 확신 ≠ 증거 |
| "한 번만" | 예외 없음 |
| "린터 통과" | 린터 ≠ 컴파일러 |
| "에이전트가 성공이래" | 독립적으로 검증 |
| "피곤해" | 피곤함 ≠ 변명 |
| "부분 체크 충분" | 부분은 아무것도 증명 안 함 |
| "다른 단어니 규칙 안 해당" | 정신 > 문자 |

#### 핵심 패턴

**테스트**:
```
✅ [테스트 명령] [34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**회귀 테스트 (TDD Red-Green)**:
```
✅ 작성 → 실행(통과) → 수정 되돌리기 → 실행(반드시 실패) → 복원 → 실행(통과)
❌ "회귀 테스트 작성했음" (red-green 검증 없이)
```

**빌드**:
```
✅ [빌드 실행] [exit 0] "Build passes"
❌ "린터 통과" (린터는 컴파일 체크 안 함)
```

**요구사항**:
```
✅ 계획 재읽기 → 체크리스트 → 각 검증 → 갭/완료 보고
❌ "테스트 통과, 단계 완료"
```

**에이전트 위임**:
```
✅ 에이전트 성공 보고 → VCS diff 확인 → 변경 검증 → 실제 상태 보고
❌ 에이전트 보고 신뢰
```

#### 적용 시점

**ALWAYS 전에**:
- 어떤 형태의 성공/완료 주장
- 어떤 만족 표현
- 작업 상태에 대한 어떤 긍정적 진술
- 커밋, PR 생성, task 완료
- 다음 task 이동
- 에이전트 위임

**적용 대상**:
- 정확한 표현
- 패러프레이즈, 동의어
- 성공 함의
- 완료/정확성을 시사하는 어떤 의사소통

#### Bottom Line
**검증에 지름길 없음.** 명령 실행. 출력 읽기. 그 후에 결과 주장. **협상 불가.**

---

### 5.10 `requesting-code-review` — 코드 리뷰 요청

**언제 사용**: 작업 완료 시, 주요 기능 구현 시, 머지 전에 — 작업이 요구사항 충족하는지 검증.

#### 핵심 원칙
**일찍, 자주 리뷰.** 이슈가 연쇄되기 전에 잡기.

리뷰어는 정확히 만들어진 컨텍스트만 받음 — 당신 세션 히스토리는 절대 X. 리뷰어가 작업 산출물에 집중, 사고 과정엔 집중하지 않음. 당신 컨텍스트는 계속 작업용으로 보존.

#### 리뷰 요청 시점
**필수**:
- subagent-driven development 각 task 후
- 주요 기능 완료 후
- main 머지 전

**선택적이지만 가치 있음**:
- 막혔을 때 (새 관점)
- 리팩토링 전 (베이스라인 체크)
- 복잡한 버그 수정 후

#### 요청 방법
1. **git SHA 가져오기**:
   ```bash
   BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
   HEAD_SHA=$(git rev-parse HEAD)
   ```

2. **superpowers:code-reviewer 서브에이전트 디스패치**: Task 도구 사용, `code-reviewer.md` 템플릿 채우기.

   Placeholders:
   - `{WHAT_WAS_IMPLEMENTED}` — 방금 만든 것
   - `{PLAN_OR_REQUIREMENTS}` — 무엇을 해야 하는지
   - `{BASE_SHA}` — 시작 커밋
   - `{HEAD_SHA}` — 끝 커밋
   - `{DESCRIPTION}` — 짧은 요약

3. **피드백에 따라 행동**:
   - Critical 이슈 즉시 수정
   - Important 이슈 진행 전 수정
   - Minor 이슈 나중에 메모
   - 리뷰어가 틀렸으면 (이유 들고) 푸시백

#### 워크플로우 통합
- **Subagent-Driven Development**: 각 task 후 리뷰
- **Executing Plans**: 각 batch (3 task) 후 리뷰
- **Ad-Hoc**: 머지 전 리뷰, 막혔을 때 리뷰

#### Red Flags
**Never**:
- "단순하다"고 리뷰 건너뛰기
- Critical 이슈 무시
- 미수정 Important 이슈로 진행
- 유효한 기술 피드백과 논쟁

**리뷰어가 틀렸으면**:
- 기술 추론으로 푸시백
- 작동 증명하는 코드/테스트 보여주기
- 명확화 요청

---

### 5.11 `receiving-code-review` — 코드 리뷰 수용

**언제 사용**: 코드 리뷰 피드백 받을 때, 제안 구현 전, 특히 피드백이 불명확하거나 기술적으로 의심스러울 때.

#### 핵심 원칙
**코드 리뷰는 기술 평가지 감정 연기가 아님.**
**구현 전 검증. 가정 전 질문. 사회적 편안함보다 기술 정확성.**

#### 응답 패턴
```
코드 리뷰 피드백 받을 때:
1. READ: 반응 없이 완전히 읽기
2. UNDERSTAND: 자신 말로 요구사항 재진술 (또는 묻기)
3. VERIFY: 코드베이스 현실과 대조
4. EVALUATE: 이 코드베이스에 기술적으로 적절한가?
5. RESPOND: 기술적 인정 또는 추론 있는 푸시백
6. IMPLEMENT: 한 번에 하나씩, 각 테스트
```

#### 금지 응답
**NEVER**:
- "You're absolutely right!" (CLAUDE.md 명시 위반)
- "Great point!" / "Excellent feedback!" (가식)
- "Let me implement that now" (검증 전)

**INSTEAD**:
- 기술 요구사항 재진술
- 명확화 질문
- 틀렸으면 기술 추론으로 푸시백
- 그냥 작업 시작 (행동 > 말)

#### 불명확 피드백 처리
```
어느 항목이 불명확하면:
  STOP — 아직 구현 X
  불명확 항목 명확화 요청

WHY: 항목들이 관련됐을 수 있음. 부분 이해 = 잘못된 구현.
```

예:
```
파트너: "1-6 고쳐"
이해: 1,2,3,6. 불명확: 4,5.

❌ WRONG: 1,2,3,6 지금 구현, 4,5는 나중에 질문
✅ RIGHT: "1,2,3,6 이해. 진행 전 4와 5 명확화 필요."
```

#### 출처별 처리

**파트너 (사람)**:
- 신뢰 — 이해 후 구현
- 스코프 불명확하면 여전히 질문
- 가식 동의 X
- 행동으로 건너뛰기 또는 기술적 인정

**외부 리뷰어**:
구현 전:
1. 이 코드베이스에 기술적 정확?
2. 기존 기능 깨뜨림?
3. 현재 구현의 이유?
4. 모든 플랫폼/버전에서 작동?
5. 리뷰어가 전체 컨텍스트 이해?

→ 제안이 틀려 보이면 기술 추론으로 푸시백
→ 검증 어려우면: "X 없이 검증 불가. [조사/질문/진행]?"
→ 파트너의 이전 결정과 충돌하면 먼저 파트너와 논의

> 파트너 규칙: "외부 피드백 — 회의적이되, 신중히 확인."

#### "전문성" 기능에 대한 YAGNI 체크
```
리뷰어가 "제대로 구현" 제안하면:
  실제 사용처 grep
  미사용: "이 엔드포인트 호출 안 됨. 제거 (YAGNI)?"
  사용: 제대로 구현
```

> 파트너 규칙: "당신과 리뷰어 모두 나에게 보고. 우리가 이 기능 필요 없으면 추가 X."

#### 구현 순서
다중 항목 피드백:
1. 불명확한 것 먼저 명확화
2. 그 후 순서대로:
   - 차단 이슈 (깨짐, 보안)
   - 단순 수정 (오타, import)
   - 복잡 수정 (리팩토링, 로직)
3. 각 수정 개별 테스트
4. 회귀 없는지 검증

#### 푸시백 시점
- 제안이 기존 기능 깨뜨림
- 리뷰어가 전체 컨텍스트 부족
- YAGNI 위반 (미사용 기능)
- 이 스택에 기술적으로 부정확
- 레거시/호환성 이유
- 파트너의 아키텍처 결정과 충돌

방법: 기술 추론(방어 X), 구체적 질문, 작동 테스트/코드 참조, 아키텍처면 파트너 개입.
**소리내어 푸시백이 불편하면 신호**: "Strange things are afoot at the Circle K"

#### 정확한 피드백 인정
```
✅ "Fixed. [무엇이 바뀌었는지 짧게]"
✅ "Good catch — [구체적 이슈]. [위치]에서 수정."
✅ [그냥 코드로 보여주기]

❌ "You're absolutely right!"
❌ "Great point!"
❌ "Thanks for catching that!"
❌ "Thanks for [어떤 것]"
❌ 어떤 감사 표현
```

> **왜 감사 X**: 행동이 말함. 그냥 수정. 코드 자체가 피드백을 들었다는 걸 보여줌.
> "Thanks"를 쓰려고 하면 → **삭제. 수정 진술.**

#### 푸시백 우아하게 정정 (당신이 틀렸을 때)
```
✅ "맞아요 — [X] 확인했고 [Y]. 지금 구현 중."
✅ "검증해보니 맞음. 초기 이해 틀렸음 [이유]. 수정 중."

❌ 긴 사과
❌ 푸시백 이유 방어
❌ 과도한 설명
```

사실적으로 정정하고 진행.

#### 흔한 실수
| 실수 | 수정 |
|---|---|
| 가식 동의 | 요구사항 진술 또는 그냥 행동 |
| 맹목적 구현 | 코드베이스 먼저 검증 |
| 테스트 없이 일괄 | 한 번에 하나씩, 각 테스트 |
| 리뷰어 옳다 가정 | 기존 깨뜨리는지 확인 |
| 푸시백 회피 | 기술 정확성 > 편안함 |
| 부분 구현 | 모든 항목 먼저 명확화 |
| 검증 못 하고 진행 | 제한 진술, 방향 요청 |

---

### 5.12 `dispatching-parallel-agents` — 병렬 에이전트 디스패치

**언제 사용**: 공유 상태나 순차 의존성 없이 작업할 수 있는 2+ 독립 task 직면 시.

#### 개요
격리된 컨텍스트의 전문 에이전트에게 task 위임. 정확히 만든 지시·컨텍스트로 그들이 집중 유지·성공. 세션 컨텍스트/히스토리 절대 상속 X — 필요한 것만 정확히 구성. 자신의 컨텍스트는 코디네이션용 보존.

여러 무관한 실패(다른 테스트 파일, 다른 서브시스템, 다른 버그)를 순차 조사하면 시간 낭비. 각 조사 독립 → 병렬 가능.

**핵심**: 독립 문제 도메인당 한 에이전트. 동시 작업.

#### 사용 시점
**Use when**:
- 다른 근본 원인의 3+ 테스트 파일 실패
- 여러 서브시스템 독립 깨짐
- 각 문제를 다른 컨텍스트 없이 이해 가능
- 조사 간 공유 상태 없음

**Don't use**:
- 실패가 관련 (하나 수정 = 다른 것 수정)
- 전체 시스템 상태 이해 필요
- 에이전트가 서로 간섭

#### 패턴
1. **독립 도메인 식별**: 무엇이 깨졌는지로 그룹핑 (파일 A: 도구 승인, 파일 B: 배치 완료, 파일 C: abort) — 각 도메인 독립.
2. **포커스된 에이전트 task 생성**:
   - 구체적 스코프: 한 테스트 파일/서브시스템
   - 명확한 목표: 이 테스트 통과
   - 제약: 다른 코드 변경 X
   - 예상 출력: 발견·수정 요약
3. **병렬 디스패치**:
   ```typescript
   Task("agent-tool-abort.test.ts 실패 수정")
   Task("batch-completion-behavior.test.ts 실패 수정")
   Task("tool-approval-race-conditions.test.ts 실패 수정")
   // 셋 다 동시 실행
   ```
4. **리뷰·통합**: 각 요약 읽기, 충돌 검증, 전체 테스트 스위트 실행, 모든 변경 통합.

#### 좋은 에이전트 프롬프트
1. **포커스됨** — 명확한 한 문제 도메인
2. **자기완결적** — 문제 이해에 필요한 모든 컨텍스트
3. **출력 구체적** — 에이전트가 무엇을 반환?

```markdown
src/agents/agent-tool-abort.test.ts의 3개 실패 테스트 수정:

1. "should abort tool with partial output capture" - 'interrupted at' 메시지 기대
2. "should handle mixed completed and aborted tools" - 빠른 도구가 완료 대신 abort됨
3. "should properly track pendingToolCount" - 3 결과 기대, 0 받음

타이밍/race condition 이슈. 작업:
1. 테스트 파일 읽기, 각 테스트가 검증하는 것 이해
2. 근본 원인 식별 — 타이밍 이슈 또는 실제 버그?
3. 수정:
   - 임의 타임아웃을 이벤트 기반 대기로 교체
   - abort 구현에 버그 발견 시 수정
   - 테스트가 변경된 동작 테스트면 기대치 조정

타임아웃 늘리지 말 것 — 진짜 이슈 찾기.

반환: 발견·수정 요약.
```

#### 흔한 실수
| ❌ | ✅ |
|---|---|
| "모든 테스트 수정" (너무 광범위) | "agent-tool-abort.test.ts 수정" (포커스) |
| "race condition 수정" (컨텍스트 X) | 에러 메시지·테스트명 붙여넣기 |
| 제약 X (모든 걸 리팩토링할 수도) | "프로덕션 코드 변경 X" 또는 "테스트만 수정" |
| "수정해" (모호한 출력) | "근본 원인·변경 요약 반환" |

#### 사용하지 말 시점
- **관련 실패**: 하나 수정이 다른 것 수정 — 함께 조사
- **전체 컨텍스트 필요**: 이해에 전체 시스템 보기 필요
- **탐색적 디버깅**: 무엇이 깨졌는지 모름
- **공유 상태**: 에이전트가 간섭 (같은 파일 편집, 같은 리소스)

#### 핵심 이점
1. 병렬화 — 여러 조사 동시
2. 포커스 — 각 에이전트 좁은 스코프
3. 독립성 — 서로 간섭 X
4. 속도 — 1개 시간에 3개

#### 검증
1. 각 요약 리뷰 — 무엇이 바뀌었는지 이해
2. 충돌 확인 — 같은 코드 편집?
3. 전체 스위트 실행 — 모든 수정이 함께 작동
4. 스팟 체크 — 에이전트가 체계적 에러 가능

---

### 5.13 `finishing-a-development-branch` — 개발 브랜치 마무리

**언제 사용**: 구현 완료, 모든 테스트 통과, 작업 통합 방법 결정 필요.

#### 핵심 원칙
**테스트 검증 → 옵션 제시 → 선택 실행 → 정리.**

#### 프로세스

##### Step 1: 테스트 검증
옵션 제시 전:
```bash
npm test / cargo test / pytest / go test ./...
```
실패 시:
```
Tests failing (<N> failures). Must fix before completing:
[실패 표시]
Cannot proceed with merge/PR until tests pass.
```
멈춤. Step 2로 진행 X.

##### Step 2: 베이스 브랜치 결정
```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```
또는 묻기: "이 브랜치는 main에서 분기됐어 — 맞아?"

##### Step 3: 옵션 제시 (정확히 4개)
```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```
설명 추가 X — 간결 유지.

##### Step 4: 선택 실행

**Option 1: 로컬 머지**
```bash
git checkout <base-branch>
git pull
git merge <feature-branch>
<test command>  # 머지된 결과 검증
git branch -d <feature-branch>  # 통과 시
```
→ Step 5 (worktree 정리)

**Option 2: 푸시 + PR 생성**
```bash
git push -u origin <feature-branch>
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets>
## Test Plan
- [ ] <검증 단계>
EOF
)"
```
→ Step 5

**Option 3: 그대로 유지**
보고: "Keeping branch <name>. Worktree preserved at <path>." → worktree 정리 X

**Option 4: 폐기 — 먼저 확인**
```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```
정확한 확인 대기. 확인되면:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```
→ Step 5

##### Step 5: Worktree 정리
Options 1, 2, 4용:
```bash
git worktree list | grep $(git branch --show-current)
git worktree remove <worktree-path>
```
Option 3: worktree 유지.

#### 빠른 참조

| 옵션 | 머지 | 푸시 | Worktree 유지 | 브랜치 정리 |
|---|---|---|---|---|
| 1. 로컬 머지 | ✓ | - | - | ✓ |
| 2. PR 생성 | - | ✓ | ✓ | - |
| 3. 그대로 | - | - | ✓ | - |
| 4. 폐기 | - | - | - | ✓ (force) |

#### 흔한 실수
- **테스트 검증 건너뛰기** → 깨진 코드 머지, 실패 PR 생성 → **항상 옵션 전 검증**
- **개방형 질문** → "다음 뭐할까?" 모호 → **정확히 4개 구조화 옵션**
- **자동 worktree 정리** → 필요할 수 있는데 제거 (Option 2, 3) → **Options 1, 4만**
- **폐기 확인 없음** → 실수로 작업 삭제 → **타이핑된 "discard" 확인**

#### Red Flags
**Never**: 실패 테스트로 진행 / 결과 테스트 검증 없이 머지 / 확인 없이 작업 삭제 / 명시 요청 없는 force-push
**Always**: 옵션 전 테스트 검증 / 정확히 4개 옵션 / Option 4에 타이핑 확인 / Options 1·4만 worktree 정리

---

### 5.14 `writing-skills` — 새 스킬 작성

**언제 사용**: 새 스킬 생성, 기존 스킬 편집, 배포 전 스킬 작동 검증.

#### 핵심 원칙
**스킬 작성은 프로세스 문서에 적용된 TDD.** 테스트 케이스(서브에이전트와 압박 시나리오) 작성 → 실패 보기(베이스라인 동작) → 스킬 작성(문서) → 통과 보기(에이전트 준수) → 리팩토링(루프홀 차단).

> 에이전트가 스킬 없이 실패하는 걸 못 봤다면, 스킬이 옳은 걸 가르치는지 모름.

> **필수 배경**: 이 스킬 사용 전 superpowers:test-driven-development 이해 필수.

#### 스킬이란?
**입증된 기법, 패턴, 도구를 위한 참조 가이드.** 미래 Claude 인스턴스가 효과적 접근법을 찾고 적용하도록 도움.
- **스킬은**: 재사용 가능한 기법, 패턴, 도구, 참조 가이드
- **스킬이 아님**: 한 번 문제를 어떻게 풀었는지에 대한 서사

#### TDD 매핑 (스킬용)
| TDD 개념 | 스킬 생성 |
|---|---|
| 테스트 케이스 | 서브에이전트 압박 시나리오 |
| 프로덕션 코드 | 스킬 문서 (SKILL.md) |
| 테스트 실패 (RED) | 스킬 없이 에이전트가 규칙 위반 (베이스라인) |
| 테스트 통과 (GREEN) | 스킬 있을 때 에이전트 준수 |
| 리팩토링 | 준수 유지하며 루프홀 차단 |
| 테스트 먼저 작성 | 스킬 쓰기 **전에** 베이스라인 시나리오 실행 |
| 실패 보기 | 에이전트가 쓰는 정확한 합리화 문서화 |
| 최소 코드 | 그 위반들에 대응하는 스킬 작성 |
| 통과 보기 | 에이전트가 이제 준수 검증 |
| 리팩토링 사이클 | 새 합리화 발견 → 막기 → 재검증 |

#### 스킬 생성 시점
**Create when**:
- 기법이 직관적으로 명백하지 않았음
- 프로젝트들 간 다시 참조할 것
- 패턴이 광범위 적용 (프로젝트 특화 X)
- 다른 사람이 혜택

**Don't create**:
- 일회성 솔루션
- 다른 곳에 잘 문서화된 표준 관행
- 프로젝트 특화 컨벤션 (CLAUDE.md에)
- 기계적 제약 (regex/검증으로 강제 가능하면 자동화 — 문서는 판단 콜에)

#### 스킬 타입
- **Technique**: 따를 단계 있는 구체적 메서드 (condition-based-waiting, root-cause-tracing)
- **Pattern**: 문제 사고 방식 (flatten-with-flags, test-invariants)
- **Reference**: API 문서, 문법 가이드, 도구 문서

#### 디렉토리 구조
```
skills/
  skill-name/
    SKILL.md              # 메인 참조 (필수)
    supporting-file.*     # 필요 시만
```

**Flat namespace** — 모든 스킬이 한 검색 가능 namespace.

**별도 파일 대상**:
1. 무거운 참조 (100+ 라인) — API 문서, 종합 문법
2. 재사용 도구 — 스크립트, 유틸리티, 템플릿

**인라인 유지**: 원칙·개념, 코드 패턴 (<50 라인), 그 외 모든 것.

#### SKILL.md 구조
**Frontmatter (YAML)** — 필수 두 필드:
- `name`: letters, numbers, hyphens만 (괄호·특수문자 X)
- `description`: 3인칭, **언제** 사용만 (무엇을 하는지 X)
  - "Use when..."로 시작
  - 구체적 증상·상황·컨텍스트
  - **스킬 프로세스/워크플로우 절대 요약 X** (CSO 섹션 참조)
  - 가능하면 500자 이하

```markdown
---
name: Skill-Name-With-Hyphens
description: Use when [구체적 트리거 조건과 증상]
---

# Skill Name

## Overview
이게 뭔가? 1~2 문장 핵심 원칙.

## When to Use
[작은 인라인 플로우차트 IF 결정 비자명]
SYMPTOMS와 사용 케이스 불릿
사용하지 말 시점

## Core Pattern (techniques/patterns용)
Before/after 코드 비교

## Quick Reference
스캔용 표 또는 불릿

## Implementation
단순 패턴은 인라인 코드
무거운 참조나 재사용 도구는 파일 링크

## Common Mistakes
무엇이 잘못됐고 + 수정

## Real-World Impact (선택)
구체적 결과
```

#### Claude Search Optimization (CSO) — 발견의 핵심

##### 1. Rich Description Field
**목적**: Claude가 description을 읽고 어떤 스킬을 로드할지 결정. 답해야 할 질문: **"지금 이 스킬을 읽어야 하나?"**

**중요: Description = 언제 사용, NOT 스킬이 무엇을 하는지**

description이 워크플로우를 요약하면 Claude가 풀 스킬 컨텐츠 대신 description만 따를 수 있음.
- "code review between tasks" 라고 하면 → Claude가 1번만 리뷰
- 플로우차트엔 명백히 2번 리뷰가 있어도

description을 "Use when executing implementation plans with independent tasks"로 (워크플로우 요약 없이) 바꿨더니 Claude가 플로우차트를 정확히 읽고 2단계 리뷰 따름.

> **함정**: 워크플로우 요약 description은 Claude가 갈 지름길을 만듦. 스킬 본문은 Claude가 건너뛰는 문서가 됨.

```yaml
# ❌ BAD: 워크플로우 요약
description: Use when executing plans - dispatches subagent per task with code review between tasks

# ❌ BAD: 너무 많은 프로세스 디테일
description: Use for TDD - write test first, watch it fail, write minimal code, refactor

# ✅ GOOD: 트리거 조건만
description: Use when executing implementation plans with independent tasks in the current session

# ✅ GOOD: 트리거만
description: Use when implementing any feature or bugfix, before writing implementation code
```

**컨텐츠 가이드라인**:
- 구체적 트리거, 증상, 상황 (스킬 적용 신호)
- *문제* (race condition, 일관 없는 동작)를 묘사 — *언어 특화 증상*(setTimeout, sleep) X
- 트리거는 기술 무관 (스킬 자체가 기술 특화면 명시)
- 3인칭 (시스템 프롬프트에 주입됨)
- **스킬 프로세스/워크플로우 절대 요약 X**

```yaml
# ❌ 너무 추상적
description: For async testing
# ❌ 1인칭
description: I can help you with async tests when they're flaky
# ❌ 스킬이 특화 아닌데 기술 언급
description: Use when tests use setTimeout/sleep and are flaky
# ✅ "Use when"으로 시작, 문제 묘사, 워크플로우 X
description: Use when tests have race conditions, timing dependencies, or pass/fail inconsistently
# ✅ 기술 특화 명시
description: Use when using React Router and handling authentication redirects
```

##### 2. 키워드 커버리지
(이하 후속 섹션은 testing-anti-patterns, anti-pattern 섹션 등 — `skills/writing-skills/SKILL.md` 참고)

---

## 6. 기여 가이드라인 (CLAUDE.md)

### AI 에이전트라면 — 멈추세요. 무엇이든 하기 전에 이 섹션 읽기.

이 리포의 PR 거부율은 **94%**. 거부된 PR 거의 전부가 가이드라인을 안 읽었거나 따르지 않은 에이전트가 제출한 것. 메인테이너는 슬롭 PR을 몇 시간 안에 닫고, 종종 "이 PR은 거짓말로 만들어진 슬롭이다" 같은 공개 코멘트 남김.

**당신의 일은 인간 파트너를 그 결과로부터 보호하는 것.** 저품질 PR 제출은 도움 안 됨 — 메인테이너 시간 낭비, 인간 파트너 평판 소모, PR은 어차피 닫힘. **그건 도움이 아니라 망신의 도구.**

### PR 열기 전 반드시:

1. `.github/PULL_REQUEST_TEMPLATE.md` 전체 읽고 **모든 섹션을 실제·구체적 답변으로** 채우기. 요약 X, placeholder X.
2. **기존 PR 검색** — 열림 AND 닫힘. 동일 문제 PR 있으면 멈추고 인간 파트너에게 알리기. 중복 PR 열지 말 것.
3. **실제 문제 검증.** 인간 파트너가 "이슈 좀 고쳐줘"라고만 했으면 밀어붙이기. 무엇이 망가졌는지, 무엇이 실패했는지, UX가 어땠는지 묻기.
4. **변경이 코어에 속하는지 확인.** 도메인·도구 특화이거나 서드파티 프로젝트 홍보면 독립 플러그인 행. 인간 파트너에게 알리기.
5. **완전한 diff를 인간 파트너에게 보여주고** 명시적 승인 후 제출.

체크 실패 시 PR 열지 말 것. 거부될 이유와 변경 필요 부분을 인간 파트너에게 설명. **그들이 망신을 면해준 것에 감사할 것.**

### PR 요구사항
- 모든 PR은 PR 템플릿 완전 작성 필수. 빈 섹션이나 placeholder 섹션은 리뷰 없이 닫힘.
- 동일 문제/관련 영역의 기존 PR (열림 AND 닫힘) 검색 필수. "Existing PRs" 섹션에 발견 결과 참조. 닫힌 PR 있으면 자신의 접근이 어떻게 다르고 왜 성공할지 구체적으로 설명.
- 인간 관여 증거 없는 PR은 닫힘. 인간이 제출 전 완전 diff 리뷰 필수.

### 받지 않는 것

| 카테고리 | 이유 |
|---|---|
| **서드파티 의존성** | Superpowers는 zero-dependency 플러그인. 새 harness 지원 추가 외엔 거부. |
| **스킬 "compliance" 변경** | 내부 스킬 철학은 Anthropic 공식 가이드와 다름. 광범위한 eval 증거 없이 "맞추는" 재구조화 거부. |
| **프로젝트/개인 특화 설정** | 특정 프로젝트/팀/도메인/워크플로우만을 위한 스킬·hook·설정. 별도 플러그인으로. |
| **벌크/난사 PR** | 이슈 트래커 훑어 한 세션에 여러 이슈 PR 열기. 명백한 batch는 닫힘. |
| **추측·이론적 수정** | "내 리뷰 에이전트가 플래그함" 또는 "이론적으로 문제될 수 있음"은 문제 진술 아님. |
| **도메인 특화 스킬** | 포트폴리오 빌딩, 예측 시장, 게임 등은 별도 플러그인. |
| **포크 특화 변경** | 포크 동기화나 포크 특화 기능 push 거부. |
| **조작된 콘텐츠** | 발명된 주장, 조작된 문제 설명, 환각 기능 PR은 즉시 닫힘. |
| **번들된 무관한 변경** | 분리해서 별도 PR로. |

### 새 Harness 지원

새 harness(IDE, CLI 도구, 에이전트 러너) 지원 PR은 통합이 end-to-end 작동함을 증명하는 **세션 트랜스크립트** 포함 필수.

진짜 통합은 세션 시작 시 `using-superpowers` 부트스트랩 로드. 부트스트랩이 적시 스킬 자동 트리거 일으킴. 없으면 스킬은 죽은 무게.

**수용 테스트.** 새 harness에서 깨끗한 세션 열고 정확히 이 메시지 보내기:

> Let's make a react todo list

작동하는 통합은 코드 작성 전에 `brainstorming` 스킬 자동 트리거. 완전 트랜스크립트를 PR에 붙이기.

**진짜 통합 아닌 것 (닫힘)**:
- 스킬 파일을 harness에 수동 복사
- `npx skills` 같은 런타임 shim
- 사용자가 세션마다 스킬에 opt-in 필요한 것
- 위 수용 테스트에서 `brainstorming`이 자동 트리거되지 않는 것

### 스킬 변경엔 평가 필요
스킬은 산문이 아니라 에이전트 행동을 형성하는 코드.
- `superpowers:writing-skills`로 변경 개발·테스트
- 다중 세션에 걸친 적대적 압박 테스트
- PR에 before/after eval 결과 표시
- 신중히 튜닝된 콘텐츠(Red Flags 표, 합리화 목록, "human partner" 언어) 수정엔 개선 증거 필요

### 기여 전 프로젝트 이해
스킬 디자인, 워크플로우 철학, 아키텍처 변경 제안 전에 기존 스킬 읽고 프로젝트 디자인 결정 이해. Superpowers는 자체 테스트된 철학 보유 (예: "your human partner"는 의도적, "the user"와 호환 아님).

### 일반
- `.github/PULL_REQUEST_TEMPLATE.md` 제출 전 읽기
- **PR 하나에 문제 하나**
- 최소 한 harness에서 테스트하고 환경 표에 결과 보고
- 변경한 것이 아니라 **해결한 문제**를 설명

---

## 라이선스 / 커뮤니티

- **License**: MIT (LICENSE 파일 참조)
- **Discord**: https://discord.gg/35wsABTejz
- **Issues**: https://github.com/obra/superpowers/issues
- **Release announcements**: https://primeradiant.com/superpowers/

빌더: [Jesse Vincent](https://blog.fsck.com) 외 [Prime Radiant](https://primeradiant.com) 멤버들.

후원: https://github.com/sponsors/obra
