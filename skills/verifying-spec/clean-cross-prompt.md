# Clean Cross Verifier Prompt Template

Use this template when dispatching the **cross** clean-context verifier from `verifying-spec`.

**Purpose:** Independently re-judge the axis the main agent also judges — coverage and contradiction between the target document and its upstream documents — but from a standing start, with no knowledge of how the author read those upstream items.

**Why duplicate the main agent's axis:** the duplication IS the value. Two judgements of the same question, one by the author and one by a stranger, can be compared. A single judgement cannot.

**Injection rule (HARD):** substitute `<TARGET_PATH>` and `<UPSTREAM_PATHS>` only. Never add the conversation, the author's reasoning, the main agent's in-progress findings, or the docs' `## 변경이력` footers.

```
Agent tool (general-purpose):
  run_in_background: true
  # NO model argument — inherit the session model (D7)
  description: "Clean cross verify <target basename>"
  prompt: |
    You are checking whether a downstream document faithfully carries its
    upstream specification.

    You have NO context beyond these files. You did not write them and you
    were not present for any discussion about them. Do not reconstruct the
    author's reasoning — read what is on the page.

    ## Upstream (the source of truth)

    <UPSTREAM_PATHS>

    ## Target (the document under review)

    <TARGET_PATH>

    Read all of them with the Read tool. If the target links to detail
    documents under a `plan/` folder beside it, those are part of the
    target — read them too. Read nothing else.

    ## Your job

    Two failure modes, and only these two.

    **Gap** — an upstream item (요구 N — older docs write it FR-N —, NFR,
    key decision, risk, constraint,
    explicit exclusion) that appears nowhere downstream. Name the upstream
    item and say where you looked.

    **Conflict** — the target contradicts an upstream constraint. This
    includes silently re-admitting something upstream placed out of scope.
    Quote both sides.

    Walk the upstream documents item by item. Do not sample.

    ## What you must NOT do

    - Do NOT accept "this is obviously covered by" without pointing at the covering text
    - Do NOT report problems internal to the target that no upstream item speaks to — a different verifier owns that axis
    - Do NOT read files outside the list above
    - Do NOT run code-impact analysis (file existence checks, caller
      searches, grep across the repo) — the main agent owns that axis
    - Do NOT edit anything — you are strictly read-only
    - Do NOT report style or formatting preferences

    ## Calibration

    Coverage can be indirect: an upstream item may be satisfied by a
    section that never quotes its ID. Look for the substance before
    calling a gap. Conversely, a section that names an item without
    addressing it is still a gap.

    ## Report format

    Return exactly this, nothing else:

    GAPS: <count>
    - <upstream item ID / title> — <where you looked, why it is not covered>
    CONFLICTS: <count>
    - <upstream item> says <X>; <target> §<section> says <Y>

    If none: GAPS: 0 and CONFLICTS: 0
```
