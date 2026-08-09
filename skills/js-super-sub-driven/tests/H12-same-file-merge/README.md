# H12 — Same-file mechanical 묶음 룰 dogfood

**v2.0.1+ — D1 3 조건 AND 룰 검증**

## 시나리오 (positive case)

가상 Android Compose chat 화면 피처. `/auto-write-plan` 발화 → 다음 변경들 plan 작성:

1. `ChatScreen.kt` — Scaffold contentWindowInsets + imePadding
2. `ChatScreen.kt` — 자동 스크롤 (`LaunchedEffect(messages.size)`)
3. `ChatScreen.kt` — BackHandler (drawer-우선)
4. `ChatScreen.kt` — 빈 화면 placeholder + 예시 prompt 3

## 기대 결과 (D1 3 조건 적용)

- (1) 같은 파일 ✅ — 4 변경 모두 ChatScreen.kt
- (2) 테스트 경계 X ✅ — 한 화면 통합 preview 로 검증
- (3) mechanical ✅ — Scaffold 옵션 / LaunchedEffect / BackHandler / placeholder 모두 mechanical

→ 4 변경 → **1 task multi-step** 으로 묶음:

```
Task N: ChatScreen 화면 4 변경
  Files: ChatScreen.kt
  Model: sonnet
  - step 1: 검증 설명 기반 통합 테스트 작성 + FAIL 확인 (실행 단계 수행, v2.9+)
  - step 2: Scaffold contentWindowInsets Edit
  - step 3: LaunchedEffect 자동 스크롤 Edit
  - step 4: BackHandler Edit
  - step 5: placeholder Edit
  - step 6: test 실행 → pass
  - step 7: self-review
```

→ wave-parallel 효과 회복 (4 wave 직렬 → 1 wave 1 task).

## 시나리오 (negative case — 분리 강제)

5번째 변경 추가 — `ChatScreen.kt` 메시지 정렬 알고리즘 변경 (시간순 → priority).

- (1) 같은 파일 ✅
- (2) 테스트 경계 ❌ — 알고리즘은 별도 unit test 필요
- (3) mechanical ❌ — 알고리즘 변경

→ 5번째 변경은 **별도 task** 로 분리. 1~4 는 묶음 유지.

## 검증 (수동 dogfood)

`/auto-write-plan` 또는 `/write-plan` 발화 시 메인이 D1 룰 catch:

- positive: 4 task 자동 분해 결과 → Step 2 자체 검토 단계에서 같은 파일 chain catch → 1 task multi-step 으로 재구성
- negative: 5번째 algorithmic 변경 catch → 4 + 1 task 로 분해

## 연결 위험

- R1 (mechanical 모호성) — 룰 본문 mechanical 예시 list 가 catch
- R2 (auto 모드 false negative) — Step 2 자체 검토가 catch
- R3 (multi-step byte-copy 정합성) — independent insertions 가정 (Scaffold / LaunchedEffect / BackHandler / placeholder 모두 file 의 다른 위치)
