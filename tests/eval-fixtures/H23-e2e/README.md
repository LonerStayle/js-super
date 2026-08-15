# H23 — `/audit-risk` E2E Fixture

End-to-end fixture for the v2.3.0 `/audit-risk` command. 6 scenarios cover the golden path + edge cases + safety constraints.

## Purpose

Validate `/audit-risk` 의 5+1 subagent 패턴 동작:

- 5 read-only subagent (A/B/C/D/E) 병렬 dispatch + 결과 종합
- 1 sequential Subagent F (HTML 보고서 생성) 의 self-contained / secret redaction / v2.2.4 mirror 톤 자유

이 fixture 는 **runtime 발동 안 함**. 사람이 dogfood 시 시나리오 실행 + ground truth 비교.

## Scenarios

### G1 — 정상 1회 호출 (golden path)

**Setup**: 실제 프로젝트 (모든 5 영역 active) 에서 `/audit-risk` 호출.

**Expected**:
- 5 subagent 모두 결과 반환 (1건 fail 시 partial OK)
- Subagent F 가 `docs/audit/<YYYY-MM-DD-HHMMSS>-audit-risk.html` write
- HTML offline 렌더 OK (file:// double-click)
- 모든 finding 의 file:line 이 HTML 에 표시
- 위험도 카운트 (Critical/High/Medium/Low) 정확
- 영역별 score 5개 모두 표시

**Verification**:
```bash
# 외부 URL 참조 0
grep -cE "https?://.+\.(css|js|woff|ttf|otf)" docs/audit/*.html
# expected: 0

# 영역별 카드 모두 존재
grep -c "api[_-]cost\|api-cost\|API Cost" docs/audit/*.html  # ≥ 1
grep -c "pii\|PII" docs/audit/*.html                           # ≥ 1
grep -c "sensitive\|Sensitive" docs/audit/*.html               # ≥ 1
grep -c "agent\|Agent" docs/audit/*.html                       # ≥ 1
grep -c "governance\|Governance" docs/audit/*.html             # ≥ 1
```

### G2 — Subagent D PASS 시나리오 (LLM 에이전트 코드 0)

**Setup**: LLM 에이전트 없는 프로젝트 (openai / anthropic / langchain 등 import 0) 에서 `/audit-risk` 호출.

**Expected**:
- Subagent D pre-check 가 LLM 에이전트 코드 부재 감지
- D 반환: `{"status": "PASS", "score": 100, "findings": [], "summary": "에이전트 위험 없음, 본 영역 점검 불필요"}`
- 다른 4 영역 (A/B/C/E) 정상 진행
- Subagent F 가 HTML 에서 Agent 영역을 **단일 PASS 카드 + 비활성 안내**로 렌더링 (findings cards X)
- 전체 위험도 카운트에서 Agent 0건 분리 명시

**Verification**:
```bash
# HTML 안에 PASS 안내 명시
grep -c "에이전트 위험 없음\|에이전트 코드 부재\|본 영역 점검 불필요" docs/audit/*.html
# expected: ≥ 1
```

### G3 — Secret Redaction

**Setup**: 의도된 hardcoded API key 포함 프로젝트 (예: `const API_KEY = "sk-test_abc123xyz"`).

**Expected**:
- Subagent E 가 secrets-hardcoded category 로 Critical finding 반환
- finding 의 `redact_secret: true` 마킹
- raw secret value 는 finding 의 어떤 필드에도 노출 X
- Subagent F 가 HTML 에서 해당 항목을 `****` 마스킹 + file:line 만 표시
- HTML 본문 어디에도 raw value (`sk-test_abc123xyz`) 가 출현하지 않음

**Verification**:
```bash
# raw secret 값이 HTML 에 노출되었는지 (의도된 값으로 검색)
grep -c "sk-test_abc123xyz\|sk-test_[a-zA-Z0-9]*" docs/audit/*.html
# expected: 0 — 마스킹 적용

# 마스킹 표시 존재
grep -c "\*\*\*\*" docs/audit/*.html
# expected: ≥ 1
```

### G4 — Self-contained (외부 URL 0)

**Setup**: G1 의 HTML 산출물에 대해 검증.

**Expected**:
- `<link href="https://...">` — 0
- `<script src="https://...">` — 0
- `@import url(...)` — 0
- 시스템 폰트 stack 또는 inline data URI 만 사용

**Verification**:
```bash
# 모든 외부 URL 검증
grep -cE "(<link[^>]+href=[\"']https?://|<script[^>]+src=[\"']https?://|@import\s+url\([\"']?https?://)" docs/audit/*.html
# expected: 0

# 정적 폰트 stack 확인 (system-ui / -apple-system 등 OK)
grep -c "system-ui\|-apple-system\|BlinkMacSystemFont\|sans-serif\|monospace" docs/audit/*.html
# expected: ≥ 1
```

### G5 — 부분 실패 fail-safe

**Setup**: Subagent A 의 context7 / WebSearch 호출이 실패하는 환경 (네트워크 차단 등) 에서 `/audit-risk` 호출.

**Expected**:
- Subagent A 가 findings 일부 반환 + `pricing_lookup_status: "failed"` 마킹
- 또는 A 전체가 fail → `area.status: "failed"`
- 메인이 종료 X — 다른 4 영역 (B/C/D/E) 정상 진행
- Subagent F 가 HTML 에서 API Cost 영역에 "추정 불가" 라벨 또는 "Subagent A 실패 — 본 영역 검사 부분 누락" 카드 명시

**Verification**:
```bash
# 부분 실패 명시 카드
grep -c "추정 불가\|Subagent.*실패\|partial\|failed" docs/audit/*.html
# expected: ≥ 1 (실패 시나리오에서)
```

### G6 — 빈 프로젝트 (graceful empty state)

**Setup**: 신규 프로젝트 (소스 파일 < 5개, 외부 SDK 0, PII 필드 0, 에이전트 0) 에서 `/audit-risk` 호출.

**Expected**:
- 5 영역 모두 findings: [] + score 100 + summary "위험 없음"
- Subagent F 가 HTML 생성 — 빈 상태도 우아하게 표현 (empty state UI)
- "이 프로젝트는 5 영역 모두 무결" 큰 hero 카드 또는 metaphor (트로피 / 체크마크 / 색감 강한 축하 톤)

**Verification**:
```bash
# 위험 없음 표시
grep -c "위험 없음\|0건\|empty\|safe\|무결" docs/audit/*.html
# expected: ≥ 1
```

## 검증 흐름 요약

| 시나리오 | 핵심 검증 | grep expected |
|---|---|---|
| G1 | golden path — 5 영역 모두 active | 외부 URL 0, 5 영역 모두 표시 |
| G2 | Agent PASS 분기 | "에이전트 위험 없음" ≥ 1 |
| G3 | Secret redaction | raw value 0, `****` ≥ 1 |
| G4 | Self-contained | 외부 URL 0, 시스템 폰트 OK |
| G5 | 부분 실패 fail-safe | "추정 불가 / 실패" ≥ 1 |
| G6 | 빈 프로젝트 | "위험 없음 / 무결" ≥ 1 |

## 사용 방법

1. dogfood 환경에서 위 시나리오 중 하나 setup
2. `/audit-risk` 호출
3. 산출된 `docs/audit/<timestamp>-audit-risk.html` 에 대해 expected verification grep 실행
4. 모든 grep PASS 확인 → 시나리오 통과
5. 1건 FAIL → `commands/audit-risk.md` 또는 `commands/audit-report-prompt.md` 결함 디버그

## 관련 파일

- `commands/audit-risk.md` — 메인 dispatch 본문 (5+1 subagent)
- `commands/audit-report-prompt.md` — Subagent F prompt
- `expected-mock-findings.md` — G1/G3 의 ground truth 모의 finding list
