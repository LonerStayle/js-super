---
name: auto-writing-plans
description: auto-flow 3단계 — /auto-write-plan 커맨드 또는 앞 단계 auto-tech-design 의 명시 invoke 로만 진입, 사용자 자유 요청에서 자동 선택 금지. requirements + tech-design 읽기 + AI 자동 task 분해 (TDD bite-sized + Model hint 자동) + RISK 코드 지점 §2 자동 + verifying-spec 자동 + code-pretty 호출 X (D-T12 와 일관) + change-history 자동 + auto-executing-plans 자동 invoke. AskUserQuestion 호출 X.
user-invocable: false
---

# Auto Writing Plans → <slug>-implementation-plan.md (auto)

## Checklist

- [ ] Step 1 — 입력 확인 + slug 추론
- [ ] Step 2 — AI 자동 task 분해 (TDD bite-sized + Model hint 자동)
- [ ] Step 3 — §2 위험 코드 지점 자동 (R-N → file:line 매핑)
- [ ] Step 4 — 산출물 자동 작성 (<slug>-implementation-plan.md)
- [ ] Step 4.5 — plan_guard 자동 (3회 재시도)
- [ ] Step 5 — verifying-spec 자동 실행 (4축 보고서)
- [ ] Step 6 — change-history 자동 ([구현계획서-수정] entry)
- [ ] Step 7 — Transition notice + auto-executing-plans invoke

## Process

### Step 1 — 입력 확인 + slug 추론

`<slug>-requirements.md` + `<slug>-tech-design.md` 모두 존재 확인. 누락 시 `ℹ️ 입력이 누락됐습니다 (<누락 파일>). /auto-brainstorm 또는 /auto-design-tech 부터 시작해주세요.` 안내 후 종료.

**2-doc → 3-doc 승격 (산출물 깊이 선택)**: tech-design frontmatter 가 `depth: 2` 면 승격으로 간주 — 한 줄 안내 후 frontmatter `depth: 3` 갱신 + `depth_reason` 승격 사유 교체 + `change-history` [개발방향-수정] entry, 이후 기존 흐름 진행 (재확인 게이트 없음 — 명시 실행이므로).

### Step 2 — AI 자동 task 분해

tech-design §1~§7 + R1~R10 분석. TDD bite-sized task 자동 생성:
- 각 task 의 Files / Model hint / TDD steps / RISK 자동 결정
- Model 힌트 자동: 기본 sonnet (sonnet 하한 — 이보다 낮은 모델 값 금지) / 설계 + 광범위 → opus / 필드 생략 시 sonnet. mechanical · Korean prose 조작 · 신규 테스트 포함 모두 sonnet
- Before/After 코드블록 (`**원본**` / `**수정 후**`) 컨벤션 — 구현 코드 전용. 테스트 코드 블록은 싣지 않고 task 헤더 `**검증**:` 필드 (자연어 1~2줄, 무엇을 + 성공 기준) 로 대체 (v2.9+)

**Same-file mechanical 묶음 룰 (v2.0.1+)**: 둘 이상의 logical change 가 다음 **세 조건 모두** 만족하면 1 task 의 multi-step 으로 묶는다.

1. **같은 파일** — Files 목록 동일
2. **테스트 경계 없음** — 한 통합 test 또는 UI preview 로 같이 검증 가능
3. **mechanical** — modifier / handler / container 옵션 / placeholder / import 등 (= 알고리즘 변경 X)

세 조건 중 하나라도 어기면 분리. multi-step task 안 step 구조: `**검증**` 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, 1회) → byte-copy Edit (N회) → test pass → self-review. 애매하면 분리 (보수적 default).

**분할 판정**: 분해 결과 task 가 **10개 이상**이면 인덱스 + `plan/` 하위 문서 구조로 쓴다. 하위 문서 이름은 `plan/tasks-NN.md` / `plan/tasks-NN-MM.md` (2자리, 연속 범위), 하나에 task 최대 3개, 번호는 전역 연번. 인덱스 task 블록은 `**상세**` 링크 + `**Files:**` + `**Model**` + `**검증**` 만 담고, step 목록과 코드 블록은 하위 문서에 둔다. 하위 문서에는 변경이력 footer 를 두지 않는다 (인덱스 한 곳으로 모음). 10개 미만이면 단일 문서 — 코드량이 많다고 판단되면 나눠도 된다 (재량은 나누는 방향으로만).

**구현 코드 강제**: 파일을 만들거나 고치는 task 는 예외 없이 코드 블록을 싣는다. 계획서가 길어졌다고 자연어 설명으로 대체하지 않는다. 코드 블록 안에 `... 생략` / `기존 코드 유지` / `이하 동일` 류 생략 표현을 쓰지 않는다 — Step 4.5 검사가 결정적으로 차단한다.

**Step 2 끝 자체 검토 (same-file 묶음 자체 검토)**: 자동 분해 결과 같은 파일만 만지는 task chain ≥ 2건 있으면 메인이 직접 D1 의 3 조건 재검토 → 묶을지 결정. 사용자 응답 wait X (auto 모드).

### Step 3 — §2 위험 코드 지점 자동

tech-design §6 R-N → file:line + mitigation 매핑. 모든 R-N 이 §2 에 entry 갖도록 보장 (writing-plans Self-Review 룰).

### Step 4 — 산출물 자동 작성

`<slug>-implementation-plan.md` schema 따라 작성. frontmatter `commit_policy: per-task`. RAW 본문, code-pretty 호출 X (D-T12 일관 — auto-flow 는 사용자 검토 게이트가 없어서 사람이 읽기 좋게 다듬는 단계 자체가 의미 없음).

### Step 4.5 — plan_guard 자동 (3회 재시도)

Plan 본문 자동 작성 직후, 메인이 helper 자동 호출. 코드 블록 존재 (G1) / 생략 표현 (G2) / 분할 구조 (G3~G5) / byte-equal (G6) 을 한 번에 본다:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_guard import check_plan, verify_documents_byte_equal
index = Path('<PLAN_PATH>')
violations = check_plan(index)
mismatches = verify_documents_byte_equal(index, Path('.'))
for v in violations:
    print(f'{v.code} — {v.human_reason} ({v.doc_path})')
for m in mismatches:
    print(f'G6 — {m.reason}')
if violations or mismatches:
    sys.exit(1)
sys.exit(0)
"
```

위반 발견 시 메인이 즉시 수정 후 재시도 (auto 모드 — 사용자 응답 wait X). G1 은 코드 블록을 실제로 채워서, G2 는 생략 표현을 실제 코드로 바꿔서, G3~G5 는 문서를 나누거나 링크·번호를 맞춰서, G6 은 `**원본**` 블록을 현재 파일과 맞춰서 해소한다. 3회 재시도 후에도 실패 시 `ℹ️ plan_guard 가 3회 실패했습니다. 사용자가 직접 개입해주세요.` 안내 후 종료. 이 검사는 실행 단계의 원본 그대로 보존 방식이 성립하기 위한 전제이자, 계획서에 코드가 실리도록 강제하는 유일한 장치다.

### Step 5 — verifying-spec 자동 실행

`verifying-spec` invoke. 4축 보고서 생성. 결과는 transition notice 직전 노출.

### Step 6 — change-history 자동

`change-history` invoke → 첫 `[구현계획서-수정]` entry. CH-id 자동.

### Step 7 — Transition notice + auto-executing-plans invoke

```
🔍 verifying-spec 결과: ...
ℹ️ /execute-plan 단계로 자동 넘어갑니다 (여러 작업을 보조 에이전트가 동시에 진행하고, 승인 게이트는 자동으로 통과합니다). 멈추려면 "stop" 입력해주세요.
```

`parse_interrupt` 매치 시 exit. 매치 X → `js-super:auto-executing-plans` invoke.

## --no-ask 플래그 (v2.5+) — 짧은 reference

본 skill 흐름은 `AskUserQuestion` 호출이 본문에 명시 X (clarifying Q 자체가 prose default). `--no-ask` 플래그 진입 시 추가 분기 없음 — 본문 그대로 도구 호출 0 보장.

단 내부 escalation (BLOCKED 자가복구 실패 / critical 7 재질문 / Other 모호 응답) 에서도 도구 호출 0 보장. 자세한 룰은 `skills/brainstorming/SKILL.md` 의 `### 예외 — \`--no-ask\` 플래그 (v2.5+)` 답습.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. |
| code-pretty 호출 | NEVER. D-T12 일관. |
| 일반 writing-plans skill body 호출 | NEVER. self-contained mirror (D-T1). |

## Related Skills

- `auto-executing-plans` — 다음 단계 (wave-parallel subagent 강제)
- `verifying-spec` / `change-history`
- `scripts/auto_flow.parse_interrupt`, `find_latest_slug`
