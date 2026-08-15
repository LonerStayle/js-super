# Expected Mock Findings — H23 Ground Truth

H23 의 G1(작은 프로젝트) / G4(비밀값 마스킹) 시나리오 검증용 ground truth 모의 finding list. dogfood 시 실제 결과와 비교한다.

## G1 — 작은 프로젝트 Mock Project (다섯 영역 모두 findings 1건 이상)

가상 프로젝트 구조:

```
mock-project/
├── src/
│   ├── api/openai_client.py       # 영역 A — loop 안 호출
│   ├── handlers/user_route.py     # 영역 B — log leak, 영역 E — auth bypass
│   ├── billing/payment.py         # 영역 C — race + no idempotency
│   ├── agents/chat_agent.py       # 영역 D — prompt injection 취약
│   └── config/secrets.py          # 영역 E — secrets hardcoded (G4 와 공유)
└── package.json
```

### Expected findings (영역별)

#### 영역 A — 외부 API 비용
```json
{
  "status": "findings",
  "checked": ["src/api/ 아래 외부 SDK 호출부"],
  "findings": [
    {
      "file": "src/api/openai_client.py",
      "line_range": "10-25",
      "severity": "심각",
      "category": "loop-call",
      "title": "OpenAI 호출이 user list loop 안에서 cache 없이 발생",
      "evidence": "for user in users 안에서 openai.ChatCompletion.create() 를 직접 호출. cache 또는 batch 미적용.",
      "impact": "요청 수만큼 유료 호출이 반복되고, 동일 입력도 매번 다시 호출됨.",
      "recommendation": "cache 도입 (redis / in-memory) 또는 batch API 사용. user 별 결과 dedupe."
    }
  ],
  "unverified": [],
  "summary": "OpenAI 호출 1건이 loop 안에서 cache 없이 발생함",
  "sdks_detected": ["openai"]
}
```

비용 숫자는 단가 출처와 호출 빈도 근거를 둘 다 확보했을 때만 evidence 에 적는다는 커맨드 규칙에 따라, 근거가 없으면 숫자를 적지 않는다.

#### 영역 B — 개인정보
```json
{
  "status": "findings",
  "checked": ["src/handlers/ 아래 로그·응답 출력부"],
  "findings": [
    {
      "file": "src/handlers/user_route.py",
      "line_range": "42-45",
      "severity": "심각",
      "category": "log-leak",
      "title": "user email + phone 이 access log 에 평문 기록",
      "evidence": "logger.info(f'User {user.email} ({user.phone}) accessed /profile') — sanitize 없이 평문.",
      "impact": "로그 시스템에 접근 가능한 누구나 사용자 email/phone 을 볼 수 있음.",
      "pii_field": "email, phone",
      "recommendation": "마스킹 적용 (예: u***@example.com) 또는 user_id 만 로깅."
    }
  ],
  "unverified": [],
  "summary": "user_route.py 의 접근 로그에 email/phone 평문 기록 1건"
}
```

#### 영역 C — 사용량·결제 로직
```json
{
  "status": "findings",
  "checked": ["src/billing/ 아래 잔액·결제 처리 함수"],
  "findings": [
    {
      "file": "src/billing/payment.py",
      "line_range": "78-92",
      "severity": "높음",
      "category": "no-idempotency",
      "title": "결제 처리에 idempotency key 부재",
      "evidence": "process_payment(amount) 가 재시도 시 중복 처리를 막는 idempotency key 없이 잔액을 차감함.",
      "impact": "네트워크 재시도나 중복 요청 시 동일 결제가 두 번 이상 청구될 수 있음.",
      "recommendation": "idempotency_key 도입 (UUID 기반)."
    }
  ],
  "unverified": [],
  "summary": "결제 처리 1건에서 idempotency 부재 확인"
}
```

#### 영역 D — LLM 에이전트
```json
{
  "status": "findings",
  "checked": ["src/agents/ 아래 system prompt 구성부"],
  "findings": [
    {
      "file": "src/agents/chat_agent.py",
      "line_range": "15-30",
      "severity": "높음",
      "category": "prompt-injection",
      "title": "user input 이 system prompt 에 sanitize 없이 주입",
      "evidence": "system_prompt = f'You are an assistant. User says: {user_input}' 형태로 직접 주입.",
      "impact": "사용자 입력으로 system prompt 지시를 덮어쓰는 injection 이 가능함.",
      "recommendation": "user_input 을 별도 message turn 으로 분리 + 검증 layer 추가."
    }
  ],
  "unverified": [],
  "summary": "chat_agent.py 에서 prompt injection 경로 1건 확인",
  "agent_frameworks_detected": ["openai"]
}
```

#### 영역 E — 거버넌스
```json
{
  "status": "findings",
  "checked": ["src/config/ 의 비밀값 선언부", "src/handlers/ 의 인증 미들웨어 적용 여부"],
  "findings": [
    {
      "file": "src/config/secrets.py",
      "line_range": "5",
      "severity": "심각",
      "category": "secrets-hardcoded",
      "title": "OpenAI API key 가 평문 hardcoded",
      "evidence": "OPENAI_API_KEY 변수가 소스 코드에 문자열로 직접 대입되어 있음 (5행). 환경변수로 분리 안 됨.",
      "impact": "저장소에 접근 가능한 누구나 API key 를 확보해 대신 호출할 수 있음.",
      "redact_secret": true,
      "recommendation": "os.environ 또는 secret manager 로 분리. git history rewrite 필요."
    },
    {
      "file": "src/handlers/user_route.py",
      "line_range": "30-32",
      "severity": "심각",
      "category": "auth-bypass",
      "title": "/admin/users 라우트에 인증 미들웨어 없음",
      "evidence": "@app.get('/admin/users') 핸들러가 require_auth() 를 호출하지 않음.",
      "impact": "인증 없이 누구나 /admin/users 에 접근할 수 있음.",
      "redact_secret": false,
      "recommendation": "@require_auth(role='admin') decorator 적용."
    }
  ],
  "unverified": [],
  "summary": "secrets-hardcoded 1건, auth-bypass 1건 확인"
}
```

## G4 — 비밀값 마스킹 검증

위 영역 E 의 secrets-hardcoded finding 이 `redact_secret: true` 이므로 다음을 확인한다.

**보조 에이전트 출력에서**:
- finding 의 evidence / title / recommendation 어디에도 값 자체(`sk-test_abc123xyz`)가 나오지 않는다.
- 파일 경로와 줄 번호만 남는다 (`src/config/secrets.py:5`).

**보고서(`docs/audit/<timestamp>-audit-risk.md`)에서**:
- 값 자체(`sk-test_abc123xyz`)가 0건이다.
- 파일:줄(`src/config/secrets.py:5`) 표시는 그대로 남는다.

### grep 검증 (사람이 dogfood 시 수행)

```bash
# 값 자체 노출 검증
grep -c "sk-test_abc123xyz" docs/audit/*-audit-risk.md
# expected: 0

# 파일:줄 표시는 남아있어야 함
grep -c "secrets\.py" docs/audit/*-audit-risk.md
# expected: ≥ 1
```

## 사용 방법

1. mock-project 를 위 구조와 의도된 결함 6개로 세팅한다.
2. `/audit-risk` 를 호출한다.
3. 산출된 보고서(`docs/audit/<timestamp>-audit-risk.md`)의 findings 를 위 ground truth 와 비교한다.
4. 모든 category / severity 가 일치하는지 확인한다.
5. G4 의 redact_secret 처리를 검증한다.

이 ground truth 는 dogfood 시 안전망이다. 실제 보조 에이전트가 위 패턴을 detect 못 하면 영역별 프롬프트 본문(`commands/audit-risk.md` 의 영역 블록)을 개선해야 한다.
