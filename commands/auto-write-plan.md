---
description: 자동 흐름의 3단계 진입 — tech-design.md 가 있는 상태에서 write-plan + execute-plan 까지 자동으로 이어갑니다. /auto-write-plan 명시 호출 전용.
disable-model-invocation: true
---

# /auto-write-plan

`<slug>` 인자는 선택입니다. 누락 시 가장 최근 <slug> 자동 선택. 이 슬래시는 `auto-writing-plans` skill 을 호출합니다.

산출물은 `<slug>-implementation-plan.md` 입니다 (RAW 본문, frontmatter 의 `commit_policy: per-task`).

다음 단계는 자동으로 이어집니다 — `/auto-execute-plan`. 2개 확정 피처 (tech-design frontmatter `depth: 2`) 에서 실행하면 3개 트랙으로 승격됩니다 (frontmatter 갱신 + 변경이력 기록).

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/auto-write-plan <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).

## `--no-clean-verify` 플래그

검증 단계에서 맥락 없는 보조 에이전트 2개를 병렬로 띄우는 것을 끕니다:

`/auto-write-plan <slug> --no-clean-verify`

기본은 켜져 있습니다. 무맥락 검증자는 대화 이력과 작성 의도를 모른 채 산출물만 보기 때문에, 메인이 자기 문서를 볼 때 놓치는 것을 잡습니다. 끄면 메인 자체 검증만 돌고 보고서도 기존 4축만 나옵니다.

자동 흐름에서도 동작은 같습니다 — 사용자에게 묻지 않고 메인이 중재해 보고서에 반영합니다.
