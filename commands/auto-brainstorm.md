---
description: 자동 흐름 진입 — Socratic 질문 (1~5개 적응) + AI 자동 진행 + 4 단계 자동 체인 (brainstorm → tech-design → write-plan → execute-plan). 사용자 입력은 첫 질문 답변에만 받습니다. /auto-brainstorm 명시 호출 전용.
disable-model-invocation: true
---

# /auto-brainstorm

피처명을 인수로 주거나 (`/auto-brainstorm 사용자 잔액 출금`) 인수 없이 호출하면 한 줄 안내 후 진행합니다. 이 슬래시는 `auto-brainstorming` skill 을 호출합니다.

산출물은 `docs/features/<오늘날짜>-<slug>/<slug>-requirements.md` 입니다 (Socratic 자유 형식, RAW).

다음 단계는 자동으로 이어집니다 — `/auto-tech-design` → `/auto-write-plan` → `/auto-execute-plan`.

흐름 중간에 멈추고 싶으면 각 skill 전환 시 한 줄 안내가 노출되니, 그때 `stop` / `멈춰` / `잠깐` 같은 단어를 입력하면 깨끗하게 종료합니다.

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/auto-brainstorm <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
