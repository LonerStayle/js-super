---
commit_policy: per-task
---

# 산출물 깊이 선택 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `subagent-driven-development` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 정식 문서 파이프라인과 auto-flow 에 "산출물 깊이 선택" 을 넣는다 — 피처 단위로 2개 (requirements + tech-design) 또는 3개 (+ implementation-plan) 를 선택. 정식 플로우는 tech-design 승인 직후 게이트 3지선다, auto-flow 는 모델 자동 판정 (default 3). 깊이 표식은 tech-design frontmatter `depth: 2`.

**Architecture:** 표식 1개 (tech-design frontmatter) 를 single source of truth 로 두고, 결정 표면 2곳 (Gate #12 확장 / auto-tech-design Step 7 판정) 이 쓰고, 소비자 4곳 (change-history 라우팅 / change-propagation matrix / preflight human_reason / write-plan 승격) 이 읽는다. 신규 파일은 fixture README 1개뿐 — 나머지는 기존 본문 확장 + `scripts/preflight.py` additive 함수 1개.

**실행 후 최종 검증 (사용자 요청):** 모든 task 완료 후 Task 14 (전수 검증) 에 더해, 실행 세션 끝에서 수정 파일 전체 diff 리뷰 + 기존/신규 회귀 grep 재실행의 강도 높은 최종 검증 패스를 별도로 수행한다.

## 1. 단계별 작업

### Task 1: scripts/preflight.py — depth 지원 (TDD)

**Files:**
- Modify: `scripts/preflight.py`
- Modify: `scripts/tests/test_preflight.py`

**Model**: sonnet

- [ ] **Step 1: 실패하는 테스트 추가** — `scripts/tests/test_preflight.py` 끝에 append:

```python


def test_feature_depth_marker_2(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 2\ndepth_reason: 사용자 선택\n---\n# x\n## 변경이력\n")
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path) == 2


def test_feature_depth_no_frontmatter(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "# x\n## 변경이력\n")
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path) == 3


def test_feature_depth_promoted_3(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 3\ndepth_reason: 승격\n---\n# x\n## 변경이력\n")
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path) == 3


def test_feature_depth_missing_dir(tmp_path):
    from scripts.preflight import feature_depth
    assert feature_depth(tmp_path / "nope") == 3


def test_execute_plan_mode_check_depth2_hint(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 2\n---\n# x\n## 변경이력\n")
    result = execute_plan_mode_check(tmp_path / "foo-implementation-plan.md")
    assert result.ok is False
    assert "승격" in result.human_reason


def test_subagent_task_entry_check_depth2_hint(tmp_path):
    td = tmp_path / "foo-tech-design.md"
    _write(td, "---\ndepth: 2\n---\n# x\n## 변경이력\n")
    result = subagent_task_entry_check(tmp_path / "foo-implementation-plan.md")
    assert result.ok is False
    assert "승격" in result.human_reason
```

- [ ] **Step 2: 테스트 실패 확인** — `python3 -m pytest scripts/tests/test_preflight.py -q` → 신규 6건 fail (feature_depth ImportError / hint 부재)
- [ ] **Step 3: `feature_depth()` 구현** — `scripts/preflight.py` 파일 끝에 append:

```python


_DEPTH_LINE = re.compile(r"^depth:\s*([23])\s*$", re.MULTILINE)


def feature_depth(feature_dir: Path) -> int:
    """피처 폴더의 산출물 깊이 (v2.9.0+ 산출물 깊이 선택).

    *-tech-design.md 의 frontmatter 에 depth: 2 가 명시된 경우에만 2 (2-doc
    확정 트랙). 필드 부재 / depth: 3 / 파일 부재 / 파싱 실패는 전부 3 (기존
    3-doc 기본 트랙). 판독 규칙 엄격 — 안전한 방향(3)으로 fallback.
    """
    if not feature_dir.exists():
        return 3
    for md in sorted(feature_dir.glob("*-tech-design.md")):
        m = _FRONTMATTER_COMMIT_POLICY.match(md.read_text(encoding="utf-8"))
        if not m:
            continue
        line = _DEPTH_LINE.search(m.group(1))
        if line and line.group(1) == "2":
            return 2
    return 3
```

- [ ] **Step 4: plan 부재 human_reason 보강 (execute_plan_mode_check)**

**원본** (`scripts/preflight.py:99-104`):
```python
    if not plan_path.exists():
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"구현계획서를 찾을 수 없습니다: {plan_path}",
        )
```

**수정 후**:
```python
    if not plan_path.exists():
        hint = ""
        if feature_depth(plan_path.parent) == 2:
            hint = (
                " — 이 피처는 2개 문서로 확정된 트랙입니다."
                " 구현이 필요해졌다면 /write-plan 으로 승격하세요."
            )
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"구현계획서를 찾을 수 없습니다: {plan_path}{hint}",
        )
```

- [ ] **Step 5: plan 부재 human_reason 보강 (subagent_task_entry_check)**

**원본** (`scripts/preflight.py:111-116`):
```python
    if not plan_path.exists():
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"플랜 파일이 존재하지 않습니다: {plan_path}",
        )
```

**수정 후**:
```python
    if not plan_path.exists():
        hint = ""
        if feature_depth(plan_path.parent) == 2:
            hint = (
                " — 이 피처는 2개 문서로 확정된 트랙입니다."
                " 구현이 필요해졌다면 /write-plan 으로 승격하세요."
            )
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"플랜 파일이 존재하지 않습니다: {plan_path}{hint}",
        )
```

- [ ] **Step 6: 전체 테스트 pass 확인** — `python3 -m pytest scripts/tests/ -q` → 전부 pass (기존 테스트 회귀 0). commit.

---

### Task 2: skills/tech-design/SKILL.md — Gate #12 3지선다 확장

**Files:**
- Modify: `skills/tech-design/SKILL.md`

**Model**: haiku

- [ ] **Step 1: Checklist 9번 재기술**

**원본** (`skills/tech-design/SKILL.md:71`):
```markdown
9. **다음 단계 진입 확인** — change-history 직후 사용자에게 명시적 yes/no 게이트. On `yes` → invoke `writing-plans` via Skill tool. On `no` → exit with notice telling the user to run /write-plan later. (v1.1.12+ — restored)
```

**수정 후**:
```markdown
9. **다음 단계 진입 확인 (산출물 깊이 선택)** — change-history 직후 사용자에게 3지선다 게이트 (Gate #12). "구현계획서까지 진행 (3개)" → invoke `writing-plans` via Skill tool. "여기서 종료 (2개 확정)" → tech-design frontmatter 에 `depth: 2` 기록 + [개발방향-수정] entry + 종료 안내. "나중에 결정" → 표식 없이 exit with notice telling the user to run /write-plan later. (v1.1.12+ restored · 깊이 선택 확장)
```

- [ ] **Step 2: 산출물 blockquote 조건부 문구**

**원본** (`skills/tech-design/SKILL.md:90`):
```markdown
> **다음 단계 안내**: 이 문서는 기술 설계서입니다 (아키텍처 / 컴포넌트 / 데이터 / 인터페이스 / 결정 / 위험 / 테스트 전략). `<slug>-requirements.md` (PRD) 를 기반으로 작성되고, 다음 단계 `<slug>-implementation-plan.md` (단계별 계획) 의 입력이 됩니다. 다음 단계로 `writing-plans` skill (또는 `/write-plan` 슬래시) 을 호출해서 구현 계획을 만드세요. 단계별 구현 task 는 여기 박지 마세요 — 그건 다음 산출물 (plan) 에 들어갑니다.
```

**수정 후**:
```markdown
> **다음 단계 안내**: 이 문서는 기술 설계서입니다 (아키텍처 / 컴포넌트 / 데이터 / 인터페이스 / 결정 / 위험 / 테스트 전략). `<slug>-requirements.md` (PRD) 를 기반으로 작성됩니다. 3개 트랙이면 다음 단계 `<slug>-implementation-plan.md` (단계별 계획) 의 입력이 됩니다 (`writing-plans` skill 또는 `/write-plan` 슬래시). 2개 확정 트랙 (frontmatter `depth: 2`) 이면 이 문서가 마지막 산출물입니다. 단계별 구현 task 는 여기 박지 마세요 — 그건 다음 산출물 (plan) 에 들어갑니다.
```

- [ ] **Step 3: dot 다이어그램 노드 추가**

**원본** (`skills/tech-design/SKILL.md:123-125`):
```dot
    "Ask: proceed to writing-plans? (Gate #12, v1.1.12+ restored)" [shape=diamond];
    "Auto-invoke writing-plans skill" [shape=doublecircle];
    "Exit: tell user to run /write-plan later" [shape=oval];
```

**수정 후**:
```dot
    "Ask: 산출물 깊이? (Gate #12, 3지선다)" [shape=diamond];
    "Auto-invoke writing-plans skill" [shape=doublecircle];
    "Record depth: 2 + exit (2개 확정)" [shape=oval];
    "Exit: tell user to run /write-plan later" [shape=oval];
```

- [ ] **Step 4: dot 다이어그램 edge 분기**

**원본** (`skills/tech-design/SKILL.md:145-147`):
```dot
    "Invoke change-history" -> "Ask: proceed to writing-plans? (Gate #12, v1.1.12+ restored)";
    "Ask: proceed to writing-plans? (Gate #12, v1.1.12+ restored)" -> "Auto-invoke writing-plans skill" [label="yes"];
    "Ask: proceed to writing-plans? (Gate #12, v1.1.12+ restored)" -> "Exit: tell user to run /write-plan later" [label="no"];
```

**수정 후**:
```dot
    "Invoke change-history" -> "Ask: 산출물 깊이? (Gate #12, 3지선다)";
    "Ask: 산출물 깊이? (Gate #12, 3지선다)" -> "Auto-invoke writing-plans skill" [label="구현계획서까지 진행 (3개)"];
    "Ask: 산출물 깊이? (Gate #12, 3지선다)" -> "Record depth: 2 + exit (2개 확정)" [label="여기서 종료 (2개 확정)"];
    "Ask: 산출물 깊이? (Gate #12, 3지선다)" -> "Exit: tell user to run /write-plan later" [label="나중에 결정"];
```

- [ ] **Step 5: Gate #12 본문 intro**

**원본** (`skills/tech-design/SKILL.md:264-266`):
```markdown
**9. Ask the proceed-to-writing-plans gate (v1.1.12+ — restored)**

After change-history is logged, ask the user explicitly. Tech-design → implementation-plan 전환은 의사결정 깊이가 다른 단계 (구현 계획에 commit 하는 시점) 라서 자동승인보다 명시적 게이트가 안전하다는 사용자 신고 반영.
```

**수정 후**:
```markdown
**9. Ask the proceed-to-writing-plans gate (v1.1.12+ restored · 산출물 깊이 선택 확장)**

After change-history is logged, ask the user explicitly. Tech-design → implementation-plan 전환은 의사결정 깊이가 다른 단계 (구현 계획에 commit 하는 시점) 라서 자동승인보다 명시적 게이트가 안전하다는 사용자 신고 반영. 이 게이트가 산출물 깊이 (2개/3개) 의 결정 지점이기도 하다 — 실제 분기 지점 (tech-design → writing-plans 전환) 과 일치하고, 문서를 다 본 상태라 가장 정보가 많은 시점이다.
```

- [ ] **Step 6: Gate #12 AskUserQuestion 3지선다**

**원본** (`skills/tech-design/SKILL.md:276-282`):
```json
  "question": "<slug>-tech-design.md 가 확정됐습니다. 다음 단계 (구현계획서 작성) 로 진행할까요?",
  "header": "다음 단계",
  "multiSelect": false,
  "options": [
    {"label": "예 — 진행", "description": "/write-plan 자동 invoke"},
    {"label": "아니오 — 종료", "description": "나중에 /write-plan 수동 실행"}
  ]
```

**수정 후**:
```json
  "question": "<slug>-tech-design.md 가 확정됐습니다. 산출물을 어디까지 만들까요?",
  "header": "산출물 깊이",
  "multiSelect": false,
  "options": [
    {"label": "구현계획서까지 진행 (3개)", "description": "/write-plan 자동 invoke — 기존 기본 흐름"},
    {"label": "여기서 종료 (2개 확정)", "description": "frontmatter depth: 2 기록 — 이 피처는 tech-design 까지"},
    {"label": "나중에 결정", "description": "표식 없이 종료 — 나중에 /write-plan 수동 실행"}
  ]
```

- [ ] **Step 7: Prose fallback 문구**

**원본** (`skills/tech-design/SKILL.md:289`):
```markdown
<slug>-tech-design.md 가 확정됐습니다. 다음 단계 (구현계획서 작성) 로 진행할까요? — yes / no
```

**수정 후**:
```markdown
<slug>-tech-design.md 가 확정됐습니다. 산출물을 어디까지 만들까요? — 3개 진행 / 2개 확정 / 나중에
```

- [ ] **Step 8: 분기 동작 bullets**

**원본** (`skills/tech-design/SKILL.md:292-294`):
```markdown
- The user may reply in any language; parse intent.
- On `yes` → invoke the `writing-plans` skill via Skill tool. NEVER cross without approval.
- On `no` → emit `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` and stop.
```

**수정 후**:
```markdown
- The user may reply in any language; parse intent.
- On "구현계획서까지 진행 (3개)" → invoke the `writing-plans` skill via Skill tool. NEVER cross without approval.
- On "여기서 종료 (2개 확정)" → `<slug>-tech-design.md` 맨 위에 frontmatter (`depth: 2` + `depth_reason: 사용자 선택`) 를 기록하고, `change-history` 로 [개발방향-수정] entry (이유: 2-doc 확정) 를 남긴 뒤 `ℹ️ 이 피처는 2개 문서로 확정됐습니다. 구현이 필요해지면 /write-plan 으로 승격하세요.` 를 출력하고 stop.
- On "나중에 결정" → emit `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` and stop (표식 기록 없음).
```

- [ ] **Step 9: Process Flow 요약 동기화**

**원본** (`skills/tech-design/SKILL.md:365-369`):
```markdown
5. **Proceed-to-writing-plans gate** (v1.1.12+ restored):

   **Gate #12 — proceed-to-writing-plans** — see Tool form + Prose fallback above (step 9 in the main Process detail).

   On `yes` → invoke writing-plans via Skill tool. On `no` → emit `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` and stop.
```

**수정 후**:
```markdown
5. **Proceed-to-writing-plans gate** (v1.1.12+ restored · 산출물 깊이 선택 3지선다):

   **Gate #12 — 산출물 깊이** — see Tool form + Prose fallback above (step 9 in the main Process detail).

   On "구현계획서까지 진행 (3개)" → invoke writing-plans via Skill tool. On "여기서 종료 (2개 확정)" → frontmatter `depth: 2` 기록 + [개발방향-수정] entry + 승격 안내 후 stop. On "나중에 결정" → emit `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` and stop.
```

- [ ] **Step 10: Related Skills 문구**

**원본** (`skills/tech-design/SKILL.md:375`):
```markdown
- `writing-plans` — next step (<slug>-implementation-plan.md)
```

**수정 후**:
```markdown
- `writing-plans` — next step for 3개 트랙 (<slug>-implementation-plan.md); 2개 확정 시 미호출
```

- [ ] **Step 11: 검증 + commit** — `grep -F "여기서 종료 (2개 확정)" skills/tech-design/SKILL.md` ≥ 1 확인 후 commit.

---

### Task 3: commands/tech-design.md — 다음 단계 문구

**Files:**
- Modify: `commands/tech-design.md`

**Model**: haiku

- [ ] **Step 1: 문구 교체**

**원본** (`commands/tech-design.md:13`):
```markdown
다음 단계는 `/write-plan` 입니다.
```

**수정 후**:
```markdown
다음 단계는 tech-design 승인 직후 게이트에서 선택합니다 — 구현계획서까지 진행 (3개) / 여기서 종료 (2개 확정) / 나중에 결정. 3개 선택 시 `/write-plan` 으로 이어집니다.
```

- [ ] **Step 2: commit**

---

### Task 4: skills/auto-tech-design/SKILL.md — Step 7 깊이 판정 분기

**Files:**
- Modify: `skills/auto-tech-design/SKILL.md`

**Model**: haiku

- [ ] **Step 1: Checklist 재기술**

**원본** (`skills/auto-tech-design/SKILL.md:17`):
```markdown
- [ ] Step 7 — Transition notice + auto-writing-plans invoke
```

**수정 후**:
```markdown
- [ ] Step 7 — 깊이 판정 + Transition notice + (3개 판정 시) auto-writing-plans invoke
```

- [ ] **Step 2: Step 7 헤딩 재기술**

**원본** (`skills/auto-tech-design/SKILL.md:57`):
```markdown
### Step 7 — Transition notice + auto-writing-plans invoke
```

**수정 후**:
```markdown
### Step 7 — 깊이 판정 + Transition notice + (3개 판정 시) auto-writing-plans invoke
```

- [ ] **Step 3: 판정 룰 + 분기 동작** — 기존 invoke 문장을 분기 구조로 확장. `js-super:auto-writing-plans` 문자열은 CLAUDE.md 회귀 grep 계약이므로 반드시 보존.

**원본** (`skills/auto-tech-design/SKILL.md:69`):
```markdown
`parse_interrupt` 매치 시 exit + `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` 안내. 매치 X → `js-super:auto-writing-plans` invoke.
```

**수정 후**:
```markdown
**깊이 판정 (산출물 깊이 선택)**: transition notice 출력 전에 메인이 requirements + tech-design 내용으로 판정한다 — 코드 변경·구현 task 가 예상되는 피처면 **3개** (아래 invoke 진행), 순수 문서·설계·조사 성격 (산출물이 설계 문서 자체) 이면 **2개**. 애매하면 3개 (기존 동작 보존). 사용자에게 묻지 않는다 (AskUserQuestion 호출 X).

- **3개 판정**: 위 transition notice 출력. `parse_interrupt` 매치 시 exit + `ℹ️ 알겠습니다. /write-plan 은 나중에 직접 실행해주세요.` 안내. 매치 X → `js-super:auto-writing-plans` invoke.
- **2개 판정**: tech-design frontmatter 에 `depth: 2` + `depth_reason: <판단 근거 1줄>` 기록 + `change-history` [개발방향-수정] entry 후, `ℹ️ 이 피처는 2개 문서 트랙으로 자동 확정했습니다 (판단 근거: <1줄>). 구현이 필요해지면 /write-plan 으로 승격하세요.` 출력하고 체인 종료. auto-writing-plans 미호출. transition notice 미출력.
```

- [ ] **Step 4: 검증 + commit** — `grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md` ≥ 1 + `grep -F "깊이 판정" skills/auto-tech-design/SKILL.md` ≥ 1 확인 후 commit.

---

### Task 5: auto 커맨드 3종 — 다음 단계 문구 병기

**Files:**
- Modify: `commands/auto-brainstorm.md`
- Modify: `commands/auto-tech-design.md`
- Modify: `commands/auto-write-plan.md`

**Model**: haiku

- [ ] **Step 1: auto-brainstorm**

**원본** (`commands/auto-brainstorm.md:12`):
```markdown
다음 단계는 자동으로 이어집니다 — `/auto-tech-design` → `/auto-write-plan` → `/auto-execute-plan`.
```

**수정 후**:
```markdown
다음 단계는 자동으로 이어집니다 — `/auto-tech-design` → `/auto-write-plan` → `/auto-execute-plan`. 단 auto-tech-design 끝의 깊이 판정이 "2개 (tech-design 까지)" 로 나오면 구현계획서 단계 전에 자동 종료됩니다.
```

- [ ] **Step 2: auto-tech-design**

**원본** (`commands/auto-tech-design.md:12`):
```markdown
다음 단계는 자동으로 이어집니다 — `/auto-write-plan` → `/auto-execute-plan`.
```

**수정 후**:
```markdown
다음 단계는 자동으로 이어집니다 — `/auto-write-plan` → `/auto-execute-plan`. 단 본 단계 끝의 깊이 판정이 "2개 (tech-design 까지)" 로 나오면 구현계획서 단계 전에 자동 종료됩니다.
```

- [ ] **Step 3: auto-write-plan**

**원본** (`commands/auto-write-plan.md:12`):
```markdown
다음 단계는 자동으로 이어집니다 — `/auto-execute-plan`.
```

**수정 후**:
```markdown
다음 단계는 자동으로 이어집니다 — `/auto-execute-plan`. 2개 확정 피처 (tech-design frontmatter `depth: 2`) 에서 실행하면 3개 트랙으로 승격됩니다 (frontmatter 갱신 + 변경이력 기록).
```

- [ ] **Step 4: commit**

---

### Task 6: skills/change-history/SKILL.md — 2-doc 라우팅 룰

**Files:**
- Modify: `skills/change-history/SKILL.md`

**Model**: haiku

- [ ] **Step 1: When to Use 표 아래 라우팅 subsection 추가**

**원본** (`skills/change-history/SKILL.md:26`):
```markdown
| Release / version bump / git tag | <slug>-implementation-plan.md `## 변경이력` (with `[릴리즈]` tag) |
```

**수정 후**:
```markdown
| Release / version bump / git tag | <slug>-implementation-plan.md `## 변경이력` (with `[릴리즈]` tag) |

### 2-doc 트랙 라우팅 (산출물 깊이 선택)

피처의 tech-design frontmatter 가 `depth: 2` (2-doc 확정 트랙) 이고 `<slug>-implementation-plan.md` 가 없으면, 위 표에서 목적지가 구현계획서인 행 ([코드-수정] / [검증] / [릴리즈]) 은 **`<slug>-tech-design.md` `## 변경이력`** 으로 라우팅한다. footer append 는 본문 (설계 내용) 수정이 아니므로 change-propagation 의 reverse-cascade 금지 룰과 충돌하지 않는다. 판독 규칙 엄격 — `depth: 2` 명시일 때만 적용, 필드 부재·`depth: 3` 은 기존 라우팅 그대로.
```

- [ ] **Step 2: 검증 + commit** — `grep -F "depth: 2" skills/change-history/SKILL.md` ≥ 1 확인 후 commit.

---

### Task 7: skills/change-propagation/SKILL.md — depth-aware matrix

**Files:**
- Modify: `skills/change-propagation/SKILL.md`

**Model**: haiku

- [ ] **Step 1: Impact Matrix 아래 2-doc 분기 subsection**

**원본** (`skills/change-propagation/SKILL.md:41`):
```markdown
Code edits never cascade upward to 요구사항 or 개발방향. The reasoning is unchanged; only the implementation moved.
```

**수정 후**:
```markdown
Code edits never cascade upward to 요구사항 or 개발방향. The reasoning is unchanged; only the implementation moved.

### 2-doc 트랙 분기 (산출물 깊이 선택)

피처의 tech-design frontmatter 가 `depth: 2` (2-doc 확정 트랙) 이면 위 matrix 를 다음과 같이 적용한다:

- `<slug>-implementation-plan.md` 행 (변경 지점·cascade 대상 양쪽) 은 무효 — 문서가 존재하지 않는다.
- `<slug>-requirements.md` / `<slug>-tech-design.md` 행의 cascade 대상에서 `<slug>-implementation-plan.md` 를 제외한다.
- `code (direct edit)` 행의 기록 목적지는 `<slug>-tech-design.md` `## 변경이력` 으로 대체한다 (footer append 는 본문 수정이 아님 — Acceptance 4 참조).
- 구현이 필요해진 변경이면 `/write-plan` 승격을 안내한다 (frontmatter `depth: 3` 갱신 후 기존 matrix 복귀).
```

- [ ] **Step 2: Anti-Pattern 행 보강**

**원본** (`skills/change-propagation/SKILL.md:138`):
```markdown
| Editing code directly without <slug>-implementation-plan.md entry | Code edits always log to <slug>-implementation-plan.md (reverse direction). |
```

**수정 후**:
```markdown
| Editing code directly without <slug>-implementation-plan.md entry | Code edits always log to <slug>-implementation-plan.md (reverse direction; 2-doc 트랙은 <slug>-tech-design.md footer). |
```

- [ ] **Step 3: Red Flag 행 보강**

**원본** (`skills/change-propagation/SKILL.md:146`):
```markdown
| "User said 'just fix the bug'" | Even bug fixes get a [코드-수정] entry in <slug>-implementation-plan.md. |
```

**수정 후**:
```markdown
| "User said 'just fix the bug'" | Even bug fixes get a [코드-수정] entry in <slug>-implementation-plan.md (2-doc 트랙은 <slug>-tech-design.md footer). |
```

- [ ] **Step 4: Acceptance 4번 예외 조항**

**원본** (`skills/change-propagation/SKILL.md:155`):
```markdown
4. Code-only edits did not modify <slug>-requirements.md or <slug>-tech-design.md (reverse-cascade is forbidden)
```

**수정 후**:
```markdown
4. Code-only edits did not modify the BODY of <slug>-requirements.md or <slug>-tech-design.md (reverse-cascade is forbidden — 단 2-doc 트랙의 `## 변경이력` footer append 는 본문 수정이 아니므로 예외)
```

- [ ] **Step 5: 검증 + commit** — `grep -F "depth: 2" skills/change-propagation/SKILL.md` ≥ 1 확인 후 commit.

---

### Task 8: skills/verifying-spec/SKILL.md — 2-doc 대체 커버 명시

**Files:**
- Modify: `skills/verifying-spec/SKILL.md`

**Model**: haiku

- [ ] **Step 1: When to Invoke 아래 명시 문단**

**원본** (`skills/verifying-spec/SKILL.md:22`):
```markdown
<slug>-requirements.md is the source of truth and is therefore not a verification target.
```

**수정 후**:
```markdown
<slug>-requirements.md is the source of truth and is therefore not a verification target.

2-doc 확정 트랙 (tech-design frontmatter `depth: 2`) 은 첫 행 (End of `tech-design`) 만 실행된다 — 이미 requirements + tech-design 조합만 전제하므로 검사 로직 변경 없음. plan 부재로 빠지는 "FR → 결정 → task 추적" 축은 tech-design §2 (영향 컴포넌트) + §7 (테스트 전략) 매핑으로 대체 커버한다.
```

- [ ] **Step 2: commit**

---

### Task 9: skills/writing-plans/SKILL.md — 2→3 승격 clause

**Files:**
- Modify: `skills/writing-plans/SKILL.md`

**Model**: haiku

- [ ] **Step 1: HARD-GATE 직후 승격 subsection**

**원본** (`skills/writing-plans/SKILL.md:32-34`):
```markdown
<HARD-GATE>
Both <slug>-requirements.md and <slug>-tech-design.md must exist in the current feature folder. If either is missing, instruct the user to run /brainstorm or /tech-design first.
</HARD-GATE>
```

**수정 후**:
```markdown
<HARD-GATE>
Both <slug>-requirements.md and <slug>-tech-design.md must exist in the current feature folder. If either is missing, instruct the user to run /brainstorm or /tech-design first.
</HARD-GATE>

### 2-doc → 3-doc 승격 (산출물 깊이 선택)

`<slug>-tech-design.md` frontmatter 가 `depth: 2` (2-doc 확정 트랙) 인 피처에서 본 skill 이 명시 실행되면 승격으로 간주한다:

1. `ℹ️ 2개 확정 트랙 피처입니다. /write-plan 실행으로 3개 트랙으로 승격합니다.` 한 줄 안내 (질문 아님 — 사용자가 명시 실행했으므로 재확인 게이트 없음)
2. frontmatter 를 `depth: 3` 으로 갱신 + `depth_reason` 을 승격 사유로 교체
3. `change-history` 로 tech-design 에 [개발방향-수정] entry (이유: 2-doc → 3-doc 승격) 기록
4. 이후 본 skill 의 기존 흐름 그대로 진행
```

- [ ] **Step 2: 검증 + commit** — `grep -F "depth: 2" skills/writing-plans/SKILL.md` ≥ 1 확인 후 commit.

---

### Task 10: skills/auto-writing-plans/SKILL.md — 승격 clause (mirror)

**Files:**
- Modify: `skills/auto-writing-plans/SKILL.md`

**Model**: haiku

- [ ] **Step 1: Step 1 승격 문단 추가**

**원본** (`skills/auto-writing-plans/SKILL.md:24`):
```markdown
`<slug>-requirements.md` + `<slug>-tech-design.md` 모두 존재 확인. 누락 시 `ℹ️ 입력이 누락됐습니다 (<누락 파일>). /auto-brainstorm 또는 /auto-tech-design 부터 시작해주세요.` 안내 후 종료.
```

**수정 후**:
```markdown
`<slug>-requirements.md` + `<slug>-tech-design.md` 모두 존재 확인. 누락 시 `ℹ️ 입력이 누락됐습니다 (<누락 파일>). /auto-brainstorm 또는 /auto-tech-design 부터 시작해주세요.` 안내 후 종료.

**2-doc → 3-doc 승격 (산출물 깊이 선택)**: tech-design frontmatter 가 `depth: 2` 면 승격으로 간주 — 한 줄 안내 후 frontmatter `depth: 3` 갱신 + `depth_reason` 승격 사유 교체 + `change-history` [개발방향-수정] entry, 이후 기존 흐름 진행 (재확인 게이트 없음 — 명시 실행이므로).
```

- [ ] **Step 2: 검증 + commit** — `grep -F "depth: 2" skills/auto-writing-plans/SKILL.md` ≥ 1 확인 후 commit.

---

### Task 11: skills/brainstorming/SKILL.md — 표기 정합

**Files:**
- Modify: `skills/brainstorming/SKILL.md`

**Model**: haiku

- [ ] **Step 1: PRD blockquote "다음 두 산출물" 정정**

**원본** (`skills/brainstorming/SKILL.md:103`):
```markdown
> **다음 단계 안내**: 이 문서는 PRD (기획 단계 요구사항만) 입니다. 다음 단계로 `tech-design` skill (또는 `/tech-design` 슬래시) 을 호출해서 `<slug>-tech-design.md` (기술 설계서) 를 만드세요. 기술 결정이나 구현 세부사항은 여기 박지 마세요 — 그건 다음 두 산출물에 들어갑니다.
```

**수정 후**:
```markdown
> **다음 단계 안내**: 이 문서는 PRD (기획 단계 요구사항만) 입니다. 다음 단계로 `tech-design` skill (또는 `/tech-design` 슬래시) 을 호출해서 `<slug>-tech-design.md` (기술 설계서) 를 만드세요. 기술 결정이나 구현 세부사항은 여기 박지 마세요 — 그건 다음 산출물 (tech-design, 3개 트랙이면 plan 까지) 에 들어갑니다.
```

- [ ] **Step 2: Entry Router 라벨 "3-MD 풀 트랙" 정정**

**원본** (`skills/brainstorming/SKILL.md:315`):
```json
    {"label": "js-super:brainstorming", "description": "3-MD 풀 트랙 / PRD + tech-design + plan / 변경이력 + 위험 주석"}
```

**수정 후**:
```json
    {"label": "js-super:brainstorming", "description": "js-super 풀 트랙 (2~3 MD — 깊이는 tech-design 승인 시 선택) / 변경이력 + 위험 주석"}
```

- [ ] **Step 3: commit**

---

### Task 12: CLAUDE.md — 결합 메모 + 회귀 catch grep

**Files:**
- Modify: `CLAUDE.md` (파일 끝에 append — 실행 시점의 마지막 줄을 Read 로 확인해 anchor 로 사용)

**Model**: sonnet

- [ ] **Step 1: 파일 끝에 아래 섹션 append**

````markdown

## 산출물 깊이 선택 (2개/3개) 결합 (v2.9.0+)

v2.9.0+ 에서 피처 단위 산출물 깊이 선택 도입 — 2개 (requirements + tech-design) 또는 3개 (+ implementation-plan). 표식 = tech-design frontmatter `depth: 2` (single source of truth). spec: `docs/features/2026-08-09-산출물-깊이-선택/`.

### 핵심 룰

- **D1 표식** — `depth: 2` 명시일 때만 2-doc 트랙. 필드 부재 / `depth: 3` / 파싱 실패 = 3-doc (기존 동작). 기존 피처 폴더 소급 없음. 판독 helper: `scripts/preflight.py:feature_depth()` (additive — 기존 함수 시그니처 무변경)
- **D2 정식 결정 표면** — tech-design Gate #12 3지선다 (구현계획서까지 진행 / 여기서 종료 (2개 확정) / 나중에 결정). "나중에 결정" 은 표식 없이 종료 (기존 no 의미 보존)
- **D3 auto 결정 표면** — auto-tech-design Step 7 깊이 판정 (구현 단계 필요성 기준, 애매하면 3). AskUserQuestion 호출 X 유지. 2개 판정 시 판단 근거 1줄 보고 + 체인 종료
- **D4 체인 grep 계약 보존** — auto-tech-design 본문의 `js-super:auto-writing-plans` 문자열은 3개 판정 분기 문장 안에 보존 (기존 회귀 grep 그대로 통과)
- **D5 변경이력 라우팅** — 2-doc 트랙의 [코드-수정]/[검증]/[릴리즈] entry 는 tech-design footer 로. footer append 는 본문 수정이 아님 (change-propagation Acceptance 4 예외 조항)
- **D6 승격** — /write-plan (또는 /auto-write-plan) 명시 실행 = 2→3 승격. frontmatter `depth: 3` 갱신 + [개발방향-수정] entry. 재확인 게이트 없음

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| Gate #12 만 확장, auto Step 7 미분기 | 정식/auto 동작 불일치 — auto 는 무조건 4단계 완주 |
| 표식 기록만, change-history 라우팅 미갱신 | 2-doc 피처 코드·검증 이력의 목적지 소실 |
| 라우팅 갱신만, change-propagation Acceptance 예외 누락 | footer append 가 reverse-cascade 금지 룰과 충돌 판정 |
| auto Step 7 재작성 시 invoke 문자열 삭제 | 기존 회귀 grep (`js-super:auto-writing-plans`) 깨짐 |
| preflight 시그니처 변경 | 4 skill bash one-liner 동기 필요 (이번 릴리즈는 additive 라 해당 없음) |
| 판독 규칙 완화 (depth 부재를 2 로 해석 등) | 기존 3-doc 피처가 2-doc 분기로 오라우팅 |

### 회귀 catch grep

```bash
# 정식 게이트 3지선다
grep -F "여기서 종료 (2개 확정)" skills/tech-design/SKILL.md
# expected: >= 1

# auto 판정 분기 + 체인 문자열 보존
grep -F "깊이 판정" skills/auto-tech-design/SKILL.md
# expected: >= 1
grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md
# expected: >= 1 (기존 계약 유지)

# depth-aware 소비자 3곳
grep -lF "depth: 2" skills/change-history/SKILL.md skills/change-propagation/SKILL.md skills/writing-plans/SKILL.md skills/auto-writing-plans/SKILL.md
# expected: 4 lines

# preflight helper
python3 -c "from scripts.preflight import feature_depth; print('OK')"
# expected: OK
```

### 영향 범위

- skill 본문 9 + commands 4 + `scripts/preflight.py` + fixture H14 + CLAUDE.md + 6 manifest. og-* / fast-tasks / worktree 계열 / generating-html 구조 영향 0
- executing-plans / js-super-sub-driven skill 본문 변경 0 — plan 부재 안내 보강은 preflight `human_reason` 안에서
- writing-plans `**Model**:` ↔ js-super-sub-driven 결합 — 3-doc 트랙 전용이라 영향 0
````

- [ ] **Step 2: 검증 + commit** — `grep -cF "## 산출물 깊이 선택 (2개/3개) 결합" CLAUDE.md` = 1 확인 후 commit.

---

### Task 13: fixture H14-depth-select 생성

**Files:**
- Create: `skills/js-super-sub-driven/tests/H14-depth-select/README.md`

**Model**: haiku

- [ ] **Step 1: README 작성** — 파일 전체 내용 (new file):

````markdown
# H14 — 산출물 깊이 선택 (depth 2/3) 시나리오 fixture

v2.9.0+ 산출물 깊이 선택의 기대 동작 검증. spec: `docs/features/2026-08-09-산출물-깊이-선택/`.

## 시나리오 A — 정식 플로우, 3개 선택 (기존 동작)

- tech-design 승인 → Gate #12 에서 "구현계획서까지 진행 (3개)" 선택
- 기대: `writing-plans` invoke, frontmatter 기록 없음, 기존 흐름과 동일

## 시나리오 B — 정식 플로우, 2개 확정

- Gate #12 에서 "여기서 종료 (2개 확정)" 선택
- 기대: tech-design 맨 위 frontmatter `depth: 2` + `depth_reason: 사용자 선택` 기록, [개발방향-수정] entry 추가, `ℹ️ 이 피처는 2개 문서로 확정됐습니다 ...` 출력 후 stop. writing-plans 미호출

## 시나리오 C — auto-flow, 3개 판정 (기존 동작)

- auto-tech-design Step 7 판정: 코드 변경·구현 task 예상 → 3개
- 기대: transition notice 출력 후 `js-super:auto-writing-plans` invoke (체인 지속)

## 시나리오 D — auto-flow, 2개 판정

- auto-tech-design Step 7 판정: 순수 문서·설계·조사 성격 → 2개
- 기대: frontmatter `depth: 2` + `depth_reason: <근거 1줄>` 기록 + [개발방향-수정] entry + 판단 근거 1줄 포함 종료 보고. auto-writing-plans 미호출, transition notice 미출력

## 시나리오 E — 승격 (2 → 3)

- depth: 2 피처에서 `/write-plan` (또는 `/auto-write-plan`) 명시 실행
- 기대: 승격 안내 1줄 (재확인 게이트 없음) → frontmatter `depth: 3` 갱신 + `depth_reason` 승격 사유 교체 + [개발방향-수정] entry → 기존 흐름 진행

## 보조 검증

- depth: 2 피처에서 `/execute-plan` → preflight fail + human_reason 에 "2개 문서로 확정된 트랙 ... /write-plan 으로 승격" 안내 노출
- 2-doc 피처의 [코드-수정]/[검증]/[릴리즈] entry → tech-design footer 라우팅 (change-history 2-doc 룰)
- 판정 fallback: frontmatter 부재 / `depth: 3` / 수동 삭제 → 전부 3-doc 동작
````

- [ ] **Step 2: commit**

---

### Task 14: 전수 검증 (기존 + 신규 회귀 grep + pytest) [검증]

**Files:** 없음 (검증 전용)

**Model**: sonnet

- [ ] **Step 1: 신규 회귀 grep 실행** — Task 12 의 "회귀 catch grep" 블록 4종 전부 기대값 확인
- [ ] **Step 2: 기존 회귀 grep 전수 실행** — CLAUDE.md 의 기존 계약 재확인:
  - `grep -cF "js-super:auto-writing-plans" skills/auto-tech-design/SKILL.md` ≥ 1 (+ auto-brainstorming/auto-writing-plans 체인 라인 각 ≥ 1)
  - auto-* 4 skill description "자동 선택 금지" 각 1
  - `--no-ask` 8 skill grep 각 ≥ 1 / og-* 커맨드 3종 `disable-model-invocation: true` 유지
  - Checklist 결합 (v2.5.2+) 대상 skill `## Checklist` 존재
  - FR-10 확인: `git diff --stat` 에 `skills/generating-html/` 변경 0 (구조 무변경 보장)
- [ ] **Step 3: pytest 전체** — `python3 -m pytest scripts/tests/ -q` 전부 pass
- [ ] **Step 4: 결과를 [검증] entry 로 기록** (PASS/FAIL 명시)

---

### Task 15: 6 manifest 버전 bump + [릴리즈]

**Files:**
- Modify: `package.json`, `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `gemini-extension.json`

**Model**: sonnet

- [ ] **Step 1: 현재 버전 확인** — `package.json` 의 `version` 을 읽고 차기 minor 결정 (현재 2.8.1 → 2.9.0). 값이 다르면 그 기준 차기 minor.
- [ ] **Step 2: bump 실행** — `scripts/bump-version.sh` 사용 (6 manifest 동기). CLAUDE.md 신규 섹션 헤딩의 버전 표기 (v2.9.0+) 가 실제 bump 버전과 다르면 헤딩도 동기 수정.
- [ ] **Step 3: [릴리즈] entry + commit** — 연관 commit SHA 기록. (git tag 는 사용자가 merge-back 후 결정 — 워크트리 안 tag 생성 금지)

## 2. 위험 코드 지점

- `skills/change-history/SKILL.md` 신규 라우팅 subsection / `skills/change-propagation/SKILL.md` 2-doc 분기 (Task 6/7) — **side-effect**: 3-doc 피처에 오적용 시 이력 목적지 뒤엉킴 (mitigation: "depth: 2 명시일 때만" 판독 규칙을 두 본문 모두에 박음)
- `skills/auto-tech-design/SKILL.md:69` 재작성 (Task 4) — **breaking**: `js-super:auto-writing-plans` 문자열 소실 시 기존 회귀 grep 계약 깨짐 (mitigation: 3개 판정 분기 문장 안에 문자열 보존 + Task 4 Step 4 / Task 14 grep)
- `skills/auto-tech-design/SKILL.md` 깊이 판정 (Task 4) — **side-effect**: 오판으로 2개 종료 후 구현 필요 (mitigation: 애매하면 3 default + Task 9/10 승격 경로 + 판단 근거 1줄 보고)
- `skills/tech-design/SKILL.md:276-282` Gate #12 옵션 확장 (Task 2) — **breaking(UX)**: 기존 2지선다 습관과 충돌 (mitigation: 첫 옵션 = 기존 "진행" 유지, AskUserQuestion enum 이라 자유 파싱 없음)
- `scripts/preflight.py` (Task 1) — **side-effect**: 공유 helper 내부 분기 추가 (mitigation: 기존 함수 시그니처·exit code 룰 무변경 + pytest 전체 회귀 0 확인)
- frontmatter 수동 삭제 — **race**: 사용자가 tech-design frontmatter 를 지우면 표식 소실 (mitigation: 판독 규칙상 3-doc 으로 안전 fallback — 기존 동작 복귀라 데이터 손실 없음)

## 3. 롤백 전략

- Code: Task 1~15 의 commit 을 역순 `git revert`. 신규 파일 1개 (fixture README) 삭제, CLAUDE.md 섹션 revert, 6 manifest 를 이전 버전으로 되돌림.
- 산출물 표식: 이미 기록된 피처 폴더의 `depth: 2` frontmatter 는 문서 편집으로 제거 가능 (제거 = 3-doc 복귀, 파괴적 아님).
- Config: feature flag 없음 — 본문 룰 기반이라 revert 로 완전 복원.

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-09 21:28] [구현계획서-수정]
- **id**: CH-20260809-003
- **이유**: 신규 피처 auto-writing-plans 결과 (TDD bite-sized 15 task + byte-copy 원본 블록 15개 1회차 통과)
- **무엇이**: 산출물-깊이-선택-implementation-plan.md 전체 (Task 1~15 / §2 위험 코드 지점 6건 / §3 롤백 전략)
- **영향범위**: verifying-spec 4축 보고 — gap 0 (FR-10 확인 항목 self-correct 1건), conflict 0, plan_byte_check ALL BYTE-EQUAL
- **연관 항목**: CH-20260809-001, CH-20260809-002
