---
commit_policy: per-task
---

# 문서가독성개선 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** 요구사항서와 기술설계서를 만드는 스킬 4개에 산출물 문서 스타일 규칙을 심고, 요구 항목 번호를 `FR-N` 에서 `요구 N` 으로 바꾸면서 그 번호를 읽는 쪽의 하위 호환을 유지한다.

**Architecture:** 문서를 만드는 쪽 (정식 2 + 자동 2) 에 통일된 이름의 스타일 규칙 섹션을 넣는다. 번호 형식 교체는 만드는 쪽의 템플릿·규칙 문구와 읽는 쪽의 인식 문구를 함께 바꾸되, 읽는 쪽은 세 세대 (`요구 N` / `## 요구 항목` 아래 `FR-N` / 옛 섹션 아래 `FR-N`) 를 모두 인식한다.

**Tech Stack:** 스킬 본문 markdown, 커맨드 markdown, 결합 메모 (CLAUDE.md), 대조 사례 fixture. 실행 코드 변경 없음.

**Spec inputs:**
- 문서가독성개선-requirements.md — 요구 1 (위에서 아래로) / 요구 2 (간결한 자연어) / 요구 3 (표·도면) / 요구 4 (항목 코드 금지 + `요구 N`) / 요구 5 (하위 호환) / 요구 6 (도면 형식 기준) / 요구 7 (정식·자동 동시)
- 문서가독성개선-tech-design.md — 결정 1 (번호 표기 형태) / 결정 2 (읽는 쪽 하위 호환) / 결정 3 (스킬 본문 직접 + 섹션 이름 통일) / 결정 4 (도면 형식 세 가지) / 결정 5 (코드 주석 금지 목록)

**대상에서 빠진 것과 그 이유:** 요구사항서의 계약을 읽는 곳으로 `writing-plans` 와 `auto-writing-plans` 가 함께 거론되지만 이번 계획의 대상이 아니다. 두 파일이 가진 `FR` 표기는 옛 피처 스펙을 가리키는 내부 주석 하나뿐이고, 요구 항목 번호를 실제로 찾아 읽는 문구가 없다. 두 파일이 만드는 구현계획서의 문체 역시 요구사항서에서 범위 밖으로 확정됐다. 목록 밖에 남은 참조가 정말 없는지는 Task 14 Step 5 에서 저장소 전체를 훑어 확인한다.

**실행 순서 주의 (모든 task 공통):** 한 파일 안에서 여러 지점을 고칠 때, **줄 수가 바뀌는 수정** (섹션 신설, 행 추가) 은 그 아래에 있는 다른 수정 지점의 줄 번호를 밀어버린다. 그래서 각 task 의 step 은 **파일 아래쪽 지점부터 위로** 배열해 두었다. 적힌 순서대로 진행하면 원본 블록의 줄 번호가 실행 시점까지 유효하다. 줄 수가 그대로인 한 줄 대 한 줄 교체끼리는 순서를 바꿔도 무방하지만, 굳이 바꿀 이유가 없다.

---

## 1. 단계별 작업

### Task 1: brainstorming 스타일 규칙 + 번호 형식 교체

**Files:**
- Modify: `skills/brainstorming/SKILL.md`

**Model**: sonnet

**검증**: `grep -c "## 산출물 문서 스타일" skills/brainstorming/SKILL.md` 가 1 이고, `grep -c '\*\*FR-1\*\*' skills/brainstorming/SKILL.md` 가 0 이며, `grep -c "요구 항목/요구 N" skills/brainstorming/SKILL.md` 가 4 (흐름도 노드 4곳) 면 성공. 옛 피처 스펙을 가리키는 내부 주석 (`(v1.1.15+, FR-3)` 등) 은 남아 있어야 한다.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "FR-N\|FR-1\|FR-2" skills/brainstorming/SKILL.md`
Expected: 14 이상 (수정 전)

- [ ] **Step 2: 변경이력 안내 문구 교체 (같은 문장 2곳)**

L220 과 L429 에 **완전히 같은 문장**이 있다. 두 곳을 한꺼번에 (replace_all) 바꾼다. 한 곳만 지정하면 문자열이 유일하지 않아 교체 자체가 실패한다.

**원본** (`skills/brainstorming/SKILL.md:429`):
```markdown
- 무엇이: <slug>-requirements.md 전체 (FR-1..N + 대화에서 나온 섹션들)
```

**수정 후**:
```markdown
- 무엇이: <slug>-requirements.md 전체 (요구 1..N + 대화에서 나온 섹션들)
```

- [ ] **Step 3: Anti-Patterns 표 2행 교체**

**원본** (`skills/brainstorming/SKILL.md:408`):
```markdown
| Writing only "user can do X" without an FR id | `FR-N: <action>` in the `## 요구 항목` section, plus a way to tell it's done |
```

**수정 후**:
```markdown
| Writing only "user can do X" without a requirement number | `**요구 N**: <action>` in the `## 요구 항목` section, plus a way to tell it's done |
```

**원본** (`skills/brainstorming/SKILL.md:410`):
```markdown
| Renaming the `## 요구 항목` section or dropping FR numbers | Downstream skills look for that exact heading and those anchors. Keep both. |
```

**수정 후**:
```markdown
| Renaming the `## 요구 항목` section or dropping the 요구 numbers | Downstream skills look for that exact heading and those anchors. Keep both. |
```

- [ ] **Step 4: Self-Review 항목 추가 (여섯 → 일곱)**

**원본** (`skills/brainstorming/SKILL.md:356`):
```markdown
6. **기술 세부 누출**: 구현 방법이나 파일 구조가 본문에 섞였는가? 다음 단계 산출물로 넘긴다.
```

**수정 후**:
```markdown
6. **기술 세부 누출**: 구현 방법이나 파일 구조가 본문에 섞였는가? 다음 단계 산출물로 넘긴다.
7. **문서 스타일**: "산출물 문서 스타일" 네 가지로 훑는다. 뒤를 먼저 읽어야 이해되는 문장, 비유, 산문으로 늘어놓은 나열, 새로 만든 항목 코드가 남았는가?
```

**원본** (`skills/brainstorming/SKILL.md:349`):
```markdown
초안을 다 쓴 뒤 처음 보는 눈으로 여섯 가지를 훑는다.
```

**수정 후**:
```markdown
초안을 다 쓴 뒤 처음 보는 눈으로 일곱 가지를 훑는다.
```

- [ ] **Step 5: 흐름도 노드 라벨 교체 (문서 작성 4곳 + 자체 점검 3곳)**

`"블록 3 — 문서 작성\n(자유 산문 + 요구 항목/FR-N)"` 는 흐름도의 노드 이름이라 선언 1곳과 연결선 3곳이 **정확히 같은 문자열**이어야 한다. 네 곳을 한꺼번에 (replace_all) 바꾼다. 하나라도 빠지면 그래프에 없는 노드를 가리키는 선이 생긴다.

**원본** (`skills/brainstorming/SKILL.md:161-165`):
```
    "제외 항목 취합해서 되돌려주기" -> "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/FR-N)";
    "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/FR-N)" -> "Self-review (6 items)";
    "Self-review (6 items)" -> "블록 4 — 승인\n초안 전체 한 번에";

    "블록 4 — 승인\n초안 전체 한 번에" -> "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/FR-N)" [label="수정 요청 — 고쳐서 다시"];
```

**수정 후**:
```
    "제외 항목 취합해서 되돌려주기" -> "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/요구 N)";
    "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/요구 N)" -> "Self-review (7 items)";
    "Self-review (7 items)" -> "블록 4 — 승인\n초안 전체 한 번에";

    "블록 4 — 승인\n초안 전체 한 번에" -> "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/요구 N)" [label="수정 요청 — 고쳐서 다시"];
```

**원본** (`skills/brainstorming/SKILL.md:140`):
```
    "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/FR-N)" [shape=box];
```

**수정 후**:
```
    "블록 3 — 문서 작성\n(자유 산문 + 요구 항목/요구 N)" [shape=box];
```

`"Self-review (6 items)"` 도 같은 성격의 노드 이름이다. 선언 1곳과 연결선 2곳, 모두 세 곳을 한꺼번에 (replace_all) `(7 items)` 로 바꾼다 (Step 4 에서 항목이 일곱으로 늘어난 것과 맞춘다). 위 Step 5 첫 블록이 그중 두 곳을 이미 담고 있고, 남은 선언부는 아래 블록이다.

**원본** (`skills/brainstorming/SKILL.md:143`):
```
    "Self-review (6 items)" [shape=box];
```

**수정 후**:
```
    "Self-review (7 items)" [shape=box];
```

- [ ] **Step 6: 요구 항목 규칙 교체 + 스타일 규칙 섹션 신설**

**원본** (`skills/brainstorming/SKILL.md:118-125`):
```markdown
`## 요구 항목` 규칙:

- 섹션 이름은 `## 요구 항목` 으로 고정한다. 다른 이름을 쓰면 다운스트림이 못 찾는다.
- 항목마다 `FR-N` 을 붙인다. 번호는 1부터 순서대로, 문서 안에서 유일해야 한다.
- 항목이 많으면 소제목으로 묶어도 된다 (`### 제거` / `### 신설` 등). 번호는 묶음을 가로질러 이어진다.
- 요구 항목이 하나뿐이어도 섹션과 번호를 쓴다. 다운스트림은 셀 수 있는 단위를 필요로 한다.

모드를 표기하는 줄은 쓰지 않는다. 경로가 하나뿐이라 표기할 모드가 없다.
```

**수정 후**:
```markdown
`## 요구 항목` 규칙:

- 섹션 이름은 `## 요구 항목` 으로 고정한다. 다른 이름을 쓰면 다운스트림이 못 찾는다.
- 항목마다 `**요구 N**:` 을 붙인다. 굵게까지 포함한 형태가 약속이다. 번호는 1부터 순서대로, 문서 안에서 유일해야 한다.
- 항목이 많으면 소제목으로 묶어도 된다 (`### 제거` / `### 신설` 등). 번호는 묶음을 가로질러 이어진다.
- 요구 항목이 하나뿐이어도 섹션과 번호를 쓴다. 다운스트림은 셀 수 있는 단위를 필요로 한다.

모드를 표기하는 줄은 쓰지 않는다. 경로가 하나뿐이라 표기할 모드가 없다.

## 산출물 문서 스타일

이 규칙은 이 skill 이 만드는 산출물 문서에 적용된다. 이 skill 본문 자체는 대상이 아니다.

**위에서 아래로 읽힌다.** 용어는 처음 쓰는 자리에서 뜻을 밝힌다. 뒤 섹션을 먼저 읽어야 이해되는 문장을 쓰지 않는다. 앞 섹션이 뒤 섹션의 결론에 기대고 있으면 순서를 바꾼다.

**간결한 자연어로 쓴다.** 한 문장에 하나를 말한다. 비유를 쓰지 않는다 — 무엇에 빗대지 말고 그것이 무엇인지 그대로 쓴다. 배경 반복, 다짐, 같은 말 되풀이는 넣지 않는다.

**나열과 비교와 구조는 표나 도면으로 보인다.** 항목이 셋 이상이면 표로 만든다. 구성 요소들의 관계나 배치를 설명해야 하면 도면을 그린다. 산문은 배경과 판단 근거에 쓴다.

**항목 코드를 만들지 않는다.** 본문에 알파벳-숫자 코드를 붙이지 않는다. 무언가를 가리켜야 하면 짧은 한국어 제목을 쓴다. 유일한 예외는 요구 항목 번호 (`요구 N`) 다 — 다음 단계 문서들이 이 번호로 항목을 찾는다.

도면 안에 붙이는 번호 (①②③) 는 표에서 설명하기 위한 도면 표기법이지 항목 코드가 아니다. 금지 대상이 아니다.
```

- [ ] **Step 7: 요구 항목 템플릿 교체**

**원본** (`skills/brainstorming/SKILL.md:108-109`):
```markdown
**FR-1**: <시스템이 무엇을 해야 하는지 한 문장>
**FR-2**: ...
```

**수정 후**:
```markdown
**요구 1**: <시스템이 무엇을 해야 하는지 한 문장>
**요구 2**: ...
```

- [ ] **Step 8: Checklist 5번 + 계약 서술 + description 교체**

**원본** (`skills/brainstorming/SKILL.md:74`):
```markdown
5. **요구사항 문서 작성** — 자유 산문. `## 요구 항목` 섹션과 `FR-N` 만 필수. 제외 항목 취합 룰 포함. 블록 3 참조.
```

**수정 후**:
```markdown
5. **요구사항 문서 작성** — 자유 산문. `## 요구 항목` 섹션과 `요구 N` 만 필수. "산출물 문서 스타일" 을 지킨다. 제외 항목 취합 룰 포함. 블록 3 참조.
```

**원본** (`skills/brainstorming/SKILL.md:34`):
```markdown
The output is free-form prose. Only three things are fixed: the H1 title, a `## 요구 항목` section whose items carry `FR-N` anchors, and the `## 변경이력` footer. Everything else takes whatever shape the dialogue produced. Downstream skills (`tech-design`, `verifying-spec`, `writing-plans`, `change-propagation`) read the `FR-N` anchors, so that section is the one contract this doc must honour.
```

**수정 후**:
```markdown
The output is free-form prose. Only three things are fixed: the H1 title, a `## 요구 항목` section whose items carry `요구 N` anchors, and the `## 변경이력` footer. Everything else takes whatever shape the dialogue produced. Downstream skills (`tech-design`, `verifying-spec`, `writing-plans`, `change-propagation`) read the `요구 N` anchors, so that section is the one contract this doc must honour. Prose style is governed by the "산출물 문서 스타일" section below.
```

**원본** (`skills/brainstorming/SKILL.md:3`):
```markdown
description: You MUST use this before creating any feature, component, or behavior change. Runs a Socratic dialogue — one question at a time, alternatives with tradeoffs, then a free-form requirements doc whose only fixed parts are the title, a `## 요구 항목` section with FR-N anchors, and the change-log footer. Writes <slug>-requirements.md to docs/features/YYYY-MM-DD-<slug>/. Does NOT cover technical design — that belongs to tech-design.
```

**수정 후**:
```markdown
description: You MUST use this before creating any feature, component, or behavior change. Runs a Socratic dialogue — one question at a time, alternatives with tradeoffs, then a free-form requirements doc whose only fixed parts are the title, a `## 요구 항목` section with 요구 N anchors, and the change-log footer. Writes <slug>-requirements.md to docs/features/YYYY-MM-DD-<slug>/. Does NOT cover technical design — that belongs to tech-design.
```

- [ ] **Step 9: 검증 grep → PASS 확인**

Run: `grep -c "## 산출물 문서 스타일" skills/brainstorming/SKILL.md; grep -c '\*\*FR-1\*\*' skills/brainstorming/SKILL.md; grep -c "요구 항목/요구 N" skills/brainstorming/SKILL.md; grep -c "Self-review (7 items)" skills/brainstorming/SKILL.md; grep -c "Self-review (6 items)" skills/brainstorming/SKILL.md`
Expected: `1`, `0`, `4`, `3`, `0` — 마지막 두 개가 흐름도 노드 이름의 무결성을 본다. `(6 items)` 가 하나라도 남으면 그래프에 없는 노드를 가리키는 선이 생긴 것이다.

- [ ] **Step 10: Commit**

```bash
git add skills/brainstorming/SKILL.md
git commit -m "docs(brainstorming): 산출물 문서 스타일 규칙 + 요구 항목 번호 형식 교체"
```

### Task 2: auto-brainstorming 스타일 압축본 + 번호 형식 교체

**Files:**
- Modify: `skills/auto-brainstorming/SKILL.md`

**Model**: sonnet

**검증**: `grep -c "## 산출물 문서 스타일" skills/auto-brainstorming/SKILL.md` 가 1 이고 `grep -c "FR-N" skills/auto-brainstorming/SKILL.md` 가 0 이면 성공.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "FR-N" skills/auto-brainstorming/SKILL.md`
Expected: 2

- [ ] **Step 2: Step 4 본문 교체**

**원본** (`skills/auto-brainstorming/SKILL.md:67-68`):
```markdown
- H1 + 다음 단계 안내 배너 + 배경 + 핵심 결정 + `## 요구 항목` (FR-N) + 우려/해결 + 다음 단계 + 변경이력 footer
- `## 요구 항목` 과 `FR-N` 은 필수. 나머지 섹션은 대화에서 나온 대로. 모드 표기 줄은 쓰지 않는다.
```

**수정 후**:
```markdown
- H1 + 다음 단계 안내 배너 + 배경 + 핵심 결정 + `## 요구 항목` (`**요구 N**:`) + 우려/해결 + 다음 단계 + 변경이력 footer
- `## 요구 항목` 과 `**요구 N**:` 은 필수. 나머지 섹션은 대화에서 나온 대로. 모드 표기 줄은 쓰지 않는다.
- 아래 "산출물 문서 스타일" 을 지킨다. 작성 직후 그 네 가지로 한 번 훑는다 (사용자 응답 wait X).
```

- [ ] **Step 3: 스타일 압축본 섹션 신설**

`## Anti-Patterns` 섹션 **바로 앞**에 아래 섹션을 삽입한다.

**원본** (`skills/auto-brainstorming/SKILL.md:83`):
```markdown
## Anti-Patterns
```

**수정 후**:
```markdown
## 산출물 문서 스타일

산출물 문서에만 적용된다 (이 skill 본문은 대상 아님).

- **위에서 아래로** — 용어는 처음 쓰는 자리에서 설명. 뒤를 먼저 읽어야 이해되는 문장 금지
- **간결한 자연어** — 한 문장에 하나. 비유 금지. 배경 반복·다짐 금지
- **표와 도면 우선** — 항목 셋 이상이면 표. 관계·배치는 도면. 산문은 배경과 판단 근거에만
- **항목 코드 금지** — 알파벳-숫자 코드를 새로 만들지 않는다. 유일한 예외는 요구 항목 번호 (`요구 N`). 도면 안 번호 (①②③) 는 표기법이라 대상 아님

전체 룰은 `skills/brainstorming/SKILL.md` 의 같은 이름 섹션 답습.

## Anti-Patterns
```

- [ ] **Step 4: Anti-Patterns 행 추가**

**원본** (`skills/auto-brainstorming/SKILL.md:88`):
```markdown
| Visual Companion offer | NEVER. D-T11. |
```

**수정 후**:
```markdown
| Visual Companion offer | NEVER. D-T11. |
| 산출물에 비유·항목 코드·산문 나열 | "산출물 문서 스타일" 네 가지 위반. 표·도면·짧은 문장으로. |
```

- [ ] **Step 5: 검증 grep → PASS 확인**

Run: `grep -c "## 산출물 문서 스타일" skills/auto-brainstorming/SKILL.md; grep -c "FR-N" skills/auto-brainstorming/SKILL.md`
Expected: `1`, `0`

- [ ] **Step 6: Commit**

```bash
git add skills/auto-brainstorming/SKILL.md
git commit -m "docs(auto-brainstorming): 산출물 문서 스타일 압축본 + 요구 항목 번호 형식 교체"
```

### Task 3: tech-design 스타일 규칙 + 도면 형식 기준 + 하위 호환

**Files:**
- Modify: `skills/tech-design/SKILL.md`

**Model**: sonnet

**검증**: `grep -c "## 산출물 문서 스타일" skills/tech-design/SKILL.md` 가 1, `grep -c "### 도면 형식" skills/tech-design/SKILL.md` 가 1, 그리고 하위 호환 문구가 살아 있어 `grep -c "FR-N" skills/tech-design/SKILL.md` 가 1 이상 (0 이면 오히려 회귀) 이면 성공.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "FR-N\|FR mapping" skills/tech-design/SKILL.md`
Expected: 8

- [ ] **Step 2: Self-Review 첫 항목 교체 + 스타일 항목 추가 (아래쪽 먼저)**

**원본** (`skills/tech-design/SKILL.md:310`):
```markdown
- Every `FR-N` in <slug>-requirements.md is mapped to either §2 (impacted components) or §4 (external IF)
```

**수정 후**:
```markdown
- Every `요구 N` in <slug>-requirements.md is mapped to either §2 (impacted components) or §4 (external IF) — 옛 문서의 `FR-N` 도 같은 항목으로 센다
- 서술 문단이 "산출물 문서 스타일" 네 가지를 지키는가 — 뒤를 먼저 읽어야 이해되는 문장 / 비유 / 산문으로 늘어놓은 나열 / 새로 만든 항목 코드
- §1 의 그림이 "도면 형식" 세 형식 중 하나이고, 절차 나열 흐름도로 구조 설명을 대신하지 않았는가
```

- [ ] **Step 3: 질의응답 항목의 번호 표기 교체**

**원본** (`skills/tech-design/SKILL.md:226`):
```markdown
- Component/file mapping (FR-N → which file/module)
```

**수정 후**:
```markdown
- Component/file mapping (요구 N → which file/module)
```

- [ ] **Step 4: 요구사항 읽기 규칙 교체 (하위 호환 세 세대)**

**원본** (`skills/tech-design/SKILL.md:217-221`):
```markdown
- **Locate the requirements** — find the `## 요구 항목` section and read its `FR-N` items. Older docs (written before the section name was fixed) carry the same `FR-N` anchors under `## 3. 기능 요구사항 (FR)`; read those the same way.
- If a doc has no `FR-N` anchors at all, treat every sentence describing a behavior the system must have as one requirement, and say so in a one-line notice. Never reject a doc as "missing FRs".

**2. Survey the codebase**
- For each `FR-N`, Grep/Read to identify likely impacted code areas
```

**수정 후**:
```markdown
- **Locate the requirements** — find the `## 요구 항목` section and read its numbered items. Three generations exist and ALL are read the same way: `**요구 N**:` (current), `**FR-N**:` under `## 요구 항목` (previous), and `**FR-N**:` under `## 3. 기능 요구사항 (FR)` (oldest). Never rewrite an old doc's numbering — read it as-is.
- If a doc has no numbered anchors at all, treat every sentence describing a behavior the system must have as one requirement, and say so in a one-line notice. Never reject a doc as "missing requirements".

**2. Survey the codebase**
- For each requirement item, Grep/Read to identify likely impacted code areas
```

- [ ] **Step 5: 스타일 규칙 + 도면 형식 섹션 신설**

`## 서술 수준 — 이름보다 역할` 섹션 **바로 앞**에 삽입한다. 두 섹션은 이웃이며 서로 다른 것을 다룬다 — 새 섹션은 문서 전체의 읽는 흐름과 표현 형식을, 기존 섹션은 서술 문단에 코드 이름을 쓸지를 정한다.

**원본** (`skills/tech-design/SKILL.md:103`):
```markdown
## 서술 수준 — 이름보다 역할
```

**수정 후**:
```markdown
## 산출물 문서 스타일

이 규칙은 이 skill 이 만드는 산출물 문서에 적용된다. 이 skill 본문 자체는 대상이 아니다.

**위에서 아래로 읽힌다.** 용어는 처음 쓰는 자리에서 뜻을 밝힌다. 뒤 섹션을 먼저 읽어야 이해되는 문장을 쓰지 않는다. 앞 섹션이 뒤 섹션의 결론에 기대고 있으면 순서를 바꾼다.

**간결한 자연어로 쓴다.** 한 문장에 하나를 말한다. 비유를 쓰지 않는다 — 무엇에 빗대지 말고 그것이 무엇인지 그대로 쓴다. 배경 반복, 다짐, 같은 말 되풀이는 넣지 않는다.

**나열과 비교와 구조는 표나 도면으로 보인다.** 항목이 셋 이상이면 표로 만든다. 구성 요소들의 관계나 배치를 설명해야 하면 도면을 그린다. 산문은 배경과 판단 근거에 쓴다.

**항목 코드를 만들지 않는다.** 본문에 알파벳-숫자 코드를 붙이지 않는다. 결정이나 위험을 가리켜야 하면 짧은 한국어 제목을 쓴다 (`### 결정 1 — 요구 항목 번호를 바꾼다`). 유일한 예외는 요구 항목 번호 (`요구 N`) 다 — 상위 문서가 정한 번호라 그대로 인용한다.

도면 안에 붙이는 번호 (①②③) 는 표에서 설명하기 위한 도면 표기법이지 항목 코드가 아니다. 금지 대상이 아니다.

### 도면 형식

§1 의 그림은 구역과 배치가 보이는 도면을 기본으로 한다. 절차 단계를 노드와 화살표로 나열한 흐름도로 구조 설명을 대신하지 않는다.

| 상황 | 형식 |
|---|---|
| 구역·레이어·배치를 보일 때 (기본) | 아스키 박스 도면 |
| 구성 요소가 여섯 개를 넘거나 요소마다 설명이 필요할 때 | 아스키 도면에 번호를 달고 표에서 설명 |
| 관계와 조건 분기가 본질이고 렌더링 환경 (GitHub, 에디터 미리보기) 을 전제할 수 있을 때 | mermaid |

mermaid 를 쓸 때도 절차 나열이 아니라 관계를 보이는 그림이어야 한다.

이 규칙은 산출물에만 적용된다. 이 skill 본문 안의 dot 흐름도는 에이전트 실행용이라 대상이 아니다.

## 서술 수준 — 이름보다 역할
```

- [ ] **Step 6: schema 안내 줄 갱신**

**원본** (`skills/tech-design/SKILL.md:91`):
```markdown
## 1. 아키텍처 개요 (diagram + prose)
```

**수정 후**:
```markdown
## 1. 아키텍처 개요 (도면 + 짧은 산문 — "도면 형식" 참조)
```

- [ ] **Step 7: Checklist 자체 점검 항목 갱신**

**원본** (`skills/tech-design/SKILL.md:66`):
```markdown
4. **자체 점검** — FR mapping coverage, alternatives present, risk categorization (no user prompt yet)
```

**수정 후**:
```markdown
4. **자체 점검** — 요구 항목 mapping coverage, alternatives present, risk categorization, 산출물 문서 스타일 + 도면 형식 (no user prompt yet)
```

- [ ] **Step 8: 검증 grep → PASS 확인**

Run: `grep -c "## 산출물 문서 스타일" skills/tech-design/SKILL.md; grep -c "### 도면 형식" skills/tech-design/SKILL.md; grep -c "FR-N" skills/tech-design/SKILL.md`
Expected: `1`, `1`, `1` 이상 (마지막은 하위 호환 문구 — 0 이면 회귀)

- [ ] **Step 9: Commit**

```bash
git add skills/tech-design/SKILL.md
git commit -m "docs(tech-design): 산출물 문서 스타일 + 도면 형식 기준 + 요구 항목 번호 세 세대 하위 호환"
```

### Task 4: auto-tech-design 스타일 압축본 + 도면 형식 압축본

**Files:**
- Modify: `skills/auto-tech-design/SKILL.md`

**Model**: sonnet

**검증**: `grep -c "## 산출물 문서 스타일" skills/auto-tech-design/SKILL.md` 와 `grep -c "### 도면 형식" skills/auto-tech-design/SKILL.md` 가 각각 1 이면 성공.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "서술 수준 — 이름보다 역할" skills/auto-tech-design/SKILL.md`
Expected: 2

- [ ] **Step 2: 스타일 + 도면 형식 압축본 신설**

`## 서술 수준 — 이름보다 역할` 섹션 **바로 앞**에 삽입한다.

**원본** (`skills/auto-tech-design/SKILL.md:84`):
```markdown
## 서술 수준 — 이름보다 역할
```

**수정 후**:
```markdown
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
```

- [ ] **Step 3: Step 4 점검 문장 확장**

**원본** (`skills/auto-tech-design/SKILL.md:42`):
```markdown
작성 직후 메인이 서술 문단을 한 번 훑는다 — 남아 있는 코드 식별자마다 "그 이름이 바뀌면 문서 밖의 무언가가 깨지는가" 를 판정하고, 아니면 역할 서술로 교체한다. 표 / 코드 블록 / 도식은 대상 아님. 룰은 아래 "서술 수준 — 이름보다 역할" 섹션. 사용자 응답 wait X (auto 모드).
```

**수정 후**:
```markdown
작성 직후 메인이 서술 문단을 한 번 훑는다 — 남아 있는 코드 식별자마다 "그 이름이 바뀌면 문서 밖의 무언가가 깨지는가" 를 판정하고, 아니면 역할 서술로 교체한다. 표 / 코드 블록 / 도식은 대상 아님. 룰은 아래 "서술 수준 — 이름보다 역할" 섹션. 같은 자리에서 "산출물 문서 스타일" 네 가지와 "도면 형식" 도 훑는다 — 뒤를 먼저 읽어야 이해되는 문장 / 비유 / 산문 나열 / 새 항목 코드 / 절차 나열 흐름도. 사용자 응답 wait X (auto 모드).
```

- [ ] **Step 4: Anti-Patterns 행 추가**

**원본** (`skills/auto-tech-design/SKILL.md:82`):
```markdown
| 서술 문단에 내부 변수나 아직 없는 함수 이름 박기 | 역할을 말로 풀어쓴다. 아래 "서술 수준" 섹션 참조. |
```

**수정 후**:
```markdown
| 서술 문단에 내부 변수나 아직 없는 함수 이름 박기 | 역할을 말로 풀어쓴다. 아래 "서술 수준" 섹션 참조. |
| §1 을 절차 나열 흐름도로만 채우기 | 도면으로 구역과 배치를 보인다. "도면 형식" 섹션 참조. |
| 산출물에 비유·새 항목 코드·산문 나열 | "산출물 문서 스타일" 네 가지 위반. |
```

- [ ] **Step 5: 검증 grep → PASS 확인**

Run: `grep -c "## 산출물 문서 스타일" skills/auto-tech-design/SKILL.md; grep -c "### 도면 형식" skills/auto-tech-design/SKILL.md`
Expected: `1`, `1`

- [ ] **Step 6: Commit**

```bash
git add skills/auto-tech-design/SKILL.md
git commit -m "docs(auto-tech-design): 산출물 문서 스타일 + 도면 형식 압축본"
```

### Task 5: verifying-spec 번호 표기 갱신 + 하위 호환

**Files:**
- Modify: `skills/verifying-spec/SKILL.md`

**Model**: haiku

**검증**: 체크리스트와 보고서 예시가 `요구 N` 을 앞세우고 옛 `FR-N` 도 함께 인식한다고 적혀 있으면 성공.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "FR-N" skills/verifying-spec/SKILL.md; grep -c "요구 N" skills/verifying-spec/SKILL.md`
Expected: `1`, `0` (수정 전 — 교체 뒤에도 `FR-N` 은 하위 호환 문구로 1을 유지한다)

- [ ] **Step 2: 보고서 예시 교체 (아래쪽 먼저)**

**원본** (`skills/verifying-spec/SKILL.md:158`):
```
✅ Mapped: <count> items (e.g., FR-1, FR-2, FR-3 → §2/§4)
```

**수정 후**:
```
✅ Mapped: <count> items (e.g., 요구 1, 요구 2, 요구 3 → §2/§4)
```

- [ ] **Step 3: 구현계획서 대상 체크리스트 교체**

**원본** (`skills/verifying-spec/SKILL.md:137`):
```markdown
- Every FR is implementable through the listed tasks (trace FR → decision → task chain)
```

**수정 후**:
```markdown
- Every requirement item is implementable through the listed tasks (trace 요구 N → decision → task chain)
```

- [ ] **Step 4: 기술설계서 대상 체크리스트 교체**

**원본** (`skills/verifying-spec/SKILL.md:130`):
```markdown
- Every FR-N from <slug>-requirements.md is mapped to <slug>-tech-design.md §2 (impacted components) or §4 (external interfaces)
```

**수정 후**:
```markdown
- Every 요구 N from <slug>-requirements.md is mapped to <slug>-tech-design.md §2 (impacted components) or §4 (external interfaces) — older docs number the same items `FR-N`; count them the same way
```

- [ ] **Step 5: 검증 grep → PASS 확인**

Run: `grep -c "요구 N\|요구 1" skills/verifying-spec/SKILL.md; grep -c "FR-N" skills/verifying-spec/SKILL.md`
Expected: `3` 이상, `1` (하위 호환 문구 유지)

- [ ] **Step 6: Commit**

```bash
git add skills/verifying-spec/SKILL.md
git commit -m "docs(verifying-spec): 요구 항목 번호 표기 갱신 + 옛 형식 하위 호환"
```

### Task 6: 무맥락 대조 검증 프롬프트 번호 표기 갱신

**Files:**
- Modify: `skills/verifying-spec/clean-cross-prompt.md`

**Model**: haiku

**검증**: 상위 항목 예시가 `요구 N` 을 앞세우고 옛 `FR-N` 도 병기하면 성공.

- [ ] **Step 1: 상위 항목 예시 교체**

**원본** (`skills/verifying-spec/clean-cross-prompt.md:38`):
```
    **Gap** — an upstream item (FR-N, NFR, key decision, risk, constraint,
```

**수정 후**:
```
    **Gap** — an upstream item (요구 N — older docs write it FR-N —, NFR,
    key decision, risk, constraint,
```

- [ ] **Step 2: 검증 grep → PASS 확인**

Run: `grep -c "요구 N" skills/verifying-spec/clean-cross-prompt.md`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add skills/verifying-spec/clean-cross-prompt.md
git commit -m "docs(clean-cross-prompt): 상위 항목 번호 표기 갱신 + 옛 형식 병기"
```

### Task 7: change-propagation 번호 표기 갱신 + 옛 표기 인식

**Files:**
- Modify: `skills/change-propagation/SKILL.md`

**Model**: haiku

**검증**: 트리거 예시·영향 목록·entry 예시 세 곳이 `요구 N` 이고, 옛 `FR-N` 표기 요청도 인식한다는 문구가 있으면 성공.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "FR-3" skills/change-propagation/SKILL.md; grep -c "FR-N" skills/change-propagation/SKILL.md`
Expected: `3`, `0` (수정 전 — 교체 뒤에는 `FR-3` 이 0, 새로 넣는 하위 호환 문구 때문에 `FR-N` 이 1)

- [ ] **Step 2: entry 예시 교체 (아래쪽 먼저)**

**원본** (`skills/change-propagation/SKILL.md:136`):
```markdown
- **무엇이**: <slug>-requirements.md §3 FR-3
```

**수정 후**:
```markdown
- **무엇이**: <slug>-requirements.md 요구 항목 요구 3
```

- [ ] **Step 3: 영향 목록 예시 교체**

**원본** (`skills/change-propagation/SKILL.md:96`):
```markdown
1. <slug>-requirements.md 요구 항목 FR-3 (직접 변경)
```

**수정 후**:
```markdown
1. <slug>-requirements.md 요구 항목 요구 3 (직접 변경)
```

- [ ] **Step 4: 트리거 예시 교체 + 옛 표기 인식 문구**

**원본** (`skills/change-propagation/SKILL.md:18`):
```markdown
1. **Natural language change request** — the user says something like "FR-3 한도 바꿔", "개발방향 §5 결정 다시", "Task 4 단계 추가". The main agent recognizes the intent and invokes this skill.
```

**수정 후**:
```markdown
1. **Natural language change request** — the user says something like "요구 3 한도 바꿔", "개발방향 §5 결정 다시", "Task 4 단계 추가". The main agent recognizes the intent and invokes this skill. Older docs number the same items `FR-N`, so a request naming "FR-3" points at the same thing — recognize both.
```

- [ ] **Step 5: 검증 grep → PASS 확인**

Run: `grep -c "요구 3" skills/change-propagation/SKILL.md; grep -c "FR-N" skills/change-propagation/SKILL.md; grep -c "FR-3" skills/change-propagation/SKILL.md`
Expected: `3`, `1`, `0`

- [ ] **Step 6: Commit**

```bash
git add skills/change-propagation/SKILL.md
git commit -m "docs(change-propagation): 요구 항목 번호 표기 갱신 + 옛 표기 인식"
```

### Task 8: risk-annotation 주석 금지 목록에 새 번호 형식 추가

**Files:**
- Modify: `skills/risk-annotation/SKILL.md`

**Model**: haiku

**검증**: 코드 주석 금지 목록에 `요구 N` 문서 참조가 포함되면 성공.

- [ ] **Step 1: 금지 목록 행 교체**

**원본** (`skills/risk-annotation/SKILL.md:115`):
```markdown
| Leaking plan-side identifiers into code comments — `# KD-2: chose async`, `# AC-3 covers this`, `# FR-1 / NFR-2`, `# CH-20260505-007`, `# task 4 of <slug>-implementation-plan.md`, etc. | Code comments must be self-contained — no `(KD\|AC\|FR\|NFR)-\d+`, no `CH-\d{8}-\d{3}`, no `[<slug>-...]` doc references, no "task N of ..." plan references. The ONLY allowed jargon in code comments is the standardized `# ⚠️ RISK(...)` form. Plan/spec identifiers are useful inside `<slug>-implementation-plan.md` for navigation; they have NO place in source files. If a reviewer needs context, the variable/function names + RISK comment + git history must carry it. |
```

**수정 후**:
```markdown
| Leaking plan-side identifiers into code comments — `# KD-2: chose async`, `# AC-3 covers this`, `# 요구 1 / FR-1 / NFR-2`, `# CH-20260505-007`, `# task 4 of <slug>-implementation-plan.md`, etc. | Code comments must be self-contained — no `(KD\|AC\|FR\|NFR)-\d+`, no `요구 \d+` doc references, no `CH-\d{8}-\d{3}`, no `[<slug>-...]` doc references, no "task N of ..." plan references. The ONLY allowed jargon in code comments is the standardized `# ⚠️ RISK(...)` form. Plan/spec identifiers are useful inside `<slug>-implementation-plan.md` for navigation; they have NO place in source files. If a reviewer needs context, the variable/function names + RISK comment + git history must carry it. |
```

- [ ] **Step 2: 검증 grep → PASS 확인**

Run: `grep -cF '요구 \d+' skills/risk-annotation/SKILL.md`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add skills/risk-annotation/SKILL.md
git commit -m "docs(risk-annotation): 코드 주석 금지 목록에 요구 항목 번호 참조 추가"
```

### Task 9: og-brainstorm 형식 비교 한 줄 갱신

**Files:**
- Modify: `commands/og-brainstorm.md`

**Model**: haiku

**검증**: 형식 비교 표의 산출물 형식 행이 `요구 N` 을 가리키면 성공. 원본 흐름 자체 설명은 바뀌지 않아야 한다.

- [ ] **Step 1: 비교 표 행 교체**

**원본** (`commands/og-brainstorm.md:179`):
```markdown
| 산출물 형식 | 자유 산문 + `## 요구 항목` 과 `FR-N` 필수 | upstream 자유 형식 단일 |
```

**수정 후**:
```markdown
| 산출물 형식 | 자유 산문 + `## 요구 항목` 과 `요구 N` 필수 | upstream 자유 형식 단일 |
```

- [ ] **Step 2: 검증 grep → PASS 확인**

Run: `grep -c "FR-N" commands/og-brainstorm.md`
Expected: 0

- [ ] **Step 3: Commit**

```bash
git add commands/og-brainstorm.md
git commit -m "docs(og-brainstorm): 형식 비교 표의 요구 항목 번호 표기 갱신"
```

### Task 10: README 예시 표기 갱신 (4곳, mechanical 묶음)

**Files:**
- Modify: `README.md`

**Model**: haiku

**검증**: `grep -c "FR-3" README.md` 가 0 이면 성공. 네 곳 모두 `요구 3` 으로 바뀌고 mermaid 그래프의 노드 라벨이 깨지지 않아야 한다.

- [ ] **Step 1: 현재 상태 확인**

Run: `grep -c "FR-3" README.md`
Expected: 4

- [ ] **Step 2: 연쇄 영향 그래프 노드 교체 (아래쪽 먼저)**

**원본** (`README.md:690`):
```
    A[요구사항 FR-3 수정] --> B[연쇄 영향 분석]
```

**수정 후**:
```
    A[요구사항 요구 3 수정] --> B[연쇄 영향 분석]
```

- [ ] **Step 3: 연쇄 영향 설명 문장 교체**

**원본** (`README.md:686`):
```markdown
요구사항의 FR-3 가 수정되면, 자동으로 아래로 영향을 확인합니다.
```

**수정 후**:
```markdown
요구사항의 요구 3 이 수정되면, 자동으로 아래로 영향을 확인합니다.
```

- [ ] **Step 4: 변경이력 예시 교체**

**원본** (`README.md:615`):
```markdown
- **무엇이**: FR-3 (1 일 출금 한도 100 만원) 신설
```

**수정 후**:
```markdown
- **무엇이**: 요구 3 (1 일 출금 한도 100 만원) 신설
```

- [ ] **Step 5: 영향 분석 그래프 노드 교체**

**원본** (`README.md:230`):
```
    A["요구사항.md<br/>FR-3 신규 추가"]:::in --> B[자동 영향 분석]:::sub
```

**수정 후**:
```
    A["요구사항.md<br/>요구 3 신규 추가"]:::in --> B[자동 영향 분석]:::sub
```

- [ ] **Step 6: 검증 grep → PASS 확인**

Run: `grep -c "FR-3" README.md`
Expected: 0

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs(README): 변경 전파 예시의 요구 항목 번호 표기 갱신 (4곳)"
```

### Task 11: 대조 사례 fixture 신규 작성

**Files:**
- Create: `skills/js-super-sub-driven/tests/H20-doc-readability/README.md`

**Model**: sonnet

**검증**: 통과 사례와 위반 사례가 짝으로 들어 있고, 네 가지 스타일 규칙과 도면 형식과 번호 하위 호환을 각각 최소 한 시나리오씩 다루면 성공. H16 fixture 의 통과/위반 대조 구성을 따른다.

- [ ] **Step 1: 참고 fixture 확인**

Run: `cat skills/js-super-sub-driven/tests/H16-tech-design-abstraction/README.md`
Expected: 통과/위반 대조 구성 확인 (구조 참고용)

- [ ] **Step 2: fixture 작성**

`skills/js-super-sub-driven/tests/H20-doc-readability/README.md` 를 새로 만든다. 담을 시나리오는 다섯이다.

| 시나리오 | 내용 |
|---|---|
| 위에서 아래로 | 용어를 뒤에서 설명한 위반 사례 ↔ 처음 쓰는 자리에서 설명한 통과 사례 |
| 비유·잔말 | 비유로 설명한 위반 사례 ↔ 그대로 서술한 통과 사례 |
| 표·도면 우선 | 다섯 항목을 산문으로 늘어놓은 위반 사례 ↔ 표로 만든 통과 사례 |
| 항목 코드 금지 | 결정에 알파벳-숫자 코드를 붙인 위반 사례 ↔ 짧은 한국어 제목을 쓴 통과 사례. 요구 항목 번호와 도면 번호는 금지 대상이 아님을 함께 보인다 |
| 도면 형식 | 절차 나열 흐름도로 §1 을 채운 위반 사례 ↔ 구역 배치를 보이는 도면 통과 사례 |

여기에 번호 하위 호환 확인을 한 항목 더한다 — 옛 `FR-N` 문서를 읽을 때 새 형식으로 고쳐 쓰지 않고 그대로 읽는지.

- [ ] **Step 3: 파일 생성 확인**

Run: `test -f skills/js-super-sub-driven/tests/H20-doc-readability/README.md && echo OK`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add skills/js-super-sub-driven/tests/H20-doc-readability/README.md
git commit -m "test(H20): 산출물 문서 스타일 통과/위반 대조 사례 추가"
```

### Task 12: fixture 인덱스 등록

**Depends on:** Task 11 (fixture 파일이 먼저 있어야 인덱스가 실재하는 것을 가리킨다)

**Files:**
- Modify: `skills/js-super-sub-driven/tests/README.md`

**Model**: haiku

**검증**: 인덱스 표에 H20 행이 있고, H17 행의 계약 표기가 새 번호 형식을 반영하면 성공.

- [ ] **Step 1: H20 행 추가 (아래쪽 먼저)**

**원본** (`skills/js-super-sub-driven/tests/README.md:76`):
```markdown
| H19-clean-verify | 무맥락 검증자 2종 병렬 — 단독(대상 MD 만) / 대조(대상 + upstream) / 중재 / `--no-clean-verify` skip |
```

**수정 후**:
```markdown
| H19-clean-verify | 무맥락 검증자 2종 병렬 — 단독(대상 MD 만) / 대조(대상 + upstream) / 중재 / `--no-clean-verify` skip |
| H20-doc-readability | 산출물 문서 스타일 — 위에서 아래로 / 비유 금지 / 표·도면 우선 / 항목 코드 금지 / 도면 형식 / 요구 항목 번호 하위 호환 |
```

- [ ] **Step 2: H17 행 표기 갱신**

**원본** (`skills/js-super-sub-driven/tests/README.md:74`):
```markdown
| H17-socratic-single-track | 모드 질문 부재 (A) / 요구 항목 + FR-N 계약 (B) / 제외 항목 취합 (C) / '모르겠다' 3단 사다리 (D) / 옛 6섹션 문서 하위호환 (E) |
```

**수정 후**:
```markdown
| H17-socratic-single-track | 모드 질문 부재 (A) / 요구 항목 + 번호 계약 (B) / 제외 항목 취합 (C) / '모르겠다' 3단 사다리 (D) / 옛 6섹션 문서 하위호환 (E) |
```

- [ ] **Step 3: 인덱스 제목 범위 갱신**

**원본** (`skills/js-super-sub-driven/tests/README.md:67`):
```markdown
## v2.9.0 이후 fixtures (H14~H19)
```

**수정 후**:
```markdown
## v2.9.0 이후 fixtures (H14~H20)
```

- [ ] **Step 4: 검증 grep → PASS 확인**

Run: `grep -c "H20-doc-readability" skills/js-super-sub-driven/tests/README.md`
Expected: 1

- [ ] **Step 5: Commit**

```bash
git add skills/js-super-sub-driven/tests/README.md
git commit -m "test: fixture 인덱스에 H20 등록 + H17 번호 계약 표기 갱신"
```

### Task 13: CLAUDE.md 결합 메모 추가

**Depends on:** Task 1~12 (검사 명령이 실제 결과와 맞아야 하므로 본문 변경이 모두 끝난 뒤 작성)

**Files:**
- Modify: `CLAUDE.md`

**Model**: sonnet

**검증**: 새 결합 섹션에 적힌 회귀 검사 명령을 그대로 실행했을 때 적힌 기대값이 나오면 성공. 검사 명령은 읽기 전용이고 자리표시자가 없어야 한다 (스킬 검증 러너가 그대로 실행한다).

- [ ] **Step 1: 결합 메모 섹션 추가**

`CLAUDE.md` 끝에 아래 구조로 섹션을 추가한다. 기존 결합 메모들의 형식 (핵심 룰 / 회귀 패턴 표 / 회귀 catch grep / 영향 범위) 을 따른다.

담을 내용:

| 항목 | 내용 |
|---|---|
| 섹션 제목 | `## 산출물 문서 스타일 + 요구 항목 번호 교체 결합` |
| 핵심 룰 | 네 스킬의 섹션 이름 통일 / 정식은 전체본·자동은 압축본 / 번호는 `**요구 N**:` / 읽는 쪽 세 세대 하위 호환 / 도면 형식 세 가지 / 옛 문서 소급 수정 금지 |
| 회귀 패턴 표 | 한쪽 경로만 수정 / 하위 호환 문구 삭제 / 읽는 쪽 한 곳 누락 / 도면 형식 기준 삭제 / 스킬 본문 자체에 스타일 규칙 적용 |
| 회귀 catch | 아래 Step 2 의 명령들 |
| 영향 범위 | 스킬 8 + 커맨드 1 + README + fixture 2 + CLAUDE.md. 구현계획서 스킬 / og-* / 워크트리 계열 / scripts / hooks 영향 0. 버전 bump 는 main 전용 룰에 따라 main 에서 |

- [ ] **Step 2: 회귀 검사 명령 삽입**

결합 메모의 회귀 catch 블록에 아래 명령들을 넣는다 (읽기 전용, 자리표시자 없음).

```bash
grep -lF "## 산출물 문서 스타일" skills/brainstorming/SKILL.md skills/auto-brainstorming/SKILL.md skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md | wc -l
# expected: 4
```

```bash
grep -cF "### 도면 형식" skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md
# expected: 각 1
```

```bash
grep -cF "**요구 1**" skills/brainstorming/SKILL.md
# expected: 1
```

```bash
grep -c "FR-N" skills/tech-design/SKILL.md
# expected: 1 이상 (하위 호환 문구 — 0 이면 회귀)
```

```bash
grep -c "FR-3" README.md
# expected: 0
```

```bash
grep -c "FR-N" commands/og-brainstorm.md
# expected: 0
```

- [ ] **Step 3: 삽입한 명령 실제 실행 → 기대값 대조**

Run: 위 Step 2 의 여섯 명령을 순서대로 실행
Expected: 각 블록에 적힌 기대값과 일치.

어긋나면 Task 1~12 중 해당 본문 수정이 빠졌거나 잘못된 것이다. 그 task 로 돌아가 본문을 고친다. 실제 값에 맞춰 기대값을 낮추지 않는다 — 그러면 검사가 회귀를 못 잡는다.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): 산출물 문서 스타일 + 요구 항목 번호 교체 결합 메모"
```

### Task 14: 전체 회귀 확인

**Depends on:** Task 1~13

**Files:** 없음 (검증 전용)

**Model**: sonnet

**검증**: 네 스킬 모두 스타일 섹션 보유, 번호 형식 교체 완료, 하위 호환 문구 생존, 스킬 검증 러너가 파싱하는 결합 규칙 수가 줄지 않음. 전부 통과가 성공 기준.

- [ ] **Step 1: 스타일 섹션 전수 확인**

Run: `grep -lF "## 산출물 문서 스타일" skills/brainstorming/SKILL.md skills/auto-brainstorming/SKILL.md skills/tech-design/SKILL.md skills/auto-tech-design/SKILL.md | wc -l`
Expected: 4

- [ ] **Step 2: 번호 교체 확인 (만드는 쪽)**

Run: `grep -c "FR-N" skills/brainstorming/SKILL.md skills/auto-brainstorming/SKILL.md`
Expected: 각 0

- [ ] **Step 3: 하위 호환 생존 확인 (읽는 쪽)**

Run: `grep -c "FR-N" skills/tech-design/SKILL.md skills/verifying-spec/SKILL.md skills/change-propagation/SKILL.md skills/verifying-spec/clean-cross-prompt.md`
Expected: 각 1 이상

- [ ] **Step 4: 스킬 검증 러너 파싱 확인**

Run: `python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(len(collect_rules(Path('.'))))"`
Expected: 100 이상 (직전보다 줄지 않음 — 새 결합 메모 규칙만큼 늘어야 정상)

- [ ] **Step 5: 목록 밖 참조 재확인 (전수)**

계획 대상 목록에 없는 파일이 요구 항목 번호를 참조하고 있는지 저장소 전체를 훑는다. 착수 시점 전수 조사 결과를 실행 시점에 다시 확인하는 단계다.

Run: `grep -rln "FR-N\|FR-[0-9]" skills/ commands/ scripts/ hooks/ agents/ README.md HANDOFF.md 2>/dev/null | grep -v "/tests/" | sort`
Expected: `skills/tech-design/SKILL.md`, `skills/verifying-spec/SKILL.md`, `skills/verifying-spec/clean-cross-prompt.md`, `skills/change-propagation/SKILL.md`, `skills/risk-annotation/SKILL.md`, `skills/brainstorming/SKILL.md`, `skills/executing-plans/SKILL.md`, `skills/writing-plans/SKILL.md` 만 나온다. 앞 다섯은 하위 호환 문구를 일부러 남긴 파일이고, `brainstorming` 은 옛 피처 스펙을 가리키는 내부 주석, 뒤 둘도 내부 주석뿐이다. 그 밖의 파일이 나오면 목록에서 빠진 참조이므로 확인 후 처리한다.

- [ ] **Step 6: 흐름도 무결성 확인**

Run: `grep -c "요구 항목/요구 N" skills/brainstorming/SKILL.md`
Expected: 4 (선언 1 + 연결선 3 — 하나라도 빠지면 그래프가 깨진 것)

- [ ] **Step 7: 변경 파일 목록 확인**

Run: `git diff main --name-only`
Expected: 스킬 8 + 커맨드 1 + README + fixture 2 + CLAUDE.md + 피처 문서 3. 6 manifest 파일이 목록에 있으면 되돌린다 (워크트리 버전 bump 금지).

## 2. 위험 코드 지점

- `skills/brainstorming/SKILL.md` 흐름도 노드 라벨 — breaking: 노드 이름 4곳 중 일부만 바꾸면 존재하지 않는 노드를 가리키는 연결선이 생겨 그래프가 깨진다 (mitigation: Task 1 Step 6 에서 네 곳 일괄 교체 + Task 14 Step 5 개수 확인)
- `skills/tech-design/SKILL.md` 요구사항 읽기 규칙 — breaking: 하위 호환 문구를 지우면 옛 피처 문서의 요구 항목을 못 읽는다 (mitigation: Task 3 Step 4 에서 세 세대 명시 + Task 14 Step 3 에서 `FR-N` 잔존을 통과 조건으로 검사)
- 정식 경로 2 ↔ 자동 경로 2 — side-effect: 한쪽만 고치면 두 경로가 만드는 문서의 문체가 갈리고, 이 어긋남은 문서를 나란히 놓고 읽기 전에는 드러나지 않는다 (mitigation: 섹션 이름 통일 + Task 14 Step 1 에서 네 파일 동시 확인)
- `skills/risk-annotation/SKILL.md` 주석 금지 목록 — side-effect: 새 번호 형식을 빠뜨리면 코드 주석에 문서 참조가 다시 새어 들어간다 (mitigation: Task 8 에서 금지 패턴에 추가)
- 계획 대상 목록 밖 파일 — breaking: 요구 항목 번호를 읽는 파일이 목록에서 빠지면 그 파일만 옛 형식을 기대한 채 남아 요구 항목을 못 찾는다 (mitigation: Task 14 Step 5 에서 저장소 전체를 훑어 착수 시점 전수 조사를 실행 시점에 재확인)
- `CLAUDE.md` 회귀 검사 명령 — side-effect: 명령 형식이 어긋나면 스킬 검증 러너가 규칙을 조용히 놓친다 (mitigation: Task 13 Step 3 에서 삽입한 명령을 실제로 실행해 대조 + Task 14 Step 4 에서 파싱된 규칙 수 확인)
- 6 manifest 버전 필드 — breaking: 워크트리에서 버전을 올리면 main 머지 때 충돌한다 (mitigation: Task 14 Step 6 에서 변경 파일 목록 확인)

## 3. 롤백 전략

- Code: revert commits (Task 1~13 각 1 commit — `git log --oneline` 으로 SHA 확인 후 `git revert <SHA>` 역순)
- DB: 해당 없음 (영구 데이터 없음)
- Config: 해당 없음 (플래그 없음 — 스킬 본문 revert 로 즉시 옛 동작 복원). 이미 새 형식으로 작성된 문서는 읽는 쪽 하위 호환이 두 형식을 모두 인식하므로 revert 후에도 읽힌다

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 09:37] [구현계획서-수정]
- **id**: CH-20260829-003
- **이유**: 신규 구현계획서 작성 (auto-flow) + 무맥락 검증 지적 8건 반영 — 목록 밖 참조 전수 재확인 단계 신설 / 같은 문장 2곳 교체 실패 방지 / 흐름도 노드 선언 누락분 블록화 + 개수 검사 추가 / 사전 상태 확인 2건 신설 / 검사 명령 대상 분리 / 기대값 불일치 시 처리 문구 정정 / 편집 순서 규칙 정밀화 / 구현계획서 스킬 미대상 근거 명시
- **무엇이**: 문서가독성개선-implementation-plan.md 전체 (Task 1~14 + §2 위험 코드 지점 + §3 롤백 전략)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260829-001, CH-20260829-002
