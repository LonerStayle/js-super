# 기술설계: 구현계획서 코드 강제 + 위키형 분할

> **다음 단계 안내**: 이 문서는 기술 설계 (개발방향) 입니다. 다음 단계로 `/write-plan` (또는 auto-flow 의 자동 진행) 을 실행해 `<slug>-implementation-plan.md` 를 만드세요.

상위 문서: `구현계획서-코드강제-분할-requirements.md` (FR-1~FR-8)

## 1. 아키텍처 개요

이번 피처는 두 축이다.

**첫째 축 — 코드 강제화 (FR-1~FR-3).** 지금까지 "구현 코드는 블록으로 싣는다" 는 룰은 skill 본문의 지시문, 즉 LLM 자율 준수에 맡겨져 있었다. 기존 결정적 검사는 이미 존재하는 `**원본**` 블록의 byte-equal 만 보므로, 블록이 아예 없는 계획서는 검사망을 그대로 통과한다 (조사 결과 확인 — 정규식 0건 매치 → 빈 리스트 → pass). 해결은 **task 를 인지하는 신규 검사 모듈**이다. 계획서의 task 헤더와 파일 목록을 파싱해 "파일을 만들거나 고치는 task 인데 코드 블록이 없다" 를 위반으로 판정하고, 코드 블록 안의 축약 마커도 함께 탐지한다. 이 검사는 계획서 작성 게이트 (정식 + auto 양쪽) 에서 실행되고, 위반이 하나라도 있으면 저장·승인을 통과하지 못한다.

**둘째 축 — 위키형 분할 (FR-4~FR-6).** task 10개 이상인 계획서는 "인덱스 + 하위 문서" 구조로 쓴다. 인덱스는 기존 파일 이름 (`<slug>-implementation-plan.md`) 을 그대로 유지해 모든 기존 발견 경로 (frontmatter 의 commit_policy, 최신 계획서 자동 선택, Entry Guard) 가 무변경으로 동작하게 한다. task 상세 (TDD step + 코드 블록) 는 피처 폴더 아래 `plan/` 하위 폴더의 문서들로 옮긴다. 인덱스의 task 블록은 헤더 필드 (Files / Model / 검증 / 상세 링크) 만 남긴다 — 실행 단계의 DAG 분석이 인덱스만 읽고 wave 를 짤 수 있도록.

두 축은 하나의 검사 모듈에서 만난다: 신규 모듈이 "인덱스 → 하위 문서 집합" 해석을 단일 진입점으로 제공하고, 코드 강제화 검사·분할 구조 검사·기존 byte-equal 검사를 모두 이 집합 위에서 돌린다. 소비자 8곳이 각자 문서 집합을 해석하면 한 곳만 어긋나도 false-pass 가 나므로, 해석 로직은 한 군데에만 둔다.

## 2. 영향 컴포넌트

| 파일 | 변경 | 내용 |
|---|---|---|
| `scripts/plan_guard.py` | 신규 | 문서 집합 해석 + FR-1/2/4/5 검사 + byte-equal 전체 순회 wrapper |
| `scripts/tests/test_plan_guard.py` | 신규 | 신규 모듈 단위 테스트 |
| `scripts/plan_byte_check.py` | 무변경 | 기존 함수 그대로 — wrapper 가 문서별로 호출 (4파일 atomic 룰 회피) |
| `scripts/preflight.py` | 수정 (additive) | code_pretty_check / glossary_check 가 분할 구조에서 하위 문서까지 보고 판정 (기존 시그니처·exit code 룰 무변경) |
| `skills/writing-plans/SKILL.md` | 수정 | 분할 판정 단계 + 인덱스/하위 문서 스키마 + 검사 one-liner 교체 + Self-Review 항목 |
| `skills/auto-writing-plans/SKILL.md` | 수정 | 위 내용의 self-contained mirror (Step 2 분할 판정 + Step 4 작성 + Step 4.5 one-liner 교체) |
| `skills/executing-plans/SKILL.md` | 수정 | Plan Loading 에 분할 구조 분기 (인덱스 먼저, task 진행 시 해당 하위 문서 읽기) |
| `skills/js-super-sub-driven/SKILL.md` | 수정 | Plan Analysis 를 인덱스 기반으로 + W-2 dispatch 직전 wave 소속 하위 문서만 읽기 |
| `skills/js-super-sub-driven/implementer-prompt.md` 외 프롬프트 3종 | 무변경 | task 전문 붙여넣기 방식이라 분할 무관 (조사 결과) |
| `skills/verifying-spec/SKILL.md` + `clean-solo-prompt.md` + `clean-cross-prompt.md` | 수정 | "대상이 분할 구조면 링크된 하위 문서까지 읽는다" 룰 1곳씩 (TARGET_PATH 단수 규약 유지) |
| `skills/code-pretty/SKILL.md` | 수정 | 대상을 문서 집합으로 — `**수정 후**` 블록이 있는 문서마다 1 dispatch (병렬) |
| `skills/glossary/SKILL.md` | 수정 | 프롬프트에 "하위 문서 링크를 따라가 읽는다" 안내 (dispatch 는 1개 유지) |
| `skills/change-history/SKILL.md` | 수정 | 하위 문서는 변경이력 footer 를 갖지 않음 (인덱스로 단일화) 1줄 |
| `commands/write-plan.md` / `execute-plan.md` / `auto-write-plan.md` / `auto-execute-plan.md` / `pretty-md.md` | 수정 | 산출물·경로 안내 문구에 분할 구조 반영 |
| `CLAUDE.md` | 수정 | 결합 메모 신설 (회귀 catch grep 포함) |
| fixture (`skills/js-super-sub-driven/tests/H20-plan-split/`) | 신규 | 분할 계획서 실행 시나리오 (H19까지 사용 중 — H20 확정) |

## 3. 문서 스키마 (데이터 모델)

### 3.1 단일 문서 (task 10개 미만 — 기존과 동일)

지금 형식 그대로. 이번 피처로 바뀌는 것 없음.

### 3.2 분할 구조 (task 10개 이상, 또는 미만이어도 재량 분할)

```
docs/features/<date>-<slug>/
├── <slug>-implementation-plan.md     ← 인덱스 (이름 무변경)
└── plan/
    ├── tasks-01-03.md                ← task 1~3 상세
    ├── tasks-04-06.md
    └── tasks-07.md                   ← 단일 task 도 허용
```

**하위 문서 이름 규약**: `plan/tasks-NN.md` 또는 `plan/tasks-NN-MM.md` (2자리 zero-pad, 연속 범위). task 번호는 문서를 가로질러 전역 연번 (1..N) 이고, 연관 task 가 인접 번호가 되도록 계획 단계에서 정렬한다. 이 이름은 기존 계획서 파일명 정규식 (`.*-implementation-plan\.md$`) 에 일부러 **매치되지 않게** 지어서, "가장 최근 계획서 자동 선택" 류 glob 이 하위 문서를 오선택하는 사고를 원천 차단한다.

**인덱스 (`<slug>-implementation-plan.md`)**: frontmatter (commit_policy) / 개요 / DAG·wave 구조 / `## 1. 단계별 작업` (아래 형식) / `## 2. 위험 코드 지점` / `## 3. 롤백 전략` / `## 변경이력` footer. 인덱스의 task 블록은 헤더 필드만 갖는다:

```markdown
### Task 4: 결제 검증 helper

**상세**: plan/tasks-04-06.md
**Files:**
- Modify: `src/pay/verify.py:40-88`
- Test: `tests/pay/test_verify.py`
**Model**: sonnet
**검증**: <자연어 1~2줄 — 기존 v2.9+ 룰 그대로>
```

step 목록과 코드 블록은 인덱스에 두지 않는다.

**하위 문서 (`plan/tasks-NN-MM.md`)**: 담당 범위의 task 블록 전문 — 인덱스와 동일한 헤더 필드 + TDD step 목록 + `**원본**`/`**수정 후**` 코드 블록. 문서당 task 최대 3개 (FR-5, 결정적 상한). **변경이력 footer 없음** — 계획서의 변경이력은 인덱스 한 곳으로 단일화한다 (용어집의 footer 예외와 같은 계열).

**중복 필드의 정합성**: Files / Model / 검증 필드가 인덱스와 하위 문서 양쪽에 존재한다. 신규 검사 모듈이 두 쪽을 파싱해 불일치를 위반으로 판정한다 (수동 desync 차단).

### 3.3 검사 모듈의 판정 규칙

신규 모듈 (`scripts/plan_guard.py`) 의 검사 항목:

| # | 검사 | 위반 조건 |
|---|---|---|
| G1 (FR-1) | 코드 블록 존재 | Create/Modify 파일이 있는 task 에 대응 코드 블록 없음 (Modify → `**원본**`+`**수정 후**` 페어, Create → `**수정 후**` + `(new file: ...)`) |
| G2 (FR-2) | 축약 마커 | 코드 블록 안 라인이 축약 마커 패턴에 매치 — 단, 그 라인이 같은 task 의 `**원본**` 블록에 동일하게 존재하면 면제 (기존 코드를 그대로 들고 온 것) |
| G3 (FR-4) | 분할 강제 | task 10개 이상인데 단일 문서 |
| G4 (FR-5) | 상한 | 하위 문서 하나에 task 4개 이상 |
| G5 | 구조 무결성 | 인덱스 링크 ↔ `plan/` 실제 파일 불일치 (끊긴 링크 / 고아 문서), task 전역 연번의 누락·중복, 인덱스-하위 문서 헤더 필드 불일치 |
| G6 | byte-equal | 기존 검사를 문서 집합 전체에 순회 적용 (인덱스만 검사해 통과하는 false-pass 차단) |

**축약 마커 패턴 (고정 목록, 모듈 상수)**: 주석 형태 (`#`, `//`, `/* */`, `<!-- -->`, `--`, `;`) 뒤에 생략·중략·이하 동일·기존 코드 유지·나머지 동일·동일 패턴 / omitted / unchanged / rest of / existing code 류가 오는 라인, 그리고 `... 생략` / `(중략)` 형태. 맨몸 `...` 한 줄은 매치하지 않는다 — Python 의 Ellipsis stub 등 정상 코드와 충돌하기 때문. G2 의 원본-면제 규칙 덕에 실제 파일에 원래 있던 표현은 걸리지 않는다.

**재량 방향 (FR-6)**: 검사는 "10개 이상 + 단일 문서" 만 막는다. 10개 미만의 분할은 허용 (검사 없음) — 재량이 분할 방향으로만 열려 있는 구조.

## 4. 외부 인터페이스

N/A — 외부 API·서비스 연동 없음. 모든 변경은 저장소 안 skill 본문·스크립트·문서 규약이다.

## 5. 핵심 결정 + 대안 비교

**결정 1 — 검사를 신규 모듈로 분리 (기존 byte-check 무변경).**
- 대안 A (기존 `plan_byte_check.py` 확장): 그 파일은 implementer-prompt / reorder-prompt / sub-driven SKILL 과 4파일 atomic 변경 룰로 묶여 있어, 확장하면 그 번들 전체 재검증이 필요하다. 또한 현 파서는 task 헤더를 아예 읽지 않아 "task 인데 블록 없음" 판정 자체가 불가능 — 사실상 재작성이 된다. → 기각.
- 채택 B (신규 모듈 + wrapper): 기존 함수는 문서별 호출로 재사용만 하고, task 인지 파싱·마커 탐지·구조 검사는 새 모듈에 둔다. atomic 번들 비접촉, 하위 호환 자동 보장.
- 깨지는 조건: 기존 byte-equal 검사의 반환 형식이 바뀌면 wrapper 도 같이 고쳐야 한다 (결합 메모에 명시).

**결정 2 — 인덱스 파일 이름 유지 + 하위 문서는 `plan/` 폴더에 비매치 이름.**
- 대안 A (하위 문서도 `-implementation-plan` 접미사): 기존 파일명 정규식에 매치돼 preflight 는 편해지지만, "최신 계획서 자동 선택" 이 하위 문서를 계획서 본체로 오선택하는 위험이 생긴다. → 기각.
- 채택 B (`plan/tasks-NN-MM.md`): 발견 경로 전부 무변경. preflight 쪽은 additive 로 하위 문서를 인지시킨다.
- 깨지는 조건: 없음에 가깝다 — 폴더 안 이름 충돌은 zero-pad 연번이라 결정적.

**결정 3 — 인덱스에 헤더 필드 유지 (DAG 입력을 인덱스로 충족).**
- 대안 A (인덱스는 링크만, 메타데이터도 하위 문서에만): 실행 단계의 DAG 분석이 결국 하위 문서 전부를 읽어야 해서 분할의 컨텍스트 절감이 사라진다. → 기각.
- 채택 B (인덱스 = 헤더 필드 + 링크, 하위 문서 = 전문): DAG 분석은 인덱스만, dispatch 는 wave 소속 하위 문서만 읽는다. 중복 필드는 검사 모듈 G5 가 정합성 보장.
- 깨지는 조건: task 헤더 필드가 앞으로 크게 늘면 중복 유지 비용이 커진다 — 그때는 인덱스 쪽을 표 형식으로 전환 검토.

**결정 4 — 강제화 게이트는 작성 단계 전용, 실행 단계는 읽기 호환만.**
- 대안 A (실행 진입 시에도 강제 검사): 기존 계획서 (소급 비대상) 가 전부 차단돼 하위 호환이 깨진다. → 기각.
- 채택 B: 정식 `/write-plan` 의 저장 게이트와 auto-flow 의 재시도 루프에서만 차단. 실행·검증 소비자는 양쪽 레이아웃을 읽기만 한다 (FR-8).

**결정 5 — verifying-spec 은 TARGET_PATH 단수 유지 + "링크 따라 읽기" 룰 추가.**
- 대안 A (검증자에게 경로 리스트 주입): 단독 검증자의 "경로 1개만 주입" 하드 룰과 충돌 — 무맥락 검증자 피처의 구조 보장 (읽기 순서를 구조로 강제) 을 흔든다. → 기각.
- 채택 B: 대상은 인덱스 경로 1개 그대로. 프롬프트에 "대상 문서가 분할 구조면 링크된 `plan/` 하위 문서도 대상의 일부로 읽는다" 를 추가한다. 하위 문서는 upstream 이 아니라 **대상의 일부**이므로 단독/대조 검증자의 순서 보장과 충돌하지 않는다.

**결정 6 — code-pretty 는 문서별 병렬 dispatch, glossary 는 단일 dispatch 유지.**
- code-pretty 는 대상 파일을 통째로 다시 쓰는 방식이라 문서 1개당 보조 에이전트 1개가 자연스럽다 (`**수정 후**` 블록이 있는 문서만). 서로 다른 파일이라 충돌 없음, 기존 "같은 메시지 병렬" 패턴 그대로.
- glossary 는 읽기 전용 + 산출물 1개 (`<slug>-glossary.md`) 라 분산할 이유가 없다 — 프롬프트에 하위 문서 읽기 안내만 추가.

## 6. 위험

- **인덱스만 검사하는 false-pass 재발** — 가장 큰 회귀. 문서 집합 해석을 신규 모듈 단일 진입점으로 강제하고, "인덱스에 코드 블록 0건 + 하위 문서 존재" 시나리오를 단위 테스트로 고정한다.
- **축약 마커 오탐** — 정상 코드가 마커 패턴에 걸려 게이트가 막히는 경우. 완화: 패턴을 주석 형태로 좁게 한정 + 원본-면제 규칙 + 맨몸 `...` 비매치. 그래도 오탐이 나면 계획서 쪽 표현을 고치는 방향으로 안내 (검사 우회 옵션은 두지 않는다 — FR-3).
- **인덱스 ↔ 하위 문서 desync** — 중복 헤더 필드가 수동 수정으로 어긋나는 경우. G5 정합성 검사로 게이트에서 잡는다.
- **preflight 시그니처 결합** — code_pretty_check / glossary_check 내부 판정을 넓히되 시그니처·exit code 룰은 유지 (CLAUDE.md 의 3-skill one-liner 동기 룰 발동 회피). 어길 경우 3 skill bash one-liner 동시 수정 필요.
- **sub-driven SKILL 수정이 4파일 atomic 번들과 겹침** — 이번 수정은 byte-copy 룰 자체가 아니라 "task 텍스트를 어디서 읽는가" 만 바꾼다. 번들의 회귀 grep (BLOCKED → reorder 분기 등) 을 구현 후 재실행해 무손상 확인.
- **executing-plans 인라인 모드의 컨텍스트** — 인덱스 + 필요 하위 문서 lazy 읽기로 절감이 목적이지만, LLM 이 습관적으로 전부 읽으면 이득이 사라진다. skill 본문에 "하위 문서는 해당 task 진행 시점에 읽는다" 를 명시.

## 7. 테스트 전략

- **단위 테스트** (`scripts/tests/test_plan_guard.py`, 기존 관례 — 평평한 `def test_*` + `tmp_path` + repo 루트 pytest):
  - 문서 집합 해석: 단일 문서 / 분할 / 끊긴 링크 / 고아 하위 문서 / 이름 규약 위반
  - G1: Modify task 블록 없음 → 위반, Create + `**수정 후**` → 통과
  - G2: 마커 탐지 + 원본-면제 + 맨몸 `...` 비매치
  - G3/G4: 10개 단일 문서 → 위반, 9개 단일 → 통과, 하위 문서 4 task → 위반
  - G5: 헤더 필드 불일치 / 연번 누락·중복
  - G6: 하위 문서의 byte-mismatch 가 인덱스 경로 진입으로 검출되는지 (false-pass 회귀 고정)
  - `**원본**` 리터럴은 기존 테스트의 우회 패턴 (`"**"+"원본"+"**"` 조합) 답습
- **fixture**: `skills/js-super-sub-driven/tests/H20-plan-split/README.md` — 분할 계획서를 sub-driven 으로 실행하는 시나리오 (인덱스 DAG 분석 → wave 별 하위 문서 읽기 → dispatch), positive + negative (10개 이상 단일 문서 차단).
- **회귀 catch grep**: CLAUDE.md 결합 메모에 bash 블록으로 박아 evals 러너가 수집 (스킬 검증 환경 파싱 계약 준수 — `# expected:` 주석 형식).

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 09:25] [개발방향-수정]
- **id**: CH-20260829-002
- **이유**: 요구사항 FR-1~FR-8 에 대한 기술 설계 최초 작성 (auto-flow) — 신규 검사 모듈 + 인덱스/하위 문서 레이아웃 + 소비자 8곳 하위 호환 방침 확정
- **무엇이**: 구현계획서-코드강제-분할-tech-design.md 전체 (§1 아키텍처 / §2 영향 컴포넌트 21항목 / §3 문서 스키마 + 검사 판정 규칙 G1~G6 / §5 핵심 결정 6건 / §6 위험 6건 / §7 테스트 전략)
- **영향범위**: verifying-spec A축 gap 0 · conflict 0. C축 — 신규 2 파일, 수정 대상 skill 8 · commands 5 · CLAUDE.md 1, 프롬프트 3종 무변경. 무맥락 검증자 2개는 사용량 크레딧 소진으로 실패(미수행) — 다음 검증 시점에 재확인 필요. fixture 번호 H20 확정 (H19까지 사용 중)
- **연관 항목**: CH-20260829-001
