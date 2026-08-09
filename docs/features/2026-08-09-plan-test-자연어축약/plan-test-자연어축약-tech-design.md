# 개발방향: plan-test-자연어축약

> 입력: `plan-test-자연어축약-requirements.md` (Socratic, auto-flow). 비활성 토픽은 N/A 한 줄 처리.

## 1. 아키텍처 개요

구현계획서의 테스트 표현을 "코드 블록" 에서 "자연어 검증 설명" 으로 바꾸고, 실제 테스트 작성 책임을 실행 단계로 옮긴다. 세 층이 함께 움직인다:

1. **계획서 작성 층** (writing-plans / auto-writing-plans) — task 블록에서 테스트 코드 블록을 제거하고 전용 필드 `**검증**:` (자연어 1~2줄) 을 신설. 구현 코드의 `**원본**` / `**수정 후**` 블록 규약은 그대로.
2. **실행 층** (executing-plans inline / js-super-sub-driven subagent) — TDD 순서 유지: `**검증**:` 설명 기반으로 실패 테스트를 먼저 작성 → FAIL 확인 → 구현 (byte-copy) → PASS 확인. 하위 호환: task 에 테스트 코드 블록이 있으면 (기존 형식) 그대로 사용.
3. **dispatch 층** (js-super-sub-driven) — 신규 테스트 작성이 포함된 task 는 implementer 모델을 task 의 `**Model**:` 값 (최소 sonnet) 으로 dispatch. 순수 byte-copy task 는 haiku 유지.

검증 도구 층 (plan_byte_check.py / code-pretty / verifying-spec) 은 라벨 기반이라 변경 없음 — 테스트 코드 블록은 원래 라벨이 없어 검사 대상이 아니었다.

## 2. 영향 컴포넌트

| 파일 | 변경 | 내용 |
|---|---|---|
| `skills/writing-plans/SKILL.md` | 있음 (핵심) | Task Structure 템플릿 (L182-223) 재작성 — 테스트 코드 블록 제거 + `**검증**:` 필드 추가. No Placeholders 룰 (L338) 의 "(without actual test code)" 반전. Bite-Sized 단계 서술 (L127-132), Checklist TDD 사이클 문구 (L65), `**Model**:` 평가 룰 (L225-241) 에 sonnet floor 추가, same-file 묶음 step 구조 (L149-152), Self-Review 에 검증 필드 구체성 항목 추가 |
| `skills/auto-writing-plans/SKILL.md` | 있음 (mirror) | Step 2 본문 (L28-32) + same-file 묶음 mirror (L36, L39) 동기. 페어 atomic |
| `skills/js-super-sub-driven/implementer-prompt.md` | 있음 (리스크 최고) | L76 "Write tests — same byte-copy rule" → "구현 코드 = STRICT BYTE-COPY / 테스트 = `**검증**` 설명 기반 자체 작성 (TDD: 테스트 먼저)" 분리. 하위 호환 분기 (블록 있으면 byte-copy). DONE 정의 (L167) 는 tests pass 유지 |
| `skills/js-super-sub-driven/SKILL.md` | 있음 | "implementer 는 항상 haiku 고정" → 조건부 룰 (신규 테스트 포함 task 는 `**Model**:` 값으로 dispatch, 최소 sonnet). `**Files:** Test:` 경로 유지 명시 (dag_builder 충돌 감지 보존) |
| `skills/executing-plans/SKILL.md` | 있음 (경미) | dot 그래프 노드 + L283 "run X, expect Y" 전제 문구를 검증 필드 기반으로 조정. 하위 호환 분기 한 줄 |
| `PROMPT_KO.md` | 있음 | L293-324 writing-plans 한국어 mirror 동기 |
| `CLAUDE.md` | 있음 | v2.0.0 4-파일 결합 메모 + v2.0.1 same-file 메모 갱신 + 본 피처 결합 메모 신설 |
| `skills/js-super-sub-driven/tests/H12-same-file-merge/README.md` | 있음 | step 구조 기대값 동기 |
| `scripts/plan_byte_check.py` | 없음 | `**원본**` 라벨 블록만 정규식 매치 — 테스트 블록은 원래 대상 밖 |
| `skills/js-super-sub-driven/reorder-prompt.md` | 없음 | 테스트 언급 0건 |
| `skills/test-driven-development/SKILL.md` | 없음 | 구현 시점 룰만 — 계획서 언급 0건. 실행 단계 TDD 담보 역할은 오히려 강화 |
| `skills/code-pretty/SKILL.md` | 없음 | `**수정 후**` 라벨 블록만 대상 (라벨 없는 블록 명시 제외) |
| `skills/verifying-spec/SKILL.md` | 없음 | test-coverage 축은 저장소 실제 테스트 파일 Glob 검사 |
| `commands/write-plan.md`, `commands/auto-write-plan.md` | 없음 | "TDD plan" 표현만 — TDD 는 실행 단계에 유지되므로 그대로 |
| og-* 커맨드 / `spec-reviewer-prompt.md` / generating-html 계열 | 없음 | upstream 분리 보존 / 테스트 무관 / 라벨 무관 |
| 6 manifest | 없음 (이번 작업 범위 밖) | 버전 bump 는 dev 가 직접 |

## 3. 데이터 모델 — task 블록 스키마

### 신규 필드 `**검증**:`

```markdown
**검증**: <이 task 의 테스트가 무엇을 검증하는지 + 성공 기준> (자연어 1~2줄)
```

- 위치: task 헤더 필드 영역 (`**Files:**` / `**Model**:` 과 같은 레벨, `**Model**:` 바로 다음 줄)
- 필수: 코드 변경 task 는 모두. verification-only task 는 기대 결과 서술로 대체 가능
- 내용 요건: "무엇을" (대상 동작·경계 조건) + "기준" (성공/실패 판정). "테스트를 작성한다" 같은 동어반복 금지

### 유지되는 규약

- `**Files:**` 의 `Test: <경로>` 줄 유지 — dag_builder 의 wave 파일 충돌 감지 (`dag_builder.py:49-54`) 가 테스트 파일을 계속 커버
- `**원본**` / `**수정 후**` 라벨 블록 = 구현 코드 전용. 테스트 파일 내용은 코드 블록으로 싣지 않음 (신규·기존 수정 모두 자연어 서술)
- `**Model**:` 필드 유지 + sonnet floor 룰 추가 (§5 D2)

### task step 구조 (새 형식)

```
step 1: **검증** 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인 (실행 단계 수행)
step 2..N: 구현 Edit (**원본**/**수정 후** byte-copy)
step N+1: 테스트 실행 → PASS 확인
step N+2: commit
```

## 4. 외부 인터페이스

N/A — 신규 슬래시 커맨드·외부 API·마커 파일 없음. 기존 커맨드 표면 변화 없음.

## 5. 핵심 결정 + 대안 비교

### D1 — 계획서의 테스트 표현 형식 (채택: 전용 필드 `**검증**:`)

- (a) step 서술 안에 자연어 삽입 — 위치가 task 마다 흔들려 실행 층·리뷰어가 찾기 어려움. 탈락
- **(b) 전용 헤더 필드 `**검증**:` (채택)** — `**Files:**`/`**Model**:` 과 같은 파싱 가능한 고정 위치. 리뷰 시 일관, 실행 층이 deterministic 하게 참조
- (c) 형식 없는 자유 서술 — placeholder 화 위험 ("테스트 작성" 한 줄로 퇴화). 탈락

### D2 — subagent 모드 테스트 작성 주체·모델 (채택: 조건부 Model 승격, 구현 byte-copy 는 불변)

- (a) haiku implementer 가 테스트도 창작 — 자연어 설명만으로 haiku 가 테스트를 쓰는 건 v2.0.0 이 제거한 transcription 품질 문제의 재도입. 탈락
- (b) 테스트 작성 전용 sonnet stage 분리 (test-writer → implementer 2회 dispatch) — 품질은 좋으나 W-2 sequence 재설계 + dispatch 2배 비용. 이번 범위에 과함. 탈락
- **(c) 조건부 Model 승격 (채택)** — 신규 테스트 작성이 포함된 task (판정: `**검증**:` 필드 + `Files:` 의 `Test:` 경로 존재) 는 implementer 를 task 의 `**Model**:` 값 (최소 sonnet) 으로 dispatch. 순수 byte-copy task 는 haiku 유지. writing-plans 의 Model 평가 룰에 "신규 테스트 포함 → 최소 sonnet" floor 를 추가해 `**Model**:` ↔ dispatch 결합 (v1.1.14+) 을 복원·유지. STRICT BYTE-COPY 룰은 모델과 무관하게 구현 코드 블록에 그대로 적용

### D3 — 하위 호환 분기 (채택: task 단위 형식 감지)

- **(a) task 단위 분기 (채택)** — task 에 테스트 코드 블록이 있으면 기존 룰 (byte-copy 포함) 그대로, 없으면 `**검증**:` 기반 작성. 기존 계획서 실행 100% 보존, 혼재 plan 도 task 단위라 안전 (요구사항 결정 3)
- (b) 새 형식 전용 — 기존 문서 실행 깨짐. 사용자가 명시 탈락시킴

### D4 — same-file 묶음 룰 step 재서술 (채택: "통합 test 작성" → "검증 설명 기반 통합 테스트 작성 (실행 단계)")

3 조건 AND (같은 파일 / 테스트 경계 없음 / mechanical) 판정 룰 자체는 불변. step 1 의 표현만 코드 블록 전제 제거. 두 skill 페어 + H12 fixture 동기 (v2.0.1+ 결합 메모).

### D5 — 동기화 범위 (채택: 8 파일 atomic + 결합 메모 갱신)

§2 의 "있음" 8 파일을 한 배치로 처리. v2.0.0 4-파일 결합 중 실제 변경은 2개 (implementer-prompt, sub-driven SKILL.md) 지만 결합 메모는 4-파일 룰이므로 CLAUDE.md 갱신에 반영. manifest bump 는 범위 밖 (dev 직접).

## 6. 예비 위험

| 위험 | 완화 |
|---|---|
| sonnet implementer 가 byte-copy 룰을 어기고 구현 코드를 "개선" (drift 회귀) | implementer-prompt 의 STRICT BYTE-COPY 룰을 모델 무관 문구로 강화 + 기존 BLOCKED → reorder 경로 유지 |
| `**검증**:` 필드가 모호하게 작성돼 실행 단계 테스트 품질 저하 | writing-plans Self-Review 에 "검증 필드가 무엇을+기준을 담는가" 항목 추가. 동어반복 금지 룰 명문화 |
| `Test:` 경로 누락 시 wave 병렬에서 테스트 파일 충돌 감지 손실 | writing-plans task 템플릿에 `Test:` 경로 필수 유지 명시 (D1 데이터 모델) |
| 테스트 포함 task 의 sonnet dispatch 로 비용 증가 | 테스트 없는 task 는 haiku 유지 — 증가분은 테스트 품질 확보 비용으로 수용 |
| 페어 skill (writing-plans ↔ auto-writing-plans) 한쪽만 수정 회귀 | 기존 v2.0.1+ 결합 메모 패턴대로 grep 회귀 catch 추가 + atomic 커밋 |
| implementer 가 기존 형식 (테스트 코드 블록) task 에서 새 룰 적용 혼동 | 하위 호환 분기를 implementer-prompt 에 명시 (블록 존재 = 기존 룰 우선) |

## 7. 테스트 전략

1. **fixture 갱신** — `skills/js-super-sub-driven/tests/H12-same-file-merge/README.md` 의 step 구조 기대값을 새 형식으로 동기
2. **신규 fixture 1건** — 새 형식 plan 샘플 (검증 필드 + 코드 블록 없음) 과 기존 형식 샘플 (테스트 코드 블록 포함) 을 나란히 두고, implementer 분기 (자체 작성 vs byte-copy) + dispatch 모델 판정 (sonnet vs haiku) 발화를 검증하는 시나리오 README
3. **회귀 catch grep** —
   - `grep -c "검증 필드" skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md` → 각 1 이상 (페어 동기)
   - `grep -n "without actual test code" skills/writing-plans/SKILL.md` → 0 (옛 룰 제거 확인)
   - `grep -c "Test:" skills/writing-plans/SKILL.md` → 1 이상 (경로 유지)
   - `grep -n "same byte-copy rule" skills/js-super-sub-driven/implementer-prompt.md` → 0 (테스트 byte-copy 룰 제거 확인)
4. **dogfood** — 본 피처의 구현계획서 자체를 새 형식 (검증 필드, 테스트 코드 블록 없음) 으로 작성해 1차 검증

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-09 21:20] [개발방향-수정]
- **id**: CH-20260809-002
- **이유**: 신규 피처 tech-design (auto-flow) — 요구사항 결정 1~3 을 설계로 구체화
- **무엇이**: plan-test-자연어축약-tech-design.md 전체 (아키텍처 개요 / 영향 컴포넌트 / task 블록 스키마 / D1~D5 / 예비 위험 / 테스트 전략)
- **영향범위**: verifying-spec 4축 통과 (gap 0, conflict 0). 구현 단계에서 G5/G6 fixture 기대값 점검 필요
- **연관 항목**: CH-20260809-001
