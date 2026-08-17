---
description: "js-super 가 만든 skill (출처 표식 .js-super-skill.json 보유) 을 홈 전체에서 조회 — 현재 프로젝트 / 글로벌 / 다른 프로젝트 세 그룹."
argument-hint: "(인자 없음)"
disable-model-invocation: true
---

# List Skills 빌더 (js-super skill 조회)

`/new-skill` 로 만든 skill 만 조회합니다. 판별 기준은 각 skill 디렉토리의 출처 표식 파일 `.js-super-skill.json` 존재 여부입니다. 표식 없는 skill (다른 플러그인 / 사용자 직접 생성 / 옛 빌더로 만든 것) 은 목록에 뜨지 않습니다.

## 1. 스캔 대상 (홈 전체)

- **현재 프로젝트**: cwd 에서 위로 올라가며 `.claude/skills/` 를 가진 첫 디렉토리 (홈 자체와 홈의 상위 폴더는 제외 — 홈의 것은 글로벌 스코프). 하위 폴더·워크트리에서 실행해도 올바른 프로젝트를 인식합니다
- **전체 (글로벌)**: `~/.claude/skills/*/`
- **다른 프로젝트**: 홈 디렉토리 아래를 훑어 발견한 나머지 프로젝트들의 `.claude/skills/*/`

숨김 폴더 (`.claude` 제외) 와 빌드·캐시 폴더 (node_modules, site-packages 등), 홈 최상위의 macOS 표준 폴더 (Library, Applications, Music, Movies, Pictures) 는 건너뜁니다. 숨김 폴더 아래의 **다른** 프로젝트는 목록에서 빠집니다 (현재 프로젝트는 직접 열거라 예외). 심링크는 따라가지 않습니다.

## 2. 수집 절차 (스캔 스크립트 1회 실행)

Bash 도구로 아래를 **한 줄 그대로** 실행합니다 (읽기 전용 — 어떤 파일도 쓰지 않음):

```bash
S=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/js-super/*/scripts/skill_scan.py" 2>/dev/null | sort -V | tail -1); [ -f "$S" ] || S=scripts/skill_scan.py; python3 "$S"
```

플러그인 설치 위치를 먼저 찾고, 못 찾으면 현재 디렉토리 기준 경로로 넘어갑니다 (js-super 저장소 자체에서 작업할 때). **환경변수 `${CLAUDE_PLUGIN_ROOT}` 를 쓰지 마세요** — 슬래시 커맨드 본문과 Bash 도구 환경에서는 그 변수가 채워지지 않아 항상 실패합니다.

출력은 JSON 이며 구조는 다음과 같습니다.

- `current_project` — `root` 는 **프로젝트 루트 절대경로** (없으면 `null`), `skills` 는 항목 배열
- `global` — `root` 는 **skills 디렉토리 절대경로** (`~/.claude/skills`), `skills` 는 항목 배열
- `other_projects` — 위와 같은 모양의 **오브젝트 배열**. 각 원소의 `root` 는 프로젝트 루트 절대경로
- 각 항목: `slug` / `path` (skill 디렉토리 절대경로) / `description` / `created` (표식 파일에 있을 때만)
- 스캔이 통째로 실패하면 최상위에 `error` 필드가 붙고 세 그룹은 빈 채로 옵니다

`description` 은 각 skill 의 `SKILL.md` frontmatter 에서 추출된 한 줄이고, 없거나 못 읽으면 "(설명 없음)" 입니다. `.removed-<timestamp>` 디렉토리 (`/remove-skill` safe-rename 결과) 와 표식 없는 디렉토리는 스크립트가 제외합니다.

**폴백**: 스크립트 실행이 실패하거나 (python3 부재 / 파일 없음) 출력에 `error` 필드가 있으면, 아래 절차로 두 스코프만 직접 조회합니다.

1. **현재 프로젝트 루트 찾기** — cwd 에서 위로 올라가며 `.claude/skills/` 를 가진 첫 디렉토리를 찾습니다 (홈 자체 제외). 못 찾으면 현재 프로젝트 그룹은 비웁니다
2. 그 `.claude/skills/` 와 `~/.claude/skills/` 각각에 대해 LS 도구로 하위 디렉토리 목록을 수집합니다
3. 각 디렉토리 안에 `.js-super-skill.json` 이 있는 것만 남깁니다 (`.removed-<timestamp>` 로 끝나는 것은 제외)
4. 남은 각 skill 의 `SKILL.md` frontmatter 에서 `description` 한 줄을 읽습니다 (실패 시 "(설명 없음)")
5. **다른 프로젝트 그룹은 "- (조회 안 함)" 으로 표시합니다** — 데이터가 없는 것이지 skill 이 없는 것이 아니므로 "(없음)" 으로 쓰면 안 됩니다
6. 안내 한 줄을 붙입니다: "ℹ️ 홈 전체 스캔을 사용할 수 없어 현재 프로젝트 + 글로벌 두 스코프만 조회했습니다."

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
- 현재 프로젝트의 `root` 가 null 이면 헤더를 "■ 현재 프로젝트 (이 위치에는 프로젝트 전용 skill 폴더가 없습니다)" 로 표시하고 항목 없이 넘어갑니다. 프로젝트 안에서 실행했더라도 `.claude/skills/` 폴더를 아직 안 만들었으면 이 상태가 정상입니다 — "프로젝트 밖에서 실행했다" 고 단정하지 마세요.
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
