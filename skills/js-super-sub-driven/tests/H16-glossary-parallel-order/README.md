# H16 — 구현계획서 용어집 + 정리/검증 순서 교체

**code-pretty ‖ glossary 병렬 dispatch → verifying-spec → 사용자 검토 순서 dogfood**

## 시나리오 A (기본 흐름)

`/write-plan` 정식 흐름. 계획서 초안에 `**수정 후**` 코드 블록 2개 + 기존 클래스 3개 참조 + 신규 함수 2개.

**기대:**
- 자체 점검 직후 `code-pretty` 와 `glossary` 의 `Agent` 호출이 **한 메시지** 에 실려 병렬 실행
- `verifying-spec` 는 두 subagent 가 모두 돌아온 **뒤** 실행 — prettify 된 코드 블록을 대상으로 검증
- 사용자 검토 게이트가 계획서 + `<slug>-glossary.md` + 4축 보고서 + 정리 요약을 **한 메시지** 로 노출
- 게이트 질문은 `AskUserQuestion` 도구 호출

## 시나리오 B (용어집 실패)

glossary subagent 가 파일을 쓰지 못하고 종료.

**기대:**
- 승인 게이트는 그대로 진행 (용어집은 blocker 아님)
- "용어집을 만들지 못했습니다" 한 줄 안내 후 계획서만으로 검토
- 재시도 자동 반복 없음

## 시나리오 C (코드 블록 0개 계획서)

문서 변경만 있는 계획서 — `**수정 후**` 블록 0개.

**기대:**
- `code_pretty_check` 는 fail (`'수정 후' 코드 블록이 없습니다`) → code-pretty 스킵
- `glossary_check` 는 **통과** → 용어집은 그대로 생성 (두 helper 의 의도적 조건 차이)

## 시나리오 D (live doc 재진입)

첫 `[구현계획서-수정]` 변경이력 entry 가 이미 찍힌 계획서에서 흐름 재진입.

**기대:** 두 helper 모두 fail (`변경이력 footer not empty`) → code-pretty / glossary 모두 미발화.

## 시나리오 E (auto-flow)

`/auto-write-plan` 실행.

**기대:** `code-pretty` / `glossary` 어느 쪽도 호출 X. 용어집 파일 미생성.

## 연결 위험

- code-pretty 본문만 순서 교체 → writing-plans 가 옛 순서 유지 (교체 무효)
- glossary dispatch 를 code-pretty 뒤로 직렬화 → 대기 시간 2배, 병렬 의도 무화
- glossary subagent 가 계획서를 수정 → 정본 오염 (skill body 의 읽기 전용 룰이 catch)
- 용어집에 `## 변경이력` footer 추가 → 다음 리비전에서 `glossary_check` 가 live 로 오판해 차단
- `glossary_check` 에 `**수정 후**` 조건 추가 → 시나리오 C 에서 용어집 통째로 스킵
