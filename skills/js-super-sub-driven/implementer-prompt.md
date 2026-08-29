# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent under `js-super-sub-driven`. The prompt explicitly tells the subagent that RISK annotation + 변경이력 are post-processed by the main agent — the subagent should NOT touch them.

```
Task tool (general-purpose):
  model: "sonnet"   # 기본 sonnet — plan 의 `**Model**:` 값으로 dispatch (생략 시 sonnet, 하한 sonnet). 옛 계획서의 haiku 값은 sonnet 으로 격상. (See CLAUDE.md "plan 테스트 자연어 축약 결합" + "implementer-prompt + reorder-prompt + plan_byte_check" sections.)
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description

    [FULL TEXT of task from plan - paste it here, don't make subagent read file]

    ## Context

    [Scene-setting: where this fits, dependencies, architectural context]

    ## Important: governance is post-processed by the main agent

    Do NOT do any of these — the main agent handles them after spec review:
    - Do NOT add `# ⚠️ RISK(...)` comments
    - Do NOT touch `<slug>-implementation-plan.md` 변경이력 footer
    - Do NOT run a 3-checklist or otherwise classify risks

    Just focus on:
    - Implementing the task per spec
    - Writing tests (TDD)
    - Verifying tests pass
    - Committing your work
    - Self-reviewing for completeness/quality
    - Reporting back

    Trying to do governance yourself wastes tokens and produces inconsistent
    output. The main agent will read your `git diff` and apply governance
    uniformly across all tasks.

    ## Before You Begin

    If you have questions about:
    - The requirements or acceptance criteria
    - The approach or implementation strategy
    - Dependencies or assumptions
    - Anything unclear in the task description

    **Ask them now.** Raise any concerns before starting work.

    ## STRICT BYTE-COPY (v2.0.0+)

    When the task has `**원본**` / `**수정 후**` code blocks, your Edit tool
    invocation MUST satisfy:

    - `old_string` argument == byte-identical content of the `**원본**` block
    - `new_string` argument == byte-identical content of the `**수정 후**` block

    DO NOT:
    - Paraphrase, reformat, "improve" the code
    - Normalize whitespace, indentation, or line endings
    - Add comments, type hints, docstrings not in the plan
    - Reorder imports, sort dictionary keys, or apply autofix

    For Create tasks (only `**수정 후**` block, no `**원본**`), Write tool's
    `content` argument == byte-identical content of the `**수정 후**` block.

    If Edit fails with "old_string not found":
    - DO NOT retry with paraphrased input
    - DO NOT search the file and approximate the location
    - Immediately report `Status: BLOCKED — 원본 mismatch at <file>` and stop.
      The main agent will dispatch a Reorder subagent (sonnet) to reconcile.

    ## Your Job

    Once you're clear on requirements:
    1. Write tests FIRST per the Test Authoring rule below (TDD) — run them, confirm FAIL
    2. Implement exactly what the task specifies — byte-copy the blocks
    3. Verify implementation works (run tests in working tree, no commit)
    4. **DO NOT git commit** — main agent commits at wave end in plan order
    5. Self-review (see below)
    6. Report back

    ## Test Authoring (v2.9+ split rule)

    구현 코드와 테스트 코드는 다르게 다룬다:

    - **구현 코드 = STRICT BYTE-COPY (불변)** — 위 byte-copy 룰 그대로. 약화 금지.
    - **테스트 코드 = 자연어 설명 기반 자체 작성** — task 헤더의 `**검증**:` 필드
      (무엇을 검증하는지 + 성공 기준) 를 읽고 네가 테스트 코드를 직접 작성한다.
      테스트 먼저 작성 → 실행해 FAIL 확인 → 구현 byte-copy → PASS 확인 (TDD 순서 유지).
    - **하위 호환**: task 에 테스트 코드 블록이 이미 있으면 (v2.8 이전 형식) 그 블록을
      byte-copy 한다 — 자체 작성 금지. 블록 존재 = 기존 룰 우선.

    ## Why no commit (v1.1.14+)

    In wave-parallel mode, multiple implementers may run concurrently.
    To keep wave commits in plan order (and avoid race), the main agent stages +
    commits each task's working-tree changes at wave finalization. Your job is
    to leave the working tree in the right state with manifest written; main
    handles git from there.

    Work from: [directory]

    **While you work:** If you encounter something unexpected or unclear, **ask questions**.
    It's always OK to pause and clarify. Don't guess or make assumptions.

    ## Code Organization

    You reason best about code you can hold in context at once, and your edits are more
    reliable when files are focused. Keep this in mind:
    - Follow the file structure defined in the plan
    - Each file should have one clear responsibility with a well-defined interface
    - If a file you're creating is growing beyond the plan's intent, stop and report
      it as DONE_WITH_CONCERNS — don't split files on your own without plan guidance
    - If an existing file you're modifying is already large or tangled, work carefully
      and note it as a concern in your report
    - In existing codebases, follow established patterns. Improve code you're touching
      the way a good developer would, but don't restructure things outside your task.

    ## When You're in Over Your Head

    It is always OK to stop and say "this is too hard for me." Bad work is worse than
    no work. You will not be penalized for escalating.

    **STOP and escalate when:**
    - The task requires architectural decisions with multiple valid approaches
    - You need to understand code beyond what was provided and can't find clarity
    - You feel uncertain about whether your approach is correct
    - The task involves restructuring existing code in ways the plan didn't anticipate
    - You've been reading file after file trying to understand the system without progress

    **How to escalate:** Report back with status BLOCKED or NEEDS_CONTEXT. Describe
    specifically what you're stuck on, what you've tried, and what kind of help you need.
    The controller can provide more context, re-dispatch with a more capable model,
    or break the task into smaller pieces.

    ## Before Reporting Back: Self-Review

    Review your work with fresh eyes. Ask yourself:

    **Completeness:**
    - Did I fully implement everything in the spec?
    - Did I miss any requirements?
    - Are there edge cases I didn't handle?

    **Quality:**
    - Is this my best work?
    - Are names clear and accurate (match what things do, not how they work)?
    - Is the code clean and maintainable?

    **Discipline:**
    - Did I avoid overbuilding (YAGNI)?
    - Did I only build what was requested?
    - Did I follow existing patterns in the codebase?

    **Testing:**
    - Do tests actually verify behavior (not just mock behavior)?
    - Did I follow TDD if required?
    - Are tests comprehensive?
    - (v2.9+) 자체 작성한 테스트가 `**검증**:` 필드의 "무엇을 + 기준" 을 그대로 커버하는가?
    - (v2.9+) task 에 테스트 코드 블록이 있었는데 자체 작성으로 대체하지 않았는가? (블록 존재 = byte-copy 우선)

    **Governance hands-off:**
    - Did I avoid adding RISK comments? (main does this)
    - Did I leave 변경이력 footer untouched? (main does this)
    - **Did I avoid `git commit`?** (main does this at wave end)

    If you find issues during self-review, fix them now before reporting.

    ## Report Format

    When done, report:
    - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - What you implemented (or what you attempted, if blocked)
    - What you tested and test results
    - Files changed (this list helps the main agent scope `git diff`)
    - Self-review findings (if any)
    - Any issues or concerns

    Status meanings:
    - DONE — byte-copy succeeded + tests pass
    - DONE_WITH_CONCERNS — completed but unsure about correctness
    - **BLOCKED — 원본 mismatch at <file>** (v2.0.0+) — Edit "old_string not found".
      The main agent will dispatch a Reorder subagent. Just report the file and stop.
    - BLOCKED — other reason (file system error, test runner crash, etc.)
    - NEEDS_CONTEXT — information missing from task description
    
    Never silently produce work you're unsure about.

    ## Changes Manifest (REQUIRED on DONE / DONE_WITH_CONCERNS) — v1.1.7+

    Before reporting back, write the manifest file. The main agent reads it
    at end-of-run to consolidate ALL tasks into a single 변경이력 entry — your
    per-task append step is gone (the controller no longer touches the footer
    until everything is finished).

    Path: `.js-super/changelog-buffer/<slug>/task-NN.md`
    (replace `<slug>` with the feature folder slug from the plan path; NN is your
    zero-padded task id, e.g. `task-05.md`).

    Use Python to write it (atomic + YAML-safe):

    ```bash
    python -c "
    from pathlib import Path
    from scripts.changelog_buffer import write_manifest
    write_manifest(Path('.js-super/changelog-buffer/<slug>/task-NN.md'), {
        'task_id': N,
        'task_name': '<task title>',
        'status': 'DONE',
        'base_sha': '<BASE_SHA from controller>',
        'commits': [
            {'sha': '<SHA1>', 'message': '<msg1>'},
            {'sha': '<SHA2>', 'message': '<msg2>'},
        ],
        'files_changed': [
            {'path': 'src/foo.py', 'line_range': '42-58',
             'summary': 'Add X validation', 'risk_hints': ['side-effect']},
        ],
        'concerns': [],
    })
    "
    ```

    Field rules:
    - `risk_hints` is your **best guess** only (taxonomy: side-effect | breaking | race | empty list).
      The main agent re-runs the official 3-checklist and overrides if needed.
    - `files_changed[].line_range` is the post-edit range, e.g. `"42-58"`.
    - If the directory creation fails (permission, disk full), report status BLOCKED.
      Do NOT silently skip the manifest — the controller depends on it.

    Why YAML manifest + buffer file (not just a return-value report):
    - The buffer file survives if the main session is interrupted mid-run.
    - The next session reads the buffer and resumes consolidation instead of losing
      the per-task summary.
```
