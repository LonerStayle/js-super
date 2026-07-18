---
description: "feature 디렉토리의 모든 <slug>-*.md 파일에 포맷만 정리하는 pass 를 보조 에이전트로 백그라운드 실행. 의미는 1:1 보존."
argument-hint: "[<slug>]"
disable-model-invocation: true
---

# /pretty-md

`<slug>` 인자는 선택입니다. 누락 시 `scripts/auto_flow.find_latest_slug(Path("docs/features"))` 를 호출해서 가장 최근 폴더를 자동으로 선택합니다.

이 슬래시는 feature 디렉토리의 모든 `<slug>-*.md` 파일에 **포맷만 정리하는 pass** 를 Sonnet 보조 에이전트로 백그라운드 호출합니다. `.md` 자동 발동 경로는 없습니다 — 사용자가 명시적으로 `/pretty-md` 를 호출했을 때만 발동합니다.

## 동작

1. 인자 `<slug>` 확인 (또는 latest slug 추론)
2. `docs/features/<date>-<slug>/<slug>-{requirements,tech-design,implementation-plan}.md` 중 존재하는 모든 `.md` 검출 (feature 폴더에는 날짜 접두어가 붙으므로, slug 만 알 때는 `docs/features/*-<slug>/` 로 glob 해서 실제 폴더를 찾을 것)
3. 각 `.md` 에 대해 Subagent dispatch:
   - `subagent_type`: `general-purpose`
   - `model`: `sonnet`
   - `run_in_background`: `true` (fire-and-forget)
   - `prompt`: 아래 룰로 format-only pass 수행
4. 메인 즉시 다음 turn — 결과 대기 X

## Subagent prompt 룰 (format-only)

- **format-only pass** — 줄바꿈 / 들여쓰기 / 빈 줄 / 표 정렬 / 코드블록 fence 일관성만 정리
- **의미 보존 절대** — 문장 / 항목 / 결정 사항 / 숫자 / 표 내용 1:1 보존 (의역 / 요약 / 재구조화 절대 X)
- **`## 변경이력` footer byte-equal 보존** — footer 영역은 정형 대상에서 완전 제외. footer 시작 라인부터 파일 끝까지 byte-equal 보장 (한 글자도 손대지 않음)
- 산출물은 같은 `.md` 파일에 in-place overwrite

## 사용 시점

- 사용자가 `.md` 직접 편집 (오타 / 표 깨짐 / 들여쓰기 손상) 후 정리 원할 때 명시 호출
- 초안 작성 직후 일관성 정리 원할 때 명시 호출
- 자동 발동 경로 없음 — opt-in 명시 호출만

## 영구 생략

- AskUserQuestion 게이트 — fire-and-forget 의도상 사용자 입력 wait X
- 의미 가공 / 재구조화 / 요약 (format-only 룰)
- `## 변경이력` footer 손댐 — byte-equal 보존
- 결과 dispatch 노출 — silent

## 다음 단계

자동 chain 없음. 1회성 액션.
