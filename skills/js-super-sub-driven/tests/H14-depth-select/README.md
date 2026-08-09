# H14 — 산출물 깊이 선택 (depth 2/3) 시나리오 fixture

산출물 깊이 선택 기능의 기대 동작 검증. spec: `docs/features/2026-08-09-산출물-깊이-선택/`.

## 시나리오 A — 정식 플로우, 3개 선택 (기존 동작)

- tech-design 승인 → Gate #12 에서 "구현계획서까지 진행 (3개)" 선택
- 기대: `writing-plans` invoke, frontmatter 기록 없음, 기존 흐름과 동일

## 시나리오 B — 정식 플로우, 2개 확정

- Gate #12 에서 "여기서 종료 (2개 확정)" 선택
- 기대: tech-design 맨 위 frontmatter `depth: 2` + `depth_reason: 사용자 선택` 기록, [개발방향-수정] entry 추가, `ℹ️ 이 피처는 2개 문서로 확정됐습니다 ...` 출력 후 stop. writing-plans 미호출

## 시나리오 C — auto-flow, 3개 판정 (기존 동작)

- auto-tech-design Step 7 판정: 코드 변경·구현 task 예상 → 3개
- 기대: transition notice 출력 후 `js-super:auto-writing-plans` invoke (체인 지속)

## 시나리오 D — auto-flow, 2개 판정

- auto-tech-design Step 7 판정: 순수 문서·설계·조사 성격 → 2개
- 기대: frontmatter `depth: 2` + `depth_reason: <근거 1줄>` 기록 + [개발방향-수정] entry + 판단 근거 1줄 포함 종료 보고. auto-writing-plans 미호출, transition notice 미출력

## 시나리오 E — 승격 (2 → 3)

- depth: 2 피처에서 `/write-plan` (또는 `/auto-write-plan`) 명시 실행
- 기대: 승격 안내 1줄 (재확인 게이트 없음) → frontmatter `depth: 3` 갱신 + `depth_reason` 승격 사유 교체 + [개발방향-수정] entry → 기존 흐름 진행

## 보조 검증

- depth: 2 피처에서 `/execute-plan` → preflight fail + human_reason 에 "2개 문서로 확정된 트랙 ... /write-plan 으로 승격" 안내 노출
- 2-doc 피처의 [코드-수정]/[검증]/[릴리즈] entry → tech-design footer 라우팅 (change-history 2-doc 룰)
- 판정 fallback: frontmatter 부재 / `depth: 3` / 수동 삭제 → 전부 3-doc 동작
