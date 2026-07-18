---
description: 현재 프로젝트 루트의 .worktrees/ 아래에 워크트리를 만들고 로컬 빌드 환경 파일을 자동 복사합니다. 단수/복수 모두 지원.
---

# /worktree

이 슬래시는 `setting-up-worktrees` skill 을 호출합니다.

## 사용 예

**단수:**
```
/worktree feature-a
```

**복수:**
```
/worktree feature-a feature-b feature-c
```

**자연어 (인수 없이 호출 후 대화):**
```
/worktree
워크트리 3개 만들어줘. 브랜치는 feature-a, feature-b, feature-c.
```

티켓명(`TICKET-123-기능명`)을 그대로 브랜치명으로 사용해도 됩니다 (한글/특수문자 OK).

## 동작

- 위치: `<프로젝트 루트>/.worktrees/<브랜치명>/`
- 브랜치 없으면 현재 HEAD에서 새로 생성, 있으면 그대로 사용
- **로컬 빌드 환경 파일 자동 복사**: 프로젝트 루트의 로컬 빌드 환경 파일(Node `.env*`, Android `local.properties`, iOS `*.xcconfig` 등)을 각 워크트리에 그대로 복사. 후보는 메인이 프로젝트 종류를 보고 자동 판단하고, 감지 목록을 한 줄로 통지한 뒤 바로 복사합니다 (블로킹 질문 없음 — 특정 파일 제외를 원하면 알려주면 존중). 커밋된 템플릿(`.env.example`/`.env.sample`/`.env.template`)은 제외.
- **Claude 메모리 폴더 자동 심링크 (PostToolUse hook)**: 워크트리 생성 시 `worktree-memory-symlink` 훅이 자동으로 메인 레포의 `~/.claude/projects/<encoded>/memory` 를 워크트리의 동일 위치에 심링크. 사용자/에이전트의 별도 액션 불필요. 메인에 메모리 0건이거나 워크트리에 이미 메모리 폴더가 있으면 자동 생략.
- `.worktrees/` 가 `.gitignore` 에 없으면 자동 추가
- 이미 같은 path 가 있으면 skip + notice (덮어쓰기 X)

## 전제

현재 디렉터리가 git 저장소여야 함. 아니면 `git init` 안내.
