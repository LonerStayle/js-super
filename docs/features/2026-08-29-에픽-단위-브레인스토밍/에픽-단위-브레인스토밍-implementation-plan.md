---
commit_policy: per-task
---

# 에픽 단위 브레인스토밍 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 큰 작업 하나를 여러 번의 브레인스토밍으로 나눠 진행할 때, 그 사이를 잇는 맥락을 대화가 아니라 파일이 나르게 한다.

**Architecture:** 사용자가 부르는 진입점 하나(`/epic`), 기존 브레인스토밍 흐름의 앞뒤에 붙는 두 단계, 진행 상태를 매번 세는 스크립트 하나로 나뉜다. 큰 작업 폴더는 피처 폴더와 나란히 놓이고 어느 쪽도 다른 쪽 안에 들어가지 않는다.

**Tech Stack:** Python 3 표준 라이브러리 (읽기 전용 스캔), 마크다운 스킬·커맨드 본문

**Spec inputs:**
- 에픽-단위-브레인스토밍-requirements.md — 요구 1~18 전부
- 에픽-단위-브레인스토밍-tech-design.md — §2 영향 파일 7개, §5 핵심 결정 7건

## 1. 단계별 작업

### Task 1: 큰 작업 스캔 스크립트

**Files:** Create `scripts/epic_scan.py`, Create `scripts/tests/test_epic_scan.py`
**Model**: sonnet
**검증**: 임시 폴더에 큰 작업 폴더 하나와 서로 다른 산출물 구성의 피처 폴더 여러 개를 만들어 두고, 진행 중인 큰 작업을 찾아 소속 피처를 기획·설계·계획·실행 네 단계로 분류하는지 확인한다. 소속 표식이 없는 피처가 별도 목록으로 세어지고, 진행 중인 큰 작업이 없을 때 빈 결과를 돌려주면 성공이다.

- [ ] Step 1: `**검증**` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인
- [ ] Step 2: `scripts/epic_scan.py` 생성 (아래 코드)
- [ ] Step 3: 테스트 실행 → pass 확인
- [ ] Step 4: self-review

**수정 후** (`scripts/epic_scan.py` — 신규)

```python
"""큰 작업(에픽) 폴더와 소속 피처를 훑어 진행 상태를 계산한다.

표준 라이브러리만 쓰고 어떤 파일도 고치지 않는다. 진행 상태를 파일에
저장해두지 않고 매번 세는 것이 이 모듈의 존재 이유다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

EPICS_DIRNAME = "epics"
FEATURES_DIRNAME = "features"
OVERVIEW_NAME = "overview.md"
CARRY_OVER_NAME = "carry-over.md"
FORECAST_NAME = "forecast.md"

STATUS_ACTIVE = "진행 중"
STATUS_DONE = "완료"

STAGE_PLANNED = "기획"
STAGE_DESIGNED = "설계"
STAGE_SCHEDULED = "계획"
STAGE_EXECUTED = "실행"

_STATUS_RE = re.compile(r"^>\s*\*\*상태\*\*:\s*(.+?)\s*$", re.MULTILINE)
_EPIC_RE = re.compile(r"^>\s*\*\*큰 작업\*\*:\s*(.+?)\s*$", re.MULTILINE)
_CODE_ENTRY_RE = re.compile(r"^###\s*\[[^\]]*\]\s*\[코드-수정\]", re.MULTILINE)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def epic_status(overview_path: Path) -> str:
    """큰 그림 문서의 상태 줄을 읽는다. 줄이 없으면 진행 중으로 본다."""
    match = _STATUS_RE.search(_read(overview_path))
    return match.group(1).strip() if match else STATUS_ACTIVE


def find_active_epics(docs_dir: Path) -> list[Path]:
    """진행 중인 큰 작업 폴더를 이름 순으로 모은다."""
    epics_dir = docs_dir / EPICS_DIRNAME
    if not epics_dir.is_dir():
        return []
    found = []
    for child in sorted(epics_dir.iterdir()):
        overview = child / OVERVIEW_NAME
        if child.is_dir() and overview.is_file():
            if epic_status(overview) == STATUS_ACTIVE:
                found.append(child)
    return found


def current_epic(docs_dir: Path) -> Optional[Path]:
    """진행 중인 것이 여럿이면 큰 그림을 가장 최근에 고친 쪽을 쓴다."""
    actives = find_active_epics(docs_dir)
    if not actives:
        return None
    return max(actives, key=lambda d: (d / OVERVIEW_NAME).stat().st_mtime)


def feature_epic(feature_dir: Path) -> Optional[str]:
    """피처 요구사항 문서 머리의 소속 표식을 읽는다."""
    for md in sorted(feature_dir.glob("*-requirements.md")):
        match = _EPIC_RE.search(_read(md))
        if match:
            return match.group(1).strip()
    return None


def feature_stage(feature_dir: Path) -> str:
    """폴더에 있는 산출물로 어느 단계까지 왔는지 판정한다."""
    plans = sorted(feature_dir.glob("*-implementation-plan.md"))
    designs = sorted(feature_dir.glob("*-tech-design.md"))
    for doc in plans + designs:
        if _CODE_ENTRY_RE.search(_read(doc)):
            return STAGE_EXECUTED
    if plans:
        return STAGE_SCHEDULED
    if designs:
        return STAGE_DESIGNED
    return STAGE_PLANNED


def collect_features(docs_dir: Path, epic_name: str) -> dict:
    """소속 피처와 표식 없는 피처를 갈라 모은다."""
    features_dir = docs_dir / FEATURES_DIRNAME
    members: list[dict] = []
    unmarked: list[str] = []
    if not features_dir.is_dir():
        return {"members": members, "unmarked": unmarked}
    for child in sorted(features_dir.iterdir()):
        if not child.is_dir():
            continue
        owner = feature_epic(child)
        if owner is None:
            unmarked.append(child.name)
        elif owner == epic_name:
            members.append({"name": child.name, "stage": feature_stage(child)})
    return {"members": members, "unmarked": unmarked}


def scan(docs_dir: Path) -> dict:
    """진행 중인 큰 작업 하나와 그 소속 피처들의 현재 상태를 돌려준다."""
    epic = current_epic(docs_dir)
    if epic is None:
        return {
            "epic": None,
            "epic_path": None,
            "active_count": 0,
            "members": [],
            "unmarked": [],
        }
    collected = collect_features(docs_dir, epic.name)
    return {
        "epic": epic.name,
        "epic_path": str(epic),
        "active_count": len(find_active_epics(docs_dir)),
        "members": collected["members"],
        "unmarked": collected["unmarked"],
    }


def main(argv: list[str]) -> int:
    docs_dir = Path(argv[1]) if len(argv) > 1 else Path("docs")
    print(json.dumps(scan(docs_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### Task 2: `/epic` 커맨드

**Files:** Create `commands/epic.md`
**Model**: sonnet
**검증**: 커맨드 파일에 명시 호출 전용 표기가 있고, 큰 작업 만들기와 상태 조회와 종료 표시 세 동작이 인자에 따라 갈리도록 본문에 적혀 있는지 확인한다. 만들기 대화가 목표와 경계까지만 묻고 전체 순서는 묻지 않는다는 제약이 본문에 있으면 성공이다.

- [ ] Step 1: `**검증**` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인
- [ ] Step 2: `commands/epic.md` 생성 (아래 본문)
- [ ] Step 3: 테스트 실행 → pass 확인
- [ ] Step 4: self-review

**수정 후** (`commands/epic.md` — 신규)

```markdown
---
description: 여러 번의 브레인스토밍으로 나눠 진행할 큰 작업을 만들고, 진행 상태를 보고, 끝났다고 표시합니다.
disable-model-invocation: true
---

# /epic — 큰 작업 관리

한 번의 브레인스토밍으로 감당이 안 되는 일을 "큰 작업" 이라 부릅니다. 큰 작업 하나가
여러 번의 브레인스토밍으로 쪼개지고, 브레인스토밍 하나가 피처 폴더 하나를 만듭니다.

이 커맨드는 그 큰 작업을 만들고, 지금 어디까지 왔는지 보고, 다 끝났다고 표시합니다.

## 1. 인자 해석

| 인자 | 하는 일 |
|---|---|
| 설명 텍스트 | 큰 작업을 새로 만듭니다 |
| 없음 | 진행 중인 큰 작업의 상태를 보여줍니다 |
| `done` | 진행 중인 큰 작업을 완료로 표시합니다 |

## 2. 큰 작업 만들기

### 2-1. 대화

목표와 경계까지만 묻고 끝냅니다. 서너 번이면 충분합니다. 각 피처의 세부 요구사항,
기술 선택, **전체 순서와 의존 관계 확정**은 묻지 않습니다. 마지막 항목이 중요합니다 —
두 번째 이후에 무엇을 할지는 첫 브레인스토밍이 끝나봐야 알 수 있고, 미리 정하면
그 목록을 소진하는 방식으로 굳습니다.

묻는 것은 다음 다섯 가지입니다.

| 묻는 것 | 채우는 칸 |
|---|---|
| 무엇을 이루려는가, 다 됐다고 볼 기준은 무엇인가 | 목표 |
| 왜 지금인가 | 배경 |
| 어디까지가 이 작업인가 | 경계 |
| 지금 확실한 것과 아직 모르는 것 | 정해진 것 · 모르는 것 |
| 첫 삽을 어디 뜨나 | 착수 가능 |

한 번에 하나씩 묻고, `AskUserQuestion` 도구를 씁니다. 답이 이미 사용자의 첫 입력에
들어 있으면 다시 묻지 않습니다.

대화 중에 "이건 나중에" 류의 말이 나오면 이월 후보로 기억해뒀다가 아래 2-3 에서
한꺼번에 기록합니다.

### 2-2. 폴더와 파일 만들기

`docs/epics/<오늘날짜>-<슬러그>/` 를 만들고 파일 셋을 씁니다. 슬러그는 사용자가 준
설명에서 뽑되, 확정 전에 한 번 확인받습니다.

`overview.md` — 큰 그림

```markdown
# 큰 작업: <이름>

> **상태**: 진행 중

## 목표
<무엇을 이루려는가. 다 됐다고 볼 기준>

## 배경
<왜 지금 하는가>

## 경계
<어디까지가 이 작업인가>

## 정해진 것
<지금까지 확정된 것. 처음에는 비어 있어도 된다>

## 지금 착수 가능
<막는 것이 없는 항목>

## 무엇을 기다림
<항목 — 무엇이 끝나야 하는지>

## 아직 모름
<해봐야 아는 것>
```

`carry-over.md` — 이월 노트

```markdown
# 이월 노트

미룬 것, 주의사항, 기각한 안, 유보한 것을 담습니다. 뒤에 붙이기만 하고 지우지
않습니다. 해소된 항목은 해소 표시를 덧붙입니다.

| 종류 | 내용 | 나온 곳 | 상태 |
|---|---|---|---|
```

`forecast.md` — 예상도

```markdown
# 예상도

시점별로 아래에 쌓습니다. 옛 예상을 덮어쓰지 않습니다. 다음 주제를 고를 때
참조하지 않습니다 — 사람이 직접 열어볼 때만 봅니다.

## <날짜> 시점 예상
<지금 시점에서 앞으로 이렇게 갈 것 같다는 짐작>
```

### 2-3. 이월 후보 기록

대화 중 모아둔 이월 후보를 목록으로 보여주고 남길 것을 고르게 한 뒤 `carry-over.md`
표에 붙입니다. 후보가 없으면 이 단계를 건너뜁니다.

### 2-4. 마치며 알릴 것

만든 폴더 경로와 파일 셋을 알리고, 첫 브레인스토밍을 시작하려면 `/brainstorm` 을
쓰면 된다고 안내합니다. 이 커맨드가 브레인스토밍을 자동으로 시작하지는 않습니다.

## 3. 상태 보기

`scripts/epic_scan.py` 를 실행해 결과를 표로 보여줍니다.

```bash
python3 scripts/epic_scan.py docs
```

진행 중인 큰 작업이 없으면 그 사실만 한 줄로 알리고 끝냅니다. 여럿이면 가장 최근에
고친 것을 쓰고 그 사실을 한 줄 덧붙입니다.

보여줄 것은 세 덩어리입니다.

| 덩어리 | 내용 |
|---|---|
| 피처 목록 | 이름과 단계 (기획 / 설계 / 계획 / 실행) |
| 미해소 이월 항목 | `carry-over.md` 에서 해소 표시가 없는 것 |
| 큰 그림 현재 상태 | `overview.md` 의 착수 가능 · 기다림 · 모름 |

스캔 결과에 표식 없는 피처가 있으면 개수를 함께 알립니다. 소속 표식이 빠지면 목록에서
조용히 사라지기 때문입니다.

## 4. 완료 표시

`overview.md` 의 상태 줄을 `완료` 로 바꿉니다. 폴더를 지우거나 옮기지 않습니다.

끝났는지는 사람이 정합니다. 예상 항목이 다 소진됐는지로 판정하지 않습니다.

## 5. 하지 않는 것

- 워크트리를 만들지 않습니다. 만드는 일은 `/worktree` 가 합니다
- 브레인스토밍을 시작하지 않습니다
- 피처 폴더를 건드리지 않습니다
- 진행 상태를 파일에 적어두지 않습니다. 볼 때마다 셉니다
```

### Task 3: 브레인스토밍 스킬에 두 단계 붙이기

**Files:** Modify `skills/brainstorming/SKILL.md`
**Model**: sonnet
**검증**: 체크리스트와 절차 상세와 흐름도 세 곳 모두에 시작 단계와 마무리 단계가 들어갔고, 기존 항목 번호 0~9 가 하나도 밀리지 않았는지 확인한다. 흐름도에서 새 노드 둘이 선언되고 연결선이 그 노드를 거쳐 가면 성공이다.

같은 파일의 일곱 자리를 고치는데 모두 텍스트 삽입이고 알고리즘 변경이 없어 한 task 의 여러 단계로 묶는다. 일곱 자리는 서로 다른 위치라 앞 단계를 적용해도 뒤 단계의 원본이 그대로 남는다.

- [ ] Step 1: `**검증**` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인
- [ ] Step 2: 체크리스트에 0.5 항목 삽입 (블록 A)
- [ ] Step 3: 체크리스트에 8.5 항목 삽입 (블록 B)
- [ ] Step 4: 절차 상세에 0.5 단계 삽입 (블록 C)
- [ ] Step 5: 절차 상세에 8.5 단계 삽입 (블록 D)
- [ ] Step 6: 흐름도 노드 선언 추가 (블록 E)
- [ ] Step 7: 흐름도 진입 연결선 재배선 (블록 F)
- [ ] Step 8: 흐름도 마무리 연결선 재배선 (블록 G)
- [ ] Step 9: `## 큰 작업 맥락` 섹션 신설 (블록 H)
- [ ] Step 10: 테스트 실행 → pass 확인
- [ ] Step 11: self-review

**블록 A** — 체크리스트 0번과 1번 사이

**원본**

```markdown
0. **Entry Router (v1.1.15+, FR-3 · v2.8.1+ og 커맨드 전용화)** — 사용자 입력에 명시적 small 신호 감지 시 `/og-brainstorm` 실행 안내 한 줄 (자동 invoke 아님 — og 는 커맨드 전용). 그 외 → AskUserQuestion 게이트. 자세한 룰은 "Entry Router" 섹션 참조.
1. **프로젝트 컨텍스트 탐색** — files, docs, recent commits
```

**수정 후**

```markdown
0. **Entry Router (v1.1.15+, FR-3 · v2.8.1+ og 커맨드 전용화)** — 사용자 입력에 명시적 small 신호 감지 시 `/og-brainstorm` 실행 안내 한 줄 (자동 invoke 아님 — og 는 커맨드 전용). 그 외 → AskUserQuestion 게이트. 자세한 룰은 "Entry Router" 섹션 참조.
0.5. **큰 작업 맥락 읽기** — `docs/epics/` 에 진행 중인 큰 작업이 있으면 큰 그림과 미해소 이월 항목을 읽어 사용자에게 보여준다. 없으면 아무 말 없이 건너뛴다. 자세한 룰은 "큰 작업 맥락" 섹션 참조.
1. **프로젝트 컨텍스트 탐색** — files, docs, recent commits
```

**블록 B** — 체크리스트 8번 뒤

**원본**

```markdown
8. **변경이력 기록** — append first `[요구사항-수정]` entry via `change-history` skill
9. **개발방향 단계 자동 진행** — Right after the change-history entry is logged, auto-invoke `tech-design` via the Skill tool with a one-line interrupt-notice. On user "stop"/"멈춰"/"잠깐" → exit cleanly with notice telling the user to run /design-tech later.
```

**수정 후**

```markdown
8. **변경이력 기록** — append first `[요구사항-수정]` entry via `change-history` skill
9. **개발방향 단계 자동 진행** — Right after the change-history entry is logged, auto-invoke `tech-design` via the Skill tool with a one-line interrupt-notice. On user "stop"/"멈춰"/"잠깐" → exit cleanly with notice telling the user to run /design-tech later.
8.5. **큰 작업 갱신** — 큰 작업이 있으면 큰 그림 갱신 판정 · 이월 항목 기록 · 예상 빗나감 판정을 수행한다. 바뀐 것이 없으면 파일을 고치지 않는다. "큰 작업 맥락" 섹션 참조.
```

**블록 C** — 절차 상세 1번 앞

**원본**

```markdown
## Process (detail)

**1. Explore project context**
```

**수정 후**

```markdown
## Process (detail)

**0.5. 큰 작업 맥락 읽기**
- `docs/epics/` 가 없거나 진행 중인 큰 작업이 없으면 아무 출력 없이 다음 단계로 간다
- 있으면 큰 그림의 착수 가능 · 기다림 · 모름과 이월 노트의 미해소 항목을 사용자에게 보여준다
- 이월 항목은 지금 앞당겨 처리할지 판단하는 데 쓴다. 순서대로 꺼내는 대기열이 아니다
- 예상도는 읽지 않는다
- **이번 피처가 이 큰 작업에 속하면 5단계에서 쓸 요구사항 문서 머리에 소속 표식 한 줄을 넣기로 기억해둔다** — `> **큰 작업**: <큰 작업 폴더 이름>`. 이 줄이 없으면 그 피처는 목록에서 조용히 빠진다

**1. Explore project context**
```

**블록 D** — 절차 상세 9번 앞

**원본**

```markdown
**9. Auto-proceed to tech-design (v1.1.9+ — no gate)**
```

**수정 후**

```markdown
**8.5. 큰 작업 갱신**

큰 작업이 없으면 이 단계 전체를 건너뛴다. 있으면 셋을 차례로 한다.

- **큰 그림 갱신 판정** — 항목이 없어졌거나 새로 생겼거나 순서가 뒤집혔을 때만 고쳐 쓴다. 표현을 다듬는 수정은 하지 않는다. 바뀐 것이 없으면 파일을 건드리지 않고 "큰 그림 변경 없음" 한 줄만 알린다
- **이월 항목 기록** — 대화 중 모아둔 후보를 목록으로 보여주고 남길 것만 이월 노트 끝에 붙인다. 종류 (미룸 / 주의 / 기각 / 유보) 와 나온 곳을 함께 적는다
- **예상 빗나감 판정** — 예상이 빗나갔을 때만 예상도 끝에 새 시점 블록을 붙인다. 무엇이 어떻게 빗나갔는지와 그렇게 판단한 근거를 함께 적고, 근거를 적을 수 없으면 기록하지 않는다

착수 가능한 피처가 둘 이상이고 서로 건드리는 곳이 겹치지 않아 보이면 나란히 갈라내 동시에 진행하도록 제안한다. 판단 근거는 대화 내용이고, 코드를 뒤져 실제 충돌을 계산하지 않는다. 제안까지가 범위이고 워크트리는 만들지 않는다.

**9. Auto-proceed to tech-design (v1.1.9+ — no gate)**
```

**블록 E** — 흐름도 노드 선언

**원본**

```dot
    "AskUserQuestion 게이트\n(og / js-super)" [shape=diamond];
    "Explore project context" [shape=box];
```

**수정 후**

```dot
    "AskUserQuestion 게이트\n(og / js-super)" [shape=diamond];
    "큰 작업 맥락 읽기\n(있을 때만)" [shape=box];
    "Explore project context" [shape=box];
```

**블록 F** — 흐름도 진입 연결선

**원본**

```dot
    "AskUserQuestion 게이트\n(og / js-super)" -> "Explore project context" [label="js-super"];
    "Explore project context" -> "Confirm feature name + slug";
```

**수정 후**

```dot
    "AskUserQuestion 게이트\n(og / js-super)" -> "큰 작업 맥락 읽기\n(있을 때만)" [label="js-super"];
    "큰 작업 맥락 읽기\n(있을 때만)" -> "Explore project context";
    "Explore project context" -> "Confirm feature name + slug";
```

**블록 G** — 흐름도 마무리 연결선

**원본**

```dot
    "Invoke change-history\n(first entry: 요구사항-수정)" -> "Auto-invoke /design-tech (no gate, v1.1.9+)";
```

**수정 후**

```dot
    "Invoke change-history\n(first entry: 요구사항-수정)" -> "큰 작업 갱신\n(있을 때만)";
    "큰 작업 갱신\n(있을 때만)" -> "Auto-invoke /design-tech (no gate, v1.1.9+)";
```

**블록 H** — `## Related Skills` 앞에 새 섹션 삽입

**원본**

```markdown
## Related Skills
```

**수정 후**

```markdown
## 큰 작업 맥락

여러 번의 브레인스토밍으로 나눠 진행하는 일 하나를 큰 작업이라 부른다. `docs/epics/` 아래에 큰 그림 (`overview.md`), 이월 노트 (`carry-over.md`), 예상도 (`forecast.md`) 세 파일로 산다. 만들고 조회하는 것은 `/epic` 커맨드가 한다.

대화가 압축되면 앞에서 정한 것과 미룬 것이 요약에서 뭉개진다. 압축을 견디는 것은 파일뿐이라, 브레인스토밍은 시작할 때 이 파일들을 읽고 끝날 때 갱신한다.

### 있는지 확인하고 없으면 조용히 지나간다

`docs/epics/` 가 없거나 상태 줄이 `진행 중` 인 큰 그림이 하나도 없으면 시작 단계와 마무리 단계를 통째로 건너뛴다. 안내 문구도 출력하지 않는다. 큰 작업 없이 피처 하나만 만드는 기존 사용법이 지금과 똑같이 동작해야 한다.

진행 중인 것이 여럿이면 큰 그림을 가장 최근에 고친 것을 쓰고 그 사실을 한 줄 알린다. 어느 것을 쓸지 사용자에게 묻지 않는다.

### 시작 단계가 읽는 것

큰 그림의 착수 가능 · 기다림 · 모름과, 이월 노트에서 해소 표시가 없는 항목이다. 예상도는 읽지 않는다 — 읽어서 대화에 들어오면 다음 주제가 그 예상을 따라가고, 예상도를 따로 떼어낸 이유가 사라진다.

미해소 이월 항목은 지금 앞당겨 처리할지 판단하는 데 쓴다. 순서대로 꺼내는 대기열이 아니라 언제든 꺼낼 수 있는 보관함이다.

### 소속 표식을 남긴다

진행 중인 큰 작업이 있으면 이번 피처의 요구사항 문서 머리에 한 줄을 넣는다. 다음 단계 안내 인용 줄과 나란히 둔다.

```markdown
# 요구사항: <피처 이름>

> **큰 작업**: 2026-08-29-<큰 작업 슬러그>
> **다음 단계 안내**: ...
```

이 줄이 유일한 소속 근거다. 빠지면 그 피처는 상태 목록에서 조용히 사라진다. 형식을 바꾸면 `scripts/epic_scan.py` 와 `commands/epic.md` 를 함께 고쳐야 한다.

### 마무리 단계가 쓰는 것

| 대상 | 쓰는 조건 |
|---|---|
| 큰 그림 | 항목이 없어졌거나 생겼거나 순서가 뒤집혔을 때만. 표현만 다듬는 수정은 하지 않는다 |
| 이월 노트 | 대화 중 나온 후보를 보여주고 고른 것만. 뒤에 붙이기만 한다 |
| 예상도 | 예상이 빗나갔을 때만. 근거를 못 적으면 쓰지 않는다 |

바뀐 것이 없으면 파일을 건드리지 않고 대화로만 알린다. 매번 뭔가 쓰게 만들면 문구만 다듬는 갱신이 쌓인다.

### 다음 워크트리 안내

다음 주제를 고르고 나면 어느 워크트리를 부모로 삼을지 알려준다.

| 다음 피처가 | 부모로 삼을 곳 |
|---|---|
| 방금 끝낸 피처의 결과에 기댐 | 방금 끝낸 피처의 워크트리 |
| 더 앞선 무언가에 기댐 | 그 앞선 피처의 워크트리 |
| 아무것에도 안 기댐 | 큰 작업 워크트리 |

착수 가능한 피처가 둘 이상이고 서로 건드리는 곳이 겹치지 않아 보이면 나란히 갈라내 동시에 가도 된다고 제안한다. 판단 근거는 대화 내용이고 코드를 뒤지지 않는다. 워크트리를 실제로 만들지는 않는다 — 그 일은 `/worktree` 가 한다.

## Related Skills
```

### Task 4: 사람이 돌리는 시나리오

**Files:** Create `skills/js-super-sub-driven/tests/H25-epic-flow/README.md`
**Model**: sonnet
**검증**: 큰 작업이 없을 때와 있을 때 두 시나리오가 실행 절차와 기대 동작으로 적혀 있는지 확인한다. 없을 때 시나리오의 기대 동작이 "아무 출력도 없다" 로 명시되어 있으면 성공이다.

저장소에서 H1 부터 H24 까지 이미 쓰여 다음 번호를 쓴다.

- [ ] Step 1: `**검증**` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인
- [ ] Step 2: 시나리오 문서 생성 (아래 본문)
- [ ] Step 3: 테스트 실행 → pass 확인
- [ ] Step 4: self-review

**수정 후** (`skills/js-super-sub-driven/tests/H25-epic-flow/README.md` — 신규)

````markdown
# H25 — 큰 작업 맥락이 브레인스토밍에 붙는가

`brainstorming` 스킬의 시작 단계 (0.5) 와 마무리 단계 (8.5) 가 조건에 맞게 동작하는지
사람이 직접 돌려 확인한다. 대화 판단이 섞여 있어 자동 검사로 덮이지 않는 부분이다.

## 시나리오 1 — 큰 작업이 없을 때 (음성 사례)

**준비**: `docs/epics/` 가 없거나, 있어도 상태 줄이 `진행 중` 인 큰 그림이 하나도 없는 상태.

**실행**: `/brainstorm 아무 주제`

**기대**: 큰 작업 관련 출력이 하나도 없다. "진행 중인 큰 작업이 없습니다" 같은 안내도
나오면 안 된다. 대화가 곧바로 프로젝트 컨텍스트 탐색과 피처 이름 확인으로 들어간다.

**실패로 볼 것**: 큰 작업이 없다는 안내가 출력되는 경우. 큰 작업을 안 쓰는 사용자에게
매번 노이즈가 된다.

## 시나리오 2 — 큰 작업이 있을 때 (양성 사례)

**준비**: `/epic 테스트용 큰 작업` 으로 큰 작업을 하나 만든다. 이월 노트에 해소되지 않은
항목을 두 건 넣고, 한 건은 해소 표시를 붙여 둔다.

**실행**: `/brainstorm 아무 주제`

**기대**:

1. 대화 시작 전에 큰 그림의 착수 가능 · 기다림 · 모름이 보인다
2. 미해소 이월 항목 두 건만 보인다. 해소 표시가 붙은 한 건은 안 보인다
3. 예상도 내용은 안 보인다
4. 브레인스토밍이 끝나면 큰 그림 갱신 판정, 이월 항목 기록, 예상 빗나감 판정이 차례로 일어난다

**실패로 볼 것**: 예상도 내용이 대화에 들어오는 경우. 다음 주제가 그 예상을 따라가게 되어
예상도를 따로 떼어낸 이유가 사라진다.

## 시나리오 3 — 바뀐 게 없을 때 (음성 사례)

**준비**: 시나리오 2 를 마친 직후 상태.

**실행**: 큰 그림에 영향이 없는 작은 피처로 `/brainstorm` 을 한 번 더 돌린다.

**기대**: 마무리 단계에서 "큰 그림 변경 없음" 한 줄만 나오고 `overview.md` 의 수정 시각이
그대로다.

**실패로 볼 것**: 항목이 그대로인데 문구만 다듬어 파일이 바뀌는 경우.

## 시나리오 4 — 항목 번호가 안 밀렸는가

**실행**:

```bash
grep -E "^[0-9]+\.[0-9]* \*\*" skills/brainstorming/SKILL.md
```

**기대**: `0.` `0.5.` `1.` `2.` 순으로 이어져 `8.` `8.5.` `9.` 로 끝난다. 기존 번호
0 부터 9 까지가 하나도 밀리지 않았다.
````

### Task 5: 문서 갱신

**Files:** Modify `README.md`, Modify `CLAUDE.md`
**Model**: sonnet
**검증**: README 커맨드 표에 새 행이 들어가고 CLAUDE.md 에 결합 메모 섹션이 붙었는지 확인한다. 결합 메모의 회귀 확인 명령이 모두 읽기 전용이고 실제로 실행 가능하면 성공이다.

- [ ] Step 1: `**검증**` 설명 기반 실패 테스트 작성 + 실행 → FAIL 확인
- [ ] Step 2: README 커맨드 표에 행 추가 (블록 I)
- [ ] Step 3: CLAUDE.md 끝에 결합 메모 추가 (블록 J)
- [ ] Step 4: 테스트 실행 → pass 확인
- [ ] Step 5: self-review

**블록 I** — README 커맨드 표

**원본**

```markdown
| `/fast-tasks` | task list | 요구사항 문서 없이 잡일 묶어 처리 |
```

**수정 후**

```markdown
| `/fast-tasks` | task list | 요구사항 문서 없이 잡일 묶어 처리 |
| `/epic <설명>` | 큰 그림 3 파일 | 여러 브레인스토밍으로 나눌 큰 작업 관리 |
```

**블록 J** — CLAUDE.md 파일 끝

**원본**

```markdown
- og-* / worktree 계열 / fast-tasks 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
```

**수정 후**

```markdown
- og-* / worktree 계열 / fast-tasks 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서

## 에픽 단위 브레인스토밍 결합

큰 작업 하나를 여러 번의 브레인스토밍으로 나눠 진행할 때 그 사이를 잇는 맥락을 파일이 나르게 한 기능. spec: `docs/features/2026-08-29-에픽-단위-브레인스토밍/`.

### 핵심 룰

- **세 파일과 그 위치** — `docs/epics/<날짜>-<slug>/` 아래 `overview.md` (큰 그림) · `carry-over.md` (이월 노트) · `forecast.md` (예상도). 피처 폴더는 `docs/features/` 에 그대로 두고 어느 쪽도 다른 쪽 안에 넣지 않는다
- **소속 표식** — 피처 요구사항 문서 머리의 `> **큰 작업**: <폴더명>` 한 줄. 이 형식을 바꾸면 스캔 스크립트와 커맨드 본문을 함께 고쳐야 한다
- **상태 표식** — 큰 그림의 `> **상태**: 진행 중` / `완료`. 줄이 없으면 진행 중으로 본다
- **진행 상태는 저장하지 않는다** — 볼 때마다 산출물 파일로 센다. 체크박스를 파일에 적어두면 갱신이 언젠가 빠지고 그때부터 적힌 것과 실제가 어긋난다
- **없으면 조용히 지나간다** — 진행 중인 큰 작업이 없으면 브레인스토밍의 두 단계를 건너뛰고 안내도 출력하지 않는다
- **예상도는 시작 단계가 읽지 않는다** — 읽으면 다음 주제가 그 예상을 따라가 예상도를 분리한 이유가 사라진다
- **워크트리는 제안만** — 부모 관계를 알려주는 데까지. 만드는 일은 `setting-up-worktrees` 가 한다
- **자동 흐름 비적용** — `auto-brainstorming` 계열에는 넣지 않는다 (요구사항 범위 밖)

### 회귀 패턴

| 누락 / 변경 | 증상 |
|---|---|
| 소속 표식 형식만 한쪽에서 변경 | 피처가 목록에서 조용히 빠진다. 스캔이 표식 없는 피처 수를 함께 보고해 catch |
| 진행 상태를 파일에 저장하는 방식으로 회귀 | 적힌 것과 실제가 어긋난다 |
| 큰 작업이 없을 때 안내 문구 출력 | 큰 작업을 안 쓰는 사용자에게 매번 노이즈 |
| 시작 단계가 예상도를 읽음 | 다음 주제가 예상을 따라가 폭포수로 굳는다 |
| 갱신을 판정이 아니라 의무로 되돌림 | 바뀐 게 없는데 문구만 다듬는 변경이 쌓인다 |
| 브레인스토밍 항목 번호를 밀어서 삽입 | 흐름도와 절차 상세의 번호 참조가 어긋난다. 0.5 / 8.5 를 쓴 이유 |
| 커맨드가 워크트리를 직접 생성 | 만들기와 되돌리기를 떠안고 기존 워크트리 절차와 둘로 갈린다 |

### 회귀 catch grep

```bash
test -f commands/epic.md && test ! -d skills/epic && echo OK
# expected: OK
```

```bash
grep -c "disable-model-invocation: true" commands/epic.md
# expected: 1
```

```bash
python3 -c "import scripts.epic_scan as m; print(len([f for f in ('scan','current_epic','feature_stage','feature_epic') if hasattr(m,f)]))"
# expected: 4
```

```bash
grep -cE "^0\.5\. |^8\.5\. " skills/brainstorming/SKILL.md
# expected: 2
```

```bash
grep -cF "## 큰 작업 맥락" skills/brainstorming/SKILL.md
# expected: 1
```

```bash
grep -rc "epic" skills/auto-brainstorming/SKILL.md
# expected: 0
```

### 영향 범위

- 커맨드 1 신규 + 스킬 본문 1 수정 + 스크립트 2 신규 + fixture 1 + README 1행 + 본 섹션
- `tech-design` / `writing-plans` / `executing-plans` / `js-super-sub-driven` 변경 0 — 큰 작업 단위는 브레인스토밍 경계에서만 갈린다
- `setting-up-worktrees` / `worktree-merge-back` / `worktree-remove` 변경 0 — 제안만 하고 실행은 기존 커맨드
- `scripts/preflight.py` / `scripts/plan_guard.py` / hooks 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
```

## 2. 위험 코드 지점

| 위치 | 분류 | 완화 |
|---|---|---|
| `skills/brainstorming/SKILL.md` (Checklist · Process · 흐름도 · 새 섹션) | side-effect | 이 스킬은 매 세션 상주한다. 새 섹션을 한 화면 분량으로 유지하고 자세한 절차는 `commands/epic.md` 에 둔다 |
| `skills/brainstorming/SKILL.md` 항목 번호 | breaking | 0.5 와 8.5 를 써서 기존 번호 0~9 를 밀지 않는다. Task 4 시나리오 4 가 확인한다 |
| `scripts/epic_scan.py` 소속 표식 정규식 | side-effect | 표식 형식이 어긋난 피처는 조용히 빠진다. 스캔 결과에 표식 없는 피처 목록을 함께 실어 보고 단계에서 드러나게 한다 |
| `scripts/epic_scan.py` 파일 읽기 | side-effect | 읽을 수 없는 파일은 빈 문자열로 처리해 스캔 전체가 죽지 않게 한다 |
| `commands/epic.md` 완료 표시 | side-effect | 상태 줄만 바꾸고 폴더를 지우거나 옮기지 않는다 |
| `docs/epics/` 신설 | side-effect | 큰 작업을 실제로 시작할 때만 만든다. 안 쓰면 폴더가 생기지 않는다 |
| `skills/brainstorming/SKILL.md` 0.5 단계의 조기 종료 | side-effect | 큰 작업이 없을 때 출력이 새면 큰 작업을 안 쓰는 사용자 전원에게 노이즈가 된다. Task 4 시나리오 1 이 확인한다 |
| `skills/brainstorming/SKILL.md` 8.5 단계의 갱신 판정 | side-effect | 판정을 의무로 읽으면 문구만 다듬는 변경이 매번 쌓인다. 근거를 못 적으면 쓰지 않는다는 조건이 안전장치다. Task 4 시나리오 3 이 확인한다 |
| 큰 그림 파일 (형제 워크트리 동시 진행 시) | side-effect | 중간을 고쳐 쓰는 파일이라 되돌려 합칠 때 충돌할 수 있다. 이월 노트와 예상도는 뒤에 붙이기만 해서 영향이 없다 |

## 3. 롤백 전략

task 마다 커밋하므로 문제가 생긴 task 의 커밋만 되돌리면 된다.

| 되돌릴 것 | 방법 |
|---|---|
| Task 1 · 2 · 4 (신규 파일) | 파일 삭제. 다른 파일이 참조하지 않아 부작용이 없다 |
| Task 3 (스킬 수정) | 해당 커밋 revert. 삽입만 했으므로 되돌리면 원래 절차로 정확히 복귀한다 |
| Task 5 (문서) | 해당 커밋 revert |

전체를 되돌려도 기존 흐름에는 영향이 없다. 이 기능은 기존 절차를 고치지 않고 앞뒤에
단계를 붙이는 방식이라, 붙인 것을 떼면 원래대로 돌아간다.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 13:26] [구현계획서-수정]
- **id**: CH-20260829-003
- **이유**: 신규 피처 구현계획 작성 + verifying-spec A축 갭 1건 보강
- **무엇이**: 에픽-단위-브레인스토밍-implementation-plan.md 전체 (task 5개 / 원본·수정 후 블록 10개 / 위험 코드 지점 9행 / 롤백 전략)
- **영향범위**: 소속 표식을 쓰는 지시가 어디에도 없던 갭을 블록 C·H 에 반영. 위험 지점 3행 추가. plan_byte_check 와 plan_guard 모두 통과
- **연관 항목**: CH-20260829-001, CH-20260829-002

### [2026-08-29 13:32] [코드-수정] (batch: tasks 1..5)
- **id**: CH-20260829-004
- **이유**: 큰 작업 하나를 여러 번의 브레인스토밍으로 나눠 진행할 때 그 사이를 잇는 맥락을 대화가 아니라 파일이 나르게 함
- **무엇이**: scripts/epic_scan.py, scripts/tests/test_epic_scan.py, commands/epic.md, skills/brainstorming/SKILL.md, skills/js-super-sub-driven/tests/H25-epic-flow/README.md, skills/js-super-sub-driven/tests/README.md, README.md, CLAUDE.md
- **영향범위**: 브레인스토밍 흐름의 앞뒤에 단계 둘이 붙었다. 기존 대화 절차와 항목 번호 0~9 는 그대로다. tech-design / writing-plans / executing-plans / js-super-sub-driven / auto-* / og-* / 워크트리 계열 변경 0
- **위험 카테고리**: side-effect
- **task별 세부 (5건)**:
  - Task 1: `scripts/epic_scan.py`, `scripts/tests/test_epic_scan.py` — 진행 중 큰 작업 탐지와 소속 피처 단계 판정, 단위 테스트 11건 (`side-effect` — 표식 어긋난 피처가 조용히 빠지지 않도록 별도 목록으로 보고) — commits: `4a2cbdc`
  - Task 2: `commands/epic.md` — 만들기 · 조회 · 완료 표시 (`none`) — commits: `fb77eda`
  - Task 3: `skills/brainstorming/SKILL.md` — 0.5 시작 단계, 8.5 마무리 단계, 흐름도 노드 둘, 큰 작업 맥락 섹션 (`side-effect` — 매 세션 상주 스킬이라 43줄 증가) — commits: `b61881e`
  - Task 4: `skills/js-super-sub-driven/tests/H25-epic-flow/README.md`, `tests/README.md` — 시나리오 4건과 인덱스 갱신 (`none`) — commits: `45f180f`
  - Task 5: `README.md`, `CLAUDE.md` — 커맨드 표 1행, 결합 메모 (`none`) — commits: `21fd06d`
- **실행 중 발견해 고친 것 (2건)**:
  - 계획서 블록 B 대로 넣으면 8.5 항목이 9번 뒤에 붙었다. 8번과 9번 사이로 옮겼다
  - 계획서 블록 E 에 "큰 작업 갱신" 노드 선언이 없어 흐름도에서 연결선만 남았다. 선언을 추가했다. 노드와 연결선 짝을 검사해 확인
  - Task 4 시나리오 4 의 grep 패턴이 `0.5` / `8.5` 를 못 잡아 정정했다
- **검증**: 테스트 118건 전부 통과 (기존 107 + 신규 11). 결합 규칙 185건 수집 정상. 결합 메모의 회귀 확인 명령 6건 모두 기대값 일치
- **연관 commits**: 93e4ad7..HEAD
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260829-001, CH-20260829-002, CH-20260829-003
