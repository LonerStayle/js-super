# 요구사항: 서브에이전트 sonnet 기본 (haiku 사용 금지)

> **다음 단계 안내**: 이 문서는 요구사항 (기획 단계) 입니다. 다음 단계로 `tech-design` skill (또는 `/design-tech` 슬래시) 을 호출해서 `<slug>-tech-design.md` (기술 설계서) 를 만드세요. 기술 결정이나 구현 세부사항은 여기 박지 마세요 — 그건 다음 산출물 (tech-design, 3개 트랙이면 plan 까지) 에 들어갑니다.

## 배경

`/execute-plan` 에서 이어지는 서브에이전트 실행 경로 (`js-super-sub-driven`) 는 지금 순수 byte-copy task 의 implementer 를 haiku 로 고정 dispatch 한다. 계획서 작성 쪽 (`writing-plans` / `auto-writing-plans`) 도 task 헤더의 `**Model**:` 필드에 haiku 를 허용하고, "1-2 파일 mechanical" 판정이면 haiku 를 배정한다.

사용자 결정: **haiku 는 품질이 기준에 못 미쳐 사용을 금지한다. 서브에이전트의 기본 (최소) 모델은 sonnet 이다.** byte-copy 같은 기계적 작업이라도 haiku 로 내리지 않는다.

## 핵심 결정

세 가지 방향을 비교했다.

- **A안 — 실행 쪽만 변경**: dispatch 시점에 haiku 를 sonnet 으로 격상. 계획서에는 haiku 표기가 남는다. → 문서와 실제 dispatch 모델이 어긋난다. 이 불일치는 과거에도 회귀로 기록된 패턴이라 기각.
- **B안 — 실행 + 작성 양쪽에서 haiku 제거 (채택)**: `**Model**:` 필드 허용 값을 sonnet | opus 로 줄이고, 실행 쪽 조건부 dispatch 의 haiku 분기를 sonnet 으로 흡수한다. 문서와 실행이 항상 일치한다. 되돌리려면 같은 지점들을 역방향으로 고치면 된다.
- **C안 — haiku 를 옵트인 플래그로 잔존**: 기본은 sonnet, 플래그 명시 시 haiku 허용. → 사용자가 "사용 금지" 를 명시했으므로 기각. 남겨두면 금지 의도가 흐려진다.

사용자 확인: 실행 쪽 + 계획서 작성 쪽 **같이 변경** (B안).

opus 는 지금처럼 무거운 task 용 상위 선택지로 유지한다. 바뀌는 것은 하한선뿐이다 — haiku 가 사라지고 sonnet 이 바닥이 된다.

## 요구 항목

**FR-1**: js-super 의 서브에이전트 dispatch 전 경로에서 haiku 모델 사용을 금지한다. 순수 byte-copy task 를 포함한 implementer dispatch 의 최소 모델은 sonnet 이다.

**FR-2**: 계획서 task 헤더의 `**Model**:` 필드 허용 값을 sonnet | opus 로 줄인다. 기존 판정 룰에서 haiku 로 떨어지던 케이스 (1-2 파일 mechanical 등) 는 sonnet 으로 흡수한다. 계획서 작성 두 경로 (정식 / auto) 가 같은 룰을 갖는다.

**FR-3**: `**Model**:` 필드 생략 시 기본값은 sonnet 이다. 이미 작성된 옛 계획서에 `**Model**: haiku` 가 남아 있어도 실행 시 sonnet 으로 격상해 dispatch 한다 (하위 호환 — 옛 계획서를 고치라고 요구하지 않는다).

**FR-4**: 이미 sonnet 고정인 보조 경로 (spec-reviewer / reorder / code-pretty / glossary) 는 동작을 바꾸지 않는다. 새 룰과 표현이 충돌하지 않는지만 맞춘다.

**FR-5**: 새 룰에 맞게 회귀 방지 장치를 갱신한다 — 결합 메모 (CLAUDE.md) 의 옛 haiku 룰 서술과 회귀 catch grep, 그리고 haiku dispatch 를 기대값으로 삼는 테스트 fixture 들.

## 우려와 해결

- **비용 · 속도 증가**: byte-copy task 까지 sonnet 으로 올리면 dispatch 비용과 대기 시간이 늘어난다. → 사용자가 품질을 우선해 수용한 트레이드오프다. byte-copy 의 STRICT 원본 보존 룰은 모델과 무관하게 그대로 유지되므로 정확성은 손해 보지 않는다.
- **결합 회귀**: 계획서 작성 룰과 dispatch 룰은 한쪽만 고치면 "계획서 모델 ↔ 실제 dispatch 모델 불일치" 회귀가 난다 (CLAUDE.md 결합 메모에 기록된 패턴). → 관련 스킬 본문 + 결합 메모 + fixture 를 한 묶음 (atomic) 으로 변경한다.

## 범위 밖

- og-* 커맨드 흐름 (upstream 원본 실행 경로) — haiku 규칙 자체가 없어 변경 대상 아님
- 모델 상위 선택지 (opus) 의 판정 룰 변경 — 하한선만 바꾼다
- 6 manifest 버전 bump — main 전용 룰에 따라 main 에서 dev 가 직접
- Claude Code 하네스 밖 (codex / cursor / gemini) 대응 문서 — 이번 변경은 스킬 본문 룰만 다룬다

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 00:11] [요구사항-수정]
- **id**: CH-20260829-001
- **이유**: 신규 피처 brainstorming 결과 (auto-flow)
- **무엇이**: 서브에이전트-sonnet-기본-requirements.md 전체 (FR-1..5 + 배경 / 핵심 결정 / 우려와 해결 / 범위 밖)
- **영향범위**: 없음 (최초 생성)
