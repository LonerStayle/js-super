"""읽기 전용 관문 테스트.

검증하는 것: 읽기 전용 파이프라인은 통과시키고, 파일을 고치거나 지우거나
새로 쓰는 명령은 전부 차단하는가. 차단할 때 이유를 함께 돌려주는가.
"""

import pytest

from evals.runner.guard import check_read_only

읽기_전용 = [
    'grep -c "hello" README.md',
    'grep -rn "x" skills/ | grep -v "tests/"',
    'ls -d skills/tech-design',
    'test -f skills/x/SKILL.md',
    'find commands -mindepth 1 -type d | wc -l',
    'awk "/Step/,/End/" file.md | grep -c "x"',
    'sed -n "34,40p" docs/testing.md',
    'git status --porcelain',
    'git ls-files | head -20',
    'git rev-parse HEAD',
    'cat README.md | wc -l',
    'grep -c "a" x.md; grep -c "b" y.md',
    'echo hello',
    'sort file.txt | uniq -c | sort -rn | head',
    'python3 -c "print(1)"',
]

차단해야_함 = [
    ('rm -rf ~/.claude/skills/foo', "삭제"),
    ('mv a.md b.md', "이동"),
    ('cp a.md b.md', "복사"),
    ('mkdir newdir', "생성"),
    ('touch newfile', "생성"),
    ('chmod +x script.sh', "권한"),
    ('echo x > out.txt', "리다이렉션"),
    ('grep x a.md >> log.txt', "리다이렉션"),
    ('git commit -m "x"', "git 쓰기"),
    ('git add .', "git 쓰기"),
    ('git push', "git 쓰기"),
    ('sed -i "" "s/a/b/" x.md', "제자리 편집"),
    ('python3 -c "open(\'x\',\'w\').write(1)"', "파이썬 쓰기"),
    ('python3 -c "import os; os.remove(\'x\')"', "파이썬 삭제"),
    ('echo `whoami`', "명령 치환"),
    ('echo $(id)', "명령 치환"),
    ('curl http://x.com', "허용 목록 밖"),
    ('npm install', "허용 목록 밖"),
    ('grep x a.md | tee log.txt', "쓰기 계열"),
]


@pytest.mark.parametrize("command", 읽기_전용)
def test_읽기_전용은_통과한다(command):
    result = check_read_only(command)
    assert result.allowed, f"{command!r} 이 막힘 — {result.reason}"


@pytest.mark.parametrize("command,why", 차단해야_함)
def test_쓰기_계열은_차단한다(command, why):
    result = check_read_only(command)
    assert not result.allowed, f"{command!r} 이 통과함 ({why} 인데)"
    assert result.reason, "차단하면서 이유를 안 줌"


def test_따옴표가_안_닫히면_차단한다():
    result = check_read_only('grep "unclosed a.md')
    assert not result.allowed
    assert "따옴표" in result.reason


def test_파이프_뒤_구간도_검사한다():
    result = check_read_only('grep x a.md | rm -rf y')
    assert not result.allowed


def test_논리연산_뒤_구간도_검사한다():
    result = check_read_only('test -f a.md && git commit -m x')
    assert not result.allowed


def test_sed_는_n_없이_차단한다():
    assert not check_read_only('sed "s/a/b/" x.md').allowed
    assert check_read_only('sed -n "1,5p" x.md').allowed
