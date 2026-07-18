---
description: "사용자가 /new-skill 슬래시를 명시 호출했을 때만 발동. 자유 텍스트 한 줄을 받아 프로젝트 또는 전체(글로벌) <slug>/SKILL.md 1 파일로 자동 생성 + js-super 출처 표식 부여."
argument-hint: "[<slug>] [--project|--global] [--force] [--dry-run] <자유 텍스트 설명>"
---

# New Skill 빌더 (프로젝트 / 전체 skill 자동 생성)

사용자가 `$ARGUMENTS` 로 던진 자유 텍스트를 읽고, **자동 발동 트리거** + **수행 동작** 으로 분해한 뒤 `<SKILL_BASE>/<slug>/SKILL.md` 1 파일을 생성합니다. `<SKILL_BASE>` 는 스코프에 따라 결정됩니다 — 프로젝트면 `<project-root>/.claude/skills`, 전체면 `~/.claude/skills`. 생성 시 js-super 출처 표식 파일 `.js-super-skill.json` 도 함께 작성합니다. skill hot-reload 덕분에 저장 즉시 사용 가능합니다.

## 1. 사전 검증

`$ARGUMENTS` 가 비어있으면 다음 안내 후 중단:

> 어떤 skill 을 만들지 한 줄로 설명해주세요.
>
> 예: `/new-skill "사용자가 .md 파일을 저장하면 prettier 로 자동 포맷하는 skill"`
> 예: `/new-skill my-helper "사용자가 X 하면 Y 와 Z 를 차례로 수행"`
> 예: `/new-skill --dry-run "..."` (실제 Write 전 미리보기)
> 예: `/new-skill auto-format --force "..."` (덮어쓰기 허용)

## 2. 입력 파싱

`$ARGUMENTS` 토큰 분해:

- **첫 토큰이 kebab-case (소문자 + 하이픈) 패턴 매치** → slug 인자로 인식
- **`--project` / `--global` 토큰** → 스코프 플래그로 인식 (위치 무관). 둘 다 주면 안내 후 중단
- **`--force` / `--dry-run` 토큰** → 플래그로 인식 (위치 무관)
- **나머지 (보통 따옴표 묶음)** → 자유 텍스트

예시:
```
/new-skill auto-format-md --project --dry-run "사용자가 .md 파일 저장하면 prettier 로 포맷"
↓
- slug 인자: "auto-format-md"
- 스코프: project
- 플래그: ["--dry-run"]
- 자유 텍스트: "사용자가 .md 파일 저장하면 prettier 로 포맷"
```

`/new-skill --dry-run "..."` 처럼 slug 인자가 없으면 § 3 단계에서 자동 생성. 스코프 플래그가 없으면 § 2.5 단계에서 사용자에게 묻습니다.

## 2.5. 스코프 결정 (프로젝트 / 전체)

생성 위치를 결정합니다. 조용한 기본값은 없습니다.

- **`--project` 명시** → `<SKILL_BASE>` = `<project-root>/.claude/skills` (현재 작업 디렉토리 기준 `.claude/skills`). 없으면 생성.
- **`--global` 명시** → `<SKILL_BASE>` = `~/.claude/skills`
- **둘 다 없음** → **`AskUserQuestion` 도구로 스코프를 묻습니다** (응답 전 진행 X):

  ```json
  {
    "questions": [
      {
        "question": "이 skill 을 어디에 만들까요?",
        "header": "생성 스코프",
        "multiSelect": false,
        "options": [
          {"label": "프로젝트", "description": "현재 프로젝트의 `.claude/skills/` — 이 프로젝트에서만 발동"},
          {"label": "전체(글로벌)", "description": "`~/.claude/skills/` — 모든 프로젝트에서 발동"}
        ]
      }
    ]
  }
  ```

  사용자 선택("프로젝트" / "전체")으로 `<SKILL_BASE>` 확정. 모호하면 1회 재질문 후 확정. `AskUserQuestion` 이 없는 하네스면 위 질문을 prose 로 대체.
- 확정된 스코프 값(`project` / `global`)은 § 5 의 마커 파일 `scope` 필드에 기록합니다.

## 3. LLM 분해 (5 단계)

### 3-1. 트리거 조건 추출 → `description` 필드 (1줄)

자유 텍스트의 **"~ 했을 때 / ~ 하면 / ~ 시"** 패턴을 catch 해서 `description` 형식으로 변환:

- 권장 패턴: `"Use when ..."` 또는 `"When the user ..."`
- max 120자 (초과 시 자동 trim — § 4 룰 적용)
- 1줄 (개행 절대 X)
- 능동태 동사로 시작 권장

예시:
```
입력: "사용자가 .md 파일을 저장하면 prettier 로 자동 포맷"
↓
description: "Use when the user saves a .md file — auto-format with prettier and report changed lines."
```

### 3-2. 수행 동작 추출 → 본문 instruction (bite-sized step 1~7)

자유 텍스트의 **동사구** 를 catch 해서 bite-sized step 으로 분해. 각 step:

- `### Step N — <헤더>` 형식
- 짧은 설명 1~3줄
- 권장 1~7 step. 8+ 단계는 사용자에게 "분리 필요" alert (강제 차단 X)

step 폭주 catch 시 다음 한 줄을 사용자에게:

> ⚠️ 입력 분해 결과 step {N} 개입니다. 너무 많을 수 있어요. 큰 작업이면 skill 두 개로 분리하는 것을 권합니다. 그대로 진행하려면 같은 명령을 다시 호출해주세요. 분리하려면 자유 텍스트를 두 개로 나눠 두 번 호출해주세요.

### 3-3. 슬러그 자동 생성 (또는 명시 인자 사용)

- 명시 인자 있으면 그대로 사용 (예: `/new-skill auto-format-md "..."` → `auto-format-md`)
- 없으면 자유 텍스트의 핵심 명사구 catch + 영문 kebab-case 변환:
  - 한국어 입력 → 핵심 의미 catch 후 영문화 (예: "마크다운 포맷터" → `markdown-formatter`)
  - 모호 시 prose 1줄 묻고 진행:

    > 슬러그 자동 생성이 모호합니다. 직접 지정해주시거나 다시 호출해주세요. 후보: `<slug-candidate-1>`, `<slug-candidate-2>`.

  - 무한 clarifying 방지 — 1회만 묻고 사용자 응답으로 확정 또는 abort.

### 3-4. `user-invocable` 결정

- 자유 텍스트에 "메뉴에 띄우지 마" / "숨겨" / "감춰" / "자동만" 단서 catch 시 → `user-invocable: false`
- 외 기본 → `user-invocable: true`

### 3-5. 충돌 검증

`<SKILL_BASE>/<slug>/SKILL.md` 존재 여부 LS 도구로 확인 (`<SKILL_BASE>` 는 § 2.5 에서 확정한 스코프 기준):

- 존재 X → § 5 의 Write 분기로
- 존재 Y + `--force` 명시 X → § 5 의 abort 분기로
- 존재 Y + `--force` 명시 Y → § 5 의 백업 + 덮어쓰기 분기로

**확정한 스코프 위치만 검증한다.** 반대 스코프(`--project` 면 글로벌, `--global` 이면 프로젝트) 또는 js-super 의 `<plugin>/skills/` cache 의 동일 이름 skill 은 검증 X — 사용자 catch 영역 (§ 6 보고 메시지 끝에 안내).

## 4. 사전 검증 룰 (Write 직전)

다음 3 휴리스틱 적용:

### 4-1. description 길이 (max 120자, 1줄)

- 120자 초과 → 자동 trim (마지막 토큰 단위 cut) + 사용자에게 한 줄 알림:

  > ℹ️ description 이 120자를 넘어 자동 정리했습니다. 원본 의도와 다르면 옵션 다시 빼고 호출해주세요.

- 개행 포함 → 자동 단일 줄 변환 (개행 → 공백)

### 4-2. 트리거 명확성 (warn 수준, 강제 X)

- "Use when" / "When the user" 패턴 미매치 시 prose 한 줄 안내:

  > ℹ️ description 이 트리거 패턴 ("Use when ...") 으로 시작하지 않아요. 자동 발동 정확도를 위해 권장합니다. 그래도 진행할게요.

### 4-3. 동사 시작 (warn 수준, 강제 X)

- 능동태 동사로 시작 X (예: "This skill ..." / "A helper ...") 시 prose 한 줄 안내:

  > ℹ️ description 이 동사로 시작하지 않아요. 자동 발동 정확도를 위해 권장합니다. 그래도 진행할게요.

### 4-4. 비밀값 / 토큰 / 하드코딩 경로 catch (abort)

자유 텍스트 또는 분해 결과에 다음 패턴 catch 시 즉시 abort:

- AWS key (`AKIA...`)
- OpenAI/Anthropic key (`sk-...`, `sk-ant-...`)
- Slack token (`xoxb-...`, `xoxp-...`)
- 일반 API key 패턴 (`api_key=` / `Bearer ` / 32+ hex 문자열)
- 사용자 PC 경로 (`/Users/<name>/` / `~/Library/` / `/home/<name>/`)

abort 메시지:

> ⚠️ 자유 텍스트에 비밀값 / 사용자 PC 경로로 보이는 패턴이 있어 중단했습니다.
>
> 해당 부분: `<catch 한 부분>`
>
> skill 본문에 비밀값 / 토큰 / 사용자 환경 경로를 박지 마세요. 환경변수 또는 빌더 호출 시점에 사용자 입력으로 받는 패턴을 권장합니다.

## 5. Write 또는 Dry-run 분기

아래 모든 분기에서 `<SKILL_BASE>` 는 § 2.5 에서 확정한 스코프 기준 경로입니다 (`<project-root>/.claude/skills` 또는 `~/.claude/skills`).

### 마커 파일 규약 (출처 표식)

신규 / 덮어쓰기 Write 시 SKILL.md 와 같은 디렉토리에 `.js-super-skill.json` 을 함께 작성합니다. 이 파일이 `/list-skills` 조회·`/remove-skill` 삭제의 js-super 출처 판별 기준입니다.

```json
{
  "generated_by": "js-super:new-skill",
  "scope": "<project|global>",
  "created": "<YYYY-MM-DDTHH:MM:SS>"
}
```

### 5-1. `--dry-run` 명시 시 (Write X)

frontmatter + 본문 instruction 미리보기만 메인 응답으로 출력:

```
ℹ️ /<slug> skill 미리보기 (--dry-run, Write X)

저장 위치 (예정): <SKILL_BASE>/<slug>/SKILL.md  (스코프: <project|global>)
함께 생성: <SKILL_BASE>/<slug>/.js-super-skill.json (출처 표식)

---
<frontmatter + 본문 preview>
---

옵션 빼고 재호출하면 실제 Write 합니다.
```

### 5-2. 기존 파일 존재 + `--force` 없음 (abort)

```
⚠️ <SKILL_BASE>/<slug>/SKILL.md 가 이미 존재합니다.

기존 파일: <SKILL_BASE>/<slug>/SKILL.md (<크기> KB, 마지막 수정 <timestamp>)

덮어쓰려면: /new-skill <slug> <스코프 플래그> --force "..." (백업 후 덮어쓰기)
다른 이름으로: /new-skill <다른-slug> "..."
미리보기만: /new-skill <slug> --dry-run "..."
```

### 5-3. 기존 파일 존재 + `--force` (백업 + 덮어쓰기)

다음 step 으로 진행 (단일 turn 흐름 — 사용자 응답 wait X):

1. Read 도구로 기존 `<SKILL_BASE>/<slug>/SKILL.md` 읽기
2. Write 도구로 `<SKILL_BASE>/<slug>/SKILL.md.bak-<YYYYMMDDHHMMSS>` 에 1번에서 읽은 내용 그대로 저장
3. Write 도구로 `<SKILL_BASE>/<slug>/SKILL.md` 덮어쓰기 (새 본문)
4. Write 도구로 `<SKILL_BASE>/<slug>/.js-super-skill.json` 작성 (위 마커 규약, 이미 있으면 갱신)
5. § 6 의 성공 보고 + 백업 경로 한 줄 추가

### 5-4. 신규 (정상 Write)

1. `<SKILL_BASE>/<slug>/` 디렉토리 생성 (필요 시)
2. `<SKILL_BASE>/<slug>/SKILL.md` 작성
3. Write 도구로 `<SKILL_BASE>/<slug>/.js-super-skill.json` 작성 (위 마커 규약)
4. § 6 의 성공 보고

## 6. 보고 양식

### 6-1. 성공

```
✅ /<slug> skill 이 <SKILL_BASE>/<slug>/SKILL.md 에 생성되었습니다. (스코프: <project|global>)

발동 조건: <description 1줄 요약>
출처 표식: <SKILL_BASE>/<slug>/.js-super-skill.json (이 파일이 있어야 /list-skills 조회·/remove-skill 삭제 대상이 됩니다)

저장 즉시 사용 가능합니다 (skill hot-reload).
- 사용자 명시 호출: /<slug>
- 자동 발동: Claude 가 description 매칭 판단 시 (프로젝트 스코프면 이 프로젝트에서만)
```

(`--force` 시 추가 한 줄):
```
백업: <SKILL_BASE>/<slug>/SKILL.md.bak-<timestamp>
```

(다른 위치 동일 이름 가능성 한 줄 — 확정 스코프 외 위치는 검증 X 이므로):
```
ℹ️ 반대 스코프 또는 다른 플러그인의 동일 이름 skill 이 있으면 자동 발동 우선순위가 모호해질 수 있습니다. 명시 호출 (`/<slug>`) 시 프로젝트 skill 이 글로벌보다 우선.
```

### 6-2. Dry-run — § 5-1 그대로

### 6-3. 충돌 abort — § 5-2 그대로

### 6-4. 비밀값 catch abort — § 4-4 그대로

## 7. 금지

- **description 1줄 이상 (개행 / 120자+ 그대로) 금지** — 자동 trim 룰 (§ 4-1) 우선 적용
- **동일 이름 skill 덮어쓰기 (`--force` 없이) 금지** — § 5-2 abort
- **skill 본문에 비밀값 / 토큰 / 하드코딩 경로 박기 금지** — § 4-4 catch
- **확정 스코프 외 위치 (반대 스코프 / `<plugin>/skills/`) 자동 검증 금지** — D-T4 단순성. 사용자 catch 영역
- **출처 표식(`.js-super-skill.json`) 작성 누락 금지** — 신규/덮어쓰기 Write 시 반드시 함께 작성 (§ 5). 누락 시 `/list-skills` 조회·`/remove-skill` 삭제 대상에서 빠짐
- **`commands/<slug>.md` 자동 생성 금지** — commands 는 hot-reload 미지원이라 빌더 의미 ↓ (META-BUILDER §2). skill 만 생성

## 8. dogfood 시나리오 (사용자 검증용)

빌더 동작 검증 시 다음 8 시나리오 참고:

| 시나리오 | 입력 | 기대 |
|---|---|---|
| T-1 happy path (slug 자동) | `/new-skill "사용자가 X 하면 Y 와 Z 차례로 수행"` | `~/.claude/skills/<auto-slug>/SKILL.md` 생성 + § 6-1 보고 |
| T-2 slug 명시 | `/new-skill my-helper "..."` | `~/.claude/skills/my-helper/SKILL.md` 생성 |
| T-3 dry-run | `/new-skill --dry-run "..."` | 메인 응답 preview + Write X |
| T-4 충돌 + force X | (T-1 직후 재호출) | abort + 기존 파일 안내 |
| T-5 충돌 + --force | `/new-skill my-helper --force "..."` | 백업 (`.bak-<timestamp>`) + 덮어쓰기 |
| T-6 비밀값 catch | `/new-skill "AWS_KEY=AKIA... 박아"` | abort + 비밀값 catch 안내 |
| T-7 description 길이 위반 | `/new-skill "150자 넘는 길고 모호한 설명..."` | 자동 trim + 사용자 알림 |
| T-8 hot-reload 검증 | T-1 결과 직후 `/<slug>` 호출 | skill 본문 로드 + 동작 |

T-1 / T-3 / T-4 / T-8 = critical. T-5 / T-6 / T-7 = edge case.
