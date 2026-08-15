---
id: self/command-skill-name-collision
title: 커맨드 이름이 스킬 이름을 가리지 않는다
status: active
layer: [D]
covers:
  - commands/*.md
  - skills/*/SKILL.md
expect:
  - kind: shell
    argv: ["bash", "-c", "for c in commands/*.md; do n=$(basename \"$c\" .md); if [ -d \"skills/$n\" ]; then echo \"$n\"; fi; done | wc -l"]
    op: eq
    value: 0
  - kind: shell
    argv: ["bash", "-c", "grep -l 'js-super:tech-design' commands/design-tech.md commands/auto-design-tech.md 2>/dev/null | wc -l"]
    op: gte
    value: 1
traceability: [2026-08-15 이름 충돌 사고]
---

# 커맨드 이름이 스킬 이름을 가리면 그 스킬은 호출 불가

**시나리오**: `commands/<이름>.md` 와 `skills/<이름>/` 이 같은 이름이면 커맨드가
스킬을 가린다. 그 스킬은 Skill 도구로 어떤 이름으로도 호출할 수 없다.
`js-super:<이름>` 을 부르면 커맨드 본문이 돌아오고, `<이름>` 만 주면 Unknown skill 이 난다.

**실제 사고 (2026-08-15)**: 네 쌍이 충돌해 있었다.

| 옛 슬래시 | 스킬 | 결과 |
|---|---|---|
| `/tech-design` | `tech-design` | 스킬 호출 불가 |
| `/auto-tech-design` | `auto-tech-design` | 스킬 호출 불가 + auto 체인 끊김 |
| `/worktree-merge-back` | `worktree-merge-back` | 스킬 호출 불가 |
| `/worktree-remove` | `worktree-remove` | 스킬 호출 불가 |

네 커맨드 모두 스킬로 넘기는 얇은 껍데기였으므로 네 기능이 전부 죽어 있었다.
슬래시를 `/design-tech`, `/auto-design-tech`, `/merge-back-worktree`,
`/remove-worktree` 로 바꿔 해소했다. 스킬 이름은 그대로 뒀다.

**왜 기존 검사로는 안 잡혔나**: `CLAUDE.md` 의 체인 확인 grep
(`grep -cF "js-super:auto-tech-design" skills/auto-brainstorming/SKILL.md`) 은
1 을 반환해 통과한다. 문자열은 제자리에 있고 해석만 달라지는 경우라
문면 검사로는 원리상 안 잡힌다.

**검증 방법**: 커맨드 파일명과 스킬 디렉토리명이 겹치는 쌍이 하나도 없어야 한다.
그리고 위임 커맨드가 가리키는 스킬 이름이 자기 슬래시 이름과 달라야 한다.

**놓치는 것**: 실제로 Skill 도구를 불렀을 때 스킬이 오는지 커맨드가 오는지는
여기서 안 본다. 그건 실행 층위(2차)에서 로드 정보와 도구 호출 기록으로 확인한다.
그때는 `--plugin-dir` 이 설치본을 대체하지 않는다는 점도 같이 처리해야 한다
(`사전실측-노트.md` §4).
