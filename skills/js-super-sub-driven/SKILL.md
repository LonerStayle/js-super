---
name: js-super-sub-driven
description: 서브에이전트 실행 경로 (1인 개발 + 사전 검증 게이트 가정). v1.1.14+ wave-parallel — 메인이 plan 분석으로 DAG 추론 → wave 단위 pair-parallel dispatch (implementer + spec reviewer). 메인이 wave 끝에서 직렬 commit + post-hoc 충돌 검출. quality reviewer는 사전 verifying-spec + TDD + RISK + 변경이력으로 분산 흡수.
---

# js-super-sub-driven (v1.1.14 wave-parallel)

js-super 워크플로에 최적화된 서브에이전트 경로. 1인 개발 + 사전 검증 게이트(verifying-spec) 가정. v1.1.14+ 부터 plan task 들이 file-disjoint + dependency-free 조건을 만족하는 그룹은 wave 단위 병렬 dispatch.

**Announce at start:** "I'm using the js-super-sub-driven skill to execute this plan with wave-parallel subagents + main-agent governance."

## Why this shape

- **Spec reviewer 유지** — fresh-context 서브에이전트가 implementer 보고서 없이 코드를 line-by-line 대조하는 시각은 메인이 못 가짐. 메인의 `verifying-spec`은 plan ↔ 상위 산출물 정합성, 이 서브에이전트는 plan task ↔ 실제 코드 정합성 — 결이 다름.
- **별도 quality reviewer 없음** — `/design-tech` / `/write-plan` 끝의 `verifying-spec`(코드 임팩트 분석) + bite-sized TDD(테스트 통과 baseline) + `risk-annotation` 3-checklist + 변경이력으로 대체. 1인 개발이 `finishing-a-development-branch`에서 최종 검수.
- **메인 후처리 (RISK + 변경이력 + atomic commit)** — wave 끝마다 task 순서대로 자동.
- **Wave-parallel (v1.1.14+)** — task 간 file-disjoint + deps-free 보장 시 동시 dispatch. final code reviewer 없는 js-super 의 cross-task 의존이 약한 점을 활용.

## When to Use

```dot
digraph when_to_use {
    "implementation-plan.md 있나?" [shape=diamond];
    "task가 대체로 독립적?" [shape=diamond];
    "git repo 있나?\n(commit_policy: per-task)" [shape=diamond];
    "메인 컨텍스트 보존 우선?" [shape=diamond];
    "this skill" [shape=box];
    "executing-plans" [shape=box];
    "executing-plans (memory-fallback)" [shape=box];
    "manual or brainstorm first" [shape=box];

    "implementation-plan.md 있나?" -> "task가 대체로 독립적?" [label="yes"];
    "implementation-plan.md 있나?" -> "manual or brainstorm first" [label="no"];
    "task가 대체로 독립적?" -> "git repo 있나?\n(commit_policy: per-task)" [label="yes"];
    "task가 대체로 독립적?" -> "executing-plans" [label="no - 결합도 높음"];
    "git repo 있나?\n(commit_policy: per-task)" -> "메인 컨텍스트 보존 우선?" [label="yes"];
    "git repo 있나?\n(commit_policy: per-task)" -> "executing-plans (memory-fallback)" [label="no"];
    "메인 컨텍스트 보존 우선?" -> "this skill" [label="yes (default)"];
    "메인 컨텍스트 보존 우선?" -> "executing-plans" [label="no - 인라인이 빠름"];
}
```

기본은 `executing-plans` (인라인). **메인 컨텍스트가 한계에 다다를 큰 피처(13+ task) + 진짜 독립적 task** 일 때 이 스킬이 빛을 발함.

## Mode Compatibility

이 스킬은 **항상 git-fast** 가정. 이유:
- 메인이 wave 끝에서 commit 하므로 git 필수 (v1.1.14+ implementer 가 commit 안 함)
- `commit_policy: single` / `none` 인 plan과는 호환 안 됨 → 이 경우 `executing-plans` (memory-fallback) 사용

`/execute-plan` 진입 시 mode-check (이미 `executing-plans`에 정의됨)에서 `commit_policy != per-task` 면 이 스킬은 후보에서 제외.

## Entry Guard (v1.1.15+ user-gate)

이 skill 호출 시 메인은 즉시 helper 검사:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.preflight import subagent_task_entry_check
result = subagent_task_entry_check(Path('<PLAN_PATH>'))
print(f'ok={result.ok} reason={result.reason} | {result.human_reason}')
sys.exit(0 if result.ok else 1)
" 2>&1
```

**exit code 분기 (v1.1.15 user-gate)**:

- **exit 0** → Plan Analysis 단계 진입.
- **exit 1** (semantic fail — plan 없음 또는 `commit_policy ≠ per-task`) → `human_reason` 노출 후 `AskUserQuestion` 게이트:
  - `"수정 후 재시도"` (사용자가 plan 작성 / commit_policy 변경 후 메인 재호출) / `"강제 진행 (위험)"` (단, 매우 위험 — plan 없으면 Wave Build 자체 불가, 메인이 한 번 더 안내) / `"스킵 (이번만)"` (subagent 모드 포기, executing-plans inline 으로 fallback 제안).
- **exit ≠ 0,1** (invocation 실패) → stderr 노출 + `AskUserQuestion` 게이트:
  - `"직접 디버깅"` / `"skill 단계 스킵"` (inline fallback).

이유: helper 가 (a) plan 존재, (b) `commit_policy: per-task` 두 조건 모두 검사 — 단일 호출. plan 없는 dispatch 또는 `single`/`none` mode plan 모두 deterministic 거부 + 사용자 확인.

## Plan Analysis & Wave Build (v1.1.14+, 1회)

Per-wave loop 보다 먼저 1회만 실행. 모든 task 완료까지 wave 구조는 immutable.

1. **Read plan tasks** — `<slug>-implementation-plan.md` 의 §1 단계별 작업 모든 task block. 같은 폴더에 `plan/tasks-*.md` 가 있으면 그 파일은 인덱스다 — DAG 분석에 필요한 헤더 필드 (`**Files:**` / `**Model**` / `**검증**` / `**상세**` 링크) 가 인덱스에 다 있으므로 **여기서는 인덱스만 읽는다**. 각 task 의 step 목록과 코드 블록은 wave dispatch 직전 (W-2 Stage 1) 에 그 task 의 `**상세**` 문서에서 읽어 프롬프트에 붙여넣는다. 보조 에이전트는 계획서 파일을 직접 열지 않으므로 프롬프트 3종은 분할 여부와 무관하게 그대로다.
2. **Parse files + deps** — 각 task block 의 `**Files:**` (Create/Modify/Test) 섹션 + step 본문에서 task ID 참조 추출 (예: "Task 1 의 helper 사용" → deps=[1]). `Test:` 경로도 files 집합에 포함 — wave file-disjoint 판정이 테스트 파일 충돌까지 커버한다 (v2.9+ 계획서에 테스트 코드 블록이 없어도 `Test:` 경로 줄을 유지하는 이유).
3. **Parse model hint** — task block 의 `**Model**:` 줄 파싱. DAG 복잡도 표시 + v2.9+ 조건부 dispatch 판정에 사용 (신규 테스트 작성 포함 task 는 이 값으로 dispatch, 최소 sonnet — Model Selection 참조). 없으면 DAG 표시상 `sonnet` (`scripts/dag_builder.py` 의 `Task.model` 기본값).
4. **Build waves** — `scripts/dag_builder.py:build_waves` 호출:

```bash
source .venv/bin/activate && python -c "
from scripts.dag_builder import Task, build_waves
tasks = [
    Task(id=1, name='Foo', files=['scripts/dag_builder.py'], deps=[], model='haiku'),
    Task(id=2, name='Bar', files=['scripts/dag_builder.py'], deps=[1], model='haiku'),
    # ...
]
waves = build_waves(tasks)
for w in waves:
    print(f'Wave {w.index}: tasks={[t.id for t in w.tasks]}')
"
```

5. **사용자 출력 (1회)**:

```
📊 DAG 분석: <N> tasks → <W> waves
  Wave 1: tasks <list> (모델: <list>)
  Wave 2: tasks <list>
  ...
```

## Model Selection

**Implementer dispatch 모델은 조건부 (v2.9+)** — 순수 byte-copy task (`**원본**`/`**수정 후**` 블록만, 신규 테스트 작성 없음) 는 **`haiku` 고정** (v2.0.0 byte-copy — 기계적 복사라 추론 모델 불필요). **신규 테스트 작성 포함 task** (`**검증**:` 필드 + `Files:` 의 `Test:` 경로 존재 + 테스트 코드 블록 없음) 는 plan 의 `**Model**:` 값 (**최소 sonnet floor**) 으로 dispatch — 자연어 검증 설명만으로 테스트 코드를 작성해야 하기 때문. 하위 호환: task 에 테스트 코드 블록이 있으면 (v2.8 이전 형식) 기존 룰 (전체 byte-copy + haiku) 우선. 구현 코드의 STRICT BYTE-COPY 는 dispatch 모델과 무관하게 적용. task 가 byte-copy 로 감당 안 되면 implementer 가 `BLOCKED` 보고 → 메인이 reorder(sonnet) dispatch (아래 W-2 Stage 1/2/3 참조).

**Spec reviewer 서브에이전트** 는 항상 **sonnet** 고정 (D11). implementer 모델과 무관.

참고 — plan 의 `**Model**:` 값이 나타내는 task 복잡도 (신규 테스트 포함 task 는 dispatch 모델로도 사용, v2.9+):

| Task 신호 | 복잡도 힌트 |
|---|---|
| 1-2 파일 + 명확한 spec, 기계적 구현 | **haiku** |
| 다중 파일 통합 / 패턴 매칭 / 디버깅 | **sonnet** |
| 설계 판단 / 광범위 코드베이스 이해 / 리뷰 | **opus** |

dispatch 예시:
```
Task tool (general-purpose):
  model: "haiku"   # 순수 byte-copy task 는 haiku / 신규 테스트 포함 task 는 plan **Model**: 값 (최소 sonnet) — v2.9+
  description: "Implement Task N: ..."
  prompt: <implementer-prompt 템플릿>
```

## Checklist

- [ ] Entry Guard (preflight + user-gate)
- [ ] Plan Analysis & Wave Build (DAG 추론, 1회)
- [ ] Wave 별 Sequence (W-1 시작 안내 → W-2 pair-parallel dispatch → W-3 재dispatch → W-4 finalization → W-5 완료 요약 → W-6 failure isolation)
- [ ] End-of-Run Consolidator (§1~§5)
- [ ] finishing-a-development-branch invoke

## Per-wave Sequence (v1.1.14+)

For each wave (in order 1..N):

### W-1. Wave 시작 안내 (사용자 출력 1회)

```
Wave i/N 시작: task <list> 병렬 실행…
```

### W-2. Pair-parallel dispatch

For each task in this wave (in plan order), 두 dispatch 를 한 메시지에 묶어 **병렬** 실행 (Agent tool multiple calls in single message):
- Implementer (`./implementer-prompt.md`, 순수 byte-copy task 는 `model: "haiku"` / 신규 테스트 포함 task 는 plan `**Model**:` 값 (최소 sonnet) — v2.9+)
- Spec reviewer 는 implementer 가 `Status: DONE` + manifest 작성 후 dispatch (`./spec-reviewer-prompt.md`, `model: "sonnet"` 고정)

페어 병렬 = wave 안 task **간** 병렬 (task A 와 task B 동시), task **안** 의 impl→review 는 직렬.

### W-2 (v2.0.0+) Stage 1/2/3 분기

For each task within wave, dispatch sequence is now:

1. **Stage 1 — Implementer** (조건부 모델, byte-copy + 테스트 자체 작성)
   Dispatch via `./implementer-prompt.md` (순수 byte-copy=haiku / 신규 테스트 포함=plan `**Model**:` 값, 최소 sonnet — v2.9+).
   - Status: DONE → proceed to Stage 3 (Spec Reviewer)
   - Status: BLOCKED — 원본 mismatch → proceed to Stage 2 (Reorder)
   - Status: BLOCKED — other → wave finalization failure isolation (D7), no Stage 2

2. **Stage 2 — Reorder/Resolve** (sonnet, conditional)
   Dispatch via `./reorder-prompt.md` (model="sonnet").
   - Status: DONE → proceed to Stage 3 (Spec Reviewer)
   - Status: NEEDS_USER → main agent invokes AskUserQuestion with reorder's
     Suggested questions. User answers → main reconciles directly via Edit
     → proceed to Stage 3.

3. **Stage 3 — Spec Reviewer** (sonnet, unchanged)
   Dispatch via `./spec-reviewer-prompt.md`. Same as v1.1.x.

Stage 1 BLOCKED → Stage 2 dispatch is automatic (no user gate). Stage 2
NEEDS_USER → main agent gate. Plan's `**Model**:` value drives Stage 1 dispatch
ONLY for tasks that author new tests (v2.9+, min sonnet floor); pure byte-copy
tasks stay haiku. Spec reviewer remains sonnet (D11/D-T2 PRD).

### W-3. Spec reviewer ❌ 시 implementer 재dispatch

기존 패턴 그대로. impl 재호출 → reviewer 재검 (working tree 만 갱신, commit 아직 X).

### W-4. Wave finalization (직렬, plan order)

모든 task 의 spec-reviewer ✅ 후 메인이 plan 순서대로:

```bash
# (a) post-hoc conflict detection
source .venv/bin/activate && python -c "
from pathlib import Path
from scripts.dag_builder import detect_conflicts
from scripts.changelog_buffer import read_manifest
manifests_dir = Path('.js-super/changelog-buffer/<slug>')
manifests = {}
for task_id in <wave_task_ids>:
    m = read_manifest(manifests_dir / f'task-{task_id:02d}.md')
    manifests[task_id] = [fc['path'] for fc in m['files_changed']]
conflicts = detect_conflicts(manifests)
print(conflicts)
"
```

- 비어있으면 정상 → step (b) 진행
- 충돌 발견 시: plan order 늦은 task 의 working tree 변경 stash → 다음 wave 로 이동:

```bash
git checkout -- <late_task_files>
# manifest 도 다음 wave 로 이동 (rename task-NN.md → task-NN.md.deferred)
```

```bash
# (b) For each task in plan order:
git diff HEAD -- <task.files>           # 3-checklist 입력
# 메인이 위험 평가 → RISK 주석 Edit
git add <task.files>
git commit -m "task <N>: <task.name>"
# (RISK 트리거 있으면 follow-up commit 별도)
```

### W-5. Wave 완료 요약 (사용자 출력 1회)

```
Wave i/N 완료: <pass list>✓ <fail list>✗ (후행 차단: <list 또는 없음>)
```

### W-6. Failure isolation (D7)

- spec-reviewer ❌ 가 retry loop 종료 후에도 ❌ → task 격리
- 격리 task 의 working tree 변경 `git checkout --` 으로 폐기, manifest 도 삭제
- DAG 에서 격리 task 의 후행 (deps 에 격리 task 포함) 모두 blocked 상태로 마킹
- 다음 wave 진행 시 blocked task 는 dispatch 대상에서 제외

## End-of-Run Consolidator (v1.1.7 그대로)

모든 wave 완료 후 1회 발화. per-wave manifest 들을 누적했다가 한꺼번에 정리.

### §1. 누적 buffer 디렉토리 종합

```bash
# Validate every task has a manifest
source .venv/bin/activate && python -c "
from pathlib import Path
from scripts.changelog_buffer import list_buffer_files
files = list_buffer_files(Path('.js-super/changelog-buffer/<slug>'))
print(f'Found {len(files)} manifests; expected {len(plan_tasks)}')
"
```

If counts mismatch → STOP, ask user (some task likely BLOCKED or interrupted).

### §2. "구현 요약" 메시지를 메인이 사용자에게 출력

```
✅ <slug> 모든 task 완료. 구현 요약:
- 계획서 N tasks → 실제 본 commit M개 (follow-up M' 포함)
- RISK 트리거: side-effect=X / breaking=Y / race=Z (총 N건)
- 누락: <list 또는 "없음">
- 초과: <list 또는 "없음">  ← plan에 없던 follow-up commit 의 변경 범위
- 코드 변경 0건 task: <task 번호 list>  ← [검증] entry로 별도 기록
- Blocked tasks: <list 또는 "없음">  ← failure isolation 결과
다음 단계: PR 작성 / finishing-a-development-branch
```

이 메시지가 plan ↔ 실제 코드 갭을 한 번에 노출 — 다음 단계(PR / merge) 진입의 자연스러운 게이트.

### §3. footer 1회 일괄 갱신

```bash
# Generate consolidated [코드-수정] (batch: tasks N..M) entry
source .venv/bin/activate && python -c "
from pathlib import Path
from scripts.changelog_buffer import consolidate_to_entry
print(consolidate_to_entry(
    manifests_dir=Path('.js-super/changelog-buffer/<slug>'),
    ch_id='<from change_id helper>',
    timestamp='<now>',
))
" >> .tmp-batch-entry.md
```

- Read `<slug>-implementation-plan.md` (1회)
- Edit `<slug>-implementation-plan.md` (`.tmp-batch-entry.md` 내용을 footer 끝에 append)
- 코드 변경 0건 task가 있으면 별도 `[검증]` entry도 함께 append (별도 CH-id)
- `rm .tmp-batch-entry.md`

### §4. 단일 log commit + buffer cleanup

```bash
git add <slug>-implementation-plan.md
git commit -m "[log] all tasks: <one-line summary>"
rm -rf .js-super/changelog-buffer/<slug>
```

### §5. finishing-a-development-branch invoke

- 슬림 finishing skill (v1.1.14+) — 테스트 자동 검증 + 종료 메시지. AskUserQuestion 게이트 X.

## Stale Buffer Detection (다음 세션)

세션 시작 시 (이 스킬 호출 직후, Entry Guard 직전) `.js-super/changelog-buffer/<slug>/` 잔존 검사:

```bash
source .venv/bin/activate && python -c "
from pathlib import Path
from scripts.changelog_buffer import detect_stale_buffer
stale = detect_stale_buffer(Path('.js-super/changelog-buffer'), '<slug>')
print(stale or 'no stale buffer')
"
```

발견되면 사용자에게 안내:
> "이전 세션의 미정리 buffer 발견: `.js-super/changelog-buffer/<slug>/task-{N..M}.md`. 복구해서 consolidator 1회만 실행할까요? — yes / no"

yes → End-of-Run Consolidator §1~§4 만 실행 (이전 task 본 commit은 이미 git 에 있음 → 새 task 진입 안 함).
no → 사용자가 직접 정리 또는 삭제.

## Commit History 모양 (예시, wave 모델)

```
* [log] all tasks: foo Tasks 1-5 완료
* [risk-annotate] task 4: ...        ← (Wave finalization 의 RISK follow-up)
* task 5: <wave-end commit by main>
* task 4: <wave-end commit by main>
* task 3: <wave-end commit by main>   ← Wave 2 finalization
* task 2: <wave-end commit by main>
* task 1: <wave-end commit by main>   ← Wave 1 finalization
```

→ task당 commit 1~2개 (wave-end main commit + RISK follow-up). v1.1.13 의 implementer multi-commit 패턴 사라짐. PR 단계에서 squash 권장. **history rewrite 안 함** (`amend` 사용 금지 — 안전).

## Example Workflow (Few-Shot, v1.1.14 wave 모드)

```
You: I'm using js-super-sub-driven to execute this plan.

[Entry guard: foo-implementation-plan.md exists ✅, commit_policy=per-task ✅]
[Read plan: 5 tasks. Parse Files/deps/Model.]
[Build waves: 3 waves (W1=[1,2], W2=[3,4], W3=[5])]
[User output: 📊 DAG 분석: 5 tasks → 3 waves]

──────────────────────────────────────
Wave 1/3 시작: task 1, 2 병렬 실행…
──────────────────────────────────────

[Single message with 2 Agent tool calls in parallel:
  - Implementer task 1 (model: haiku)
  - Implementer task 2 (model: haiku)]   # 두 task 모두 순수 byte-copy → haiku (신규 테스트 포함 task 면 plan **Model**: 값 — v2.9+)

[Both return: Status DONE + manifest written to buffer]

[Single message with 2 Agent tool calls:
  - Spec reviewer task 1 (model: sonnet)
  - Spec reviewer task 2 (model: sonnet)]

[Both return: ✅ Spec compliant]

[Wave finalization, plan order]:
  - detect_conflicts(manifests) → []  (no conflict)
  - task 1: git diff HEAD → 3-checklist → no RISK → git add + commit "task 1"
  - task 2: git diff HEAD → 3-checklist → side-effect trigger → Edit RISK comment → git add + commit "task 2" + follow-up "[risk-annotate] task 2"

[Wave 1/3 완료: 1✓ 2✓ (2/2 통과)]

──────────────────────────────────────
Wave 2/3 시작: task 3, 4 병렬 실행…
──────────────────────────────────────

[Pair-parallel dispatch...]

[Spec reviewer task 4 returns ❌: missing AC-3]
[Re-dispatch implementer task 4 with reviewer findings]
[Re-dispatch spec reviewer task 4 → ✅]

[Wave finalization → 2 commits in plan order]

[Wave 2/3 완료: 3✓ 4✓ (2/2 통과)]

──────────────────────────────────────
Wave 3/3 시작: task 5...
──────────────────────────────────────

[End-of-run consolidator (v1.1.7 그대로):]
  ✅ foo 모든 task 완료. 구현 요약: ...
  - footer 1회 batch entry append
  - [log] 단일 commit
  - buffer cleanup

[finishing-a-development-branch invoke (slim, v1.1.14)]
```

**핵심 패턴**:
1. dispatch 는 항상 **명시 모델 주입** (implementer=조건부: 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan **Model**: 값 (최소 sonnet), spec-reviewer=sonnet 고정) — 부모 모델 상속 회피
2. wave 단위 pair-parallel — task **간** 병렬, task **안** impl→review 직렬
3. wave finalization 단계에서 메인이 plan order 직렬 commit (implementer 는 commit X)
4. post-hoc conflict 검출 → 충돌 시 plan order 늦은 task rollback + 다음 wave 재배치
5. footer 는 **end-of-run 1회**, task / wave 별로 안 건드림
6. 인터럽트 발생 시 buffer 디렉토리 잔존 → 다음 세션에서 stale detection 으로 재개

## Cost Comparison

| | this skill (v1.1.14) | inline (executing-plans) |
|---|---|---|
| task당 서브에이전트 호출 | **2개** (impl + spec) + 루프 | 0개 |
| 메인 컨텍스트 누적 | 중간 (+ DAG + 충돌검사 + 변경이력) | 무거움 (모든 코드) |
| Wall-clock 시간 | wave 단위 병렬 → 큰 피처에서 단축 | 직렬 |
| 거버넌스 (RISK / 변경이력) | ✅ | ✅ |

## Anti-Patterns

| Wrong | Right |
|---|---|
| Quality reviewer 흉내 (메인이 사후 quality 리뷰 추가) | 빠진 이유 있음. TDD + RISK + finishing-a-development-branch 가 대체. |
| 메인 후처리 스킵 (시간 절약 목적) | RISK / 변경이력이 누락되면 인라인과 격차 발생. 후처리는 HARD-GATE. |
| Implementer 가 commit 하도록 두기 (v1.1.13 패턴 그대로) | v1.1.14+ 메인이 wave 끝에서 commit. implementer-prompt 에 명시적 금지. |
| wave 분할 안 하고 task 그대로 직렬 dispatch | wave = 1 인 plan 만 자연스럽게 직렬. 다중 wave plan 에 직렬 강행은 D3 위배. |
| 같은 wave task 들 commit 순서 race 방치 | wave 끝 plan order 직렬 commit 강제. |
| post-hoc conflict 검출 skip | DAG 추론 오류 안전망. 매 wave finalization 첫 단계. |
| `commit_policy: single`/`none` plan 에 이 스킬 강행 | git 필수 + commit 자유 가정. 호환 안 됨. STOP. |
| RISK 주석을 implementer 프롬프트에 넣어서 시키기 | 옵션 A 의 함정 (fresh-context 일관성 약함). 메인이 한다는 게 이 스킬의 본질. |
| amend 로 history rewrite | follow-up commit 사용 (안전). amend 는 push 된 브랜치 깨뜨림. |
| Implementer 보고서 보고 spec reviewer 디스패치 안 함 | spec reviewer 는 fresh-context 로 코드 직접 본다는 게 가치. 스킵하면 빠진 이유가 사라짐. |

## Red Flags

| Thought | Reality |
|---|---|
| "spec reviewer 도 빼자, 사전 게이트가 있잖아" | 사전 게이트는 plan ↔ 상위 정합성, spec reviewer 는 plan task ↔ 코드 정합성. 다른 시각. |
| "RISK 주석 follow-up commit 도 끝에 모아 하자" | 아니. RISK 주석은 wave finalization 즉시 (코드 인접 commit). batch 대상은 변경이력 footer 갱신뿐. |
| "RISK 트리거 잡으면 implementer 한테 재시켜야 하나" | 아니. 메인이 직접 Edit. implementer 재디스패치는 비용↑. |
| "wave 분할 X 한 plan 도 그냥 직렬로 가자" | wave = 1 이면 자연스러운 직렬. 다중 wave 가능한데 강제 직렬은 가치 손실. |

## Acceptance

A wave is complete only when ALL hold:
1. 모든 task 의 implementer Status: DONE + spec reviewer ✅
2. detect_conflicts(wave manifests) == [] 이거나 충돌 task 가 deferred 처리됨
3. plan order 직렬 commit 완료 (RISK follow-up 포함)
4. 사용자에게 wave 완료 요약 출력 (✓/✗ + blocked tasks)

A task within a wave is complete only when ALL hold:
1. Implementer Status: DONE + buffer manifest written (`.js-super/changelog-buffer/<slug>/task-NN.md`)
2. Spec reviewer ✅ (재리뷰 후라도 OK)
3. Wave finalization 의 메인 후처리 완료 (3-checklist + RISK 주석 + plan-order commit)

The whole run is complete only when End-of-Run Consolidator emits the 구현 요약 message, appends consolidated entries, runs `[log] all tasks` commit, and removes the buffer directory.

## Related Skills

- `executing-plans` — 인라인 대안 (메인 컨텍스트 한계 안 갈 때 더 빠름)
- `risk-annotation` — Wave finalization §W-4 (b) 에서 사용
- `change-history` — End-of-Run Consolidator §3 에서 사용
- `finishing-a-development-branch` — 모든 task 완료 후 호출 (slim, v1.1.14+)
- `verifying-spec` — `/design-tech`, `/write-plan` 단계에서 사전 게이트로 이미 수행됨 (이 스킬은 그 결과를 신뢰)

## Critical / Non-critical 판정 룰 (v2.3.5+)

subagent execute 흐름의 핵심 UX 룰. 사용자가 subagent 모드를 선택한 시점부터 메인은 진행 위임으로 간주하고, **critical 케이스만 재질문** 한다.

### 룰 1: Critical 케이스 — 사용자 재질문 mandatory (AskUserQuestion 강제)

| 케이스 | 이유 |
|---|---|
| 사용자가 선택한 모드 자체를 변경 (subagent → inline 권유 등) | 약속 위반. 명시 동의 필수. |
| plan 의 task 범위 확장 (계획 안 된 파일 / 함수 손대야 함) | scope creep — 사용자 의도 모호 |
| 파괴적 작업 (rm -rf / git reset --hard / force-push / 데이터 손실 위험) | 비가역 |
| plan 안 task 간 충돌 발견 (task A 수정본이 task B 원본과 불일치) | byte-copy 룰 위반, plan 재작성 필요 |
| BLOCKED 보고 후 reorder dispatch 도 자동 복구 실패 (W-2 분기) | 사용자 직접 개입 필요 |
| 외부 서비스 호출 (push / PR 생성 / 외부 API 트리거) | blast radius 커짐 |
| 사용자가 명시 약속 X 한 새 의존성 / 외부 도구 도입 | 약속 외 변경 |

### 룰 2: Non-critical 최적화 — 자율 진행 (게이트 X)

| 케이스 | 자율 결정 방향 |
|---|---|
| task 병렬 vs 순차 (wave 분할) | plan 의 dependencies 만족 시 wave-parallel default (v2.0.0+ Per-wave Sequence) |
| task 묶음 (same-file mechanical 3-AND 룰 만족 시) | 묶음 default (v2.0.1+) |
| task 안 보조 결정 (변수명 / format / order of imports) | plan 의 `**원본**` + `**수정본**` byte-copy 우선, 없으면 implementer 자율 |
| implementer dispatch model | v2.9+ 조건부 자동 판정 — 순수 byte-copy 는 haiku / 신규 테스트 포함은 plan `**Model**:` 값 (최소 sonnet). 게이트 없이 자동 |
| wave 완료 후 다음 wave 진입 타이밍 | 자동 진입 (게이트 X) |
| 중간 결과 보고 빈도 | 매 task X, 매 wave 단위 OR BLOCKED 시만 |

### 룰 3: 모드 선택 = 사용자 위임 신호

사용자가 subagent 모드를 선택한 시점부터, 그 모드에 내포된 진행 방식 (wave-parallel / 묶음 / 자동 진입) 은 묵시 동의로 간주한다. 사용자는 모드 선택 후 백그라운드 작업으로 이동할 수 있어야 한다. **모드 진행 중 추가 게이트는 룰 1 (critical) 에 해당하지 않으면 차단**.

### 룰 4: BLOCKED 자가 복구 우선 (W-2 분기 정합)

v2.0.0+ Per-wave Sequence W-2 분기와 정합:

- implementer BLOCKED 보고 → 메인이 **reorder dispatch 자동** (Stage 2 sonnet conditional). 사용자 개입 X.
- reorder 도 BLOCKED → 룰 1 의 마지막 케이스로 사용자 재질문 (AskUserQuestion fire)

→ silent overwrite 차단 + 자가 복구 보존. 안전성 핵심 (v2.0.0 byte-copy + reorder 3-stage).

## 사용자 질문 = AskUserQuestion 도구 (v2.3.5+)

룰 1 (critical 7 케이스) 재질문은 **반드시 `AskUserQuestion` 도구** 로 호출. prose 자연어 질문 금지.

- yes/no 도 `choices: [yes, no]` AskUserQuestion
- 다중 옵션은 `choices` enum
- 자유 응답 필요 시 dummy choice `[알겠음]` + question 본문에 "자유 응답" 명시
- 알람 시스템 (`repeat-alert.sh` 4-layer) 의 `Notification.elicitation_dialog` 매처 fire — 사용자 백그라운드 작업 시 OS 알람 catch

prose 질문 좁은 예외:

- 자유 텍스트 / 긴 응답 요구 (open question)
- 사용자 응답 직후 확인용 단순 ack (그래도 AskUserQuestion yes/no 권장)
- 질문 아닌 상태 보고 / 진행 알림

본 룰은 `using-superpowers` (매 세션 주입) 의 "User Decisions — AskUserQuestion First (v2.3.5+)" 전역 룰의 skill body 측 cross-reference.

## Anti-Patterns (v2.3.5)

| 안티 패턴 | 이유 |
|---|---|
| "wave 3 부터 병렬로 진행해도 될까요?" 류 게이트 | 룰 2 위반. plan dependencies 만족 시 자율 wave-parallel. |
| 매 wave 완료 후 "다음 wave 진입할까요?" 게이트 | 룰 3 위반. 모드 선택 = 진행 위임. |
| "같은 파일이라 묶을까요?" 게이트 | 룰 2 위반. 3-AND 룰 (v2.0.1+) 으로 자동 판정. |
| BLOCKED → 곧장 사용자 재질문 (reorder skip) | 룰 4 위반. reorder dispatch 자동 시도 우선. |
| implementer model 변경 시 게이트 | 룰 2 위반. v2.9+ 조건부 룰 (순수 byte-copy=haiku / 신규 테스트 포함=plan **Model**: 값) 로 자동 판정. |
| 변수명 / format / import 순서 게이트 | 룰 2 위반. plan byte-copy 우선, 없으면 implementer 자율. |
| 사용자 모드 선택 무시하고 subagent → inline 자동 전환 권유 | 룰 1 위반. 모드 변경은 명시 동의 필수. |
| 모든 mid-flight 결정을 "안전성" 명목으로 게이트 | 과보호. 룰 1 7 케이스 외엔 자율. |
| "이렇게 진행할까요?" 류 prose 자연어 질문 | AskUserQuestion 룰 위반. (yes/no) 도구 사용 강제. |
| "옵션 1: ... 옵션 2: ... 어느 쪽?" prose 멀티 옵션 | AskUserQuestion options 사용. |
| 마크다운 체크박스 / numbered list 로 사용자 선택 유도 (prose) | AskUserQuestion 사용. |
| critical 재질문을 prose 로 ("force-push 해도 될까요?") | critical 일수록 AskUserQuestion + 알람 fire 필수. |
| AskUserQuestion 호출 직후 prose 추가 질문 (이중 질문) | 한 turn 한 도구 호출 / 답변 흐름 보존. |
| "Y/N?" 한 글자 응답 유도 prose | AskUserQuestion (yes/no) 사용. |
| skill body boilerplate 만 따르고 ad-hoc 결정엔 prose | using-superpowers 전역 룰 위반. 전역 적용. |
| AskUserQuestion 호출이 overhead 라며 prose fallback | 일관성 ≫ 호출 비용. |
