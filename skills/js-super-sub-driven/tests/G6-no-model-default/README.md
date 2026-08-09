# G6: No Model Field — Sonnet Default

**Scenario:** plan task block 에 `**Model**:` 줄 없음 (v1.1.13 이전 plan 시뮬레이션). G2 plan 재사용.

**Expected:** DAG 표시 default 는 sonnet 유지. dispatch 는 v2.9+ 조건부 룰 — 신규 테스트 작성 포함 task 면 sonnet (floor), 아니면 haiku. 한 줄 dispatch log 로 판정 근거 표기 (예: "Task 1 model: haiku (순수 byte-copy)").
