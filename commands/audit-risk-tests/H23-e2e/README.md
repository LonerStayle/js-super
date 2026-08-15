# H23 — `/audit-risk` E2E Fixture

End-to-end fixture for `/audit-risk`. 6 시나리오로 골든 패스 + 경계 케이스 + 안전성 제약을 다룬다.

## Purpose

`/audit-risk` 의 규모별 모드 동작을 검증한다.

- 소스 파일 40개 미만이고 총 8,000줄 미만이면 축소 모드. 보조 에이전트 1개가 다섯 영역을 순서대로 순회한다.
- 둘 중 하나라도 넘으면 전체 모드. 보조 에이전트 5개를 한 메시지에 병렬로 호출한다.
- 두 모드 모두 결과를 취합한 뒤 메인이 마크다운 보고서 1개를 직접 작성한다 (`docs/audit/<timestamp>-audit-risk.md`). 보고서 전용 에이전트는 따로 없다.

이 fixture 는 **runtime 에서 자동 실행되지 않는다**. 사람이 dogfood 할 때 시나리오를 직접 세팅하고 결과를 ground truth 와 비교한다.

## Scenarios

### G1 — 작은 프로젝트 (축소 모드)

**Setup**: 소스 파일 40개 미만, 총 8,000줄 미만인 프로젝트에서 `/audit-risk` 를 호출한다.

**Expected**:
- Step 1 규모 측정에서 두 조건(파일 수·줄 수)을 모두 충족해 축소 모드로 안내됨
- `Task` 호출 1회로 다섯 영역(A~E)을 순서대로 모두 점검함
- 코드베이스가 작다는 이유로 영역을 건너뛰지 않음
- `docs/audit/<timestamp>-audit-risk.md` 가 1개 생성됨

**Verification**:
```bash
# 보고서 존재
ls docs/audit/*-audit-risk.md
# expected: 파일 1개 이상

# 모드 표기 확인
grep -c "모드: 간단(1)" docs/audit/*-audit-risk.md
# expected: ≥ 1

# 다섯 영역 이름이 보고서에 모두 등장
grep -c "외부 API 비용\|개인정보\|사용량·결제 로직\|LLM 에이전트\|거버넌스" docs/audit/*-audit-risk.md
# expected: ≥ 5
```

### G2 — 큰 프로젝트 (전체 모드)

**Setup**: 소스 파일 40개 이상이거나 총 8,000줄 이상인 프로젝트에서 `/audit-risk` 를 호출한다.

**Expected**:
- Step 1 규모 측정에서 두 조건 중 하나라도 넘어 전체 모드로 안내됨
- 메인이 한 메시지에 `Task` 호출 5개(영역 A~E 각 1개)를 병렬로 실행함
- 다섯 결과를 모두 기다린 뒤 취합함
- `docs/audit/<timestamp>-audit-risk.md` 가 1개 생성됨

**Verification**:
```bash
# 모드 표기 확인
grep -c "모드: 전체(5)" docs/audit/*-audit-risk.md
# expected: ≥ 1
```

### G3 — 문제 없는 프로젝트 (clean)

**Setup**: 위험 패턴이 없는 프로젝트(외부 SDK 미사용, PII 필드 없음, 결제 로직 없음, 인증 우회 없음)에서 `/audit-risk` 를 호출한다.

**Expected**:
- 각 영역이 `status: "clean"` 을 반환하고 `checked` 배열(무엇을 어떤 기준으로 봤는지)을 채움
- 보고서에 영역별로 "점검함, 해당 항목 없음" 이 명시적으로 나옴
- 없는 위험을 만들어내지 않음 — 억지 findings 0건

**Verification**:
```bash
# "점검함, 해당 항목 없음" 표기 존재
grep -c "점검함, 해당 항목 없음" docs/audit/*-audit-risk.md
# expected: ≥ 1

# 요약 표의 건수가 모두 0 인지 육안 확인
grep -A5 "^## 요약" docs/audit/*-audit-risk.md
```

### G4 — 비밀값 하드코딩 (마스킹)

**Setup**: 의도된 hardcoded API key 를 포함한 프로젝트(예: `const API_KEY = "sk-test_abc123xyz"`)에서 `/audit-risk` 를 호출한다.

**Expected**:
- 영역 E 가 secrets-hardcoded category 로 finding 을 반환하고 `redact_secret: true` 로 마킹함
- finding 의 어떤 필드에도 값 자체가 남지 않음 — 파일 경로와 줄 번호만 남음
- 보고서에도 값이 나오지 않고 파일:줄만 표시됨

**Verification**:
```bash
# 값 자체가 노출되었는지 확인 (의도된 값으로 검색)
grep -c "sk-test_abc123xyz" docs/audit/*-audit-risk.md
# expected: 0

# 파일:줄 표시는 남아있음
grep -c "secrets\.py" docs/audit/*-audit-risk.md
# expected: ≥ 1
```

### G5 — 영역 1개 실패 (부분 보고서)

**Setup**: 영역 하나(예: 영역 A, context7/WebSearch 호출이 막힌 환경)가 실패하도록 만든 뒤 `/audit-risk` 를 호출한다.

**Expected**:
- 실패한 영역만 `status: "failed"` 로 표시되고 나머지 4개 영역은 정상 진행됨
- 메인이 전체를 중단하지 않고 부분 보고서를 작성함
- 보고서에서 실패한 영역이 "점검 실패" 로 표기됨

**Verification**:
```bash
# "점검 실패" 표기 존재
grep -c "점검 실패" docs/audit/*-audit-risk.md
# expected: ≥ 1

# 나머지 4개 영역은 findings 또는 "점검함, 해당 항목 없음" 으로 정상 표기됨을 육안 확인
```

### G6 — LLM 에이전트 코드 없음 (해당 없음)

**Setup**: LLM 에이전트 코드가 없는 프로젝트(openai / anthropic / langchain 등 import 0)에서 `/audit-risk` 를 호출한다.

**Expected**:
- 영역 D 의 사전 확인이 LLM 에이전트 코드 부재를 감지하고 즉시 종료함
- 영역 D 가 `status: "skipped"` 를 반환하고 "LLM 에이전트 관련 코드가 없어 이 영역은 해당되지 않음" 을 요약으로 남김
- 다른 4개 영역은 정상 진행됨
- 보고서에서 영역 D 가 "해당 없음 (관련 코드 없음)" 으로 표기됨

**Verification**:
```bash
# "해당 없음" 표기 존재
grep -c "해당 없음 (관련 코드 없음)" docs/audit/*-audit-risk.md
# expected: ≥ 1
```

## 검증 흐름 요약

| 시나리오 | 핵심 검증 | grep expected |
|---|---|---|
| G1 | 작은 프로젝트 — 축소 모드 진입 | "모드: 간단(1)" ≥ 1 |
| G2 | 큰 프로젝트 — 전체 모드 진입 | "모드: 전체(5)" ≥ 1 |
| G3 | 문제 없음 — 억지 항목 없음 | "점검함, 해당 항목 없음" ≥ 1 |
| G4 | 비밀값 마스킹 | 값 자체 0, 파일:줄 ≥ 1 |
| G5 | 영역 1개 실패 — 부분 보고서 | "점검 실패" ≥ 1 |
| G6 | 에이전트 영역 미해당 | "해당 없음 (관련 코드 없음)" ≥ 1 |

## 사용 방법

1. dogfood 환경에서 위 시나리오 중 하나를 세팅한다.
2. `/audit-risk` 를 호출한다.
3. 산출된 `docs/audit/<timestamp>-audit-risk.md` 에 대해 해당 시나리오의 verification grep 을 실행한다.
4. 모든 grep 이 통과하면 시나리오 통과다.
5. 1건이라도 FAIL 이면 `commands/audit-risk.md` 를 디버그한다.

## 관련 파일

- `commands/audit-risk.md` — 메인 실행 본문 (규모 판정 + 모드별 보조 에이전트 호출 + 보고서 작성)
- `expected-mock-findings.md` — G1 / G4 의 ground truth 모의 finding list
