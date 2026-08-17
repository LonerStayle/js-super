---
commit_policy: per-task
---

# understand-anything-command 구현계획서

> **다음 단계 안내**: 이 계획을 task-by-task 로 실행하려면 `js-super-sub-driven` (보조 에이전트 강제 모드, 권장) 또는 `executing-plans` (인라인 모드) 를 사용하세요. 각 step 은 체크박스 (`- [ ]`) 형식이라 진행 상황 추적이 가능합니다.

**Goal:** Understand-Anything v2.9.4 의 그래프 생성 + 조회 4종을 js-super 의 명시 호출 전용 커맨드 5개로 이식한다.

**Architecture:** js-super 저장소에는 얇은 진입점(커맨드 5개)만 남긴다. 분석 엔진·스크립트·보조 에이전트 프롬프트는 최초 실행 때 원저장소를 `~/.understand-anything-plugin` 에 버전 고정 clone 해 재사용한다. `/understand` 는 사본 안의 원본 절차를 그대로 따르고 덮어쓰기 조항 5개만 적용하며, 조회 4종은 본문을 인라인 이식해 엔진 없이도 동작한다.

**Tech Stack:** 커맨드 markdown (instruction-only) / bash (부트스트랩 검사) / 원본 엔진(Node + pnpm + Python, 사용자 머신에서 준비)

**Spec inputs:**
- understand-anything-command-requirements.md — FR-1~FR-9 (5 커맨드, 명시 호출 전용, 런타임 엔진 확보, viewer 재활용, 워크트리 정책, 규모 보고, 한국어 톤)
- understand-anything-command-tech-design.md — D-1(원본 참조 + 덮어쓰기) / D-2(조회 인라인) / D-3(사본 위치·버전 검사) / D-4(프롬프트 파일 직접 호출) / D-5(AskUserQuestion + 톤) / D-6(워크트리) / D-7(viewer 안내) / D-8(훅 없음), R-1~R-7

---

## 1. 단계별 작업

### Task 1: commands/understand.md — 메인 파이프라인 커맨드

**Files:**
- Create: `commands/understand.md`

**Model**: haiku

**검증**: 파일이 frontmatter `disable-model-invocation: true` 를 갖고, 본문에 버전 고정 문자열(clone 태그 `v2.9.4` 와 viewer 릴리즈 URL)이 각각 존재한다 — `grep -c "disable-model-invocation: true"` 가 1, `grep -c "v2.9.4"` 가 2 이상.

- [ ] **Step 1: 파일 작성 (아래 내용 그대로)**

**수정 후** (new file: `commands/understand.md`):

````markdown
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
````

- [ ] **Step 2: 검증 명령 실행**

Run: `grep -c "disable-model-invocation: true" commands/understand.md && grep -c "v2.9.4" commands/understand.md`
Expected: `1` 그리고 `2` 이상

- [ ] **Step 3: Commit**

```bash
git add commands/understand.md
git commit -m "feat(understand): /understand 메인 파이프라인 커맨드 — 부트스트랩 + 원본 절차 참조 + 덮어쓰기 5조항"
```

### Task 2: commands/understand-chat.md — 그래프 질의응답

**Files:**
- Create: `commands/understand-chat.md`

**Model**: haiku

**검증**: 파일이 `disable-model-invocation: true` 와 공통 최신성 검사 블록(`GRAPH_COMMIT_RAW`)을 갖는다 — 각각 grep 매치 1 이상.

- [ ] **Step 1: 파일 작성 (아래 내용 그대로)**

**수정 후** (new file: `commands/understand-chat.md`):

````markdown
---
description: 지식 그래프 기반 코드베이스 질의응답 — /understand 산출물(.ua/knowledge-graph.json)을 읽어 답합니다
argument-hint: "[query]"
disable-model-invocation: true
---

# /understand-chat

최종 답변과 사용자 안내는 한국어 친화 톤으로 쓴다 (짧은 문장, 영어 식별자 최소). 아래 절차 본문은 원본(Understand-Anything v2.9.4) 그대로다.

Answer questions about this codebase using the knowledge graph in the project's data directory (`.ua/knowledge-graph.json`, or the legacy `.understand-anything/knowledge-graph.json` when that directory is present).

## Graph Structure Reference

The knowledge graph JSON has this structure:
- `project` — {name, description, languages, frameworks, analyzedAt, gitCommitHash}
- `nodes[]` — each has {id, type, name, filePath?, summary, tags[], complexity, languageNotes?}
  - Code node types: file, function, class, module, concept
  - Non-code node types: config, document, service, table, endpoint, pipeline, schema, resource
  - Domain/knowledge node types: domain, flow, step, article, entity, topic, claim, source
  - IDs use the node type as prefix, e.g. `file:path`, `function:path:name`, `config:path`, `article:path`
- `edges[]` — each has {source, target, type, direction, weight}
  - Key types: imports, contains, calls, depends_on, configures, documents, deploys, triggers, contains_flow, flow_step, related, cites
- `layers[]` — each has {id, name, description, nodeIds[]}
- `tour[]` — each has {order, title, description, nodeIds[]}

## How to Read Efficiently

1. Use Grep to search within the JSON for relevant entries BEFORE reading the full file
2. Only read sections you need — don't dump the entire graph into context
3. Node names and summaries are the most useful fields for understanding
4. Edges tell you how components connect — follow imports and calls for dependency chains

## Instructions

1. **Resolve the data directory `$UA_DIR`.** Run `UA_DIR=$([ -d .understand-anything ] && echo .understand-anything || echo .ua)` — this is the legacy `.understand-anything/` when it already exists, otherwise the new `.ua/`. Check that `$UA_DIR/knowledge-graph.json` exists in the current project root. If not, tell the user to run `/understand` first.

2. **Check graph freshness before using graph-derived context**:
   - Read `project.gitCommitHash` from the graph metadata as `GRAPH_COMMIT_RAW`. Resolve it as a commit before using it in any Git diff, then compare it with `git rev-parse HEAD` and inspect project-scoped committed and working-tree changes from the project root:
     ```bash
     GRAPH_COMMIT=$(git rev-parse --verify --end-of-options "${GRAPH_COMMIT_RAW}^{commit}" 2>/dev/null)
     git rev-parse HEAD
     git diff --name-only "$GRAPH_COMMIT" HEAD -- .
     git diff --cached --name-only -- .
     git diff --name-only -- .
     git ls-files --others --exclude-standard -- .
     ```
   - The `-- .` pathspec is required: commits that only touch a sibling monorepo project must not make this graph stale. A hash mismatch alone is not stale when the project diff is empty.
   - Ignore the selected data directory (`.ua/` or legacy `.understand-anything/`) in every command's output because it contains generated graph artifacts, not project source drift.
   - If the committed diff or any working-tree command reports project files, warn before answering that graph-derived context may omit those changes. Suggest: Run `/understand` to refresh the graph.
   - Run the commit diff only when `GRAPH_COMMIT_RAW` resolves successfully. If the graph commit or Git metadata is missing, invalid, or unavailable, give a brief best-effort warning and continue instead of blocking.

3. **Read project metadata only** — use Grep or Read with a line limit to extract just the `"project"` section from the top of the file for context (name, description, languages, frameworks).

4. **Search for relevant nodes** — use Grep to search the knowledge graph file for the user's query keywords: "$ARGUMENTS"
   - Search `"name"` fields: `grep -i "query_keyword"` in the graph file
   - Search `"summary"` fields for semantic matches
   - Search `"tags"` arrays for topic matches
   - Note the `id` values of all matching nodes

5. **Find connected edges** — for each matched node ID, Grep for that ID in the `edges` section to find:
   - What it imports or depends on (downstream)
   - What calls or imports it (upstream)
   - This gives you the 1-hop subgraph around the query

6. **Read layer context** — Grep for `"layers"` to understand which architectural layers the matched nodes belong to.

7. **Answer the query** using only the relevant subgraph:
   - Reference specific files, functions, and relationships from the graph
   - Explain which layer(s) are relevant and why
   - Be concise but thorough — link concepts to actual code locations
   - If the query doesn't match any nodes, say so and suggest related terms from the graph
````

- [ ] **Step 2: 검증 명령 실행**

Run: `grep -c "disable-model-invocation: true" commands/understand-chat.md && grep -c "GRAPH_COMMIT_RAW" commands/understand-chat.md`
Expected: `1` 그리고 `1` 이상

- [ ] **Step 3: Commit**

```bash
git add commands/understand-chat.md
git commit -m "feat(understand): /understand-chat 그래프 질의응답 커맨드 인라인 이식"
```

### Task 3: commands/understand-diff.md — 변경 영향 분석

**Files:**
- Create: `commands/understand-diff.md`

**Model**: haiku

**검증**: 파일이 `disable-model-invocation: true` 와 최신성 블록을 갖고, 원본의 대시보드 자동 호출 문구 대신 viewer 릴리즈 URL 이 들어 있다 — `understand-dashboard` grep 0, viewer URL grep 1.

- [ ] **Step 1: 파일 작성 (아래 내용 그대로)**

**수정 후** (new file: `commands/understand-diff.md`):

````markdown
---
description: 현재 변경분의 영향 범위 분석 — 지식 그래프로 변경·영향 컴포넌트와 위험을 구조화해 보고합니다
disable-model-invocation: true
---

# /understand-diff

최종 답변과 사용자 안내는 한국어 친화 톤으로 쓴다 (짧은 문장, 영어 식별자 최소). 아래 절차 본문은 원본(Understand-Anything v2.9.4) 그대로다.

Analyze the current code changes against the knowledge graph in the project's data directory (`.ua/knowledge-graph.json`, or the legacy `.understand-anything/knowledge-graph.json` when that directory is present).

## Graph Structure Reference

The knowledge graph JSON has this structure:
- `project` — {name, description, languages, frameworks, analyzedAt, gitCommitHash}
- `nodes[]` — each has {id, type, name, filePath?, summary, tags[], complexity, languageNotes?}
  - Code node types: file, function, class, module, concept
  - Non-code node types: config, document, service, table, endpoint, pipeline, schema, resource
  - Domain/knowledge node types: domain, flow, step, article, entity, topic, claim, source
  - IDs use the node type as prefix, e.g. `file:path`, `function:path:name`, `config:path`, `article:path`
- `edges[]` — each has {source, target, type, direction, weight}
  - Key types: imports, contains, calls, depends_on, configures, documents, deploys, triggers, contains_flow, flow_step, related, cites
- `layers[]` — each has {id, name, description, nodeIds[]}
- `tour[]` — each has {order, title, description, nodeIds[]}

## How to Read Efficiently

1. Use Grep to search within the JSON for relevant entries BEFORE reading the full file
2. Only read sections you need — don't dump the entire graph into context
3. Node names and summaries are the most useful fields for understanding
4. Edges tell you how components connect — follow imports and calls for dependency chains

## Instructions

1. **Resolve the data directory `$UA_DIR`.** Run `UA_DIR=$([ -d .understand-anything ] && echo .understand-anything || echo .ua)` — this is the legacy `.understand-anything/` when it already exists, otherwise the new `.ua/`. Check that `$UA_DIR/knowledge-graph.json` exists. If not, tell the user to run `/understand` first.

2. **Get the changed files list** (do NOT read the graph yet):
   - If on a branch with uncommitted changes: `git diff --name-only`
   - If on a feature branch: `git diff main...HEAD --name-only` (or the base branch)
   - If the user specifies a PR number: get the diff from that PR

3. **Read project metadata and check graph freshness** — use Grep or Read with a line limit to extract the `"project"` section, including `gitCommitHash` as `GRAPH_COMMIT_RAW`, then:
   - Resolve it as a commit before using it in any Git diff. From the project root, compare the resolved commit with `git rev-parse HEAD` and inspect project-scoped committed and working-tree changes:
     ```bash
     GRAPH_COMMIT=$(git rev-parse --verify --end-of-options "${GRAPH_COMMIT_RAW}^{commit}" 2>/dev/null)
     git rev-parse HEAD
     git diff --name-only "$GRAPH_COMMIT" HEAD -- .
     git diff --cached --name-only -- .
     git diff --name-only -- .
     git ls-files --others --exclude-standard -- .
     ```
   - The `-- .` pathspec is required: commits that only touch a sibling monorepo project must not make this graph stale. A hash mismatch alone is not stale when the project diff is empty.
   - Ignore the selected data directory (`.ua/` or legacy `.understand-anything/`) in every command's output because it contains generated graph artifacts, not project source drift.
   - If the committed diff or any working-tree command reports project files, warn before impact analysis that the graph may omit those changes. Suggest: Run `/understand` to refresh the graph.
   - Run the commit diff only when `GRAPH_COMMIT_RAW` resolves successfully. If the graph commit or Git metadata is missing, invalid, or unavailable, give a brief best-effort warning and continue instead of blocking.

4. **Find nodes for changed files** — for each changed file path, use Grep to search the knowledge graph for:
   - Nodes with matching `"filePath"` values (e.g., `grep "changed/file/path"`)
   - This finds file-level nodes (including non-code types) AND function/class nodes defined in those files
   - Note the `id` values of all matched nodes

5. **Find connected edges (1-hop)** — for each matched node ID, Grep for that ID in the edges to find:
   - What imports or depends on the changed nodes (upstream callers)
   - What the changed nodes import or call (downstream dependencies)
   - These are the "affected components" — things that might break or need updating

6. **Identify affected layers** — Grep for the matched node IDs in the `"layers"` section to determine which architectural layers are touched.

7. **Provide structured analysis**:
   - **Changed Components**: What was directly modified (with summaries from matched nodes)
   - **Affected Components**: What might be impacted (from 1-hop edges)
   - **Affected Layers**: Which architectural layers are touched and cross-layer concerns
   - **Risk Assessment**: Based on node `complexity` values, number of cross-layer edges, and blast radius (number of affected components)
   - Suggest what to review carefully and any potential issues

8. **Write diff overlay for dashboard** — after producing the analysis, write the diff data to `$UA_DIR/diff-overlay.json` so the dashboard can visualize changed and affected components. The file contains:
   ```json
   {
     "version": "1.0.0",
     "baseBranch": "<the base branch used>",
     "generatedAt": "<ISO timestamp>",
     "changedFiles": ["<list of changed file paths>"],
     "changedNodeIds": ["<node IDs from step 4>"],
     "affectedNodeIds": ["<node IDs from step 5, excluding changedNodeIds>"]
   }
   ```
   After writing, tell the user they can view the diff overlay visually by running:
   ```bash
   npx --yes https://github.com/Egonex-AI/Understand-Anything/releases/download/v2.9.4/understand-anything-viewer.tgz "<project-dir>"
   ```
   (viewer 가 뜨면 출력의 토큰 포함 URL 을 반드시 전달한다.)
````

- [ ] **Step 2: 검증 명령 실행**

Run: `grep -c "disable-model-invocation: true" commands/understand-diff.md && grep -c "understand-dashboard" commands/understand-diff.md; grep -c "releases/download/v2.9.4/understand-anything-viewer.tgz" commands/understand-diff.md`
Expected: `1` / `0` (grep 이 매치 없음으로 exit 1 이어도 카운트 0 이면 통과) / `1`

- [ ] **Step 3: Commit**

```bash
git add commands/understand-diff.md
git commit -m "feat(understand): /understand-diff 변경 영향 분석 커맨드 인라인 이식 — 대시보드 호출을 viewer 안내로 대체"
```

### Task 4: commands/understand-explain.md — 파일·함수 딥다이브

**Files:**
- Create: `commands/understand-explain.md`

**Model**: haiku

**검증**: 파일이 `disable-model-invocation: true` 와 최신성 블록(`GRAPH_COMMIT_RAW`)을 갖는다 — 각각 grep 매치 1 이상.

- [ ] **Step 1: 파일 작성 (아래 내용 그대로)**

**수정 후** (new file: `commands/understand-explain.md`):

````markdown
---
description: 특정 파일·함수 딥다이브 설명 — 지식 그래프의 연결 관계 + 실제 소스를 함께 읽어 역할과 데이터 흐름을 설명합니다
argument-hint: "[file-path]"
disable-model-invocation: true
---

# /understand-explain

최종 답변과 사용자 안내는 한국어 친화 톤으로 쓴다 (짧은 문장, 영어 식별자 최소). 아래 절차 본문은 원본(Understand-Anything v2.9.4) 그대로다.

Provide a thorough, in-depth explanation of a specific code component.

## Graph Structure Reference

The knowledge graph JSON has this structure:
- `project` — {name, description, languages, frameworks, analyzedAt, gitCommitHash}
- `nodes[]` — each has {id, type, name, filePath?, summary, tags[], complexity, languageNotes?}
  - Code node types: file, function, class, module, concept
  - Non-code node types: config, document, service, table, endpoint, pipeline, schema, resource
  - Domain/knowledge node types: domain, flow, step, article, entity, topic, claim, source
  - IDs use the node type as prefix, e.g. `file:path`, `function:path:name`, `config:path`, `article:path`
- `edges[]` — each has {source, target, type, direction, weight}
  - Key types: imports, contains, calls, depends_on, configures, documents, deploys, triggers, contains_flow, flow_step, related, cites
- `layers[]` — each has {id, name, description, nodeIds[]}
- `tour[]` — each has {order, title, description, nodeIds[]}

## How to Read Efficiently

1. Use Grep to search within the JSON for relevant entries BEFORE reading the full file
2. Only read sections you need — don't dump the entire graph into context
3. Node names and summaries are the most useful fields for understanding
4. Edges tell you how components connect — follow imports and calls for dependency chains

## Instructions

1. **Resolve the data directory `$UA_DIR`.** Run `UA_DIR=$([ -d .understand-anything ] && echo .understand-anything || echo .ua)` — this is the legacy `.understand-anything/` when it already exists, otherwise the new `.ua/`. Check that `$UA_DIR/knowledge-graph.json` exists. If not, tell the user to run `/understand` first.

2. **Check graph freshness before using graph-derived context**:
   - Read `project.gitCommitHash` from the graph metadata as `GRAPH_COMMIT_RAW`. Resolve it as a commit before using it in any Git diff, then compare it with `git rev-parse HEAD` and inspect project-scoped committed and working-tree changes from the project root:
     ```bash
     GRAPH_COMMIT=$(git rev-parse --verify --end-of-options "${GRAPH_COMMIT_RAW}^{commit}" 2>/dev/null)
     git rev-parse HEAD
     git diff --name-only "$GRAPH_COMMIT" HEAD -- .
     git diff --cached --name-only -- .
     git diff --name-only -- .
     git ls-files --others --exclude-standard -- .
     ```
   - The `-- .` pathspec is required: commits that only touch a sibling monorepo project must not make this graph stale. A hash mismatch alone is not stale when the project diff is empty.
   - Ignore the selected data directory (`.ua/` or legacy `.understand-anything/`) in every command's output because it contains generated graph artifacts, not project source drift.
   - If the committed diff or any working-tree command reports project files, warn before explaining that graph-derived context may omit those changes. Suggest: Run `/understand` to refresh the graph.
   - Run the commit diff only when `GRAPH_COMMIT_RAW` resolves successfully. If the graph commit or Git metadata is missing, invalid, or unavailable, give a brief best-effort warning and continue instead of blocking.

3. **Find the target node** — use Grep to search the knowledge graph for the component: "$ARGUMENTS"
   - For file paths (e.g., `src/auth/login.ts`): search for `"filePath"` matches
   - For function notation (e.g., `src/auth/login.ts:verifyToken`): search for the function name in `"name"` fields filtered by the file path
   - Note the exact node `id`, `type`, `summary`, `tags`, and `complexity`

4. **Find all connected edges** — Grep for the target node's ID in the edges section:
   - `"source"` matches → things this node calls/imports/depends on (outgoing)
   - `"target"` matches → things that call/import/depend on this node (incoming)
   - Note the connected node IDs and edge types

5. **Read connected nodes** — for each connected node ID from step 4, Grep for those IDs in the nodes section to get their `name`, `summary`, and `type`. This builds the component's neighborhood.

6. **Identify the layer** — Grep for the target node's ID in the `"layers"` section to find which architectural layer it belongs to and that layer's description.

7. **Read the actual source file** — Read the source file at the node's `filePath` for the deep-dive analysis.

8. **Explain the component in context**:
   - Its role in the architecture (which layer, why it exists)
   - Internal structure (functions, classes it contains — from `contains` edges)
   - External connections (what it imports, what calls it, what it depends on — from edges)
   - Data flow (inputs → processing → outputs — from source code)
   - Explain clearly, assuming the reader may not know the programming language
   - Highlight any patterns, idioms, or complexity worth understanding
````

- [ ] **Step 2: 검증 명령 실행**

Run: `grep -c "disable-model-invocation: true" commands/understand-explain.md && grep -c "GRAPH_COMMIT_RAW" commands/understand-explain.md`
Expected: `1` 그리고 `1` 이상

- [ ] **Step 3: Commit**

```bash
git add commands/understand-explain.md
git commit -m "feat(understand): /understand-explain 딥다이브 커맨드 인라인 이식"
```

### Task 5: commands/understand-onboard.md — 온보딩 가이드 생성

**Files:**
- Create: `commands/understand-onboard.md`

**Model**: haiku

**검증**: 파일이 `disable-model-invocation: true` 와 최신성 블록(`GRAPH_COMMIT_RAW`)을 갖고, 산출물 경로 `docs/UA_ONBOARDING.md` 가 유지된다 — 각각 grep 매치 1 이상.

- [ ] **Step 1: 파일 작성 (아래 내용 그대로)**

**수정 후** (new file: `commands/understand-onboard.md`):

````markdown
---
description: 온보딩 가이드 문서 생성 — 지식 그래프의 레이어·투어·핵심 파일을 정리해 docs/UA_ONBOARDING.md 초안을 만듭니다
disable-model-invocation: true
---

# /understand-onboard

최종 답변과 사용자 안내는 한국어 친화 톤으로 쓴다 (짧은 문장, 영어 식별자 최소). 가이드 본문의 언어는 그래프 내용의 언어를 따른다. 아래 절차 본문은 원본(Understand-Anything v2.9.4) 그대로다.

Generate a comprehensive onboarding guide from the project's knowledge graph.

## Graph Structure Reference

The knowledge graph JSON has this structure:
- `project` — {name, description, languages, frameworks, analyzedAt, gitCommitHash}
- `nodes[]` — each has {id, type, name, filePath?, summary, tags[], complexity, languageNotes?}
  - Code node types: file, function, class, module, concept
  - Non-code node types: config, document, service, table, endpoint, pipeline, schema, resource
  - Domain/knowledge node types: domain, flow, step, article, entity, topic, claim, source
  - IDs use the node type as prefix, e.g. `file:path`, `function:path:name`, `config:path`, `article:path`
- `edges[]` — each has {source, target, type, direction, weight}
  - Key types: imports, contains, calls, depends_on, configures, documents, deploys, triggers, contains_flow, flow_step, related, cites
- `layers[]` — each has {id, name, description, nodeIds[]}
- `tour[]` — each has {order, title, description, nodeIds[]}

## How to Read Efficiently

1. Use Grep to search within the JSON for relevant entries BEFORE reading the full file
2. Only read sections you need — don't dump the entire graph into context
3. Node names and summaries are the most useful fields for understanding
4. Edges tell you how components connect — follow imports and calls for dependency chains

## Instructions

1. **Resolve the data directory `$UA_DIR`.** Run `UA_DIR=$([ -d .understand-anything ] && echo .understand-anything || echo .ua)` — this is the legacy `.understand-anything/` when it already exists, otherwise the new `.ua/`. Check that `$UA_DIR/knowledge-graph.json` exists. If not, tell the user to run `/understand` first.

2. **Check graph freshness before using graph-derived context**:
   - Read `project.gitCommitHash` from the graph metadata as `GRAPH_COMMIT_RAW`. Resolve it as a commit before using it in any Git diff, then compare it with `git rev-parse HEAD` and inspect project-scoped committed and working-tree changes from the project root:
     ```bash
     GRAPH_COMMIT=$(git rev-parse --verify --end-of-options "${GRAPH_COMMIT_RAW}^{commit}" 2>/dev/null)
     git rev-parse HEAD
     git diff --name-only "$GRAPH_COMMIT" HEAD -- .
     git diff --cached --name-only -- .
     git diff --name-only -- .
     git ls-files --others --exclude-standard -- .
     ```
   - The `-- .` pathspec is required: commits that only touch a sibling monorepo project must not make this graph stale. A hash mismatch alone is not stale when the project diff is empty.
   - Ignore the selected data directory (`.ua/` or legacy `.understand-anything/`) in every command's output because it contains generated graph artifacts, not project source drift.
   - If the committed diff or any working-tree command reports project files, warn before generating the guide that onboarding content may omit those changes. Suggest: Run `/understand` to refresh the graph.
   - Run the commit diff only when `GRAPH_COMMIT_RAW` resolves successfully. If the graph commit or Git metadata is missing, invalid, or unavailable, give a brief best-effort warning and continue instead of blocking.

3. **Read project metadata** — use Grep or Read with a line limit to extract the `"project"` section (name, description, languages, frameworks).

4. **Read layers** — Grep for `"layers"` to get the full layers array. These define the architecture and will structure the guide.

5. **Read the tour** — Grep for `"tour"` to get the guided walkthrough steps. These provide the recommended learning path.

6. **Read file-level structural nodes only** — use Grep to find nodes with file-level types (`file`, `config`, `document`, `service`, `pipeline`, `table`, `schema`, `resource`, `endpoint`) in the knowledge graph. Skip function-level and class-level nodes to keep the guide high-level. Extract each node's `name`, `filePath`, `summary`, and `complexity`.

7. **Identify complexity hotspots** — from the file-level nodes, find those with the highest `complexity` values. These are areas new developers should approach carefully.

8. **Generate the onboarding guide** with these sections:
   - **Project Overview**: name, languages, frameworks, description (from project metadata)
   - **Architecture Layers**: each layer's name, description, and key files (from layers + file nodes)
   - **Key Concepts**: important patterns and design decisions (from node summaries and tags)
   - **Guided Tour**: step-by-step walkthrough (from the tour section)
   - **File Map**: what each key file does (from file-level nodes, organized by layer)
   - **Complexity Hotspots**: areas to approach carefully (from complexity values)

9. Format as clean markdown
10. Offer to save the guide to `docs/UA_ONBOARDING.md` in the project
11. Suggest the user commit it to the repo for the team
````

- [ ] **Step 2: 검증 명령 실행**

Run: `grep -c "disable-model-invocation: true" commands/understand-onboard.md && grep -c "UA_ONBOARDING" commands/understand-onboard.md`
Expected: `1` 그리고 `1` 이상

- [ ] **Step 3: Commit**

```bash
git add commands/understand-onboard.md
git commit -m "feat(understand): /understand-onboard 온보딩 가이드 커맨드 인라인 이식"
```

### Task 6: README.md — 유틸리티 표 5행 + 주의 문단

**Files:**
- Modify: `README.md:531-534`

**Model**: haiku

**검증**: 유틸리티 표에 understand 계열 5행이 들어가고(표 행으로 시작하는 줄만 세어 5), 표 아래 주의 문단이 요구 사항·토큰 비용·동시 설치 세 가지를 모두 언급한다(각 문구 1건씩).

- [ ] **Step 1: 표와 문단 수정**

**원본** (`README.md:531-534`):
```markdown
| `/pretty-md` | `.md` 본문 다듬기 (의미는 안 바꿈) |
| `/tech-teach-me` | 요구사항·기술설계·구현계획 문서를 강의로 쪼개 한 강씩 설명 |

<br/>
```

**수정 후**:
```markdown
| `/pretty-md` | `.md` 본문 다듬기 (의미는 안 바꿈) |
| `/tech-teach-me` | 요구사항·기술설계·구현계획 문서를 강의로 쪼개 한 강씩 설명 |
| `/understand [path]` | 코드베이스 분석 → 지식 그래프 생성 (재실행 시 변경분만 증분) |
| `/understand-chat <질문>` | 그래프 기반 코드베이스 질의응답 |
| `/understand-diff` | 현재 변경분의 영향 범위 분석 |
| `/understand-explain <파일>` | 특정 파일·함수 딥다이브 설명 |
| `/understand-onboard` | 온보딩 가이드 문서 생성 |

> `/understand` 계열은 Understand-Anything v2.9.4 이식판입니다. 최초 실행 때 분석 엔진을 사용자 홈에 내려받아 준비하고 (git · Node 22 · pnpm 10 · Python 3 필요, 네트워크 1회), 전체 분석은 프로젝트 크기에 비례해 토큰을 씁니다 — 실행 전에 규모를 보고하고 큰 프로젝트면 범위 축소를 먼저 제안합니다. 원본 Understand-Anything 플러그인과 커맨드 이름이 겹치므로 동시 설치는 권장하지 않습니다.

<br/>
```

- [ ] **Step 2: 검증 명령 실행**

Run:
```bash
grep -cE '^\| `/understand' README.md
grep -c '네트워크 1회' README.md
grep -c '토큰을 씁니다' README.md
grep -c '동시 설치는 권장하지 않습니다' README.md
```
Expected: `5` / `1` / `1` / `1`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(understand): README 유틸리티 표에 understand 계열 5행 + 요구·비용 주의 문단"
```

### Task 7: CLAUDE.md — 결합 메모 + 회귀 catch grep

**Files:**
- Modify: `CLAUDE.md:1774` (파일 끝에 섹션 추가)

**Model**: haiku

**검증**: 결합 메모 섹션 헤더가 1건 존재하고, 그 안의 회귀 규칙 6건이 eval 러너가 읽는 형식(`# expected:` 주석)을 지킨다 — 주석 6건. 러너의 규칙 수집이 실제로 이 규칙들을 집어가는지도 함께 확인한다.

- [ ] **Step 1: 파일 끝에 섹션 추가**

**원본** (`CLAUDE.md:1774`):
````markdown
- `evals/` 는 Claude Code 의 자동 로드 경로 밖이라 사용자 세션에 안 올라간다
````

**수정 후**:
````markdown
- `evals/` 는 Claude Code 의 자동 로드 경로 밖이라 사용자 세션에 안 올라간다

## understand 커맨드 5종 결합 (Understand-Anything 이식)

Understand-Anything v2.9.4 의 그래프 생성(`/understand`)과 조회 4종(chat / diff / explain / onboard)을 커맨드 전용으로 이식. 엔진·스크립트·보조 에이전트 프롬프트는 저장소에 없고, 최초 실행 시 원저장소를 `~/.understand-anything-plugin` 에 버전 고정 clone 해 재사용한다. spec: `docs/features/2026-08-16-understand-anything-command/`.

### 핵심 룰

- 5 커맨드 모두 `disable-model-invocation: true` — 자동 발동 경로 0
- 엔진 확보는 런타임 clone (태그 v2.9.4) — 저장소에 엔진 코드·바이너리·빌드 파이프라인 반입 금지
- 조회 4종의 공통 블록 (Graph Structure Reference + 최신성 검사) 은 4파일 복붙 동기 — 한 곳 수정 시 4곳 동시 수정
- 버전 고정 문자열 (clone 태그 / viewer 릴리즈 URL) 은 등장하는 파일 전체에서 일치 유지 — 한쪽만 올리면 엔진과 viewer 의 스키마가 어긋난다
- `/understand` 의 덮어쓰기 표 (O-1~O-5) 밖 원본 절차는 무수정 — 특히 배치 파일명 규약을 변형하면 병합에서 조용히 유실된다
- 훅 미도입 — 증분 갱신은 `/understand` 재실행만. hooks/ 에 understand 관련 항목을 넣지 않는다

### 회귀 패턴 (한쪽만 변경 시)

| 누락 | 증상 |
|---|---|
| 조회 4종 공통 블록 한 곳만 수정 | 커맨드별 최신성 판정이 갈림 — 같은 그래프에 다른 경고 |
| clone 태그만 올리고 viewer URL 미동기 | 새 스키마 그래프를 옛 viewer 가 못 읽음 (또는 반대) |
| 스킬 디렉토리 신설 (skills/understand*) | 커맨드가 스킬을 가려 호출 불가 — 이름 충돌 룰 위반 |
| 훅에 자동 갱신 추가 | 요구사항 범위 밖 재유입 — 컨텍스트 상주 제거 취지 위배 |

### 회귀 catch grep

```bash
# 5 커맨드 존재 + 명시 호출 전용
grep -lF "disable-model-invocation: true" commands/understand.md commands/understand-chat.md commands/understand-diff.md commands/understand-explain.md commands/understand-onboard.md | wc -l
# expected: 5

# 커맨드 ↔ 스킬 이름 충돌 없음
ls -d skills/understand* 2>/dev/null | wc -l
# expected: 0

# 버전 고정 문자열 (clone 태그 + viewer URL)
grep -c "v2.9.4" commands/understand.md
# expected: >= 2

# 조회 4종 공통 최신성 블록 동기
grep -lF "GRAPH_COMMIT_RAW" commands/understand-chat.md commands/understand-diff.md commands/understand-explain.md commands/understand-onboard.md | wc -l
# expected: 4

# viewer URL 등장 파일 일치 (understand + understand-diff)
grep -rlF "releases/download/v2.9.4/understand-anything-viewer.tgz" commands/ | wc -l
# expected: 2

# 훅 미도입
grep -rln "understand-anything" hooks/ | wc -l
# expected: 0
```

### 영향 범위

- commands 5 신규 + README 1곳 + fixture 1 (`commands/understand-tests/H24-e2e/`). skills/ / scripts/ / hooks/ / agents/ 영향 0
- 버전 bump 는 main 전용 룰에 따라 main 에서
- 원본 플러그인과 동시 설치는 비전제 (커맨드 이름 동일) — README 주의 문단이 사용자 안내 캐리어
````

- [ ] **Step 2: 검증 명령 실행**

Run:
```bash
grep -c "## understand 커맨드 5종 결합" CLAUDE.md
awk '/^## understand 커맨드 5종 결합/,0' CLAUDE.md | grep -c '^# expected:'
python3 -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from evals.runner.coupling import collect_rules; print(sum(1 for r in collect_rules(Path('.')) if 'understand' in r.command))"
```
Expected: `1` / `6` / `6` 이상 (러너가 새 규칙을 실제로 수집)

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(understand): CLAUDE.md 결합 메모 — 5 커맨드 동기 룰 + 회귀 catch grep"
```

### Task 8: fixture — commands/understand-tests/H24-e2e/README.md

**Files:**
- Create: `commands/understand-tests/H24-e2e/README.md`

**Model**: haiku

**검증**: 사람이 돌리는 E2E 시나리오 문서가 준비 / 실행 순서와 기대 결과 / 실패 기록 세 섹션을 갖고, 실행 표에 10행이 들어간다 — 섹션 헤더 3건 + 표 행 10건.

- [ ] **Step 1: 파일 작성 (아래 내용 그대로)**

**수정 후** (new file: `commands/understand-tests/H24-e2e/README.md`):

````markdown
# H24 — /understand 계열 E2E 시나리오

`/understand` 5 커맨드 이식의 수동 검증 시나리오. 릴리즈 전 1회 사람이 돌린다.

## 준비

1. 소형 샘플 저장소 하나를 준비한다 (파일 20~40개 규모, git 초기화 + 커밋 1개 이상. js-super 저장소 자신도 가능).
2. `~/.understand-anything-plugin` 이 없는 상태에서 시작하면 부트스트랩 경로까지 검증된다 (있으면 버전 검사 경로만 검증).
3. git / Node 22+ / pnpm 10+ / Python 3 이 설치된 머신.

## 실행 순서와 기대 결과

| # | 실행 | 기대 결과 |
|---|---|---|
| 1 | 샘플 저장소에서 `/understand` | (사본 없을 때) "엔진 사본을 내려받습니다" 안내 → clone → 빌드. 도구 미충족이면 그 지점에서 한국어 안내 후 즉시 중단 |
| 2 | 계속 진행 | `.understandignore` 확인이 AskUserQuestion 팝업으로 온다 (산문 대기 아님). 대규모 스코핑 확인과 출력 언어 확인은 조건부라 이 소형 저장소에서는 안 떠도 통과 — 대신 파일 수를 세어 보고하는 줄이 진행 보고에 있어야 한다 |
| 3 | 완료 대기 | `.ua/knowledge-graph.json` + `meta.json` + `fingerprints.json` 생성. 종료 보고가 한국어 + viewer npx 한 줄 + gitignore 권장 네 줄 포함 |
| 4 | 안내된 viewer 명령 실행 | 브라우저에서 노드가 그려진 그래프 화면이 뜨고, 좌측 상단에 샘플 저장소 이름이 표시된다. 화면에 스키마 오류 배너가 없다 (있으면 버전 불일치) |
| 5 | `/understand-chat "엔트리포인트가 어디야"` | 그래프 기반 답변 (한국어). 그래프 없으면 `/understand` 먼저 실행 안내 |
| 6 | 파일 하나 수정 후 `/understand-diff` | 변경·영향 컴포넌트 + 위험 평가 구조화 보고 + `.ua/diff-overlay.json` 생성 + viewer 안내 |
| 7 | `/understand-explain <파일경로>` | 그래프 연결 관계 + 실제 소스 기반 딥다이브 설명 |
| 8 | `/understand-onboard` | 6섹션 온보딩 가이드 생성 + `docs/UA_ONBOARDING.md` 저장 제안 |
| 9 | `/understand` 재실행 | 진행 보고의 분석 대상 파일 수가 6번에서 고친 파일 수만큼으로 줄어든다 (1회차 전체 파일 수와 다름). 실행 후 `meta.json` 의 `gitCommitHash` 가 현재 HEAD 로 갱신된다 |
| 10 | 워크트리 안에서 `/understand` | 산출물이 메인 저장소 루트의 `.ua/` 에 생성. `--here` 를 주면 워크트리 안에 생성 |

## 실패 기록

발견한 어긋남은 이 파일 하단에 날짜와 함께 남기고, 수정 커밋과 연결한다.
````

- [ ] **Step 2: 검증 명령 실행**

Run:
```bash
grep -cE '^## (준비|실행 순서와 기대 결과|실패 기록)$' commands/understand-tests/H24-e2e/README.md
grep -cE '^\| [0-9]+ \|' commands/understand-tests/H24-e2e/README.md
```
Expected: `3` / `10`

- [ ] **Step 3: Commit**

```bash
git add commands/understand-tests/H24-e2e/README.md
git commit -m "test(understand): H24 E2E 수동 시나리오 fixture"
```

### Task 9: 정적 회귀 일괄 검증 (코드 변경 없음)

**Files:**
- Test: CLAUDE.md 결합 메모의 회귀 catch grep 6종 일괄 실행

**Model**: haiku

**검증**: Task 7 에서 박은 회귀 grep 6종이 전부 기대값으로 통과한다 — 5 / 0 / >=2 / 4 / 2 / 0.

- [ ] **Step 1: 회귀 grep 일괄 실행**

Run:
```bash
grep -lF "disable-model-invocation: true" commands/understand.md commands/understand-chat.md commands/understand-diff.md commands/understand-explain.md commands/understand-onboard.md | wc -l
ls -d skills/understand* 2>/dev/null | wc -l
grep -c "v2.9.4" commands/understand.md
grep -lF "GRAPH_COMMIT_RAW" commands/understand-chat.md commands/understand-diff.md commands/understand-explain.md commands/understand-onboard.md | wc -l
grep -rlF "releases/download/v2.9.4/understand-anything-viewer.tgz" commands/ | wc -l
grep -rln "understand-anything" hooks/ | wc -l
```
Expected: `5` / `0` / `2` 이상 / `4` / `2` / `0`

- [ ] **Step 2: 결과를 변경이력 [검증] entry 로 기록** (git-fast 모드에서는 end-of-run 일괄 entry 에 포함)

## 2. 위험 코드 지점

- `commands/understand.md` §0-2 (clone) — breaking: 원저장소·릴리즈 소실 시 부트스트랩 실패 (mitigation: 태그 v2.9.4 고정 + 실패 시 원인 안내 후 즉시 중단)
- `commands/understand.md` §0-2 (버전 검사) — breaking: 기존 다른 버전 사본과 절차·스키마 불일치 (mitigation: 재설치 게이트, 거부 시 중단 — 불일치 사본으로 진행 금지)
- `commands/understand.md` §0-1 — side-effect: 도구 미충족 머신에서 반쯤 진행 후 실패 (mitigation: 4종 선행 검사 + 즉시 중단)
- `commands/understand.md` §2 표 하단 문장 — race: 배치 파일명 규약 변형 시 병합에서 조용히 유실 (mitigation: "절대 변형 금지" 명문 + 원본 절차 무수정)
- `commands/understand.md` §2 O-3 — side-effect: 워크트리 실행 시 산출물 위치 혼동 (mitigation: 기본 메인 루트 + `--here` 명시 옵트인, fixture #10 으로 확인)
- `README.md` 유틸리티 표 아래 문단 — side-effect: 토큰 비용·동시 설치 미인지 (mitigation: 주의 문단 + 실행 전 규모 보고 유지)
- `commands/understand.md` §3-2 — side-effect: 대상 프로젝트의 작업 파일(`.ua/intermediate/`, `.ua/tmp/`, `.ua/.trash-*/`)과 변경 분석 임시 산출물(`.ua/diff-overlay.json`)을 사용자가 의도치 않게 커밋 (mitigation: 종료 보고에 gitignore 권장 네 줄 안내)
- `commands/understand-{chat,diff,explain,onboard}.md` 공통 블록 — breaking: 4곳 중 한 곳만 수정 시 최신성 판정 불일치 (mitigation: CLAUDE.md 동기 룰 + 회귀 grep 4파일 검사)

## 3. 롤백 전략

- Code: task 별 commit 이라 `git revert <SHA>` 로 파일 단위 되돌림 가능. 전체 철회는 5 커맨드 + README + CLAUDE.md + fixture 커밋 revert
- 사용자 머신: 엔진 사본은 `~/.understand-anything-plugin` 삭제로 제거 (저장소 밖 산출물, 안내만 — 자동 삭제 없음)
- 대상 프로젝트: `.ua/` 디렉토리 삭제로 원상복구
- Config/DB/feature flag: 해당 없음

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-17 20:52] [구현계획서-수정]
- **id**: CH-20260817-004
- **이유**: 신규 구현계획서 작성 (Task 1~9). 무맥락 검증 지적 9건을 반영한 상태로 확정 — 엔진 사본의 중첩 구조 명시, Bash 호출마다 셸이 새로 뜨는 점을 고려한 경로 표기, `--here` 적용 방식 구체화, 코드 펜스 중첩 오류 수정, 작업 파일 gitignore 범위 보강, Task 6·7·8 의 검증 기준과 실제 검사 명령 일치
- **무엇이**: understand-anything-command-implementation-plan.md 전체 (§1 Task 1~9, §2 위험 코드 지점 8건, §3 롤백 전략)
- **영향범위**: understand-anything-command-tech-design.md — D-3 근거 수정이 같은 검증에서 함께 발생 (CH-20260817-003). 코드 변경은 아직 없음 (실행 단계에서 발생)
- **연관 항목**: CH-20260817-002, CH-20260817-003

### [2026-08-17 20:59] [코드-수정] (batch: tasks 1..8)
- **id**: CH-20260817-005
- **이유**: Understand-Anything v2.9.4 의 그래프 생성 + 조회 4종을 js-super 명시 호출 전용 커맨드로 이식 완료. 엔진은 저장소에 넣지 않고 최초 실행 시 버전 고정으로 내려받는 구조
- **무엇이**: commands/understand.md, commands/understand-chat.md, commands/understand-diff.md, commands/understand-explain.md, commands/understand-onboard.md, README.md, CLAUDE.md, commands/understand-tests/H24-e2e/README.md
- **영향범위**: 신규 커맨드 5종이라 기존 호출자 0. README 유틸리티 표와 CLAUDE.md 결합 메모가 늘어남. skills / scripts / hooks / agents / 6 manifest 변경 0. eval 러너가 CLAUDE.md 에서 새 회귀 규칙 6건을 수집함(실측 확인)
- **위험 카테고리**: breaking, side-effect, race
- **task별 세부 (8건)**:
  - Task 1: `commands/understand.md` (신규 113줄) — 도구 검사 4종 + 사본 확보 + 원본 절차 참조 + 덮어쓰기 5조항 + 종료 안내 (`breaking`: 원저장소·버전 의존 / `side-effect`: 도구 미충족·작업 파일 커밋 / `race`: 배치 파일명 규약 명문) — commits: `b4660df`
  - Task 2: `commands/understand-chat.md` (신규) — 그래프 질의응답 (`none`) — commits: `3c3f827`
  - Task 3: `commands/understand-diff.md` (신규) — 변경 영향 분석, 원본의 대시보드 자동 호출을 viewer 안내로 교체 (`none`) — commits: `fb3a19c`
  - Task 4: `commands/understand-explain.md` (신규) — 파일·함수 딥다이브 (`none`) — commits: `473df43`
  - Task 5: `commands/understand-onboard.md` (신규) — 온보딩 가이드 생성 (`none`) — commits: `3354e7b`
  - Task 6: `README.md:533-539` — 유틸리티 표 5행 + 요구·비용·동시 설치 주의 문단 (`side-effect`: 비용 미인지 완화) — commits: `c16e9b0`
  - Task 7: `CLAUDE.md:1776-1836` — 결합 메모 + 회귀 catch grep 6종 (`breaking`: 4파일 공통 블록 동기 룰) — commits: `495806a`
  - Task 8: `commands/understand-tests/H24-e2e/README.md` (신규) — 수동 E2E 시나리오 10단계 — commits: `5d48d57`
- **연관 commits**: `b4660df`, `3c3f827`, `fb3a19c`, `473df43`, `3354e7b`, `c16e9b0`, `495806a`, `5d48d57`
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회

### [2026-08-17 20:59] [검증] (task: Task 9 — 회귀 검사 일괄 실행)
- **id**: CH-20260817-006
- **이유**: 릴리즈 전 정적 회귀 규칙 6종이 실제 저장소 상태에서 통과하는지 확인
- **무엇이**: 5 커맨드 명시 호출 전용 플래그 / 커맨드↔스킬 이름 충돌 / 버전 고정 문자열 / 조회 4종 공통 블록 동기 / viewer URL 등장 파일 일치 / 훅 미도입
- **결과**: PASS — 실측 5 / 0 / 5 / 4 / 2 / 0 (기대 5 / 0 / 2 이상 / 4 / 2 / 0). 커맨드↔스킬 충돌 전수 검사도 출력 없음. Task 6 실행 중 계획서의 검증 정규식 오류 1건(백틱 앞 여분 문자)을 발견해 계획서를 교정함
- **연관 commit**: 위 batch entry 의 8개 커밋
- **연관 항목**: CH-20260817-005
