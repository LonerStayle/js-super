---
commit_policy: per-task
---

# 스킬목록-전체프로젝트조회 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** `/list-skills` 의 조회 범위를 홈 전체 (현재 프로젝트 / 글로벌 / 다른 프로젝트) 로 확장한다.

**Architecture:** 커맨드는 지시문만 담고, 실제 탐색은 전용 스캔 스크립트 (표준 라이브러리만, 읽기 전용) 가 결정적으로 수행한다. 스크립트가 홈 전체를 훑어 출처 표식 있는 skill 을 세 그룹으로 분류한 JSON 을 돌려주면 메인이 목록으로 렌더링한다. 스크립트 실패 시 기존 두 스코프 조회로 폴백한다.

**Tech Stack:** Python 3 표준 라이브러리 (`os.walk` / `pathlib` / `json` / `argparse`), pytest (단위 테스트), 커맨드 markdown (지시문).

**Spec inputs:**
- 스킬목록-전체프로젝트조회-requirements.md — FR-1 (홈 전체 조회) / FR-2 (프로젝트별 그룹 + 경로) / FR-3 (`/remove-skill` 이동 안내) / FR-4 (프루닝 + 권한 오류 무시) / FR-5 (기존 조회 규칙 유지) / FR-6 (문서·결합 메모 갱신 + evals 무회귀)
- 스킬목록-전체프로젝트조회-tech-design.md — D1 (전용 스크립트) / D2 (`${CLAUDE_PLUGIN_ROOT}` 해석) / D3 (스캔 범위 규칙 + 상향 탐지 + 직접 열거) / D4 (JSON 계약) / D5 (실패 폴백)

---

## 1. 단계별 작업

### Task 1: 스캔 스크립트 + 단위 테스트

**Files:**
- Create: `scripts/skill_scan.py`
- Test: `scripts/tests/test_skill_scan.py`

**Model**: sonnet

**검증**: 임시 디렉터리에 가짜 홈 구조 (마커 있는/없는 skill, `.removed-*`, 숨김·무거운 폴더 아래 프로젝트, 하위 폴더 cwd) 를 만들어 8개 시나리오 — 표식 필터 / removed 제외 / 프루닝 / 세 그룹 분류·중복 배제 / 상향 탐지 (홈 제외 포함) / 설명 폴백 / 접근 오류 무시 / 표식 skill 0개 프로젝트의 다른-프로젝트 목록 제외 — 를 pytest 로 검증. 전부 PASS 가 성공 기준.

- [ ] **Step 1: 실패 테스트 작성 + FAIL 확인 (실행 단계 수행)**

`**검증**:` 설명 기반으로 실행 단계가 `scripts/tests/test_skill_scan.py` 를 직접 작성한다 (기존 `scripts/tests/test_preflight.py` 의 tmp_path fixture 패턴 답습). 계획서에는 테스트 코드를 싣지 않는다.

Run: `python3 -m pytest scripts/tests/test_skill_scan.py -v`
Expected: FAIL (구현 전 — import 오류)

- [ ] **Step 2: 스크립트 구현**

**수정 후** (new file: `scripts/skill_scan.py`):
```python
"""js-super skill 홈 전체 스캔 helper.

`/list-skills` 커맨드가 호출한다. 홈 디렉터리 아래의 `.claude/skills/` 를 찾아
출처 표식(`.js-super-skill.json`)이 있는 skill 만 세 그룹(현재 프로젝트 / 글로벌 /
다른 프로젝트)으로 분류해 JSON 으로 출력한다. 읽기 전용 — 어떤 파일도 쓰지 않는다.

표준 라이브러리만 사용한다. 사용자 프로젝트에는 이 저장소의 가상환경이 없어
시스템 `python3` 로 어디서든 실행돼야 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MARKER_NAME = ".js-super-skill.json"
# 14자리 = YYYYMMDDHHMMSS (/remove-skill 의 safe-rename 타임스탬프 형식)
REMOVED_RE = re.compile(r"\.removed-\d{14}$")

# 홈 스캔에서 내려가지 않는 디렉터리 이름.
# 숨김 디렉터리(이름이 "." 시작)는 이름 규칙으로 별도 프루닝된다.
PRUNE_DIR_NAMES = {
    "Library",
    "Applications",
    "node_modules",
    "site-packages",
    "__pycache__",
    "venv",
    "Music",
    "Movies",
    "Pictures",
    "Public",
}


def read_description(skill_dir: Path) -> str:
    """SKILL.md frontmatter 의 description 1줄. 실패 시 '(설명 없음)'."""
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return "(설명 없음)"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "(설명 없음)"
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            value = line[len("description:"):].strip().strip("\"'")
            return value if value else "(설명 없음)"
    return "(설명 없음)"


def read_created(skill_dir: Path):
    """출처 표식의 created 값. 없거나 못 읽으면 None (파일시스템 시각은 쓰지 않는다)."""
    try:
        data = json.loads((skill_dir / MARKER_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    created = data.get("created")
    return created if isinstance(created, str) else None


def collect_skills(skills_root: Path) -> list:
    """한 `.claude/skills/` 아래에서 출처 표식 있는 skill 항목만 모은다."""
    entries = []
    try:
        children = sorted(skills_root.iterdir(), key=lambda p: p.name)
    except OSError:
        return entries
    for child in children:
        try:
            if not child.is_dir() or REMOVED_RE.search(child.name):
                continue
            if not (child / MARKER_NAME).is_file():
                continue
        except OSError:
            continue
        entry = {
            "slug": child.name,
            "path": str(child),
            "description": read_description(child),
        }
        created = read_created(child)
        if created is not None:
            entry["created"] = created
        entries.append(entry)
    return entries


def find_current_project(cwd: Path, home: Path):
    """cwd 에서 위로 올라가며 `.claude/skills` 를 가진 첫 디렉터리 (홈 자체는 제외)."""
    for cand in [cwd, *cwd.parents]:
        if cand == home:
            return None
        try:
            if (cand / ".claude" / "skills").is_dir():
                return cand
        except OSError:
            continue
    return None


def scan_home_projects(home: Path) -> list:
    """홈 아래 프로젝트 루트(`.claude/skills` 보유) 목록.

    숨김 디렉터리와 PRUNE_DIR_NAMES 는 내려가지 않는다. `.claude` 는 프루닝 전에
    매치한다 (숨김이지만 찾는 대상). 접근 오류는 os.walk 기본 동작으로 무시된다.
    """
    roots = []
    for dirpath, dirnames, _filenames in os.walk(home, topdown=True, followlinks=False):
        current = Path(dirpath)
        # 홈 자체의 `.claude` 는 글로벌 스코프라 프로젝트로 치지 않는다
        if ".claude" in dirnames and current != home:
            try:
                if (current / ".claude" / "skills").is_dir():
                    roots.append(current)
            except OSError:
                pass
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in PRUNE_DIR_NAMES
        ]
    return roots


def scan(home: Path, cwd: Path) -> dict:
    """세 그룹(current_project / global / other_projects) 분류 결과."""
    home = home.resolve()
    cwd = cwd.resolve()
    current_root = find_current_project(cwd, home)
    global_root = home / ".claude" / "skills"

    others = []
    for root in scan_home_projects(home):
        if current_root is not None and root.resolve() == current_root:
            continue
        skills = collect_skills(root / ".claude" / "skills")
        if not skills:
            # 표식 있는 skill 이 하나도 없는 프로젝트는 목록에 내지 않는다 (노이즈 방지)
            continue
        others.append({"root": str(root), "skills": skills})
    others.sort(key=lambda g: g["root"])

    return {
        "current_project": {
            "root": str(current_root) if current_root else None,
            "skills": (
                collect_skills(current_root / ".claude" / "skills")
                if current_root
                else []
            ),
        },
        "global": {
            "root": str(global_root),
            "skills": collect_skills(global_root),
        },
        "other_projects": others,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="js-super skill 홈 전체 스캔 (읽기 전용)")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(json.dumps(scan(args.home, args.cwd), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: 테스트 실행 → PASS 확인**

Run: `python3 -m pytest scripts/tests/test_skill_scan.py -v`
Expected: PASS (8개 시나리오 전부 — 테스트 함수 개수는 묶는 방식에 따라 다를 수 있음)

- [ ] **Step 4: Commit**

```bash
git add scripts/skill_scan.py scripts/tests/test_skill_scan.py
git commit -m "feat: skill_scan.py — /list-skills 홈 전체 스캔 helper + 단위 테스트"
```

### Task 2: 커맨드 본문 개정

**Files:**
- Modify: `commands/list-skills.md:1-69`

**Model**: sonnet

**검증**: grep 3종 — `skill_scan.py` 호출 1건 이상 / 옛 금지 문구 ("다른 프로젝트의 `.claude/skills/` 스캔 금지") 0건 / "다른 프로젝트" 표기 2건 이상 — 전부 통과가 성공 기준.

- [ ] **Step 1: 현재 상태 확인 (FAIL 기대)**

Run: `grep -cF "skill_scan.py" commands/list-skills.md`
Expected: 0 (구현 전)

- [ ] **Step 2: 본문 전체 교체**

**원본** (`commands/list-skills.md:1-69`):
````markdown
---
description: "js-super 가 만든 skill (출처 표식 .js-super-skill.json 보유) 만 프로젝트 + 전체 두 스코프에서 조회."
argument-hint: "(인자 없음)"
disable-model-invocation: true
---

# List Skills 빌더 (js-super skill 조회)

`/new-skill` 로 만든 skill 만 조회합니다. 판별 기준은 각 skill 디렉토리의 출처 표식 파일 `.js-super-skill.json` 존재 여부입니다. 표식 없는 skill (다른 플러그인 / 사용자 직접 생성 / 옛 빌더로 만든 것) 은 목록에 뜨지 않습니다.

## 1. 스캔 대상 (두 스코프만)

- **프로젝트**: `<project-root>/.claude/skills/*/` — 현재 작업 디렉토리(cwd) 기준 `.claude/skills`
- **전체 (글로벌)**: `~/.claude/skills/*/`

**다른 프로젝트의 `.claude/skills/` 는 스캔하지 않습니다.** 현재 프로젝트 + 전체만 봅니다 (중앙 레지스트리 없음 — 다른 프로젝트에서 만든 skill 은 그 프로젝트에서 `/list-skills` 호출 시 보입니다).

## 2. 수집 절차

각 스코프 디렉토리에 대해:

1. LS 도구로 하위 디렉토리(`<slug>/`) 목록 수집
2. 각 `<slug>/` 안에 `.js-super-skill.json` 존재하는지 확인 → **존재하는 것만 통과** (필터)
3. 통과한 각 skill 의 `<slug>/SKILL.md` frontmatter 에서 `description` 1줄 추출
   - 추출 실패 / description 없음 → "(설명 없음)" fallback
4. (선택) `.js-super-skill.json` 의 `created` 값을 읽어 생성 시각 표시 가능

`.removed-<timestamp>` 로 끝나는 디렉토리(`/remove-skill` safe-rename 결과) 는 제외합니다.

## 3. 출력 양식

스코프별 그룹으로 묶어 메인 응답으로 출력. 변경 도구(Write/Edit/Bash mutate) 호출 없음 — 읽기 전용.

```
📋 js-super 가 만든 skill 목록

■ 프로젝트 (<project-root 절대경로>)
- <slug-a> — <description 1줄>
- <slug-b> — <description 1줄>

■ 전체 (글로벌, ~/.claude/skills/)
- <slug-c> — <description 1줄>

(스캔 경로: <project-root>/.claude/skills/, ~/.claude/skills/)
```

- 한 스코프가 비어 있으면 그 그룹에 "- (없음)" 표시.
- 스캔한 실제 경로를 끝에 명시합니다 (cwd 가 프로젝트 루트가 아닐 가능성 catch — 사용자가 위치 확인 가능).

## 4. 빈 결과

양쪽 모두 표식 있는 skill 이 0건이면:

```
ℹ️ js-super 가 만든 skill 이 없습니다.

스캔 경로: <project-root>/.claude/skills/, ~/.claude/skills/

/new-skill 로 새 skill 을 만들면 출처 표식과 함께 생성되어 여기에 표시됩니다.
표식 없는 기존 skill (다른 플러그인 / 직접 생성 / 옛 빌더) 은 이 목록에 뜨지 않습니다.
```

## 5. 금지

- **다른 프로젝트의 `.claude/skills/` 스캔 금지** — 현재 프로젝트 + 전체만. 중앙 레지스트리 도입 X (빌더 단순성 보존)
- **표식 없는 skill 표시 금지** — `.js-super-skill.json` 없는 디렉토리는 목록에서 제외
- **파일 변경 금지** — 읽기 전용 조회. Write / Edit / mutate Bash 호출 X
- **`skills/list-skills/` 로 빌더 변환 금지** — 빌더는 command (자동 발동 사고 방지, META-BUILDER 룰 답습)
- **출처 표식은 신뢰 신호일 뿐 보안 경계 아님** — 사용자가 표식 파일을 수동 복사하면 비-js-super skill 도 목록에 뜰 수 있음 (낮은 빈도, 수용)
````

**수정 후**:
````markdown
---
description: "js-super 가 만든 skill (출처 표식 .js-super-skill.json 보유) 을 홈 전체에서 조회 — 현재 프로젝트 / 글로벌 / 다른 프로젝트 세 그룹."
argument-hint: "(인자 없음)"
disable-model-invocation: true
---

# List Skills 빌더 (js-super skill 조회)

`/new-skill` 로 만든 skill 만 조회합니다. 판별 기준은 각 skill 디렉토리의 출처 표식 파일 `.js-super-skill.json` 존재 여부입니다. 표식 없는 skill (다른 플러그인 / 사용자 직접 생성 / 옛 빌더로 만든 것) 은 목록에 뜨지 않습니다.

## 1. 스캔 대상 (홈 전체)

- **현재 프로젝트**: cwd 에서 위로 올라가며 `.claude/skills/` 를 가진 첫 디렉토리 (홈 자체는 제외 — 홈의 것은 글로벌 스코프). 하위 폴더·워크트리에서 실행해도 올바른 프로젝트를 인식합니다
- **전체 (글로벌)**: `~/.claude/skills/*/`
- **다른 프로젝트**: 홈 디렉토리 아래를 훑어 발견한 나머지 프로젝트들의 `.claude/skills/*/`

숨김 폴더 (`.claude` 제외) 와 시스템·캐시 폴더 (Library, node_modules 등) 는 건너뜁니다. 숨김 폴더 아래의 **다른** 프로젝트는 목록에서 빠집니다 (현재 프로젝트는 직접 열거라 예외).

## 2. 수집 절차 (스캔 스크립트 1회 실행)

Bash 도구로 스캔 스크립트를 한 번 실행합니다 (읽기 전용 — 어떤 파일도 쓰지 않음):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/skill_scan.py"
```

- 출력은 JSON — `current_project` / `global` / `other_projects` 세 그룹. 그룹마다 `root` (절대경로) + `skills` 배열, 항목은 `slug` / `path` / `description` / `created` (있을 때만)
- `description` 은 각 skill 의 `SKILL.md` frontmatter 에서 추출된 값 (실패 시 "(설명 없음)")
- `created` 는 출처 표식 파일의 `created` 값에서만 읽습니다 (없으면 필드·표시 모두 생략)
- `.removed-<timestamp>` 디렉토리 (`/remove-skill` safe-rename 결과) 는 스크립트가 제외합니다

**폴백**: 스크립트 실행이 실패하면 (변수 미해석 / python3 부재 등) 기존 두 스코프만 LS 도구로 조회하고 (cwd 기준 `.claude/skills/` + `~/.claude/skills/`, 표식 필터·removed 제외 동일 적용) 안내 한 줄을 붙입니다: "ℹ️ 홈 전체 스캔을 사용할 수 없어 현재 프로젝트 + 글로벌 두 스코프만 조회했습니다."

## 3. 출력 양식

그룹별로 묶어 메인 응답으로 출력. 변경 도구(Write/Edit/Bash mutate) 호출 없음 — 읽기 전용.

```
📋 js-super 가 만든 skill 목록

■ 현재 프로젝트 (<root 절대경로>)
- <slug-a> — <description 1줄>

■ 전체 (글로벌, ~/.claude/skills/)
- <slug-c> — <description 1줄>

■ 다른 프로젝트
- <root-1 절대경로>
  - <slug-d> — <description 1줄>
- <root-2 절대경로>
  - <slug-e> — <description 1줄>

ℹ️ 다른 프로젝트의 skill 을 지우려면 그 프로젝트로 이동해 /remove-skill 을 실행하세요.
```

- 한 그룹이 비어 있으면 그 그룹에 "- (없음)" 표시.
- **다른 프로젝트** 그룹에는 표식 있는 skill 이 1개 이상인 프로젝트만 나옵니다 (표식 skill 이 없는 프로젝트 루트는 스크립트가 제외).
- 현재 프로젝트의 `root` 가 null 이면 (프로젝트 밖에서 실행) 헤더를 "■ 현재 프로젝트 (없음 — 프로젝트 밖에서 실행)" 로 표시하고 항목 없이 넘어갑니다.
- 다른 프로젝트 그룹이 하나라도 있으면 `/remove-skill` 이동 안내 한 줄을 반드시 포함.
- `created` 값이 있으면 항목 끝에 생성 시각을 덧붙일 수 있습니다 (선택).

## 4. 빈 결과

세 그룹 모두 표식 있는 skill 이 0건이면:

```
ℹ️ js-super 가 만든 skill 이 없습니다.

/new-skill 로 새 skill 을 만들면 출처 표식과 함께 생성되어 여기에 표시됩니다.
표식 없는 기존 skill (다른 플러그인 / 직접 생성 / 옛 빌더) 은 이 목록에 뜨지 않습니다.
```

## 5. 금지

- **표식 없는 skill 표시 금지** — `.js-super-skill.json` 없는 디렉토리는 목록에서 제외
- **파일 변경 금지** — 읽기 전용 조회. Write / Edit / mutate Bash 호출 X (스캔 스크립트도 읽기 전용)
- **다른 프로젝트 skill 원격 삭제 금지** — 삭제는 해당 프로젝트로 이동해 `/remove-skill` (안내만)
- **`skills/list-skills/` 로 빌더 변환 금지** — 빌더는 command (자동 발동 사고 방지, META-BUILDER 룰 답습)
- **출처 표식은 신뢰 신호일 뿐 보안 경계 아님** — 사용자가 표식 파일을 수동 복사하면 비-js-super skill 도 목록에 뜰 수 있음 (낮은 빈도, 수용)
````

- [ ] **Step 3: 검증 grep → PASS 확인**

Run:
```bash
grep -cF "skill_scan.py" commands/list-skills.md
grep -c '다른 프로젝트의 `.claude/skills/` 스캔 금지' commands/list-skills.md
grep -cF "다른 프로젝트" commands/list-skills.md
```
Expected: 1 이상 / 0 / 2 이상

- [ ] **Step 4: Commit**

```bash
git add commands/list-skills.md
git commit -m "feat: /list-skills 홈 전체 조회 — 스캔 스크립트 호출 + 세 그룹 출력 + 폴백"
```

### Task 3: README 표현 갱신 (2곳, mechanical 묶음)

**Files:**
- Modify: `README.md:482`, `README.md:529`

**Model**: haiku

**검증**: `grep -c "프로젝트 + 전체" README.md` 가 0 이면 성공 (옛 두-스코프 표현 잔존 없음).

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "프로젝트 + 전체" README.md`
Expected: 2 (수정 전)

- [ ] **Step 2: 소개 불릿 교체**

**원본** (`README.md:482`):
```markdown
- `/list-skills` — **js-super 가 만든 skill 만** 모아 보기 (현재 프로젝트 + 전체)
```

**수정 후**:
```markdown
- `/list-skills` — **js-super 가 만든 skill 만** 홈 전체에서 모아 보기 (현재 프로젝트 / 글로벌 / 다른 프로젝트)
```

- [ ] **Step 3: 유틸리티 표 행 교체**

**원본** (`README.md:529`):
```markdown
| `/list-skills` | js-super 가 만든 skill 만 조회 (프로젝트 + 전체) |
```

**수정 후**:
```markdown
| `/list-skills` | js-super 가 만든 skill 만 홈 전체 조회 (현재 / 글로벌 / 다른 프로젝트) |
```

- [ ] **Step 4: 검증 grep → PASS 확인**

Run: `grep -c "프로젝트 + 전체" README.md`
Expected: 0

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README /list-skills 안내를 홈 전체 조회로 갱신 (2곳)"
```

### Task 4: CLAUDE.md v2.7 결합 메모 개정 (3곳, mechanical 묶음)

**Files:**
- Modify: `CLAUDE.md:969`, `CLAUDE.md:981`, `CLAUDE.md:1013`

**Model**: sonnet

**의존**: Task 5 와 같은 파일 (`CLAUDE.md`) 을 수정하므로 병렬 금지 — Task 4 → Task 5 순서로 순차 실행. Step 1 의 「아래 "스킬목록 홈 전체 조회 결합" 참조」 문구는 Task 5 가 만드는 섹션을 가리키며, Task 5 완료 시점에 해소된다.

**검증**: 옛 문구 grep 0건 ("다른 프로젝트 스캔 X" / 옛 회귀 표 행) + 새 문구 grep 1건 이상 ("FR-2 공식 폐지") + v2.7 섹션 헤더 grep 은 그대로 1건 이상 — 전부 만족이 성공 기준.

- [ ] **Step 1: 핵심 룰 D-3 교체**

**원본** (`CLAUDE.md:969`):
```markdown
- **D-3 조회/삭제 범위 = 현재 프로젝트 cwd `.claude/skills` + 전체** — 다른 프로젝트 스캔 X (중앙 레지스트리 없음)
```

**수정 후**:
```markdown
- **D-3 삭제 범위 = 현재 프로젝트 cwd `.claude/skills` + 전체** — 조회는 스킬목록-전체프로젝트조회 피처 (2026-08-16) 로 홈 전체로 확장됨 (아래 "스킬목록 홈 전체 조회 결합" 참조). 삭제는 그대로 두 스코프 (중앙 레지스트리 없음)
```

- [ ] **Step 2: 회귀 패턴 표 행 교체**

**원본** (`CLAUDE.md:981`):
```markdown
| list-skills 다른 프로젝트 스캔 추가 | FR-2 "다른 프로젝트 안 보임" 위반 + 빌더 단순성 손상 |
```

**수정 후**:
```markdown
| list-skills 조회가 두 스코프 (cwd + 글로벌) 로 회귀 | 홈 전체 조회 피처 (2026-08-16, FR-2 공식 폐지) 무력화 — "스킬목록 홈 전체 조회 결합" 참조 |
```

- [ ] **Step 3: 영향 범위의 범위 밖 항목 교체**

**원본** (`CLAUDE.md:1013`):
```markdown
- 범위 밖: 비-js-super 강제 삭제 우회 / 옛 마커 없는 skill 마이그레이션 / 다른 프로젝트 조회·삭제
```

**수정 후**:
```markdown
- 범위 밖: 비-js-super 강제 삭제 우회 / 옛 마커 없는 skill 마이그레이션 / 다른 프로젝트 삭제 (조회는 스킬목록-전체프로젝트조회 피처로 이후 채택됨)
```

- [ ] **Step 4: 검증 grep → PASS 확인**

Run:
```bash
grep -c "다른 프로젝트 스캔 X" CLAUDE.md
grep -c '스캔 추가 | FR-2' CLAUDE.md
grep -cF "FR-2 공식 폐지" CLAUDE.md
grep -cF "## new-skill-enhanced — 스코프 분기 + 출처 표식 결합 (v2.7+)" CLAUDE.md
```
Expected: 0 / 0 / 1 이상 / 1 이상

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md v2.7 메모 개정 — 조회 범위 홈 전체 확장 반영 (FR-2 공식 폐지)"
```

### Task 5: CLAUDE.md 신규 결합 메모 추가

**Files:**
- Modify: `CLAUDE.md:1772-1774` (파일 끝에 신규 섹션 append)

**Model**: sonnet

**의존**: Task 4 이후 순차 실행 (같은 파일 `CLAUDE.md` 수정 — 병렬 금지). Task 4 가 참조하는 "스킬목록 홈 전체 조회 결합" 섹션을 본 task 가 만든다.

**검증**: 신규 섹션 헤더 grep 1건 이상 + 섹션 안 확인용 명령 (bash 블록 + `# expected:`) 이 eval 러너 파싱 형식을 지키는지 — Task 6 의 evals 실행에서 "새로 깨짐 0" 으로 최종 확인.

- [ ] **Step 1: 파일 끝에 섹션 추가**

**원본** (`CLAUDE.md:1772-1774`):
```markdown
- 본 파일의 코드 블록 형식이나 `# expected:` 주석 형식을 바꾸면 러너가 조용히 룰을 놓친다. 러너는 파싱된 룰 수가 직전 실행보다 줄면 경고한다. 절대 수치를 assert 로 박지는 않는다 (자산이 계속 늘어나는 저장소에서 절대값 검사는 매 릴리즈에 마찰을 부과한다)
- fixture README (`skills/*/tests/**/*.md`) 도 같은 형식으로 읽힌다. 두 원천을 합쳐 111건이다
- `evals/` 는 Claude Code 의 자동 로드 경로 밖이라 사용자 세션에 안 올라간다
```

**수정 후**:
````markdown
- 본 파일의 코드 블록 형식이나 `# expected:` 주석 형식을 바꾸면 러너가 조용히 룰을 놓친다. 러너는 파싱된 룰 수가 직전 실행보다 줄면 경고한다. 절대 수치를 assert 로 박지는 않는다 (자산이 계속 늘어나는 저장소에서 절대값 검사는 매 릴리즈에 마찰을 부과한다)
- fixture README (`skills/*/tests/**/*.md`) 도 같은 형식으로 읽힌다. 두 원천을 합쳐 111건이다
- `evals/` 는 Claude Code 의 자동 로드 경로 밖이라 사용자 세션에 안 올라간다

## 스킬목록 홈 전체 조회 결합 (스킬목록-전체프로젝트조회)

`/list-skills` 의 조회 범위를 홈 전체로 확장 — 현재 프로젝트 / 글로벌 / 다른 프로젝트 세 그룹. 탐색은 `scripts/skill_scan.py` (표준 라이브러리만, 읽기 전용) 가 수행하고 커맨드는 렌더링만 한다. v2.7 의 FR-2 "다른 프로젝트 안 보임" 은 이 피처로 **공식 폐지** (사용자 결정). spec: `docs/features/2026-08-16-스킬목록-전체프로젝트조회/`.

### 핵심 룰

- **L-1 커맨드 ↔ 스크립트 JSON 계약** — 스크립트 출력 키 (`current_project` / `global` / `other_projects`, 각 그룹 `root` + `skills[]`, 항목 `slug`/`path`/`description`/`created`) 를 바꾸면 커맨드 본문 § 2 도 동시 수정. 한쪽만 바꾸면 목록이 조용히 빈다
- **L-2 표식 필터 유지** — `.js-super-skill.json` 있는 것만 목록에. 갈래 C (표식 없는 skill 표시) 는 미채택
- **L-3 원격 삭제 금지** — 다른 프로젝트 skill 은 안내만 (해당 프로젝트에서 `/remove-skill` 실행)
- **L-4 스크립트 실패 폴백** — 기존 두 스코프 (cwd + 글로벌) LS 조회로 격하 + 안내 한 줄. 스크립트 실패가 조회 커맨드를 죽이면 안 됨
- **L-5 현재 프로젝트 = 상향 탐지 + 직접 열거** — cwd 에서 위로 올라가 `.claude/skills` 보유 첫 디렉토리 (홈 자체 제외). 숨김 경로 (워크트리) 아래여도 현재 그룹에는 나옴
- **L-6 읽기 전용** — 스크립트·커맨드 모두 파일 변경 없음

### 회귀 패턴

| 누락 | 증상 |
|---|---|
| 스크립트 JSON 키만 변경 (커맨드 미동기) | 목록이 조용히 빔 (L-1) |
| 커맨드가 옛 "다른 프로젝트 스캔 금지" 로 회귀 | 홈 전체 조회 무력화 — 본 피처 무화 |
| 표식 필터 제거 | 갈래 C 무단 도입 — `/remove-skill` 로 못 지우는 항목 노출 |
| 프루닝 (숨김·무거운 폴더) 제거 | 스캔이 분 단위로 느려짐 + 워크트리 사본 중복 노출 |
| 폴백 제거 | 플러그인 루트 변수 미지원 하네스에서 조회 커맨드 전체 사망 |

### 회귀 catch grep

```bash
# 스크립트 존재 + 커맨드가 호출
test -f scripts/skill_scan.py && grep -cF "skill_scan.py" commands/list-skills.md
# expected: >= 1

# 옛 금지 조항 잔존 catch
grep -c '다른 프로젝트의 `.claude/skills/` 스캔 금지' commands/list-skills.md
# expected: 0

# 세 그룹 JSON 계약 (커맨드 ↔ 스크립트 동기)
grep -cF "other_projects" commands/list-skills.md scripts/skill_scan.py
# expected: 각 >= 1

# 폴백 존재
grep -cF "홈 전체 스캔을 사용할 수 없어" commands/list-skills.md
# expected: >= 1

# 단위 테스트 존재 + import 가능
test -f scripts/tests/test_skill_scan.py && python3 -c "from scripts.skill_scan import scan; print('OK')"
# expected: OK

# 결합 메모 본문 존재
grep -cF "## 스킬목록 홈 전체 조회 결합" CLAUDE.md
# expected: >= 1
```

### 영향 범위

- `commands/list-skills.md` + `scripts/skill_scan.py` (신규) + `scripts/tests/test_skill_scan.py` (신규) + `README.md` 2곳 + `CLAUDE.md` (v2.7 메모 개정 + 본 섹션). 버전 bump 는 main 전용 룰에 따라 main 에서
- `commands/new-skill.md` / `commands/remove-skill.md` — 변경 0 (출처 표식 규약 그대로. 3 커맨드 동시 수정 룰은 규약 변경 시에만 발동)
- og-* / auto-* / worktree 계열 / `scripts/preflight.py` / hooks 영향 0
````

- [ ] **Step 2: 검증 grep → PASS 확인**

Run: `grep -cF "## 스킬목록 홈 전체 조회 결합" CLAUDE.md`
Expected: 1 이상

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 신규 결합 메모 — 스킬목록 홈 전체 조회 (L-1~L-6 + 회귀 grep)"
```

### Task 6: E2E 검증 + evals 무회귀 확인

**Files:**
- Test: (코드 변경 없음 — 검증 전용)

**Model**: sonnet

**검증**: (1) scratchpad 가짜 홈에서 스크립트 실행 → 세 그룹 JSON 이 기대 분류와 일치, (2) 실제 홈에서 1회 실행 → 오류 없이 완주 + 유효한 JSON (소요 시간은 참고 보고), (3) evals 러너 실행 → 기존 대비 "새로 깨짐" 0.

- [ ] **Step 1: scratchpad 가짜 홈 E2E**

Run: scratchpad 아래에 가짜 홈 (마커 있는 skill 2곳 + 글로벌 1곳 + 숨김 폴더 아래 1곳) 구성 후
`python3 scripts/skill_scan.py --home <가짜홈> --cwd <가짜홈/proj-a/sub>`
Expected: current_project = proj-a / global 1건 / other_projects 에 proj-b 만 (숨김 폴더 아래는 제외)

- [ ] **Step 2: 실제 홈 1회 실행**

Run: `time python3 scripts/skill_scan.py > /dev/null`
Expected: exit 0 + 유효한 JSON (시간은 참고 보고)

- [ ] **Step 3: evals 무회귀**

Run: `python3 evals/run.py` (또는 `.venv/bin/python evals/run.py` — venv 가 있는 루트에서)
Expected: 새로 깨짐 0 (신규 결합 메모의 grep 룰 포함 전부 통과)

## 2. 위험 코드 지점

- `scripts/skill_scan.py:scan_home_projects` — side-effect: 홈 전체 탐색이 보호 폴더에 닿아 접근 오류·지연 가능 (mitigation: 숨김·무거운 폴더 프루닝 상수 + os.walk 오류 무시 + followlinks=False)
- `commands/list-skills.md` §2 ↔ `scripts/skill_scan.py` JSON 키 — breaking: 한쪽만 변경 시 목록이 조용히 빔 (mitigation: CLAUDE.md 신규 결합 메모 L-1 + 단위 테스트가 키 구조 고정)
- `CLAUDE.md:969-1013` v2.7 메모 — breaking: 미갱신 시 다음 세션이 본 변경을 회귀로 판정 (mitigation: Task 4 개정 + Task 6 evals 확인)
- `commands/list-skills.md` §2 폴백 — breaking: `${CLAUDE_PLUGIN_ROOT}` 미지원 하네스에서 스크립트 경로 해석 실패 (mitigation: 두 스코프 LS 조회 폴백 절차 명시)
- `scripts/skill_scan.py:collect_skills` — side-effect: 위조 표식 노출 표면 확대 (mitigation: 기존 규약 유지 — 신뢰 신호일 뿐, 읽기 전용이라 피해 없음)

## 3. 롤백 전략

- Code: revert commits (Task 1~5 각 1 commit — `git log --oneline` 으로 SHA 확인 후 `git revert <SHA>` 역순)
- DB: 해당 없음 (영구 데이터 없음)
- Config: 해당 없음 (플래그 없음 — 커맨드 본문 revert 로 즉시 옛 동작 복원)

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-17 20:39] [구현계획서-수정]
- **id**: CH-20260817-003
- **이유**: 신규 구현계획서 작성 (code-pretty 1블록 정리 + 용어집 병렬 생성 + verifying-spec 무맥락 검증 지적 4건 채택 반영 — Task 4·5 의존 선언 / 표식 0개 프로젝트 제외 / null root 렌더링 규칙 / upstream 오기 정정 연동)
- **무엇이**: 스킬목록-전체프로젝트조회-implementation-plan.md 전체 (Task 1~6 + §2 위험 코드 지점 + §3 롤백 전략)
- **영향범위**: 없음 (최초 생성). 용어집 스킬목록-전체프로젝트조회-glossary.md 파생 생성
- **연관 항목**: CH-20260817-001, CH-20260817-002

### [2026-08-17 21:11] [코드-수정] (batch: tasks 1..6)
- **id**: CH-20260817-004
- **이유**: `/list-skills` 조회 범위를 홈 전체(현재 프로젝트 / 글로벌 / 다른 프로젝트)로 확장. 전체 task 실행 후 적대적 테스트 2종(기능 공격 / 문서 계약 감사)에서 나온 결함 15건까지 반영
- **무엇이**: scripts/skill_scan.py, scripts/tests/test_skill_scan.py, commands/list-skills.md, README.md, CLAUDE.md, evals/baseline.json
- **영향범위**: `/list-skills` 조회 흐름 전용. `/new-skill`·`/remove-skill` 본문 변경 0 (출처 표식 규약 그대로), og-* / auto-* / worktree 계열 / preflight / hooks 영향 0
- **위험 카테고리**: side-effect (홈 전체 순회), breaking (커맨드↔스크립트 JSON 계약, v2.7 계약 폐지)
- **task별 세부 (6건)**:
  - Task 1: `scripts/skill_scan.py` 전체 + `scripts/tests/test_skill_scan.py` — 홈 전체 탐색 helper 신설, 단위 테스트 (`side-effect`) — commits: `ae7aae5`
  - Task 2: `commands/list-skills.md:1-69` — 스캔 스크립트 호출 + 세 그룹 출력 + 폴백 (`breaking`) — commits: `e68fa7e`
  - Task 3: `README.md:482,529` — 두-스코프 표현을 홈 전체로 (`none`) — commits: `06fb738`
  - Task 4: `CLAUDE.md:969,981,1013` — v2.7 메모 개정, FR-2 공식 폐지 (`breaking`) — commits: `068343b`
  - Task 5: `CLAUDE.md` 말미 — 신규 결합 메모 L-1~L-6 + 회귀 확인 명령 (`none`) — commits: `c28541d`
  - Task 6: 검증 전용 — 가짜 홈 E2E, 실제 홈 1회(4.2초, 유효 JSON), evals 새로 깨짐 0 (`none`) — commits: 없음
- **적대적 테스트 반영 (계획 외 추가, 사용자 요청)**:
  - 크래시 3건 — 마커가 dict 아닌 유효 JSON / 비-UTF8 SKILL.md / SKILL.md 가 named pipe (`side-effect`) — commits: `ce570fd`
  - 오탐 6건 — 문장 안 따옴표 잘림, BOM 미인식, YAML 블록 스칼라 오출력, 심링크로 홈 밖 유출·별칭 중복, 홈 밖 cwd 에서 홈 조상까지 상승, Public·venv 이름 프로젝트 누락 (`breaking`) — commits: `ce570fd`
  - 문서 결함 6건 — 환경변수가 슬래시 커맨드에서 안 채워져 핵심 경로가 항상 실패하던 문제, root 의미 차이 미명시, null root 안내 오류, 폴백 절차 결손 3단계, v2.7 D-1 의 폐지 계약 인용 (`breaking`) — commits: `44c8543`
  - 회귀 룰 무력화 3건 — JSON 키 전수 대조로 교체, 판정 불가 기대값 숫자화, 기준선 미반영 (`none`) — commits: `44c8543`, `f9fafb1`
- **연관 commits**: `262854d..f9fafb1` (8건)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260817-003
