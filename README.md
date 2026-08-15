<div align="center">

# js-super

### 프로덕션 코드를 안전하게 만들고 실용적으로 만드는 에이전틱 플러그인

머릿속 아이디어가 실제 코드가 되기까지, 매 단계마다 한 번 더 확인합니다.
**문서와 코드가 따로 놀지 않도록, AI 가 멋대로 진행하지 않도록.**

<br/>

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-2.9.0-7c3aed?style=for-the-badge&labelColor=0d1117">
  <img alt="Upstream" src="https://img.shields.io/badge/upstream-superpowers%205.0.7-f97316?style=for-the-badge&labelColor=0d1117">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge&labelColor=0d1117">
  <img alt="Language" src="https://img.shields.io/badge/lang-한국어-3b82f6?style=for-the-badge&labelColor=0d1117">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-Plugin-a78bfa?style=for-the-badge&labelColor=0d1117">
</p>

<p>
  <img alt="Commands" src="https://img.shields.io/badge/commands-24-06b6d4?style=flat-square&labelColor=0d1117">
  <img alt="Skills" src="https://img.shields.io/badge/skills-26-06b6d4?style=flat-square&labelColor=0d1117">
  <img alt="Zero deps" src="https://img.shields.io/badge/dependencies-zero-22c55e?style=flat-square&labelColor=0d1117">
</p>

<sub>upstream <a href="https://github.com/obra/superpowers">superpowers</a> 5.0.7 (MIT, Jesse Vincent) 의 프로덕션 안전성 확장</sub>

</div>

<br/>

---

## 이런 경험 있으세요?

<table>
<tr>
<td width="33%" valign="top">

#### "AI 가 코드만 던져요. 검토할 게 너무 많아요"

뭘 만들었는지, 왜 이렇게 했는지 따라가기 어려울 때.

**js-super 는** 단계마다 문서를 자동으로 정리해요. 요구사항 / 기술설계 / 구현계획이 각각 `.md` 로 쌓이고, 문서 하단에는 무엇이 왜 바뀌었는지가 자동으로 기록됩니다.

사람도 AI 도 같은 `.md` 를 봅니다. **검토 부담이 확 줄어요.**

</td>
<td width="33%" valign="top">

#### "이거 배포해도 괜찮나?"

위험한 부분이 어딘지, 어디서 깨질지 막막할 때.

**js-super 는** 위험한 코드 줄마다 `# RISK(...)` 주석을 자동으로 붙여 줍니다. 배포 직전에는 `/audit-risk` 한 줄로 보안 / 비용 / 거버넌스를 한 번 더 훑어볼 수 있어요.

</td>
<td width="33%" valign="top">

#### "AI 가 멋대로 진행해요"

되묻지 않고 코드를 갈아엎거나, 중요한 결정을 몰래 내릴 때.

**js-super 는** 단계마다 확인 게이트를 둡니다. *(v2.3.5+)* 자잘한 결정은 알아서, **위험한 결정만 사람에게** 물어봅니다.

</td>
</tr>
</table>

<br/>

---

## 전체 흐름 한눈에

```mermaid
flowchart LR
    classDef cmd fill:#7c3aed,stroke:#a78bfa,color:#fff,stroke-width:2px
    classDef doc fill:#1e293b,stroke:#06b6d4,color:#e2e8f0,stroke-width:2px
    classDef gate fill:#dc2626,stroke:#fca5a5,color:#fff,stroke-width:2px
    classDef out fill:#15803d,stroke:#86efac,color:#fff,stroke-width:2px

    A["/brainstorm"]:::cmd --> B[요구사항.md]:::doc
    B --> G1{확인 게이트}:::gate
    G1 --> C["/design-tech"]:::cmd
    C --> D[기술설계.md]:::doc
    D --> G2{확인 게이트 + 깊이 선택}:::gate
    G2 -->|3개 문서| E["/write-plan"]:::cmd
    G2 -->|2개 문서로 종료| Z[여기서 마무리 — 필요해지면 /write-plan 으로 승격]:::doc
    E --> F[구현계획.md]:::doc
    F --> G3{확인 게이트}:::gate
    G3 --> H["/execute-plan"]:::cmd
    H --> I[코드 + 변경이력 + 위험 주석]:::out
```

각 단계 사이 **확인 게이트** 에서 AI 가 한 번 멈춥니다. 다음 단계로 자동으로 넘어가지 않아요.

<br/>

---

## 1 분이면 시작합니다

**1. 설치** — Claude Code 안에서:

```
/plugin marketplace add LonerStayle/js-super
/plugin install js-super@js-super
```

세션 한 번 재시작하면 끝.

**2. 첫 피처 만들기** — 슬래시 4 줄로:

```
/brainstorm 사용자 잔액 출금 기능
/design-tech
/write-plan
/execute-plan
```

각 단계가 끝날 때마다 AI 가 한 번씩 물어봐요. 답변에 따라 다음 단계로.

<sub>산출물은 <code>docs/features/2026-05-23-사용자-잔액-출금/</code> 폴더에 2~3 개 <code>.md</code> 로 쌓입니다 (기술설계 게이트에서 구현계획까지 갈지 선택 — v2.9.0).</sub>

<br/>

---

## 서브에이전트 모드 — 계획서 그대로 복붙 + 의존그래프 자동 병렬

> *"피처가 커서 task 가 7-8 개인데, 하나씩 하면 시간 너무 걸려요"*
> *"근데 AI 가 코드 새로 짓는 건 더 무서워요. 계획 그대로만 했으면 좋겠어요"*

서브에이전트 모드는 두 가지 강력한 약속을 합니다.

**① 일꾼 AI 는 계획서를 그대로 복붙해요**

구현계획.md 의 task 마다 `**원본**` → `**수정본**` 변경이 적혀 있어요. 일꾼 AI 는 그 변경을 **한 글자도 안 틀리게 복사** 해서 실제 코드에 적용합니다. 자기 머리로 새 코드를 짓지 않아요. 의심스러우면 즉시 멈춥니다.

→ AI 가 계획에 없던 코드를 만들어서 깨지는 사고 **0**.

**② 의존그래프를 자동 분석해 wave 로 묶어 동시 처리**

7 개 task 를 무작정 7 개 동시에 돌리지 않아요. 먼저 task 사이 의존관계를 분석한 뒤 **wave 단위** 로 묶어 단계적으로 dispatch 합니다.

```mermaid
flowchart LR
    classDef wave fill:#1e293b,stroke:#06b6d4,color:#e2e8f0,stroke-width:2px

    subgraph W1["Wave 1 — 의존 없음, 동시"]
        direction TB
        T1["T1: User.balance 컬럼"]:::wave
        T2["T2: 마이그레이션"]:::wave
    end

    subgraph W2["Wave 2 — Wave 1 끝나야"]
        direction TB
        T3["T3: withdraw API"]:::wave
    end

    subgraph W3["Wave 3 — Wave 2 끝나야"]
        direction TB
        T4["T4: 라우트 등록"]:::wave
        T5["T5: 단위 테스트"]:::wave
    end

    W1 --> W2 --> W3
```

Wave 1 (T1+T2 동시) → Wave 2 (T3) → Wave 3 (T4+T5 동시). 순서가 꼬여서 깨질 일 없이, 안전한 범위에서 최대 병렬.

**③ 일꾼이 막히면 조정자가 먼저 복구 시도해요**

```mermaid
flowchart LR
    classDef main fill:#7c3aed,stroke:#a78bfa,color:#fff
    classDef sub fill:#1e293b,stroke:#06b6d4,color:#e2e8f0
    classDef block fill:#dc2626,stroke:#fca5a5,color:#fff

    P[구현계획.md]:::sub --> I["일꾼 (haiku)<br/>복붙 + 의존 분석"]:::sub
    I -->|성공| M[메인 AI]:::main
    I -.-> B(("막힘")):::block
    B -.->|자동 호출| R["조정자 (sonnet)<br/>복구 시도"]:::sub
    R -.->|복구| I
    R -.->|실패| M
```

<table>
<tr>
<td width="50%" valign="top">

**이렇게 동작해요**

- 일꾼은 계획서 변경을 **그대로 복붙** — 자기 머리로 코드 X
- task 의존그래프 자동 분석 → **wave 단위 병렬**
- 막혀도 조정자가 **자동 복구 먼저** 시도
- 그래도 안 되면 그제서야 사람에게

</td>
<td width="50%" valign="top">

**그래서 뭐가 좋아요?**

- 7 task → 3 wave 로 묶이면 **체감 시간 ⅓ ~ ½**
- 계획서가 기준 → **AI 멋대로 코드 짓는 사고 0**
- 의존 있는 건 **자동으로 순서대로** → race / 깨짐 차단
- 일꾼 = haiku (저렴) / 조정자 = sonnet (똑똑) → **비용·속도·안전 동시**

</td>
</tr>
</table>

<br/>

---

## 기획자가 새 요구사항을 추가해도, 3 개 문서가 같이 따라옵니다

> *"기획에서 갑자기 FR 하나 추가됐어요. 기술설계랑 구현계획도 다 다시 봐야 해요. 코드는 어디까지 영향 있는지도 모르겠어요"*

스펙은 살아있는 동안 계속 바뀝니다. 그때마다 3 개 문서를 손으로 정합 맞추는 건 사람의 일이 아니에요. **js-super 는 그걸 자동으로**:

```mermaid
flowchart LR
    classDef in fill:#7c3aed,stroke:#a78bfa,color:#fff
    classDef sub fill:#1e293b,stroke:#06b6d4,color:#e2e8f0
    classDef out fill:#15803d,stroke:#86efac,color:#fff

    A["요구사항.md<br/>FR-3 신규 추가"]:::in --> B[자동 영향 분석]:::sub
    B --> C{"기술설계<br/>영향?"}:::sub
    B --> D{"구현계획<br/>영향?"}:::sub
    B --> E{"이미 작성된<br/>코드 영향?"}:::sub
    C -->|YES| F["§4 갱신 제안"]:::sub
    D -->|YES| G["T7~T9 갱신 제안"]:::sub
    E -->|YES| H["해당 코드 위치 표시"]:::sub
    F --> I[사용자 확인]:::sub
    G --> I
    H --> I
    I --> J["3 개 md 동기화"]:::out
```

<table>
<tr>
<td width="50%" valign="top">

**자동으로 일어나는 일**

- 요구사항 수정 → 기술설계 / 구현계획 **둘 다** 영향 분석
- 이미 작성된 코드가 있다면 **어디서 깨질지** 위치 표시
- 사용자 확인 후 3 개 md 가 **한 번에 정렬**
- 각 문서 footer 에 **"왜, 언제, 무엇이 바뀌었는지"** 자동 기록

</td>
<td width="50%" valign="top">

**그래서 뭐가 좋아요?**

- 기획자 / PM 이 새 요구사항을 던져도 **3 개 문서가 따로 놀지 않음**
- 한 달 뒤에 본인이 다시 봐도 변경이력 footer 로 **맥락이 살아있음**
- PR 작성 직전, 머지 직전, 운영 중 어느 시점이든 **같은 흐름**
- 깜박하고 한 문서만 고쳐서 3 개 문서가 어긋나는 사고 차단

</td>
</tr>
</table>

<br/>

---

## 매일 쓰는 도구들

### `/auto-brainstorm` — 한 번에 끝까지 자동 진행

> *"4 단계마다 매번 게이트 답하기 무거워요. clarifying Q 만 답하면 끝까지 갔으면 좋겠어요"*

친숙한 영역 / 작은 ~ 중간 피처 / 빠른 prototype 일 때. 요구사항 → 기술설계 → 구현계획 → 실행까지 **4 단계 chain 을 자동으로** 돌리되, 변경이력 / 위험 주석 / 3 개 MD 산출물은 **그대로** 챙겨갑니다.

<table>
<tr>
<td width="50%" valign="top">

**이렇게 쓰세요**

```
/auto-brainstorm 사용자 잔액 출금 기능
```

→ AI 가 Socratic clarifying Q 1~5 개를 물어봐요.
→ 사용자는 답변만. 그 뒤로 모든 단계 자동 진행.

</td>
<td width="50%" valign="top">

**그래서 뭐가 좋아요?**

- 4 단계 게이트 자동 → **답할 게 clarifying Q 만**
- 변경이력 / 위험 주석 / 3 MD 산출물은 **그대로**
- 마지막에 wave-parallel 서브에이전트 자동 실행 → **속도까지**
- 친숙한 영역 / 작은 ~ 중간 피처에 최적

</td>
</tr>
</table>

<br/>

### `/fast-tasks` — 잡일 묶어 처리하기

> *"요구사항 문서부터 만들기엔 너무 작은 일인데, 그냥 시키기엔 변경이력은 남기고 싶어요"*

이슈 트래커에 쌓인 자잘한 fix 들. 의존성 업데이트. 같은 파일 안 작은 refactor 묶음.
**4 단계 풀 워크플로는 무겁고, 그냥 chat 으로 던지자니 흔적이 안 남는** 그 사이를 채웁니다.

<table>
<tr>
<td width="50%" valign="top">

**이렇게 쓰세요**

```
/fast-tasks
- 결제 API 응답 v1 → v2 호환 처리
- 로그인 폼 placeholder 한국어로
- requirements.txt requests 버전 bump
- README 의 v2.3.4 → v2.3.5
```

</td>
<td width="50%" valign="top">

**그래서 뭐가 좋아요?**

- 요구사항 / 기술설계 단계는 건너뜀
- 그래도 **변경이력 / 위험 주석 / 확인 게이트는 그대로**
- 한 task 끝날 때마다 footer 가 어지러워지지 않게, **마지막에 한 번에 정리**

</td>
</tr>
</table>

<br/>

### `/worktree` — 한 줄로 작업 공간 격리

> *"PR 리뷰하면서, 진행 중인 티켓도 보고, 가끔 긴급 hotfix 도 끼어들어요"*

한 코드베이스에서 여러 작업을 동시에 들고 있을 때. raw `git worktree add` 는 매번 `.env` 복사 / 빌드 / Claude 메모리 처리를 손으로 해야 합니다.
**`/worktree` 는 그걸 한 줄로**, 그리고 **Claude 메모리까지 자동으로 연결**해 줍니다.

<table>
<tr>
<td width="50%" valign="top">

**이렇게 쓰세요**

```bash
# 단수
/worktree GNG-432-캔버스첨부오류

# 복수
/worktree feature-a feature-b feature-c

# 자연어
/worktree
워크트리 3 개 만들어줘.
브랜치는 결제 / 정산 / 환불.
```

</td>
<td width="50%" valign="top">

**그래서 뭐가 좋아요?**

- `.env*` 파일을 **묻지 않고 자동 복사** → 빌드 / 서버 바로 실행 가능
- Claude 메모리가 **메인 ↔ 워크트리 양방향** 으로 연결됨 → 새 워크트리 첫 세션부터 컨텍스트 그대로
- `.gitignore` 도 알아서 처리
- 자연어로 "3 개 만들어줘" 한 줄도 OK

</td>
</tr>
</table>

<br/>

### `/merge-back-worktree` — main 더럽히지 않고 머지 준비

> *"feature 작업 1 주 했더니 main 이 멀리 갔어요. 머지하려니 충돌 무서워요"*

feature 브랜치가 오래 살면 main 이 앞으로 갑니다. 보통은 main 워크트리에서 `git merge feature` 하다가 거기서 충돌 나서 main 이 더러워지죠.
**`/merge-back-worktree` 은 거꾸로**, **feature 워크트리 안에서 main 을 당겨와 충돌을 거기서 해결**합니다.

<table>
<tr>
<td width="50%" valign="top">

**이렇게 쓰세요**

```bash
# feature 워크트리로 들어가서
cd .worktrees/GNG-432-캔버스첨부오류
/merge-back-worktree
```

이걸 하면 main 의 최신 변경을 이 워크트리로 당겨 옵니다. 충돌은 여기서만 일어나요.

</td>
<td width="50%" valign="top">

**그래서 뭐가 안전해요?**

- **main 워크트리는 손도 안 댑니다** — 충돌이 터져도 거긴 깨끗
- main 워크트리에 진입한 상태에서는 **호출 자체가 차단**됩니다
- 위험한 자동 해결 옵션 (`--strategy ours/theirs`) 은 **안 씁니다** — 한쪽 변경을 임의로 버리지 않음
- `git push --force` **금지** — remote main 도 안전
- 정리 (워크트리 삭제 / 브랜치 삭제) 는 **물어보고 진행**

</td>
</tr>
</table>

<br/>

### `/audit-risk` — 배포 직전 한 번 더 훑기

> *"배포 전에 보안 / 비용 한 번 점검하고 싶은데 시간이 없어요"*

프로젝트 크기에 맞춰 AI 1 명 또는 5 명이 코드를 훑고, 결과를 마크다운 보고서 한 장으로 정리합니다. 코드는 **건드리지 않아요**.

```mermaid
flowchart TD
    classDef main fill:#7c3aed,stroke:#a78bfa,color:#fff
    classDef sub fill:#1e293b,stroke:#06b6d4,color:#e2e8f0
    classDef out fill:#15803d,stroke:#86efac,color:#fff

    M[메인 AI]:::main
    A["API 비용 추정"]:::sub
    B["개인정보 노출"]:::sub
    C["민감 로직 검토"]:::sub
    D["AI 자동화 위험"]:::sub
    E["거버넌스 점검"]:::sub
    R["docs/audit/...md"]:::out

    M --> A & B & C & D & E
    A & B & C & D & E --> M
    M --> R
```

- 프로젝트 규모가 작으면 다섯 영역을 AI 1 명이 순서대로 훑는 방식으로 자동 전환됩니다
- Snyk, Bandit 같은 외부 보안 도구를 **대체하는 게 아니라 보완**합니다 (다른 각도로 catch)
- 보고서는 `.md` 한 장 — gitignored, 편집기에서 바로 읽고 이전 결과와 비교할 수 있습니다

<br/>

### `/new-skill` · `/list-skills` · `/remove-skill` — 나만의 skill 만들고 관리하기 *(v2.7+)*

> *"자주 반복하는 작업을 슬래시 명령 하나로 만들어 두고 싶어요"*

자유 텍스트 한 줄이면 `/new-skill` 이 `SKILL.md` 한 장을 자동으로 만들어 줍니다. 만들 위치는 **이 프로젝트만** 쓸지 **전체(글로벌)** 로 쓸지 매번 물어봐요.

<table>
<tr>
<td width="50%" valign="top">

**이렇게 쓰세요**

```
/new-skill PR 설명을 한국어로 요약해줘
/list-skills
/remove-skill pr-요약
```

→ `/new-skill` 은 프로젝트 / 전체 어디에 만들지 먼저 물어봅니다.

</td>
<td width="50%" valign="top">

**그래서 뭐가 좋아요?**

- `/new-skill` — 설명 한 줄 → skill 자동 생성, **스코프(프로젝트 / 전체) 선택**
- `/list-skills` — **js-super 가 만든 skill 만** 모아 보기 (현재 프로젝트 + 전체)
- `/remove-skill` — 기본은 안전한 rename 정리, **js-super 가 만든 것만** 대상
- 출처 표식이 있어 **다른 플러그인 / 직접 만든 skill 은 못 건드려요**

</td>
</tr>
</table>

<br/>

---

## 슬래시 명령 목록

### 워크플로

| 명령 | 결과물 | 한 줄 설명 |
|---|---|---|
| `/brainstorm <주제>` | `요구사항.md` | 소크라테스 대화 → 요구사항 정리 |
| `/design-tech` | `기술설계.md` | 요구사항 기반 기술 설계 |
| `/write-plan` | `구현계획.md` | task 단위로 잘게 쪼개기 |
| `/execute-plan` | 코드 + 흔적 | 인라인 / 서브에이전트 모드 선택 |
| `/auto-*` 4 개 | 같은 결과물 | 게이트 최소화 자동 진행 |
| `/og-*` 3 개 | upstream 흐름 | js-super 확장이 무겁다 싶을 때 |
| `/fast-tasks` | task list | 요구사항 문서 없이 잡일 묶어 처리 |

### 유틸리티

| 명령 | 한 줄 설명 |
|---|---|
| `/goodmorning` | 아침 브리핑 — 워크트리·세션 기록을 실행 시점에 수집해 위험 우선 보고 |
| `/audit-risk` | 규모에 맞춰 AI 1~5 명이 보안·거버넌스 점검 → 마크다운 보고서 |
| `/worktree <브랜치>` | 격리 작업 공간 + `.env*` + Claude 메모리 자동 |
| `/merge-back-worktree` | feature 워크트리 안에서 안전한 main 머지 |
| `/remove-worktree` | 현재 워크트리 + 브랜치 안전 정리 |
| `/new-skill <설명>` | 자유 텍스트 한 줄 → skill 자동 생성 (프로젝트 / 전체 선택) |
| `/list-skills` | js-super 가 만든 skill 만 조회 (프로젝트 + 전체) |
| `/remove-skill <이름>` | js-super 가 만든 skill 안전 정리 |
| `/pretty-md` | `.md` 본문 다듬기 (의미는 안 바꿈) |
| `/tech-teach-me` | 요구사항·기술설계·구현계획 문서를 강의로 쪼개 한 강씩 설명 |

<br/>

---

## 한 가지 작업, 두 가지 얼굴

<table>
<tr>
<td width="50%" valign="top" align="center">

#### `.md` — 진짜 문서

요구사항 / 기술설계 / 구현계획 각자 1 개씩.

문서 하단에 **누가 / 언제 / 왜 바꿨는지** 자동으로 쌓여요.

사람도 AI 도 이 `.md` 를 봐요.

</td>
<td width="50%" valign="top" align="center">

#### 코드 — 위험 주석

```python
# RISK(side-effect):
#   외부 결제 호출
#   by: /write-plan T5
```

3 가지 카테고리로 자동 부착.

PR 리뷰 시 `grep "# RISK"` 한 줄로 catch.

</td>
</tr>
</table>

<br/>

---

## 더 깊이 알고 싶다면

<details>
<summary><b>3 개의 <code>.md</code> 분리는 왜?</b></summary>

<br/>

한 피처가 한 폴더 안에 세 개의 `.md` 로 나뉘어 있어요.

```
docs/features/2026-05-23-잔액-출금/
├── 잔액-출금-requirements.md      ← /brainstorm
├── 잔액-출금-tech-design.md       ← /design-tech
└── 잔액-출금-implementation-plan.md ← /write-plan
```

- 날짜는 **생성일** — 작업이 길어져도 폴더명은 안 바뀝니다
- 세 문서가 같은 폴더라 PR 리뷰 한 곳에서 끝
- 각 문서 끝에는 변경이력 footer 가 자동 누적

</details>

<details>
<summary><b>변경이력은 어떻게 생겼나요?</b></summary>

<br/>

```markdown
## 변경이력

### CH-001 [요구사항-추가] 2026-05-23 14:30
- **이유**: 사용자가 출금 한도 추가 요청
- **무엇이**: FR-3 (1 일 출금 한도 100 만원) 신설
- **영향범위**: tech-design §4 / impl-plan T7~T9
- **연관 CH-id**: -
```

- 종류: `[요구사항-추가/수정/삭제]` / `[코드-수정]` / `[검증]` / `[릴리즈]`
- 코드 변경은 commit SHA 만 참조 (문서가 무거워지지 않게)
- 한 작업이 여러 task 로 나뉘어도 **마지막에 한 번에 footer 정리** *(v1.1.7+)*

</details>

<details>
<summary><b>위험 주석 3 종</b></summary>

<br/>

```python
# RISK(side-effect): 외부 결제 호출, 멱등성 미보장 — by /write-plan T5
def charge(user_id, amount):
    return payment_gateway.charge(user_id, amount)

# RISK(breaking): API v1 응답 구조 변경, v1 클라이언트 깨짐 — by /design-tech §3
def get_balance_v2(user_id) -> dict:
    ...

# RISK(race): 동시 출금 시 잔액 차감 충돌 가능 — by /design-tech §5
def withdraw(user_id, amount):
    balance = db.get_balance(user_id)
    ...
```

| 종류 | 무슨 뜻 |
|---|---|
| `side-effect` | 외부 호출 / DB 쓰기 / 파일 / 로그 |
| `breaking` | API 시그니처 / 응답 / DB 스키마 변경 |
| `race` | 동시성 / 트랜잭션 / 멱등성 |

</details>

<details>
<summary><b>확인 게이트 — 어디서 멈추나요?</b></summary>

<br/>

7 곳에서 멈춥니다. 모두 한국어로 묻고, **OS 알람**까지 울려서 자리에 없어도 catch 가능 *(v1.1.10+)*.

| 시점 | 게이트 |
|---|---|
| 요구사항 확인 | 예 / 아니오 |
| → 기술설계로 | (자동) |
| 기술설계 확인 | 예 / 아니오 |
| → 구현계획으로 | 예 / 아니오 |
| 구현계획 확인 | 예 / 아니오 |
| 실행 방식 | 인라인 / 서브에이전트 |
| 마무리 | 머지 / PR / 그대로 / 폐기 |

**v2.3.5+** — 실행 중에는 사소한 결정 (병렬로 할까? task 묶을까?) 은 자율 진행, **위험한 결정만 사람에게**:
- 실행 모드 변경
- 계획 밖 파일 손대기
- 파괴적 작업 (rm / reset / push --force)
- task 끼리 충돌
- 외부 서비스 호출 (push, PR 생성)
- 약속 안 한 새 의존성

</details>

<details>
<summary><b>문서 하나 바꾸면 아래도 같이 검토</b></summary>

<br/>

요구사항의 FR-3 가 수정되면, 자동으로 아래로 영향을 확인합니다.

```mermaid
flowchart LR
    A[요구사항 FR-3 수정] --> B[연쇄 영향 분석]
    B --> C{기술설계 영향?}
    B --> D{구현계획 영향?}
    B --> E{코드 영향?}
    C -->|YES| F[§4 갱신 제안]
    D -->|YES| G[T7~T9 갱신 제안]
    E -->|YES| H[해당 코드 위치 표시]
    F --> I[사용자 확인]
    G --> I
    H --> I
    I --> J[문서 일괄 갱신]
```

승인한 문서만 갱신되고, 각 문서 footer 에 변경 사유가 함께 기록됩니다.

</details>

<details>
<summary><b>서브에이전트 모드 — task 가 많을 때</b></summary>

<br/>

구현계획의 task 가 5 개 넘고 서로 독립적이면, **AI 여러 개가 병렬로** task 를 처리할 수 있어요.

```mermaid
flowchart LR
    classDef main fill:#7c3aed,stroke:#a78bfa,color:#fff
    classDef sub fill:#1e293b,stroke:#06b6d4,color:#e2e8f0
    classDef block fill:#dc2626,stroke:#fca5a5,color:#fff

    M[메인 AI]:::main
    P[구현계획.md]:::sub
    I["일꾼 (haiku)<br/>계획 그대로 실행"]:::sub
    R["조정자 (sonnet)<br/>막히면 복구 시도"]:::sub
    B((막힘)):::block

    M --> P --> I
    I -->|성공| M
    I -.-> B
    B -.->|자동 호출| R
    R -.->|복구| I
    R -.->|실패| M
```

- **일꾼 (haiku, 빠르고 저렴)** — 계획 그대로 실행. 의심스러우면 즉시 멈춥니다.
- **조정자 (sonnet, 똑똑)** — 일꾼이 막히면 자동으로 복구 시도. 그래도 안 되면 사람에게.
- 일반 `/execute-plan` (인라인) 은 영향 0 — 평소처럼 LLM 자율로 진행됩니다.

</details>

<details>
<summary><b>전체 Skill 26 개</b></summary>

<br/>

**워크플로 코어 (4)** — brainstorming / tech-design / writing-plans / executing-plans

**자동 흐름 (4)** *(v1.1.17+)* — auto-brainstorming / auto-tech-design / auto-writing-plans / auto-executing-plans

**upstream 원본 (커맨드 전용, v2.8.1+)** — `/og-brainstorm` / `/og-write-plan` / `/og-execute-plan` (스킬 → 커맨드 본문 인라인, 컨텍스트 미상주)

**문서 (3)** — code-pretty / glossary *(구현계획서 용어집)* / change-history

**검증·거버넌스 (4)** — verifying-spec / verification-before-completion / change-propagation / risk-annotation

**서브에이전트 (3)** — js-super-sub-driven / subagent-driven-development / dispatching-parallel-agents

**워크트리 (3)** — setting-up-worktrees / worktree-merge-back / worktree-remove

**테스트·디버깅 (2)** — test-driven-development / systematic-debugging

**리뷰·마무리 (3)** — requesting-code-review / receiving-code-review / finishing-a-development-branch

**메타 (1)** — using-superpowers

</details>

<br/>

---

## 필요한 도구 (사용자 환경)

| 용도 | 필요한 것 |
|---|---|
| Hook 처리 | `jq` 또는 `python3` (둘 중 하나) |
| Claude Code | 최신 버전 권장 |

> js-super 자체는 **외부 의존성 0**.

<br/>

---

## upstream superpowers 와의 관계

이 저장소는 [superpowers](https://github.com/obra/superpowers) v5.0.7 에서 갈라져 나온 포크에 **프로덕션 안전성 확장** 을 얹은 형태입니다 (v2.8.1 부터 og 스킬을 커맨드로 인라인하며 upstream 과 완전 분리). 단계별 확인 게이트 / 변경이력 자동 footer / 위험 주석 / 서브에이전트 wave-parallel 실행 / `.html` 다크 모드 사본 / 보안·거버넌스 감사 — 실무에서 발생하는 검토 부담 / AI 자동승인 폭주 / 문서·코드 정합 문제를 풀기 위한 확장입니다. 게이트 UI 는 한국어로 노출됩니다. upstream 업데이트는 수동 머지로 따라갑니다.

**`/og-*` — upstream 원본 흐름이 필요할 때**:

| 명령 | 산출물 위치 |
|---|---|
| `/og-brainstorm` | `docs/superpowers/specs/...` |
| `/og-write-plan` | `docs/superpowers/plans/...` |
| `/og-execute-plan` | (코드만) |

og-* 흐름은 변경이력 / 위험 주석 / 검증 게이트가 **안 따라옵니다**. upstream 그대로의 가벼운 흐름.

> **중요** — `/og-*` 와 정식 `/brainstorm` ... 흐름을 **한 피처 안에서 섞지 마세요**. 산출물 경로가 다르게 분리됩니다.

<br/>

---

## 버전 마일스톤

<details>
<summary><b>최근 (v2.x)</b></summary>

<br/>

| 버전 | 무엇이 바뀌었나요 |
|---|---|
| **v2.9.0** | 산출물 깊이 선택 (2~3 문서) + 구현계획서 테스트 자연어 축약 + `/goodmorning` 단일화 (goodnight 통합) + 워크트리 재분기·심링크 훅 안정화 |
| **v2.8** | `/goodnight` · `/goodmorning` 세션 핸드오프 + og 흐름 커맨드 전용화 |
| **v2.7** | skill 빌더 3종 고도화 — 생성 스코프(프로젝트 / 전체) + 출처 표식 + `/list-skills` 조회 |
| **v2.6** | `/new-skill` · `/remove-skill` — skill 만들고 정리하기 |
| **v2.5** | `--no-ask` 모드 + `/remove-worktree` 워크트리 정리 |
| **v2.4** | 한국어 친화 안내 톤 |
| **v2.3.5** | 실행 중 자잘한 재질문 줄임, 질문할 땐 알람 보장 |
| **v2.3.0** | `/audit-risk` 보안·거버넌스 1 회 감사 |
| **v2.1.0** | `/fast-tasks` 잡일 묶어 처리 |
| **v2.0.4** | `/merge-back-worktree` 안전한 머지 |
| **v2.0.0** | 서브에이전트 병렬 모드 |

<sub>v2.2 ~ v2.8.2 에 걸쳐 있던 <code>.html</code> 사람용 사본 기능 (<code>generating-html</code> 스킬 · <code>/sync-html</code> 명령) 은 이후 제거됐습니다. 산출물은 <code>.md</code> 로 통일됩니다.</sub>

</details>

<details>
<summary><b>이전 (v1.x)</b></summary>

<br/>

| 버전 | 무엇이 바뀌었나요 |
|---|---|
| **v1.1.17** | `/auto-*` 4 개 자동 흐름 |
| **v1.1.10** | 게이트 한국어화 |
| **v1.1.7** | 변경이력 마지막에 한 번에 정리 |
| **v1.1.5** | 워크트리 ↔ 메인 메모리 자동 연결 |
| **v1.1.0** | PRD / 자유 모드 선택 |
| **v1.0.0** | 3-MD 분리 + 변경이력 + 위험 주석 |

</details>

<br/>

---

<div align="center">

### 라이선스

**MIT** (upstream superpowers 와 동일)

<br/>

<sub>버그 / 제안: <a href="https://github.com/LonerStayle/js-super/issues">GitHub Issues</a></sub>

<br/>

<sub>프로덕션 Claude Code 워크플로우를 위해</sub>

</div>
