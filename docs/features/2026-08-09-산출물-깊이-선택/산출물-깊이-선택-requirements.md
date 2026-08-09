# 요구사항: 산출물 깊이 선택

> **모드**: Socratic (자유 형식) — auto-brainstorming. 다음 단계의 `tech-design` 가 본 문서를 자유 형식 산문으로 읽습니다 (PRD 6 섹션 ID 강제 X).

## 배경

js-super 정식 플로우 (brainstorming → tech-design → writing-plans) 는 항상 3개 문서 (requirements / tech-design / implementation-plan) 를 만들고, auto-flow 체인도 4단계 끝까지 자동으로 달린다. 그러나 작업 성격에 따라 구현계획서가 불필요한 피처 (설계 논의가 목적인 작업, 문서 산출 자체가 결과물인 작업) 도 같은 깊이를 강제당한다.

이 기능은 피처 단위로 문서를 어디까지 만들지 선택할 수 있게 한다:

- **2개** = 테크디자인까지 (requirements + tech-design)
- **3개** = 구현계획서까지 (requirements + tech-design + implementation-plan) — 기존 동작

## 핵심 결정

1. **선택 시점 = tech-design 승인 직후** (사용자 결정 — 옵션 (c)). 실제 분기 지점 (tech-design → writing-plans 전환) 과 일치하고, 기존에 살아 있는 "구현계획서로 진행? 예/아니오" 게이트를 확장하는 방식이라 추가 팝업이 0 이다. 문서를 다 본 상태라 가장 정보가 많은 시점이기도 하다.
2. **"1개 (requirements 만)" 정식 선택지는 넣지 않는다.** brainstorming → tech-design 전환 안내에서 "stop" 을 입력하면 이미 requirements 만 남기고 멈출 수 있어 자연 커버된다. 정식 선택지로 승격하면 게이트 복잡도만 늘어난다. (사용자 (c) 선택에 포함된 제안 수용.)
3. **접근안 비교 (자동 선택 근거)**:
   - **A. 무상태 게이트 확장** — 게이트에 선택지만 추가하고 아무 흔적도 남기지 않음. 이후 세션에서 그 피처가 "2개로 확정된 트랙" 인지 "아직 plan 을 안 만든 3개 트랙" 인지 구분할 수 없어, 변경이력 라우팅·execute-plan 안내·change-propagation 이 판단 불가 → 기각.
   - **B. 깊이 표식 기록 (채택)** — "2개 확정" 선택 결과를 피처 폴더 안에 기계 판독 가능한 형태로 기록하고, 후속 skill 들이 이를 읽어 deterministic 하게 분기. 구체 저장 위치·형식은 tech-design 에서 결정.
   - **C. 진입 커맨드 플래그 (--depth)** — 선택 시점이 진입 시로 당겨져 사용자 결정 (c) 와 상충 → 이번 범위에서 제외 (후속 후보).
4. **auto-flow 는 묻지 않고 모델이 판단한다.** auto-* 의 AskUserQuestion 호출 금지 룰을 유지하며, 판단 시점은 auto-tech-design 의 전환 Step. 판단이 애매하면 **3개 (기존 동작 보존 default)**.

## 기능 요구

- **FR-1 정식 플로우 게이트 확장** — tech-design 승인 후 진행 게이트를 3지선다로 확장: ① "구현계획서까지 진행 (3개)" ② "여기서 종료 (2개 확정)" ③ "나중에 결정" (기존 "아니오 — 종료" 의미 보존 — 표식 없이 종료, /write-plan 나중에 직접). AskUserQuestion 도구 사용 (v2.3.5+ 룰 유지).
- **FR-2 깊이 표식** — "2개 확정" 선택 시 피처 폴더에 깊이 표식을 기록한다. 3개 진행·나중에 결정 시 표식 없음 = 기존 동작과 동일. 표식은 기계 판독 가능하고 사람이 읽어도 명확해야 한다.
- **FR-3 auto-flow 자동 판단** — auto-tech-design 의 전환 시점에 모델이 requirements + tech-design 내용을 근거로 판단한다: 코드 변경·구현 task 가 예상되는 피처면 3개 (auto-writing-plans 체인 계속), 순수 문서·설계·조사 성격이면 2개 (체인 종료 + 판단 근거 1줄 포함 종료 보고 + 깊이 표식 기록). 애매하면 3개. 사용자에게 묻지 않는다.
- **FR-4 체인 안전** — auto-tech-design 본문의 `js-super:auto-writing-plans` invoke 문자열은 조건부 문장으로 감싸서 보존한다 (CLAUDE.md 회귀 catch grep 계약 유지). 체인 스킬 4종의 frontmatter description 진입 제약 문구는 변경하지 않는다.
- **FR-5 2-doc 피처에서 /execute-plan 진입** — 기존 preflight 3중 가드가 plan 부재를 이미 막고 있으므로 신규 가드는 만들지 않는다. 안내 문구만 보강한다: 깊이 표식이 있으면 "이 피처는 2개 문서로 확정된 트랙입니다. 구현이 필요해졌다면 /write-plan 으로 승격하세요" 를 노출.
- **FR-6 2→3 승격 경로** — 2개 확정 피처에서 사용자가 /write-plan 을 명시 실행하면 승격을 허용한다. 승격 시 깊이 표식을 갱신하고 변경이력에 기록한다.
- **FR-7 변경이력 라우팅 (2-doc)** — 구현계획서 footer 로 가던 기록 (코드 수정·검증·릴리즈 entry) 은 2-doc 피처에서 tech-design footer 로 라우팅한다. change-propagation 의 "code-only 편집은 tech-design 을 수정하면 안 됨" acceptance 와의 충돌은 "변경이력 footer append 는 본문 수정이 아님" 예외 조항으로 해소한다. 세부 규칙은 tech-design 에서.
- **FR-8 change-propagation depth-aware** — impact matrix 가 깊이 표식을 읽어, 2-doc 피처의 cascade 대상에서 구현계획서를 제외한다.
- **FR-9 verifying-spec** — tech-design 직후 검증은 이미 requirements + tech-design 2개 조합만 전제하므로 그대로 동작한다. plan 부재로 사라지는 "FR → 결정 → task 추적" 축은 2-doc 트랙에서 tech-design 의 영향 컴포넌트·테스트 전략 축으로 대체 커버함을 명시한다.
- **FR-10 generating-html** — 문서 타입별 독립 발화 구조를 유지한다. 2-doc 피처면 자연히 `.html` 동봉본도 2개만 생성된다 (구조 변경 없음, 확인만).

## 우려/해결

| 우려 | 해결 |
|---|---|
| 2-doc 피처에서 코드·검증 변경이력의 기록 목적지 소실 (최대 구멍) | FR-7 라우팅 재정의 (tech-design footer) |
| change-propagation acceptance ("code 편집이 tech-design 수정 금지") 와 정면 충돌 | footer append 는 본문 수정이 아니라는 예외 조항 (FR-7) |
| CLAUDE.md 회귀 catch grep 계약 (auto 체인 invoke 문자열) 깨짐 | FR-4 조건부 문장으로 문자열 보존 + 구현 후 기존 grep 전수 실행 |
| auto 판단 오판 (2개로 끊었는데 구현이 필요해짐) | default 3개 (애매하면 계속) + FR-6 승격 경로 |
| writing-plans `**Model**:` 필드 ↔ js-super-sub-driven 결합 영향 | 3-doc 트랙에서만 발동하는 결합 — 2-doc 트랙은 writing-plans 자체를 타지 않으므로 영향 없음 (탐색으로 확인) |

## 범위 밖

- "1개 (requirements 만)" 정식 선택지 — 기존 전환 안내의 "stop" 으로 커버 (핵심 결정 2).
- `--depth` 진입 커맨드 플래그 — 후속 후보 (핵심 결정 3-C).
- og-* 커맨드 3종 — 분리된 흐름, 손대지 않음.
- 기존 피처 폴더 소급 마이그레이션 — 표식 없는 기존 폴더는 전부 3-doc 트랙으로 간주.
- fast-tasks / worktree 계열 skill — 무관.

## 수용 기준

1. 정식 플로우에서 tech-design 승인 게이트에 3지선다가 노출되고, "여기서 종료 (2개 확정)" 선택 시 writing-plans 가 호출되지 않으며 깊이 표식 + 종료 안내가 남는다.
2. auto-flow 에서 순수 문서 성격 피처 실행 시 auto-writing-plans 가 호출되지 않고 판단 근거가 보고된다. 구현 성격 피처는 기존과 동일하게 4단계 완주한다.
3. CLAUDE.md 의 기존 회귀 catch grep 이 전부 통과한다 (특히 `js-super:auto-writing-plans` invoke 문자열 grep).
4. 신규 회귀 catch grep + CLAUDE.md 결합 메모 갱신 + 6 manifest bump 가 같은 배치에 포함된다.
5. 구현 완료 후 강도 높은 최종 검증 패스를 별도로 실행한다 (사용자 요청) — 회귀 grep 전수 + verifying-spec + 주요 시나리오 (정식 2개 / 정식 3개 / auto 2개 / auto 3개 / 승격) 점검.

## 다음 단계

`tech-design` 단계에서 결정할 것: 깊이 표식의 저장 위치·형식, 게이트 확장의 정확한 문구·옵션 스키마, auto 판단 기준의 구체 문구, FR-7 라우팅 규칙 상세, 수정 대상 파일 목록과 atomic patch 범위, 신규 회귀 catch grep 설계.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-09 21:11] [요구사항-수정]
- **id**: CH-20260809-001
- **이유**: 신규 피처 auto-brainstorming 결과 (Socratic auto 모드, 사용자 결정: 선택 시점 = tech-design 승인 직후)
- **무엇이**: 산출물-깊이-선택-requirements.md 전체 (배경 / 핵심 결정 4건 / FR-1..FR-10 / 우려·해결 / 범위 밖 / 수용 기준)
- **영향범위**: 없음 (최초 생성)
