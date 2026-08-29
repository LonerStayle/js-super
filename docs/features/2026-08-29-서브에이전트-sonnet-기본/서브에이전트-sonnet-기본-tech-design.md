# 기술설계: 서브에이전트 sonnet 기본 (haiku 사용 금지)

> **입력**: `서브에이전트-sonnet-기본-requirements.md` (FR-1..5)
> **다음 단계**: `/write-plan` (또는 auto-writing-plans) 로 구현계획서 작성

## 1. 구조 개요

모델 규칙은 두 층으로 나뉘어 있다.

- **계획서 작성 층** — 계획서를 쓸 때 task 마다 `**Model**:` 값을 산정하는 룰. 정식 경로와 자동 경로가 같은 판정표를 복제해 갖고 있다.
- **실행 층** — 서브에이전트 실행 경로가 implementer 를 띄울 때 실제 모델을 정하는 룰. 지금은 조건부 2분기다: 순수 byte-copy task 는 haiku 고정, 신규 테스트 작성 포함 task 는 계획서의 `**Model**:` 값 (최소 sonnet).

이번 변경으로 실행 층의 분기 자체가 사라진다. **implementer 는 항상 계획서의 `**Model**:` 값으로 dispatch 하고, 값이 없거나 haiku 면 sonnet 으로 올린다.** 계획서 작성 층은 `**Model**:` 허용 값을 sonnet | opus 두 개로 줄이고, haiku 로 떨어지던 판정 행을 sonnet 으로 흡수한다. 두 층이 같은 하한선 (sonnet) 을 공유하므로 문서와 실제 dispatch 가 어긋날 여지가 없어진다.

이미 sonnet 고정인 보조 경로 (spec-reviewer / reorder / code-pretty / glossary) 는 변경이 없고, "Haiku 로 내리지 마라" 류의 금지 문구는 새 룰과 같은 방향이라 그대로 둔다.

## 2. 영향 컴포넌트

| 파일 | 변경 내용 |
|---|---|
| `skills/writing-plans/SKILL.md` | Task Structure 템플릿 예시 `**Model**: haiku` → `sonnet` (L201). Task Model Hint 섹션 (L232~248): enum `haiku \| sonnet \| opus` → `sonnet \| opus`, 판정표의 haiku 행 sonnet 흡수, "순수 byte-copy 는 haiku 고정 유지" 문구 제거, backward compat 문단은 "필드 생략 시 sonnet" 만 서술 (옛 계획서의 haiku 값 격상은 실행 층 소관으로 위임 — 이 본문에서 haiku 단어 자체를 없앤다, §7 grep 기대값과 쌍) |
| `skills/auto-writing-plans/SKILL.md` | Model 힌트 자동 룰 (L31): "1-2 파일 mechanical → haiku" 를 sonnet 으로 교체 (writing-plans 와 페어 동기) |
| `skills/js-super-sub-driven/SKILL.md` | Model Selection 섹션 (L112) 조건부 룰 → 단일 룰 재작성, 복잡도 힌트 표 (L118~123) haiku 행 제거, dispatch 예시 (L125~130) · DAG 예시 (L91~92) · Per-wave W-2 (L153) · Stage 1 분기 (L163, L181) · dispatch log 예시 (L350~351) · 명시 모델 주입 룰 (L396) · 자동 판정 표 2곳 (L482, L524) 모두 sonnet 기준으로 동기 |
| `skills/js-super-sub-driven/implementer-prompt.md` | 헤더 주석 (L7): 기본 haiku → 기본 sonnet (plan `**Model**:` 값, haiku 격상 포함) |
| `skills/js-super-sub-driven/reorder-prompt.md` | L15 서술 "implementer (haiku, byte-copy mode)" → sonnet 으로 정정 |
| `skills/executing-plans/SKILL.md` | 룰 2 dispatch row (L329) + Anti-Pattern row (L381) 조건부 서술 → 단일 룰 서술. haiku 단어 없이 쓴다 — 하위 호환 격상 룰은 `js-super-sub-driven` 참조로 위임 (§7 grep 기대값과 쌍) |
| `skills/js-super-sub-driven/tests/G5-model-haiku/README.md` | 재목적화 — `**Model**: haiku` 잔존 계획서의 **sonnet 격상** 검증 시나리오로 Expected 재작성 (FR-3 하위 호환). 디렉토리명 유지 |
| `skills/js-super-sub-driven/tests/G6-no-model-default/README.md` | Expected: 필드 생략 시 sonnet 단일 기본 (조건부 분기 서술 제거) |
| `skills/js-super-sub-driven/tests/G8-reviewer-sonnet/README.md` | Scenario 의 implementer 모델 서술 sonnet 격상 반영 (reviewer sonnet 고정 검증은 그대로) |
| `skills/js-super-sub-driven/tests/H11-user-edit-reorder/README.md`, `tests/H15-natural-lang-verify/README.md` | implementer 모델 서술 haiku → sonnet |
| `skills/js-super-sub-driven/tests/README.md` | G5 · G8 행 (L21, L24) 설명 갱신 |
| `CLAUDE.md` | v1.1.14 결합 메모 (L148) "haiku/sonnet/opus 분기" → "sonnet/opus 분기", v2.9 결합 메모 항목 4 (L253) 조건부 룰 서술 갱신, **신규 결합 섹션** (본 피처) + 회귀 catch grep 추가 |

**무변경 (의도)**: `spec-reviewer-prompt.md` / `code-pretty` / `glossary` (Haiku 금지-언급은 새 룰과 정합), `scripts/` (haiku 참조 없음), `hooks/`, og-* 커맨드, `auto-executing-plans` (dispatch 룰을 js-super-sub-driven 에 위임 — 자체 haiku 언급 없음), `docs/features/` 과거 스펙 (날짜 박힌 기록), Claude Code 하네스 밖 대응 문서 (codex / cursor / gemini `references/*-tools.md` 류 — 요구사항 범위 밖), 6 manifest (버전 bump 는 main 전용).

## 3. 데이터 모델

N/A — 저장 데이터 변경 없음.

## 4. 외부 인터페이스

N/A — 외부 연동 없음.

## 5. 핵심 결정 + 대안 비교

### D1 — 실행 층: 조건부 분기 폐지, 단일 룰로

**채택**: implementer dispatch 모델 = 계획서 `**Model**:` 값. 값이 없으면 sonnet 기본값 적용 — 이때는 별도 격상 표기 없이 dispatch log 의 통상 판정 근거 (예: "Task 1 model: sonnet (기본값)") 만 찍는다. haiku 값이 남아 있으면 sonnet 으로 격상하고, 같은 dispatch log 의 판정 근거 자리에 격상 사실을 표기한다 (예: "Task 1 model: sonnet (haiku 격상)"). 즉 로그 줄 자체는 모든 task 에 동일하게 1줄이고, "격상" 표기는 haiku 잔존 케이스에만 붙는다.

- 대안 A (기각) — 조건부 분기를 유지하고 haiku 자리만 sonnet 치환: 두 분기의 결과가 사실상 같아져 분기가 죽은 코드가 된다. 읽는 세션마다 "왜 나눠져 있지" 를 다시 추론하는 비용만 남는다.
- 대안 B (기각) — 계획서 값을 무시하고 전부 sonnet 고정: opus 상위 선택지가 사라진다. 무거운 task 의 품질 손실. 요구사항 (하한선만 변경) 위반.
- 되돌리는 비용: 조건부 분기 문단을 복원하면 된다 — 이 문서의 §2 표가 복원 지점 목록.

### D2 — 작성 층: `**Model**:` enum 을 sonnet | opus 2값으로

**채택**: 판정표에서 haiku 행 ("1-2 파일 mechanical") 을 삭제하고 해당 신호를 sonnet 행으로 흡수. 필드 생략 시 기본 sonnet. 정식 (`writing-plans`) 과 자동 (`auto-writing-plans`) 페어 동기.

- 대안 (기각) — haiku 를 표에 남기고 "사용 금지" 주석: 금지된 값이 판정표에 남아 있으면 작성 세션이 실수로 배정할 여지가 생긴다. 값 자체를 없애는 쪽이 구조적으로 안전.

### D3 — 하위 호환: 옛 계획서의 haiku 는 실행 시점 격상

**채택**: 이미 저장된 계획서에 `**Model**: haiku` 가 있어도 문서를 고치라고 요구하지 않는다. 실행 층이 sonnet 으로 격상해 dispatch 하고 로그 한 줄로 알린다.

- 대안 (기각) — 실행 전에 계획서를 자동 수정: 계획서 수정은 change-history entry 를 요구하는 정본 변경이라, 실행 진입마다 문서를 건드리는 부작용이 생긴다. 격상은 dispatch 시점의 해석으로 충분.

### D4 — G5 fixture 재목적화, 디렉토리명 유지

**채택**: `tests/G5-model-haiku/` 는 "haiku 값 잔존 계획서 → sonnet 격상" 검증 시나리오로 Expected 를 재작성한다. 디렉토리명은 유지 (tests/README 인덱스 · 과거 스펙 참조가 이름을 가리킴 — 이름이 바뀌면 문서 밖이 깨진다).

- 대안 (기각) — fixture 삭제: FR-3 하위 호환 시나리오의 검증 커버가 사라진다.

### D5 — 금지-언급 파일 무변경

`spec-reviewer-prompt.md` 의 "Do NOT drop to haiku", `code-pretty` / `glossary` 의 Haiku 금지 문구는 새 룰과 같은 방향이라 그대로 둔다. 따라서 회귀 grep 은 "저장소 전체 haiku 0건" 이 아니라 **허용-언급만 0건** 으로 설계해야 한다 (§7).

## 6. 예비 위험

- **결합 회귀 (최대 위험)** — 작성 층과 실행 층 중 한쪽만 고치면 "계획서 모델 ↔ 실제 dispatch 모델 불일치" 가 재발한다 (CLAUDE.md v1.1.14 결합 메모에 기록된 패턴). → §2 표 전체를 한 묶음 (atomic) 으로 변경 + 신규 결합 메모로 고정.
- **격상 문구의 haiku 단어 잔존** — 하위 호환 룰을 서술하려면 haiku 라는 단어가 남는다. 전수 "haiku 0건" grep 은 쓸 수 없고, 파일별로 기대값을 세분화해야 한다 (§7).
- **eval 러너 파싱 계약** — CLAUDE.md 신규 결합 섹션의 bash 블록은 읽기 전용 명령 + `# expected:` 형식을 지켜야 러너가 룰로 수집한다. `evals/baseline.json` 기준선 반영은 main 몫 (기존 관례).
- **비용 · 대기 시간 증가** — byte-copy task 의 sonnet 격상. 요구사항에서 수용된 트레이드오프. STRICT BYTE-COPY 룰은 모델 무관 유지라 정확성 회귀는 없음.
- **워크트리 버전 bump 금지** — 6 manifest 는 건드리지 않는다 (main 전용 룰).

## 7. 테스트 전략

정적 검증 중심 (스킬 본문 룰 변경이라 실행 코드는 없음).

1. **회귀 catch grep (신규 결합 메모에 박을 것)** — 허용-언급 0건 설계:
   - `writing-plans` / `auto-writing-plans` / `executing-plans` 본문: haiku 언급 0
   - `js-super-sub-driven/SKILL.md` + `implementer-prompt.md`: `model: "haiku"` 패턴 0, haiku 언급은 격상 (하위 호환) 문구 1곳씩만
   - 격상 룰 존재: 격상 문구 grep ≥ 1
   - enum 2값 확인: `sonnet | opus` 표기 grep ≥ 1
   (정확한 grep 명령과 기대값은 구현계획서 task 로 확정)
2. **fixture 기대값 갱신** — G5 (격상 positive), G6 (생략 시 sonnet), G8 (implementer sonnet + reviewer sonnet 유지), H11 / H15 (서술 동기), tests/README 인덱스.
3. **eval 러너 실행** — `evals/run.py` 로 coupling 룰 수집이 깨지지 않았는지 (룰 수 감소 경고 없음) 확인.
4. **수동 dogfood** — 별도 세션에서 sub-driven 실행 시 dispatch log 에 sonnet 이 찍히는지 (G5 시나리오) 확인. 이번 릴리즈 범위에선 정적 검증까지.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 00:17] [개발방향-수정]
- **id**: CH-20260829-002
- **이유**: auto-tech-design 자동 설계 + verifying-spec 지적 3건 반영 (haiku 언급 위치 §2↔§7 정합화, 격상 로그 규칙 명확화, 하네스 밖 문서 무변경 목록 추가)
- **무엇이**: 서브에이전트-sonnet-기본-tech-design.md 전체 (§1~§7, D1~D5)
- **영향범위**: 다음 단계 구현계획서 (미작성) — 본 문서 §2 표가 task 분해 입력
- **연관 항목**: CH-20260829-001
