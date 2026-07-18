---
description: "사용자가 /remove-skill 슬래시를 명시 호출했을 때만 발동. js-super 가 만든 skill 만 정리 (프로젝트/전체 양쪽 탐색, 출처 표식 없으면 무조건 차단). default = .removed-<timestamp> rename, --force = rm -rf hard-delete."
argument-hint: "<slug> [--project|--global] [--force] [--dry-run]"
---

# Remove Skill 빌더 (js-super skill 정리)

`/new-skill` 로 만든 skill 만 정리합니다. 대상은 프로젝트(`<project-root>/.claude/skills/<slug>/`) 와 전체(`~/.claude/skills/<slug>/`) 양쪽에서 찾습니다. **js-super 출처 표식 (`.js-super-skill.json`) 이 없으면 무조건 차단** — `--force` 로도 우회되지 않습니다. 표식이 있으면 default 는 safe-rename (회복 가능), `--force` 는 hard-delete (회복 불가).

## 1. 사전 검증

`$ARGUMENTS` 에서 **`--` 로 시작하지 않는 첫 토큰**(첫 kebab-case 토큰)이 slug 인자입니다 (필수, 위치 무관 — `--dry-run` 등 플래그가 앞에 와도 됨, § 2 파싱 규칙과 동일). slug 토큰이 아예 없으면 다음 안내 후 중단:

> 어떤 skill 을 정리할지 slug 를 알려주세요.
>
> 예: `/remove-skill auto-format-md` (safe-rename)
> 예: `/remove-skill --dry-run auto-format-md` (미리보기)
> 예: `/remove-skill auto-format-md --force` (회복 불가 hard-delete)

## 2. 입력 파싱

`$ARGUMENTS` 토큰 분해:

- **첫 kebab-case 토큰** → slug 인자
- **`--project` / `--global` 토큰** → 스코프 플래그로 인식 (위치 무관, 선택). 양쪽 동시 존재 시 어느 쪽을 정리할지 지정용
- **`--force` / `--dry-run` 토큰** → 플래그로 인식 (위치 무관)

예시:
```
/remove-skill auto-format-md --dry-run
↓
- slug: "auto-format-md"
- 플래그: ["--dry-run"]
```

## 3. 존재 검증 + 메타데이터 수집

LS 도구로 **양쪽 스코프**에서 `<slug>/` 디렉토리 존재 확인:

- 프로젝트: `<project-root>/.claude/skills/<slug>/` (현재 작업 디렉토리 기준 `.claude/skills`)
- 전체: `~/.claude/skills/<slug>/`

탐색 결과로 대상(`<TARGET>`) 을 확정:

- **양쪽 다 없음** → § 4-1 부재 분기로
- **한쪽만 존재** → 그 디렉토리가 `<TARGET>`
- **양쪽 다 존재** → 스코프 플래그(`--project`/`--global`)로 지정된 쪽이 `<TARGET>`. 플래그 없으면 § 4-0' 모호 분기 (어느 스코프인지 prose 로 1회 확인 후 진행)

`<TARGET>` 확정 후 디렉토리 크기 (LS 결과의 파일 size 합) + SKILL.md 마지막 수정 timestamp + 스코프(project/global) 수집. 보고 양식 (§ 5) 에서 사용. 미확보 시 "<unknown>" 표시.

## 4. 분기 실행

### 4-1. 부재 (양쪽 스코프 모두 `<slug>/` 없음)

LS 도구로 `<project-root>/.claude/skills/` + `~/.claude/skills/` 목록 가져와서 abort 메시지에 두 스코프의 현재 skill 목록 표시. § 5-4 보고 양식 사용. 변경 X.

### 4-0'. 모호 (양쪽 다 존재 + 스코프 플래그 없음)

**`AskUserQuestion` 도구로 어느 스코프를 정리할지 묻습니다** (응답 전 변경 X):

```json
{
  "questions": [
    {
      "question": "`<slug>` 가 프로젝트와 전체(글로벌) 양쪽에 있습니다. 어느 쪽을 정리할까요?",
      "header": "정리 스코프",
      "multiSelect": false,
      "options": [
        {"label": "프로젝트", "description": "현재 프로젝트의 `.claude/skills/<slug>/`"},
        {"label": "전체(글로벌)", "description": "`~/.claude/skills/<slug>/`"}
      ]
    }
  ]
}
```

사용자 선택("프로젝트" / "전체")으로 `<TARGET>` 확정. `AskUserQuestion` 이 없는 하네스면 위 질문을 prose 로 대체 (`--project` / `--global` 로 재호출 안내 포함).

### 4-0. 출처 표식 검사 (차단 게이트 — `<TARGET>` 확정 후, 4-2/4-3/4-4 실행 분기보다 먼저)

`<TARGET>/.js-super-skill.json` 존재 여부 LS 도구로 확인:

- **부재 → 무조건 차단**. `--force` 가 있어도 차단. § 5-5 보고 양식 사용. 변경 X.
- **존재 → 아래 4-2/4-3/4-4 분기 진입** (기존 동작).

js-super 가 만들지 않은 skill (다른 플러그인 / 사용자 직접 생성 / 옛 빌더로 만든 표식 없는 것) 을 건드리지 않기 위한 핵심 안전 게이트입니다.

### 4-2. `--dry-run` 명시 (변경 X)

§ 5-3 보고 양식으로 메인 응답 — `<TARGET>` 이 어디로 rename / 삭제되는지 안내. Bash / Edit / Write 도구 호출 X. **`--force` 와 함께 와도 `--dry-run` 이 우선** — 미리보기만 하고 절대 삭제하지 않는다 (안전 우선).

### 4-3. default safe-rename

Bash 도구로 1 줄 호출 (`<TARGET>` = 확정된 디렉토리 절대경로):

```bash
mv <TARGET> <TARGET>.removed-$(date +%Y%m%d%H%M%S)
```

성공 시 § 5-1 보고. timestamp 는 단위 unique 보장 (동시 호출 0 가정).

### 4-4. `--force` 명시 (옵트인 hard-delete)

Bash 도구로 1 줄 호출:

```bash
rm -rf <TARGET>
```

회복 불가. § 5-2 보고 (회복 불가 강조).

## 5. 보고 양식

### 5-1. Safe-rename 성공

```
✅ <TARGET>/ 가 안전 정리되었습니다. (스코프: <project|global>)

rename: <TARGET>/ → <TARGET>.removed-<timestamp>/

회복하려면: mv <TARGET>.removed-<timestamp> <TARGET>
완전 삭제하려면: rm -rf <TARGET>.removed-<timestamp>/

자동 발동이 즉시 차단됐는지 확인하려면 /reload-plugins 한 번 호출해주세요.
```

### 5-2. `--force` hard-delete 성공

```
✅ <TARGET>/ 가 영구 삭제되었습니다. (스코프: <project|global>)

⚠️ 회복 불가. 다시 만들려면 /new-skill <slug> "..." 로 재생성해주세요.

자동 발동이 즉시 차단됐는지 확인하려면 /reload-plugins 한 번 호출해주세요.
```

### 5-3. Dry-run

```
ℹ️ /remove-skill <slug> 미리보기 (--dry-run, 변경 X)

대상 (스코프: <project|global>): <TARGET>/ (<크기> KB, 마지막 수정 <timestamp>)
출처 표식: <TARGET>/.js-super-skill.json (존재 — 정리 가능)
변경 예정: <`--force` 도 함께 지정됐으면 `rm -rf <TARGET>/` (hard-delete, 회복 불가) / 아니면 `<TARGET>.removed-<timestamp>/` (safe-rename)>

--force 옵션 시 회복 불가 hard-delete.

옵션 빼고 재호출하면 실제 변경 적용.
```

### 5-4. Skill 부재 abort

```
⚠️ `<slug>` 가 프로젝트 / 전체 어느 스코프에도 존재하지 않습니다.

프로젝트 (`<project-root>/.claude/skills/`):
- <slug-1>
- ...
전체 (`~/.claude/skills/`):
- <slug-2>
- ...

slug 명을 다시 확인해주세요.
```

### 5-5. 출처 표식 부재 차단

```
⚠️ <TARGET>/ 는 js-super 가 만든 skill 이 아니라 정리할 수 없습니다.

이유: 출처 표식 (<TARGET>/.js-super-skill.json) 이 없습니다. /remove-skill 은 /new-skill 로 만든 skill 만 정리합니다 (--force 로도 우회되지 않습니다).

정리 대상 확인: /list-skills (js-super 가 만든 skill 목록)
직접 만들지 않은 skill 은 사용자가 수동으로 정리해주세요.
```

## 6. 금지

- **slug 인자 누락 시 abort** — `/new-skill` 과 달리 slug 는 필수 (정리 대상 명확성)
- **출처 표식 없는 skill 정리 금지** — `.js-super-skill.json` 부재 시 § 4-0 에서 무조건 차단. `--force` 로도 우회 X (핵심 안전 게이트)
- **`--force` 자동 적용 금지** — 옵트인 플래그 명시한 경우만 hard-delete
- **프로젝트/전체 외 위치 (`<plugin>/skills/` cache) 검증 금지** — 빌더 latency 보존. 다른 위치 정리는 사용자 catch 영역
- **rename 후 자동 발동 차단 보장 명시 X** — 보고 메시지에 `/reload-plugins` 호출 안내만 (사용자 catch 영역)
- **`.removed-<timestamp>` 디렉토리 추가 정리 자동 호출 금지** — 사용자가 직접 정리 (보고 메시지에 안내만)
