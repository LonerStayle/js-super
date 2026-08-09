---
description: 직전에 만든 <slug>-requirements.md를 받아 기술 설계 대화를 진행하고 <slug>-tech-design.md를 작성합니다.
---

# /tech-design

이 슬래시는 `tech-design` skill 을 호출합니다.

전제: 동일한 피처 폴더에 `<slug>-requirements.md` 가 이미 존재해야 합니다. 없으면 `/brainstorm` 부터 먼저 실행해주세요.

산출물은 `docs/features/<날짜>-<slug>/<slug>-tech-design.md` 와 메인 에이전트 검증 보고서 (대화로 출력) 입니다.

다음 단계는 tech-design 승인 직후 게이트에서 선택합니다 — 구현계획서까지 진행 (3개) / 여기서 종료 (2개 확정) / 나중에 결정. 3개 선택 시 `/write-plan` 으로 이어집니다.

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/tech-design <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
