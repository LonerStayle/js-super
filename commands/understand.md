---
description: 코드베이스를 분석해 지식 그래프(.ua/knowledge-graph.json)를 생성합니다 — Understand-Anything v2.9.4 이식판, /understand-chat·diff·explain·onboard 의 입력
argument-hint: "[path] [--full | --review | --here | --language <code> | --exclude <glob>]"
disable-model-invocation: true
---

# /understand — 코드베이스 지식 그래프 생성

대상 프로젝트를 분석해 `.ua/knowledge-graph.json` 을 만든다. 구조 추출은 원본 엔진(tree-sitter 기반 결정론 스크립트)이, 의미 요약은 보조 에이전트가 맡는다. 이미 그래프가 있으면 변경분만 증분 분석한다.

이 커맨드는 Understand-Anything v2.9.4 의 이식판이다. 절차 본문은 아래 엔진 사본 안의 원본 문서를 그대로 따르고, js-super 환경에 맞는 덮어쓰기 조항만 이 파일에 둔다.

## 0. 준비 — 엔진 사본 확보 (반드시 선행)

아래 검사를 순서대로 통과해야 분석을 시작할 수 있다. 실패하면 그 지점에서 한국어로 안내하고 즉시 중단한다 — 반쯤 진행한 채 실패하지 않는다.

**0-1. 도구 검사** — 네 가지 모두 확인:

```bash
git --version && node --version && pnpm --version && python3 --version
```

node 는 22 이상, pnpm 은 10 이상이어야 한다. 하나라도 없거나 버전 미달이면 무엇이 부족한지와 설치 방법을 안내하고 중단한다.

**0-2. 경로 두 가지 — 서로 다르다** — 원저장소는 저장소 루트 아래에 플러그인 폴더가 한 겹 더 있는 구조다. 그래서 내려받는 위치와 엔진을 실제로 실행하는 위치가 다르다.

| 부르는 이름 | 경로 | 무엇 |
|---|---|---|
| 사본 루트 | `~/.understand-anything-plugin` | clone 이 만드는 디렉토리 (저장소 전체) |
| 엔진 기준 경로 | `~/.understand-anything-plugin/understand-anything-plugin` | 실제 플러그인 — 절차 본문·보조 에이전트 프롬프트·스크립트·엔진 패키지가 여기 있다 |

아래 명령들은 Bash 호출마다 새 셸에서 돌아 변수가 이어지지 않으므로, 경로를 변수에 담지 말고 그대로 적는다.

**0-3. 엔진 사본 존재 검사**:

```bash
ls ~/.understand-anything-plugin/understand-anything-plugin/skills/understand/SKILL.md 2>/dev/null
```

- **없으면** (최초 1회, 네트워크 필요) — "엔진 사본을 내려받습니다 (최초 1회)" 한 줄을 안내한 뒤 사본 루트로 clone 한다:

```bash
git clone --depth 1 --branch v2.9.4 https://github.com/Egonex-AI/Understand-Anything.git ~/.understand-anything-plugin
```

  clone 실패(네트워크 불가·저장소 소실) 시 원인을 안내하고 중단한다.

- **있으면** 버전 검사:

```bash
grep '"version"' ~/.understand-anything-plugin/understand-anything-plugin/.claude-plugin/plugin.json
```

  출력이 `2.9.4` 가 아니면 AskUserQuestion 으로 "고정 버전(v2.9.4)으로 재설치할까요?" 를 묻는다 — 예: 사본 루트를 `~/.understand-anything-plugin.bak-<타임스탬프>` 로 rename 한 뒤 위 clone 을 다시 실행 / 아니오: 중단. **버전이 다른 사본으로는 진행하지 않는다.**

**0-4. 엔진 빌드 확인** — 엔진 기준 경로 안에서 돌린다 (그 안에 자체 workspace 설정이 있다). 명령은 원본이 쓰는 것과 같다:

```bash
ls ~/.understand-anything-plugin/understand-anything-plugin/packages/core/dist/index.js 2>/dev/null \
  || (cd ~/.understand-anything-plugin/understand-anything-plugin \
      && (pnpm install --frozen-lockfile 2>/dev/null || pnpm install) \
      && pnpm --filter @understand-anything/core build)
```

빌드 실패 시 에러 요약과 Node/pnpm 버전 재확인 안내 후 중단한다.

## 1. 실행 — 원본 절차를 그대로 따른다

`~/.understand-anything-plugin/understand-anything-plugin/skills/understand/SKILL.md` 를 Read 도구로 전부 읽고, 그 안의 Phase 0~7 절차를 그대로 수행한다. 사용자가 준 인자(`$ARGUMENTS`)도 원본 규약대로 해석한다 (`--here` 만 예외 — 덮어쓰기 O-3).

보조 에이전트가 필요한 단계는 같은 엔진 기준 경로 아래 `agents/<이름>.md` 프롬프트 파일을 읽어 범용 보조 에이전트(general-purpose)로 호출한다. 병렬 상한(파일 분석 동시 5개)과 배치 파일명 규약은 원본 그대로 지킨다.

## 2. 덮어쓰기 조항 (원본 절차보다 우선)

| # | 원본 | 이식판 |
|---|---|---|
| O-1 | 설치 경로를 여러 후보에서 스스로 찾음 (Phase 0) | 탐색 생략 — §0-2 의 엔진 기준 경로로 고정. 원본 탐색은 플러그인이 최상위에 놓인 배치를 전제하는데 이 사본은 한 겹 안쪽이라 맞지 않는다 |
| O-2 | 사용자 확인을 산문으로 대기 (ignore 파일 확인 / 대규모 스코핑 / 출력 언어 확인) | AskUserQuestion 도구로 호출. 확인 지점의 수와 발생 조건은 원본 그대로 — 새 게이트 추가 금지이며, 원본이 조건부로 띄우는 확인은 조건이 안 맞으면 안 뜨는 게 정상이다 |
| O-3 | 워크트리 리다이렉트 옵트아웃 = 환경변수로 끔 | 인자에 `--here` 가 있으면 엔진을 실행하는 **모든 Bash 호출의 맨 앞에** `UNDERSTAND_NO_WORKTREE_REDIRECT=1 ` 를 붙여 현재 위치에 저장한다 (Bash 호출마다 셸이 새로 뜨므로 한 번 export 로는 이어지지 않는다). 인자가 없으면 변수를 아예 붙이지 않아 원본대로 메인 저장소 루트에 저장된다 |
| O-4 | 종료 시 `/understand-dashboard` 자동 호출 | 호출 금지 — 아래 §3 viewer 안내로 대체 |
| O-5 | 안내문 영어 | 사용자에게 보이는 진행 보고·질문·요약은 한국어 친화 톤 (짧은 문장, 영어 식별자 최소). 그래프 내용(요약·레이어명)의 언어는 원본의 자동 감지와 `config.json` 저장 동작 그대로 |

이 표에 없는 것은 전부 원본 그대로다. 특히 배치 파일명 규약(`batch-<N>.json` / `batch-<N>-part-<k>.json`)과 병합·검증·지문 생성 절차는 절대 변형하지 않는다 — 어기면 병합 단계에서 결과가 조용히 유실된다.

## 3. 종료 보고

원본 Phase 7 의 요약 보고에 다음을 한국어로 덧붙인다:

1. **viewer 안내** 한 줄:

```bash
npx --yes https://github.com/Egonex-AI/Understand-Anything/releases/download/v2.9.4/understand-anything-viewer.tgz "<분석한 프로젝트 경로>"
```

   viewer 가 뜨면 출력의 **토큰 포함 URL** (`http://127.0.0.1:<PORT>?token=...`) 을 사용자에게 반드시 전달한다. 기동 실패 시엔 실패 사유만 안내한다 — 그래프는 이미 생성돼 있어 손실이 없다.

2. **gitignore 권장** — 대상 프로젝트에 아직 없다면 다음 네 줄을 안내한다. 앞의 셋은 실행 중 생겼다 사라지는 작업 파일이고, 마지막은 변경 분석을 돌릴 때만 생기는 임시 산출물이다.

```gitignore
.ua/intermediate/
.ua/tmp/
.ua/.trash-*/
.ua/diff-overlay.json
```

3. **재실행 안내**: 같은 명령을 다시 실행하면 변경분만 증분 분석한다.
