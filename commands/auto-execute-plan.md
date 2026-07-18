---
description: 자동 흐름의 4단계 진입 (마지막) — implementation-plan.md 가 있는 상태에서 보조 에이전트 강제로 여러 작업 동시 진행 (승인 게이트 자동 통과) + 실패 격리 + 마무리 자동. /auto-execute-plan 명시 호출 전용.
disable-model-invocation: true
---

# /auto-execute-plan

`<slug>` 인자는 선택입니다. 누락 시 가장 최근 implementation-plan.md 를 자동으로 선택합니다. 이 슬래시는 `auto-executing-plans` skill 을 호출합니다.

동작은 보조 에이전트 강제로 `js-super-sub-driven` 호출 (승인 게이트 자동 통과 명시 적용). 실패한 task 가 있어도 격리해서 나머지 task 는 계속 진행하고, 마지막에 결과를 모아서 마무리합니다.

종료 시점 메시지에 commit 개수 / RISK 카운트 / 멈춘 task 목록이 노출됩니다.

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/auto-execute-plan <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
