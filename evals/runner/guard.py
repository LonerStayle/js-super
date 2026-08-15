"""CLAUDE.md 에서 가져온 셸 명령이 읽기 전용인지 검사한다.

결합 룰은 파이프가 들어간 셸 파이프라인이라 인자 배열로 표현되지 않는다.
그래서 셸을 거치되, 거치기 전에 이 관문을 통과해야 한다 (설계서 D5).
관문에 걸린 룰은 조용히 통과시키지 않고 차단 상태로 보고한다.

지금 저장소의 룰 111건은 전부 읽기 전용이지만, 앞으로 누가 쓰기 명령을
넣지 않는다는 보장이 없다. 그 경우를 형식 차원에서 막는 것이 이 모듈이다.

검사는 따옴표를 인식한다. 이걸 안 하면 `grep -nE "a|b"` 의 파이프나
`grep "<style>"` 의 꺾쇠를 실제 파이프·리다이렉션으로 오인한다.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

ALLOWED = {
    "grep", "ls", "test", "awk", "sed", "find", "cat", "wc",
    "head", "tail", "echo", "sort", "uniq", "cut", "tr",
    "python3", "git", "true", "false", "[", "basename", "dirname",
    "printf", "diff", "comm", "md5", "shasum", "sha256sum", "stat",
}

# 자체적으로는 아무것도 실행하지 않는 셸 제어 낱말.
KEYWORDS = {
    "for", "do", "done", "if", "then", "else", "elif", "fi",
    "while", "until", "case", "esac", "in", "!",
}

GIT_ALLOWED = {
    "status", "diff", "log", "ls-files", "rev-parse", "show", "check-ignore",
    "worktree",
}
GIT_WORKTREE_ALLOWED = {"list"}

FORBIDDEN_HEADS = {
    "rm", "mv", "cp", "mkdir", "touch", "chmod", "chown", "ln",
    "tee", "dd", "curl", "wget", "npm", "pip", "pip3",
}

PY_WRITE = re.compile(
    r"open\s*\([^)]*['\"][wax]"
    r"|os\.(remove|unlink|rmdir|rename|makedirs|mkdir)"
    r"|shutil\.(rmtree|move|copy)"
    r"|\.(write_text|write_bytes|unlink|mkdir|touch)\s*\("
)

SEPARATORS = ("&&", "||", "|", ";", "\n")

# fixture README 는 <slug> / <date> / <SHA> 같은 자리표시자를 쓴다.
# 그대로는 실행되지 않으므로 리다이렉션으로 오인하기 전에 먼저 걸러낸다.
PLACEHOLDER = re.compile(r"<[a-zA-Z][\w-]*>")

# `NAME=value` 형태의 변수 대입.
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str = ""


def check_read_only(command: str) -> GuardResult:
    """셸 명령이 읽기 전용이면 허용, 아니면 이유와 함께 차단."""
    command = _join_continuations(command)

    masked = mask_quoted(command)
    if masked is None:
        return GuardResult(False, "따옴표가 닫히지 않음")

    if PLACEHOLDER.search(masked):
        return GuardResult(False, "자리표시자가 있어 그대로 실행 불가")
    if _has_write_redirect(masked):
        return GuardResult(False, "출력 리다이렉션 사용")
    if "`" in masked:
        return GuardResult(False, "역따옴표 명령 치환 사용")
    if PY_WRITE.search(command):
        return GuardResult(False, "파이썬 쓰기 호출 포함")

    for inner in _substitutions(command, masked):
        nested = check_read_only(inner)
        if not nested.allowed:
            return GuardResult(False, f"명령 치환 안에서 차단: {nested.reason}")

    for segment in _segments(command, masked):
        verdict = _check_segment(segment)
        if not verdict.allowed:
            return verdict

    return GuardResult(True)


def _check_segment(segment: str) -> GuardResult:
    try:
        words = shlex.split(_blank_substitutions(segment))
    except ValueError:
        return GuardResult(False, "따옴표가 닫히지 않음")

    # `for f in a b c` 는 아무것도 실행하지 않는다. 루프 변수와 값 목록을 건너뛴다.
    if words and words[0] == "for":
        if "in" in words:
            words = words[words.index("in") + 1:]
            return GuardResult(True)  # 값 목록은 실행되지 않는다
        words = words[2:]

    while words and words[0] in KEYWORDS:
        words = words[1:]

    # `n=$(basename ...)` 같은 변수 대입. 대입 자체는 아무것도 안 쓴다.
    # 오른쪽의 명령 치환은 이미 위에서 재귀 검사했다.
    while words and ASSIGNMENT.match(words[0]):
        words = words[1:]

    if not words:
        return GuardResult(True)

    head = words[0]
    if head in FORBIDDEN_HEADS:
        return GuardResult(False, f"쓰기 계열 명령: {head}")
    if head not in ALLOWED:
        return GuardResult(False, f"허용 목록 밖 명령: {head}")

    if head == "git":
        sub = next((w for w in words[1:] if not w.startswith("-")), "")
        if sub not in GIT_ALLOWED:
            return GuardResult(False, f"허용 목록 밖 git 하위 명령: {sub or '(없음)'}")
        if sub == "worktree":
            after = words[words.index(sub) + 1:]
            verb = next((w for w in after if not w.startswith("-")), "")
            if verb not in GIT_WORKTREE_ALLOWED:
                return GuardResult(False, f"git worktree {verb or '(없음)'} 는 허용 안 함")

    if head == "sed":
        flags = [w for w in words[1:] if w.startswith("-")]
        if any(f.startswith("-i") for f in flags):
            return GuardResult(False, "sed -i 는 파일을 고침")
        if not any(f.startswith("-n") for f in flags):
            return GuardResult(False, "sed 는 -n 과 함께만 허용")

    return GuardResult(True)


def _blank_substitutions(segment: str) -> str:
    """`$( ... )` 를 낱말 하나로 뭉친다.

    안 그러면 `n=$(basename "$c" .md)` 가 shlex 에서 여러 낱말로 쪼개져
    변수 대입 판정이 깨진다. 안쪽 명령은 이미 재귀로 따로 검사했다.
    """
    out: list[str] = []
    index = 0
    while index < len(segment):
        if segment.startswith("$(", index):
            depth = 1
            cursor = index + 2
            while cursor < len(segment) and depth:
                if segment[cursor] == "(":
                    depth += 1
                elif segment[cursor] == ")":
                    depth -= 1
                cursor += 1
            out.append("SUBST")
            index = cursor
            continue
        out.append(segment[index])
        index += 1
    return "".join(out)


def _join_continuations(command: str) -> str:
    """줄 끝 역슬래시로 이어진 줄을 한 줄로 합친다.

    이걸 안 하면 여러 줄에 걸친 명령이 줄바꿈에서 잘려 따옴표가 깨진다.
    """
    return re.sub(r"\\\s*\n\s*", " ", command)


def mask_quoted(command: str) -> str | None:
    """따옴표 안 내용을 같은 길이의 밑줄로 덮는다.

    구조 문자(파이프·리다이렉션)를 찾을 때 따옴표 안을 보면 안 된다.
    `grep -nE "a|b"` 의 파이프는 파이프가 아니고, `grep "<style>"` 의
    꺾쇠는 리다이렉션이 아니다. 닫히지 않은 따옴표면 None.
    """
    out: list[str] = []
    quote: str | None = None
    escaped = False

    for char in command:
        if escaped:
            out.append("_" if quote else char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            out.append("_" if quote else char)
            continue
        if quote:
            out.append("_" if char != quote else char)
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            out.append(char)
            continue
        out.append(char)

    return None if quote else "".join(out)


def _has_write_redirect(masked: str) -> bool:
    """따옴표 밖의 출력 리다이렉션을 찾는다.

    `2>/dev/null` 처럼 버리는 리다이렉션은 허용한다. 실제로 파일이 생기지
    않고, CLAUDE.md 룰이 잡음을 줄이려고 흔히 쓴다.
    """
    for match in re.finditer(r">{1,2}", masked):
        start, end = match.span()
        if end < len(masked) and masked[end] == "&":
            continue
        tail = masked[end:].lstrip()
        if tail.startswith("/dev/null"):
            continue
        return True
    return False


def _substitutions(command: str, masked: str) -> list[str]:
    """따옴표 밖의 $( ... ) 안쪽 명령을 뽑는다."""
    found: list[str] = []
    index = 0
    while True:
        start = masked.find("$(", index)
        if start == -1:
            return found
        depth = 0
        for cursor in range(start + 1, len(masked)):
            if masked[cursor] == "(":
                depth += 1
            elif masked[cursor] == ")":
                depth -= 1
                if depth == 0:
                    found.append(command[start + 2:cursor])
                    index = cursor + 1
                    break
        else:
            return found


def _segments(command: str, masked: str) -> list[str]:
    """따옴표 밖의 파이프·세미콜론·논리연산으로 구간을 나눈다.

    파이프 뒤 구간을 검사하지 않으면 `grep x | rm -rf y` 가 통과한다.
    """
    cuts = [0]
    index = 0
    while index < len(masked):
        for sep in SEPARATORS:
            if masked.startswith(sep, index):
                cuts.append(index)
                cuts.append(index + len(sep))
                index += len(sep)
                break
        else:
            index += 1
    cuts.append(len(masked))

    parts: list[str] = []
    for start, end in zip(cuts[::2], cuts[1::2]):
        chunk = command[start:end].strip()
        if chunk and chunk not in SEPARATORS:
            parts.append(chunk)
    return parts
