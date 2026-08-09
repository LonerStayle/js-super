# G5: Model Hint = haiku

**Scenario:** plan 의 task 1 에 `**Model**: haiku` 명시.

**Expected:** task 1 은 신규 테스트 작성 없음 (`**검증**:` 필드/`Test:` 경로 기반 판정) → 메인이 implementer dispatch 시 `model: "haiku"` 로 호출 (v2.9+ 조건부 룰의 순수 byte-copy 분기). spec-reviewer 는 sonnet.
