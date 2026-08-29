# H11 — 사용자 mid-flight 수정 + reorder dispatch (v2.0.0+)

## 시나리오

1. plan 작성 + 저장. plan_byte_check ✅ 통과 (작성 시점 byte-equal).
2. **사용자가 plan 실행 전 직접 `<file>` 편집** (한 줄 추가, 다른 위치).
3. `/auto-execute-plan` 또는 메인 wave-parallel dispatch 발화.
4. Wave 진입 → Implementer (sonnet, byte-copy) 시도.
5. Edit "old_string not found" — 사용자 추가 한 줄 때문에 file 이 plan 의 `**원본**` 과 다름.
6. Implementer Status: BLOCKED — 원본 mismatch at <file>.
7. 메인이 자동으로 Reorder dispatch (sonnet, ./reorder-prompt.md).
8. Reorder 가 사용자 추가 line + plan net change 호환 가능 판정 → 둘 다 적용 → Status: DONE.
9. Spec Reviewer ✅.
10. Wave finalization commit — commit 안 plan 변경 + 사용자 추가 line 둘 다 포함.

## 검증 항목

- [ ] 메인이 reorder dispatch 발화했는지 (Stage 1 BLOCKED → Stage 2 자동)
- [ ] Reorder 가 silent overwrite 안 함 (사용자 line 손실 0)
- [ ] commit 안 plan 변경 + 사용자 변경 둘 다 포함
- [ ] Spec Reviewer 가 정상 통과

## 회귀 패턴

| 회귀 | 증상 |
|---|---|
| Stage 1 BLOCKED 후 Stage 2 안 부름 | 메인 SKILL.md W-2 분기 누락 |
| Reorder 가 user line 무시 | reorder-prompt 의 silent overwrite 차단 룰 약화 |
| Reorder 가 NEEDS_USER 안 escalate | reorder-prompt 의 escalation default 룰 약화 |
| plan_byte_check 가 작성 단계에서 false-pass | helper Mismatch detection 약화 (G1 fixture 이미 catch) |

## 의존

- `skills/js-super-sub-driven/implementer-prompt.md` — STRICT BYTE-COPY rule
- `skills/js-super-sub-driven/reorder-prompt.md` — Status: NEEDS_USER 형식
- `skills/js-super-sub-driven/SKILL.md` — Per-wave Sequence W-2 분기
- `scripts/plan_byte_check.py` — 작성 단계 차단

## 다음 단계

본 fixture 는 release v2.0.0 자체 dogfood 와 자연스럽게 만나야 함. 본 release 의 plan 안 task 1개를 의도적으로 사용자 시뮬레이션 commit 으로 `<file>` 수정 → reorder dispatch 발화 검증.
