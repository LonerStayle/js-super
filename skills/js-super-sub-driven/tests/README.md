# Test Fixtures

## v1.1.7 (changelog batch consolidator)

| Fixture | 검증 대상 | 연결 AC | 자동? |
|---|---|---|---|
| F1-basic-batch | 2-task → consolidated entry 1개 (slim schema) | AC-1, AC-4 | ✅ pytest |
| F2-zero-code-task | 코드 0건 task → [검증] entry | AC-3 | (수동 비교) |
| F3-mode-schema-divergence | per-task vs single 모드 schema 분기 | AC-4 | (수동 비교) |
| F4-interrupt-recovery | 세션 끊긴 후 buffer 잔존 detection | R2 mitigation | ✅ pytest |
| F5-cleanup | consolidator 성공 후 buffer 디렉토리 cleanup | R4 mitigation | (수동 dogfood) |

## v1.1.14 (wave-parallel + model hint)

| Fixture | 검증 대상 | 연결 AC | 자동? |
|---|---|---|---|
| G1-entry-guard | plan 없는 폴더 ABORT | AC-3 | (수동 dogfood) |
| G2-simple-wave | 3 task disjoint, 1 wave 동시 dispatch | AC-1 | (수동 dogfood) |
| G3-deps | task 2 가 task 1 helper 사용, 2 waves | D-T1/D-T7 | (수동 dogfood) |
| G4-failure-isolation | wave 안 task 1개 spec FAIL → 형제 commit + 격리 | AC-2 | (수동 dogfood) |
| G5-model-haiku | `**Model**: haiku` 잔존 → sonnet 격상 dispatch | AC-4 | (수동 dogfood) |
| G6-no-model-default | Model 필드 없음 → sonnet 디폴트 | AC-5 | (수동 dogfood) |
| G7-post-hoc-conflict | DAG 추론 오류 시뮬, conflict rollback + 재배치 | R1 | (수동 dogfood) |
| G8-reviewer-sonnet | implementer 격상 케이스에도 reviewer sonnet 고정 | AC-6 | (수동 dogfood) |

자동 (pytest) 항목은 `scripts/tests/test_changelog_buffer.py` + `scripts/tests/test_dag_builder.py` + `scripts/tests/test_preflight.py` 로 호출됨. G1~G8 의 동작 검증은 dogfood 에서 사용자가 직접 비교 (subagent dispatch 는 pytest 로 모킹 불가).

## v1.1.15+ — flow-slim dogfood fixtures (FR-1/FR-3/FR-4/FR-5/FR-6)

| Fixture | 검증 대상 | 연결 AC | 자동? |
|---|---|---|---|
| H1-router-small | small 신호 자동 라우팅 → og-brainstorming | AC-6, FR-3 | (수동 dogfood) |
| H2-router-ambiguous | 모호 피처 → AskUserQuestion 게이트 | AC-7, FR-3 | (수동 dogfood) |
| H3-adaptive-na | 비활성 토픽 dialogue 스킵 + N/A 한 줄 | AC-1, AC-8, FR-1 | (수동 dogfood) |
| H4-preflight-fail | 변경이력 entry 존재 시 exit 1 + 게이트 | AC-11, FR-4 | (수동 dogfood) |
| H6-task-name-friendly | Checklist 항목명 사용자 친화 한국어 | AC-15, AC-17, FR-6 | (수동 dogfood) |

- H1 — entry router: small 신호 자동 라우팅 (FR-3, AC-6)
- H2 — entry router: 모호 피처 게이트 발화 (FR-3, AC-7)
- H3 — adaptive 7-topic: 비활성 N/A 박힘 (FR-1, AC-1, AC-8)
- H4 — preflight 강제 실패 게이트 (FR-4, AC-11)
- H6 — task name friendly (FR-6, AC-15, AC-17)

## v1.1.17+ — auto-flow dogfood fixtures

- H7 — auto-brainstorm small 피처 자동 chain (D1, D4)
- H8 — /auto-design-tech 기존 PRD 활용 chain (D-T9, D4)
- H9 — mid-flight stop 인터럽트 (D7, D-T8, R11)
- H10 — auto-execute BLOCKED → failure isolation (D6, R2, R9)

## v2.0.0+ — byte-copy + reorder 3-stage fixtures

| Fixture | 시나리오 |
|---|---|
| H11-user-edit-reorder | 사용자 mid-flight 수정 → Implementer BLOCKED → Reorder dispatch → DONE (silent overwrite 차단 검증) |

## v2.0.1+ — same-file mechanical 묶음 룰 fixtures

| Fixture | 시나리오 |
|---|---|
| H12-same-file-merge | 같은 파일 4 mechanical 변경 plan → D1 3 조건 catch → 1 task multi-step 묶음 (positive) + 5번째 algorithmic 변경 → 분리 (negative) |

## v2.0.2+ — og-flow rename + 핸드오프 강화 fixtures

- `H13-og-flow-subagent-routing/` — og-flow Subagent path 매칭 검증 (upstream 원본 매칭 / js-super-sub-driven 미매칭)

## v2.9.0 이후 fixtures (H14~H20)

| Fixture | 시나리오 |
|---|---|
| H14-depth-select | 산출물 깊이 선택 — 기술설계 게이트 3지선다 / `depth: 2` 표식 판독 / 2→3 승격 |
| H15-natural-lang-verify | 구현계획서 테스트 자연어 축약 — `**검증**` 필드 / 구현 byte-copy 와 테스트 자체 작성 분리 |
| H16-tech-design-abstraction | 기술설계 서술 수준 — 이름보다 역할 (통과 사례 + 위반 사례 대조) |
| H17-socratic-single-track | 모드 질문 부재 (A) / 요구 항목 + FR-N 계약 (B) / 제외 항목 취합 (C) / '모르겠다' 3단 사다리 (D) / 옛 6섹션 문서 하위호환 (E) |
| H18-glossary-parallel-order | code-pretty ‖ glossary 병렬 dispatch → verifying-spec → 사용자 검토 순서. 용어집 실패 non-blocking / 두 helper 조건 차이 / live doc 차단 / auto-flow 미적용 5 시나리오 |
| H19-clean-verify | 무맥락 검증자 2종 병렬 — 단독(대상 MD 만) / 대조(대상 + upstream) / 중재 / `--no-clean-verify` skip |
| H20-worktree-naming | `/worktree` 이름 해석 — AI 네이밍 제안 + 재분기 `부모__자식` 누적 / 명시 이름 존중 / detached HEAD fallback 5 시나리오 |

> 번호 규약: 병렬 워크트리에서 각자 선점해 `H16` 이 세 fixture 에 중복됐던 것을 정리했습니다 (glossary → H18, clean-verify → H19). 신규 fixture 는 본 인덱스의 마지막 번호 다음을 쓰세요.
