# H27 — 뮤테이션 도구 사전 확인 E2E Fixture

`/execute-plan` 과 `/slice` 진입 시 "이 프로젝트 언어의 뮤테이션 도구가 없으면 한 번만 묻고, 답을 기록해 다시 묻지 않는다" 를 검증한다. 판정과 기록은 `scripts/preflight.py mutation-tools` 가 하고, 커맨드 본문은 첫 줄로 분기해 `AskUserQuestion` 을 부른다.

이 fixture 는 **runtime 에서 자동 실행되지 않는다**. 단위 테스트 (`scripts/tests/test_mutation_tools_check.py`) 가 판정 함수를 덮고, 아래 시나리오는 사람이 dogfood 할 때 커맨드 본문의 흐름을 확인한다.

## 공통 준비

임시 파이썬 프로젝트 하나 (git 저장소, `.venv` 에 pytest 만 설치, mutmut 없음):

```bash
mkdir -p e2e/src e2e/tests && cd e2e && git init -q
printf 'def add(a, b):\n    return a + b\n' > src/calc.py
printf 'from src.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > tests/test_calc.py
python3 -m venv .venv && .venv/bin/python -m pip install -q pytest
```

스크립트 한 줄 (커맨드 본문과 같은 것):

```bash
P=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/js-super/*/scripts/preflight.py" 2>/dev/null | sort -V | tail -1); [ -f "$P" ] || P=scripts/preflight.py; if [ -f "$P" ]; then python3 "$P" mutation-tools; else echo "PREFLIGHT_ABSENT"; fi
```

## Scenarios

### G1 — 도구 없음 + 테스트 있음 → 묻는다

**Setup**: 공통 준비 그대로.

**Expected**:
- 첫 줄 `MUTATION_TOOLS_ASK`, 둘째 줄에 `파이썬 (mutmut 없음)`
- `- python | 파이썬 | mutmut 없음 | 설치 범위: 프로젝트 로컬 | 설치 명령: <e2e>/.venv/bin/python -m pip install mutmut`
- 커맨드가 `AskUserQuestion` 을 **한 번** 부른다. 선택지는 설치한다 / 설치하지 않는다 (다시 묻지 않음) / 이번만 건너뛴다 셋이고, 질문 본문에 위 설치 명령과 범위가 그대로 들어 있다
- 어느 답이든 흐름이 멈추지 않고 다음 단계 (실행 모드 질문 또는 Step 1) 로 간다

### G2 — 거절 → 기록 → 다시 묻지 않는다

**Setup**: G1 에서 "설치하지 않는다" 선택.

**Expected**:
- `--record python=declined` 가 돌고 `.js-super/mutation-tools.json` 에 `"python": {"decision": "declined", ...}` 가 생긴다
- "다시 물으려면 그 파일에서 python 줄을 지우면 된다" 한 줄 안내
- 스크립트를 다시 돌리면 첫 줄 `MUTATION_TOOLS_OK`, 둘째 줄에 `기록됨 (설치하지 않음 (다시 묻지 않음))`
- `.code-gate.json` 은 생기지도 바뀌지도 않는다

**Verification**:
```bash
python3 -c "import json;print(json.load(open('.js-super/mutation-tools.json'))['python']['decision'])"
# expected: declined
test ! -f .code-gate.json && echo OK
# expected: OK
```

### G3 — 설치 → installed → 다시 묻지 않는다

**Setup**: G1 에서 "설치한다" 선택 (기록 파일은 비운 상태).

**Expected**:
- 표의 설치 명령이 **그대로** 실행된다 (`.venv/bin/python -m pip install mutmut`). 전역 pip 나 다른 명령으로 바꾸지 않는다
- 종료 코드 0 → `--record python=installed`
- 다시 돌리면 `MUTATION_TOOLS_OK` 와 `mutmut 있음` (도구가 실제로 있으므로 기록과 무관하게 묻지 않는다)

### G4 — 이번만 건너뛴다 → 기록 없음 → 다음에 다시 묻는다

**Expected**: 기록 파일이 생기지 않고, 다시 돌리면 다시 `MUTATION_TOOLS_ASK`.

### G5 — 테스트 없는 프로젝트 → 묻지 않는다

**Setup**: `tests/` 를 지운다.

**Expected**: `MUTATION_TOOLS_OK` + `파이썬: 테스트 없음`. 팝업 없음. 도구를 깔아도 못 재는 프로젝트에서 설치를 묻지 않는다.

### G6 — 자바 파일 → 묻지 않고 켜는 법만 한 번

**Setup**: `src/main/java/A.java` 하나 추가.

**Expected**:
- 첫 실행: `안내: 자바 파일이 있지만 뮤테이션은 기본 꺼짐입니다 (...). 켜려면 .code-gate.json 의 mutation 에 "java": "gradle" 를 적으십시오.` 가 나오고 커맨드가 그대로 보여준다. 팝업 없음
- 기록 파일에 `"java": {"decision": "noted"}` 가 생기고, 두 번째 실행부터 그 안내가 나오지 않는다

### G7 — 가상환경 없음 → 설치 범위가 "사용자 환경" 으로 바뀐다

**Setup**: `.venv` 를 지운다.

**Expected**: 설치 범위 `사용자 환경 (프로젝트 밖)` 과 `프로젝트 가상환경을 찾지 못해 <시스템 python> 에 설치됩니다` 안내. 팝업 본문에 그 사실이 빠지지 않는다.

### G8 — `/auto-execute-plan` 은 묻지 않는다

**Expected**: 자동 흐름 진입 시 이 스크립트가 돌지 않고 `AskUserQuestion` 도 없다. `skills/auto-executing-plans/SKILL.md` 와 `commands/auto-execute-plan.md` 에 `mutation-tools` 문자열이 없다.

### G9 — 스크립트를 못 찾음 → 한 줄 알리고 진행

**Setup**: 플러그인 캐시도 `scripts/preflight.py` 도 없는 프로젝트.

**Expected**: `PREFLIGHT_ABSENT` → `ℹ️ 뮤테이션 도구 확인을 건너뜁니다 (js-super 스크립트를 찾지 못했습니다).` 한 줄. 흐름은 그대로 진행.

## Regression catch

```bash
grep -c "mutation-tools" commands/execute-plan.md commands/slice.md
# expected: 각 2 이상
```

```bash
grep -c "mutation-tools" skills/auto-executing-plans/SKILL.md commands/auto-execute-plan.md
# expected: 각 0
```

```bash
grep -cF "MUTATION_TOOLS_ASK" scripts/preflight.py commands/execute-plan.md commands/slice.md
# expected: 각 1 이상
```
