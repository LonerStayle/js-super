# H16 — 무맥락 검증자 병렬 (clean-context verifiers)

`verifying-spec` 이 메인 자체 검증과 동시에 맥락 없는 보조 에이전트 둘을 띄우고, 결과를 중재해 하나의 보고서로 내는지 확인한다.

관련 파일: `skills/verifying-spec/SKILL.md`, `skills/verifying-spec/clean-solo-prompt.md`, `skills/verifying-spec/clean-cross-prompt.md`

## S1 — 기본 호출 (플래그 없음)

**입력**: 아무 피처 폴더에서 `/tech-design <slug>` 실행. `--no-clean-verify` 미지정.

**Expected**
- dispatch 직후 `ℹ️ 무맥락 검증자 2개를 백그라운드로 띄웠습니다.` 안내 1회 노출
- 두 `Agent` 호출이 **한 메시지**에 묶여 나감 (순차 dispatch 면 실패)
- 두 호출 모두 `run_in_background: true`, `model` 인자 **없음**
- 단독 검증자 프롬프트에 upstream 문서 경로가 **주입되지 않음**
- 어느 검증자에게도 대화 이력 / 작성 의도 서술 / `## 변경이력` footer 내용이 주입되지 않음
- 최종 보고서에 `## A. Consistency`, `## C. Code Impact`, `## 무맥락 검증`, `## 중재`, `## 권장` 이 모두 존재
- 사용자 게이트는 **1개** (보고서를 두 개로 쪼개 두 번 묻지 않음)

## S2 — `--no-clean-verify` 지정

**입력**: `/tech-design <slug> --no-clean-verify`

**Expected**
- 보조 에이전트 dispatch **0건**
- 기존 4축(`## A. Consistency`, `## C. Code Impact`, `## 권장`)이 그대로 존재
- `## 무맥락 검증` 섹션이 `--no-clean-verify 로 건너뜀` 한 줄로 존재. **이 줄이 없으면 실패** — 섹션이 통째로 빠지면 사용자가 검증자가 돌았는지 안 돌았는지 구분할 수 없다 (skill 본문 플래그 섹션 + Acceptance 5 와 동일 기준)
- 흐름은 정상 진행 (건너뛰었다고 멈추지 않음)

## S3 — 검증자 실패

**입력**: 기본 호출 중 한 검증자가 실패하거나 응답 없음.

**Expected**
- 보고서 `## 무맥락 검증` 에 해당 검증자가 **실패로 표기**됨 (사유 포함)
- 나머지 검증자 결과와 메인 자체 검증 결과로 보고서를 완성하고 **진행**
- 실패를 조용히 생략하지 않음 (표기 없이 진행하면 실패)
- 실패를 이유로 흐름 전체를 중단하지 않음

## 안티 패턴 (하나라도 관찰되면 회귀)

| 관찰 | 깨진 것 |
|---|---|
| 단독 검증자에게 upstream 경로가 넘어감 | FR-3 순서 보장 (D1) |
| 두 dispatch 가 별도 메시지로 나감 | R-8 지연 합산 |
| `model: "sonnet"` 등 고정 모델 지정 | FR-7 / D7 |
| 무맥락 지적이 기각됐는데 사유가 보고서에 없음 | FR-5 |
| 판정이 갈렸다고 사용자에게 되물음 | FR-5 위임 룰 |
| 메인 A + C 검증을 생략하고 보조 에이전트 결과만 사용 | HARD-GATE (대체 금지) |
| `HARD-GATE` 에서 EXCEPTION 2 가 삭제됨 | FR-8 / R-1 |
