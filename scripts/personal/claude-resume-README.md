Claude Code 사용 중 `"hit your session limit"` 에러로 멈춘 세션만 선별하여 리셋 시점에 재개 메시지를 전송하는 iTerm2 Python 스크립트 가이드입니다.

---

## 1. 사전 준비 (iTerm2 Python API 활성화)

1. iTerm2 실행
2. 설정 창 열기: `Cmd + ,` (상단 메뉴 `iTerm2` -> `Settings...`)
3. `General` 탭 -> `Magic` 하위 탭 이동
4. `Enable Python API` 체크박스 활성화

---

## 2. 파일 목록 및 저장 경로

### 1) 수동 일괄 실행용 (`iterm2-claude-resume-auto.py`)
사용자가 원할 때 메뉴나 단축키로 즉시 실행하여 리밋 걸린 세션들에 메시지를 1회 일괄 발송합니다.
* **저장 위치**: `~/Library/Application Support/iTerm2/Scripts/iterm2-claude-resume-auto.py`
* **특징**: 최근 20줄만 검사하여 이전 리밋 로그로 인한 오작동 방지

### 2) 무인 자동 감시용 (`iterm2-claude-auto-resume-once.py`)
백그라운드에 상주하며 리셋 시간(예: `resets 3pm`)을 자동 계산하여 정각에 **딱 1회** 스스로 재개합니다.
* **저장 위치**: `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/iterm2-claude-auto-resume-once.py`
* **안전장치**:
  * 세션당 1회 전송 보장 (중복 발송 방지)
  * 리셋 시점에 화면 최하단을 재검증하여 계정 전환 등으로 이미 작업 중이면 발송 자동 취소

---

## 3. 사용 방법

### `iterm2-claude-resume-auto.py` (수동 실행)
* **메뉴 실행**: 토큰 리셋 후 상단 메뉴 `Scripts` -> `iterm2-claude-resume-auto.py` 클릭
* **단축키 지정**:
  1. `Settings` (`Cmd + ,`) -> `Keys` -> `Key Bindings` 이동
  2. 하단 `+` 버튼 클릭
  3. `Keyboard Shortcut`: 원하는 단축키 입력 (예: `Ctrl + Option + R`)
  4. `Action`: `Run Python Script` 선택 후 `iterm2-claude-resume-auto.py` 지정

### `iterm2-claude-auto-resume-once.py` (무인 자동 감시)
* `AutoLaunch` 디렉토리에 넣어두면 iTerm2가 켜질 때 백그라운드에서 자동 실행됩니다.
* 수동으로 감시 프로세스를 시작하려면 상단 메뉴 `Scripts` -> `iterm2-claude-auto-resume-once.py`를 클릭합니다.

---

## 4. 참고 사항
* **메시지 수정**: 각 파이썬 파일 상단의 `resume_message` 변수 값을 수정하여 전송 문구를 변경할 수 있습니다.
* **감지 키워드**: 화면에 출력된 고유 문구인 `"hit your session limit"`을 기준으로 대상 세션을 식별합니다.
