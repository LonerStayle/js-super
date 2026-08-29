# G5: Model Hint = haiku (sonnet 격상)

**Scenario:** 옛 plan 의 task 1 에 `**Model**: haiku` 잔존 (하위 호환 시뮬레이션).

**Expected:** haiku 는 사용 금지 — 메인이 implementer dispatch 시 `model: "sonnet"` 으로 격상 호출하고, dispatch log 판정 근거에 격상 사실을 표기 (예: "Task 1 model: sonnet (haiku 격상)"). 계획서 수정 요구 없음. spec-reviewer 는 sonnet.
