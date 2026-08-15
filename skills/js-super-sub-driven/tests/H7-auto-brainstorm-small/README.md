# H7 — Auto-brainstorm small 피처 자동 chain

## 시나리오

`/auto-brainstorm` small 피처 호출 → 1 clarifying Q + AI 자동 진행 + 4 단계 chain 끝까지.

## 입력

```
/auto-brainstorm 헤더 폰트 사이즈 변경
```

## 기대 동작

1. auto-brainstorming skill 진입
2. slug 자동 추론: "header-font-size-change" 또는 "헤더-폰트-사이즈-변경"
3. 폴더 생성: `docs/features/<date>-<slug>/`
4. clarifying Q 1개: "이 피처의 핵심 user story 한 줄?"
   사용자 답변
5. AI 자동 approach 선택 → 산출물 자동 작성 → change-history 자동
6. ℹ️ Auto-proceeding to /design-tech. Type "stop" to abort.
7. auto-tech-design → auto-writing-plans → auto-executing-plans 자동 chain
8. finishing 자동 + commits N

## 매핑

- AC: PRD D1 (slash invoke), D4 (chain), D2 (clarifying Q only 사용자 입력)
- FR: auto-flow 핵심
