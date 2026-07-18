# og-* 완전 분리 + auto-* 자동발동 차단 — 실행 기록

> 배경: Matt Pocock ① 트리거 원칙 + 사용자 관례(커맨드는 `disable-model-invocation: true`) + 컨텍스트 절감
> 상위 결합 메모: `CLAUDE.md` "## og-* upstream 완전 분리 — 커맨드 인라인 (v2.8.1+)"
> 작성: 2026-07-18 · 상태: **적용 완료 (미커밋)**

---

## 0. 핵심 개념 — 스킬 vs 커맨드의 컨텍스트 비용

| | 상주하나? | 자동 체인 가능? |
|---|---|---|
| **스킬** (Skill 도구) | 항상 상주 (description 매 세션 로드) | O — 스킬끼리 이름으로 호출 |
| **커맨드** (SlashCommand, `disable-model-invocation`) | 미상주 (호출 때만 로드) | X — 모델이 다음 커맨드 자동 호출 불가 |

→ "컨텍스트에서 빼기 + 커맨드 전용" 을 진짜 하려면 **스킬을 없애고 커맨드 본문에 넣어야** 한다. 대신 자동 체인은 포기(수동 진행). 둘 다는 불가능.

---

## 1. og-* — 완전 분리 (스킬 삭제 + 커맨드 인라인)

og 는 단계마다 사용자 리뷰가 자연스러워 **수동 체인이 오히려 적합** → 완전 분리 채택.

### 변경 (커맨드 3 인라인 + 스킬 3 삭제 + router 전환)

| 파일 | 변경 |
|---|---|
| `commands/og-brainstorm.md` | 원본 brainstorming 절차 전체 인라인 (187줄) + `disable-model-invocation: true` |
| `commands/og-write-plan.md` | 원본 writing-plans 절차 인라인 (195줄) + 플래그 |
| `commands/og-execute-plan.md` | 원본 executing-plans 절차 인라인 (100줄) + 플래그 |
| `skills/og-brainstorming/` | **삭제** |
| `skills/og-writing-plans/` | **삭제** |
| `skills/og-executing-plans/` | **삭제** |
| `skills/brainstorming/SKILL.md` | Entry Router: "small 신호 → og-brainstorming skill auto-invoke" → "`/og-brainstorm` 실행 **안내**" (자동 invoke 제거) |
| `README.md` | Skill 목록 32→29, og 3종 → 커맨드 전용 표기 |
| `CLAUDE.md` | 완전 분리 결합 메모 (mirror 룰 og 한해 폐기) |

### 스킬 참조 치환

- `invoke og-writing-plans skill` → `run /og-write-plan`
- og 단계 자동 체인(스킬→스킬) → 각 커맨드 끝에서 "다음 커맨드 실행 안내" (수동)

### 결과 (트레이드오프)

- 자동 체인: **수동** (사용자가 다음 커맨드 실행)
- 컨텍스트 상주 비용: **없음** ✅
- 모델 오발동: **차단** (커맨드 플래그 + router 안내화)

### upstream untouched 스킬 참조는 유지

`subagent-driven-development` / `finishing-a-development-branch` / `using-git-worktrees` 는 js-super 가 안 건드린 원본 → og 커맨드가 그대로 참조.

### 검증 grep (전부 통과)

```bash
grep -lF "disable-model-invocation: true" commands/og-brainstorm.md commands/og-write-plan.md commands/og-execute-plan.md   # 3
grep -nE "Skill tool.*og-|invoke .*og-(brainstorming|writing-plans|executing-plans) skill" commands/og-*.md                 # empty
ls -d skills/og-* 2>/dev/null                                                                                                # 없음
grep -rn "og-brainstorming\|og-writing-plans\|og-executing-plans" skills/ | grep -v "/tests/"                                # empty
grep -c "Advise: run /og-brainstorm" skills/brainstorming/SKILL.md                                                           # 3
grep -c "Auto-invoke og-brainstorming" skills/brainstorming/SKILL.md                                                         # 0
```

---

## 2. auto-* — 자동발동 차단만 (스킬 유지, 그대로 둠)

auto 는 서로를 **스킬 이름으로** 부르는 체인이라 스킬을 지우면 체인이 끊긴다. 자동 체인을 유지하기로 결정 → **완전 분리 안 함.** (사용자 결정: "냅두자")

### 변경 (커맨드 4 플래그 + 스킬 4 description)

| 층 | 변경 |
|---|---|
| 커맨드 4종 | `disable-model-invocation: true` — 모델 자동 발동 차단 |
| 스킬 진입 1 (`auto-brainstorming`) | "명시 호출 전용 — 자동 선택 금지 (기본 진입은 brainstorming)" |
| 스킬 체인 3 | "커맨드 또는 앞 단계의 명시 invoke 로만 진입, 자유 요청에서 자동 선택 금지" (체인 보존 문구) |

### 체인 안전성

`disable-model-invocation` 은 SlashCommand 도구만 막는다. 체인은 Skill 도구로 스킬 이름 호출(`js-super:auto-tech-design` invoke) → **영향 없음, 체인 그대로.**

### 결과

- 자동 체인: **자동** (스킬→스킬 그대로)
- 컨텍스트 상주 비용: **있음** (스킬 유지 → description 상주)
- 모델 오발동: **차단**

### auto 도 컨텍스트 0 으로 빼려면

4단계 체인 + 내부 스킬 호출(verifying-spec / change-history / generating-html) + CLAUDE.md 결합 룰을 커맨드로 합치는 큰 재구성 필요. **보류** (사용자 결정).

---

## 3. og vs auto 최종 상태

| | 자동 체인 | 컨텍스트 비용 | 오발동 차단 |
|---|---|---|---|
| **og** (완전 분리) | 수동 | 없음 ✅ | 됨 |
| **auto** (스킬 유지) | 자동 | 있음 | 됨 |

---

## 4. 남은 일 (사용자 판단)

- **manifest 버전 bump** (6종, 2.8.0 → 2.8.1) + commit — 릴리즈 의식 별도. 지금 미적용.
- **행동 검증 (권장)**: `/og-brainstorm` 실행 시 인라인 절차대로 동작하는지, "브레인스토밍 하자"에 `brainstorming` 이 뜨고 삭제된 og 스킬을 안 부르는지 확인.
- **test fixtures 정리 (후속)**: `skills/js-super-sub-driven/tests/H1/H2/H13` README 가 옛 og 라우팅 명칭 참조 — 실행 무관 문서, 후속 정리.
