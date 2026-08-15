# H8 — /auto-design-tech (기존 PRD 활용) → chain 끝까지

## 시나리오

이미 `<slug>-requirements.md` 있는 상태에서 `/auto-design-tech` 부터 시작. latest <slug> 추론.

## 입력

```
/auto-design-tech
```

(인자 누락 — `find_latest_slug` 활용)

## 기대 동작

1. auto-tech-design skill 진입
2. `scripts/auto_flow.find_latest_slug` 호출 → 가장 최근 폴더 slug 반환
3. ⚙️ <slug> 자동 선택. 다른 폴더면 'stop' 후 인자 명시.
4. requirements.md 읽기 → adaptive 7-topic announce → AI 자동 design decision
5. tech-design.md 자동 작성 → verifying-spec → change-history
6. ℹ️ Auto-proceeding to /write-plan. Type "stop" to abort.
7. auto-writing-plans → auto-executing-plans 자동 chain

## 매핑

- AC: D-T9 (latest <slug> 추론), D4 (chain), D-T1 (mirror)
- FR: auto-flow 중간 진입점
