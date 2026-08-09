# 개발방향: 워크트리-재분기

> **다음 단계 안내**: 이 문서는 기술 설계서입니다 (아키텍처 / 컴포넌트 / 데이터 / 인터페이스 / 결정 / 위험 / 테스트 전략). `워크트리-재분기-requirements.md` (PRD) 를 기반으로 작성되고, 다음 단계 `워크트리-재분기-implementation-plan.md` (단계별 계획) 의 입력이 됩니다. 다음 단계로 `writing-plans` skill (또는 `/write-plan` 슬래시) 을 호출해서 구현 계획을 만드세요. 단계별 구현 task 는 여기 박지 마세요 — 그건 다음 산출물 (plan) 에 들어갑니다.

## 1. 아키텍처 개요 (diagram + prose)

핵심 변경은 `setting-up-worktrees` 스킬의 **루트 해석 단계**를 둘로 쪼개는 것이다. 지금은 "호출 위치의 루트" 하나 (`git rev-parse --show-toplevel`) 를 배치 기준과 분기 기준 양쪽에 쓰는데, 워크트리 안에서 호출하면 이 둘이 갈라져야 한다:

- **배치 기준 = MAIN_ROOT** (메인 저장소 루트) — `git worktree list --porcelain` 의 첫 entry. 새 워크트리는 항상 `MAIN_ROOT/.worktrees/<새브랜치>`.
- **분기 기준 = 호출 위치의 HEAD** — git 명령을 호출 cwd 에서 실행하므로 HEAD 가 자동으로 현재 워크트리의 커밋을 가리킨다.

```
[호출 위치]                          [배치 위치]
메인 루트에서 호출 ──→ MAIN_ROOT = 자기 자신 ──→ 기존 동작 그대로 (FR-5)
워크트리 A 에서 호출 ─→ MAIN_ROOT = 첫 entry ──→ MAIN_ROOT/.worktrees/<새브랜치>
                        분기 기준 = A 의 HEAD      (중첩 방지, FR-1 + FR-2)
```

흐름: Step 0 루트 해석 (MAIN_ROOT + BASE_SHA + BASE_BRANCH 캡처) → Step 3.5 dirty 게이트 (신규, FR-3) → Step 4 워크트리 생성 (브랜치별 개별 `git worktree add` Bash 호출) → 훅이 메모리 심링크 → Step 6 보고 확장 (FR-4).

## 2. 영향 받는 컴포넌트/파일

| 파일 | 변경 | 관련 FR |
|---|---|---|
| `skills/setting-up-worktrees/SKILL.md` | Step 0 루트 해석 이원화 + Step 3.5 dirty 게이트 신설 + Step 4 개별 add 호출 + Step 5 복사 소스 변경 + Step 6 보고 확장 + Defaults 표 / Anti-Patterns 갱신 | FR-1~5 |
| `commands/worktree.md` | 동작 안내 동기화 (v2.0.2+ 결합 룰 — skill 과 atomic) | FR-1~4 |
| `hooks/worktree-memory-symlink` | ROOT 해석을 `--show-toplevel` → 메인 워크트리 (worktree list 첫 entry) 로 교체 | FR-1, FR-7 |
| `skills/setting-up-worktrees/scripts/setup-memory-symlinks.sh` | **변경 불필요** — 인자 기반이라 훅이 올바른 MAIN_ROOT 를 넘기면 그대로 동작 (검토 완료) | FR-7 |
| `CLAUDE.md` | 결합 메모 신설 (skill + command + hook atomic 룰) | — |
| 6 manifest | 버전 bump (repo 관례) | — |

### FR-7 검토에서 발견한 기존 버그 2건 (본 설계에서 수정)

1. **훅 prefix match 취약**: 훅은 Bash 명령 문자열이 정확히 `git worktree add ` 로 **시작**할 때만 발화한다 (`hooks/worktree-memory-symlink:53-56`). 현재 스킬 Step 4 는 `for BR in ...` 루프 한 방이라 프리픽스가 매치되지 않아 **훅이 아예 발화하지 않는 잠재 버그**가 있다. → Step 4 를 브랜치별 개별 `git worktree add ...` Bash 호출로 재구성 (변수 계산은 별도 선행 호출).
2. **워크트리 안 호출 시 훅 silent ignore**: 훅의 ROOT 는 호출 cwd 의 `--show-toplevel` (`hooks/worktree-memory-symlink:62`) 이라, 워크트리 안에서 호출하면 새 워크트리 경로 (`MAIN_ROOT/.worktrees/...`) 가 `$ROOT/.worktrees/` 프리픽스와 매치되지 않아 심링크가 조용히 생략된다 (`hooks/worktree-memory-symlink:120-130`). → 훅의 ROOT 해석을 메인 워크트리로 교체.

## 3. 데이터 모델/스키마 변경 — N/A: 본 피처는 DB/스키마 무관 (skill 본문 + bash 훅 변경)

## 4. 외부 인터페이스 — N/A: API/event 노출 없음

## 5. 핵심 결정 + 대안 비교 (why this path)

- **D-1 메인 루트 판정 = `git worktree list --porcelain` 첫 entry** (채택). 첫 entry 가 메인 워크트리라는 것은 git 문서가 보장하고, `/goodmorning` 등 기존 커맨드와 같은 컨벤션. 대안: `git rev-parse --git-common-dir` 의 부모 디렉토리 — bare repo / `.git` 위치 특수 배치에서 가정이 깨질 수 있어 기각.
- **D-2 분기 기준 = 호출 cwd 의 HEAD** (채택). git 명령을 호출 위치에서 실행하면 HEAD 가 자동으로 현재 워크트리 커밋 — 별도 인자 불필요, 사용자 질문 0. `BASE_SHA`/`BASE_BRANCH` 를 생성 직전 캡처해 보고에 사용. 사용자가 "dev 기준으로" 처럼 베이스를 명시하면 그 브랜치를 `git worktree add` 마지막 인자로 지정. 대안: 항상 메인 브랜치 기준 — FR-2 위반이라 기각.
- **D-3 dirty 게이트 = AskUserQuestion 2 옵션** (채택). `git status --porcelain` 이 비어있지 않으면 "WIP 커밋 후 분기" / "마지막 커밋 시점 기준 분기" 선택 (FR-3). WIP 커밋 메시지는 변경 요약으로 LLM 생성. stash 금지 (요구사항 명시). 대안: worktree-merge-back v2.5.2 처럼 무조건 자동 커밋 — 분기 시작점이 달라지는 결정이라 사용자 선택 유지 (요구사항 FR-3 명시).
- **D-4 심링크 훅 수정** (채택). 훅의 ROOT 해석만 메인 워크트리로 교체 — 스크립트 (`setup-memory-symlinks.sh`) 는 인자 기반이라 무변경. 대안: 스킬 본문에서 심링크 직접 수행 — 과거 회귀 (v1.1.2~v1.1.4, 에이전트가 인코딩을 머리로 시뮬레이션) 때문에 Anti-Pattern 으로 금지된 경로라 기각.
- **D-5 `git worktree add` 를 Bash 명령 시작으로 유지** (채택). 훅 프리픽스 매치 보장을 위해 MAIN_ROOT 계산 Bash 호출과 `git worktree add` Bash 호출을 분리하고, 복수 브랜치도 브랜치별 개별 호출. 대안: 훅의 프리픽스 매치를 substring 매치로 완화 — 오발화 표면이 넓어져 기각 (스킬 절차 쪽에서 보장하는 것이 보수적).
- **D-6 `.gitignore` 대상 = MAIN_ROOT** (채택). 기존 idempotent 추가 로직 유지, 대상만 메인 루트. 워크트리 안 호출로 메인 워크트리에 실제 추가가 일어나는 경우 (드묾 — 보통 이미 등록됨) 한 줄 알림. 대안: 워크트리 호출 시 `.gitignore` 생략 — 신규 저장소 첫 재분기 시 등록 누락 위험이라 기각.
- **D-7 로컬 빌드 환경 파일 복사 소스 = 호출 위치 워크트리 루트 우선** (채택). base 워크트리에서 갱신된 env 가 최신일 가능성이 높다. 후보 파일이 호출 위치에 없으면 MAIN_ROOT 에서 fallback 복사. 대안: 항상 MAIN_ROOT — base 의 최신 env 를 놓쳐 기각.
- **D-8 스택 안내 판정 = BASE_BRANCH ≠ 메인 워크트리 브랜치** (채택). 다르면 보고에 스택 구조 (새브랜치 → 베이스 → 메인) + "베이스가 메인에 리베이스되면 새 브랜치도 리베이스 필요" 주의를 출력 (FR-4). BASE_SHA 는 항상 출력.

## 6. 위험/사이드이펙트 (preliminary)

- **breaking**: Step 0 루트 해석 교체가 잘못되면 기존 메인 루트 호출까지 깨진다 (FR-5 위반). 메인 루트에서는 worktree list 첫 entry = 자기 자신이므로 동작 동일해야 하며, E2E 시나리오 (a) 로 검증.
- **breaking**: 훅 ROOT 해석 교체 실패 시 기존 메인 루트 생성 케이스의 심링크까지 깨질 수 있다. 훅 단독 시뮬레이션 테스트 (가짜 JSON stdin) 로 양쪽 케이스 검증.
- **side-effect**: 워크트리 안 호출 시 MAIN_ROOT 의 `.gitignore` 에 추가가 발생하면 메인 워크트리가 dirty 해진다. 실제 추가가 일어난 경우에만 한 줄 알림으로 완화 (D-6).
- **side-effect**: upstream `using-git-worktrees` 스킬 등 다른 경로로 만드는 워크트리 — 훅은 `.worktrees/` 아래 경로만 처리하므로 영향 없음 (기존과 동일).
- **race**: 없음 — 전 단계 동기 순차 실행.

## 7. 테스트 전략

Bash E2E (FR-6, scratchpad 임시 git 저장소에서 실행, 사용자 명시 요구 — 구현 마지막 단계 필수):

- **(a) 기존 동작**: 메인 루트에서 신규 브랜치 생성 → `.worktrees/` 배치 + dev HEAD 분기 확인 (FR-5)
- **(b) 재분기**: 워크트리 A 안에서 신규 브랜치 생성 → 메인루트/.worktrees/ 배치 (중첩 없음) + 분기 커밋 == A 의 HEAD 확인 (FR-1, FR-2)
- **(c) dirty 분기**: A 에 uncommitted 변경 → WIP 커밋 경로와 커밋 시점 분기 경로 각각 결과 검증 (FR-3; AskUserQuestion 은 E2E 에서 양 분기 모두 스크립트로 실행)
- **(d) 기존 브랜치 attach**: 로컬 존재 브랜치 / remote-only 브랜치 attach 케이스 (기존 로직 회귀 확인)
- **(e) 훅 단독 시뮬레이션**: `hooks/worktree-memory-symlink` 에 가짜 JSON stdin (메인 루트 cwd / 워크트리 cwd 두 케이스) → MAIN_ROOT 해석 + 심링크 스크립트 인자 검증. `$HOME` 을 임시 디렉토리로 격리해 실제 `~/.claude` 오염 방지.
- 스킬 본문 회귀 grep: `git worktree add` 가 개별 Bash 호출 프리픽스로 유지되는지, `--show-toplevel` 단독 사용이 배치 기준으로 남아있지 않은지.

---
## 변경이력

### [2026-08-09 20:48] [개발방향-수정]
- **id**: CH-20260809-002
- **이유**: 신규 기술 설계 (verifying-spec 4축 보고서 gap/conflict 0건 — 사용자 auto 진행 지시로 게이트 자동 통과)
- **무엇이**: 워크트리-재분기-tech-design.md 전체 (D-1..D-8, FR-7 검토 버그 2건 포함)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260809-001
