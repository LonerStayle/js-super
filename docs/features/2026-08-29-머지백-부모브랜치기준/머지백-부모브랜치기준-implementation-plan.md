---
slug: 머지백-부모브랜치기준
commit_policy: per-task
execution_mode: main-inline-or-subagent
note: "슬림 plan — `**원본**` 블록 생략 (마크다운 skill 본문의 중첩 코드 펜스가 plan_byte_check 파서와 충돌, v2.5.1-worktree-cleanup-auto 선례). implementer 가 대상 파일을 직접 Read 후 task 지시대로 편집."
---

# 머지백 부모브랜치 기준 (implementation-plan)

**Slug**: 머지백-부모브랜치기준
**작성일**: 2026-08-29
**총 task 수**: 7 (Wave 1~3)
**참조**: requirements (CH-20260829-001), tech-design (CH-20260829-002, CH-20260829-003)

핵심: `/merge-back-worktree` 의 머지 대상을 "워크트리 목록 첫 entry = 최상위" 추론에서 **생성 시 기록된 직계 부모 브랜치** 로 교체한다. 기록은 공유 git config 키 2개 (`branch.<BR>.js-super-parent` = 부모 이름 / `branch.<BR>.js-super-parent-base` = 분기 SHA). 판별은 검증 4건 전부 통과 시에만 자동 진행, 하나라도 실패하면 AskUserQuestion 게이트로 사용자 확인 (조용한 최상위 fallback 금지).

---

## §1. Tasks

### Wave 1 — 본문 5 파일 (전부 독립 파일 — 병렬 가능)

#### Task 1 — setting-up-worktrees: 분기 부모 기록 (FR-2)

- **Files**: `skills/setting-up-worktrees/SKILL.md`
- **Model**: sonnet (Korean prose + 다중 위치 편집)
- **검증**: 본문에 `js-super-parent` 가 2회 이상 등장하고, 기록 명령이 "별도 Bash 호출" 로 명시되며, Acceptance 에 기록 검증 항목이 추가됐다. `grep -c "js-super-parent" skills/setting-up-worktrees/SKILL.md` ≥ 2 로 확인.
- **작업 내용** (한 파일 multi-step — same-file 묶음 룰):
  1. **Step 4 끝에 기록 서브스텝 추가** — "신규 브랜치 생성 직전 `BASE_SHA` / `BASE_BRANCH` ..." 문단 바로 뒤에 다음 요지의 블록 추가:
     - 신규 분기 (`-b`) 로 워크트리를 만든 경우에만, add 성공 직후 **별도의 후속 Bash 호출**로 분기 부모를 기록한다 (`git worktree add` 와 한 호출로 묶으면 메모리 심링크 훅의 접두사 매치가 깨진다):

       ```bash
       git config "branch.<BR>.js-super-parent" "$BASE_BRANCH"
       git config "branch.<BR>.js-super-parent-base" "$BASE_SHA"
       ```
     - `worktree-merge-back` 가 이 기록으로 직계 부모를 판별한다. 같은 이름 브랜치를 이 스킬로 다시 만들면 덮어쓴다.
     - 기록 생략 케이스: 기존 로컬 브랜치 attach / remote-only attach (분기 이력을 모름) / `BASE_BRANCH` 가 빈 값 (detached HEAD). 기록이 없으면 머지백 시점에 사용자 확인 게이트가 흡수한다.
  2. **Defaults 표 Branch creation 행 보강** — 행 끝에 "신규 생성 시 분기 부모를 공유 git config 에 기록 (`js-super-parent` / `js-super-parent-base`)" 추가.
  3. **Step 6 보고 갱신** — "분기 기준: <BASE_BRANCH> @ <BASE_SHA 앞 7자리>" 줄 아래에 "부모 기록: ✓ (머지백이 이 브랜치로 머지)" / attach 케이스는 "부모 기록: 없음 (기존 브랜치 attach — 머지백 시 대상 확인)" 표기 추가.
  4. **Anti-Patterns 행 추가** — "기록 명령을 `git worktree add` 와 한 Bash 호출로 묶기 | 훅 프리픽스 미매치 → 심링크 미생성. 기록은 add 이후 별도 호출." 행 추가.
  5. **Acceptance 항목 추가** — "11. 신규 분기로 만든 워크트리마다 분기 부모 기록 (`js-super-parent` + `js-super-parent-base`) 이 남았고, attach 케이스는 기록 없이 보고에 그 사실이 표기됐다."
- **RISK**: side-effect — `worktree-memory-symlink` 훅 결합 (기록 명령이 add 호출의 접두사를 바꾸면 안 됨 — 별도 호출로 회피)
- **Self-Review**: Step 4 의 기존 add 명령 4줄 (attach / remote-only / 신규 HEAD / 베이스 명시) 은 무변경. HARD-GATE 2건 무변경.

#### Task 2 — worktree-merge-back: 머지 대상을 직계 부모로 교체 (FR-1, FR-3, FR-4, FR-5)

- **Files**: `skills/worktree-merge-back/SKILL.md`
- **Model**: sonnet (다중 섹션 교체 + Korean prose + 게이트 신설)
- **검증**: `grep -c "MAIN_INFO" skills/worktree-merge-back/SKILL.md` = 0 / `grep -c "js-super-parent" ...` ≥ 2 / `grep -cF "판별 실패" ...` ≥ 1 / 기존 결합 grep 유지 — `grep -F "git default 재귀 머지"` ≥ 1, `grep -F "Step 4.5"` ≥ 1, `grep -F "Step 1 — Working tree 검사 + 자동 커밋 (v2.5.2+"` ≥ 1, `grep -c "Other / 모호 응답 처리 (v2.1.1+)"` 매치 수 변화 없음 (헤더 문자열 보존), `--no-ask` 0건.
- **작업 내용** (한 파일 multi-step — same-file 묶음 룰):
  1. **frontmatter description 갱신** — "parent 브랜치를 먼저 흡수해" 앞에 머지 대상이 "생성 시 기록된 직계 부모 브랜치" 임을 명시 (한 문장 유지, 길이 비슷하게).
  2. **도입부 문단 갱신** — "parent (main) 워크트리로" → "직계 부모 워크트리로" 계열 표현으로 교체하고, 끝에 "머지 대상은 워크트리 생성 시 기록된 직계 부모 브랜치 — 재분기 워크트리는 최상위가 아니라 자기를 분기시킨 브랜치로 머지된다. 판별이 불확실하면 자동 진행하지 않고 사용자에게 확인한다." 요지 2문장 추가. 버전 태그는 새로 달지 않는다 (bump 는 main 에서).
  3. **`## Other / 모호 응답 처리 (v2.1.1+)` 섹션 재활성** — 헤더 문자열은 그대로 두고, 본문을 "본 skill 은 Step 2 판별 실패 시 머지 대상 확인 게이트 1건을 갖는다 (부모브랜치기준 개선으로 재도입). 사용자가 Other 자유 응답 또는 모호 답변 시 → 그 질문만 단독 재호출 + prose 설명 추가, 자동 진행 X." 로 교체. `## Process` 헤더의 "(v2.5.2+ — 게이트 0건, ...)" 표현과 그 아래 "게이트 0건" 서술 2곳도 "게이트 1건 (Step 2 판별 실패 시에만)" 으로 동기.
  4. **Step 2 전면 교체** — 기존 "### Step 2 — Parent worktree 추론 (자동)" 섹션 (MAIN_INFO / MAIN_PATH / MAIN_BRANCH bash + WT_COUNT 검사 + "추론 실패 (multi-parent / nested) → 명시 차단" 줄) 을 "### Step 2 — 직계 부모 판별 (기록 기반, 검증 4건)" 으로 교체. 새 본문 요지:
     - tech-design §3 의 판별 bash 그대로: FEATURE_BRANCH / PARENT_BRANCH / PARENT_BASE 판독 + 검증 4건 (① 기록 존재 + 자기 자신 아님 ② `refs/heads/` 실존 ③ 워크트리 체크아웃 → PARENT_PATH 확보 ④ `git merge-base --is-ancestor "$PARENT_BASE" HEAD` 분기점 조상 검사)
     - 기존 WT_COUNT ≥ 2 검사는 유지 (HARD-GATE 보조 — `MAIN_*` 변수 미사용이라 그대로)
     - 최상위 브랜치 이름은 **신규 변수 `TOP_BRANCH`** 로 얻는다 (`git worktree list --porcelain` 첫 entry 의 branch 필드 — 옛 `MAIN_BRANCH`/`MAIN_PATH`/`MAIN_INFO` 변수명은 재사용 금지, Self-Review grep 과 충돌). 용도는 스택 판정 (Step 5) 과 게이트 후보 나열뿐 — 머지 대상 결정에 쓰지 않는다는 문장 명시. (HARD-GATE 블록 안의 `MAIN_WORKTREE` 는 진입 차단용이라 무변경 — grep 대상 아님)
     - **판별 실패 게이트**: 검증 4건 중 하나라도 실패 → `AskUserQuestion` 으로 머지 대상 확인. 질문 본문에 실패 사유 1줄 (기록 없음 / 부모 브랜치 삭제됨 / 부모 미체크아웃 / 분기점 조상 아님). options = 최상위 브랜치 + 다른 워크트리 체크아웃 브랜치들 (자기 자신 제외, 4개 초과분은 Other 안내) + **"중단" 옵션 항상 포함**. 중단 선택 시 안내 1줄 출력 후 종료 — "부모 워크트리를 먼저 만들고 (`/worktree <부모브랜치>`) 본 skill 을 재호출해주세요" (부모 미체크아웃 케이스의 정상 탈출 경로 — R2). 사용자가 브랜치를 고른 경우 (Other 포함) 에도 검증 ②③ 재적용 — 실패 시 사유 안내 + 게이트 재호출 (탈출은 언제든 "중단"). 조용한 최상위 fallback / 히스토리 추정 자동 진행 절대 금지.
  5. **Step 3 갱신** — 머지 대상 서술을 "직계 부모 브랜치 (Step 2 판별 결과)" 로, bash 를 `git merge $PARENT_BRANCH` 로 교체. "git default 재귀 머지" 문구와 충돌 처리 절차 (conflict marker 시 prose 안내 + `--strategy` 금지) 는 그대로 유지.
  6. **Step 4 갱신** — pre-check `git merge-base --is-ancestor $PARENT_BRANCH HEAD`, 머지 실행 `git -C "$PARENT_PATH" merge --no-ff "$FEATURE_BRANCH" -m "Merge branch '$FEATURE_BRANCH' into $PARENT_BRANCH"` 로 변수 교체.
  7. **Step 4.5 갱신** — cp 대상 경로 `$MAIN_PATH` → `$PARENT_PATH` (환경 파일은 직계 부모 워크트리로 동기화). 나머지 룰 (LLM 판단 / silent 금지 / `-pP`) 무변경.
  8. **Step 5 갱신** — 종료 메시지의 `<MAIN_BRANCH>` → `<PARENT_BRANCH>`, "Remote 동기화 / push" 안내의 main-path → parent-path. 그리고 `PARENT_BRANCH` ≠ 최상위 브랜치일 때만 붙는 스택 안내 블록 추가: "ℹ️ 이 머지는 직계 부모 (<PARENT_BRANCH>) 까지입니다. 최상위 (<최상위 브랜치>) 반영은 부모 워크트리에서 `/merge-back-worktree` 를 다시 실행해주세요."
  9. **Anti-Patterns 표 갱신** — 변수 교체 반영 (`cd .*MAIN_PATH` 행 → `cd .*PARENT_PATH` 표현) + 신규 3행: "기록 없을 때 조용히 최상위로 머지 | NEVER — 판별 실패 게이트로 사용자 확인 (FR-3)", "커밋 히스토리 추정으로 부모 자동 선택 | NEVER — 기록 + 검증 4건만 신뢰", "게이트에서 사용자가 고른 대상을 재검증 없이 머지 | 검증 ②③ 재적용 후 진행".
  10. **"Why 부모브랜치 기준" 섹션 추가** — "Why v2.5.2" 다음에: 재분기 워크트리에서 최상위로 머지하려던 문제 (모델이 우연히 막아주던 상태) + 기록 기반 판별 + 검증 4건 + 게이트 요약 5줄 이내.
  11. **Related Skills 갱신** — `setting-up-worktrees` 행을 "워크트리 생성 페어 — 분기 부모 기록 (`js-super-parent`) 을 이 skill 이 판독" 으로 교체.
- **RISK**: breaking — Step 2 는 이 skill 의 모든 후속 단계가 쓰는 변수의 원천 (교체 누락 시 절반은 부모, 절반은 최상위로 동작하는 최악 케이스). Self-Review 에서 `MAIN_PATH|MAIN_BRANCH|MAIN_INFO` 전수 grep 으로 잔존 0 확인.
- **Self-Review**: HARD-GATE worktree-only 블록 무변경 (그 안의 `MAIN_WORKTREE` 변수는 진입 차단용이라 유지 — 머지 대상 아님). Step 1 자동 커밋 절차 무변경. `--strategy ours/theirs` 금지 문구 유지.

#### Task 3 — commands/merge-back-worktree.md 안내 동기

- **Files**: `commands/merge-back-worktree.md`
- **Model**: sonnet (Korean prose)
- **검증**: 본문에 "직계 부모" 가 1회 이상 등장하고, 판별 실패 시 확인 게이트 안내가 있다. `grep -cF "직계 부모" commands/merge-back-worktree.md` ≥ 1.
- **작업 내용**:
  1. description — "워크트리에서 parent 로" → "워크트리에서 직계 부모로" 갱신.
  2. 자동화 불릿 갱신 — "머지 대상은 parent 워크트리의 **로컬** 브랜치" 불릿을 "머지 대상은 워크트리 생성 시 기록된 **직계 부모** 브랜치의 로컬 상태 (재분기 워크트리는 자기를 분기시킨 브랜치로 머지 — 최상위 아님). 기록이 없거나 부모가 사라졌으면 자동 진행하지 않고 머지 대상을 물어봄" 으로 교체. origin 미fetch 문구는 유지.
- **RISK**: none (안내문)
- **Self-Review**: 슬래시 이름 ≠ 스킬 이름 주의 문구 유지. 한국어 친화 톤 (v2.4+).

#### Task 4 — commands/worktree.md 안내 동기

- **Files**: `commands/worktree.md`
- **Model**: sonnet (Korean prose)
- **검증**: 동작 섹션에 분기 부모 기록 안내 1줄이 있다. `grep -cF "부모" commands/worktree.md` ≥ 1.
- **작업 내용**: "## 동작" 의 분기 기준 불릿 다음에 불릿 1개 추가 — "**분기 부모 자동 기록**: 새 브랜치로 만들 때 분기 부모(브랜치 + 커밋)를 저장소 설정에 기록 — 나중에 `/merge-back-worktree` 가 이 기록으로 직계 부모에 머지합니다. 기존 브랜치를 붙일 때는 기록하지 않습니다 (머지백 시 대상 확인)."
- **RISK**: none (안내문)
- **Self-Review**: 기존 불릿 무변경. 한국어 친화 톤.

#### Task 6 — CLAUDE.md 결합 메모 신규 섹션

- **Files**: `CLAUDE.md`
- **Model**: sonnet (Korean prose + eval 파싱 계약 준수)
- **검증**: `grep -cF "## 워크트리 부모브랜치 기록 결합" CLAUDE.md` ≥ 1 이고, 신규 섹션의 bash 블록이 eval 러너 파싱 형식 (bash fence + `# expected:`) 을 지킨다.
- **작업 내용**: 파일 끝 ("## 스킬목록 홈 전체 조회 결합" 섹션 뒤) 에 `## 워크트리 부모브랜치 기록 결합` 섹션 append:
  - **핵심 룰**: 기록 키 2개 규약 (`branch.<BR>.js-super-parent` / `.js-super-parent-base`) 은 생성 (`setting-up-worktrees`) 과 판독 (`worktree-merge-back`) 이 공유 — 한쪽만 바꾸면 desync. 검증 4건 + 판별 실패 AskUserQuestion 게이트 (조용한 최상위 fallback 금지). 기록 명령은 add 와 별도 Bash 호출 (훅 접두사 보존). 게이트 1건 재도입으로 Other 룰 (v2.1.1+) 재활성.
  - **회귀 패턴 표**: 한쪽 skill 만 변경 / 기록을 add 호출에 합침 (훅 사망) / 게이트 제거 후 최상위 fallback / 검증 ④ 제거 (stale 상속 자동 머지) — 4행.
  - **회귀 catch grep** (읽기 전용, 실제 경로):

    ```bash
    grep -lF "js-super-parent" skills/setting-up-worktrees/SKILL.md skills/worktree-merge-back/SKILL.md
    # expected: 2 lines
    grep -c "MAIN_INFO" skills/worktree-merge-back/SKILL.md
    # expected: 0
    grep -cF "판별 실패" skills/worktree-merge-back/SKILL.md
    # expected: >= 1
    test -f skills/worktree-merge-back/tests/H18-parent-branch/README.md && echo OK
    # expected: OK
    ```
  - **영향 범위**: 스킬 2 + 커맨드 2 + fixture 1 + CLAUDE.md. `worktree-remove` / og-* / auto-* / scripts / hooks 본문 영향 0 (훅은 접두사 계약만 재확인). 버전 bump 는 main 전용 룰.
- **RISK**: side-effect — eval 러너가 본 섹션의 bash 블록을 룰로 수집 (형식 어기면 조용히 누락)
- **Self-Review**: `# expected:` 가 각 명령 바로 뒤 / 쓰기 명령 없음 / 자리표시자 없음.

### Wave 2 — fixture (Task 2 결과물 대조 필요 — Wave 1 완료 후)

#### Task 5 — fixture H18-parent-branch 신규 (시나리오 6종)

- **Files**: `skills/worktree-merge-back/tests/H18-parent-branch/README.md` (신규)
- **Model**: sonnet (신규 한국어 시나리오 문서)
- **검증**: 파일이 존재하고 tech-design §7 의 시나리오 (a)~(f) 6종이 모두 있다. `test -f` + `grep -c "시나리오"` ≥ 1.
- **작업 내용**: 기존 fixture (H14-normal 등) 형식을 답습해 작성 — scratchpad 임시 저장소 셋업 (main → A 워크트리 → A 에서 B 재분기, 기록 심기) + 시나리오 6종:
  - (a) 재분기 + 기록 있음 → B 가 A 로 머지 + 스택 안내 출력 (최상위 미변경 확인)
  - (b) 기록 없음 (config 키 제거 후 실행) → 게이트 발동, 조용한 최상위 머지 없음
  - (c) 기록 있음 + 부모 브랜치 삭제 → 게이트 (사유: 부모 브랜치 삭제됨)
  - (d) 기록 있음 + 부모 워크트리 제거 (브랜치 존속) → 게이트 (사유: 부모 미체크아웃 — "중단" 후 부모 워크트리 재생성 경로 확인)
  - (e) 최상위 직계 + 기록 있음 → 최상위로 머지, 스택 안내 없음 (기존 동작 보존)
  - (f) 스킬 밖 동명 재생성으로 stale 기록 상속 (분기점 조상 아님) → 검증 ④ 가 게이트로 떨어뜨림
  - 각 시나리오에 기대 결과 + 확인 명령 명시. 저장소 커밋 대상은 README 뿐 (임시 저장소는 scratchpad).
- **RISK**: none (문서 신규)
- **Self-Review**: 기대 결과가 skill body (Task 2 결과물) 의 실제 문구와 어긋나지 않는지 대조 — 이 대조 때문에 본 task 는 Wave 1 과 병렬 불가.

### Wave 3 — 검증 (Wave 1~2 전체 완료 후)

#### Task 7 — [검증] 회귀 grep 전수 + 기존 결합 룰 재실행

- **Files**: 없음 (읽기 전용 검증)
- **Model**: haiku
- **검증**: 신규 grep 4건 (Task 6 수록분) + Task 1~4 의 검증 grep 전부 기대값 일치. 기존 결합 룰 — v2.5.1 (D-1 origin 0건 / D-2 재귀 머지 ≥1 / D-3 Step 4.5 ≥1 / D-5 HARD-GATE 2 skill) / v2.5.2 (Step 1 자동 커밋 ≥1 / 옛 종료 안내 0건 / 커밋 안 된 변경 ≥1) / `--no-ask` 비적용 (worktree-merge-back 0건) / 커맨드↔스킬 이름 충돌 검사 — 모두 기대값 유지. evals 룰 수집 `collect_rules` ≥ **149** (계획 작성 시점 기준선 145 + Task 6 신규 4건).
- **작업 내용**: 위 grep 들을 일괄 실행하고 PASS/FAIL 표로 보고. FAIL 시 해당 task 로 되돌아가 수정. 보고 끝에 릴리즈 후 `/reload-plugins` 필요 안내 1줄 포함 (§2 의 R4 mitigation — 플러그인은 캐시에서 로드되므로 머지·릴리즈 전까지 사용자 세션에 미반영).
- **RISK**: none

---

## §2. 위험 코드 지점 (tech-design §6 매핑)

- `skills/worktree-merge-back/SKILL.md` Step 2→3/4/4.5/5 변수 파급 — breaking: 교체 누락 시 단계별로 다른 대상 (mitigation: Task 2 Self-Review 의 `MAIN_*` 전수 grep 0 + Task 7 재확인) — R 대응: FR-4
- `skills/worktree-merge-back/SKILL.md` Step 4 pre-check — side-effect: 부모 리베이스·재작성 시 흡수 가정 깨짐 (mitigation: 기존 merge-base 검증 유지 — R1)
- `skills/worktree-merge-back/SKILL.md` Step 2 검증 ③ — side-effect: 부모 워크트리 부재 시 머지 실행 경로 없음 (mitigation: 게이트로 사용자 확인 — R2)
- `skills/worktree-merge-back/SKILL.md` Other 룰 · Process 헤더 — side-effect: "게이트 0건" 서술 잔존 시 문서 모순 (mitigation: Task 2 스텝 3 동기 — R3)
- `skills/setting-up-worktrees/SKILL.md` Step 4 기록 — side-effect: add 와 한 호출로 묶으면 memory-symlink 훅 미발화 (mitigation: 별도 후속 호출 명시 + Anti-Patterns 행 — 훅 결합)
- 동명 재생성 stale 상속 (R5, 수용) — mitigation: 검증 ④ + fixture (f) 문서화 (Task 5)
- 플러그인 캐시 반영 (R4) — mitigation: 릴리즈 후 `/reload-plugins` 안내 (Task 7 보고에 1줄)

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-08-29 09:18] [구현계획서-수정]
- **id**: CH-20260829-004
- **이유**: auto-writing-plans 최초 작성 — 슬림 plan (마크다운 본문 중첩 펜스로 `**원본**` 블록 생략, v2.5.1 선례) + task 7건 분해
- **무엇이**: 머지백-부모브랜치기준-implementation-plan.md 전체 (§1 Task 1~7 + §2 위험 코드 지점). plan_byte_check PASS (0 mismatches)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260829-002, CH-20260829-003

### [2026-08-29 09:18] [구현계획서-수정]
- **id**: CH-20260829-005
- **이유**: verifying-spec 무맥락 검증 지적 5건 채택 반영 (단독 5 — 대체 변수명 미정 / 게이트 탈출 경로 부재 / Wave 병렬 모순 / Task 7 누락 산출물 / 기준선 없는 검증)
- **무엇이**: Task 2 스텝 4 (`TOP_BRANCH` 신규 변수 명시 + 게이트 "중단" 옵션·탈출 경로) · Wave 재편 (Task 5 → Wave 2, Task 7 → Wave 3) · Task 7 (`/reload-plugins` 안내 1줄 + `collect_rules` 기준선 145→149 명시)
- **영향범위**: 실행 단계의 wave 순서와 Task 2/7 구현 내용
- **연관 항목**: CH-20260829-004

### [2026-08-29 09:33] [코드-수정] (batch: tasks 1..6)
- **id**: CH-20260829-006
- **이유**: `/merge-back-worktree` 의 머지 대상을 최상위 추론에서 생성 시 기록된 직계 부모 브랜치로 교체 (FR-1~5)
- **무엇이**: skills/setting-up-worktrees/SKILL.md, skills/worktree-merge-back/SKILL.md, commands/merge-back-worktree.md, commands/worktree.md, CLAUDE.md, skills/worktree-merge-back/tests/H18-parent-branch/README.md
- **영향범위**: 워크트리 생성·머지백 두 흐름. `worktree-remove` / og-* / auto-* / scripts / hooks 본문 영향 0
- **위험 카테고리**: breaking, side-effect
- **task별 세부 (6건)**:
  - Task 1: `skills/setting-up-worktrees/SKILL.md:31,164-178,220-231,254,292` — 신규 `-b` 분기 시 부모 기록 (config 키 2개), add 와 별도 Bash 호출 (훅 접두사 보존) (`side-effect`) — commit: `f3e3b24`
  - Task 2: `skills/worktree-merge-back/SKILL.md:3,8,12-14,44-48,90-132,133-243,256-258,304-312` — Step 2 판별 교체 (검증 4건 + 판별 실패 게이트) + Step 3/4/4.5/5 부모 기준 + 스택 안내 (`breaking`) — commit: `0077c53`
  - Task 3: `commands/merge-back-worktree.md:2,9` — 머지 대상 = 직계 부모 안내 동기 (`none`) — commit: `dc1d147`
  - Task 4: `commands/worktree.md:33` — 분기 부모 자동 기록 안내 1줄 (`none`) — commit: `7ceebfd`
  - Task 6: `CLAUDE.md` (append 40줄) — 결합 메모 신규 섹션 + 회귀 catch grep 4건 (`side-effect`) — commit: `34e0d5c`
  - Task 5: `skills/worktree-merge-back/tests/H18-parent-branch/README.md` (신규 197줄) — 판별 시나리오 6종 (`none`) — commit: `1b53932`
- **연관 commits**: `f3e3b24`, `0077c53`, `dc1d147`, `7ceebfd`, `34e0d5c`, `1b53932`
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회

### [2026-08-29 09:33] [검증] (task: Task 7 — 회귀 grep 전수 + 기존 결합 룰 재실행)
- **id**: CH-20260829-007
- **이유**: 신규 결합 룰 4건 + 기존 v2.5.1 / v2.5.2 결합 룰 + 커맨드↔스킬 이름 충돌 + 단위 테스트 재확인
- **무엇이**: 신규 4건 (js-super-parent 2파일 / MAIN_INFO 0 / 판별 실패 ≥1 / H18 fixture 존재), 기존 D-1·D-2·D-3·D-5, v2.5.2 Step 1 자동 커밋 3건, `--no-ask` 비적용, MAIN_* 잔존 0, 이름 충돌 0, Task 1~4 검증 grep, eval 결합 룰 수집, pytest
- **결과**: PASS — 신규 4건 전부 기대값 일치 (2 lines / 0 / 9 / OK). 기존 결합 룰 전부 유지 (origin 0, 재귀 머지 3, Step 4.5 8건, HARD-GATE 2 skill, Step 1 자동 커밋 1, 옛 종료 안내 0, `--no-ask` 0, MAIN_* 0). 커맨드↔스킬 이름 충돌 0. eval 결합 룰 145 → 155 (기대 ≥149). pytest 87 passed
- **연관 commit**: `1b53932` (마지막 코드 commit)
- **연관 항목**: CH-20260829-006
