# G8: Spec-reviewer Always Sonnet

**Scenario:** plan task 1 에 `**Model**: haiku` 박힘 (implementer 는 sonnet 으로 격상). 동시에 spec-reviewer dispatch 가 sonnet 인지 검증. G5 plan 재사용.

**Expected dispatch:**
- Implementer: `model: "sonnet"` (Task 1 hint 는 금지된 값 → 격상)
- Spec reviewer: `model: "sonnet"` (D11 고정, hint 무관)
