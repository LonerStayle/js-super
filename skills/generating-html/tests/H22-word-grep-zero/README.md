# H22 — `docs-pretty` + `regen-html` 단어 grep 0 회귀 catch (메타 dogfood)

> v2.2.2 신규. fixture 는 README 만 (Python 코드 없음). 신규 skill / command / CLAUDE.md 추가 시 옛 단어 (`docs-pretty`, `regen-html`) 재발 차단.

## 시나리오 (단어 grep 0 보장)

1. **v2.2.2 rename** — `docs-pretty` skill → `generating-html` skill, `/regen-html` 슬래시 → `/sync-html` 슬래시
2. **회귀 catch grep** — 신규 skill / command / CLAUDE.md / README.md 본문에 옛 단어 (`docs-pretty`, `regen-html`) 재발 시 즉시 catch
3. **제외 경로 룰** — 다음 경로는 fixture history / upstream mirror 라 grep 대상 제외:
   - `og-*` 디렉토리 (upstream superpowers verbatim mirror)
   - `js-super-sub-driven/tests/H4-preflight-fail/` (fixture history)
   - `js-super-sub-driven/tests/H5-docs-pretty-pre-review/` (fixture history — 디렉토리명 자체에 옛 단어 포함, 보존)
   - `js-super-sub-driven/tests/H6-task-name-friendly/` (fixture history — 본문에 옛 단어 메타 언급)
4. **변경이력 footer 안의 옛 단어** — 변경이력 (`docs/features/**/*.md` 의 `## 변경이력` footer) 안의 옛 단어는 audit chain 의 일부라 보존. grep 대상 제외 (`docs/features/` 디렉토리 자체는 grep 대상 X — skill / command / 최상위 CLAUDE.md / README.md 만).

## 회귀 catch grep 명령

```bash
grep -rn "docs-pretty\|regen-html" \
  skills/ commands/ CLAUDE.md README.md \
  --exclude-dir=og-* \
  --exclude-dir=H4-preflight-fail \
  --exclude-dir=H5-docs-pretty-pre-review \
  --exclude-dir=H6-task-name-friendly \
  --exclude-dir=H19-pretty-md \
  --exclude-dir=H22-word-grep-zero
# expected: 역사 메타 참조만 허용 — tests/ fixture 인덱스 (H5 행) + CLAUDE.md v2.2.2 rename 메모 자기 참조.
#           live skill / command 본문 hit = 회귀.
```

## 검증 체크리스트

- [ ] 위 grep 명령 결과 0 (회귀 없음)
- [ ] `og-*` 디렉토리 내부 단어 매치 grep 대상 제외 정상 동작 (upstream verbatim 보존)
- [ ] `js-super-sub-driven/tests/H4-6` fixture history 제외 정상 동작
- [ ] `docs/features/**` 안 변경이력 footer 보존 (grep 대상 자체에서 제외)
- [ ] 신규 skill / command 추가 시 본 grep 명령 PR check 통과
- [ ] CLAUDE.md 결합 메모 갱신 시 옛 단어 (`docs-pretty`, `regen-html`) 사용 X — 신규 단어 (`generating-html`, `sync-html`, `pretty-md`) 사용

## 제외 경로 정당화

| 경로 | 이유 |
|---|---|
| `skills/og-*/` | upstream superpowers 5.0.7 verbatim mirror. js-super rename 영향 0. |
| `skills/js-super-sub-driven/tests/H4-preflight-fail/` | v1.1.14 fixture history. 옛 4 skill (`docs-pretty` 포함) 의 preflight 통합 동작 검증. 디렉토리명 / 본문에 옛 단어 보존. |
| `skills/js-super-sub-driven/tests/H5-docs-pretty-pre-review/` | v1.1.15+ fixture history. 디렉토리명 자체에 `docs-pretty` 포함. 옛 시점의 사전-리뷰 동작 검증 — 보존. |
| `skills/js-super-sub-driven/tests/H6-task-name-friendly/` | v1.1.15+ TaskCreate 명칭 룰 (FR-6) fixture. 본문에 옛 4 skill 의 친화 명칭 예시 포함. 보존. |
| `docs/features/**` 변경이력 footer | audit chain 의 일부. `## 변경이력` entry 안의 옛 단어는 그 시점의 record 라 영구 보존. |

## 실패 모드 검증

| 시나리오 | 기대 동작 |
|---|---|
| 신규 skill 본문에 `docs-pretty` 단어 잔존 | grep 0 보장 깨짐 → PR check fail → 작성자에게 즉시 알람 |
| 신규 command 본문에 `regen-html` 단어 잔존 | 동일 — PR check fail |
| CLAUDE.md 결합 메모 갱신 시 옛 단어 사용 | 동일 — PR check fail |
| 신규 fixture (H23+) 가 옛 단어 메타 언급 | 디렉토리명 prefix 만 추가 제외 경로 등록 (CLAUDE.md 결합 메모 갱신) |

## CI 통합 후보 (v2.2.x patch)

본 grep 명령은 v2.2.2 시점 수동 검증. 향후 CI step 추가 후보:

```yaml
- name: 옛 단어 grep 0 회귀 catch (H22)
  run: |
    ! grep -rn "docs-pretty\|regen-html" \
      skills/ commands/ CLAUDE.md README.md \
      --exclude-dir=og-* \
      --exclude-dir=H4-preflight-fail \
      --exclude-dir=H5-docs-pretty-pre-review \
      --exclude-dir=H6-task-name-friendly
```

## Anti-Patterns 회귀 catch

```bash
# 옛 단어 재발 grep (본 fixture 의 핵심 검증)
grep -rn "docs-pretty\|regen-html" \
  skills/ commands/ CLAUDE.md README.md \
  --exclude-dir=og-* \
  --exclude-dir=H4-preflight-fail \
  --exclude-dir=H5-docs-pretty-pre-review \
  --exclude-dir=H6-task-name-friendly
# expected: 0

# 본 fixture README 자체는 grep 대상에서 자기 자신을 메타 catch (디렉토리 H22-word-grep-zero 내부 README 만)
# → 본 README 안의 `docs-pretty` / `regen-html` 단어는 메타 설명 목적이라 잠재적 false positive
# → 회피: 본 README 는 skills/generating-html/tests/H22-word-grep-zero/ 안에 위치 → 위 grep 의 `skills/` 패턴에 포함됨
# → 추가 mitigation: H22 디렉토리 자체를 제외 경로로 등록 검토 (--exclude-dir=H22-word-grep-zero), 또는 본 README 의 옛 단어를 backtick escape (`docs-pretty`, `regen-html`) 후 grep 패턴에서 backtick 포함 라인 제외
# 현재 fixture 는 단어 매치 자체를 메타 설명 목적으로 두고 디렉토리 제외 경로 옵션 명시
```

## 디렉토리 제외 경로 운영 룰

본 H22 fixture 자체가 옛 단어를 메타 설명 목적으로 포함 → 회귀 catch grep 실행 시 본 디렉토리도 제외:

```bash
grep -rn "docs-pretty\|regen-html" \
  skills/ commands/ CLAUDE.md README.md \
  --exclude-dir=og-* \
  --exclude-dir=H4-preflight-fail \
  --exclude-dir=H5-docs-pretty-pre-review \
  --exclude-dir=H6-task-name-friendly \
  --exclude-dir=H22-word-grep-zero
# expected: 0
```

CI step 도 위 명령으로 통합 검토 (v2.2.x patch 후보).
