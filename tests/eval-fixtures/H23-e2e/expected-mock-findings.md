# Expected Mock Findings — H23 Ground Truth

H23 의 G1 / G3 시나리오 검증용 ground truth 모의 finding list. dogfood 시 실제 결과와 비교.

## G1 — Golden Path Mock Project

가상 프로젝트 구조 (5 영역 모두 1+ finding):

```
mock-project/
├── src/
│   ├── api/openai_client.py       # API Cost — loop 안 호출
│   ├── handlers/user_route.py     # PII — log leak + Governance — auth bypass
│   ├── billing/payment.py         # Sensitive Logic — race + no idempotency
│   ├── agents/chat_agent.py       # Agent — prompt injection 취약 (D ACTIVE)
│   └── config/secrets.py          # Governance — secrets hardcoded
└── package.json
```

### Expected findings (영역별)

#### API Cost (A)
```json
{
  "file": "src/api/openai_client.py",
  "line_range": "10-25",
  "severity": "Critical",
  "category": "loop-call",
  "title": "OpenAI 호출이 user list loop 안에서 cache 없이 발생",
  "description": "for user in users 안에서 openai.ChatCompletion.create() 직접 호출. cache 또는 batch 미적용.",
  "estimated_cost": {"best": "$50/month", "worst": "$500/month", "confidence": "medium", "basis": "GPT-4 단가 + 추정 사용자 100~1000명"},
  "recommendation": "cache 도입 (redis / in-memory) 또는 batch API 사용. user 별 결과 dedupe."
}
```

#### PII (B)
```json
{
  "file": "src/handlers/user_route.py",
  "line_range": "42-45",
  "severity": "Critical",
  "category": "log-leak",
  "title": "User email + phone 이 access log 에 평문 기록",
  "description": "logger.info(f'User {user.email} ({user.phone}) accessed /profile') — sanitize 없이 평문.",
  "pii_field": "email, phone",
  "recommendation": "마스킹 적용 (e.g., `u***@example.com`) 또는 user_id 만 로깅."
}
```

#### Sensitive Logic (C)
```json
{
  "file": "src/billing/payment.py",
  "line_range": "78-92",
  "severity": "Critical",
  "category": "no-idempotency",
  "title": "결제 처리에 idempotency key 부재",
  "description": "process_payment(amount) 가 retry 시 중복 청구 가능. transaction wrapping 도 없음.",
  "recommendation": "idempotency_key 도입 (UUID 기반) + db transaction 적용."
}
```

#### Agent (D, ACTIVE 가정)
```json
{
  "file": "src/agents/chat_agent.py",
  "line_range": "15-30",
  "severity": "High",
  "category": "prompt-injection",
  "title": "User input 이 system prompt 에 sanitize 없이 주입",
  "description": "system_prompt = f'You are an assistant. User says: {user_input}'. injection 취약.",
  "recommendation": "user_input 을 별도 message turn 으로 분리 + 검증 layer 추가."
}
```

#### Governance (E)
```json
{
  "file": "src/config/secrets.py",
  "line_range": "5",
  "severity": "Critical",
  "category": "secrets-hardcoded",
  "title": "OpenAI API key 가 평문 hardcoded",
  "description": "OPENAI_API_KEY = '<REDACTED>' (line 5). 환경변수로 분리 안 됨.",
  "redact_secret": true,
  "recommendation": "os.environ 또는 secret manager 로 분리. git history rewrite 필요."
}
```

```json
{
  "file": "src/handlers/user_route.py",
  "line_range": "30-32",
  "severity": "Critical",
  "category": "auth-bypass",
  "title": "/admin/users 라우트에 auth middleware 없음",
  "description": "@app.get('/admin/users') 핸들러가 require_auth() 호출 안 함. 누구나 접근 가능.",
  "recommendation": "@require_auth(role='admin') decorator 적용."
}
```

## G3 — Secret Redaction 검증

위 G1 의 Governance secrets-hardcoded finding 이 `redact_secret: true` 이므로:

**Subagent E 출력에서**:
- finding.description 에 raw `sk-test_abc123xyz` 가 포함되면 안 됨 (이미 `<REDACTED>` placeholder)
- recommendation 에도 raw value 0

**Subagent F HTML 출력에서**:
- raw `sk-test_abc123xyz` 패턴 0건
- `****` 또는 `<REDACTED>` 또는 유사 마스킹 표시 ≥ 1건
- file:line (`src/config/secrets.py:5`) 표시 OK

### grep 검증 (사람이 dogfood 시 수행)

```bash
# Raw secret 노출 검증
grep -c "sk-test_abc123xyz" docs/audit/*.html
# expected: 0

# Mask 표시
grep -cE "\*{4,}|<REDACTED>" docs/audit/*.html
# expected: ≥ 1
```

## 사용 방법

1. mock-project setup (위 구조 + 의도된 결함 5개)
2. `/audit-risk` 호출
3. 산출 HTML 의 findings 와 위 ground truth 비교
4. 모든 category / severity 일치 확인
5. G3 의 redact_secret 처리 검증

이 ground truth 는 dogfood 시 안전망. 실제 LLM subagent 가 위 패턴을 detect 못 하면 prompt 본문 (`commands/audit-risk.md` 의 영역별 prompt) 개선 필요.
