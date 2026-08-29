# Reorder/Resolve Subagent Prompt Template (v2.0.0+)

Used when implementer reports `Status: BLOCKED — 원본 mismatch`. Sonnet only.
The reorder subagent reconciles plan changes with user-side edits when
Edit "old_string not found" because the file diverged from plan's `**원본**`
block.

```
Task tool (general-purpose):
  model: "sonnet"   # v2.0.0+ FIXED — reorder needs free judgment + Korean prose handling. NOT haiku.
  description: "Reorder Task N: reconcile plan vs user edit"
  prompt: |
    You are reconciling Task N: [task name]

    The implementer (byte-copy mode) reported BLOCKED because
    Edit's old_string did not match the actual file. Your job is to
    figure out whether the file diverged due to:
    
    (a) User manual edit before plan execution — preserve user intent + apply plan's net change
    (b) Genuine plan-vs-file conflict — escalate to user via Status: NEEDS_USER

    DO NOT silently overwrite user edits. When in doubt, escalate.

    ## Inputs

    - Task description + `**원본**` block + `**수정 후**` block (from plan)
    - Current file state (read with Read tool — DO NOT trust the implementer's report)
    - BLOCKED reason from implementer

    ## Task Description

    [FULL TEXT of task from plan]

    ## Plan blocks

    **원본** (from plan):
    [original block byte-equal to plan]

    **수정 후** (from plan):
    [target block byte-equal to plan]

    ## Implementer report

    [BLOCKED reason verbatim]

    ## Your Job

    1. Read the actual file with Read tool. Identify what differs from `**원본**`.
    2. Categorize:
       (a) Compatible — user added an unrelated line, plan's net change still applies cleanly
       (b) Conflict — user edited the same lines plan wants to change
    3. (a) → apply both: write the file so user's change AND plan's net change are present.
            Use Edit with the actual current content as old_string + reconciled content as new_string.
            Verify by re-reading after.
    4. (b) → escalate. Do NOT pick a side.

    ## Status formats

    Status: DONE
      Reconciled successfully. Both user edit and plan change present.
      Files changed: <list>
      
    Status: NEEDS_USER
      Reason: <one-line description of conflict>
      Conflict:
        plan intent: <what plan wanted to change>
        user edit:   <what user changed>
      Files: <file:line>
      Suggested questions:
        - <question 1 the main agent could ask the user>
        - <question 2>

    ## Constraints

    - DO NOT git commit (main agent handles wave-end commits)
    - DO NOT touch the 변경이력 footer
    - DO NOT add RISK comments (main does this post-hoc)
    - DO NOT escalate to user directly (main handles AskUserQuestion)
    - DO NOT silently apply only the plan change if user edit is incompatible —
      that's exactly the silent overwrite v2.0.0 byte-copy is designed to prevent

    ## When to NEEDS_USER

    Default to NEEDS_USER if:
    - User edit and plan change touch overlapping lines
    - User intent unclear from the diff alone
    - Reconciliation requires architectural judgment (e.g., user changed a
      type signature; plan adds a feature that also touches that signature)

    Reconciliation is meant for purely additive cases. Anything else escalates.
```
