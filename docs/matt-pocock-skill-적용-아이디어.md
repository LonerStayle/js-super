# Matt Pocock「좋은 스킬 체크리스트」— js-super 적용 아이디어

> 출처: <https://www.youtube.com/watch?v=YLq04CDeOTE> (자막 정리본 `matt-pocock-good-skills.md`)
> 분석 대상: 이 저장소 (js-super, Superpowers 포크) skill 33개 + command 27개
> 작성일: 2026-07-18 · **개정: 최근 머지 내용(프롬프트가공 · 미라클모닝 · update-claude-md) 반영**

---

## 0. 한 줄 요약 — 개정판

Matt의 4단계(**트리거 · 구조 · 유도 · 가지치기**)는 훌륭한 **진단 렌즈**입니다.

첫 분석은 "js-super가 무엇을 해야 하나"였습니다. 그런데 최근 머지를 반영하니 그림이 바뀝니다 — **js-super는 이미 Matt 방향으로 움직이고 있습니다.** 프롬프트 65개를 검토해 정합화했고(프롬프트가공), 죽은 프롬프트를 실제로 삭제했고, 새 커맨드는 user-invoke 전용으로 만들기 시작했습니다.

그래서 개정판의 질문은 바뀝니다: **"무엇을 시작할까"가 아니라 "얼마나 왔고, 무엇이 남았나."**

---

## 0.5 최근 머지가 바꾼 그림 — 이미 움직이고 있다

세션 시작(`170e0b0`) 이후 이 워크트리에 머지된 내용 중 Matt 체크리스트와 직결되는 것:

| 머지 | 무슨 일 | Matt 체크리스트 연결 |
|---|---|---|
| **프롬프트가공** (`889c1dc`) | 프롬프트 **65개** 서브에이전트 검토 → **188건** 발견 → 정답 명확한 것만 수정 | **④ 가지치기** — 체계적 정합화 패스 실행 |
| 〃 | `generating-html` **죽은 A 프롬프트 삭제** (287→223줄, **−64**) | **④ 삭제 테스트** 실전 |
| 〃 | `docs/reviews/` 검토·재검토·적용요약 3종 기록 | **④ 가지치기 커밋 문화** 시작 |
| **미라클모닝** (v2.8.0) | `/goodnight`·`/goodmorning` 신규 — 둘 다 `disable-model-invocation: true` | **① 트리거** — user-invoke 전용 채택 |
| **update-claude-md** | `/update-claude-md` 신규 — `disable-model-invocation: true` + CLAUDE.md 구체값 자동 검증·갱신 | **① 트리거** + **가지치기 자동 유지보수** |

핵심: **프롬프트가공은 Matt의 "관찰 → 처방 → 압축 → 삭제" 회로를 그대로 한 바퀴 돈 것**입니다. 65개를 서브에이전트로 검토하고, 188건 중 "정답이 명확한 것만" 고친 절제까지 Matt의 삭제 테스트 철학과 같습니다.

---

## 1. 실측 현황 (개정 — 축소와 순증이 공존)

| 항목 | 수치 | 의미 |
|---|---|---|
| 확장 vs 원본 크기 | brainstorming 641 vs 170 (**3.8×**) · writing-plans 530 vs 174 (**3.0×**) · executing-plans 383 vs 81 (**4.7×**) | 큰 skill은 여전히 3~5배 |
| **generating-html 축소** | 287 → **223줄 (−64)** | 죽은 프롬프트 삭제 — 삭제 테스트 실전 |
| 그 외 skill 순증 | brainstorming 631→641, tech-design 402→405 등 | 정합화하며 새 룰도 추가돼 **총량은 오히려 증가** |
| 본문 속 버전 마커 | sub-driven 30 · tech-design 24 · generating-html 21 | changelog가 여전히 본문 상주 |
| 참고파일 분리 | **36개** | 구조 원칙은 잘 지키는 중 |
| **커맨드 user-invoke 전환** | **3 / 27** (`disable-model-invocation: true`) | ① 트리거 착수 — 신규 3종만, 24개는 백로그 |

**한 줄 판정**: js-super는 **삭제도 하고(generating-html) 순증도 합니다(큰 skill들).** 문제는 "가지치기를 안 한다"가 아니라 **"성장 속도를 가지치기가 못 따라간다"** 입니다. 정확히 Matt가 말한 증상입니다.

---

## 2. 체크리스트별 진단 + 아이디어 (개정)

### ① 트리거 — 누가 부르나 (★ 이미 착수)

**Matt**: user-invoke는 예측 불가능성 + eval 부담을 통째로 제거한다. 그래서 대부분 user-invoke로 만든다.

**js-super 현황 (개정)**
- commands ↔ skills 두 층 구조는 여전히 강점(grill-me/grilling 패턴).
- **신규 3종(`goodnight`·`goodmorning`·`update-claude-md`)이 `disable-model-invocation: true` 채택** — Matt의 처방을 프로젝트가 관례로 굳히기 시작. description에도 "발동조건 문구"를 빼는 방향.
- 하지만 **27개 중 3개만** 전환됨. 나머지 24개(brainstorm·tech-design·auto-* 등)는 아직 model-invoke 여지.

**아이디어 (개정)**
- **T1 (진행 중 → 완주)**: `disable-model-invocation: true` 전환을 나머지 24개로 확장. 신규 3종이 레퍼런스. "명시 호출 전용 + description에 발동조건 문구 X"를 커맨드 표준으로.
- **T2**: 그래도 model-invoke를 유지할 skill(brainstorming 등)은 description을 트리거 신호만 남기고 다이어트.

### ② 구조 — 본문은 작게 (★ 부분 실행)

**Matt**: 가끔 쓰는 참고자료는 본문 밖으로. 본문엔 "필요하면 이 파일 봐라" 한 줄만.

**js-super 현황 (개정)**
- 참고파일 36개 분리 + **generating-html에서 죽은 프롬프트 −64줄 삭제** = 구조·삭제 둘 다 실행한 사례.
- 그러나 큰 skill 본문은 여전히 버전 마커·coupling 메모로 순증.

**아이디어**
- **S1**: generating-html 사례를 다른 큰 skill로 확대 — 본문 속 `vN.N+` 마커를 `RELEASE-NOTES.md`로. **단** grep 회귀 catch 의존 마커는 load-bearing → 신호 교체 + atomic patch 필수.

### ③ 유도 — 강한 단어 · 미래 숨기기 (변동 없음)

**js-super 현황**
- brainstorm→design→plan→execute **4분할**이 "미래를 숨긴다"를 정확히 구현. (강점 유지)
- **긴장**: auto-flow 체인은 반대로 4단계를 광고 → "목표 보이면 서두른다" 재도입 위험.

**아이디어**
- **E1**: 약한 문장 → 모델이 아는 강한 용어로 압축 (vertical slice, code smell, seam 등).
- **E2**: 프롬프트가공이 이미 서브에이전트 검토를 했으니, 여기에 **reasoning trace 검증**(심은 단어가 사고 과정에 되돌아오는지)을 얹으면 유도 효과를 계량 가능.

### ④ 가지치기 — 핵심 재평가 (★ 실행 중이나 성장에 뒤짐)

**첫 분석의 오해 정정**: "js-super는 중복만 쌓는다"는 틀렸습니다. **프롬프트가공(65개 검토·188건 발견)과 generating-html 삭제**가 증거입니다. js-super는 가지치기를 **합니다.**

**진짜 문제 = 속도 불균형**
- 삭제(generating-html −64)보다 순증(brainstorming +10, 새 커맨드 3종, 새 룰)이 빠름.
- 의도적 중복(Checklist ×14, `--no-ask` ×8 등)은 여전히 유효 — 사용자 환경에 CLAUDE.md가 안 전달되므로 skill 본문 복제는 필요. 함부로 못 지움.

**아이디어**
- **P1**: 프롬프트가공의 "188건 발견 → 정답 명확한 것만 수정" 패턴을 **정기화**. 남은 미수정 건(188 − 수정분)을 백로그로.
- **P2 (안전한 삭제 타깃)**: 중복 boilerplate 말고 **버전 마커·자명한 지시 문장**을 삭제 테스트로. red-flag 표·rationalization 목록은 eval 없이 금지(CLAUDE.md).

---

## 3. 놓친 한 가지 — context.md 도그푸딩 (여전히 없음)

**Matt**: 레포 루트에 `context.md` 용어집 — 자기 skill이 가르치는 "용어 통일"을 자기 레포에 먼저 적용.

**js-super 현황 (개정)**
- `context.md` **여전히 없음** (실측 확인).
- 다만 인접 유지보수 도구는 생김: `/update-claude-md`(CLAUDE.md 구체값 자동 검증), `/goodnight`·`/goodmorning`(세션 핸드오프). **"자기 문서를 자동 관리한다"는 도그푸딩의 절반은 시작**된 셈.
- 내부 용어(wave-parallel, byte-copy, fire-and-forget, critical/non-critical...)는 아직 CLAUDE.md 결합 메모에 흩어짐.

**아이디어**
- **G1 (여전히 1순위)**: 루트 `context.md` 용어집 신설. `/update-claude-md`가 이미 "구체값 자동 검증"을 하니, **G1 + update-claude-md를 묶어 "용어집도 자동 검증 대상"으로** 확장하면 도그푸딩이 완성된다.

---

## 4. 우선순위 (개정 — 착수분 반영)

| 순위 | 아이디어 | 상태 | 노력 | 위험 |
|---|---|---|---|---|
| 1 | **T1** disable-model-invocation 전환 24개 완주 | **진행 중** (3/27) | 중간 | 낮음 |
| 2 | **G1** context.md 용어집 (+ update-claude-md 연동) | 미착수 | 낮음 | 낮음 |
| 3 | **P1** 프롬프트가공 "188건" 백로그 정기 소진 | **1회 실행됨** | 중간 | 중간 |
| 4 | **T2** model-invoke description 다이어트 | 미착수 | 낮음 | 낮음 |
| 5 | **E1·E2** 강한 단어 + trace 검증 | 미착수 | 중간 | 중간 |
| 6 | **S1** 버전 마커 → RELEASE-NOTES (큰 skill로 확대) | generating-html만 | 중간 | **높음** |

---

## 5. 하지 말 것 / 함정 (유지)

- Matt의 "가지치기"를 **compliance 리팩터**로 오해해 red-flag 표·rationalization 목록·"human partner" 표현을 건드리지 말 것 (CLAUDE.md가 eval 없이 금지).
- `og-*` skill 본문은 upstream mirror — 손대지 말 것.
- 의도적 중복을 "중복이니까"라는 **단독 근거**로 지우지 말 것.
- skill 행동 변경은 `writing-skills` + 서브에이전트 압박 테스트로 eval 후 진행. (프롬프트가공이 이미 이 방식 — 답습하면 됨.)

---

## 6. 한 줄 결론 (개정)

> js-super는 Matt 체크리스트를 **몰라서 안 한 게 아니라, 이미 한 바퀴 돌고 있었습니다.** ① 트리거는 신규 커맨드부터 user-invoke로 전환 착수, ④ 가지치기는 프롬프트가공으로 65개를 훑었습니다. 남은 일은 **전환 완주(3→27)**, **놓친 context.md**, 그리고 **성장 속도를 가지치기가 따라잡게 만드는 정기화**입니다.
