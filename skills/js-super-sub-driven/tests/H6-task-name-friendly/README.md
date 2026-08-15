# H6 — TaskCreate task 이름 사용자 친화화

## 시나리오

`/brainstorm`, `/design-tech`, `/write-plan`, `/execute-plan` 진입 시 메인이 TaskCreate 로 만든 Checklist 항목 이름이 사용자 친화 한국어인지 검증.

## 기대 동작

1. 각 skill 진입 시 TaskCreate 목록에 다음 패턴이 노출되지 않음:
   - `Invoke ... skill` (예: `Invoke change-history skill`, `Invoke docs-pretty skill`, `Invoke verifying-spec`)
   - `Gate #N` (예: `Gate #13 plan + verify 결합`)
   - `CH-id` (예: `CH-20260510-001`)
   - 영어 식별자 (`docs-pretty`, `verifying-spec`)
2. 대신 한국어 친화 표현 노출:
   - `변경이력 기록`, `문서 포맷 정리`, `사양 정합성 검증`
   - `초안 검토 및 승인`, `다음 단계 진입 확인`, `구현 단계 핸드오프`
3. 본문 (Process Flow / Detailed Step) 의 영어 식별자는 유지 (메인이 정확한 skill 호출에 필요)
4. upstream og-* skill 들 (verbatim) 은 손대지 않음
5. 변경이력 footer 의 entry tag (`[요구사항-수정]` 등) 는 schema 매직 키워드라 유지

## 검증 방법

```bash
for f in skills/brainstorming/SKILL.md skills/tech-design/SKILL.md skills/writing-plans/SKILL.md skills/executing-plans/SKILL.md skills/finishing-a-development-branch/SKILL.md; do
  awk '/^## Checklist/,/^## /' "$f" | grep -cE "Invoke .* skill|Gate #|CH-[0-9]"
done
```

→ 모두 0 출력 PASS.

## 매핑

- AC-15 (Checklist 항목명 사용자 친화)
- AC-17 (Process Flow / Detailed Step 영어 식별자 유지)
- FR-6 (TaskCreate 명칭 룰)
