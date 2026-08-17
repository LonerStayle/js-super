# 용어집: 스킬목록-전체프로젝트조회

> 이 문서는 `스킬목록-전체프로젝트조회-implementation-plan.md` 를 처음 읽는 사람을 위한 참고 자료입니다.
> 계획서가 바뀌면 다시 만들어지며, 내용이 어긋날 때는 계획서가 정본입니다.

## 한눈에 보기

이 피처는 `/list-skills` 커맨드가 skill 목록을 찾는 범위를 현재 프로젝트와 글로벌 두 곳에서 사용자 홈 디렉토리 전체로 넓히는 작업이다. 핵심은 신규 파일 하나(`scripts/skill_scan.py`)이고, 이 스크립트가 홈 디렉토리를 훑어 JSON 결과를 만들면 `commands/list-skills.md` 는 그 결과를 받아 사람이 읽을 목록으로 바꿔 보여주기만 한다. 읽기 순서를 고른다면 `scripts/skill_scan.py` 의 `scan` 함수부터 보고, 그다음 `commands/list-skills.md` 의 "수집 절차" 항목을 보는 편이 이해가 빠르다.

## 이번에 새로 만드는 것

| 이름 | 종류 | 위치 | 하는 일 |
|---|---|---|---|
| `scripts/skill_scan.py` | 파일 (신규 스크립트) | `scripts/skill_scan.py` | 홈 디렉토리 전체를 훑어 출처 표식이 있는 skill 을 현재 프로젝트, 글로벌, 다른 프로젝트 세 그룹으로 분류한 JSON 을 표준출력으로 내보낸다. |
| `scan` | 함수 | `scripts/skill_scan.py` | 세 그룹 분류를 총괄하는 진입 함수. 실행 위치에서 현재 프로젝트를 찾고, 홈 아래를 훑어 나머지 프로젝트를 찾은 뒤, 각각에서 `collect_skills` 로 skill 목록을 채운다. |
| `collect_skills` | 함수 | `scripts/skill_scan.py` | 한 프로젝트의 skill 디렉토리 안에서 출처 표식 파일이 있는 skill 항목만 골라 이름, 경로, 설명으로 이루어진 목록으로 만든다. |
| `find_current_project` | 함수 | `scripts/skill_scan.py` | 실행 위치에서 상위 디렉토리로 한 단계씩 올라가며 skill 디렉토리를 가진 첫 프로젝트를 찾는다. 홈 디렉토리 자체는 대상에서 뺀다. |
| `scan_home_projects` | 함수 | `scripts/skill_scan.py` | 홈 디렉토리 아래를 전부 훑어 skill 디렉토리를 가진 프로젝트를 찾는다. 숨김 폴더와 시스템·용량이 큰 폴더는 내려가지 않는다. |
| `read_description` | 함수 | `scripts/skill_scan.py` | skill 하나의 소개 파일 앞부분에서 한 줄짜리 설명 값을 꺼낸다. 못 읽으면 설명이 없다는 뜻의 문구를 돌려준다. |
| `read_created` | 함수 | `scripts/skill_scan.py` | 출처 표식 파일에서 생성 시각 값을 꺼낸다. 값이 없거나 파일을 못 읽으면 아무것도 돌려주지 않는다. |
| `MARKER_NAME` | 상수 | `scripts/skill_scan.py` | 출처 표식 파일의 이름을 담은 문자열 상수다. |
| `REMOVED_RE` | 상수 (정규식) | `scripts/skill_scan.py` | `/remove-skill` 이 삭제 대기 상태로 이름을 바꿔둔 디렉토리를 걸러내기 위한 패턴이다. |
| `PRUNE_DIR_NAMES` | 상수 | `scripts/skill_scan.py` | 홈 전체를 훑을 때 안으로 들어가지 않을 디렉토리 이름 목록이다. 스캔 속도를 지키고 접근 오류를 줄이기 위한 것이다. |
| `main` | 함수 | `scripts/skill_scan.py` | 명령줄에서 이 스크립트를 실행했을 때의 진입점. 홈 위치와 실행 위치를 인자로 바꿔 받을 수 있어 테스트에서 가짜 홈 디렉토리를 넣어볼 수 있다. |
| `scripts/tests/test_skill_scan.py` | 파일 (신규 테스트) | `scripts/tests/test_skill_scan.py` | `skill_scan.py` 의 동작을 임시 디렉토리에 가짜 홈 구조를 만들어 검증하는 단위 테스트다. |

## 이미 있는 것 (계획서가 건드리거나 불러 쓰는)

| 이름 | 종류 | 위치 | 하는 일 | 알아둘 점 |
|---|---|---|---|---|
| `commands/list-skills.md` | 커맨드 파일 | `commands/list-skills.md` | `/list-skills` 슬래시 커맨드의 지시문이다. js-super 가 만든 skill 을 조회해 보여주는 절차가 그대로 적혀 있다 (커맨드는 실행되는 코드가 아니라 Claude 가 읽고 따르는 지시문이다). | 이번 계획에서 스캔 대상을 두 스코프에서 홈 전체로 넓히는 방향으로 이 파일 전체가 교체된다. |
| `.js-super-skill.json` | 마커 파일 (규약) | 각 skill 디렉토리 안 | `/new-skill` 이 skill 을 만들 때 함께 써두는 출처 표식 파일이다. 만든 주체, 스코프, 생성 시각 세 값을 담고 있고, 이 파일이 있는지 여부로 js-super 가 만든 skill 인지를 가린다 (`commands/new-skill.md:172`). | `/list-skills` 조회와 `/remove-skill` 삭제가 같은 판별 기준을 쓴다. 이 파일 자체를 보안 경계로 쓰지는 않는다 — 사용자가 파일을 수동으로 복사하면 다른 skill 도 표식이 있는 것처럼 보일 수 있다. |
| `${CLAUDE_PLUGIN_ROOT}` | 환경 변수 | 플러그인 실행 환경에서 주입됨 | 이 플러그인이 설치된 경로를 가리키는 환경 변수다. 사용자 프로젝트 안에서 커맨드가 실행될 때 스크립트의 절대 경로를 찾는 데 쓴다. | `hooks/hooks.json` 이 이미 같은 방식으로 쓰고 있어 이번 계획은 그 선례를 따른 것이다. 이 변수를 지원하지 않는 실행 환경에서는 해석이 실패할 수 있어 커맨드에 폴백 절차가 딸려 있다. |
| `commands/new-skill.md` | 커맨드 파일 | `commands/new-skill.md` | `/new-skill` 커맨드. 새 skill 을 만들면서 출처 표식 파일을 함께 쓴다. | 이번 계획에서는 참조만 되고 수정되지 않는다. |
| `commands/remove-skill.md` | 커맨드 파일 | `commands/remove-skill.md` | `/remove-skill` 커맨드. 출처 표식이 있는 skill 디렉토리 이름 끝에 삭제 시각을 붙여 안전하게 지우는 게 기본 동작이고, 강제 옵션을 주면 완전히 지운다. | 이번 계획의 스캔 스크립트가 걸러내는 이름 패턴이 바로 이 커맨드가 남기는 흔적이다. 시각 표기는 14자리 숫자 형식이다 (`commands/remove-skill.md:98`). |
| `scripts/preflight.py` | 파일 (기존 helper) | `scripts/preflight.py` | 계획서 작성과 실행 흐름에서 여러 조건(코드 정리 여부, 실행 방식 등)을 결정적으로 점검하는 helper 모듈이다. | 이번 계획에서 새로 만드는 `skill_scan.py` 와 같은 폴더에 있는 이웃 파일이라 헷갈릴 수 있지만 용도가 다르다. `preflight.py` 는 계획서 작성·실행 흐름을 점검하고, `skill_scan.py` 는 skill 목록을 조회한다. |
| `scripts/tests/test_preflight.py` | 파일 (기존 테스트) | `scripts/tests/test_preflight.py` | `preflight.py` 의 단위 테스트다. 임시 디렉토리를 만들어 파일을 써넣고 점검 함수를 호출하는 방식으로 검증한다. | 계획서 Task 1 이 이 파일의 작성 방식을 그대로 따라 새 테스트를 쓰라고 지시하고 있어, 새 테스트 파일을 이해하려면 이 파일을 먼저 보는 게 도움이 된다. |
| `evals/run.py` | 파일 (기존 검증 러너) | `evals/run.py` | 이 저장소의 결합 규칙과 기존 단위 테스트, 정적 산출물 검사를 한 번에 돌려서 무엇이 새로 깨졌는지 보고하는 진입점이다. | Task 6 의 마지막 검증 단계에서 이 스크립트를 실행해 새로 깨진 것이 없는지 확인한다. 별도의 대화형 모델 호출 없이 결정적으로만 돈다. |
| `commit_policy` (frontmatter 값) | 설정 키 | 계획서 파일 맨 앞부분 | 이 계획서를 어떤 방식으로 실행할지 정하는 값이다. task 마다 커밋한다는 값으로 설정돼 있으면 `scripts/preflight.py` 가 이를 읽어 보조 에이전트 강제 실행 모드 진입 가능 여부를 판정한다 (`scripts/preflight.py:127`). | 보조 에이전트 강제 실행 모드로 이 계획서를 실행하려면 이 값이 task 마다 커밋하는 설정이어야 하고, 다른 값이면 진입이 막힌다. |

## 헷갈리기 쉬운 짝

| 이것 | 저것 | 차이 |
|---|---|---|
| `find_current_project` | `scan_home_projects` | 둘 다 프로젝트 루트를 찾지만 방향이 반대다. `find_current_project` 는 실행 위치에서 위로 한 단계씩만 올라가 딱 하나(현재 프로젝트)를 찾고, `scan_home_projects` 는 홈 디렉토리에서 아래로 전부 훑어 발견되는 프로젝트를 모두 모은다. |
| `read_description` | `read_created` | 둘 다 skill 하나의 정보를 읽는 함수지만 읽는 파일이 다르다. `read_description` 은 skill 의 소개 파일을, `read_created` 는 출처 표식 파일을 읽는다. |
