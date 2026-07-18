# 강한 단어 유도 기법 — eval 계획서

> 출처 인사이트: Matt Pocock 「좋은 스킬」 발표 (`matt-pocock-good-skills.md`)
> 상위 분석: `docs/matt-pocock-skill-적용-아이디어.md`
> 작성: 2026-07-18 · 상태: **미실행 (나중에 진행)**

---

## 0. 한 줄 가설

> **긴 설명 < 강한 단어.** 행동을 문단으로 설명하는 것보다, 모델이 이미 학습한 정확한 용어 하나를 심는 게 더 강하게 행동을 유도한다. 그리고 그 효과는 **추론 과정(reasoning trace)에 그 단어가 되돌아오는지**로 검증할 수 있다.

이 문서는 그 가설을 js-super에서 **실제로 검증**하기 위한 eval 설계다. 결과가 유의미하면 적용, 무차이면 접는다.

---

## 1. 메커니즘 (왜 먹히나)

- `vertical slice`, `blast radius` 같은 용어는 소프트웨어 공학에서 수십 년 쓰였다 → **모델 학습 데이터에 깊게 박힘.**
- 그 단어를 심으면, 단어에 딸린 **행동 뭉치 전체**가 통째로 딸려온다.
- 반대로 문단은 그냥 문장이라 모델이 매번 새로 해석해야 하고, 길수록 놓칠 확률이 커진다.
- 검증이 되는 게 핵심 — 문단은 "먹혔는지" 알 방법이 없지만, 단어는 추론 과정에 다시 나타나는지로 확인 가능하다.

---

## 2. js-super 현황 (실측)

### 이미 강한 단어를 쓰는 곳 (재추가 금지 — 이미 있음)

| 단어 | 위치 | 불러오는 행동 |
|---|---|---|
| `blast radius` | `executing-plans:310`, `js-super-sub-driven:471` | "이 변경이 얼마나 번지나" |
| `single source of truth` | `writing-plans:113`, `executing-plans:115`, `generating-html:120` | "정답 위치는 한 곳" |
| `idempotent` | `code-pretty:3,232`, `setting-up-worktrees:192,205` | "두 번 돌려도 같은 결과" |
| `happy path` | `api-auto-testing:100` | "정상 흐름 먼저" |

→ 결론: js-super는 이 기법을 **이미 절반은 쓴다.** 순진하지 않음.

### 약한 단어 지점 (1차 후보)

| 현재 단어 | 위치 | 부족한 의미 |
|---|---|---|
| `bite-sized` | `writing-plans:30,125`, `executing-plans:20` | 크기(작게)만 지정. **모양(위→아래 완결·실행가능)은 미지정** |

`bite-sized`만 있으면 에이전트가 **작은 층별 조각**(작은 DB task, 작은 API task)을 만들 수 있다 — Matt가 경고한 horizontal 실패 모드. `vertical slice`는 그 여지를 막는다.

---

## 3. 1차 후보 변경 (before / after)

> 원칙: `bite-sized`를 **교체**하는 게 아니라 **강한 단어를 더한다** (크기 + 모양 둘 다 지정).

**Before** (`writing-plans:125` 부근, 현행):
```
## Bite-Sized Task Granularity (inherited from upstream)
... decompose into bite-sized TDD tasks ...
```

**After** (후보안 — 실험용):
```
## Bite-Sized, Vertical-Slice Task Granularity
Decompose into bite-sized TDD tasks. Each task MUST be a thin **vertical slice** —
a small cut that runs end-to-end (data → logic → surface), not a horizontal layer
(all-DB, then all-API, then all-UI). A task that only touches one layer is a red flag.
```

핵심은 `vertical slice` + `end-to-end` + `horizontal layer` 대비를 심는 것. 단어 3개로 행동을 유도.

---

## 4. eval 프로토콜

### 셋업

- **대상 skill**: `writing-plans` (1차). 통과하면 `executing-plans`로 확장.
- **테스트 입력**: 레이어가 뚜렷한 대표 요청 1~2개. 예: "React 투두 앱 (API + DB + 화면)", "회원가입 API + 이메일 인증".
- **실행 방식**: js-super의 기존 방법론 답습 — `writing-skills` + 서브에이전트 압박 테스트. 각 arm N=5회.

### 두 갈래 (A/B)

| Arm | 내용 |
|---|---|
| **A (대조군)** | 현행 `writing-plans` (`bite-sized`만) |
| **B (실험군)** | §3 After 안 (`+ vertical slice`) |

### 측정 지표

| 코드 | 지표 | 기대 |
|---|---|---|
| **M1 (trace)** | 추론 과정에 `vertical slice` / `thin slice` / `end-to-end` 개념이 등장하는가 | B에서만 등장 |
| **M2 (구조)** | 생성된 plan의 task들이 vertical(각 task가 위→아래 완결·실행가능)인가 vs horizontal(레이어별)인가 — task 제목·내용 분류 | B의 vertical 비율 ↑ |
| **M3 (실행가능성)** | **첫 task만** 구현해도 돌아가는 산출물이 나오는가 | B에서 상승 |

M2 분류 기준(각 task 라벨링):
- **vertical** = 한 기능이 data→logic→surface를 관통 (예: "투두 1개 추가 — 모델+엔드포인트+버튼")
- **horizontal** = 한 레이어만 (예: "모든 DB 스키마 작성", "모든 API 작성")

---

## 5. 합격 / 불합격 기준

- **합격**: B가 A 대비 **M2 vertical 비율이 뚜렷이 상승** + **M1 등장**. → `writing-plans`에 적용, `executing-plans`로 확장.
- **애매**: M1은 등장하나 M2 무차이. → 단어를 더 강한 것으로 교체 재실험 (예: `walking skeleton`, `tracer bullet`).
- **불합격**: A/B 무차이. → **접는다.** 억지 적용 금지.

---

## 6. 확장 후보 백로그 (2차 — 1차 통과 시 스캔)

다른 skill에서 "약한 문단 → 강한 단어" 후보를 훑을 대상:

- [ ] `systematic-debugging` — "근본 원인 찾기" 설명이 긴가? → `root cause` / `rubber duck` / `bisect`
- [ ] `test-driven-development` — 회귀 방지 설명 → `characterization test` / `regression`
- [ ] `receiving-code-review` — "맹목 수용 말고 검증" → 이미 강한 표현 있는지 확인
- [ ] `brainstorming` (631줄) — 긴 설명 문단이 강한 단어로 압축 가능한지 (bloat 1순위)
- [ ] `verifying-spec` — "증거 먼저" → `evidence before assertion` 이미 있음?

각 후보: 먼저 "이미 강한 단어 쓰는지" 확인 → 없으면 §4 프로토콜 축소판 적용.

---

## 7. 제약 / 주의 (반드시 지킬 것)

- **정밀 보강이지 혁명 아님.** 1차는 사실상 `writing-plans` 한 곳. 기대치를 그렇게 잡을 것.
- **upstream 상속 텍스트다.** `bite-sized`는 `writing-plans:125` "inherited from upstream". og-* mirror 룰과 별개지만, upstream 패턴 수정은 eval 근거 없이 하지 말 것 (CLAUDE.md).
- **red-flag 표 / rationalization 목록 / "human partner" 표현은 건드리지 말 것** — eval 없이 금지 (CLAUDE.md).
- **eval 선행.** 이 문서의 §3 After는 "후보안"이지 확정안 아님. §4를 돌린 뒤 결정.
- **trace 검증은 grep과 다르다.** "파일에 문장 있나"(정적)가 아니라 "에이전트가 그 개념을 실제로 썼나"(행동)를 본다. js-super에 없는 방식이라, eval 인프라를 이 기회에 같이 만들 수 있음.

---

## 8. 참고 (출처)

- 인사이트: `matt-pocock-good-skills.md` (`03:19`~`04:37` — vertical slice + trace 검증 구간)
- 실측 근거: `grep -rniE "vertical slice|blast radius|idempotent|bite-sized" skills/*/SKILL.md` (2026-07-18)
- 방법론: `skills/writing-skills/SKILL.md` + `skills/writing-skills/testing-skills-with-subagents.md`
