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
