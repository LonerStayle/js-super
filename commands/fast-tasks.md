---
description: 가벼운 task 여러 개를 한 batch 로 처리합니다 (각 task 마다 Socratic 질문 2~3개 + 단일 .md 파일 + 보조 에이전트 병렬 호출). 명시 슬래시 호출만 — 자동 발동 X.
---

# /fast-tasks

task 5~15개가 한꺼번에 할당된 경우 쓰는 **가벼운 batch 경로** 입니다. 명시 `/fast-tasks` 호출 시에만 발동합니다.

## Other / 모호 응답 처리 (v2.1.1+)

Step 1 Socratic Q × N 흐름의 AskUserQuestion 게이트에서 사용자가 "Other" 자유 응답 또는 "모르겠음 / 이해 안 됨" 류 답변 catch 시 → **그 질문만 단독 재호출 + prose 설명 추가**. 다음 task 자동 진행 X (해당 task 명세 미확정 상태로 넘어가지 않음).

## 영구 생략 (가벼움이 의도)

본 흐름은 다음 항목을 **절대 자동으로 추가하지 말 것**:

- `<slug>-tech-design.md`
- `<slug>-implementation-plan.md`
- `verifying-spec` 4축 보고서
- 변경이력 footer / `change-history` skill 호출
- `risk-annotation` (RISK 주석)
- `code-pretty` 호출
- AskUserQuestion 게이트 (Socratic Q 외)

→ 최종 산출물은 단일 `<batch-slug>-tasks.md` **1 파일** + 실제 코드 변경만.

## Process

### Step 1 — Per-task Mini Socratic

사용자 첫 입력에서 task 목록 파싱. 각 task **마다** Socratic 질문 **2~3개** 던짐 (3개 초과 금지).

- 라운드 N회: task 1 질문 → 답 → task 2 질문 → 답 → ...
- 목표: 각 task 의 **입력/출력/제약** 최소 명확화
- 답이 명확하면 2개로 끝, 모호하면 3개까지

### Step 2 — 단일 `<batch-slug>-tasks.md` 작성

```
docs/features/YYYY-MM-DD-fast-tasks-<batch-slug>/<batch-slug>-tasks.md
```

본문:

```markdown
# <Batch slug> — Fast tasks (N개)

## Task 1: <title>
- 명세: <Socratic 합의>
- 영향 파일: <메인 추정>

## Task 2: <title>
...

---

## 병렬화 계획 (DAG)

- Chain A: 1 → 4 → 5   (이유: 4 가 1 산출물 의존, 5 가 4 산출물 의존)
- Chain B: 2 → 7       (이유: 7 이 2 export 사용)
- Independent: 3, 6, 8, 9, 10
```

### Step 3 — 보조 에이전트 병렬 호출

메인이 §병렬화 계획 을 읽고 다음과 같이 호출합니다:

- **Chain (연결된 task)** — 하나의 보조 에이전트가 순서대로 처리합니다 (1 → 4 → 5).
- **Independent (독립 task)** — 각각 별도 보조 에이전트로 동시 호출합니다 (Agent tool 한 메시지 안에 여러 호출).
- **종속 판단** — LLM 휴리스틱 (명세 + 영향 파일 기반) 으로 결정합니다. 사용자가 명시할 필요 X.

각 보조 에이전트가 자체적으로 commit 까지 수행합니다 (task 단위 commit). 메인은 호출과 결과 종합만 합니다.

### Step 4 — 한 줄 요약

```
✅ fast-tasks <batch-slug> 완료: N 개 task / M 개 commit / 멈춘 task 0 개.
   다음 단계는 PR 또는 git merge 를 직접 진행해주세요.
```

AskUserQuestion 게이트는 없습니다. 사용자가 직접 후속 처리합니다.

## Non-goals

- 사용자가 명시 종속 그래프 그려주는 모드 (LLM 휴리스틱만)
- chain 내부 task 실패 시 자동 재시도 (사용자 수동 재실행)
- 풀 brainstorming 흐름으로 fallback (원하면 별도 `/brainstorm`)

## 입력 예시

```
/fast-tasks

이번 스프린트 할당 10개:
1) 로그인 페이지 다크모드 토글 추가
2) /api/users GET endpoint 추가 (페이지네이션)
3) Button 컴포넌트 size variant (sm/md/lg)
...
```
