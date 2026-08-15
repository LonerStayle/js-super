# H9 — Mid-flight stop 인터럽트 → cleanly exit

## 시나리오

auto-brainstorming 끝 → transition notice → 사용자가 "stop" 입력 → exit.

## 입력 흐름

```
/auto-brainstorm 새 피처
... (clarifying Q + AI 자동 진행) ...
ℹ️ 기술설계 단계로 자동 넘어갑니다. 멈추려면 "stop" 입력해주세요.

사용자: stop
```

## 기대 동작

1. 메인이 다음 turn 시작 시 `parse_interrupt("stop")` → True
2. `js-super:auto-tech-design` invoke 안 함
3. 종료 메시지: ℹ️ 알겠습니다. 기술설계는 나중에 /auto-design-tech (자동) 또는 /design-tech (단계별 확인) 으로 실행해주세요.
4. requirements.md + change-history 첫 entry 는 이미 commit 됨 → 보존

다른 키워드도 동작:
- "멈춰" / "잠깐" / "abort" / "취소" / "중단" / "잠시만" / "Stop please" 모두 인터럽트로 catch

## 매핑

- AC: D7 (transition notice + stop catch), D-T8 (parse_interrupt 룰), R11 (broad catch + 모호 시 명시 확인)
- FR: auto-flow 안전성
