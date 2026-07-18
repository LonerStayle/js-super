---
description: "프로젝트 전체의 보안 / 거버넌스 / 비용을 1회성으로 감사하고 HTML 보고서 1개를 산출. 코드는 변경하지 않음."
disable-model-invocation: true
---

# /audit-risk

이 슬래시는 프로젝트 전체의 **보안 / 거버넌스 / 비용을 1회성으로 감사**하는 명령입니다. 코드는 변경하지 않고, HTML 보고서 1개를 산출합니다 (`docs/audit/<timestamp>-audit-risk.html`, gitignored).

> **자동 발동 없음** — 사용자가 명시적으로 호출할 때만 발동합니다. 1회 호출 시 Sonnet 보조 에이전트 6개 + 약간의 context7/WebSearch 비용이 듭니다.
> **LLM 기반 best-effort 감사** — 정확한 청구서가 아닙니다. 외부 보안 도구 (Snyk / SonarQube / Semgrep) 와 보완 관계로 사용해주세요.

## 흐름 (메인 에이전트 단계별 실행)

### Step 1 — 출력 폴더 보장

```bash
mkdir -p docs/audit/
```

### Step 2 — 5 read-only subagent 병렬 dispatch

메인이 **한 메시지에 5개 `Task` 호출** (`subagent_type: "general-purpose"`, `model: "sonnet"`, `run_in_background: false`). 각 prompt 본문은 아래 영역별 inline. 5 결과 모두 wait.

#### Subagent A — API Cost

```
You are auditing this project for **외부 API 비용 위험**.

## 검출 대상
- HTTP client 사용처 (fetch / axios / got / requests / aiohttp / urllib)
- 외부 SDK 임포트 (openai / anthropic / stripe / twilio / sendgrid / aws-sdk / google-cloud / azure)
- 호출 패턴: loop 안 호출 / N+1 / retry 무한 / cache 미적용 / batch 안 묶음

## 비용 분석
- /context7 로 각 SDK pricing 페이지 조회 (예: openai → tokens 단가)
- WebSearch fallback ("<sdk-name> pricing 2026") — context7 결과 부족 시
- 호출 빈도 추정 (cron / user-action / event trigger)
- 월 best-case / worst-case 추정 + 신뢰도 라벨 (high/medium/low)

## 위험도 매트릭스
- Critical: 단가 ↑ + loop 안 호출 + cache 없음
- High: 단가 중 + retry 무한
- Medium: 단가 ↓ + 빈도 ↑
- Low: 단가 ↓ + 빈도 ↓ (또는 dead code)

## 출력 schema
{
  "findings": [
    {
      "file": "<path>",
      "line_range": "<start-end>",
      "severity": "Critical|High|Medium|Low",
      "category": "loop-call | retry-infinite | no-cache | batch-missing | n-plus-1",
      "title": "<짧은 제목>",
      "description": "<상세>",
      "estimated_cost": {"best": "$X/month", "worst": "$Y/month", "confidence": "high|medium|low", "basis": "<근거 한 줄>"},
      "recommendation": "<권장 조치>"
    }
  ],
  "score": <0-100, 100=완벽>,
  "summary": "<영역 한 줄 요약>",
  "sdks_detected": ["<list>"],
  "pricing_lookup_status": "ok|partial|failed"
}

read-only. 코드 수정 X. dead code / 잠재 위험은 Low 분류 엄격 적용.
```

#### Subagent B — PII Security

```
You are auditing this project for **사용자 개인정보 (PII) 노출 위험**.

## 검출 대상
- 필드 keyword: email / phone / mobile / ssn / 주민번호 / passport / 카드번호 / cvv / address / 주소 / 생년월일 / birthday / dob / ip_address / device_id / mac_address
- 평문 저장 패턴 (DB write / file write / localStorage / sessionStorage / cookie)
- log 출력 패턴 — console.log / logger.{info,debug} / print / slog / fmt.Println 에 PII 직접 포함
- 외부 송신 — 3rd-party API body / GA / Sentry / Mixpanel 등에 PII
- response body 에 불필요 PII 포함

## 위험도 매트릭스
- Critical: log 또는 외부 송신에 PII 평문
- High: DB 평문 저장 + 암호화 X
- Medium: response 에 불필요 PII
- Low: 마스킹 안 된 internal display only

## 출력 schema
{
  "findings": [
    {
      "file": "<path>",
      "line_range": "<start-end>",
      "severity": "Critical|High|Medium|Low",
      "category": "log-leak | db-plaintext | external-send | response-overshare | no-masking",
      "title": "<짧은 제목>",
      "description": "<상세>",
      "pii_field": "<email | phone | ssn | ...>",
      "recommendation": "<마스킹 / 암호화 / 제거 등>"
    }
  ],
  "score": <0-100>,
  "summary": "<영역 한 줄 요약>"
}

read-only.
```

#### Subagent C — Sensitive Logic

```
You are auditing this project for **사용량 / 비용 / 결제 로직 결함**.

## 검출 대상
- keyword: usage / cost / bill / payment / charge / subscription / credit / quota / limit / rate-limit / balance
- 패턴:
  - **Race condition** — counter increment without lock / transaction (`counter++` / `count = count + 1`)
  - **Off-by-one** — `< limit` vs `<= limit` 혼용
  - **검증 누락** — 입력 sanitize / 음수 / overflow 미체크
  - **트랜잭션 X** — multi-step 결제 / 잔액 차감 + 부수 작업이 트랜잭션 밖
  - **Idempotency X** — 결제 / 외부 요청 재시도 시 중복 처리 위험 (idempotency key 부재)

## 위험도 매트릭스
- Critical: race 또는 트랜잭션 X 가 비용/결제 로직
- High: idempotency X 가 결제 로직
- Medium: off-by-one 또는 검증 누락
- Low: 잠재 위험 (실제 경로 X dead code)

## 출력 schema
{
  "findings": [
    {
      "file": "<path>",
      "line_range": "<start-end>",
      "severity": "Critical|High|Medium|Low",
      "category": "race | off-by-one | validation-missing | no-transaction | no-idempotency",
      "title": "<짧은 제목>",
      "description": "<상세>",
      "recommendation": "<lock / transaction / idempotency key / 검증 추가 등>"
    }
  ],
  "score": <0-100>,
  "summary": "<영역 한 줄 요약>"
}

read-only.
```

#### Subagent D — Agent Risk

```
You are auditing this project for **LLM 에이전트 위험**.

## Pre-check (반드시 시작 직전 실행)

LLM 에이전트 코드 존재 여부 grep:
- import 패턴: openai / anthropic / langchain / langgraph / crewai / autogen / llamaindex
- system prompt 변수 / tool calling 코드
- agent loop / multi-turn / orchestrator

**없으면 즉시 종료**:
{"status": "PASS", "summary": "에이전트 위험 없음, 본 영역 점검 불필요", "score": 100, "findings": []}

**있으면 다음 검출**:

## 검출 대상
- **민감 데이터 접근**: 에이전트 context / tool 가 PII / 결제 정보 / 인증 토큰에 접근
- **Prompt injection 취약**: user input 이 system prompt 에 sanitize 없이 주입
- **System prompt 노출**: response 에 system prompt 그대로 노출 가능 패턴
- **Tool 호출 권한 과다**: destructive 도구 (DB delete / payment / email send) 호출 가능 + 검증 X
- **Output 검증 미적용**: LLM output 을 그대로 코드 실행 / DB write / 외부 호출

## 위험도 매트릭스
- Critical: tool 권한 과다 + 검증 X (destructive 직접 실행)
- High: prompt injection 취약 + 민감 데이터 접근
- Medium: system prompt 노출 / output 검증 미적용
- Low: 잠재 위험

## 출력 schema (활성 시)
{
  "status": "ACTIVE",
  "findings": [
    {
      "file": "<path>",
      "line_range": "<start-end>",
      "severity": "Critical|High|Medium|Low",
      "category": "sensitive-data-access | prompt-injection | system-prompt-leak | tool-overpermission | no-output-validation",
      "title": "<짧은 제목>",
      "description": "<상세>",
      "recommendation": "<sanitize / RBAC / validation 등>"
    }
  ],
  "score": <0-100>,
  "summary": "<영역 한 줄 요약>",
  "agent_frameworks_detected": ["<list>"]
}

read-only.
```

#### Subagent E — Governance

```
You are auditing this project for **인증 / 권한 / audit log / 거버넌스 회피** 위험.

## 검출 대상
- **인증 미들웨어 우회**: 라우트 핸들러에 auth check 없음 (특히 admin / internal API)
- **RBAC 미적용**: 권한별 분기 없는 sensitive endpoint
- **Audit log 결여**: 민감 작업 (결제 / 권한 변경 / 데이터 삭제) 후 log 없음
- **Secrets hardcoding**: API key / DB password / JWT secret 이 코드에 평문
- **환경변수 부주의**: process.env.X 를 sanitize 없이 client 노출
- **CORS 과다 허용**: `*` 또는 너무 넓은 origin
- **SQL injection**: 문자열 concat 으로 query 조립
- **XSS**: HTML escape 미적용 사용자 입력 렌더링
- **CSRF**: state-changing endpoint 가 CSRF token 미검증
- **보안 룰 wrap-around**: `if (env === "dev")` 같은 분기로 prod 에서 검증 우회

## 위험도 매트릭스
- Critical: secrets hardcoded / SQL injection / 인증 우회 (admin)
- High: RBAC 누락 / XSS / CSRF
- Medium: audit log 결여 / CORS 과다
- Low: 잠재 위험 / dev-only 검증 우회

## 출력 schema
{
  "findings": [
    {
      "file": "<path>",
      "line_range": "<start-end>",
      "severity": "Critical|High|Medium|Low",
      "category": "auth-bypass | rbac-missing | audit-missing | secrets-hardcoded | env-leak | cors-wide | sql-injection | xss | csrf | dev-wrap-around",
      "title": "<짧은 제목>",
      "description": "<상세>",
      "recommendation": "<auth middleware / parametrized query / escape / token 등>",
      "redact_secret": <true|false>
    }
  ],
  "score": <0-100>,
  "summary": "<영역 한 줄 요약>"
}

⚠️ **Secret 감지 시 raw 값 절대 출력 X**. `redact_secret: true` + file:line 만 보고. raw secret 은 어떠한 필드에도 포함하지 말 것.

read-only.
```

### Step 3 — 5 결과 수집 + 부분 실패 처리

5개 결과 모두 wait. 결과 각각이 위 schema 따라야 함. 1건 fail 시 `area.status: "failed"` 마킹 + 나머지로 계속 (부분 보고서 생성).

```python
# 메인이 결과 종합 (의사 코드)
areas = {
    "api_cost": A_result or {"status": "failed", "findings": [], "score": null},
    "pii": B_result or {"status": "failed", ...},
    "sensitive_logic": C_result or {...},
    "agent": D_result or {...},
    "governance": E_result or {...},
}
```

### Step 4 — Subagent F dispatch (HTML 보고서 생성, primary)

메인이 `commands/audit-report-prompt.md` Read → 1 Task 호출:
- `subagent_type: "general-purpose"`
- `model: "sonnet"`
- `run_in_background: false`
- 입력: 5 areas 결과 + project_meta (git remote / detected stack / rough loc) + timestamp (`YYYY-MM-DD-HHMMSS`)
- 출력 target: `docs/audit/<timestamp>-audit-risk.html`

prompt 본문은 `commands/audit-report-prompt.md` 전체 + 입력 schema JSON inject.

### Step 4.5 — F 결과 검증 + fallback (v2.3.1+)

F 가 단일 Write tool 호출 후 보고. 메인이 다음 검증:

```bash
# (a) 파일 존재 + size guard (0 < size ≤ 120KB)
[ -f "docs/audit/<timestamp>-audit-risk.html" ] && \
  size=$(stat -f%z "docs/audit/<timestamp>-audit-risk.html" 2>/dev/null || stat -c%s "docs/audit/<timestamp>-audit-risk.html") && \
  [ "$size" -gt 0 ] && [ "$size" -le 122880 ]
```

| F 보고 / 검증 결과 | 메인 액션 |
|---|---|
| `Status: DONE` + 파일 존재 + size OK | 정상 → Step 5 진행 |
| `Status: BLOCKED — Write failed at <reason>` 또는 파일 부재 | **메인 takeover** (아래) |
| `Status: BLOCKED — verification failed` | F 보고 reason 노출 + **메인 takeover** |
| 파일 존재 + size = 0 (empty / corrupt) | partial write — `rm <path>` + **메인 takeover** |
| 파일 존재 + size > 120KB | partial / runaway 가능 — `rm <path>` + **메인 takeover** (시각 요소 압축) |

#### Fallback: 메인 takeover (v2.3.1+)

F 가 BLOCKED 또는 partial write 한 경우, 메인이 직접 HTML 생성:

1. **partial file cleanup**: `rm -f docs/audit/<timestamp>-audit-risk.html` (disk 잔존 방지)
2. 메인이 `commands/audit-report-prompt.md` 의 룰 답습 (메모리에서 HTML 작성)
3. 단일 Write tool 호출 — `docs/audit/<timestamp>-audit-risk.html` (메인은 컨텍스트에 5 areas raw 이미 보유 — 재전달 비용 0)
4. takeover 결과를 사용자 출력에 표시: `⚠️ F subagent BLOCKED (<reason>) — 메인 takeover 로 HTML 생성됨.`

이 fallback chain 은 v2.3.0 dogfood 에서 catch 된 회귀 해결: F 가 ~55KB+ HTML 을 chunk write 시도 → verification 무한 루프 + partial file disk 잔존.

### Step 5 — 사용자 1줄 요약 출력

```
✅ 감사 완료: docs/audit/<timestamp>-audit-risk.html
- Critical: <N>건 / High: <N>건 / Medium: <N>건 / Low: <N>건
- 영역별 점수: API <X>/100, PII <X>/100, 민감로직 <X>/100, 에이전트 <X|PASS>/100, 거버넌스 <X>/100

⚠️ best-effort LLM 감사. 정확한 청구서 X. 외부 보안 도구 (Snyk / SonarQube / Semgrep) 와 보완 관계. Secret 의심 항목은 보고서에서 `****` 마스킹됨.
```

## Non-goals

- 자동 fix / 수정 PR 생성 — 사용자가 보고서 보고 직접 결정
- 비용 예측 정확도 보증 — best-effort 추정
- CVE 자동 매칭 / 컴플라이언스 인증 (OWASP / SOC2 / GDPR)
- 외부 보안 도구 (Snyk / SonarQube / Semgrep) 연동
- CI/CD 통합 — 수동 호출만
- 차분 감사 (이전 보고서와 diff) — v2.3.x 후속 후보
- 5 영역 외 추가 영역 (퍼포먼스 / 접근성 / 라이센스) — v2.3.x 후속 후보
- `.auditignore` suppress — v2.3.x 후속 후보

## 빈도 / 비용

자동 발동 경로 0. 사용자 명시 호출만. 1회 비용 = Sonnet × 6 + 약간의 context7/WebSearch. 누적 비용 미미.
