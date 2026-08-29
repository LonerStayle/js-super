---
name: auto-tech-design
description: auto-flow 2단계 — /auto-design-tech 커맨드 또는 앞 단계 auto-brainstorming 의 명시 invoke 로만 진입, 사용자 자유 요청에서 자동 선택 금지. requirements.md 읽기 + adaptive 7-topic 자동 판정 + design decision 자동 alternatives 비교 → recommendation 자동 선택 + verifying-spec 4축 보고서 transition 직전 노출 + auto-writing-plans 자동 invoke. AskUserQuestion 호출 X.
---

# Auto Designing Direction → <slug>-tech-design.md (auto)

## Checklist

- [ ] Step 1 — 입력 확인 + slug 추론
- [ ] Step 2 — adaptive 7-topic 자동 판정
- [ ] Step 3 — AI 자동 design decision (각 활성 토픽)
- [ ] Step 4 — 산출물 자동 작성 + 서술 수준 점검 (<slug>-tech-design.md)
- [ ] Step 5 — verifying-spec 자동 실행 (4축 보고서)
- [ ] Step 6 — change-history 자동 ([개발방향-수정] entry)
- [ ] Step 7 — 깊이 판정 + Transition notice + (3개 판정 시) auto-writing-plans invoke

## Process

### Step 1 — 입력 확인 + slug 추론

`<slug>-requirements.md` 존재 확인. 인자 누락 시 `scripts/auto_flow.find_latest_slug(Path("docs/features"))` 호출.

### Step 2 — adaptive 7-topic 자동 판정

`<slug>-requirements.md` 본문 분석. 항상 활성 4 (1,2,5,6) + 조건부 3 (3,4,7). 메인이 본문 컨텍스트로 판단 + 한 줄 announce:

```
ℹ️ 활성 토픽은 ... 이고, 비활성 토픽은 ... 입니다 (이유: ...). 자동 흐름이라 사용자 응답 없이 다음 단계로 넘어갑니다.
```

→ 사용자 catch 가능 위치이지만 응답 wait X.

### Step 3 — AI 자동 design decision

각 활성 토픽에 대해 메인이 2-3 alternatives + recommendation 1개 자동 선택 (D-T3). reasoning 은 §5 결정+대안 비교 에 logged. 비활성 토픽은 N/A 한 줄.

### Step 4 — 산출물 자동 작성 + 서술 수준 점검

`<slug>-tech-design.md` 7-section schema 따라 작성. RAW 본문.

작성 직후 메인이 서술 문단을 한 번 훑는다 — 남아 있는 코드 식별자마다 "그 이름이 바뀌면 문서 밖의 무언가가 깨지는가" 를 판정하고, 아니면 역할 서술로 교체한다. 표 / 코드 블록 / 도식은 대상 아님. 룰은 아래 "서술 수준 — 이름보다 역할" 섹션. 같은 자리에서 "산출물 문서 스타일" 네 가지와 "도면 형식" 도 훑는다 — 뒤를 먼저 읽어야 이해되는 문장 / 비유 / 산문 나열 / 새 항목 코드 / 절차 나열 흐름도. 사용자 응답 wait X (auto 모드).

### Step 5 — verifying-spec 자동 실행

`verifying-spec` skill invoke (메인 자체 수행 또는 skill 호출). 4축 보고서 생성. 결과는 다음 단계 transition notice 직전 노출.

### Step 6 — change-history 자동

`change-history` skill invoke → 첫 `[개발방향-수정]` entry. CH-id 자동.

### Step 7 — 깊이 판정 + Transition notice + (3개 판정 시) auto-writing-plans invoke

```
🔍 verifying-spec 결과:
   - A1 consistency: ✅
   - A2 ...
   - C1 impact: ⚠️ 영향 N 컴포넌트
   - C2 ...

ℹ️ /write-plan 단계로 자동 넘어갑니다. 멈추려면 "stop" 입력해주세요.
```

**깊이 판정 (산출물 깊이 선택)**: transition notice 출력 전에 메인이 requirements + tech-design 내용으로 판정한다 — 코드 변경·구현 task 가 예상되는 피처면 **3개** (아래 invoke 진행), 순수 문서·설계·조사 성격 (산출물이 설계 문서 자체) 이면 **2개**. 애매하면 3개 (기존 동작 보존). 사용자에게 묻지 않는다 (AskUserQuestion 호출 X).

- **3개 판정**: 위 transition notice 출력. `parse_interrupt` 매치 시 exit + `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` 안내. 매치 X → `js-super:auto-writing-plans` invoke.
- **2개 판정**: tech-design frontmatter 에 `depth: 2` + `depth_reason: <판단 근거 1줄>` 기록 + `change-history` [개발방향-수정] entry 후, `ℹ️ 이 피처는 2개 문서 트랙으로 자동 확정했습니다 (판단 근거: <1줄>). 구현이 필요해지면 /write-plan 으로 승격하세요.` 출력하고 체인 종료. auto-writing-plans 미호출. transition notice 미출력.

## --no-ask 플래그 (v2.5+) — 짧은 reference

본 skill 흐름은 `AskUserQuestion` 호출이 본문에 명시 X (clarifying Q 자체가 prose default). `--no-ask` 플래그 진입 시 추가 분기 없음 — 본문 그대로 도구 호출 0 보장.

단 내부 escalation (BLOCKED 자가복구 실패 / critical 7 재질문 / Other 모호 응답) 에서도 도구 호출 0 보장. 자세한 룰은 `skills/brainstorming/SKILL.md` 의 `### 예외 — \`--no-ask\` 플래그 (v2.5+)` 답습.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. |
| 일반 tech-design skill body 호출 | NEVER. self-contained mirror (D-T1). |
| transition notice 후 wait sleep | NEVER. |
| 서술 문단에 내부 변수나 아직 없는 함수 이름 박기 | 역할을 말로 풀어쓴다. 아래 "서술 수준" 섹션 참조. |
| §1 을 절차 나열 흐름도로만 채우기 | 도면으로 구역과 배치를 보인다. "도면 형식" 섹션 참조. |
| 산출물에 비유·새 항목 코드·산문 나열 | "산출물 문서 스타일" 네 가지 위반. |

## 산출물 문서 스타일

산출물 문서에만 적용된다 (이 skill 본문은 대상 아님).

- **위에서 아래로** — 용어는 처음 쓰는 자리에서 설명. 뒤를 먼저 읽어야 이해되는 문장 금지
- **간결한 자연어** — 한 문장에 하나. 비유 금지. 배경 반복·다짐 금지
- **표와 도면 우선** — 항목 셋 이상이면 표. 관계·배치는 도면. 산문은 배경과 판단 근거에만
- **항목 코드 금지** — 알파벳-숫자 코드를 새로 만들지 않는다. 결정·위험은 짧은 한국어 제목으로. 유일한 예외는 요구 항목 번호 (`요구 N`). 도면 안 번호 (①②③) 는 표기법이라 대상 아님

### 도면 형식

§1 의 그림은 도면이 기본이다. 절차 나열 흐름도로 구조 설명을 대신하지 않는다.

| 상황 | 형식 |
|---|---|
| 구역·레이어·배치 (기본) | 아스키 박스 도면 |
| 구성 요소 여섯 개 초과 또는 요소별 설명 필요 | 아스키 도면 + 번호 + 설명 표 |
| 관계·조건 분기가 본질 + 렌더링 환경 전제 가능 | mermaid |

이 skill 본문 안의 dot 흐름도는 에이전트 실행용이라 대상이 아니다. 전체 룰은 `skills/tech-design/SKILL.md` 의 같은 이름 섹션 답습.

## 서술 수준 — 이름보다 역할

`<slug>-tech-design.md` 의 **서술 문단** (줄글로 설명하는 부분) 에서는 코드 식별자를 기본적으로 쓰지 않는다. 이름을 쓰려는 자리마다 그 역할을 말로 풀어쓰고, **그 이름이 바뀌면 문서 밖의 무언가가 깨지는 경우**에만 실제 이름을 쓴다.

| 실제 이름을 쓴다 | 말로 풀어쓴다 |
|---|---|
| 사용자가 입력하는 명령어 | 내부 변수, 지역 변수 |
| 설정 파일의 키 이름 | 아직 없는 새 함수·클래스 이름 |
| 외부나 다른 팀이 호출하는 공개 함수 | 직접 지은 중간 계산값 |
| 저장소에 이미 있는 파일 경로 | 반복문 변수, 임시로 붙인 이름 |

적용 부위는 서술 문단뿐 — §2 영향 파일 표, 코드 블록, 도식은 그대로 둔다. 배경 설명은 `skills/tech-design/SKILL.md` 의 같은 이름 섹션 답습 (본 skill 은 판단에 필요한 부분만 보유).

## Related Skills

- `auto-writing-plans` — 다음 단계
- `verifying-spec` — 4축 보고서 생성
- `change-history` — 첫 entry append
- `scripts/auto_flow.parse_interrupt`, `find_latest_slug`
