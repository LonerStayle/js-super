# G6: No Model Field — Sonnet Default

**Scenario:** plan task block 에 `**Model**:` 줄 없음 (v1.1.13 이전 plan 시뮬레이션). G2 plan 재사용.

**Expected:** DAG 표시 default 는 sonnet 유지. dispatch 는 단일 룰 — plan `**Model**:` 값, 생략 시 sonnet 기본 (haiku 사용 금지, 하한 sonnet). 한 줄 dispatch log 로 판정 근거 표기 (예: "Task 1 model: sonnet (기본값)").
