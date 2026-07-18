---
description: <slug>-implementation-plan.md를 task-by-task로 실행합니다. 매 코드 변경마다 위험 주석 자동 부착 + 변경 전·후 코드를 변경이력에 보존합니다.
---

# /execute-plan

이 슬래시는 plan 의 task 수를 세서 실행 모드 양자택일을 묻고 해당 skill 을 호출합니다.

전제:
- 동일 피처 폴더에 `<slug>-implementation-plan.md` 가 있어야 합니다.
- plan 의 frontmatter 에 `commit_policy` 필드가 있어야 합니다 (없으면 `per-task` 로 간주).

## 실행 모드 양자택일

| 옵션 | skill | 권장 |
|---|---|---|
| **1) 인라인** | `executing-plans` | 중간 크기 plan (task 12개 이하) |
| **2) 보조 에이전트** | `js-super-sub-driven` | 큰 plan (task 13개 이상) |

다음 메시지로 사용자에게 묻습니다:

> "Plan 에 task 가 <N> 개 있습니다. 두 가지 실행 방식이 있어요:
>
> 1. **인라인** (중간 크기 plan, 12개 이하 권장) — 메인 에이전트가 `executing-plans` 로 직접 편집합니다. 빠르고 전체 토큰이 적게 들지만, task 수에 따라 메인 컨텍스트가 누적됩니다.
> 2. **보조 에이전트** (큰 plan, 13개 이상 권장) — `js-super-sub-driven` 으로 implementer + spec reviewer 보조 에이전트가 처리합니다. 메인 컨텍스트는 보존되지만, 호출 비용이 추가됩니다.
>
> 어느 쪽으로 진행할까요?"

upstream 원본 `subagent-driven-development` 는 이 양자택일에서 제시하지 않습니다. 사용자가 명시적으로 "upstream 원본으로" 요청한 경우에만 호출합니다.

## 자동 동작 (인라인 / 보조 에이전트 공통)

- `risk-annotation` 의 3-체크리스트가 동작하며, 필요 시 `# ⚠️ RISK(...)` 주석을 자동으로 붙입니다.
- 매 task 가 끝날 때마다 `<slug>-implementation-plan.md` 의 변경이력에 `[코드-수정]` entry 를 추가합니다.
- `commit_policy: per-task` 인 경우 task 단위로 atomic commit 합니다.

차이점은:
- **인라인** — 메인이 직접 편집합니다. git-fast / memory-fallback 모드가 자동 선택됩니다.
- **보조 에이전트 (js-super)** — implementer + spec reviewer 보조 에이전트가 작업하고, 메인이 RISK / 변경이력 / atomic commit 후처리를 합니다. 호출하는 skill 은 `js-super-sub-driven` 입니다.

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/execute-plan <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
