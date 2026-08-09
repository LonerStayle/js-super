# 개발방향: 산출물 깊이 선택

> **다음 단계 안내**: 이 문서는 기술 설계서입니다 (아키텍처 / 컴포넌트 / 데이터 / 인터페이스 / 결정 / 위험 / 테스트 전략). `산출물-깊이-선택-requirements.md` 를 기반으로 작성되고, 다음 단계 `산출물-깊이-선택-implementation-plan.md` (단계별 계획) 의 입력이 됩니다. 단계별 구현 task 는 여기 박지 마세요 — 그건 다음 산출물 (plan) 에 들어갑니다.

## 1. 아키텍처 개요

핵심은 **깊이 표식 (depth marker) 하나를 single source of truth 로 두고, 두 개의 결정 표면과 네 개의 소비자가 그것을 읽는 구조**다. 새 스크립트나 새 skill 은 만들지 않는다 — 기존 skill 본문의 분기 지점 확장 + `scripts/preflight.py` 의 additive 함수 1개가 전부다.

### 결정 표면 (표식을 쓰는 곳, 2곳)

1. **정식 플로우 — tech-design 승인 직후 게이트 확장 (FR-1)**: 기존 Gate #12 (proceed-to-writing-plans, 현재 "예 — 진행 / 아니오 — 종료" 2지선다) 를 3지선다로 확장한다:
   - "구현계획서까지 진행 (3개)" → 기존 yes 동작 그대로 (writing-plans invoke). 표식 없음.
   - "여기서 종료 (2개 확정)" → tech-design frontmatter 에 `depth: 2` 기록 + [개발방향-수정] 변경이력 entry + 종료 안내. writing-plans 미호출.
   - "나중에 결정" → 기존 no 동작 그대로 (표식 없이 종료, "/write-plan 은 나중에" 안내).
2. **auto-flow — auto-tech-design Step 7 조건부화 (FR-3)**: transition notice 직전에 메인이 requirements + tech-design 내용으로 깊이를 판정한다. 3개 판정이면 기존 그대로 `js-super:auto-writing-plans` invoke (문자열 보존 — FR-4), 2개 판정이면 `depth: 2` 기록 + 판단 근거 1줄 포함 종료 보고 + 체인 종료. 사용자에게 묻지 않는다.

### 소비자 (표식을 읽는 곳, 4곳)

| 소비자 | 읽는 방식 | 동작 |
|---|---|---|
| `change-history` 라우팅 (FR-7) | skill 본문 룰 (LLM) | `depth: 2` 피처의 [코드-수정]·[검증]·[릴리즈] entry 를 tech-design footer 로 라우팅 |
| `change-propagation` matrix (FR-8) | skill 본문 룰 (LLM) | `depth: 2` 피처의 cascade 대상에서 구현계획서 제외 |
| `/execute-plan` 진입 안내 (FR-5) | `scripts/preflight.py` (deterministic) | plan 부재 fail 시 `depth: 2` 감지하면 human_reason 에 승격 안내 추가 |
| `/write-plan` 승격 (FR-6) | skill 본문 룰 (LLM) | `depth: 2` 감지 시 승격 안내 + `depth: 3` 갱신 + 변경이력 entry 후 정상 진행 |

### 건드리지 않는 곳

- `generating-html` — 문서 타입별 독립 발화라 구조 변경 없음 (FR-10).
- `executing-plans` / `js-super-sub-driven` skill 본문 — 이미 preflight 의 `human_reason` 을 그대로 노출하므로 본문 변경 0 (안내 보강은 preflight.py 안에서).
- og-* 커맨드 3종, fast-tasks, worktree 계열, verifying-spec 의 검사 로직 (2-doc 대체 커버 명시 1줄만 추가).

## 2. 영향 받는 컴포넌트/파일

| 대상 | 변경 내용 | 관련 FR |
|---|---|---|
| `skills/tech-design/SKILL.md` | Gate #12 3지선다 확장 (본문 + Process Flow 요약 2곳) + Checklist 9번 재기술 + dot 다이어그램 분기 + 산출물 blockquote 조건부 문구 + Related Skills | FR-1, FR-2 |
| `commands/tech-design.md` | "다음 단계는 /write-plan" 문구 조건부화 | FR-1 |
| `skills/auto-tech-design/SKILL.md` | Step 7 깊이 판정 분기 + Checklist 재기술 + 판정 기준 명문화 | FR-3, FR-4 |
| `commands/auto-brainstorm.md`, `commands/auto-tech-design.md`, `commands/auto-write-plan.md` | "다음 단계는 자동으로 이어집니다" 문구에 조기 종료 가능성 병기 | FR-3 |
| `skills/change-history/SKILL.md` | When-to-Use 표 + Target Routing 에 depth-aware 룰 추가 | FR-7 |
| `skills/change-propagation/SKILL.md` | impact matrix depth-aware 분기 + Acceptance 4번 예외 조항 + Change Level 표 주석 | FR-7, FR-8 |
| `skills/verifying-spec/SKILL.md` | 2-doc 트랙 대체 커버 명시 (When to Invoke 표 주변 1-2줄) | FR-9 |
| `skills/writing-plans/SKILL.md` | HARD-GATE 직후 승격 clause (depth: 2 감지 → 안내 + 갱신 + entry) | FR-6 |
| `skills/auto-writing-plans/SKILL.md` | 동일 승격 clause (self-contained mirror 유지, 짧게) | FR-6 |
| `scripts/preflight.py` | `feature_depth()` 신규 함수 + `execute_plan_mode_check` / `subagent_task_entry_check` 의 plan-부재 human_reason 보강 | FR-2, FR-5 |
| `skills/brainstorming/SKILL.md` | Entry Router 라벨 "3-MD 풀 트랙" → "2~3 MD (깊이는 tech-design 승인 시 선택)" + "다음 두 산출물" blockquote 조건부 문구 | 표기 정합 |
| `CLAUDE.md` | 결합 메모 신규 섹션 + 신규 회귀 catch grep | 수용 기준 4 |
| 6 manifest | minor bump (구현 시점의 main 기준 차기 minor — 병합 시 확정) | 릴리즈 |

- 기존 회귀 grep 계약 유지 확인 대상: `js-super:auto-writing-plans` 문자열 (auto-tech-design 본문), auto-* 4종 description 진입 제약 문구, `--no-ask` 8 skill grep, Checklist 9 skill grep.
- `.gitignore` 변경 없음 (신규 산출물 파일 없음 — 표식은 기존 .md 의 frontmatter).

## 3. 데이터 모델/스키마 변경 (깊이 표식)

DB 는 없다. 표식은 `<slug>-tech-design.md` 맨 위 YAML frontmatter 로 정의한다.

```yaml
---
depth: 2
depth_reason: <1줄 — 정식 게이트: "사용자 선택" / auto: 모델 판단 근거>
---
```

- **판독 규칙 (엄격)**: `depth: 2` 일 때만 2-doc 트랙. 필드 부재 / `depth: 3` / 파싱 실패 = 전부 3-doc 트랙 (기존 동작). 기존 피처 폴더는 전부 frontmatter 가 없으므로 자동으로 3-doc 간주 — 소급 마이그레이션 불필요 (requirements 범위 밖 항목과 일치).
- **기록 시점**: 정식 게이트 "여기서 종료" 선택 시 / auto 판정 2개 시. "구현계획서까지 진행"·"나중에 결정" 은 기록하지 않는다 (표식 부재 = 기본 3-doc 이므로 쓸 필요 없음).
- **승격 (FR-6)**: `/write-plan` 진입 시 `depth: 2` 감지 → `depth: 3` 으로 갱신 (필드 유지 — "한때 2개 확정이었다가 승격됨" 이력이 남음) + `depth_reason` 을 승격 사유로 교체 + [개발방향-수정] entry.
- **선례**: implementation-plan frontmatter 의 `commit_policy: per-task` + `scripts/preflight.py` 의 `_FRONTMATTER_COMMIT_POLICY` 파서. 같은 파싱 방식 (정규식 기반, YAML 라이브러리 불필요) 을 `feature_depth()` 로 일반화한다.
- **`feature_depth(feature_dir: Path) -> int`**: 폴더 안 `*-tech-design.md` 의 frontmatter 를 읽어 2 또는 3 반환 (부재·실패 = 3). 신규 additive 함수 — 기존 함수 시그니처 무변경이라 4 skill caller bash one-liner 동기화 불필요 (CLAUDE.md preflight 결합 룰 위반 없음).

## 4. 외부 인터페이스

N/A — 외부 API·네트워크·서드파티 인터페이스 없음. 전부 플러그인 내부 skill 본문 / 커맨드 본문 / helper 함수 변경.

## 5. 핵심 결정 + 대안 비교

### D1. 깊이 표식 저장 위치 — tech-design frontmatter (채택)

| 대안 | 장점 | 단점 |
|---|---|---|
| **(채택) tech-design.md frontmatter `depth: 2`** | 문서 열면 바로 보임 (사람 가독) + `commit_policy` 파서 선례로 deterministic 판독 + 파일 추가 없음 | tech-design 스키마에 frontmatter 개념 신규 도입 |
| 피처 폴더 안 marker 파일 (`.js-super-depth.json`) | `test -f` 판별 최단순 (v2.7 `.js-super-skill.json` 선례) | 숨김 파일이라 사람이 못 봄 + 문서와 표식이 분리돼 drift 가능 |
| 변경이력 footer entry 로 표현 | 파일 변경 없음 | 기계 판독 불가 (LLM 해석 의존) — preflight deterministic 요구와 충돌 |

**근거**: 소비자 4곳 중 preflight 가 deterministic 판독을 요구하고, 사람도 문서만 열면 트랙을 알 수 있어야 한다. frontmatter 가 둘 다 만족하는 유일한 후보.

### D2. 게이트 스키마 — 3지선다, "나중에 결정" 유지 (채택)

2지선다 ("진행 / 2개 확정") 로 줄이면 기존 "아니오 — 종료" (미결 상태로 나가기) 의미가 사라진다. 미결 종료는 실사용에서 필요한 escape (지금 결정하기 싫은 경우) 라 유지한다. 옵션 순서는 기존 습관 보존을 위해 "진행" 을 첫 번째로 둔다.

### D3. auto 판정 기준 — "구현 단계 필요성" (채택)

판정 질문은 "이 피처는 코드/본문 변경 task 로 실행돼야 하는가":

- **3개 신호**: tech-design §2 에 수정 대상 파일이 있고 그 변경이 task 분해·실행을 요구 / requirements 에 실행·릴리즈 수용 기준 존재.
- **2개 신호**: 산출물이 설계 문서 자체 (아키텍처 검토, RFC, 조사 보고, 의사결정 기록) / §2 가 "수정 파일 없음" 또는 문서 산출물뿐.
- **default**: 애매하면 3개 (기존 동작 보존 — requirements 핵심 결정 4).

대안이었던 "파일 수 임계값" (예: 수정 파일 0개면 2) 은 기각 — js-super 처럼 .md 가 곧 코드인 저장소에서 오판 위험이 큼. 의미 기반 판정 + 안전 default 가 낫다.

### D4. 회귀 grep 계약 보존 — 조건부 문장으로 invoke 문자열 감싸기 (채택)

auto-tech-design Step 7 을 "깊이 판정 → 3개면 `js-super:auto-writing-plans` invoke / 2개면 종료 보고" 로 재기술하면 기존 grep (`grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md` ≥ 1) 이 그대로 통과한다. 문자열 삭제·치환 금지.

### D5. 변경이력 라우팅 충돌 해소 — "footer append 는 본문 수정이 아님" 예외 조항 (채택)

change-propagation Acceptance 4번 ("code-only 편집이 requirements/tech-design 을 수정하면 안 됨") 의 의도는 **본문 (설계 내용) 무단 변경 금지**다. `## 변경이력` footer append 는 감사 기록 추가일 뿐 설계 내용 변경이 아니므로, "본문(body) 수정 금지, footer append 는 예외" 로 문구를 정밀화한다. 이 예외는 `depth: 2` 피처에만 적용 — 3-doc 피처의 라우팅은 기존 그대로 (구현계획서 footer).

### D6. preflight 확장 방식 — 신규 함수 추가, 기존 시그니처 무변경 (채택)

`execute_plan_mode_check` / `subagent_task_entry_check` 는 이미 plan_path 를 받으므로 `plan_path.parent` 로 피처 폴더를 알 수 있다. plan 부재 fail 경로 안에서 `feature_depth()` 를 호출해 human_reason 만 보강한다: `"이 피처는 2개 문서로 확정된 트랙입니다. 구현이 필요해졌다면 /write-plan 으로 승격하세요."` 반환 형식·exit code 룰 무변경 → CLAUDE.md 의 "helper 시그니처 변경 시 4 skill 동기" 룰에 안 걸린다.

## 6. 위험/사이드이펙트 (preliminary)

| 위험 | 카테고리 | 완화 |
|---|---|---|
| 3-doc 피처에서 change-history 가 tech-design footer 로 오라우팅 | side-effect | 판독 규칙 엄격화 — `depth: 2` 명시일 때만 2-doc 분기 (D1, §3) |
| auto 체인 invoke 문자열 grep 계약 깨짐 | breaking (회귀) | D4 조건부 문장 방식 + 구현 후 기존 grep 전수 실행 |
| auto 오판으로 2개 종료 후 구현 필요해짐 | side-effect | default 3 + FR-6 승격 경로 + 판단 근거 1줄 보고로 사용자 catch 가능 |
| Gate #12 확장이 기존 대화 습관 ("예/아니오") 과 충돌 | breaking (UX) | AskUserQuestion enum 이라 자유 입력 파싱 없음 — 옵션 순서만 기존 보존 (D2) |
| frontmatter 도입이 다른 .md 파서 (docs_pretty_check 등) 와 충돌 | side-effect | docs_pretty_check 는 파일 존재·footer·파일명만 검사 — frontmatter 무관 (탐색 확인). 구현 시 fixture 로 재확인 |
| tech-design 승인 후 사용자가 frontmatter 를 수동 삭제 | race | 삭제 = 3-doc 복귀 (안전한 방향으로 fallback — 기존 동작) |

## 7. 테스트 전략

1. **신규 회귀 catch grep** (구현계획서에서 확정, CLAUDE.md 에 박음):
   - Gate 3지선다 존재: `grep -F "여기서 종료 (2개 확정)" skills/tech-design/SKILL.md` ≥ 1
   - auto 판정 분기 존재: `grep -F "깊이 판정" skills/auto-tech-design/SKILL.md` ≥ 1 + 기존 `js-super:auto-writing-plans` grep ≥ 1 유지
   - depth-aware 라우팅: `grep -F "depth: 2" skills/change-history/SKILL.md skills/change-propagation/SKILL.md skills/writing-plans/SKILL.md` 각 ≥ 1
   - preflight: `python3 -c "from scripts.preflight import feature_depth"` 성공
2. **preflight 단위 검사**: `feature_depth()` — frontmatter 있는 폴더 (2 반환) / 없는 폴더 (3 반환) / `depth: 3` (3 반환) 세 케이스를 python one-liner 로 검증.
3. **기존 회귀 grep 전수 실행**: CLAUDE.md 의 auto-* 4 description / `--no-ask` 8 skill / Checklist 9 skill / preflight 결합 grep 전부 재실행 → 전부 기존 기대값 유지.
4. **시나리오 fixture**: `skills/js-super-sub-driven/tests/` 패턴을 따라 신규 fixture 1건 (H14-depth-select — 현재 tests/ 최신이 H13 이라 다음 번호, 구현 시점 재확인) — 정식 2개 / 정식 3개 / auto 2개 / auto 3개 / 승격 5 시나리오의 기대 동작 README. `feature_depth()` 단위 테스트는 기존 `scripts/tests/test_preflight.py` 에 추가.
5. **최종 빡센 검증 패스** (requirements 수용 기준 5, 사용자 요청): 구현 완료 후 별도 검증 전용 패스 — 위 1~4 전부 + verifying-spec 재실행 + 수정 파일 전체 diff 리뷰.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-09 21:17] [개발방향-수정]
- **id**: CH-20260809-002
- **이유**: 신규 피처 auto-tech-design 결과 (adaptive 7-topic — 활성 1,2,3,5,6,7 / 비활성 4)
- **무엇이**: 산출물-깊이-선택-tech-design.md 전체 (아키텍처 / 영향 컴포넌트 21파일 / 깊이 표식 frontmatter 스키마 / 핵심 결정 D1~D6 / 위험 6건 / 테스트 전략 5항)
- **영향범위**: verifying-spec 4축 보고 — gap 0, conflict 0, 위험 후보 side-effect 2·breaking 2·race 1
- **연관 항목**: CH-20260809-001
