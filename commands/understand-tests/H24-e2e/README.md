# H24 — /understand 계열 E2E 시나리오

`/understand` 5 커맨드 이식의 수동 검증 시나리오. 릴리즈 전 1회 사람이 돌린다.

## 준비

1. 소형 샘플 저장소 하나를 준비한다 (파일 20~40개 규모, git 초기화 + 커밋 1개 이상. js-super 저장소 자신도 가능).
2. `~/.understand-anything-plugin` 이 없는 상태에서 시작하면 부트스트랩 경로까지 검증된다 (있으면 버전 검사 경로만 검증).
3. git / Node 22+ / pnpm 10+ / Python 3 이 설치된 머신.

## 실행 순서와 기대 결과

| # | 실행 | 기대 결과 |
|---|---|---|
| 1 | 샘플 저장소에서 `/understand` | (사본 없을 때) "엔진 사본을 내려받습니다" 안내 → clone → 빌드. 도구 미충족이면 그 지점에서 한국어 안내 후 즉시 중단 |
| 2 | 계속 진행 | `.understandignore` 확인이 AskUserQuestion 팝업으로 온다 (산문 대기 아님). 대규모 스코핑 확인과 출력 언어 확인은 조건부라 이 소형 저장소에서는 안 떠도 통과 — 대신 파일 수를 세어 보고하는 줄이 진행 보고에 있어야 한다 |
| 3 | 완료 대기 | `.ua/knowledge-graph.json` + `meta.json` + `fingerprints.json` 생성. 종료 보고가 한국어 + viewer npx 한 줄 + gitignore 권장 네 줄 포함 |
| 4 | 안내된 viewer 명령 실행 | 브라우저에서 노드가 그려진 그래프 화면이 뜨고, 좌측 상단에 샘플 저장소 이름이 표시된다. 화면에 스키마 오류 배너가 없다 (있으면 버전 불일치) |
| 5 | `/understand-chat "엔트리포인트가 어디야"` | 그래프 기반 답변 (한국어). 그래프 없으면 `/understand` 먼저 실행 안내 |
| 6 | 파일 하나 수정 후 `/understand-diff` | 변경·영향 컴포넌트 + 위험 평가 구조화 보고 + `.ua/diff-overlay.json` 생성 + viewer 안내 |
| 7 | `/understand-explain <파일경로>` | 그래프 연결 관계 + 실제 소스 기반 딥다이브 설명 |
| 8 | `/understand-onboard` | 6섹션 온보딩 가이드 생성 + `docs/UA_ONBOARDING.md` 저장 제안 |
| 9 | `/understand` 재실행 | 진행 보고의 분석 대상 파일 수가 6번에서 고친 파일 수만큼으로 줄어든다 (1회차 전체 파일 수와 다름). 실행 후 `meta.json` 의 `gitCommitHash` 가 현재 HEAD 로 갱신된다 |
| 10 | 워크트리 안에서 `/understand` | 산출물이 메인 저장소 루트의 `.ua/` 에 생성. `--here` 를 주면 워크트리 안에 생성 |

## 실패 기록

발견한 어긋남은 이 파일 하단에 날짜와 함께 남기고, 수정 커밋과 연결한다.
