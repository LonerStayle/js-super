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
