# H4 — Preflight 강제 실패: AskUserQuestion 게이트 발화

## 시나리오

`<slug>-implementation-plan.md` 에 가짜 변경이력 entry 박은 채로 code-pretty 호출. preflight 가 `변경이력 footer not empty` 로 fail (exit 1) → 게이트 발화. (v2.8.2 에서 docs-pretty/generating-html 계열이 제거돼 현행 preflight 게이트 소비자인 code-pretty 로 대상 교체)

## 입력 (시뮬레이션 setup)

`/tmp/test-h4-implementation-plan.md` 작성. 본 파일에는 다음 구조가 들어가야 함:

- H1: `# 구현계획서: test-h4`
- `**수정 후**` 라벨이 붙은 코드 블록 1개
- 구분선 `---`
- H2 footer: `## 변경이력` (정상 한국어 헤더)
- H3 entry: `### [2026-05-10 12:00] [요구사항-수정]`
- entry 본문: id, 이유, 무엇이, 영향범위 4 필드

## 기대 동작

1. code-pretty Step 1 — preflight bash one-liner 실행
2. exit 1, `human_reason` = `"이미 변경이력 entry 가 존재합니다 (live doc). code-pretty 는 최초 생성 단계에서만 발화합니다"`
3. 메인이 `human_reason` 한 줄 노출 후 AskUserQuestion 게이트:
   - choices: `"수정 후 재시도"` / `"강제 진행 (위험)"` / `"스킵 (이번만)"`
4. 사용자가 `"수정 후 재시도"` 선택 → entry 제거 후 재호출 → preflight ok=True → Step 2 dispatch
5. 사용자가 `"스킵 (이번만)"` 선택 → 이번 호출 스킵 + skill 즉시 종료 (v2.8.2+ 명시 호출 전용 — caller 계약 폐지)

## 매핑

- AC-11 (preflight 강제 실패 시뮬레이션)
- FR-4 (user-gate)

## 주의

이 README 파일 자체는 .md 확장자지만 `*-implementation-plan.md` 패턴 미스매치라 preflight 트리거 안 됨. 정상 한국어 `## 변경이력` 헤더 박아도 preflight 영향 X.
