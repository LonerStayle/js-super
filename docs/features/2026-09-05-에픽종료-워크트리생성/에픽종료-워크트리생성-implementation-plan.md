---
commit_policy: per-task
---

# 에픽 종료 워크트리 생성 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 큰 작업 파트의 실행이 끝나면 에픽 파일을 갱신·커밋하고 다음 파트 워크트리를 만든 뒤, 새 세션이 인사하면 인수인계를 보내 곧바로 다음 브레인스토밍이 시작되게 한다.

**Architecture:** 마무리 절차는 새 스킬 `epic-close` 하나에 모으고, 실행이 끝나는 자리 (마무리 스킬 `finishing-a-development-branch`, 수동 커맨드 `/epic-next`) 가 그 스킬을 이름으로 부른다. 자식 쪽은 커맨드 `/epic-handoff` 하나가 부모를 찾아 인사하고 인수인계를 받아 브레인스토밍을 시작한다. 이름·경로 계산은 새 스크립트 `scripts/epic_chain.py` 가 결정적으로 한다. 브레인스토밍 스킬에 있던 마무리 단계는 빠진다.

**Tech Stack:** Markdown 스킬·커맨드 본문, Python 3 표준 라이브러리 (`scripts/epic_chain.py`), pytest, git worktree, Claude Code `ListAgents` / `SendMessage` / `AskUserQuestion` 도구

**Spec inputs:**
- 에픽종료-워크트리생성-requirements.md — 요구 1~16 (발동 조건·시점, 마무리 순서, 이름 규칙, 세션 인수인계, 미추적 복사, 단발성 비적용, 잘린 부분 정리)
- 에픽종료-워크트리생성-tech-design.md — §1 구성 요소 ①~⑩ 와 단계 표, §3 이번 파트 판별 / 다음 파트 선택 / 복사 대상 / 메시지 형식, §4 세션 찾기·부모 무응답·다른 하네스, §5 결정 1~7

---

## 1. 단계별 작업

### Task 1: 에픽 사슬 스크립트 (`scripts/epic_chain.py`)

**Files:**
- Create: `scripts/epic_chain.py`
- Test: `scripts/tests/test_epic_chain.py`

**Model**: sonnet

**검증**: `parse_part` 가 규칙에 맞는 브랜치에서 (에픽 이름, 번호) 를, 맞지 않는 브랜치에서 (브랜치 자신, 1) 을 돌려주고, `next_branch_name('결제__ep_part2_환불','정산')` 이 `결제__ep_part3_정산`, `next_branch_name('결제','환불 처리')` 가 `결제__ep_part2_환불-처리` 이며 작업명의 `__` 와 `/` 가 하이픈으로 바뀐다. `untracked_paths` 는 임시 git 저장소에서 커밋된 경로를 빼고 무시된 경로와 미추적 경로만 돌려주며 존재하지 않는 경로는 뺀다. `latest_member_feature` 는 주어진 이름들 중 mtime 이 가장 큰 파일을 가진 폴더 이름을 고르고 (소속 여부는 보지 않는다) 폴더가 없으면 None 을 돌려준다. `python3 scripts/epic_chain.py next 결제 정산` 이 이름을 출력한다.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계가 테스트 코드를 직접 작성한다.

Run: `source .venv/bin/activate && pytest scripts/tests/test_epic_chain.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 2: 스크립트 작성**

**수정 후** (new file: `scripts/epic_chain.py`):
```python
"""에픽 파트 사슬 — 브랜치 이름과 워크트리 경로를 다루는 결정적 계산.

epic-close 스킬이 부른다. 표준 라이브러리만 쓰고 저장소를 고치지 않는다.
브랜치 이름 규칙:  <에픽 워크트리 이름>__ep_part<번호>_<작업명>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

PART_SEP = "__ep_part"
_PART_RE = re.compile(r"^(?P<epic>.+?)__ep_part(?P<num>\d+)_(?P<topic>.+)$")


def parse_part(branch: str) -> tuple[str, int]:
    """브랜치 이름에서 (에픽 워크트리 이름, 파트 번호) 를 읽는다.

    규칙에 맞지 않으면 그 브랜치 자체가 첫 파트다 — (branch, 1).
    """
    match = _PART_RE.match(branch)
    if not match:
        return branch, 1
    return match.group("epic"), int(match.group("num"))


def topic_slug(topic: str) -> str:
    """작업명을 브랜치에 넣을 수 있는 꼴로 만든다.

    공백은 하이픈으로. 구분자로 예약된 `__` 와 폴더를 중첩시키는 `/` 는 하이픈으로.
    앞뒤 하이픈은 지운다.
    """
    text = topic.strip().replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"_{2,}", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def next_branch_name(current_branch: str, topic: str) -> str:
    """현재 브랜치에서 다음 파트의 브랜치 이름을 만든다."""
    epic, num = parse_part(current_branch)
    return f"{epic}{PART_SEP}{num + 1}_{topic_slug(topic)}"


def is_tracked(repo_root: Path, rel_path: str) -> bool:
    """경로가 git 에 추적되는지 본다. ls-files 가 비면 미추적이다 (무시 목록 여부와 무관)."""
    result = subprocess.run(
        ["git", "ls-files", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def untracked_paths(repo_root: Path, rel_paths: list[str]) -> list[str]:
    """존재하지만 git 이 추적하지 않는 경로만 돌려준다. 자식 워크트리로 복사할 대상이다."""
    found = []
    for rel in rel_paths:
        if (repo_root / rel).exists() and not is_tracked(repo_root, rel):
            found.append(rel)
    return found


def latest_member_feature(features_dir: Path, member_names: list[str]) -> Optional[str]:
    """주어진 폴더 이름들 중 파일이 가장 최근에 수정된 폴더 이름을 고른다. 소속 판정은 부르는 쪽이 한다."""
    best_name: Optional[str] = None
    best_mtime = -1.0
    for name in member_names:
        folder = features_dir / name
        if not folder.is_dir():
            continue
        mtimes = [p.stat().st_mtime for p in folder.rglob("*") if p.is_file()]
        mtime = max(mtimes) if mtimes else folder.stat().st_mtime
        if mtime > best_mtime:
            best_name, best_mtime = name, mtime
    return best_name


USAGE = """사용법:
  epic_chain.py parse <현재 브랜치>
  epic_chain.py next <현재 브랜치> <작업명>
  epic_chain.py untracked <저장소 루트> <경로>...
  epic_chain.py latest <features 폴더> <피처 폴더 이름>..."""


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(USAGE)
        return 2
    cmd = argv[1]
    if cmd == "parse" and len(argv) == 3:
        epic, num = parse_part(argv[2])
        print(json.dumps({"epic": epic, "part": num}, ensure_ascii=False))
        return 0
    if cmd == "next" and len(argv) == 4:
        print(next_branch_name(argv[2], argv[3]))
        return 0
    if cmd == "untracked" and len(argv) >= 4:
        print(json.dumps(untracked_paths(Path(argv[2]), argv[3:]), ensure_ascii=False))
        return 0
    if cmd == "latest" and len(argv) >= 4:
        print(latest_member_feature(Path(argv[2]), argv[3:]) or "")
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `source .venv/bin/activate && pytest scripts/tests/test_epic_chain.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/epic_chain.py scripts/tests/test_epic_chain.py
git commit -m "feat(epic): 에픽 사슬 스크립트 — 브랜치 파싱 · 다음 이름 · 미추적 경로 · 최근 피처"
```

### Task 2: `epic-close` 스킬 신설

**Files:**
- Create: `skills/epic-close/SKILL.md`

**Model**: sonnet

**검증**: 파일이 frontmatter (`name: epic-close`, 진입 제약이 든 description) 로 시작하고, 단계 표 8행 (이번 파트 판별 · 발동 검사 · 갱신 · 갱신 커밋 · 선택 · 생성 · 안내 · 인사 대기) 이 있으며, `grep -c "git add -A"` 가 2 (Step 2 금지 문장 + Anti-Pattern 행), `grep -c "forecast.md"` 가 1 이상, `grep -c "js-super:setting-up-worktrees"` 가 1, `grep -c "에픽 파트 인수인계 요청"` 이 1, `grep -c "에픽 파트 인수인계 —"` 가 1 이다.

- [ ] **Step 1: 검증 grep 이 FAIL 함을 확인 (파일 없음)**

Run: `test -f skills/epic-close/SKILL.md && echo EXISTS || echo MISSING`
Expected: MISSING

- [ ] **Step 2: 스킬 본문 작성**

**수정 후** (new file: `skills/epic-close/SKILL.md`):
````markdown
---
name: epic-close
description: 커맨드 /epic-next 또는 finishing-a-development-branch 의 명시 invoke 로만 진입 — 자유 요청에서 자동 선택 금지. 큰 작업(에픽) 파트 마무리 — 에픽 파일 갱신·커밋 → 다음 파트 선택 → 다음 파트 워크트리 생성 → 자식 세션 인수인계 대기. 진행 중 에픽이 없거나 소속 표식이 없으면 아무 출력 없이 돌아간다.
---

# Epic Close — 파트 마무리와 다음 파트 워크트리

큰 작업 (에픽) 은 파트의 사슬이다. 한 파트의 실행이 끝나면 이 스킬이 에픽 파일을 갱신해 커밋하고, 다음 파트를 고르고, 그 워크트리를 만들고, 새 세션이 인사하면 인수인계를 보낸다. 사슬은 앞으로만 간다 — 되돌려 합치는 단계는 없고 형제 파트를 동시에 만들지 않는다.

**Announce at start (에픽이 있을 때만):** "큰 작업 <이름> 의 파트 마무리를 시작합니다."

## 진입 계약

| 부르는 곳 | 시점 | 인자 |
|---|---|---|
| `finishing-a-development-branch` Step 3 | 실행 스킬 (인라인 / 보조 에이전트) 이 끝난 뒤 | 없음 |
| `/epic-next` | 사용자가 직접. 2개 문서 트랙처럼 실행 스킬 밖에서 구현한 파트 | 선택: 피처 폴더 경로 |

자유 요청에서 자동 선택하지 않는다. 사용자에게 묻는 일은 모두 `AskUserQuestion` 으로 한다.

## 단계

| 단계 | 하는 일 |
|---|---|
| 이번 파트 판별 | 어느 피처가 방금 끝난 파트인지 정한다 |
| 발동 검사 | 진행 중 에픽과 소속 표식이 없으면 아무 출력 없이 돌아간다 |
| 갱신 | 큰 그림 갱신 판정 · 이월 항목 기록 · 예상 빗나감 판정 |
| 갱신 커밋 | 에픽 폴더의 파일만 명시해 커밋한다 |
| 선택 | 갱신된 큰 그림의 착수 가능 목록에서 다음 파트 하나를 고른다 |
| 생성 | 이름을 확정하고 워크트리를 만든 뒤 git 이 추적하지 않는 문서를 복사한다 |
| 안내 | 새 세션 열기 · 이름 관례 · `/epic-handoff` 실행을 안내한다 |
| 인사 대기 | 턴을 마친다. 자식의 인사가 오면 인수인계를 보낸다 |

## 스크립트 위치

```bash
E=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/js-super/*/scripts/epic_scan.py" 2>/dev/null | sort -V | tail -1); [ -f "$E" ] || E=scripts/epic_scan.py
C=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/js-super/*/scripts/epic_chain.py" 2>/dev/null | sort -V | tail -1); [ -f "$C" ] || C=scripts/epic_chain.py
test -f "$E" && test -f "$C" && echo "OK $E $C" || echo "SCRIPT_ABSENT"
```

`${CLAUDE_PLUGIN_ROOT}` 는 쓰지 않는다 — Bash 도구 환경에서 채워지지 않는다.

스크립트를 찾기 전에 `test -d docs/epics` 를 먼저 본다. 폴더가 없으면 에픽이 없는 프로젝트이므로 **아무 출력 없이** 스킬을 끝낸다 (스크립트 유무와 무관). 폴더는 있는데 출력이 `SCRIPT_ABSENT` 면 "에픽 스크립트를 찾을 수 없습니다. 플러그인 설치를 확인해주세요." 한 줄을 내고 끝낸다 — 에픽이 있을 수 있는데 판정할 수 없는 상태라 이때만 조용히 지나가지 않는다.

## Process (detail)

### Step 0 — 이번 파트 판별 + 발동 검사

```bash
python3 "$E" docs
```

- `epic` 이 `null` 이면 **아무 출력 없이** 스킬을 끝낸다. 단발성 피처의 실행 종료 메시지는 지금과 똑같아야 한다
- **이번 파트 결정** — 인자로 피처 폴더가 왔으면 그 폴더. 없으면 `docs/features/` 의 **모든** 폴더 이름을 넘겨 파일이 가장 최근에 수정된 폴더를 고른다 (방금 실행이 끝난 피처는 계획서 변경이력이 막 갱신돼 항상 가장 최근이다):

```bash
python3 "$C" latest docs/features $(ls docs/features)
```

- **소속 검사** — 고른 폴더 이름이 스캔 결과의 `members` 에 없으면 (소속 표식이 없는 피처) **아무 출력 없이** 끝낸다. 인자로 온 폴더도 같은 검사를 거친다. 소속 표식이 있는 다른 피처가 저장소에 있어도 그쪽으로 옮겨 가지 않는다 — 방금 끝난 것이 단발성 피처면 에픽 마무리는 일어나지 않는다
- 통과했으면 한 줄 알린다: "이번 파트: docs/features/<폴더>". 다른 폴더가 맞으면 `/epic-next <폴더>` 로 다시 부르라고 덧붙인다
- `active_count` 가 2 이상이면 큰 그림을 가장 최근에 고친 에픽을 쓴다는 사실을 한 줄 알린다
- 현재 파트 번호는 브랜치에서 읽는다: `python3 "$C" parse "$(git rev-parse --abbrev-ref HEAD)"`. 규칙에 맞지 않는 브랜치면 그 브랜치가 첫 파트 (번호 1) 다

### Step 1 — 갱신

`docs/epics/<에픽 폴더>/` 의 세 파일을 읽고 셋을 차례로 한다. 판단 근거는 이번 파트의 대화와 피처 문서 (요구사항 · 기술설계 · 구현계획서의 변경이력) 다.

- **큰 그림 갱신 판정** — 항목이 없어졌거나 새로 생겼거나 순서가 뒤집혔을 때만 `overview.md` 를 고쳐 쓴다. 표현을 다듬는 수정은 하지 않는다. 방금 끝낸 파트가 "지금 착수 가능" 에 있으면 그 항목은 없어진 것이다 — 빼고 "정해진 것" 에 옮긴다. 목록에 없으면 그 이유로 파일을 건드리지 않는다. 항목 변화가 하나도 없으면 파일을 건드리지 않고 "큰 그림 변경 없음" 한 줄만 알린다
- **이월 항목 기록** — 이번 파트에서 미룬 것 · 주의사항 · 기각한 안 · 유보를 목록으로 보여주고 `AskUserQuestion` (multiSelect) 으로 남길 것을 고르게 한 뒤 `carry-over.md` 끝에 붙인다. 종류와 나온 곳을 함께 적는다. 후보가 없으면 건너뛴다
- **예상 빗나감 판정** — 예상이 빗나갔을 때만 `forecast.md` 끝에 새 시점 블록을 붙인다. 무엇이 어떻게 빗나갔는지와 근거를 함께 적고, 근거를 적을 수 없으면 기록하지 않는다

### Step 2 — 갱신 커밋

```bash
git status --porcelain -- docs/epics/<에픽 폴더>
```

- 출력이 있으면 그 폴더만 담아 커밋한다. `git add -A` 를 쓰지 않는다:

```bash
git add docs/epics/<에픽 폴더> && git commit -m "epic(<에픽 폴더>): part<N> 마무리 — 큰 그림 갱신"
```

- 출력이 없으면 (바뀐 게 없거나 폴더가 git 에 무시돼 있음) 커밋하지 않고 "에픽 파일 커밋 없음" 한 줄을 알린다. 무시된 폴더는 Step 4 의 복사가 나른다
- 이 커밋이 자식이 최신 큰 그림을 물려받는 유일한 경로다. 커밋 전에 워크트리를 만들지 않는다

### Step 3 — 선택

`overview.md` 의 "지금 착수 가능" 목록이 입력이다. **`forecast.md` 는 열지 않는다.** 목록에서 하나를 추천하고 이유를 먼저 말한 뒤 `AskUserQuestion` 으로 묻는다.

옵션 순서: 추천 파트 (첫 번째) / 착수 가능 목록의 나머지 항목 / "지금은 안 만듦" / "에픽 완료". 착수 가능 목록이 비어 있으면 뒤의 둘만 준다.

| 선택 | 그 뒤 |
|---|---|
| 파트 하나 | Step 4 로 |
| 지금은 안 만듦 | "나중에 `/epic-next` 로 이어갈 수 있습니다" 한 줄을 내고 끝낸다 |
| 에픽 완료 | `overview.md` 의 상태 줄을 `> **상태**: 완료` 로 바꾸고 그 파일만 커밋한 뒤 끝낸다 (`/epic done` 과 같다) |

### Step 4 — 생성

**이름 확정.** 규칙대로 이름을 만든다:

```bash
BR=$(git rev-parse --abbrev-ref HEAD); python3 "$C" next "$BR" "<다음 파트 작업명>"
```

결과 (`<에픽 워크트리 이름>__ep_part<N+1>_<작업명>`) 를 보여주고 `AskUserQuestion` 으로 "이 이름으로" 또는 직접 입력 (Other) 을 받는다. 직접 입력한 이름은 그대로 쓴다.

**워크트리 생성.** `js-super:setting-up-worktrees` 스킬을 Skill 도구로 부르되 인자에 확정한 이름을 넣는다 (예: `<이름> 워크트리 만들어줘`). 그 스킬이 현재 HEAD 에서 분기하고, 부모 브랜치를 git config 에 기록하고, 환경 파일과 메모리 심링크를 처리한다. 작업 트리가 dirty 면 그 스킬의 dirty 게이트가 묻는다.

**미추적 문서 복사.** 워크트리가 생기면:

```bash
python3 "$C" untracked . docs/epics/<에픽 폴더> docs/features/<이번 파트 폴더>
```

결과 목록의 경로마다 자식 워크트리의 같은 위치로 복사한다 (`mkdir -p "<자식>/<상위 폴더>"` 뒤 `cp -R`). 자식 쪽에 그 경로가 이미 있으면 복사하지 않고 알린다. 목록이 비어 있으면 (둘 다 추적 중) 아무것도 하지 않는다.

### Step 5 — 안내

`ListAgents` 를 한 번 부른다. 첫 줄 "This session is <이름>" 이 이 세션의 이름이다. 그 이름에 현재 브랜치 이름이 들어 있지 않으면 마지막 줄에 `/rename` 을 권한다.

안내문의 `<접두어>` 는 이 세션 이름에서 현재 브랜치 이름 앞에 붙어 있는 부분이다 (예: 세션 이름이 `js수퍼-결제` 이고 브랜치가 `결제` 면 접두어는 `js수퍼`). 이 세션 이름에 브랜치가 안 들어 있으면 저장소 폴더 이름을 접두어로 쓴다. 안내문에는 계산한 값을 채워 넣는다 — `<접두어>` 를 글자 그대로 출력하지 않는다.

출력 (완전 문장):

```
다음 파트 워크트리를 만들었습니다.
- 경로: <자식 워크트리 경로>
- 브랜치: <자식 브랜치> (부모: <현재 브랜치>)

이어서 할 일:
1. 새 터미널에서 그 경로로 들어가 세션을 엽니다.
2. 세션 이름에 워크트리 이름을 넣습니다. 예: /rename <접두어>-<자식 브랜치>
3. 그 세션에서 /epic-handoff 를 실행합니다. 이 세션이 인수인계를 보냅니다.

이 세션의 이름은 "<이 세션 이름>" 입니다.
```

이름에 브랜치가 안 들어 있으면 한 줄 더: "자식이 이 세션을 찾을 수 있게 `/rename <접두어>-<현재 브랜치>` 로 바꿔주세요."

### Step 6 — 인사 대기와 인수인계

턴을 마친다. 아무것도 더 보내지 않는다. `ListAgents` 를 반복해서 부르지 않는다.

`<cross-session-message>` 가 도착하고 첫 줄이 `에픽 파트 인수인계 요청` 으로 시작하면, 그 메시지의 `세션 이름` 을 받는 쪽으로 `SendMessage` 를 한 번 보낸다. 내용은 대화와 피처 문서에서 모은다. 대화가 압축돼 있으면 기술설계의 결정·위험 섹션과 구현계획서의 변경이력에서 다시 모은다.

```
에픽 파트 인수인계 — 다음 파트: <주제>
## 다음 파트
<주제와 고른 이유>
## 이번 파트에서 정한 것
<결정 · 버린 안 · 실행 중 알게 된 함정>
## 읽을 파일
- docs/epics/<에픽 폴더>/overview.md
- docs/epics/<에픽 폴더>/carry-over.md
- docs/features/<이번 파트 폴더>/
## 부모 브랜치
<현재 브랜치>
```

에픽 파일의 본문을 어느 칸에도 복사하지 않는다. `forecast.md` 는 목록에 넣지 않는다. 인사가 오기 전에는 보내지 않는다.

## 다른 하네스

`ListAgents` / `SendMessage` 도구가 없으면 Step 5 에서 `ListAgents` 호출과 세션 이름 관련 줄 (2번 항목, "이 세션의 이름은" 줄, `/rename` 권고) 을 모두 빼고, 경로·브랜치와 1번 항목만 낸 뒤 "이 환경은 세션 간 인수인계를 지원하지 않습니다. 새 세션에서 `/brainstorm <주제>` 로 시작하세요." 를 붙인다. Step 6 은 건너뛴다. Step 0~4 는 그대로 돈다.

## Anti-Patterns

| 금지 | 이유 |
|---|---|
| 에픽이 없을 때 "진행 중인 큰 작업이 없습니다" 출력 | 단발성 피처마다 노이즈. 아무 출력 없이 돌아간다 |
| 커밋 전에 워크트리 생성 | 자식이 옛 큰 그림을 물려받는다 |
| `git add -A` | 실행이 남긴 무관한 파일이 에픽 커밋에 섞인다 |
| 형제 워크트리를 여럿 생성 | 항상 하나. 병렬 실험은 자식 세션에서 다시 갈라낸다 |
| 선택 단계에서 `forecast.md` 읽기 | 다음 주제가 예상을 따라간다 |
| 인수인계에 에픽 파일 본문 복사 | 파일이 정본. 사본이 낡는다 |
| 인사 전에 인수인계 전송 / `ListAgents` 반복 확인 | 자식이 언제 뜨는지 부모는 모른다. 도구 계약이 반복 확인을 금지한다 |
| 확정 질문 없이 이름 변경 | 확정 질문을 거친 이름만 쓴다. 사용자 직접 입력은 그대로 |

## Related Skills

- `finishing-a-development-branch` — Step 3 에서 이 스킬을 부른다
- `setting-up-worktrees` — 워크트리 생성과 부모 기록
- `brainstorming` — 자식 세션이 인수인계를 받은 뒤 시작하는 스킬 (시작 단계가 에픽 파일을 읽는다)
````

- [ ] **Step 3: 검증 grep 통과 확인**

Run: `grep -c "git add -A" skills/epic-close/SKILL.md; grep -c "forecast.md" skills/epic-close/SKILL.md; grep -c "js-super:setting-up-worktrees" skills/epic-close/SKILL.md; grep -c "에픽 파트 인수인계 요청" skills/epic-close/SKILL.md; grep -c "에픽 파트 인수인계 —" skills/epic-close/SKILL.md`
Expected: `2` / `4` 이상 / `1` / `1` / `1`

- [ ] **Step 4: Commit**

```bash
git add skills/epic-close/SKILL.md
git commit -m "feat(epic): epic-close 스킬 — 파트 마무리 · 다음 파트 워크트리 · 인수인계 대기"
```

### Task 3: `/epic-next` 커맨드 신설

**Files:**
- Create: `commands/epic-next.md`

**Model**: sonnet

**검증**: 파일이 `disable-model-invocation: true` 를 갖고 `js-super:epic-close` 를 정확히 한 번 언급하며, `skills/epic-next/` 디렉토리가 없다 (커맨드 ↔ 스킬 이름 충돌 없음).

- [ ] **Step 1: 파일 부재 확인**

Run: `test -f commands/epic-next.md && echo EXISTS || echo MISSING`
Expected: MISSING

- [ ] **Step 2: 커맨드 작성**

**수정 후** (new file: `commands/epic-next.md`):
```markdown
---
description: 큰 작업(에픽)의 현재 파트를 마무리하고 다음 파트 워크트리를 만듭니다. 구현계획서 없이 구현한 파트나 실행 스킬 밖에서 끝낸 파트에서 직접 부릅니다.
disable-model-invocation: true
---

# /epic-next — 파트 마무리와 다음 파트 워크트리

실행 스킬 (`/execute-plan`, 보조 에이전트 실행) 로 끝낸 파트는 마무리 스킬이 이 절차를 자동으로 부릅니다. 이 커맨드는 그 밖의 경우를 위한 문입니다.

| 경우 | 예 |
|---|---|
| 구현계획서 없이 직접 구현한 파트 | 기술설계에서 2개 문서로 확정한 피처 |
| 실행이 끊겼다가 나중에 마무리하는 파트 | 세션이 중간에 닫힌 경우 |
| 선택 단계에서 "지금은 안 만듦" 을 고른 뒤 이어가는 경우 | 다음 날 이어서 |

## 인자

선택. 피처 폴더 경로 (예: `docs/features/2026-09-05-환불/`). 없으면 소속 피처 중 가장 최근에 수정된 폴더를 고르고 그 사실을 알립니다.

## 하는 일

`js-super:epic-close` 스킬을 Skill 도구로 부릅니다. 인자가 있으면 그대로 넘깁니다. 절차 (갱신 → 갱신 커밋 → 선택 → 생성 → 안내 → 인사 대기) 는 그 스킬이 합니다.

스킬이 "진행 중인 큰 작업이 없다" 고 조용히 돌아오면, 사용자가 직접 부른 커맨드이므로 한 줄 알립니다.

> 진행 중인 큰 작업이 없거나 이 피처에 소속 표식이 없습니다. `/epic` 으로 큰 작업을 만들거나 요구사항 문서 머리에 `> **큰 작업**: <폴더명>` 을 넣어주세요.

## 하지 않는 것

- 테스트를 돌리지 않습니다. 실행 스킬 밖에서 구현했다면 테스트는 직접 확인합니다
- 형제 워크트리를 여럿 만들지 않습니다
- 되돌려 합치지 않습니다
```

- [ ] **Step 3: 검증**

Run: `grep -c "disable-model-invocation: true" commands/epic-next.md; grep -c "js-super:epic-close" commands/epic-next.md; test ! -d skills/epic-next && echo NO_COLLISION`
Expected: `1` / `1` / `NO_COLLISION`

- [ ] **Step 4: Commit**

```bash
git add commands/epic-next.md
git commit -m "feat(epic): /epic-next 커맨드 — 파트 마무리 수동 진입"
```

### Task 4: `/epic-handoff` 커맨드 신설

**Files:**
- Create: `commands/epic-handoff.md`

**Model**: sonnet

**검증**: 파일이 `disable-model-invocation: true` 를 갖고, `js-super-parent` 로 부모를 읽는 bash 한 줄과 인사 메시지 템플릿 (첫 줄 `에픽 파트 인수인계 요청`) 이 있으며, `js-super:brainstorming` 호출과 "그냥 시작" 대체 경로가 각 1회 이상 언급되고, `skills/epic-handoff/` 디렉토리가 없다.

- [ ] **Step 1: 파일 부재 확인**

Run: `test -f commands/epic-handoff.md && echo EXISTS || echo MISSING`
Expected: MISSING

- [ ] **Step 2: 커맨드 작성**

**수정 후** (new file: `commands/epic-handoff.md`):
````markdown
---
description: 에픽 파트 워크트리에서 연 새 세션이 부모 세션에 인사를 보내고 인수인계를 받아 다음 파트 브레인스토밍을 시작합니다.
disable-model-invocation: true
---

# /epic-handoff — 인수인계 받고 다음 파트 시작

부모 세션이 파트를 마무리하며 이 워크트리를 만들었을 때, 새 세션에서 한 번 실행합니다. 이 커맨드가 부모를 찾아 인사하고, 인수인계가 오면 브레인스토밍을 시작합니다.

## 1. 워크트리와 부모 확인

```bash
BR=$(git rev-parse --abbrev-ref HEAD); P=$(git config "branch.$BR.js-super-parent" 2>/dev/null); echo "branch=$BR"; echo "parent=${P:-NONE}"
```

`parent=NONE` 이면 멈추고 알립니다.

> 이 브랜치에는 부모 기록이 없습니다. 파트 마무리로 만든 워크트리에서 실행해주세요.

## 2. 자기 이름과 부모 세션 찾기

`ListAgents` 를 한 번 부릅니다.

- 첫 줄 "This session is <이름>" 이 이 세션의 이름입니다.
- 목록에서 이름에 `<parent>` 가 들어 있는 행을 고릅니다.

| 결과 | 처리 |
|---|---|
| 정확히 하나 | 그 행 |
| 여럿 | 이름 끝이 `<parent>` 로 끝나는 행으로 좁힙니다. 그래도 하나가 아니면 후보를 `AskUserQuestion` 으로 고르게 합니다 |
| 없음 | "부모 세션 <parent> 을 찾지 못했습니다. 부모 세션 이름에 브랜치 이름이 들어 있는지 확인해주세요." 를 내고 `AskUserQuestion` 으로 묻습니다: "인수인계 없이 시작" / "중단" |

`ListAgents` 도구가 없는 환경이면 "이 환경은 세션 간 인수인계를 지원하지 않습니다." 를 내고 같은 질문을 합니다.

## 3. 인사 보내기

`SendMessage` 로 한 번 보냅니다. `to` 는 2 에서 고른 행의 이름입니다 (목록에 `[ref]` 가 붙어 있으면 함께).

```
에픽 파트 인수인계 요청 — <BR> 세션이 준비됐습니다
세션 이름: <이 세션 이름>
워크트리: <현재 경로>
브랜치: <BR> (부모: <parent>)
이 메시지를 받은 부모 세션은 SendMessage 로 위 세션 이름에 인수인계를 보내주세요.
내용은 다음 파트 주제와 이유 · 이번 파트의 결정과 버린 안과 함정 · 읽을 파일 경로 · 부모 브랜치 이름입니다.
```

## 4. 기다리기

출력하고 턴을 마칩니다.

> 부모 세션 <이름> 에 인사를 보냈습니다. 인수인계를 기다립니다. 오지 않으면 "그냥 시작" 이라고 입력해주세요.

시간을 재지 않습니다. `ListAgents` 를 반복해서 부르지 않습니다.

## 5. 인수인계가 오면

`<cross-session-message>` 의 첫 줄이 `에픽 파트 인수인계 —` 로 시작하면, "다음 파트" 아래의 주제를 꺼내 `js-super:brainstorming` 스킬을 Skill 도구로 부릅니다. 인자는 그 주제입니다. 결정과 함정은 대화에 있으므로 다시 넘기지 않습니다 — 브레인스토밍이 그 메시지를 읽습니다.

사용자가 "그냥 시작" 이라고 하거나 2 의 질문에서 "인수인계 없이 시작" 을 골랐으면, 인자 없이 `js-super:brainstorming` 을 부릅니다. 두 경우의 동작은 같습니다. 시작 단계가 워크트리의 에픽 파일을 읽고, 주제는 브레인스토밍이 묻습니다.

## 6. 하지 않는 것

- 인사를 두 번 보내지 않습니다
- 부모가 답하기 전에 브레인스토밍을 시작하지 않습니다 (사용자가 "그냥 시작" 이라고 했거나 "인수인계 없이 시작" 을 고른 경우만 예외)
- 에픽 파일이나 피처 문서를 고치지 않습니다
````

- [ ] **Step 3: 검증**

Run: `grep -c "disable-model-invocation: true" commands/epic-handoff.md; grep -c "js-super-parent" commands/epic-handoff.md; grep -c "에픽 파트 인수인계 요청" commands/epic-handoff.md; grep -c "js-super:brainstorming" commands/epic-handoff.md; grep -c "그냥 시작" commands/epic-handoff.md; test ! -d skills/epic-handoff && echo NO_COLLISION`
Expected: `1` / `1` / `1` / `2` / `2` 이상 / `NO_COLLISION`

- [ ] **Step 4: Commit**

```bash
git add commands/epic-handoff.md
git commit -m "feat(epic): /epic-handoff 커맨드 — 자식 세션 인사 · 인수인계 수신 · 브레인스토밍 시작"
```

### Task 5: 마무리 스킬이 epic-close 를 부른다

**Files:**
- Modify: `skills/finishing-a-development-branch/SKILL.md:48`

**Model**: sonnet

**검증**: Step 2 와 "Worktree Cleanup" 사이에 Step 3 이 생기고 `grep -c "js-super:epic-close"` 가 1 이다. Step 1·2 의 본문은 바이트 단위로 그대로다.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "js-super:epic-close" skills/finishing-a-development-branch/SKILL.md`
Expected: `0`

- [ ] **Step 2: Step 3 삽입**

**원본** (`skills/finishing-a-development-branch/SKILL.md:48`):
```markdown
## Worktree Cleanup (manual)
```

**수정 후**:
```markdown
### Step 3 — 큰 작업 파트 마무리 (에픽이 있을 때만)

Step 2 의 메시지를 낸 뒤 `js-super:epic-close` 스킬을 Skill 도구로 부른다. 진행 중인 큰 작업이 없거나 이번 피처의 요구사항 문서에 소속 표식이 없으면 그 스킬은 아무 출력 없이 돌아온다 — 단발성 피처의 종료 메시지는 지금과 똑같다. 에픽이 있으면 그 스킬이 에픽 파일 갱신, 다음 파트 선택, 워크트리 생성, 자식 세션 인수인계까지 이어간다.

## Worktree Cleanup (manual)
```

- [ ] **Step 3: 검증**

Run: `grep -c "js-super:epic-close" skills/finishing-a-development-branch/SKILL.md; grep -n "^### Step" skills/finishing-a-development-branch/SKILL.md`
Expected: `1` / Step 1, Step 2, Step 3 세 줄

- [ ] **Step 4: Commit**

```bash
git add skills/finishing-a-development-branch/SKILL.md
git commit -m "feat(epic): 마무리 스킬 끝에서 epic-close 호출"
```

### Task 6: 브레인스토밍 스킬 — 마무리 단계 제거 + 잘린 부분 복구

**Files:**
- Modify: `skills/brainstorming/SKILL.md:78-80`
- Modify: `skills/brainstorming/SKILL.md:162-164`
- Modify: `skills/brainstorming/SKILL.md:185-188`
- Modify: `skills/brainstorming/SKILL.md:249-260`
- Modify: `skills/brainstorming/SKILL.md:483`
- Modify: `skills/brainstorming/SKILL.md:487`
- Modify: `skills/brainstorming/SKILL.md:497-504`

**Model**: sonnet

**검증**: `grep -cE "^8\.5\. |큰 작업 갱신"` 이 0, `grep -c "^## Related Skills"` 가 1, `grep -c "### 인수인계 메시지로 진입했을 때"` 가 1, `grep -c "^0\.5\. "` 가 1 (시작 단계 유지) 이고, dot 흐름도에서 `Invoke change-history` 노드가 `Auto-invoke /design-tech` 노드로 직접 이어지며 선언 없는 노드를 가리키는 간선이 없다 (노드 이름 집합과 간선 양끝 집합 비교). 소속 표식 예시 블록이 복구돼 `grep -c "큰 작업\*\*: 2026-08-29-<큰 작업 슬러그>"` 가 1 이다.

파일 아래쪽부터 위로 고친다 (앞쪽 줄 번호가 밀리지 않게).

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -cE "^8\.5\. |큰 작업 갱신" skills/brainstorming/SKILL.md; grep -c "^## Related Skills" skills/brainstorming/SKILL.md`
Expected: `5` / `0`

- [ ] **Step 2: 큰 작업 맥락 섹션 꼬리 복구 (소속 표식 예시 · 인수인계 진입 · 마무리 위치 · 관련 스킬 헤더)**

**원본** (`skills/brainstorming/SKILL.md:497-504`):
```markdown
### 소속 표식을 남긴다

진행 중인 큰 작업이 있으면 이번 피처의 요구사항 문서 머리에 한 줄을 넣는다. 다음 단계 안내 인용 줄과 나란히 둔다.


- `tech-design` — next step (technical spec)
- `change-history` — first requirements entry
- `change-propagation` — when the requirements doc is later edited, cascades to downstream MDs
```

**수정 후**:
````markdown
### 소속 표식을 남긴다

진행 중인 큰 작업이 있으면 이번 피처의 요구사항 문서 머리에 한 줄을 넣는다. 다음 단계 안내 인용 줄과 나란히 둔다.

```markdown
# 요구사항: <피처 이름>

> **큰 작업**: 2026-08-29-<큰 작업 슬러그>
> **다음 단계 안내**: ...
```

이 줄이 유일한 소속 근거다. 빠지면 그 피처는 상태 목록에서 조용히 사라지고, 파트 실행이 끝났을 때 `epic-close` 가 이 피처를 찾지 못한다. 형식을 바꾸면 `scripts/epic_scan.py` 와 `commands/epic.md` 를 함께 고쳐야 한다.

### 인수인계 메시지로 진입했을 때

`/epic-handoff` 가 부모 세션의 인수인계 메시지를 받고 이 스킬을 불렀으면, 그 메시지의 "다음 파트" 가 피처 주제이고 "이번 파트에서 정한 것" 이 커버 목록의 답이다. 그 내용을 다시 묻지 않는다. 시작 단계 (0.5) 는 그대로 돈다 — 에픽 파일은 워크트리에 있다.

### 마무리는 실행 끝에서

큰 그림 갱신 · 이월 항목 기록 · 예상 빗나감 판정은 이 스킬이 하지 않는다. 파트 실행이 끝난 뒤 `epic-close` 스킬 (마무리 스킬 `finishing-a-development-branch` 가 부르거나 `/epic-next` 로 직접) 이 한다. 요구사항 직후에 갱신하면 다음 파트가 앞 파트의 코드 없이 시작하고, 실행 중 나온 미룬 항목이 이월 노트에 안 남는다.

## Related Skills

- `tech-design` — next step (technical spec)
- `change-history` — first requirements entry
- `change-propagation` — when the requirements doc is later edited, cascades to downstream MDs
- `epic-close` — 파트 실행이 끝난 뒤의 에픽 갱신과 다음 파트 워크트리
````

- [ ] **Step 3: "있는지 확인" 문단 — 마무리 단계 언급 제거**

**원본** (`skills/brainstorming/SKILL.md:487`):
```markdown
`docs/epics/` 가 없거나 상태 줄이 `진행 중` 인 큰 그림이 하나도 없으면 시작 단계와 마무리 단계를 통째로 건너뛴다. 안내 문구도 출력하지 않는다. 큰 작업 없이 피처 하나만 만드는 기존 사용법이 지금과 똑같이 동작해야 한다.
```

**수정 후**:
```markdown
`docs/epics/` 가 없거나 상태 줄이 `진행 중` 인 큰 그림이 하나도 없으면 시작 단계를 통째로 건너뛴다. 안내 문구도 출력하지 않는다. 큰 작업 없이 피처 하나만 만드는 기존 사용법이 지금과 똑같이 동작해야 한다.
```

- [ ] **Step 4: 섹션 머리 문단 — "끝날 때 갱신한다" 교체**

**원본** (`skills/brainstorming/SKILL.md:483`):
```markdown
대화가 압축되면 앞에서 정한 것과 미룬 것이 요약에서 뭉개진다. 압축을 견디는 것은 파일뿐이라, 브레인스토밍은 시작할 때 이 파일들을 읽고 끝날 때 갱신한다.
```

**수정 후**:
```markdown
대화가 압축되면 앞에서 정한 것과 미룬 것이 요약에서 뭉개진다. 압축을 견디는 것은 파일뿐이라, 브레인스토밍은 시작할 때 이 파일들을 읽는다. 갱신은 파트 실행이 끝난 뒤 `epic-close` 가 한다.
```

- [ ] **Step 5: 절차 상세의 8.5 블록 제거**

**원본** (`skills/brainstorming/SKILL.md:249-260`):
```markdown

**8.5. 큰 작업 갱신**

큰 작업이 없으면 이 단계 전체를 건너뛴다. 있으면 셋을 차례로 한다.

- **큰 그림 갱신 판정** — 항목이 없어졌거나 새로 생겼거나 순서가 뒤집혔을 때만 고쳐 쓴다. 표현을 다듬는 수정은 하지 않는다. 바뀐 것이 없으면 파일을 건드리지 않고 "큰 그림 변경 없음" 한 줄만 알린다
- **이월 항목 기록** — 대화 중 모아둔 후보를 목록으로 보여주고 남길 것만 이월 노트 끝에 붙인다. 종류 (미룸 / 주의 / 기각 / 유보) 와 나온 곳을 함께 적는다
- **예상 빗나감 판정** — 예상이 빗나갔을 때만 예상도 끝에 새 시점 블록을 붙인다. 무엇이 어떻게 빗나갔는지와 그렇게 판단한 근거를 함께 적고, 근거를 적을 수 없으면 기록하지 않는다

착수 가능한 피처가 둘 이상이고 서로 건드리는 곳이 겹치지 않아 보이면 나란히 갈라내 동시에 진행하도록 제안한다. 판단 근거는 대화 내용이고, 코드를 뒤져 실제 충돌을 계산하지 않는다. 제안까지가 범위이고 워크트리는 만들지 않는다.

**9. Auto-proceed to tech-design (v1.1.9+ — no gate)**
```

**수정 후**:
```markdown

**9. Auto-proceed to tech-design (v1.1.9+ — no gate)**
```

- [ ] **Step 6: 흐름도 간선 — change-history 에서 design-tech 로 직결**

**원본** (`skills/brainstorming/SKILL.md:185-188`):
```dot
    "블록 4 — 승인\n초안 전체 한 번에" -> "Invoke change-history\n(first entry: 요구사항-수정)" [label="승인"];
    "Invoke change-history\n(first entry: 요구사항-수정)" -> "큰 작업 갱신\n(있을 때만)";
    "큰 작업 갱신\n(있을 때만)" -> "Auto-invoke /design-tech (no gate, v1.1.9+)";
    "Auto-invoke /design-tech (no gate, v1.1.9+)" -> "Auto-invoke tech-design skill" [label="continue"];
```

**수정 후**:
```dot
    "블록 4 — 승인\n초안 전체 한 번에" -> "Invoke change-history\n(first entry: 요구사항-수정)" [label="승인"];
    "Invoke change-history\n(first entry: 요구사항-수정)" -> "Auto-invoke /design-tech (no gate, v1.1.9+)";
    "Auto-invoke /design-tech (no gate, v1.1.9+)" -> "Auto-invoke tech-design skill" [label="continue"];
```

- [ ] **Step 7: 흐름도 노드 선언 — 큰 작업 갱신 노드 제거**

**원본** (`skills/brainstorming/SKILL.md:162-164`):
```dot
    "Invoke change-history\n(first entry: 요구사항-수정)" [shape=box];
    "큰 작업 갱신\n(있을 때만)" [shape=box];
    "Auto-invoke /design-tech (no gate, v1.1.9+)" [shape=box];
```

**수정 후**:
```dot
    "Invoke change-history\n(first entry: 요구사항-수정)" [shape=box];
    "Auto-invoke /design-tech (no gate, v1.1.9+)" [shape=box];
```

- [ ] **Step 8: Checklist — 8.5 항목 제거**

**원본** (`skills/brainstorming/SKILL.md:78-80`):
```markdown
8. **변경이력 기록** — append first `[요구사항-수정]` entry via `change-history` skill
8.5. **큰 작업 갱신** — 큰 작업이 있으면 큰 그림 갱신 판정 · 이월 항목 기록 · 예상 빗나감 판정을 수행한다. 바뀐 것이 없으면 파일을 고치지 않는다. "큰 작업 맥락" 섹션 참조.
9. **개발방향 단계 자동 진행** — Right after the change-history entry is logged, auto-invoke `tech-design` via the Skill tool with a one-line interrupt-notice. On user "stop"/"멈춰"/"잠깐" → exit cleanly with notice telling the user to run /design-tech later.
```

**수정 후**:
```markdown
8. **변경이력 기록** — append first `[요구사항-수정]` entry via `change-history` skill
9. **개발방향 단계 자동 진행** — Right after the change-history entry is logged, auto-invoke `tech-design` via the Skill tool with a one-line interrupt-notice. On user "stop"/"멈춰"/"잠깐" → exit cleanly with notice telling the user to run /design-tech later.
```

- [ ] **Step 9: 검증**

Run: `grep -cE "^8\.5\. |큰 작업 갱신" skills/brainstorming/SKILL.md; grep -c "^## Related Skills" skills/brainstorming/SKILL.md; grep -c "### 인수인계 메시지로 진입했을 때" skills/brainstorming/SKILL.md; grep -c "^0\.5\. " skills/brainstorming/SKILL.md; grep -c "큰 작업\*\*: 2026-08-29-<큰 작업 슬러그>" skills/brainstorming/SKILL.md`
Expected: `0` / `1` / `1` / `1` / `1`

Run (dot 노드·간선 짝 검사): `awk '/^```dot/{f=1;next} /^```/{f=0} f' skills/brainstorming/SKILL.md | python3 -c "import re,sys; t=sys.stdin.read(); decl=set(re.findall(r'^\s*\"([^\"]+)\"\s*\[shape', t, re.M)); used=set(re.findall(r'\"([^\"]+)\"\s*->', t))|set(re.findall(r'->\s*\"([^\"]+)\"', t)); print(sorted(used-decl))"`
Expected: `[]`

- [ ] **Step 10: Commit**

```bash
git add skills/brainstorming/SKILL.md
git commit -m "refactor(brainstorming): 에픽 마무리 단계를 epic-close 로 이동 + 잘린 섹션 복구"
```

### Task 7: 2개 확정 종료 안내와 /epic 안내 한 줄씩

**Files:**
- Modify: `skills/tech-design/SKILL.md:333`
- Modify: `commands/epic.md:144`

**Model**: sonnet

**검증**: `grep -c "/epic-next"` 가 `skills/tech-design/SKILL.md` 와 `commands/epic.md` 에서 각 1 이고, `commands/epic.md` 에 `/epic-handoff` 가 1회 있다. 두 파일의 다른 줄은 바이트 단위로 그대로다.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "/epic-next" skills/tech-design/SKILL.md commands/epic.md`
Expected: 각 `0`

- [ ] **Step 2: 기술설계 스킬 — 2개 확정 종료 안내에 한 문장**

**원본** (`skills/tech-design/SKILL.md:333`):
```markdown
- On "여기서 종료 (2개 확정)" → `<slug>-tech-design.md` 맨 위에 frontmatter (`depth: 2` + `depth_reason: 사용자 선택`) 를 기록하고, `change-history` 로 [개발방향-수정] entry (이유: 2-doc 확정) 를 남긴 뒤 `ℹ️ 이 피처는 2개 문서로 확정됐습니다. 구현이 필요해지면 /write-plan 으로 승격하세요.` 를 출력하고 stop.
```

**수정 후**:
```markdown
- On "여기서 종료 (2개 확정)" → `<slug>-tech-design.md` 맨 위에 frontmatter (`depth: 2` + `depth_reason: 사용자 선택`) 를 기록하고, `change-history` 로 [개발방향-수정] entry (이유: 2-doc 확정) 를 남긴 뒤 `ℹ️ 이 피처는 2개 문서로 확정됐습니다. 구현이 필요해지면 /write-plan 으로 승격하세요.` 를 출력하고 stop. 요구사항 문서 머리에 소속 표식 (`> **큰 작업**:`) 이 있으면 한 줄 더 붙인다: `ℹ️ 큰 작업에 속한 피처입니다. 구현이 끝나면 /epic-next 로 파트를 마무리하세요.`
```

- [ ] **Step 3: /epic 커맨드 — 하지 않는 것에 두 커맨드 안내**

**원본** (`commands/epic.md:144`):
```markdown
- 워크트리를 만들지 않습니다. 만드는 일은 `/worktree` 가 합니다
```

**수정 후**:
```markdown
- 워크트리를 만들지 않습니다. 파트 마무리와 다음 파트 워크트리는 `/epic-next` 가, 새 세션의 인수인계는 `/epic-handoff` 가 합니다
```

- [ ] **Step 4: 검증**

Run: `grep -c "/epic-next" skills/tech-design/SKILL.md commands/epic.md; grep -c "/epic-handoff" commands/epic.md`
Expected: 각 `1` / `1`

- [ ] **Step 5: Commit**

```bash
git add skills/tech-design/SKILL.md commands/epic.md
git commit -m "docs(epic): 2개 확정 종료 안내와 /epic 안내에 파트 마무리 커맨드 한 줄"
```

### Task 8: 사람이 돌리는 시나리오 — H25 갱신 + H27 신설 + 인덱스

**Files:**
- Modify: `skills/js-super-sub-driven/tests/H25-epic-flow/README.md:3-4`
- Modify: `skills/js-super-sub-driven/tests/H25-epic-flow/README.md:30`
- Modify: `skills/js-super-sub-driven/tests/H25-epic-flow/README.md:37-44`
- Modify: `skills/js-super-sub-driven/tests/H25-epic-flow/README.md:55-56`
- Create: `skills/js-super-sub-driven/tests/H27-epic-close/README.md`
- Modify: `skills/js-super-sub-driven/tests/README.md:67`
- Modify: `skills/js-super-sub-driven/tests/README.md:80`

**Model**: sonnet

**검증**: H25 에 남은 `8.5` 언급은 시나리오 4 에서 옛 항목이 없어졌음을 설명하는 한 줄뿐 (`grep -c "8\.5"` 가 1), H27 파일이 존재하고 시나리오 7개 (`grep -c "^## 시나리오"` 가 7), 인덱스에 H27 행이 1개, fixture 번호 중복 검사 (`ls skills/js-super-sub-driven/tests commands/understand-tests commands/slice-tests tests/eval-fixtures | grep -oE '^H[0-9]+' | sort | uniq -d | wc -l`) 가 0 이다.

H25 는 아래쪽부터 고친다.

- [ ] **Step 1: 현재 상태 확인**

Run: `test -d skills/js-super-sub-driven/tests/H27-epic-close && echo EXISTS || echo MISSING; grep -c "8\.5" skills/js-super-sub-driven/tests/H25-epic-flow/README.md`
Expected: `MISSING` / `3`

- [ ] **Step 2: H25 시나리오 4 기대 — 8.5 제거**

**원본** (`skills/js-super-sub-driven/tests/H25-epic-flow/README.md:55-56`):
```markdown
**기대**: `0.` `0.5.` `1.` `2.` 순으로 이어져 `8.` `8.5.` `9.` 로 끝난다. 기존 번호
0 부터 9 까지가 하나도 밀리지 않았다.
```

**수정 후**:
```markdown
**기대**: `0.` `0.5.` `1.` `2.` 순으로 이어져 `8.` `9.` 로 끝난다. 기존 번호 0 부터
9 까지가 하나도 밀리지 않았고, 옛 `8.5.` (큰 작업 갱신) 은 없다 — 그 단계는 `epic-close` 로 옮겨졌다 (H27).
```

- [ ] **Step 3: H25 시나리오 3 — 마무리 단계 언급을 H27 로 넘김**

**원본** (`skills/js-super-sub-driven/tests/H25-epic-flow/README.md:37-44`):
```markdown
**준비**: 시나리오 2 를 마친 직후 상태.

**실행**: 큰 그림에 영향이 없는 작은 피처로 `/brainstorm` 을 한 번 더 돌린다.

**기대**: 마무리 단계에서 "큰 그림 변경 없음" 한 줄만 나오고 `overview.md` 의 수정 시각이
그대로다.

**실패로 볼 것**: 항목이 그대로인데 문구만 다듬어 파일이 바뀌는 경우.
```

**수정 후**:
```markdown
**준비**: 시나리오 2 를 마친 직후 상태.

**실행**: 큰 그림에 영향이 없는 작은 피처로 `/brainstorm` 을 한 번 더 돌리고 승인까지 간다.

**기대**: 브레인스토밍이 끝나도 `overview.md` · `carry-over.md` · `forecast.md` 의 수정 시각이
그대로다. 갱신은 파트 실행이 끝난 뒤 `epic-close` 가 한다 (H27 시나리오 2).

**실패로 볼 것**: 브레인스토밍 승인 직후에 에픽 파일이 바뀌는 경우.
```

- [ ] **Step 4: H25 시나리오 2 의 4번 항목**

**원본** (`skills/js-super-sub-driven/tests/H25-epic-flow/README.md:30`):
```markdown
4. 브레인스토밍이 끝나면 큰 그림 갱신 판정, 이월 항목 기록, 예상 빗나감 판정이 차례로 일어난다
```

**수정 후**:
```markdown
4. 브레인스토밍이 끝나도 에픽 파일 셋은 바뀌지 않는다. 갱신은 파트 실행이 끝난 뒤 `epic-close` 가 한다 (H27)
```

- [ ] **Step 5: H25 머리 문단**

**원본** (`skills/js-super-sub-driven/tests/H25-epic-flow/README.md:3-4`):
```markdown
`brainstorming` 스킬의 시작 단계 (0.5) 와 마무리 단계 (8.5) 가 조건에 맞게 동작하는지
사람이 직접 돌려 확인한다. 대화 판단이 섞여 있어 자동 검사로 덮이지 않는 부분이다.
```

**수정 후**:
```markdown
`brainstorming` 스킬의 시작 단계 (0.5) 가 조건에 맞게 동작하는지 사람이 직접 돌려 확인한다.
대화 판단이 섞여 있어 자동 검사로 덮이지 않는 부분이다. 마무리 (에픽 파일 갱신) 는 H27 이 본다.
```

- [ ] **Step 6: H27 신설**

**수정 후** (new file: `skills/js-super-sub-driven/tests/H27-epic-close/README.md`):
````markdown
# H27 — 파트 실행이 끝나면 다음 파트 워크트리와 인수인계가 이어지는가

`epic-close` 스킬 · `/epic-next` · `/epic-handoff` 를 사람이 직접 돌려 확인한다. 세션 두 개가
필요하다. 임시 저장소에서 돌리고 저장소에는 아무것도 커밋하지 않는다.

## 준비 (공통)

임시 저장소를 만들어 커밋 하나를 두고, `/epic 테스트 큰 작업` 으로 큰 작업을 만든다. 큰 그림의
"지금 착수 가능" 에 항목을 둘 적는다. `/brainstorm` 으로 첫 파트를 만들어 요구사항 문서 머리에
소속 표식이 붙게 한다. 세션 이름은 `/rename <접두어>-<브랜치>` 로 브랜치 이름이 들어가게 짓는다.

## 시나리오 1 — 에픽이 없을 때 (음성 사례)

**준비**: `docs/epics/` 가 없는 저장소에서 구현계획서 하나를 실행한다.

**실행**: 실행이 끝나 마무리 스킬 (`finishing-a-development-branch`) 이 돈다.

**기대**: 종료 메시지 (✅ 모든 task 완료 …) 뒤에 아무 출력도 없다. "진행 중인 큰 작업이 없습니다"
같은 안내도 없다.

**실패로 볼 것**: 에픽 관련 문구가 한 줄이라도 나오는 경우.

## 시나리오 2 — 정상 마무리

**준비**: 공통 준비 상태에서 첫 파트를 실행까지 끝낸다 (실행 스킬로 끝냈으면 자동으로 이어지고,
아니면 `/epic-next`).

**기대** (순서대로):

1. "이번 파트: docs/features/<폴더>" 한 줄
2. 큰 그림 갱신 판정 · 이월 항목 선택 질문 · 예상 빗나감 판정. 방금 끝낸 파트가 착수 가능에서
   정해진 것으로 옮겨진다
3. `git log -1 --stat` 에 `docs/epics/` 아래 파일만 담긴 커밋
4. 추천 파트와 이유가 먼저 나오고 선택 질문 (추천 / 나머지 / 지금은 안 만듦 / 에픽 완료)
5. 이름 확정 질문. 제안 이름이 `<에픽 워크트리>__ep_part2_<작업명>` 꼴
6. 워크트리가 `.worktrees/<이름>` 에 생기고 `git config branch.<이름>.js-super-parent` 가 현재
   브랜치
7. 안내 4 항목 (경로 · 새 터미널 · `/rename` · `/epic-handoff`) 과 이 세션의 이름

**실패로 볼 것**: 3 보다 6 이 먼저인 경우 (커밋 전 생성). 워크트리가 둘 이상 생기는 경우.
`forecast.md` 의 내용이 선택 질문에 섞이는 경우.

## 시나리오 3 — 인사와 인수인계

**준비**: 시나리오 2 를 마친 부모 세션을 그대로 둔다.

**실행**: 새 터미널에서 자식 워크트리로 들어가 세션을 열고 `/rename <접두어>-<자식 브랜치>` 뒤
`/epic-handoff`.

**기대**:

1. 자식이 부모 세션을 찾아 인사를 한 번 보내고 "인수인계를 기다립니다" 를 내고 턴을 마친다
2. 부모 세션이 깨어나 인수인계 메시지를 보낸다. 네 절 (다음 파트 / 이번 파트에서 정한 것 / 읽을
   파일 / 부모 브랜치) 이 있고, 읽을 파일에 `forecast.md` 가 없고, 에픽 파일 본문이 복사돼 있지 않다
3. 자식이 추가 질문 없이 브레인스토밍을 시작하고, 시작 단계가 큰 그림과 미해소 이월 항목을 보여준다

**실패로 볼 것**: 부모 세션이 깨어나지 않는 경우 — 이때는 설계 전제가 깨진 것이므로 기술설계
§6 첫 행대로 요구사항으로 돌아가 인사 방식을 다시 정한다. 자식이 주제를 다시 묻는 경우.

## 시나리오 4 — 에픽 폴더가 gitignore 일 때

**준비**: 공통 준비에 더해 `.gitignore` 에 `docs/epics/` 를 넣고 커밋한다.

**실행**: 시나리오 2 와 같다.

**기대**: 갱신 커밋 단계가 "에픽 파일 커밋 없음" 한 줄을 내고 넘어간다. 생성 뒤 자식 워크트리의
`docs/epics/<폴더>/` 에 `overview.md` · `carry-over.md` · `forecast.md` 셋이 있다.

**실패로 볼 것**: 자식 워크트리에 에픽 폴더가 없는 경우. 커밋 단계가 오류로 멈추는 경우.

## 시나리오 5 — 2개 문서 트랙

**준비**: 소속 표식이 있는 피처를 `/design-tech` 에서 "여기서 종료 (2개 확정)" 으로 끝낸다.

**기대**: 종료 안내에 "구현이 끝나면 /epic-next 로 파트를 마무리하세요" 한 줄이 있다. 직접 구현한
뒤 `/epic-next` 를 치면 시나리오 2 와 같은 순서로 진행된다.

**실패로 볼 것**: 종료 안내에 그 한 줄이 없는 경우.

## 시나리오 6 — 부모가 없을 때

**준비**: 시나리오 2 를 마친 뒤 부모 세션을 닫는다.

**실행**: 자식 세션에서 `/epic-handoff`.

**기대**: "부모 세션 <브랜치> 을 찾지 못했습니다" 와 질문 (인수인계 없이 시작 / 중단). "인수인계
없이 시작" 을 고르면 브레인스토밍이 시작되고 시작 단계가 에픽 파일을 읽는다.

**실패로 볼 것**: 인사를 반복해서 보내거나 세션 목록을 반복 조회하는 경우.

## 시나리오 7 — 결합 검사

```bash
grep -c "js-super:epic-close" skills/finishing-a-development-branch/SKILL.md
# expected: 1
grep -cE "^8\.5\. |큰 작업 갱신" skills/brainstorming/SKILL.md
# expected: 0
grep -c "^## Related Skills" skills/brainstorming/SKILL.md
# expected: 1
python3 -c "from scripts.epic_chain import next_branch_name; print(next_branch_name('결제__ep_part2_환불', '정산'))"
# expected: 결제__ep_part3_정산
```
````

- [ ] **Step 7: 인덱스 — 범위 헤더와 H27 행**

**원본** (`skills/js-super-sub-driven/tests/README.md:80`):
```markdown
| H25-epic-flow | 큰 작업 맥락 — 없을 때 무출력 / 있을 때 큰 그림·미해소 이월만 노출 (예상도 제외) / 바뀐 게 없으면 파일 무변경 / 항목 번호 0~9 무밀림 |
```

**수정 후**:
```markdown
| H25-epic-flow | 큰 작업 맥락 (시작 단계) — 없을 때 무출력 / 있을 때 큰 그림·미해소 이월만 노출 (예상도 제외) / 브레인스토밍 승인 직후 에픽 파일 무변경 / 항목 번호 0~9 무밀림 |
| H27-epic-close | 파트 마무리 — 에픽 없을 때 무출력 / 갱신·커밋 → 선택 → 워크트리 (`__ep_partN_`) → 안내 / 자식 인사 → 인수인계 → 브레인스토밍 / gitignore 복사 / 2개 문서 트랙 / 부모 부재 |
```

**원본** (`skills/js-super-sub-driven/tests/README.md:67`):
```markdown
## v2.9.0 이후 fixtures (H14~H25)
```

**수정 후**:
```markdown
## v2.9.0 이후 fixtures (H14~H27)
```

- [ ] **Step 8: 검증**

Run: `grep -c "8\.5" skills/js-super-sub-driven/tests/H25-epic-flow/README.md; grep -c "^## 시나리오" skills/js-super-sub-driven/tests/H27-epic-close/README.md; grep -c "H27-epic-close" skills/js-super-sub-driven/tests/README.md; ls skills/js-super-sub-driven/tests commands/understand-tests commands/slice-tests tests/eval-fixtures 2>/dev/null | grep -oE '^H[0-9]+' | sort | uniq -d | wc -l`
Expected: `1` (옛 8.5 를 설명하는 시나리오 4 의 한 줄만) / `7` / `1` / `0`

- [ ] **Step 9: Commit**

```bash
git add skills/js-super-sub-driven/tests/H25-epic-flow/README.md skills/js-super-sub-driven/tests/H27-epic-close/README.md skills/js-super-sub-driven/tests/README.md
git commit -m "test(epic): H25 갱신 + H27 파트 마무리 시나리오 신설"
```

### Task 9: README 커맨드 표 + CLAUDE.md 결합 메모

**Files:**
- Modify: `README.md:518`
- Modify: `CLAUDE.md:2240`
- Modify: `CLAUDE.md:2211`
- Modify: `CLAUDE.md:2208-2209`
- Modify: `CLAUDE.md:2206`

**Model**: sonnet

**검증**: README 커맨드 표에 `/epic-next` 와 `/epic-handoff` 행이 각 1개 생기고, CLAUDE.md 에 `## 에픽 종료 워크트리 생성 결합` 섹션이 1개 있으며 그 안의 회귀 catch grep 이 전부 기대값과 맞는다 (실행 단계에서 각 명령을 실제로 돌려 확인). 옛 에픽 섹션의 "워크트리는 제안만" 문구가 0 이다. 결합 규칙 수집 (`evals.runner.coupling.collect_rules`) 이 직전보다 늘어난다.

CLAUDE.md 는 아래쪽부터 고친다.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "/epic-next" README.md CLAUDE.md; grep -c "워크트리는 제안만" CLAUDE.md; python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"`
Expected: 각 `0` / `1` / 결합 규칙 수 N (기록해 둔다 — Step 7 의 기준값)

- [ ] **Step 2: CLAUDE.md 회귀 패턴 표 행 — 8.5 언급 정정**

**원본** (`CLAUDE.md:2240`):
```markdown
| 브레인스토밍 항목 번호를 밀어서 삽입 | 흐름도와 절차 상세의 번호 참조가 어긋난다. 0.5 / 8.5 를 쓴 이유 |
```

**수정 후**:
```markdown
| 브레인스토밍 항목 번호를 밀어서 삽입 | 흐름도와 절차 상세의 번호 참조가 어긋난다. 0.5 를 쓴 이유 (옛 8.5 는 에픽 종료 워크트리 생성 결합에서 `epic-close` 로 옮겨져 없어졌다) |
```

- [ ] **Step 3: CLAUDE.md 새 결합 메모 섹션 삽입 (검사 게이트 섹션 앞)**

**원본** (`CLAUDE.md:2211`):
```markdown
## 검사 게이트 ↔ 두 실행 흐름 결합
```

**수정 후**:
````markdown
## 에픽 종료 워크트리 생성 결합

큰 작업 파트의 실행이 끝나면 에픽 파일을 갱신·커밋하고 다음 파트 워크트리를 만든 뒤, 새 세션이 인사하면 인수인계를 보내 곧바로 다음 브레인스토밍이 시작되게 한 기능. 브레인스토밍에 있던 마무리 단계 (8.5) 는 여기로 옮겨져 없어졌다. spec: `docs/features/2026-09-05-에픽종료-워크트리생성/`.

### 핵심 룰

- **마무리 절차는 `skills/epic-close/` 한 곳** — 실행이 끝나는 자리 셋 (인라인 실행 · 보조 에이전트 실행 · 수동 `/epic-next`) 이 모두 이 스킬을 이름으로 부른다. 앞의 둘은 `finishing-a-development-branch` Step 3 를 거친다. 두 실행 스킬 본문에는 사본을 두지 않는다
- **발동 조건은 스킬 안에서** — 진행 중 에픽 + 이번 피처의 소속 표식. "이번 피처" 는 인자로 받거나, 없으면 `docs/features/` 전체에서 파일이 가장 최근에 수정된 폴더다 (방금 실행이 끝난 피처는 계획서 변경이력이 막 갱신된다). 그 폴더에 표식이 없으면 아무 출력 없이 돌아간다 — 표식 있는 다른 피처로 옮겨 가지 않는다. og / auto 브레인스토밍은 표식을 남기지 않아 걸러지고, 표식이 붙은 피처를 자동 실행 커맨드로 실행한 경우는 원하는 발동이다 (요구 2)
- **순서는 갱신 → 갱신 커밋 → 선택 → 생성** — 커밋이 자식이 최신 큰 그림을 물려받는 유일한 경로다. 커밋 전에 워크트리를 만들지 않는다. 갱신 커밋은 에픽 폴더만 명시해 담는다
- **사슬은 앞으로만, 항상 하나** — 되돌려 합치는 단계 없음, 형제 워크트리 동시 생성 없음. 이름은 `<에픽 워크트리>__ep_part<N>_<작업명>` 평탄형 (앞 파트 이름 누적 안 함). 계산은 `scripts/epic_chain.py`
- **미추적 문서는 폴더 단위로 복사** — 후보는 에픽 폴더 전체와 이번 파트의 피처 폴더. `git ls-files` 가 비면 복사한다. 예상도도 이 경로로 자식에 간다
- **인수인계는 자식이 먼저 인사** — `/epic-handoff` 가 `js-super-parent` 기록과 세션 이름 (브랜치 이름 포함 관례) 으로 부모를 찾아 인사하고, 부모는 인사가 온 뒤에만 `SendMessage` 로 보낸다. 내용은 파일에 없는 네 가지 (다음 파트 · 이번 파트의 결정 · 읽을 경로 · 부모 브랜치). 에픽 파일 본문과 `forecast.md` 는 넣지 않는다
- **부모 무응답은 시간이 아니라 사용자 입력으로** — 자식은 "그냥 시작" 입력을 받으면 인수인계 없이 브레인스토밍을 시작한다. `ListAgents` 반복 조회 금지
- **2개 문서 트랙은 수동** — 실행이 스킬 밖에서 끝나 신호가 없다. 기술설계의 2개 확정 종료 안내가 `/epic-next` 한 줄을 붙인다

### 회귀 패턴

| 누락 / 변경 | 증상 |
|---|---|
| 두 실행 스킬에 절차 사본 삽입 | 한쪽만 고치면 실행 방식에 따라 동작이 갈린다 |
| 발동 검사 약화 (에픽 없을 때 안내 출력) | 단발성 피처마다 노이즈 — 요구 14 위반 |
| 커밋 전에 워크트리 생성 | 자식이 옛 큰 그림을 물려받는다 |
| 형제 생성 옵션 추가 | 큰 그림 파일이 두 갈래로 갈린다 |
| 복사 후보를 인수인계 목록으로 좁힘 | `forecast.md` 가 자식에 안 간다 (성공 기준 4) |
| 인사 전에 인수인계 전송 / 이름 관례 삭제 | 자식이 부모를 못 찾거나 잘못된 세션이 받는다 |
| 브레인스토밍에 8.5 부활 | 요구사항 직후 갱신 → 다음 파트가 앞 파트 코드 없이 시작 |
| 계획서 수정 후 블록을 백틱 세 개로 열고 안에 마크다운 예시를 넣음 | 이 기능의 원인이었던 잘림 재발 — 바깥 펜스는 백틱 네 개 |

### 회귀 catch grep

```bash
test -d skills/epic-close && test -f commands/epic-next.md && test -f commands/epic-handoff.md && echo OK
# expected: OK
```

```bash
grep -c "js-super:epic-close" skills/finishing-a-development-branch/SKILL.md commands/epic-next.md
# expected: 각 1
```

```bash
grep -c "disable-model-invocation: true" commands/epic-next.md commands/epic-handoff.md
# expected: 각 1
```

```bash
grep -cE "^8\.5\. |큰 작업 갱신" skills/brainstorming/SKILL.md
# expected: 0
```

```bash
grep -c "^## Related Skills" skills/brainstorming/SKILL.md
# expected: 1
```

```bash
grep -c "epic-close\|epic_chain" skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md
# expected: 각 0
```

```bash
python3 -c "from scripts.epic_chain import next_branch_name; print(next_branch_name('결제__ep_part2_환불', '정산'))"
# expected: 결제__ep_part3_정산
```

```bash
grep -c "git add -A" skills/epic-close/SKILL.md
# expected: 2
```

```bash
grep -c "/epic-next" skills/tech-design/SKILL.md commands/epic.md
# expected: 각 1
```

```bash
test -f skills/js-super-sub-driven/tests/H27-epic-close/README.md && echo OK
# expected: OK
```

```bash
for c in commands/epic-next.md commands/epic-handoff.md; do n=$(basename "$c" .md); [ -d "skills/$n" ] && echo "충돌: $n"; done; test ! -f commands/epic-close.md && echo NO_COLLISION
# expected: NO_COLLISION
```

### 영향 범위

- 신규 5 (`skills/epic-close/SKILL.md` · `commands/epic-next.md` · `commands/epic-handoff.md` · `scripts/epic_chain.py` · 그 테스트) + 수정 7 (`finishing-a-development-branch` · `brainstorming` · `tech-design` · `commands/epic.md` · H25 · tests 인덱스 · README) + 본 섹션. 버전 bump 는 main 전용 룰에 따라 main 에서
- `executing-plans` / `js-super-sub-driven` / `setting-up-worktrees` / `scripts/epic_scan.py` / hooks 본문 변경 0
- og-\* / auto-\* / worktree 계열 영향 0 — 마무리 스킬을 거쳐도 발동 검사가 걸러낸다

## 검사 게이트 ↔ 두 실행 흐름 결합
````

- [ ] **Step 4: CLAUDE.md 옛 에픽 섹션 — 두 불릿 교체**

**원본** (`CLAUDE.md:2208-2209`):
```markdown
- **워크트리는 제안만** — 부모 관계를 알려주는 데까지. 만드는 일은 `setting-up-worktrees` 가 한다
- **자동 흐름 비적용** — `auto-brainstorming` 계열에는 넣지 않는다 (요구사항 범위 밖)
```

**수정 후**:
```markdown
- **마무리와 워크트리는 `epic-close` 가** — 브레인스토밍에 있던 마무리 단계 (8.5) 는 파트 실행이 끝난 뒤로 옮겨졌고, 다음 파트 워크트리도 거기서 만든다. "에픽 종료 워크트리 생성 결합" 참조
- **자동 흐름 비적용** — `auto-brainstorming` 계열에는 넣지 않는다 (요구사항 범위 밖)
```

- [ ] **Step 5: CLAUDE.md 옛 에픽 섹션 — "두 단계" 를 "시작 단계" 로**

**원본** (`CLAUDE.md:2206`):
```markdown
- **없으면 조용히 지나간다** — 진행 중인 큰 작업이 없으면 브레인스토밍의 두 단계를 건너뛰고 안내도 출력하지 않는다
```

**수정 후**:
```markdown
- **없으면 조용히 지나간다** — 진행 중인 큰 작업이 없으면 브레인스토밍의 시작 단계를 건너뛰고 안내도 출력하지 않는다. 실행 끝의 `epic-close` 도 같다
```

- [ ] **Step 6: README 커맨드 표 두 행**

**원본** (`README.md:518`):
```markdown
| `/epic <설명>` | 큰 그림 3 파일 | 여러 브레인스토밍으로 나눌 큰 작업 관리 |
```

**수정 후**:
```markdown
| `/epic <설명>` | 큰 그림 3 파일 | 여러 브레인스토밍으로 나눌 큰 작업 관리 |
| `/epic-next [피처 폴더]` | 에픽 파일 갱신 커밋 + 다음 파트 워크트리 | 파트 실행이 끝났는데 자동 마무리가 안 도는 경우 (2개 문서 트랙 등) |
| `/epic-handoff` | 부모 세션 인사 → 인수인계 수신 → 브레인스토밍 시작 | 다음 파트 워크트리에서 연 새 세션에서 한 번 |
```

- [ ] **Step 7: 검증 — 회귀 catch grep 전부 실행**

Run: `grep -c "/epic-next" README.md; grep -c "^## 에픽 종료 워크트리 생성 결합" CLAUDE.md; grep -c "워크트리는 제안만" CLAUDE.md; grep -c "js-super:epic-close" skills/finishing-a-development-branch/SKILL.md commands/epic-next.md; grep -c "epic-close\|epic_chain" skills/executing-plans/SKILL.md skills/js-super-sub-driven/SKILL.md; python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"`
Expected: `1` / `1` / `0` / 각 `1` / 각 `0` / Step 1 에서 기록한 N 보다 큰 수 (새 섹션의 grep 블록 10개 이상이 더해진다)

- [ ] **Step 8: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs(epic): README 커맨드 표 2행 + CLAUDE.md 에픽 종료 워크트리 생성 결합 메모"
```

## 2. 위험 코드 지점

- `skills/epic-close/SKILL.md` Step 6 (인사 대기) — race: 턴을 마친 부모 세션이 자식의 메시지에 깨어난다는 계약을 문서로 확인하지 못함 (mitigation: H27 시나리오 3 을 첫 e2e 로 돌려 확인. 안 깨어나면 요구사항으로 돌아가 인사 방식 재결정 — 사용자가 부모에 입력하는 완화책은 쓰지 않음)
- `skills/epic-close/SKILL.md` Step 6 — side-effect: 인사 시점에 부모 대화가 압축돼 인수인계 내용을 대화에서 못 꺼냄 (mitigation: 인사 메시지가 할 일을 담고, 내용은 기술설계 §5·§6 과 계획서 변경이력에서 다시 모은다)
- `commands/epic-handoff.md` §2 — side-effect: 세션 이름이 관례를 안 따라 부모를 못 찾음 (mitigation: 부모가 안내 단계에서 자기 이름을 확인하고 `/rename` 권고, 자식은 후보 없음 안내 + 인수인계 없이 시작 옵션)
- `skills/finishing-a-development-branch/SKILL.md` Step 3 — side-effect: og / 자동 흐름에서도 epic-close 가 불림 (mitigation: 스킬 안 발동 검사 — 진행 중 에픽 + 소속 표식. og / auto 브레인스토밍은 표식을 남기지 않는다)
- `skills/brainstorming/SKILL.md` 8.5 제거 — breaking: H25 시나리오 2·3·4 가 옛 동작을 기대 (mitigation: Task 8 이 H25 를 함께 고친다)
- `skills/epic-close/SKILL.md` Step 2 — side-effect: 갱신 커밋에 무관한 변경이 섞임 (mitigation: `git add docs/epics/<폴더>` 경로 명시, `git add -A` 금지 문장 + Anti-Pattern 행)
- `skills/epic-close/SKILL.md` Step 4 복사 — side-effect: 자식 워크트리의 같은 경로를 덮어씀 (mitigation: 경로가 이미 있으면 복사하지 않고 알린다)
- `skills/epic-close/SKILL.md` Step 0 최근 수정 판별 — side-effect: 실행 직후 다른 피처의 문서를 손으로 고친 뒤 마무리가 돌면 그쪽이 잡힘 (mitigation: 전체 피처 중 최근 폴더를 고르되 소속 표식이 없으면 조용히 종료하므로 단발성 피처로 새는 일은 없다. 고른 폴더 한 줄 알림 + `/epic-next <폴더>` 인자로 지정 가능)
- 이 계획서 자체 (Task 2 · 4 · 6 Step 2 · 8 Step 6 · 9 Step 3 의 수정 후 블록) — side-effect: 마크다운 예시나 bash 블록이 안에 있어 백틱 세 개로 열면 이 기능의 원인이었던 잘림이 재발 (mitigation: 바깥 펜스를 백틱 네 개로 열었다. 실행 뒤 각 파일 끝부분이 계획서와 같은지 `tail` 로 확인)
- `skills/epic-close/SKILL.md` Step 4 워크트리 생성 — side-effect: 워크트리 생성 스킬의 이름 제안이 개입해 규칙을 덮어씀 (mitigation: 확정한 이름을 인자에 명시한다. 명시 이름은 그대로 쓴다는 규칙이 그 스킬에 있다)

## 3. 롤백 전략

- Code: Task 별 커밋을 역순으로 `git revert`. 신규 파일 5 개는 revert 로 사라지고, 수정 7 파일은 원본 블록 상태로 돌아간다
- 브레인스토밍 스킬만 되돌리고 싶으면 Task 6 커밋 하나만 revert — 8.5 와 옛 흐름도가 돌아오지만 잘린 섹션 복구도 같이 사라지므로, 그 경우 Step 2 의 수정 후 블록에서 "마무리는 실행 끝에서" 절만 빼고 다시 적용한다
- DB / Config: 해당 없음. 사용자 환경 산출물 (워크트리 · git config 부모 기록) 은 이 기능이 새로 만드는 것이 아니라 기존 워크트리 스킬의 것이라 별도 롤백 없음
- 플러그인 캐시: 머지 뒤 `/reload-plugins` 로 반영. 되돌린 뒤에도 같은 명령

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-09-05 13:23] [구현계획서-수정]
- **id**: CH-20260905-003
- **이유**: 신규 구현 계획 (요구 1~16 · 기술설계 결정 1~7 → Task 1~9)
- **무엇이**: 에픽종료-워크트리생성-implementation-plan.md 전체 (Task 9건, §2 위험 코드 지점 10건, §3 롤백)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260905-001, CH-20260905-002

### [2026-09-05 13:38] [코드-수정] (batch: tasks 1..9)
- **id**: CH-20260905-005
- **이유**: 구현계획서 Task 1~9 실행 — 에픽 파트 마무리를 실행 끝으로 옮기고 다음 파트 워크트리 생성 + 세션 인수인계를 붙임
- **무엇이**: scripts/epic_chain.py (신규) · scripts/tests/test_epic_chain.py (신규, 9건) · skills/epic-close/SKILL.md (신규) · commands/epic-next.md (신규) · commands/epic-handoff.md (신규) · skills/finishing-a-development-branch/SKILL.md (Step 3) · skills/brainstorming/SKILL.md (8.5 제거 · 흐름도 노드 1 간선 2 제거 · 큰 작업 맥락 꼬리 복구 · Related Skills 헤더 복구) · skills/tech-design/SKILL.md (2개 확정 안내 한 줄) · commands/epic.md (하지 않는 것 한 줄) · H25 갱신 · H27 신설 · tests/README.md 인덱스 · README.md 커맨드 표 2행 · CLAUDE.md (에픽 섹션 불릿 2 + 회귀 표 1행 + 결합 메모 신설)
- **영향범위**: 브레인스토밍 승인 직후 에픽 파일 갱신이 더 이상 일어나지 않는다 (실행 끝으로 이동). 마무리 스킬을 거치는 모든 흐름 (인라인 · 보조 에이전트 · og · auto 실행) 이 epic-close 를 부르지만 발동 검사 (진행 중 에픽 + 이번 피처의 소속 표식) 가 걸러낸다. 결합 규칙 214 → 229
- **위험 카테고리**: side-effect
- **task별 세부 (9건)**:
  - Task 1: scripts/epic_chain.py, scripts/tests/test_epic_chain.py — 브랜치 파싱 · 다음 이름 · 미추적 경로 · 최근 폴더 (RISK side-effect 1건: ls-files 가 비면 무시된 경로도 복사 대상 — 의도된 동작) — commits: a5c1ec5
  - Task 2: skills/epic-close/SKILL.md — 8단계 절차 + 스크립트 위치 해석 + 다른 하네스 + Anti-Patterns (none) — commits: 60daf72
  - Task 3: commands/epic-next.md — 명시 호출 전용 수동 진입 (none) — commits: e32d7c9
  - Task 4: commands/epic-handoff.md — 부모 찾기 · 인사 · 인수인계 수신 · 브레인스토밍 시작 · 대체 경로 (none) — commits: d34ea03
  - Task 5: skills/finishing-a-development-branch/SKILL.md — Step 3 epic-close 호출 (side-effect: 모든 실행 흐름이 지나감, 발동 검사가 걸러냄) — commits: 77d1ee5
  - Task 6: skills/brainstorming/SKILL.md — 7곳 수정, 아래에서 위로 적용, dot 미선언 노드 0 (breaking: H25 기대 변경 → Task 8 동반) — commits: 0045824
  - Task 7: skills/tech-design/SKILL.md, commands/epic.md — 안내 한 줄씩 (none) — commits: dea9f9e
  - Task 8: H25 4곳 · H27 신설 (시나리오 7) · tests/README.md 인덱스 (none) — commits: 467b50f
  - Task 9: README.md 2행 · CLAUDE.md 4곳 (결합 메모 92줄) (none) — commits: ff9bf37
- **실행 중 발견해 고친 것 (1건)**:
  - 계획서 블록을 손으로 옮기지 않고 스크래치 도우미가 펜스 길이를 보고 바이트 그대로 꺼내 적용했다 (중첩 펜스 잘림 재발 차단). 12개 원본 블록 모두 1회 일치, 신규 5 파일의 끝부분이 계획서와 같음을 tail 로 확인
- **검증**: pytest 9건 통과 (epic_chain). 각 task 의 검증 grep 전부 기대값 일치. 변경분 검사 게이트: task 1~9 발견 없음 (변경 파일 합계 12) — 건너뜀 6항목 (pytest · coverage · lizard · mutmut 미설치, CRAP 데이터 없음, jscpd 미설치 — 이 워크트리에 가상환경이 없어 시스템 파이썬으로 잰 결과), 의존 방향 통과
- **연관 commits**: a5c1ec5..ff9bf37
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260905-003

### [2026-09-05 13:50] [코드-수정]
- **id**: CH-20260905-007
- **이유**: e2e 발견 — 이름 확정 AskUserQuestion 이 옵션 1개라 도구가 거부 (InputValidationError). 옵션을 "이 이름으로" / "다른 이름으로" 둘로
- **무엇이**: skills/epic-close/SKILL.md Step 4 이름 확정 문단
- **영향범위**: 기술설계 §3 동기 (CH-20260905-006)
- **위험 카테고리**: none
- **연관 항목**: CH-20260905-005

### [2026-09-05 13:50] [검증]
- **id**: CH-20260905-008
- **이유**: 사용자 기준 e2e (H27 시나리오) — 임시 복제본에서 실제 흐름 실행
- **결과**:
  - 시나리오 1 (에픽 없음): 이 저장소 실행 끝에서 docs/epics 부재 → 무출력 — 통과
  - 시나리오 2 (정상 마무리): 스캔 → 최근 폴더 = 방금 끝난 파트 · 소속 대조 통과 → 큰 그림 갱신 (환불 → 정해진 것) · 이월 2건 (사용자 선택) · 예상도 무변경 → 에픽 폴더만 담은 커밋 → 추천(정산) 먼저 + 선택 → 이름 `에픽종료-워크트리생성__ep_part2_정산` → 워크트리 + 부모 기록 → 세 파일 상속 — 통과. 워크트리 생성은 setting-up-worktrees 의 Step 4 명령을 직접 실행 (스킬 본문 미로드)
  - 시나리오 3 (인사 → 인수인계): 사용자가 원격이라 쉬는 중인 js수퍼 세션을 자식 대역으로 사용. 인사가 도착하자 쉬던 이 세션이 깨어남 (§6 첫 행 race 위험 해소) → 인수인계 전송 → 대역이 절 4개 · forecast 없음 · 본문 없음 확인 — 통과. 브레인스토밍 시작은 대역이라 생략
  - 시나리오 4 (gitignore): 무시된 에픽 폴더 → 커밋 없음 한 줄 → 자식에 상속 안 됨 → untracked 판정 → 복사 → 세 파일 존재 — 통과
  - 시나리오 5 (2개 문서 트랙): 기술설계 스킬의 종료 안내 한 줄 grep 으로 확인 (실행은 미수행)
  - 시나리오 6 (부모 부재): 커맨드 본문 검토로만 확인 (실행은 미수행)
  - 결함 1건: 이름 확정 질문 옵션 1개 → CH-20260905-007 로 수정
- **연관 항목**: CH-20260905-005, CH-20260905-007
