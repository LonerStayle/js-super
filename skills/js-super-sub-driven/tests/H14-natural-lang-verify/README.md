# H14 — 계획서 테스트 자연어 축약 (v2.9+)

**검증 필드 기반 실행 분기 + dispatch 모델 판정 dogfood**

## 시나리오 A (새 형식)

plan 의 task 에 테스트 코드 블록 없음 + 헤더에 `**검증**: 잔액 0 미만 출금 시 예외 발생 + 잔액 불변` + `Files: Test: tests/test_wallet.py` + `**Model**: sonnet`.

**기대:**
- implementer dispatch 모델 = plan `**Model**:` 값 (최소 sonnet) — 신규 테스트 작성 포함 판정
- implementer 가 검증 설명 기반 테스트 코드 자체 작성 → FAIL 확인 → 구현 byte-copy → PASS
- 구현 코드 블록은 STRICT BYTE-COPY 유지

## 시나리오 B (기존 형식 — 하위 호환)

plan 의 task 에 테스트 코드 블록 존재 (v2.8 이전 형식).

**기대:**
- 블록 존재 = 기존 룰 우선 — 테스트도 byte-copy, 자체 작성 금지
- implementer dispatch 모델 = haiku (byte-copy)

## 시나리오 C (혼재 plan)

task 1 은 새 형식, task 2 는 기존 형식.

**기대:** task 단위 분기 — 한 plan 안에서 두 룰이 task 별로 독립 적용.

## 연결 위험

- 하위 호환 분기 누락 → 시나리오 B 에서 자체 작성 drift (implementer-prompt "Test Authoring (v2.9+ split rule)" 가 catch)
- `Test:` 경로 제거 → wave 충돌 감지 손실 (writing-plans 템플릿의 Test: 경로 유지 룰이 catch)
