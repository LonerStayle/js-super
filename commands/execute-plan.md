---
description: <slug>-implementation-plan.md를 task-by-task로 실행합니다. 매 코드 변경마다 위험 주석 자동 부착 + 변경 전·후 코드를 변경이력에 보존합니다.
---

# /execute-plan

이 슬래시는 plan 의 task 수를 세서 실행 모드 양자택일을 묻고 해당 skill 을 호출합니다.

전제:
- 동일 피처 폴더에 `<slug>-implementation-plan.md` 가 있어야 합니다.
- plan 의 frontmatter 에 `commit_policy` 필드가 있어야 합니다 (없으면 `per-task` 로 간주).

## 0. 뮤테이션 도구 확인 (프로젝트당 한 번만 묻기)

실행 모드를 묻기 전에 이 프로젝트 언어의 뮤테이션 도구가 있는지 한 번 봅니다. 없으면 커밋 직전 검사에서 C7 뮤테이션이 매번 건너뛰어지는데, 그 안내는 코드를 다 쓴 뒤에야 나옵니다. 그래서 여기서 먼저 묻습니다. 이 확인은 아무것도 막지 않습니다 — 어느 답이든 실행 모드 질문으로 넘어갑니다.

```bash
P=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/js-super/*/scripts/preflight.py" 2>/dev/null | sort -V | tail -1); [ -f "$P" ] || P=scripts/preflight.py; if [ -f "$P" ]; then python3 "$P" mutation-tools; else echo "PREFLIGHT_ABSENT"; fi
```

`${CLAUDE_PLUGIN_ROOT}` 는 쓰지 않습니다 (슬래시 커맨드의 Bash 환경에서 채워지지 않습니다). 가상환경도 켜지 않습니다 — 스크립트가 검사 대상 프로젝트의 인터프리터를 스스로 찾습니다.

출력 첫 줄로 분기합니다.

| 첫 줄 | 다음 |
|---|---|
| `MUTATION_TOOLS_OK` | 아무 말 없이 실행 모드 질문으로 넘어갑니다 |
| `MUTATION_TOOLS_ASK` | 그 아래 `- <언어> \| ...` 줄마다 (언어마다) `AskUserQuestion` 을 한 번씩 부릅니다 |
| `PREFLIGHT_ABSENT` | 한 줄 알리고 넘어갑니다: `ℹ️ 뮤테이션 도구 확인을 건너뜁니다 (js-super 스크립트를 찾지 못했습니다).` |
| 그 밖 (빈 출력 · 다른 첫 줄) | 옛 버전 캐시가 잡힌 경우입니다. `PREFLIGHT_ABSENT` 와 같이 한 줄 알리고 넘어갑니다 |

`안내:` 로 시작하는 줄이 있으면 그대로 보여줍니다 (자바 · 러스트처럼 기본이 꺼진 언어를 켜는 법). 스크립트가 한 번 보여준 뒤 기록하므로 다음부터는 나오지 않습니다.

**질문 형식 (언어마다 한 번)**

- 질문 본문: "<언어> 뮤테이션 도구(<도구>)가 없습니다. 설치할까요?" 다음 줄에 스크립트가 낸 **설치 명령과 설치 범위를 그대로** 적습니다. 범위가 "사용자 환경 (프로젝트 밖)" 이면 그 사실을 빼지 않습니다. 줄 끝에 `|` 로 덧붙은 안내가 있으면 그것도 옮깁니다.
- 선택지 셋: **설치한다** / **설치하지 않는다 (다시 묻지 않음)** / **이번만 건너뛴다 (다음에 다시 묻기)**

| 답 | 하는 일 |
|---|---|
| 설치한다 | 표의 설치 명령을 프로젝트 루트에서 **그대로** 실행합니다 (다른 명령으로 바꾸거나 전역 설치로 바꾸지 않습니다). 종료 코드 0 이면 `installed`, 아니면 출력 마지막 줄을 보여주고 `install_failed` 로 기록합니다 |
| 설치하지 않는다 | `declined` 로 기록합니다. 다시 물으려면 `.js-super/mutation-tools.json` 에서 그 언어 줄을 지우면 된다고 한 줄 알립니다 |
| 이번만 건너뛴다 | 기록하지 않습니다. 다음 실행에 다시 묻습니다 |

기록은 같은 스크립트로 합니다 (Bash 호출 사이에 변수가 남지 않으므로 경로를 다시 찾습니다).

```bash
P=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/js-super/*/scripts/preflight.py" 2>/dev/null | sort -V | tail -1); [ -f "$P" ] || P=scripts/preflight.py; python3 "$P" mutation-tools --record <언어>=<installed|install_failed|declined>
```

- `.code-gate.json` 은 건드리지 않습니다. 사람만 고치는 파일입니다. 기록은 `.js-super/mutation-tools.json` 에만 남습니다.
- `--no-ask` 플래그가 있으면 이 질문도 prose 로 묻습니다 (아래 `--no-ask` 절).
- `/auto-execute-plan` 은 이 단계를 거치지 않습니다. 자동 흐름은 묻지 않습니다.

## 실행 모드 양자택일

| 옵션 | skill | 권장 |
|---|---|---|
| **1) 인라인** | `executing-plans` | 중간 크기 plan (task 12개 이하) |
| **2) 보조 에이전트** | `js-super-sub-driven` | 큰 plan (task 13개 이상) |

다음 메시지로 사용자에게 묻습니다:

> "Plan 에 task 가 <N> 개 있습니다. 두 가지 실행 방식이 있어요:
>
> 1. **인라인** (중간 크기 plan, 12개 이하 권장) — 메인 에이전트가 `executing-plans` 로 직접 편집합니다. 빠르고 전체 토큰이 적게 들지만, task 수에 따라 메인 컨텍스트가 누적됩니다.
> 2. **보조 에이전트** (큰 plan, 13개 이상 권장) — `js-super-sub-driven` 으로 implementer + spec reviewer 보조 에이전트가 처리합니다. 메인 컨텍스트는 보존되지만, 호출 비용이 추가됩니다.
>
> 어느 쪽으로 진행할까요?"

upstream 원본 `subagent-driven-development` 는 이 양자택일에서 제시하지 않습니다. 사용자가 명시적으로 "upstream 원본으로" 요청한 경우에만 호출합니다.

## 자동 동작 (인라인 / 보조 에이전트 공통)

- `risk-annotation` 의 3-체크리스트가 동작하며, 필요 시 `# ⚠️ RISK(...)` 주석을 자동으로 붙입니다.
- 매 task 가 끝날 때마다 `<slug>-implementation-plan.md` 의 변경이력에 `[코드-수정]` entry 를 추가합니다.
- `commit_policy: per-task` 인 경우 task 단위로 atomic commit 합니다.

차이점은:
- **인라인** — 메인이 직접 편집합니다. git-fast / memory-fallback 모드가 자동 선택됩니다.
- **보조 에이전트 (js-super)** — implementer + spec reviewer 보조 에이전트가 작업하고, 메인이 RISK / 변경이력 / atomic commit 후처리를 합니다. 호출하는 skill 은 `js-super-sub-driven` 입니다.

## `--no-ask` 플래그 (v2.5+)

`AskUserQuestion` 도구가 느리거나 불안정할 때, 도구 호출을 완전히 우회하고 싶을 때 사용:

`/execute-plan <slug> --no-ask`

질문은 그대로 받지만 메인 에이전트가 채팅 메시지 (prose) 형식으로 묻습니다. 사용자도 채팅으로 응답하면 됩니다. 알람 fire X — 백그라운드 작업 중이면 응답 시점을 직접 체크해야 합니다.

플래그 위치 자유 (`<slug> --no-ask` 또는 `--no-ask <slug>` 모두 가능).
