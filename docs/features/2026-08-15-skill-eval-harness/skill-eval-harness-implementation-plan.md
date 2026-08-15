---
commit_policy: per-task
---

# 스킬 검증 환경 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** js-super 의 스킬·커맨드가 의도대로 동작하는지 확인하는 검증 환경의 1차를 만든다. 1차는 Claude 를 띄우지 않고 비용 0 으로 도는 층위(결합 검사, 산출물 정적 검사, 기존 pytest)까지다.

**Architecture:** 파이썬 러너가 뼈대다. 결합 룰은 복제하지 않고 `CLAUDE.md` 를 실행 시점에 파싱해서 쓴다. 케이스는 마크다운 앞머리에 메타데이터를 얹고 본문은 원문 그대로 둔다. 진입점은 `evals/run.py` 명령줄 하나다.

**Tech Stack:** Python 3 (표준 라이브러리 + `pytest`, `pyyaml`), bash (결합 룰 실행 전용)

**Spec inputs:**
- `skill-eval-harness-requirements.md` — 4층위 검증, 커버리지 전수, 기본 실행 30분, eval 자산 미노출, 기계+모델 혼합 판정
- `skill-eval-harness-tech-design.md` — D1 pytest 러너 / D2 `CLAUDE.md` 실행 시점 파싱 / D5 인자 배열 + 읽기 전용 관문 / D9 결합 룰 층위 미태깅 / D10 진입점은 명령줄 / D13 홈 격리 없음

**1차 범위 밖 (2차 이후):** 격리 사본, 헤드리스 실행, 발동·절차 층위, 모델 판정 캐시, fixture 44건 이관, 병렬 실행

---

## 1. 단계별 작업

### Task 1: 사전 실측 2건

예산 계산의 지배 변수 두 개가 지금 [추론]이다. 이 값이 틀리면 뒤의 설계가 통째로 흔들리므로 코드를 쓰기 전에 먼저 잰다.

**Files:**
- Create: `docs/features/2026-08-15-skill-eval-harness/사전실측-노트.md`

**Model**: sonnet

**검증**: 절차 세그먼트 1건의 실제 소요 초와 비용, 그리고 보조 에이전트를 쓰는 케이스에서 실행 기록에 어떤 필드가 채워지는지가 노트에 실제 숫자와 실제 필드명으로 적혀 있으면 성공이다. "측정했다" 같은 서술만 있고 숫자가 없으면 실패다.

- [ ] **Step 1: 절차 세그먼트 1건 실측**

임시 디렉토리에 최소 저장소 사본을 만들고, 요구사항 문서 하나만 미리 넣어둔 상태에서 `/design-tech` 한 단계만 돌린다.

```bash
TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT
rsync -a --exclude .git --exclude .worktrees ./ "$TMPD/repo/"
cd "$TMPD/repo"
time claude -p "docs/features 의 최신 폴더에서 /design-tech 를 실행해라. 첫 토픽 판정까지만 하고 멈춰라." \
  --plugin-dir "$TMPD/repo" \
  --setting-sources "" \
  --session-id "$(uuidgen)" \
  --output-format stream-json --verbose \
  --permission-mode dontAsk \
  --max-turns 40 > "$TMPD/seg.jsonl"
```

Expected: `seg.jsonl` 이 생기고 마지막 줄의 `result` 객체에 `duration_ms` 와 `total_cost_usd` 가 들어 있다.

- [ ] **Step 2: 보조 에이전트 관측 신호 실측**

`Task` 도구를 실제로 쓰는 케이스를 한 번 돌려 실행 기록에 무엇이 남는지 본다.

```bash
claude -p "Explore 에이전트 하나를 띄워서 skills/ 디렉토리에 SKILL.md 가 몇 개인지 세어 보고해라." \
  --session-id "$(uuidgen)" \
  --output-format stream-json --verbose \
  --max-turns 20 > "$TMPD/task.jsonl"
python3 -c "
import json, sys
keys = set()
for line in open('$TMPD/task.jsonl'):
    try: obj = json.loads(line)
    except Exception: continue
    keys.update(obj.keys())
print(sorted(keys))
"
```

Expected: 이벤트 종류 목록이 출력되고, 그 안에 `parent_tool_use_id` 가 있는지 없는지 확인된다.

- [ ] **Step 3: 노트 작성**

두 실측의 실제 숫자와 필드명을 노트에 적는다. 세그먼트 소요가 설계서의 [추론] 120초와 얼마나 다른지, 그 차이가 30분 검산을 깨는지 한 줄로 판정한다.

- [ ] **Step 4: Commit**

```bash
git add docs/features/2026-08-15-skill-eval-harness/사전실측-노트.md
git commit -m "chore(eval): 사전 실측 2건 — 세그먼트 소요 + 보조 에이전트 관측 신호"
```

---

### Task 2: 테스트 자산을 커맨드 디렉토리 밖으로 이동

`commands/` 아래 하위 디렉토리가 슬래시 커맨드로 등록된다. 지금 `commands/audit-risk-tests/H23-e2e/README.md` 가 `js-super:audit-risk-tests:H23-e2e:README` 라는 슬래시로 사용자에게 노출되고 있다. 요구사항 수용 기준 11 이 이 항목이다.

**Files:**
- Move: `commands/audit-risk-tests/` → `tests/eval-fixtures/H23-e2e/`

**Model**: haiku

**검증**: 이동 후 `commands/` 아래에 하위 디렉토리가 하나도 없고, 옮겨진 파일 수가 이동 전과 같으면 성공이다. 파일이 하나라도 줄면 실패다.

- [ ] **Step 1: 이동 전 파일 수 기록**

```bash
find commands/audit-risk-tests -type f | wc -l
```

- [ ] **Step 2: 이동**

```bash
mkdir -p tests/eval-fixtures
git mv commands/audit-risk-tests tests/eval-fixtures/H23-e2e
```

- [ ] **Step 3: 검증**

```bash
find tests/eval-fixtures/H23-e2e -type f | wc -l
find commands -mindepth 1 -type d | wc -l
```

Expected: 첫 번째는 Step 1 과 같은 수, 두 번째는 `0`.

- [ ] **Step 4: Commit**

```bash
git add -A commands tests/eval-fixtures
git commit -m "fix: 테스트 자산이 슬래시 커맨드로 등록되던 문제 — commands/ 밖으로 이동"
```

---

### Task 3: 기존 테스트의 경로 의존성 제거

`scripts/tests/test_changelog_buffer.py` 가 fixture 경로를 현재 작업 디렉토리 기준 상대경로로 갖고 있다. 저장소 루트가 아닌 곳에서 pytest 를 돌리면 깨진다. 러너가 이 pytest 를 항상 전수로 돌릴 예정이라 먼저 고친다.

**Files:**
- Modify: `scripts/tests/test_changelog_buffer.py:88-89`
- Test: `scripts/tests/test_changelog_buffer.py`

**Model**: sonnet

**검증**: 저장소 루트가 아닌 임의의 디렉토리를 현재 위치로 두고 이 테스트를 돌려도 통과하면 성공이다. 지금은 그 상황에서 파일을 못 찾아 실패한다.

- [ ] **Step 1: 현재 상태가 실패하는 것을 확인**

```bash
cd /tmp && python3 -m pytest /Users/seobi/jinsup_space/js-super/.worktrees/eval생성/scripts/tests/test_changelog_buffer.py::test_F1_basic_batch_fixture -v
```

Expected: FAIL (fixture 경로를 못 찾음)

- [ ] **Step 2: 경로를 파일 위치 기준으로 변경**

**원본** (`scripts/tests/test_changelog_buffer.py:88-89`):
```python
def test_F1_basic_batch_fixture():
    fixtures = Path("skills/js-super-sub-driven/tests/F1-basic-batch")
```

**수정 후**:
```python
def test_F1_basic_batch_fixture():
    repo_root = Path(__file__).resolve().parents[2]
    fixtures = repo_root / "skills/js-super-sub-driven/tests/F1-basic-batch"
```

- [ ] **Step 3: 두 위치에서 통과 확인**

```bash
cd /Users/seobi/jinsup_space/js-super/.worktrees/eval생성 && python3 -m pytest scripts/tests/ -v
cd /tmp && python3 -m pytest /Users/seobi/jinsup_space/js-super/.worktrees/eval생성/scripts/tests/ -v
```

Expected: 두 번 다 PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/tests/test_changelog_buffer.py
git commit -m "fix(test): fixture 경로를 실행 위치 비의존으로 변경"
```

---

### Task 4: 개발 환경 설정 갱신

러너 실행 기록을 커밋 대상에서 빼고, 병렬 실행에 필요한 의존성을 선언한다. 두 파일 모두 설정 한 줄 추가로, 같은 논리적 변경이다.

**Files:**
- Modify: `.gitignore:23-24`
- Modify: `requirements-dev.txt:1-5`

**Model**: haiku

**검증**: `evals/runs/` 아래 임의 파일을 만들었을 때 git 이 무시하고, `pytest-xdist` 가 의존성 목록에 들어 있으면 성공이다.

- [ ] **Step 1: `.gitignore` 에 실행 기록 제외 추가**

**원본** (`.gitignore:23-24`):
```gitignore
# v2.3.0 — /audit-risk 보고서 폴더 (개인 도구 산출물, repo 노이즈 방지)
docs/audit/
```

**수정 후**:
```gitignore
# v2.3.0 — /audit-risk 보고서 폴더 (개인 도구 산출물, repo 노이즈 방지)
docs/audit/

# 2026-08-15 — eval harness 실행 기록 (매 실행마다 생성, 커밋 대상 아님)
evals/runs/
```

- [ ] **Step 2: `requirements-dev.txt` 에 병렬 실행 의존성 추가**

**원본** (`requirements-dev.txt:1-5`):
```text
pytest>=7.4
requests>=2.31
pytest-json-report>=1.5
pytest-httpserver>=1.0
pyyaml>=6.0
```

**수정 후**:
```text
pytest>=7.4
requests>=2.31
pytest-json-report>=1.5
pytest-httpserver>=1.0
pyyaml>=6.0
pytest-xdist>=3.5
```

- [ ] **Step 3: 확인**

```bash
mkdir -p evals/runs && touch evals/runs/x.tmp
git check-ignore -v evals/runs/x.tmp
grep -c "pytest-xdist" requirements-dev.txt
rm -f evals/runs/x.tmp
```

Expected: 첫 명령이 `.gitignore` 규칙을 출력하고, 두 번째가 `1` 을 출력한다.

- [ ] **Step 4: Commit**

```bash
git add .gitignore requirements-dev.txt
git commit -m "chore(eval): 실행 기록 제외 + 병렬 실행 의존성 선언"
```

---

### Task 5: 테스트 실행 지침의 낡은 제약 갱신

`docs/testing.md` 의 두 제약이 새 설계와 정면 충돌한다. 하나는 플러그인 디렉토리 안에서만 돌리라는 것이고, 다른 하나는 이제 존재하지 않는 개발용 마켓플레이스 설정을 요구한다. 남겨두면 다음 사람이 충돌하는 지침 둘을 보게 된다.

**Files:**
- Modify: `docs/testing.md:36-38`

**Model**: sonnet

**검증**: 갱신 후 `docs/testing.md` 에 "superpowers plugin directory" 와 "superpowers-dev" 문자열이 남아 있지 않고, 대신 `--plugin-dir` 로 임시 사본에서 돌리는 방식이 적혀 있으면 성공이다.

- [ ] **Step 1: 두 제약 교체**

**원본** (`docs/testing.md:36-38`):
```markdown
- Must run from the **superpowers plugin directory** (not from temp directories)
- Claude Code must be installed and available as `claude` command
- Local dev marketplace must be enabled: `"superpowers@superpowers-dev": true` in `~/.claude/settings.json`
```

**수정 후**:
```markdown
- Claude Code must be installed and available as `claude` command
- Run against an isolated copy, not the working tree: `rsync -a --exclude .git ./ "$TMPD/repo/"` then pass `--plugin-dir "$TMPD/repo"`
- Pass `--setting-sources ""` so the user's own settings and plugins do not leak into the run
- Do NOT rely on a dev marketplace entry in `~/.claude/settings.json` — that mechanism is gone; `--plugin-dir` is the supported way to test a working copy
```

- [ ] **Step 2: 확인**

```bash
grep -c "superpowers plugin directory\|superpowers-dev" docs/testing.md
grep -c "plugin-dir" docs/testing.md
```

Expected: 첫 번째 `0`, 두 번째 `1` 이상

- [ ] **Step 3: Commit**

```bash
git add docs/testing.md
git commit -m "docs(testing): 낡은 실행 제약 2건 갱신 — plugin-dir 격리 방식으로 교체"
```

---

### Task 6: 러너 골격 + 결합 룰 파서

`CLAUDE.md` 의 bash 코드 블록에서 검사 명령과 기대값을 뽑아낸다. 룰을 복제하지 않고 실행 시점에 읽는 것이 D2 다.

**Files:**
- Create: `evals/__init__.py`
- Create: `evals/conftest.py`
- Create: `evals/runner/__init__.py`
- Create: `evals/runner/coupling.py`
- Create: `evals/tests/__init__.py`
- Test: `evals/tests/test_coupling.py`

**Model**: sonnet

**검증**: `CLAUDE.md` 를 파싱했을 때 룰이 100건 이상 나오고, 각 룰이 명령 문자열과 기대값(숫자 또는 자연어)과 출처 줄 번호를 갖고 있으면 성공이다. 기대값 주석이 없는 룰은 기대값이 `None` 으로 들어와야 하고 파싱이 죽으면 안 된다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계가 테스트 코드를 직접 작성한다.

Run: `python3 -m pytest evals/tests/test_coupling.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 패키지 뼈대 + 테스트 경로 설정**

`evals/__init__.py`, `evals/runner/__init__.py`, `evals/tests/__init__.py` 는 빈 파일로 만든다. `evals/conftest.py` 는 pytest 를 어느 위치에서 돌려도 저장소 루트를 import 경로에 넣어준다.

**수정 후** (`new file: evals/conftest.py`):
```python
"""pytest 를 어느 위치에서 돌려도 저장소 루트를 import 경로에 넣는다.

scripts/tests 가 실행 위치에 묶여 있던 문제와 같은 종류를 미리 막는다.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
```

- [ ] **Step 3: 파서 구현**

**수정 후** (`new file: evals/runner/coupling.py`):
```python
"""CLAUDE.md 의 bash 코드 블록에서 결합 회귀 룰을 추출한다.

룰을 파일로 복제하지 않는다. CLAUDE.md 가 정답 원천이고 (설계서 D2),
러너는 실행할 때마다 새로 읽는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FENCE_OPEN = re.compile(r"^```(bash|sh|shell)\s*$")
FENCE_CLOSE = re.compile(r"^```\s*$")
EXPECTED = re.compile(r"^#\s*expected:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
COMMENT = re.compile(r"^\s*#")


@dataclass(frozen=True)
class Rule:
    """CLAUDE.md 한 곳에서 뽑은 검사 명령 하나."""

    source: str          # "CLAUDE.md:1234"
    command: str         # 실행할 셸 명령 (여러 줄 가능)
    expected: str | None  # "# expected:" 주석 값. 없으면 None

    @property
    def expected_is_numeric(self) -> bool:
        if self.expected is None:
            return False
        return _leading_int(self.expected) is not None

    @property
    def expected_int(self) -> int | None:
        return None if self.expected is None else _leading_int(self.expected)


def _leading_int(text: str) -> int | None:
    match = re.match(r"^\s*(각\s*)?(>=|<=|==)?\s*(\d+)", text)
    return int(match.group(3)) if match else None


def parse_claude_md(path: Path) -> list[Rule]:
    """CLAUDE.md 를 읽어 Rule 목록을 만든다."""
    lines = path.read_text(encoding="utf-8").splitlines()
    rules: list[Rule] = []
    in_fence = False
    buffer: list[str] = []
    buffer_start = 0

    for index, line in enumerate(lines, start=1):
        if not in_fence:
            if FENCE_OPEN.match(line):
                in_fence = True
                buffer = []
                buffer_start = index + 1
            continue
        if FENCE_CLOSE.match(line):
            rules.extend(_split_block(buffer, buffer_start, path.name))
            in_fence = False
            continue
        buffer.append(line)

    return rules


def _split_block(block: list[str], start_line: int, filename: str) -> list[Rule]:
    """코드 블록 하나를 '명령 + expected 주석' 단위로 자른다.

    형식은 CLAUDE.md 안에서 일관되게 '명령 여러 줄 → # expected: 값' 이다.
    expected 주석이 없이 다음 명령이 시작되면 기대값 없는 룰로 닫는다.
    """
    rules: list[Rule] = []
    pending: list[str] = []
    pending_line = start_line

    def close(expected: str | None) -> None:
        command = "\n".join(pending).strip()
        if command:
            rules.append(
                Rule(
                    source=f"{filename}:{pending_line}",
                    command=command,
                    expected=expected,
                )
            )

    for offset, raw in enumerate(block):
        line_number = start_line + offset
        matched = EXPECTED.match(raw.strip())
        if matched:
            close(matched.group("value"))
            pending = []
            pending_line = line_number + 1
            continue
        if COMMENT.match(raw) or not raw.strip():
            if not pending:
                pending_line = line_number + 1
            continue
        if not pending:
            pending_line = line_number
        pending.append(raw)

    close(None)
    return rules
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest evals/tests/test_coupling.py -v`
Expected: PASS

- [ ] **Step 5: 실제 CLAUDE.md 로 건수 확인**

```bash
python3 -c "
from pathlib import Path
from evals.runner.coupling import parse_claude_md
rules = parse_claude_md(Path('CLAUDE.md'))
print('rules:', len(rules))
print('with expected:', sum(1 for r in rules if r.expected))
print('numeric:', sum(1 for r in rules if r.expected_is_numeric))
"
```

Expected: `rules` 가 100 이상

- [ ] **Step 6: Commit**

```bash
git add evals/
git commit -m "feat(eval): CLAUDE.md 결합 룰 파서"
```

---

### Task 7: 읽기 전용 관문 + 단언 실행기

결합 룰은 셸 파이프라인이라 셸을 거쳐야 한다. 대신 실행 전에 읽기 전용인지 검사한다 (설계서 D5). 우리가 직접 쓰는 단언은 인자 배열로만 받아 셸을 안 거친다.

**Files:**
- Create: `evals/runner/guard.py`
- Create: `evals/runner/assertions.py`
- Test: `evals/tests/test_guard.py`
- Test: `evals/tests/test_assertions.py`

**Model**: sonnet

**검증**: 관문이 `grep ... | grep -v ...` 같은 읽기 전용 파이프라인은 통과시키고, `rm -rf x`, `echo a > b`, `git commit`, `sed -i`, `python3 -c "open('x','w')"` 는 전부 차단하면 성공이다. 단언 실행기는 `zero`, `eq`, `gte`, `lte`, `lines_eq`, `exists`, `capture` 일곱 연산이 각각 통과와 실패를 정확히 가리면 성공이다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `python3 -m pytest evals/tests/test_guard.py evals/tests/test_assertions.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 관문 구현**

**수정 후** (`new file: evals/runner/guard.py`):
```python
"""CLAUDE.md 에서 가져온 셸 명령이 읽기 전용인지 검사한다.

결합 룰은 파이프가 들어간 셸 파이프라인이라 인자 배열로 표현되지 않는다.
그래서 셸을 거치되, 거치기 전에 이 관문을 통과해야 한다 (설계서 D5).
관문에 걸린 룰은 조용히 통과시키지 않고 차단 상태로 보고한다.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

ALLOWED = {
    "grep", "ls", "test", "awk", "sed", "find", "cat", "wc",
    "head", "tail", "echo", "sort", "uniq", "cut", "tr",
    "python3", "git", "true", "false", "[",
}

GIT_ALLOWED = {
    "status", "diff", "log", "ls-files", "rev-parse", "show", "check-ignore",
}

FORBIDDEN_TOKENS = re.compile(r"(^|\s)(rm|mv|cp|mkdir|touch|chmod|chown|ln|tee|dd)(\s|$)")
REDIRECT = re.compile(r"(?<![0-9<>])>{1,2}(?!&)")
SUBSHELL = re.compile(r"`|\$\(")
PY_WRITE = re.compile(r"open\s*\([^)]*['\"][wax]|os\.(remove|unlink|rmdir|rename)|shutil\.(rmtree|move|copy)|Path\([^)]*\)\.(write_text|write_bytes|unlink)")


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str = ""


def check_read_only(command: str) -> GuardResult:
    """셸 명령이 읽기 전용이면 허용, 아니면 이유와 함께 차단."""
    if REDIRECT.search(command):
        return GuardResult(False, "출력 리다이렉션 사용")
    if SUBSHELL.search(command):
        return GuardResult(False, "명령 치환 사용")
    if FORBIDDEN_TOKENS.search(command):
        return GuardResult(False, "쓰기 계열 명령 포함")
    if PY_WRITE.search(command):
        return GuardResult(False, "파이썬 쓰기 호출 포함")

    for segment in _segments(command):
        try:
            words = shlex.split(segment)
        except ValueError:
            return GuardResult(False, "따옴표가 닫히지 않음")
        if not words:
            continue
        head = words[0]
        if head not in ALLOWED:
            return GuardResult(False, f"허용 목록 밖 명령: {head}")
        if head == "git":
            sub = next((w for w in words[1:] if not w.startswith("-")), "")
            if sub not in GIT_ALLOWED:
                return GuardResult(False, f"허용 목록 밖 git 하위 명령: {sub or '(없음)'}")
        if head == "sed":
            if any(w.startswith("-i") for w in words[1:]):
                return GuardResult(False, "sed -i 는 파일을 고침")
            if not any(w.startswith("-n") for w in words[1:]):
                return GuardResult(False, "sed 는 -n 과 함께만 허용")

    return GuardResult(True)


def _segments(command: str) -> list[str]:
    """파이프·세미콜론·논리연산으로 구간을 나눈다."""
    parts = re.split(r"\|\||&&|\||;|\n", command)
    return [p.strip() for p in parts if p.strip()]
```

- [ ] **Step 3: 단언 실행기 구현**

**수정 후** (`new file: evals/runner/assertions.py`):
```python
"""단언을 평가한다.

두 경로가 있다.
- run_argv: 우리가 케이스에 직접 쓰는 단언. 인자 배열만 받고 셸을 안 거친다.
- run_shell_rule: CLAUDE.md 에서 가져온 결합 룰. 관문을 통과해야 셸로 간다.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from evals.runner.guard import check_read_only

TIMEOUT_S = 30


@dataclass(frozen=True)
class Outcome:
    status: str          # PASS | FAIL | BLOCKED
    actual: str = ""
    reason: str = ""


def run_argv(argv: list[str], cwd: Path) -> tuple[int, str]:
    """인자 배열을 셸 없이 실행한다."""
    proc = subprocess.run(
        argv, cwd=str(cwd), capture_output=True, text=True,
        timeout=TIMEOUT_S, shell=False,
    )
    return proc.returncode, proc.stdout

def run_shell_rule(command: str, cwd: Path) -> Outcome:
    """CLAUDE.md 결합 룰을 관문 통과 후 bash 로 실행한다.

    셸을 bash 로 고정한다. zsh 는 매치 없는 글롭을 오류로 만들어
    같은 룰이 환경마다 다르게 동작한다.
    """
    verdict = check_read_only(command)
    if not verdict.allowed:
        return Outcome("BLOCKED", reason=verdict.reason)
    try:
        proc = subprocess.run(
            ["bash", "-c", command], cwd=str(cwd), capture_output=True,
            text=True, timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return Outcome("BLOCKED", reason=f"{TIMEOUT_S}초 초과")
    return Outcome("PASS", actual=proc.stdout)


def compare(op: str, actual: str, expected) -> Outcome:
    """관측값과 기대값을 비교한다."""
    text = actual.strip()
    if op == "zero":
        return _verdict(text == "" or text == "0", text, "출력이 비어 있어야 함")
    if op == "exists":
        return _verdict(bool(text), text, "출력이 있어야 함")
    if op == "capture":
        return Outcome("PASS", actual=text)

    numbers = [int(t) for t in text.split() if t.lstrip("-").isdigit()]
    if op == "lines_eq":
        count = len([line for line in actual.splitlines() if line.strip()])
        return _verdict(count == int(expected), str(count), f"{expected} 줄이어야 함")
    if not numbers:
        return Outcome("FAIL", actual=text, reason="숫자를 못 읽음")

    target = int(expected)
    if op == "eq":
        return _verdict(all(n == target for n in numbers), text, f"{target} 이어야 함")
    if op == "gte":
        return _verdict(all(n >= target for n in numbers), text, f"{target} 이상이어야 함")
    if op == "lte":
        return _verdict(all(n <= target for n in numbers), text, f"{target} 이하여야 함")
    return Outcome("BLOCKED", actual=text, reason=f"모르는 연산: {op}")


def _verdict(ok: bool, actual: str, want: str) -> Outcome:
    return Outcome("PASS", actual=actual) if ok else Outcome("FAIL", actual=actual, reason=want)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest evals/tests/test_guard.py evals/tests/test_assertions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add evals/
git commit -m "feat(eval): 읽기 전용 관문 + 단언 실행기"
```

---

### Task 8: 케이스 로더

케이스는 마크다운 앞머리에 YAML 메타데이터를 얹은 형식이다. 본문은 사람이 읽는 시나리오라 손대지 않는다.

**Files:**
- Create: `evals/runner/cases.py`
- Create: `evals/cases/self/eval-assets-not-loaded.md`
- Test: `evals/tests/test_cases.py`

**Model**: sonnet

**검증**: 앞머리가 있는 마크다운을 읽어 필수 6개 항목(`id`, `title`, `status`, `layer`, `covers`, `expect`)을 뽑아내고, 필수 항목이 빠지면 그 파일 경로와 빠진 항목 이름을 담은 오류를 내면 성공이다. 앞머리가 아예 없는 파일은 케이스가 아니라고 판단하고 건너뛰어야 한다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `python3 -m pytest evals/tests/test_cases.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 로더 구현**

**수정 후** (`new file: evals/runner/cases.py`):
```python
"""케이스 파일을 읽는다.

형식은 '마크다운 앞머리 YAML + --- 아래 원문 본문' 이다.
본문은 기존 fixture README 를 그대로 복사한 것이라 파서가 건드리지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REQUIRED = ("id", "title", "status", "layer", "covers", "expect")
VALID_STATUS = {"active", "stale", "wip", "blocked"}
VALID_LAYER = {"A", "B", "C", "D"}


class CaseError(ValueError):
    """케이스 파일이 형식에 안 맞을 때."""


@dataclass
class Case:
    path: Path
    meta: dict
    body: str

    id: str = ""
    title: str = ""
    status: str = "active"
    layer: list = field(default_factory=list)
    covers: list = field(default_factory=list)
    expect: list = field(default_factory=list)

    def __post_init__(self) -> None:
        for key in REQUIRED:
            setattr(self, key, self.meta[key])

    @property
    def needs_claude(self) -> bool:
        return "run" in self.meta

    @property
    def danger(self) -> str:
        return str(self.meta.get("danger", "-"))


def load_case(path: Path) -> Case | None:
    """케이스 하나를 읽는다. 앞머리가 없으면 None."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    _, _, rest = text.partition("---\n")
    raw_meta, sep, body = rest.partition("\n---\n")
    if not sep:
        raise CaseError(f"{path}: 앞머리가 닫히지 않음")

    meta = yaml.safe_load(raw_meta) or {}
    missing = [key for key in REQUIRED if key not in meta]
    if missing:
        raise CaseError(f"{path}: 필수 항목 누락 — {', '.join(missing)}")
    if meta["status"] not in VALID_STATUS:
        raise CaseError(f"{path}: 모르는 status — {meta['status']}")
    bad_layer = [item for item in meta["layer"] if item not in VALID_LAYER]
    if bad_layer:
        raise CaseError(f"{path}: 모르는 layer — {', '.join(bad_layer)}")

    return Case(path=path, meta=meta, body=body)


def load_all(root: Path) -> tuple[list[Case], list[str]]:
    """cases/ 아래를 전부 읽는다. (케이스 목록, 오류 목록)"""
    cases: list[Case] = []
    errors: list[str] = []
    for path in sorted(root.rglob("*.md")):
        try:
            case = load_case(path)
        except CaseError as exc:
            errors.append(str(exc))
            continue
        if case is not None:
            cases.append(case)
    return cases, errors
```

- [ ] **Step 3: 첫 케이스 작성 — eval 자산 미노출 검사**

**수정 후** (`new file: evals/cases/self/eval-assets-not-loaded.md`):
```markdown
---
id: self/eval-assets-not-loaded
title: eval 자산이 Claude Code 로드 경로에 없다
status: active
layer: [C]
covers:
  - evals/**
  - commands/**
  - skills/**
expect:
  - kind: shell
    argv: ["bash", "-c", "find commands -mindepth 1 -type d | wc -l"]
    op: eq
    value: 0
  - kind: shell
    argv: ["bash", "-c", "ls -d skills/evals evals/skills 2>/dev/null | wc -l"]
    op: eq
    value: 0
traceability: [수용기준-8, 수용기준-11]
---

# eval 자산이 사용자에게 안 보인다

**시나리오**: Claude Code 는 `skills/`, `commands/`, `agents/`, `hooks/hooks.json` 네 곳만
자동으로 읽어들인다. eval 자산이 그 안에 들어가면 플러그인 사용자 세션에 스킬 설명이
상주하거나 슬래시 목록에 뜬다.

**과거 사고**: `commands/audit-risk-tests/H23-e2e/README.md` 가
`js-super:audit-risk-tests:H23-e2e:README` 라는 슬래시로 실제 등록되고 있었다.
`commands/` 아래 하위 디렉토리가 재귀로 스캔되고 디렉토리명이 콜론으로 이어지기 때문이다.

**검증 방법**: `commands/` 아래에 하위 디렉토리가 하나도 없어야 하고,
`skills/` 아래에 eval 관련 디렉토리가 없어야 한다.

**놓치는 것**: 플러그인 캐시에 실제로 무엇이 로드되는지는 여기서 안 본다.
그건 헤드리스 실행이 붙는 2차에서 로드 정보 한 줄을 읽어 확인한다.
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest evals/tests/test_cases.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add evals/
git commit -m "feat(eval): 케이스 로더 + 자산 미노출 케이스"
```

---

### Task 9: 검사 단계 (lint)

실행 전에 무료로 도는 검사다. 모순되는 기대값을 잡아 실행을 거부하고, 케이스에 안 걸린 대상과 게이트 결손을 보고한다.

**Files:**
- Create: `evals/runner/lint.py`
- Test: `evals/tests/test_lint.py`

**Model**: sonnet

**검증**: 같은 명령에 다른 기대값을 가진 케이스 쌍을 넣으면 모순으로 잡아내고, `git ls-files` 결과 중 어느 케이스의 `covers` 에도 안 걸린 파일을 미등록 목록으로 내면 성공이다. 모순이 하나라도 있으면 실행 거부 신호를 내야 한다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `python3 -m pytest evals/tests/test_lint.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 검사 구현**

**수정 후** (`new file: evals/runner/lint.py`):
```python
"""실행 전 검사. 비용 0.

세 가지를 본다.
1. 같은 명령에 기대값이 다른 케이스 쌍 (있으면 실행 거부)
2. 어느 케이스의 covers 에도 안 걸린 대상 파일
3. 스킬 본문의 승인 게이트 지점 대비 게이트 케이스 결손
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from evals.runner.cases import Case
from evals.runner.coupling import Rule

TARGET_PREFIXES = ("skills/", "commands/", "agents/", "hooks/", "scripts/")
GATE_PATTERN = re.compile(r"AskUserQuestion")


@dataclass
class LintReport:
    conflicts: list[str] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    gate_gaps: list[str] = field(default_factory=list)
    case_errors: list[str] = field(default_factory=list)

    @property
    def must_refuse(self) -> bool:
        """모순이나 케이스 형식 오류가 있으면 실행하지 않는다."""
        return bool(self.conflicts or self.case_errors)


def normalize(command: str) -> str:
    """공백과 줄바꿈 차이를 없앤 비교용 형태."""
    return " ".join(command.split())


def find_conflicts(rules: list[Rule], cases: list[Case]) -> list[str]:
    """같은 명령인데 기대값이 다른 쌍을 찾는다."""
    seen: dict[str, tuple[str, str]] = {}
    conflicts: list[str] = []

    def register(command: str, expected: str | None, source: str) -> None:
        if expected is None:
            return
        key = normalize(command)
        if key in seen and seen[key][0] != expected:
            conflicts.append(
                f"같은 명령에 기대값이 다름:\n"
                f"    명령: {key[:100]}\n"
                f"    {seen[key][1]} → {seen[key][0]}\n"
                f"    {source} → {expected}"
            )
            return
        seen.setdefault(key, (expected, source))

    for rule in rules:
        register(rule.command, rule.expected, rule.source)
    for case in cases:
        for item in case.expect:
            if item.get("kind") != "shell":
                continue
            argv = item.get("argv", [])
            command = argv[-1] if argv else ""
            value = item.get("value")
            register(command, None if value is None else str(value), case.id)

    return conflicts


def find_uncovered(repo_root: Path, cases: list[Case]) -> list[str]:
    """어느 케이스의 covers 에도 안 걸린 대상 파일."""
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=str(repo_root),
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()

    targets = [
        path for path in tracked
        if path.startswith(TARGET_PREFIXES) and "/tests/" not in path
    ]
    globs = [pattern for case in cases if case.status == "active" for pattern in case.covers]

    return [
        path for path in targets
        if not any(fnmatch.fnmatch(path, pattern) for pattern in globs)
    ]


def find_gate_gaps(repo_root: Path, cases: list[Case]) -> list[str]:
    """승인 게이트가 있는 스킬 중 게이트 케이스가 없는 것."""
    covered = {
        pattern for case in cases
        if "B" in case.layer for pattern in case.covers
    }
    gaps: list[str] = []
    for skill in sorted((repo_root / "skills").glob("*/SKILL.md")):
        body = skill.read_text(encoding="utf-8")
        hits = len(GATE_PATTERN.findall(body))
        if hits == 0:
            continue
        rel = str(skill.relative_to(repo_root))
        if not any(fnmatch.fnmatch(rel, pattern) for pattern in covered):
            gaps.append(f"{rel} — 게이트 언급 {hits}회, 절차 케이스 없음")
    return gaps


def run_lint(repo_root: Path, rules: list[Rule], cases: list[Case], case_errors: list[str]) -> LintReport:
    return LintReport(
        conflicts=find_conflicts(rules, cases),
        uncovered=find_uncovered(repo_root, cases),
        gate_gaps=find_gate_gaps(repo_root, cases),
        case_errors=list(case_errors),
    )
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `python3 -m pytest evals/tests/test_lint.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add evals/
git commit -m "feat(eval): 실행 전 검사 — 모순 / 미등록 / 게이트 결손"
```

---

### Task 10: 기준선 대조 + 상태 분류

이전 실행 대비 무엇이 새로 깨졌는지 가린다. 관측값과 사람의 판단을 분리하는 것이 핵심이다.

**Files:**
- Create: `evals/runner/baseline.py`
- Test: `evals/tests/test_baseline.py`

**Model**: sonnet

**검증**: 기준선에 통과로 적힌 항목이 이번에 실패하면 `REGRESSION`, 기준선에 회귀로 적힌 항목이 이번에도 실패하면 `KNOWN`, 그 항목이 이번에 통과하면 `FIXED`, 기준선에 없는 항목은 `NEW` 로 분류하면 성공이다. 라벨이 없는 항목이 통과 집계에 들어가면 실패다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `python3 -m pytest evals/tests/test_baseline.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 대조기 구현**

**수정 후** (`new file: evals/runner/baseline.py`):
```python
"""기준선 대조.

baseline.json 은 verdict (그때 관측된 값) 와 label (사람의 판단) 을 나눠 담는다.
관측만 굳히면 지금 실패 중인 진짜 회귀가 정답으로 박제된다 (요구사항 결정 8).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

PASSING = {"PASS", "KNOWN", "FIXED"}
NOT_COUNTED = {"NOT-SELECTED", "DEFERRED", "BLOCKED", "PENDING"}


@dataclass(frozen=True)
class Classified:
    case_id: str
    status: str
    verdict: str
    label: str | None
    detail: str = ""


def load_baseline(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "cases": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_baseline(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def classify(case_id: str, verdict: str, baseline: dict, detail: str = "") -> Classified:
    """이번 관측을 기준선과 대조해 상태를 정한다."""
    if verdict in NOT_COUNTED:
        return Classified(case_id, verdict, verdict, None, detail)

    record = baseline.get("cases", {}).get(case_id)
    if record is None:
        return Classified(case_id, "NEW", verdict, None, detail)

    label = record.get("label")
    was_pass = record.get("verdict") == "PASS"

    if verdict == "PASS":
        status = "FIXED" if not was_pass else "PASS"
    elif label in {"regression-open", "blocked"}:
        status = "KNOWN"
    elif was_pass:
        status = "REGRESSION"
    else:
        status = "KNOWN" if label else "FAIL"

    return Classified(case_id, status, verdict, label, detail)


def summarize(rows: list[Classified]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def has_blocking_failure(rows: list[Classified]) -> bool:
    """새로 깨진 것이나 미분류가 있으면 실패로 끝낸다."""
    return any(row.status in {"REGRESSION", "FAIL", "NEW"} for row in rows)
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `python3 -m pytest evals/tests/test_baseline.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add evals/
git commit -m "feat(eval): 기준선 대조 + 상태 분류"
```

---

### Task 11: 보고 + 상태 누수 방지

무엇이 돌았고 무엇이 건너뛰어졌는지 명시한다. 건너뛴 항목이 조용히 통과로 집계되면 안 된다.

**Files:**
- Create: `evals/runner/report.py`
- Test: `evals/tests/test_report.py`

**Model**: sonnet

**검증**: 보고서에 상태별 건수가 나오고, 미선택·연기·차단·보류 네 상태가 통과 집계에서 제외되며, 각각의 목록이 별도로 표시되면 성공이다. 네 상태 중 하나라도 통과 수에 더해지면 실패다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `python3 -m pytest evals/tests/test_report.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 보고 구현**

**수정 후** (`new file: evals/runner/report.py`):
```python
"""사람이 읽는 보고서를 만든다.

건너뛴 항목을 조용히 통과로 집계하지 않는 것이 이 모듈의 존재 이유다
(요구사항 수용 기준 5).
"""

from __future__ import annotations

from evals.runner.baseline import NOT_COUNTED, PASSING, Classified
from evals.runner.lint import LintReport

ORDER = [
    "REGRESSION", "FAIL", "NEW", "KNOWN", "FIXED", "PASS",
    "NOT-SELECTED", "DEFERRED", "BLOCKED", "PENDING",
]

LABEL = {
    "REGRESSION": "새로 깨짐",
    "FAIL": "실패",
    "NEW": "신규 (미분류)",
    "KNOWN": "이미 알려진 실패",
    "FIXED": "고쳐짐",
    "PASS": "통과",
    "NOT-SELECTED": "이번에 선택 안 됨",
    "DEFERRED": "예산 초과로 미룸",
    "BLOCKED": "실행 못 함",
    "PENDING": "판정 대기",
}


def passing_count(rows: list[Classified]) -> int:
    """통과로 집계되는 수. NOT_COUNTED 는 절대 포함하지 않는다."""
    return sum(1 for row in rows if row.status in PASSING and row.status not in NOT_COUNTED)


def render(rows: list[Classified], lint: LintReport, elapsed_s: float) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1

    lines = ["", f"검증 결과 — {len(rows)}건, {elapsed_s:.1f}초", ""]
    for status in ORDER:
        if status in counts:
            lines.append(f"  {LABEL[status]:<18} {counts[status]:>4}")
    lines.append("")

    for status in ("REGRESSION", "FAIL", "NEW", "BLOCKED"):
        listed = [row for row in rows if row.status == status]
        if not listed:
            continue
        lines.append(f"[{LABEL[status]}]")
        for row in listed:
            suffix = f" — {row.detail}" if row.detail else ""
            lines.append(f"  {row.case_id}{suffix}")
        lines.append("")

    if lint.case_errors:
        lines.append("[케이스 형식 오류]")
        lines.extend(f"  {item}" for item in lint.case_errors)
        lines.append("")
    if lint.conflicts:
        lines.append("[상충하는 기대값 — 실행 거부]")
        lines.extend(f"  {item}" for item in lint.conflicts)
        lines.append("")
    if lint.uncovered:
        lines.append(f"[케이스에 안 걸린 대상 {len(lint.uncovered)}건]")
        lines.extend(f"  {item}" for item in lint.uncovered[:20])
        if len(lint.uncovered) > 20:
            lines.append(f"  … 외 {len(lint.uncovered) - 20}건")
        lines.append("")
    if lint.gate_gaps:
        lines.append(f"[승인 게이트 케이스 결손 {len(lint.gate_gaps)}건]")
        lines.extend(f"  {item}" for item in lint.gate_gaps)
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `python3 -m pytest evals/tests/test_report.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add evals/
git commit -m "feat(eval): 보고 + 상태 누수 방지"
```

---

### Task 12: 명령줄 진입점 통합 + 첫 기준선 저작

지금까지의 조각을 하나로 잇고, 실제로 한 번 돌려 지금 실패 중인 결합 룰을 분류한다.

**Files:**
- Create: `evals/run.py`
- Create: `evals/baseline.json`
- Modify: `CLAUDE.md` (끝에 결합 메모 1섹션 추가)
- Test: `evals/tests/test_run.py`

**Model**: sonnet

**검증**: `python3 evals/run.py --check` 가 결합 룰 100건 이상과 기존 pytest 54함수를 돌리고 30초 안에 끝나며 상태별 건수를 출력하면 성공이다. `--accept` 없이는 기준선 파일을 절대 고치지 않아야 하고, 분류 안 된 항목이 있으면 `--accept` 를 거부해야 한다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

Run: `python3 -m pytest evals/tests/test_run.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 진입점 구현**

**수정 후** (`new file: evals/run.py`):
```python
#!/usr/bin/env python3
"""스킬 검증 환경 진입점.

1차 범위는 Claude 를 띄우지 않는 층위만 돈다.
  - 결합 룰 (CLAUDE.md 실행 시점 파싱)
  - 기존 pytest (scripts/tests)
  - 정적 산출물 케이스

사용법:
  python3 evals/run.py --check          이번 상태를 보고만 한다
  python3 evals/run.py --accept         지금 결과를 기준선으로 굳힌다 (분류 필수)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evals.runner import assertions, baseline, cases, coupling, lint, report  # noqa: E402


def collect_coupling(repo_root: Path) -> list[baseline.Classified]:
    rules = coupling.parse_claude_md(repo_root / "CLAUDE.md")
    base = baseline.load_baseline(repo_root / "evals" / "baseline.json")
    rows: list[baseline.Classified] = []

    for index, rule in enumerate(rules):
        case_id = f"coupling/{rule.source}#{index}"
        outcome = assertions.run_shell_rule(rule.command, repo_root)
        if outcome.status == "BLOCKED":
            rows.append(baseline.classify(case_id, "BLOCKED", base, outcome.reason))
            continue
        if rule.expected is None:
            rows.append(baseline.classify(case_id, "PENDING", base, "기대값 주석 없음"))
            continue
        if not rule.expected_is_numeric:
            rows.append(baseline.classify(case_id, "PENDING", base, f"자연어 기대값: {rule.expected}"))
            continue

        op = "eq" if "각" not in rule.expected and ">=" not in rule.expected else "gte"
        verdict = assertions.compare(op, outcome.actual, rule.expected_int)
        rows.append(baseline.classify(case_id, verdict.status, base, verdict.reason))

    return rows


def collect_pytest(repo_root: Path) -> list[baseline.Classified]:
    base = baseline.load_baseline(repo_root / "evals" / "baseline.json")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "scripts/tests", "evals/tests", "-q"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return [baseline.classify("pytest/scripts+evals", status, base, tail)]


def collect_cases(repo_root: Path) -> tuple[list[baseline.Classified], list[cases.Case], list[str]]:
    base = baseline.load_baseline(repo_root / "evals" / "baseline.json")
    loaded, errors = cases.load_all(repo_root / "evals" / "cases")
    rows: list[baseline.Classified] = []

    for case in loaded:
        if case.status != "active":
            rows.append(baseline.classify(case.id, "BLOCKED", base, f"status={case.status}"))
            continue
        if case.needs_claude:
            rows.append(baseline.classify(case.id, "NOT-SELECTED", base, "1차 범위 밖 (실행 층위)"))
            continue
        failures = []
        for item in case.expect:
            argv = item["argv"]
            code, out = assertions.run_argv(argv, repo_root)
            verdict = assertions.compare(item["op"], out, item.get("value"))
            if verdict.status != "PASS":
                failures.append(f"{' '.join(argv)[:60]} → {verdict.reason} (실제 {verdict.actual!r})")
        status = "PASS" if not failures else "FAIL"
        rows.append(baseline.classify(case.id, status, base, "; ".join(failures)))

    return rows, loaded, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="스킬 검증 환경")
    parser.add_argument("--check", action="store_true", help="보고만 한다 (기본)")
    parser.add_argument("--accept", action="store_true", help="지금 결과를 기준선으로 굳힌다")
    args = parser.parse_args()

    started = time.time()
    case_rows, loaded, case_errors = collect_cases(REPO_ROOT)
    rules = coupling.parse_claude_md(REPO_ROOT / "CLAUDE.md")
    lint_report = lint.run_lint(REPO_ROOT, rules, loaded, case_errors)

    if lint_report.must_refuse:
        print(report.render([], lint_report, time.time() - started))
        print("검사 단계에서 막혔습니다. 위 항목을 먼저 정리해주세요.")
        return 2

    rows = case_rows + collect_coupling(REPO_ROOT) + collect_pytest(REPO_ROOT)
    print(report.render(rows, lint_report, time.time() - started))

    if args.accept:
        unclassified = [row for row in rows if row.status in {"NEW", "FAIL", "PENDING"}]
        if unclassified:
            print(f"미분류 {len(unclassified)}건이 있어 기준선을 굳히지 않습니다.")
            print("각 항목을 회귀 또는 낡음으로 분류한 뒤 다시 실행해주세요.")
            return 3
        data = baseline.load_baseline(REPO_ROOT / "evals" / "baseline.json")
        for row in rows:
            data.setdefault("cases", {})[row.case_id] = {
                "verdict": row.verdict, "label": row.label or "confirmed",
                "reason": row.detail,
            }
        baseline.save_baseline(REPO_ROOT / "evals" / "baseline.json", data)
        print("기준선을 갱신했습니다.")
        return 0

    return 1 if baseline.has_blocking_failure(rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 실제로 한 번 돌려 현재 상태 확인**

```bash
python3 evals/run.py --check
```

Expected: 상태별 건수가 출력되고 30초 안에 끝난다. 결합 룰 실패가 보고서에 목록으로 뜬다.

- [ ] **Step 4: 실패 항목 분류 + 기준선 저작**

보고서의 실패·보류 항목을 하나씩 보고 회귀인지 낡음인지 정한다. 진짜 회귀는 고치고, 낡은 룰은 `CLAUDE.md` 를 갱신하거나 기준선에 `stale` 로 표시한다. 분류가 끝나면 굳힌다.

```bash
python3 evals/run.py --accept
```

Expected: 미분류가 0 이면 기준선이 갱신된다.

- [ ] **Step 5: `CLAUDE.md` 에 결합 메모 추가**

러너가 `CLAUDE.md` 를 파싱한다는 계약을 명시한다. 코드 블록 형식이나 `# expected:` 주석 형식을 바꾸면 러너가 조용히 0건을 매치하므로, 그 결합을 문서에 남긴다.

- [ ] **Step 6: Commit**

```bash
git add evals/ CLAUDE.md
git commit -m "feat(eval): 명령줄 진입점 + 첫 기준선"
```

---

## 2. 위험 코드 지점

설계서 §6 의 위험 분류를 1차 범위의 실제 위치에 대응시킨다.

- `evals/runner/assertions.py:run_shell_rule` — **side-effect**: `CLAUDE.md` 룰을 셸로 실행한다. 지금 116건은 전부 읽기 전용이지만 앞으로 누가 쓰기 명령을 넣으면 그대로 돈다 (설계서 R2b). mitigation: 같은 파일의 `check_read_only` 관문을 반드시 먼저 통과시킨다. 관문을 우회하는 호출 경로를 만들지 않는다.
- `evals/runner/guard.py:check_read_only` — **breaking**: 이 관문이 느슨하면 R2b 가 그대로 열리고, 너무 빡빡하면 정상 룰이 전부 차단되어 검사가 무의미해진다. mitigation: 실제 `CLAUDE.md` 116건을 넣었을 때 차단이 몇 건인지 Task 12 Step 3 에서 확인한다. 차단이 10건을 넘으면 관문이 과하다는 신호다.
- `evals/runner/assertions.py:run_shell_rule` — **breaking**: 셸을 `bash` 로 고정한다. 사용자 기본 셸(zsh)로 돌리면 매치 없는 글롭이 오류가 되어 같은 룰이 환경마다 다르게 동작한다. 이번 세션에서 실제로 두 번 발생했다. mitigation: `subprocess.run(["bash", "-c", ...])` 를 바꾸지 않는다.
- `evals/runner/coupling.py:parse_claude_md` — **breaking**: `CLAUDE.md` 의 코드 블록 형식이나 `# expected:` 주석 형식이 바뀌면 파싱이 조용히 0건을 매치한다 (설계서 R5). mitigation: Task 12 에서 `CLAUDE.md` 에 결합 메모를 남기고, 파싱된 룰 수가 직전 실행보다 줄면 경고한다. 절대값 검사는 쓰지 않는다 (설계서 D11).
- `scripts/tests/test_changelog_buffer.py:88-89` — **breaking**: 경로 하드코딩. 러너가 이 pytest 를 항상 전수로 돌리므로 여기가 깨지면 매 실행이 실패로 뜬다 (설계서 R3). mitigation: Task 3 에서 파일 위치 기준으로 바꾸고, 저장소 루트가 아닌 곳에서도 통과하는지 확인한다.
- `evals/runner/baseline.py:classify` — **side-effect**: 라벨 없는 항목을 통과로 처리하면 지금 실패 중인 진짜 회귀가 정답으로 박제된다 (요구사항 결정 8). mitigation: `NEW` 상태는 통과 집계에서 빼고, `--accept` 는 미분류가 하나라도 있으면 거부한다.
- `evals/run.py:main` — **race**: 실행 중 사용자가 같은 워크트리를 편집하면 결합 검사 결과가 중간 상태를 반영한다 (설계서 R8). mitigation: 1차는 격리 사본을 안 쓰므로 이 위험이 남는다. 실행이 30초라 노출 창이 짧다는 점에 기대고, 격리는 2차에서 붙인다. 실행 시작·종료 시 `git rev-parse HEAD` 를 기록해 다르면 보고에 표시한다.

## 3. 롤백 전략

- **코드**: 각 task 가 독립 커밋이라 `git revert <SHA>` 로 개별 되돌리기가 된다. `evals/` 는 신규 디렉토리라 통째로 지워도 기존 동작에 영향이 없다.
- **이동한 파일**: Task 2 의 `git mv` 는 `git mv tests/eval-fixtures/H23-e2e commands/audit-risk-tests` 로 되돌린다.
- **설정 파일**: Task 4, 5 는 각각 한 줄 단위 추가·교체라 revert 로 충분하다.
- **기준선**: `evals/baseline.json` 은 커밋 대상이라 이력이 남는다. 잘못 굳혔으면 이전 커밋의 파일로 되돌린 뒤 다시 분류한다.
- **되돌릴 수 없는 것**: 없다. 1차는 원본 저장소를 읽기만 하고, 유일한 쓰기가 `evals/` 신규 파일과 위 네 파일의 한 줄 단위 수정이다.

---

## 변경이력

<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-15 14:30] [구현계획서-수정]
- **id**: CH-20260815-005
- **이유**: 신규 구현계획서. 1차 범위(결합 검사 + 산출물 정적 검사 + 기존 pytest)를 12 task 로 분해
- **무엇이**: skill-eval-harness-implementation-plan.md 전체 (§1 Task 1~12 / §2 위험 코드 지점 7건 / §3 롤백 전략)
- **영향범위**: 없음 (최초 생성). `plan_byte_check` 통과 — 원본 블록 4개가 실제 파일과 바이트 일치. 검증 단계에서 `evals/tests/__init__.py` 와 `evals/conftest.py` 누락을 발견해 Task 6 에 추가함 (Task 3 이 고치는 것과 같은 종류의 경로 의존 버그를 새로 만들 뻔함)
- **연관 항목**: CH-20260815-003, CH-20260815-004

### [2026-08-15 15:02] [코드-수정] (batch: tasks 1..12)
- **id**: CH-20260815-007
- **이유**: 1차 범위 전체 실행 — 비용 0 층위 검증 환경 완성
- **무엇이**: evals/ 신규 (run.py + runner 6모듈 + 케이스 2 + 기준선 + 라벨), commands/audit-risk-tests → tests/eval-fixtures/H23-e2e 이동, scripts/tests/test_changelog_buffer.py 경로 수정, .gitignore, requirements-dev.txt, docs/testing.md, CLAUDE.md 결합 메모, 사전실측-노트.md
- **영향범위**: 스킬·커맨드 본문 변경 0 (검증 대상이지 수정 대상 아님). 기존 pytest 64함수 그대로 통과. 신규 테스트 116함수 추가
- **위험 카테고리**: side-effect, breaking
- **task별 세부 (12건)**:
  - Task 1: 사전 실측 — 세그먼트 35.3초 (설계 추정 120초의 3분의 1), 보조 에이전트 관측 필드 확정, `--plugin-dir` 이 설치본을 대체하지 않는다는 발견
  - Task 2: `commands/audit-risk-tests/` → `tests/eval-fixtures/H23-e2e/` 이동 (수용 기준 11 해소)
  - Task 3: fixture 경로를 실행 위치 비의존으로 (`breaking` 예방)
  - Task 4: `.gitignore` + `requirements-dev.txt`
  - Task 5: `docs/testing.md` 낡은 제약 2건 + 문제 해결 절 갱신
  - Task 6: 결합 룰 파서 — CLAUDE.md 86건 + fixture README 28건 = 114건
  - Task 7: 읽기 전용 관문 + 단언 실행기 (`side-effect` 방어 핵심)
  - Task 8: 케이스 로더 + 자산 미노출 케이스
  - Task 9: 검사 단계 — 모순 / 미등록 / 게이트 결손
  - Task 10~11: 기준선 대조 + 상태 분류 + 보고
  - Task 12: 명령줄 진입점 + 첫 기준선 + 이름 충돌 케이스 + CLAUDE.md 파싱 계약
- **연관 commits**: c0cd630..HEAD (5b69e5c cbaf0cc 9297df3 f8c8f56 436ca3e 40f90b3 c615526 1e11cf6 74ea9c0 46d70e2 e64c45f c631452 )
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260815-005, CH-20260815-006

### [2026-08-15 15:02] [검증] (task: 1차 전체)
- **id**: CH-20260815-008
- **이유**: 1차 수용 기준 충족 확인 + 회귀 검출 능력 실증
- **무엇이**: 기존 pytest 64함수 / 신규 테스트 116함수 / 결합 룰 114건 / 정적 케이스 2건 / 회귀 주입 실험 1회
- **결과**: PASS — 전체 실행 3초, 종료 코드 0. 회귀 주입(커맨드 이름 충돌 재현) 시 "새로 깨짐 1" 검출 후 복구 확인. 수용 기준 2(30분 이내) 는 3초로 크게 충족, 기준 3(결합+pytest 항상 전수) 충족, 기준 5(건너뛴 항목 명시) 충족, 기준 6(회귀 구분) 실증, 기준 8·11 충족. 기준 1·4·9 는 2차 대상
- **연관 commit**: 5b69e5c
