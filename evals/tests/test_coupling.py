"""결합 룰 파서 테스트.

검증하는 것: CLAUDE.md 형태의 마크다운에서 bash 코드 블록 안의 검사 명령과
'# expected:' 주석을 짝지어 뽑아내는가. 기대값 주석이 없는 명령도 버리지 않고
expected=None 으로 담는가. 실제 저장소를 넣으면 CLAUDE.md 80건 + fixture README 를 합쳐 110건 이상 나오는가.
"""

from pathlib import Path

import pytest

from evals.runner.coupling import Rule, collect_rules, parse_claude_md

REPO_ROOT = Path(__file__).resolve().parents[2]


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "CLAUDE.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_명령과_기대값을_짝지어_뽑는다(tmp_path):
    path = write(tmp_path, """
# 문서

## 회귀 catch grep

```bash
grep -c "hello" README.md
# expected: 1
```
""")
    rules = parse_claude_md(path)
    assert len(rules) == 1
    assert rules[0].command == 'grep -c "hello" README.md'
    assert rules[0].expected == "1"
    assert rules[0].expected_int == 1
    assert rules[0].expected_is_numeric is True


def test_한_블록에_여러_룰이_있으면_각각_나눈다(tmp_path):
    path = write(tmp_path, """
```bash
grep -c "a" x.md
# expected: 1

grep -c "b" y.md
# expected: 0
```
""")
    rules = parse_claude_md(path)
    assert len(rules) == 2
    assert rules[0].expected == "1"
    assert rules[1].command == 'grep -c "b" y.md'
    assert rules[1].expected == "0"


def test_기대값_주석이_없으면_None_으로_담고_버리지_않는다(tmp_path):
    path = write(tmp_path, """
```bash
grep -c "a" x.md
```
""")
    rules = parse_claude_md(path)
    assert len(rules) == 1
    assert rules[0].expected is None
    assert rules[0].expected_int is None
    assert rules[0].expected_is_numeric is False


def test_여러_줄_명령을_한_룰로_묶는다(tmp_path):
    path = write(tmp_path, """
```bash
grep -rn "x" skills/ \\
  | grep -v "tests/"
# expected: 0
```
""")
    rules = parse_claude_md(path)
    assert len(rules) == 1
    assert "\n" in rules[0].command
    assert rules[0].expected == "0"


def test_bash_가_아닌_블록은_무시한다(tmp_path):
    path = write(tmp_path, """
```python
print("not a rule")
```

```json
{"a": 1}
```
""")
    assert parse_claude_md(path) == []


def test_각_N_이상_형태의_기대값도_숫자로_읽는다(tmp_path):
    path = write(tmp_path, """
```bash
grep -c "x" a.md b.md
# expected: 각 >= 1
```
""")
    rules = parse_claude_md(path)
    assert rules[0].expected_is_numeric is True
    assert rules[0].expected_int == 1


def test_자연어_기대값은_숫자가_아니라고_판정한다(tmp_path):
    path = write(tmp_path, """
```bash
grep -n "x" a.md
# expected: 출력 없음
```
""")
    rules = parse_claude_md(path)
    assert rules[0].expected == "출력 없음"
    assert rules[0].expected_is_numeric is False


def test_출처에_파일명과_줄번호가_들어간다(tmp_path):
    path = write(tmp_path, """
line1

```bash
grep -c "x" a.md
# expected: 1
```
""")
    rules = parse_claude_md(path)
    assert rules[0].source.startswith("CLAUDE.md:")
    assert int(rules[0].source.split(":")[1]) > 0


@pytest.mark.skipif(
    not (REPO_ROOT / "CLAUDE.md").exists(), reason="CLAUDE.md 없음"
)
def test_실제_CLAUDE_md_에서_80건_이상_나온다():
    rules = parse_claude_md(REPO_ROOT / "CLAUDE.md")
    assert len(rules) >= 80, f"실제로 {len(rules)}건"
    assert all(isinstance(rule, Rule) for rule in rules)
    assert sum(1 for rule in rules if rule.expected) >= 50


@pytest.mark.skipif(
    not (REPO_ROOT / "CLAUDE.md").exists(), reason="저장소 아님"
)
def test_두_원천을_합치면_110건_이상():
    """설계서의 116건은 CLAUDE.md 단독이 아니라 fixture README 를 합한 수다."""
    rules = collect_rules(REPO_ROOT)
    assert len(rules) >= 110, f"실제로 {len(rules)}건"
    sources = {rule.source.split(":")[0] for rule in rules}
    assert "CLAUDE.md" in sources
    assert any(src.startswith("skills/") for src in sources), "fixture README 를 못 읽음"
