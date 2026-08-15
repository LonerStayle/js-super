---
description: "프로젝트 전체의 보안 / 개인정보 / 비용 / 거버넌스를 1회성으로 점검하고 마크다운 보고서 1개를 남깁니다. 코드는 변경하지 않습니다."
disable-model-invocation: true
---

# /audit-risk

이 슬래시는 프로젝트 전체의 **보안 / 개인정보 / 비용 / 거버넌스를 1회성으로 점검**하는 명령입니다. 코드는 변경하지 않고, 마크다운 보고서 1개를 남깁니다 (`docs/audit/<timestamp>-audit-risk.md`, gitignored).

> **자동 발동 없음** — 사용자가 명시적으로 호출할 때만 발동합니다. 1회 호출 비용은 보조 에이전트 기준으로 축소 모드 1개, 전체 모드 5개입니다. 여기에 context7 / WebSearch 조회가 조금 더해집니다.
> **코드를 읽어 판단한 결과입니다** — 정확한 청구서가 아니고, 외부 보안 도구 (Snyk / SonarQube / Semgrep) 를 대신하지도 않습니다. 보완 관계로 사용해주세요.

## 흐름 (메인 에이전트 단계별 실행)

```
Step 1  출력 폴더 보장 + 코드 규모 측정 → 모드 결정 (축소 / 전체)
Step 2  [축소 모드] 보조 에이전트 1개가 다섯 영역을 순서대로 순회
        [전체 모드] 보조 에이전트 5개를 한 메시지에 병렬 호출
Step 3  결과 취합 (영역 1개 실패해도 나머지로 진행)
Step 4  메인이 마크다운 보고서를 직접 작성 (Write 1회)
Step 5  사용자에게 요약 출력
```

---

### Step 1 — 출력 폴더 보장 + 규모 판정

```bash
mkdir -p docs/audit/

EXT_RE='\.(js|jsx|mjs|cjs|ts|tsx|py|go|rb|java|kt|kts|swift|rs|php|cs|c|h|cc|cpp|hpp|m|mm|scala|dart|sh|sql|vue|svelte)$'

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SRC=$(git ls-files | grep -Ei "$EXT_RE")
else
  SRC=$(find . -type d \( -name node_modules -o -name .git -o -name dist -o -name build \
        -o -name vendor -o -name .venv -o -name target \) -prune -o -type f -print \
        | grep -Ei "$EXT_RE")
fi

FILE_COUNT=$(printf '%s\n' "$SRC" | grep -c . )
LINE_COUNT=$(printf '%s\n' "$SRC" | grep . | tr '\n' '\0' | xargs -0 cat 2>/dev/null | wc -l | tr -d ' ')

echo "파일 ${FILE_COUNT} / 줄 ${LINE_COUNT:-0}"
```

**모드 결정** — 아래 두 조건을 **모두** 만족할 때만 축소 모드입니다.

- 소스 파일 수가 40개 미만이다
- 총 줄 수가 8,000 미만이다

둘 중 하나라도 넘으면 전체 모드입니다. 어느 한쪽이라도 크면 전체 모드로 가므로, 애매한 경우는 자동으로 전체 모드가 됩니다.

측정값과 모드는 사용자에게 한 줄로 알립니다. 사용자에게 보여줄 때는 축소 모드를 "간단 모드" 로 적습니다.

```
점검 대상 27개 파일 / 4,100줄 — 간단 모드로 진행합니다.
```

```
점검 대상 214개 파일 / 38,600줄 — 전체 모드로 진행합니다.
```

측정이 실패하면 (명령 오류 / 소스 파일 0개) 전체 모드로 진행하고, 그 사실을 한 줄 알립니다.

---

### Step 2 — 보조 에이전트 호출 (모드 분기)

각 영역 프롬프트는 **아래 "공통 지시문" 전문 + 해당 영역 블록**을 이어 붙여 만듭니다. 공통 지시문을 빼고 영역 블록만 넘기면 안 됩니다.

#### 축소 모드 — 보조 에이전트 1개

`Task` 호출 1회 (`subagent_type: "general-purpose"`, `model: "sonnet"`, `run_in_background: false`).

프롬프트 = 공통 지시문 + 영역 A~E 블록 5개 전부. 다음 문장을 함께 넣습니다.

```
다섯 영역 (A 외부 API 비용 / B 개인정보 / C 사용량·결제 로직 / D LLM 에이전트 / E 거버넌스) 을
A 부터 E 까지 순서대로 모두 점검한다. 코드베이스가 작다는 이유로 영역을 건너뛰지 않는다.
영역마다 별도의 반환 객체를 만들고, 최종 출력은 다섯 개 객체를 담은 배열로 낸다:

[
  {"area": "api_cost", "status": ..., "checked": [...], "findings": [...], "unverified": [...], "summary": "..."},
  {"area": "pii", ...},
  {"area": "sensitive_logic", ...},
  {"area": "agent", ...},
  {"area": "governance", ...}
]
```

#### 전체 모드 — 보조 에이전트 5개 병렬

메인이 **한 메시지에 5개 `Task` 호출** (`subagent_type: "general-purpose"`, `model: "sonnet"`, `run_in_background: false`). 각 프롬프트는 공통 지시문 + 영역 블록 1개. 다섯 결과를 모두 기다립니다.

---

## 공통 지시문 (모든 영역 프롬프트 앞에 붙임)

```
이 프로젝트를 읽기 전용으로 점검한다. 코드를 수정하지 않는다.

## 심각도 정의 (3단계)

- 심각 — 실행 경로 확인됨. 발생 시 데이터 유출·손실 또는 금전 손실로 직결
- 높음 — 실행 경로 확인됨. 영향이 조건부이거나 범위가 제한적
- 보통 — 실행 경로 확인됨. 즉각적인 피해는 없고 관행·유지보수 문제

세 단계 모두 "실행 경로를 확인했다" 를 전제로 한다. 실행 경로를 확인하지 못한 항목에는
심각도를 붙이지 않고 unverified 배열로 보낸다. 낮은 심각도를 붙여 건수를 늘리지 않는다.

## 표현 규칙

- 코드에서 확인한 사실 (evidence) 과 그로 인한 영향 (impact) 을 분리해서 적는다
- 비용 추정은 단가 출처와 호출 빈도 근거를 함께 댈 수 있을 때만 적고, 그렇지 않으면 적지 않는다
- "치명적", "심각한", "위험천만", "즉시" 같은 형용사·부사를 쓰지 않는다
- 발견 항목이 없으면 만들어내지 말고 status: "clean" 과 확인 범위를 반환한다

## 반환 형식

{
  "status": "clean | findings | skipped | failed",
  "checked": ["<무엇을 어떤 기준으로 봤는지 — 1~3 항목>"],
  "findings": [ ... ],
  "unverified": [ ... ],
  "summary": "<한 줄>"
}

- "clean" — 점검했고 해당 항목이 없음
- "findings" — 발견 항목 있음
- "skipped" — 이 영역이 이 프로젝트에 적용되지 않음 (예: LLM 에이전트 코드 자체가 없음)
- "failed" — 점검을 끝내지 못함

checked 는 status 가 "clean" 일 때 필수다. 무엇을 봤는지 남겨야 "점검했지만 없음" 과
"점검하지 않음" 이 구분된다. status 가 "findings" 일 때도 채우면 좋다.

### findings 항목

{
  "file": "<경로>",
  "line_range": "<시작-끝>",
  "severity": "심각 | 높음 | 보통",
  "category": "<영역별 하위 분류>",
  "title": "<제목>",
  "evidence": "<코드에서 확인한 사실>",
  "impact": "<이 상태에서 무엇이 일어나는지>",
  "recommendation": "<권장 조치>"
}

### unverified 항목 (심각도 없음)

{
  "file": "<경로>",
  "line_range": "<시작-끝>",
  "title": "<제목>",
  "why_unverified": "<코드만으로 판단할 수 없는 이유>",
  "how_to_check": "<사용자가 확인하는 방법>"
}
```

---

## 영역 블록

### 영역 A — 외부 API 비용

```
점검 영역: 외부 API 비용 위험. area 값은 "api_cost".

## 검출 대상
- HTTP client 사용처 (fetch / axios / got / requests / aiohttp / urllib)
- 외부 SDK 임포트 (openai / anthropic / stripe / twilio / sendgrid / aws-sdk / google-cloud / azure)
- 호출 패턴: loop 안 호출 / N+1 / retry 무한 / cache 미적용 / batch 안 묶음

## 비용 근거 조회 (근거를 댈 수 있을 때만)
- context7 로 각 SDK 의 가격 페이지 조회 (예: openai → 토큰 단가)
- context7 결과가 부족하면 WebSearch fallback ("<sdk-name> pricing 2026")
- 단가 출처와 호출 빈도 근거를 둘 다 확보한 경우에만 evidence 에 숫자를 적는다
- 둘 중 하나라도 없으면 숫자를 적지 않고, 호출 패턴 사실만 적는다

## 심각도 기준 (세 단계 모두 실행 경로를 확인한 항목에만 붙인다)
- 심각 — 유료 호출이 loop 또는 사용자 요청 경로 안에 있고 상한·캐시가 없음
- 높음 — 유료 호출에 재시도 상한이 없거나, 호출 빈도가 외부 입력에 좌우됨
- 보통 — 유료 호출이 배치로 묶이지 않았거나 캐시 대상인데 캐시가 없음

호출 경로를 확인하지 못한 코드 (진입점이 없어 보이는 코드 포함) 는 unverified 로 보낸다.

## category 값
loop-call | retry-infinite | no-cache | batch-missing | n-plus-1

## 추가 반환 필드
"sdks_detected": ["<감지한 SDK 목록>"]
```

### 영역 B — 개인정보

```
점검 영역: 사용자 개인정보 (PII) 노출 위험. area 값은 "pii".

## 검출 대상
- 필드 keyword: email / phone / mobile / ssn / 주민번호 / passport / 카드번호 / cvv /
  address / 주소 / 생년월일 / birthday / dob / ip_address / device_id / mac_address
- 평문 저장 패턴 (DB write / file write / localStorage / sessionStorage / cookie)
- log 출력 패턴 — console.log / logger.{info,debug} / print / slog / fmt.Println 에 개인정보 직접 포함
- 외부 송신 — 외부 API body / GA / Sentry / Mixpanel 등에 개인정보 포함
- response body 에 불필요한 개인정보 포함

## 심각도 기준 (세 단계 모두 실행 경로를 확인한 항목에만 붙인다)
- 심각 — 로그 또는 외부 송신에 개인정보가 평문으로 나가는 경로를 확인함
- 높음 — 개인정보가 암호화 없이 저장되는 경로를 확인함
- 보통 — 응답에 필요 이상의 개인정보가 포함되거나 표시 시 마스킹이 없음

필드 이름만 개인정보처럼 보이고 실제 값의 출처를 확인하지 못한 경우는 unverified 로 보낸다.

## category 값
log-leak | db-plaintext | external-send | response-overshare | no-masking

## 추가 반환 필드
findings 항목마다 "pii_field": "<email | phone | ssn | ...>"

개인정보 값 자체를 출력하지 않는다. 파일 경로와 줄 번호, 필드 이름만 적는다.
```

### 영역 C — 사용량·결제 로직

```
점검 영역: 사용량 / 비용 / 결제 로직 결함. area 값은 "sensitive_logic".

## 검출 대상
- keyword: usage / cost / bill / payment / charge / subscription / credit / quota /
  limit / rate-limit / balance
- 패턴:
  - Race condition — 잠금이나 트랜잭션 없는 카운터 증가 (`counter++` / `count = count + 1`)
  - Off-by-one — `< limit` 과 `<= limit` 혼용
  - 검증 누락 — 입력 sanitize / 음수 / overflow 미체크
  - 트랜잭션 부재 — 다단계 결제나 잔액 차감과 부수 작업이 한 트랜잭션 밖
  - 멱등성 부재 — 결제나 외부 요청 재시도 시 중복 처리 (idempotency key 없음)

## 심각도 기준 (세 단계 모두 실행 경로를 확인한 항목에만 붙인다)
- 심각 — 금액이나 잔액을 바꾸는 경로에서 경합 또는 트랜잭션 부재를 확인함
- 높음 — 결제 경로에 멱등성 장치가 없음을 확인함
- 보통 — 경계 조건 오류나 입력 검증 누락을 확인함

호출되는 지점을 찾지 못한 코드는 unverified 로 보낸다. 예전 방식대로 낮은 심각도를 붙이지 않는다.

## category 값
race | off-by-one | validation-missing | no-transaction | no-idempotency
```

### 영역 D — LLM 에이전트

```
점검 영역: LLM 에이전트 위험. area 값은 "agent".

## 사전 확인 (반드시 시작 직전 실행)

LLM 에이전트 코드가 있는지 grep 으로 먼저 확인한다.
- import 패턴: openai / anthropic / langchain / langgraph / crewai / autogen / llamaindex
- system prompt 변수 / tool calling 코드
- agent loop / multi-turn / orchestrator

없으면 즉시 종료하고 아래를 반환한다. 없는 위험을 만들어내지 않는다.

{
  "status": "skipped",
  "checked": ["LLM SDK 임포트 / system prompt 변수 / tool calling 코드 grep"],
  "findings": [],
  "unverified": [],
  "summary": "LLM 에이전트 관련 코드가 없어 이 영역은 해당되지 않음"
}

있으면 아래를 점검한다.

## 검출 대상
- 민감 데이터 접근 — 에이전트 context 나 tool 이 개인정보 / 결제 정보 / 인증 토큰에 접근
- Prompt injection 취약 — 사용자 입력이 sanitize 없이 system prompt 에 주입
- System prompt 노출 — 응답에 system prompt 가 그대로 나갈 수 있는 경로
- Tool 권한 과다 — 파괴적 도구 (DB delete / 결제 / 메일 발송) 를 검증 없이 호출 가능
- 출력 검증 미적용 — LLM 출력을 그대로 실행하거나 DB write / 외부 호출에 사용

## 심각도 기준 (세 단계 모두 실행 경로를 확인한 항목에만 붙인다)
- 심각 — 파괴적 도구를 검증 없이 호출하는 경로를 확인함
- 높음 — 사용자 입력이 프롬프트에 주입되면서 민감 데이터에 접근하는 경로를 확인함
- 보통 — system prompt 노출 가능성 또는 출력 검증 누락을 확인함

## category 값
sensitive-data-access | prompt-injection | system-prompt-leak | tool-overpermission |
no-output-validation

## 추가 반환 필드
"agent_frameworks_detected": ["<감지한 프레임워크 목록>"]
```

### 영역 E — 거버넌스

```
점검 영역: 인증 / 권한 / 감사 로그 / 거버넌스 회피 위험. area 값은 "governance".

## 검출 대상
- 인증 미들웨어 우회 — 라우트 핸들러에 인증 검사 없음 (특히 admin / internal API)
- 권한 분기 미적용 — 권한별 분기 없는 민감 endpoint
- 감사 로그 결여 — 결제 / 권한 변경 / 데이터 삭제 후 기록 없음
- 비밀값 하드코딩 — API key / DB password / JWT secret 이 코드에 평문
- 환경변수 부주의 — process.env.X 를 sanitize 없이 클라이언트에 노출
- CORS 과다 허용 — `*` 또는 너무 넓은 origin
- SQL injection — 문자열 concat 으로 쿼리 조립
- XSS — HTML escape 없이 사용자 입력 렌더링
- CSRF — 상태를 바꾸는 endpoint 가 CSRF token 미검증
- 검증 우회 분기 — `if (env === "dev")` 같은 분기로 운영에서 검증을 건너뜀

## 심각도 기준 (세 단계 모두 실행 경로를 확인한 항목에만 붙인다)
- 심각 — 비밀값 하드코딩, SQL injection, 관리자 경로 인증 우회 중 하나를 확인함
- 높음 — 권한 분기 누락 / XSS / CSRF 경로를 확인함
- 보통 — 감사 로그 결여 또는 CORS 과다 허용을 확인함

라우트가 실제로 노출되는지 확인하지 못한 경우는 unverified 로 보낸다.

## category 값
auth-bypass | rbac-missing | audit-missing | secrets-hardcoded | env-leak |
cors-wide | sql-injection | xss | csrf | dev-wrap-around

## 추가 반환 필드
findings 항목마다 "redact_secret": <true|false>

비밀값을 감지해도 값 자체를 절대 출력하지 않는다. "redact_secret": true 로 표시하고
파일 경로와 줄 번호만 적는다. raw 비밀값은 어떠한 필드에도 넣지 않는다.
```

---

### Step 3 — 결과 취합 + 부분 실패 처리

다섯 영역 결과를 모읍니다. 각 결과는 공통 지시문의 반환 형식을 따라야 합니다.

영역 1개가 실패하거나 형식을 어기면 그 영역만 `{"status": "failed", "checked": [], "findings": [], "unverified": [], "summary": "<실패 이유>"}` 로 표시하고, 나머지 영역으로 부분 보고서를 만듭니다. 전체를 중단하지 않습니다.

```python
# 메인이 결과를 종합 (의사 코드)
areas = {
    "api_cost":        A_result or {"status": "failed", "summary": "점검 실패"},
    "pii":             B_result or {"status": "failed", "summary": "점검 실패"},
    "sensitive_logic": C_result or {"status": "failed", "summary": "점검 실패"},
    "agent":           D_result or {"status": "failed", "summary": "점검 실패"},
    "governance":      E_result or {"status": "failed", "summary": "점검 실패"},
}
```

축소 모드에서는 에이전트 1개가 배열 5개를 반환하므로, `area` 값으로 위 다섯 칸에 채워 넣습니다. 배열에 빠진 영역이 있으면 그 영역을 `failed` 로 표시합니다.

---

### Step 4 — 메인이 마크다운 보고서 직접 작성

메인은 영역별 결과를 이미 갖고 있으므로 다른 에이전트에게 다시 넘기지 않습니다. `Write` 도구 1회로 `docs/audit/<timestamp>-audit-risk.md` 를 만듭니다. `<timestamp>` 형식은 `YYYY-MM-DD-HHMMSS` 입니다.

#### 작성 시 표현 규칙 (영역 프롬프트와 동일)

- 코드에서 확인한 사실과 그로 인한 영향을 분리해서 적는다
- 비용 추정은 단가 출처와 호출 빈도 근거를 함께 댈 수 있을 때만 적고, 그렇지 않으면 적지 않는다
- "치명적", "심각한", "위험천만", "즉시" 같은 형용사·부사를 쓰지 않는다
- 발견 항목이 없으면 만들어내지 말고 "점검함, 해당 항목 없음" 과 확인 범위를 적는다

영역 상태를 표에 옮길 때는 이 대응을 씁니다.

| 반환 status | 보고서 표기 |
|---|---|
| `findings` | 발견 N건 |
| `clean` | 점검함, 해당 항목 없음 |
| `skipped` | 해당 없음 (관련 코드 없음) |
| `failed` | 점검 실패 |

#### 보고서 구조

```markdown
# 감사 결과 — <프로젝트명>

생성: <YYYY-MM-DD HH:MM> / 모드: 간단(1) | 전체(5) / 대상: <N>개 파일, <M>줄

이 결과는 코드를 읽어 판단한 것으로, 외부 보안 도구를 대신하지 않습니다.

## 요약

| 심각도 | 건수 |
|---|---|
| 심각 | N |
| 높음 | N |
| 보통 | N |
| 확인 필요 | N |

| 영역 | 상태 |
|---|---|
| 외부 API 비용 | 발견 N건 |
| 개인정보 | 점검함, 해당 항목 없음 |
| 사용량·결제 로직 | 점검함, 해당 항목 없음 |
| LLM 에이전트 | 해당 없음 (관련 코드 없음) |
| 거버넌스 | 발견 N건 |

## 영역별 결과
### <영역명>
<발견 항목이 있으면 항목별로 파일:줄 / 확인한 사실 / 영향 / 권장 조치>
<없으면: 점검함, 해당 항목 없음. 확인한 범위: ...>

## 확인 필요
<심각도 미부여 항목 — 왜 판단 못 했는지 + 확인 방법>

## 조치 순서
<심각 → 높음 → 보통 순 목록>
```

비밀값으로 표시된 항목 (`redact_secret: true`) 은 보고서에도 값을 적지 않고 파일 경로와 줄 번호만 남깁니다.

---

### Step 5 — 사용자 요약 출력

```
감사를 마쳤습니다. 보고서는 docs/audit/<timestamp>-audit-risk.md 에 있습니다.
모드: 간단 (보조 에이전트 1개) / 대상: 27개 파일, 4,100줄
심각 2건, 높음 3건, 보통 5건, 확인 필요 4건입니다.

영역별 상태
- 외부 API 비용: 발견 2건
- 개인정보: 점검함, 해당 항목 없음
- 사용량·결제 로직: 점검함, 해당 항목 없음
- LLM 에이전트: 해당 없음 (관련 코드 없음)
- 거버넌스: 발견 8건

이 결과는 코드를 읽어 판단한 것입니다. 외부 보안 도구 (Snyk / SonarQube / Semgrep) 를 대신하지 않습니다.
비밀값으로 의심되는 항목은 값 없이 파일과 줄 번호만 적었습니다.
```

영역이 실패한 경우 그 영역 줄에 "점검 실패" 와 이유를 적고, 부분 보고서라는 사실을 한 줄 덧붙입니다.

## Non-goals

- 자동 수정 / 수정 PR 생성 — 사용자가 보고서를 보고 직접 결정합니다
- 비용 추정 정확도 보증 — 근거를 댈 수 있을 때만 적고, 그 값도 추정입니다
- CVE 자동 매칭 / 컴플라이언스 인증 (OWASP / SOC2 / GDPR)
- 외부 보안 도구 (Snyk / SonarQube / Semgrep) 연동
- CI/CD 통합 — 수동 호출만 합니다
- 차분 감사 (이전 보고서와 비교) — 후속 후보
- 다섯 영역 외 추가 영역 (퍼포먼스 / 접근성 / 라이센스) — 후속 후보
- `.auditignore` 로 항목 감추기 — 후속 후보

## 빈도 / 비용

자동 발동 경로가 없습니다. 사용자 명시 호출만 있습니다. 1회 비용은 축소 모드에서 Sonnet 보조 에이전트 1개, 전체 모드에서 5개이고, 여기에 context7 / WebSearch 조회가 조금 더해집니다. 보고서 작성은 메인이 직접 하므로 추가 에이전트가 붙지 않습니다.
