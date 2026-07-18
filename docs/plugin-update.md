# 플러그인 업데이트 절차 (cheat sheet)

skill / command / README / manifest 등을 수정한 뒤 **새 버전을 Claude Code에 반영**하는 표준 절차.

---

## 1. 버전 bump (semver)

| 변경 종류 | bump | 예시 |
|---|---|---|
| 작은 보강 / 버그 fix / 민감정보 스크럽 | patch | 1.0.0 → 1.0.1 |
| 기존 동작 변경 / skill 보강 / 새 기능 추가 | minor | 1.0.0 → 1.1.0 |
| 호환 깨지는 변경 / 워크플로우 재설계 | major | 1.0.0 → 2.0.0 |

수정해야 할 파일 **3개** (셋 다 동일 버전):

```bash
# .claude-plugin/plugin.json
"version": "1.1.0"

# .claude-plugin/marketplace.json (plugins[0].version)
"version": "1.1.0"

# package.json
"version": "1.1.0"
```

빠른 확인:
```bash
grep -n '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json package.json
# 세 줄 모두 같은 숫자여야 함
```

---

## 2. Claude Code 안에서 갱신

```
# 1) 마켓플레이스 메타데이터 새로 읽기
/plugin marketplace update js-super

# 2) 플러그인 자체 업데이트 (옵션 A: 한 번에)
/plugin update js-super@js-super

# 또는 옵션 B: 깨끗하게 재설치 (manifest 변경이 클 때 권장)
/plugin uninstall js-super@js-super
/plugin install js-super@js-super
```

---

## 3. Claude Code 세션 재시작

skill 본문 / command 본문 변경은 **세션 시작 시점**에 다시 읽힙니다. 반드시 재시작 후 검증.

---

## 4. 검증

신규 세션에서:

```
/help
```

또는 `/` 입력 후 자동완성에 5개 보이는지:

```
/brainstorm   /design   /write-plan   /execute-plan   /worktree
```

skill 본문 변경 검증 (예: 위험 주석 6-checklist 항목 추가됐는지):

```bash
grep -n "복잡 분기" skills/risk-annotation/SKILL.md
```

---

## 5. 문제 시 롤백

manifest만 되돌리기:

```bash
# 옛 버전으로 (예: 1.0.0)
sed -i '' 's/"version": "1.1.0"/"version": "1.0.0"/' \
    .claude-plugin/plugin.json \
    .claude-plugin/marketplace.json \
    package.json
```

또는 git 사용 시:
```bash
git checkout HEAD~1 -- .claude-plugin/ package.json
```

이후 위 §2~§4 다시 실행.

---

## 자주 하는 실수

| 증상 | 원인 | 해결 |
|---|---|---|
| 슬래시 자동완성에 변경된 description 안 보임 | 세션 재시작 안 함 | 세션 종료 + 재시작 |
| `/plugin marketplace update` 가 "no changes" | 세 manifest 중 일부만 bump됨 | 셋 다 동일 버전으로 통일 |
| 새 skill 추가했는데 invoke 안 됨 | install 안 됨 (marketplace update만 함) | `/plugin update` 또는 uninstall+install |
| 기존 conversation history 못 찾음 | 디렉터리 rename 시 `.claude/projects/` 인코딩 폴더 안 옮김 | [docs/migrations/2026-05-02-rename-to-js-super.md](migrations/2026-05-02-rename-to-js-super.md) 참고 |

---

## 한 줄 요약

```
manifest 3파일 버전 동시 bump
→ /plugin marketplace update js-super
→ /plugin uninstall + install (또는 /plugin update)
→ 세션 재시작
→ 자동완성으로 검증
```
