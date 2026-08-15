---
id: self/eval-assets-not-loaded
title: eval 자산이 Claude Code 로드 경로에 없다
status: active
layer: [C]
covers:
  - commands/*.md
  - evals/*.py
  - evals/runner/*.py
expect:
  - kind: shell
    argv: ["bash", "-c", "find commands -mindepth 1 -type d | wc -l"]
    op: eq
    value: 0
  - kind: shell
    argv: ["bash", "-c", "ls -d skills/evals evals/skills 2>/dev/null | wc -l"]
    op: eq
    value: 0
  - kind: shell
    argv: ["bash", "-c", "ls -d evals/commands agents/evals 2>/dev/null | wc -l"]
    op: eq
    value: 0
  - kind: shell
    argv: ["bash", "-c", "n=0; for f in commands/*.md; do head -1 \"$f\" | grep -q '^---$' || n=$((n+1)); done; echo $n"]
    op: eq
    value: 0
traceability: [수용기준-8, 수용기준-11]
---

# eval 자산이 사용자에게 안 보인다

**시나리오**: Claude Code 는 `skills/`, `commands/`, `agents/`, `hooks/hooks.json`
네 곳만 자동으로 읽어들인다. eval 자산이 그 안에 들어가면 플러그인 사용자 세션에
스킬 설명이 상주하거나 슬래시 목록에 뜬다.

**과거 사고**: `commands/audit-risk-tests/H23-e2e/README.md` 가
`js-super:audit-risk-tests:H23-e2e:README` 라는 슬래시로 실제 등록되고 있었다.
`commands/` 아래 하위 디렉토리가 재귀로 스캔되고 디렉토리명이 콜론으로 이어지기
때문이다. 2026-08-15 에 `tests/eval-fixtures/H23-e2e/` 로 옮겨 해소했다.

**같은 종류로 걸렸던 것 (2026-08-15 해소)**: `commands/audit-report-prompt.md` 도
`/audit-risk` 의 프롬프트 자산인데 `commands/` 에 있어 슬래시로 등록되고 있었다.
같은 날 audit-risk 가 마크다운 단일 산출물로 재작성되면서 이 파일 자체가 삭제돼
문제도 함께 사라졌다.

프롬프트 자산의 제자리는 소유 스킬 옆이다
(`skills/js-super-sub-driven/implementer-prompt.md`,
`skills/verifying-spec/clean-solo-prompt.md` 등).
스킬 없이 커맨드만 있는 흐름에서 프롬프트 자산이 새로 필요해지면 둘 곳부터 정할 것 —
`commands/` 아래에 두면 같은 문제가 반복된다.

**검증 방법**: `commands/` 아래에 하위 디렉토리가 하나도 없어야 하고,
`skills/` 와 `agents/` 아래에 eval 관련 디렉토리가 없어야 하며,
`commands/*.md` 가 전부 frontmatter 로 시작해야 한다 (frontmatter 없는 파일은
커맨드가 아니라 자산인데 커맨드로 등록되고 있다는 뜻).

**놓치는 것**: 플러그인 캐시에 실제로 무엇이 로드되는지는 여기서 안 본다.
그건 헤드리스 실행이 붙는 2차에서 로드 정보 한 줄을 읽어 확인한다.
그때는 `--plugin-dir` 이 설치본을 대체하지 않는다는 점도 같이 처리해야 한다
(`사전실측-노트.md` §4).
