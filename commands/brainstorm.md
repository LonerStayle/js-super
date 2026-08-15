---
description: 새 피처의 <slug>-requirements.md 를 소크라테스 대화로 작성합니다. 기획 레벨 합의 후 /design-tech으로 넘어갑니다.
---

# /brainstorm

피처명을 인수로 주거나 (`/brainstorm 사용자 잔액 출금`) 인수 없이 호출하면 피처명을 묻습니다. 이 슬래시는 `brainstorming` skill 을 호출합니다.

산출물은 `docs/features/<오늘날짜>-<slug>/<slug>-requirements.md` 입니다.

다음 단계는 `/design-tech` 입니다.

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/brainstorm <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
