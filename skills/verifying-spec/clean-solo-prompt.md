# Clean Solo Verifier Prompt Template

Use this template when dispatching the **solo** clean-context verifier from `verifying-spec`.

**Purpose:** Read the target document COLD — no upstream spec, no conversation history, no author narrative — and report what is wrong with the document *on its own terms*. This catches the failure class that requirement-matching cannot: a document that satisfies every upstream item and is still unbuildable.

**Injection rule (HARD):** substitute ONLY `<TARGET_PATH>`. Never add upstream paths, the author's reasoning, the conversation, or the doc's `## 변경이력` footer. The urge to "give it a little context" is exactly the bug this verifier exists to catch.

```
Agent tool (general-purpose):
  run_in_background: true
  # NO model argument — inherit the session model (D7)
  description: "Clean solo verify <target basename>"
  prompt: |
    You are reviewing a technical document you have never seen before.

    You have NO context about this project, this feature, or why this
    document was written. That is deliberate. Do not ask for context, and
    do not charitably reconstruct what the author probably meant.

    ## The document

    <TARGET_PATH>

    Read it with the Read tool. This is the ONLY file you may read.

    ## Your job

    Judge the document on its own terms. Someone is handed this file and
    told "build this." Can they?

    Report anything that would stop them.

    **Ambiguity** — a sentence readable two ways, where the two readings
    produce different implementations.

    **Undecided** — a decision the document defers or leaves implicit
    while later sections assume it was made.

    **Internal contradiction** — one section assumes the opposite of
    another. Quote both.

    **Unverifiable** — a success criterion nobody could check. "Works
    well", "is fast", "handles errors gracefully".

    **Unbuildable** — a step or component described too thinly to build,
    with no pointer to where the detail lives.

    **Dead weight** — content that contradicts nothing and adds nothing.
    A section restating another. A decision with no consequence.

    ## What you must NOT do

    - Do NOT guess what the upstream requirements probably said
    - Do NOT read any other file, including siblings in the same folder
    - Do NOT run code-impact analysis (file existence checks, caller
      searches, grep across the repo) — the main agent owns that axis
    - Do NOT edit anything — you are strictly read-only
    - Do NOT soften a finding because the author "probably meant" something
    - Do NOT report style or formatting preferences

    ## Calibration

    Do not manufacture findings. An empty report is a valid result and
    beats a padded one. But do not stay quiet about something that
    genuinely blocked you while reading.

    ## Report format

    Return exactly this, nothing else:

    FINDINGS: <count>
    - [<ambiguity|undecided|contradiction|unverifiable|unbuildable|dead-weight>] <section or line reference> — <what is wrong, one or two sentences>
    - ...

    If nothing: FINDINGS: 0
```
