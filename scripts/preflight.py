"""Deterministic pre-flight checks for js-super-sub-driven skills.

Replaces LLM inference in skill pre-flight steps with bash-callable Python
helpers. Each function returns a PreflightResult; callers parse exit code
0 (ok) / 1 (fail with reason on stderr or stdout).
"""
import re
from pathlib import Path
from typing import NamedTuple


class PreflightResult(NamedTuple):
    ok: bool
    reason: str
    human_reason: str = ""  # v1.1.15+ optional 한국어 1줄 설명. backward compat: default 빈 문자열.


_PLAN_MD_PATTERN = re.compile(r".*-implementation-plan\.md$")
_CHANGELOG_ENTRY = re.compile(r"^### \[", re.MULTILINE)
_FRONTMATTER_COMMIT_POLICY = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL
)
_COMMIT_POLICY_LINE = re.compile(
    r"^commit_policy:\s*(per-task|single|none)\s*$", re.MULTILINE
)


def _has_changelog_entries(text: str) -> bool:
    if "## 변경이력" not in text:
        return False
    footer = text.rsplit("## 변경이력", 1)[1]
    return _CHANGELOG_ENTRY.search(footer) is not None


def _read_commit_policy(text: str) -> str:
    m = _FRONTMATTER_COMMIT_POLICY.match(text)
    if not m:
        return "per-task"
    line = _COMMIT_POLICY_LINE.search(m.group(1))
    return line.group(1) if line else "per-task"


def _plan_text_bundle(file_path: Path) -> str:
    """인덱스 + 분할 하위 문서의 본문을 이어붙인다.

    분할 구조에서는 코드 블록이 하위 문서에 있으므로, 인덱스만 읽으면
    '수정 후 블록 없음' 으로 잘못 판정한다.
    """
    from scripts.plan_guard import resolve_documents

    parts = []
    for path in resolve_documents(file_path).all_paths:
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def code_pretty_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(
            False,
            f"file not found: {file_path}",
            f"대상 파일이 존재하지 않습니다: {file_path}",
        )
    if not _PLAN_MD_PATTERN.match(str(file_path)):
        return PreflightResult(
            False,
            "code-pretty target must be implementation-plan.md",
            "code-pretty 대상은 -implementation-plan.md 파일이어야 합니다",
        )
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(
            False,
            "변경이력 footer not empty (doc is live)",
            "이미 변경이력 entry 가 존재합니다 (live doc). code-pretty 는 최초 생성 단계에서만 발화합니다",
        )
    # ⚠️ RISK(side-effect): 분할 구조에서는 코드 블록이 하위 문서에 있어 인덱스 본문만으로 판정하면 오탐 — by 구현계획서-코드강제-분할 task 2
    if "**수정 후**" not in _plan_text_bundle(file_path):
        return PreflightResult(
            False,
            "no '수정 후' code blocks found — nothing to prettify",
            "'수정 후' 코드 블록이 없습니다. prettify 할 내용이 없습니다",
        )
    return PreflightResult(True, "ok", "정상")


def execute_plan_mode_check(plan_path: Path) -> PreflightResult:
    if not plan_path.exists():
        hint = ""
        if feature_depth(plan_path.parent) == 2:
            hint = (
                " — 이 피처는 2개 문서로 확정된 트랙입니다."
                " 구현이 필요해졌다면 /write-plan 으로 승격하세요."
            )
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"구현계획서를 찾을 수 없습니다: {plan_path}{hint}",
        )
    text = plan_path.read_text(encoding="utf-8")
    policy = _read_commit_policy(text)
    return PreflightResult(True, f"commit_policy={policy}", f"정상 (commit_policy: {policy})")


def subagent_task_entry_check(plan_path: Path) -> PreflightResult:
    if not plan_path.exists():
        hint = ""
        if feature_depth(plan_path.parent) == 2:
            hint = (
                " — 이 피처는 2개 문서로 확정된 트랙입니다."
                " 구현이 필요해졌다면 /write-plan 으로 승격하세요."
            )
        return PreflightResult(
            False,
            f"plan not found: {plan_path}",
            f"플랜 파일이 존재하지 않습니다: {plan_path}{hint}",
        )
    text = plan_path.read_text(encoding="utf-8")
    policy = _read_commit_policy(text)
    if policy != "per-task":
        return PreflightResult(
            False,
            f"js-super-sub-driven requires commit_policy: per-task (got {policy})",
            f"js-super-sub-driven 는 commit_policy: per-task 를 요구합니다 (현재: {policy})",
        )
    return PreflightResult(True, "ok", "정상")


_DEPTH_LINE = re.compile(r"^depth:\s*([23])\s*$", re.MULTILINE)


# ⚠️ RISK(side-effect): 공유 preflight helper — execute_plan/subagent 진입 안내가 이 판독에 의존, 판독 실패는 3-doc 안전 fallback — by 산출물-깊이-선택 task 1
def feature_depth(feature_dir: Path) -> int:
    """피처 폴더의 산출물 깊이 (산출물 깊이 선택 기능).

    *-tech-design.md 의 frontmatter 에 depth: 2 가 명시된 경우에만 2 (2-doc
    확정 트랙). 필드 부재 / depth: 3 / 파일 부재 / 파싱 실패는 전부 3 (기존
    3-doc 기본 트랙). 판독 규칙 엄격 — 안전한 방향(3)으로 fallback.
    """
    if not feature_dir.exists():
        return 3
    for md in sorted(feature_dir.glob("*-tech-design.md")):
        m = _FRONTMATTER_COMMIT_POLICY.match(md.read_text(encoding="utf-8"))
        if not m:
            continue
        line = _DEPTH_LINE.search(m.group(1))
        if line and line.group(1) == "2":
            return 2
    return 3


# ---------------------------------------------------------------------------
# 뮤테이션 도구 사전 확인 — 실행 흐름 진입 시 한 번만 묻기
#
# 게이트는 도구가 없으면 C7 을 건너뛰고 설치 안내를 결과 표에 싣는다. 그 안내는
# 커밋 직전에야 나와 그 회차는 이미 뮤테이션 없이 지나간 뒤다. 여기서는 흐름 진입
# 시점에 "이 프로젝트 언어의 도구가 없는가" 를 먼저 보고, 없으면 커맨드가 한 번
# 묻게 한다. 답은 .js-super/mutation-tools.json 에 언어별로 남겨 다시 묻지 않는다.
#
# 기록은 .code-gate.json 에 쓰지 않는다 — 그 파일은 사람만 고친다 (게이트의 회피
# 방지 장치). 도구 유무 판정과 설치 명령의 출처는 게이트와 어댑터다. 여기서 이름을
# 다시 적으면 어댑터를 더할 때 이 파일이 뒤처진다.
# ---------------------------------------------------------------------------

import json
import os
import subprocess
import sys
from datetime import datetime

MUTATION_TOOLS_MARKER = Path(".js-super") / "mutation-tools.json"
MUTATION_DECISIONS = ("declined", "installed", "install_failed", "noted")
_MUTATION_DECISION_KO = {
    "declined": "설치하지 않음 (다시 묻지 않음)",
    "installed": "설치함",
    "install_failed": "설치 실패 (다시 묻지 않음)",
    "noted": "안내함",
}
# 프로젝트 언어를 셀 때 들어가지 않는 폴더. 숨김 폴더(`.`)도 전부 뺀다.
_SCAN_SKIP_DIRS = frozenset({
    "node_modules", "venv", "__pycache__", "dist", "build", "target", "bin", "obj",
    "vendor", "site-packages",
})
_SCAN_MAX_DEPTH = 8
_INSTALL_CMD_IN_PARENS = re.compile(r"\(([^()]*)\)")


class MutationToolStatus(NamedTuple):
    language: str
    label: str
    tool: str
    default_enabled: bool
    has_files: bool
    has_tests: bool
    tool_present: bool
    install_cmd: str
    install_scope: str    # "project" (가상환경 · node_modules) / "user" (PATH) / ""
    decision: str         # 기록된 값 (MUTATION_DECISIONS) 또는 ""
    ask: bool
    note: str


class MutationToolsResult(NamedTuple):
    ask: tuple            # 이번에 물을 언어 (MutationToolStatus)
    notes: tuple          # 한 번만 보여줄 안내 (기본 꺼짐 언어)
    statuses: tuple       # 등록된 언어 전부
    human_reason: str


def _gate():
    """게이트 모듈을 늦게 가져온다. preflight 의 다른 함수는 게이트를 모른다."""
    if __package__ in (None, ""):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts import code_gate
    return code_gate


def _scan_allowed(rel: Path) -> bool:
    parts = rel.parts[:-1]
    return not any(p.startswith(".") or p in _SCAN_SKIP_DIRS for p in parts)


def _project_files(repo_root: Path) -> list:
    """프로젝트 파일의 상대 경로. git 이 있으면 무시 규칙을 따르고, 없으면 직접 훑는다."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            return [Path(p) for p in proc.stdout.split("\0") if p and _scan_allowed(Path(p))]
    except (OSError, subprocess.TimeoutExpired):
        pass
    found = []
    base_depth = len(repo_root.resolve().parts)
    for dirpath, dirnames, filenames in os.walk(repo_root):
        current = Path(dirpath)
        if len(current.resolve().parts) - base_depth >= _SCAN_MAX_DEPTH:
            dirnames[:] = []
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in _SCAN_SKIP_DIRS)
        for name in filenames:
            found.append((current / name).relative_to(repo_root))
    return found


def _adapter_suffixes(adapter) -> frozenset:
    """어댑터 모듈이 신고한 대상 확장자 (`MUTATION_*SUFFIXES`). 이름을 여기 적지 않는다."""
    out: set = set()
    for name, value in vars(adapter.module).items():
        if name.startswith("MUTATION_") and name.endswith("SUFFIXES") and isinstance(value, (set, frozenset)):
            out |= set(value)
    return frozenset(out)


def _package_json(repo_root: Path) -> dict:
    try:
        loaded = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _js_runner_plugin(repo_root: Path, adapter) -> str | None:
    """프로젝트 테스트 러너에 맞는 Stryker 러너 플러그인 디렉토리 이름. 못 정하면 None."""
    pkg = _package_json(repo_root)
    deps = {**(pkg.get("devDependencies") or {}), **(pkg.get("dependencies") or {})}
    test_script = str((pkg.get("scripts") or {}).get("test", ""))
    for directory, runner in adapter.module.STRYKER_RUNNER_PLUGINS:
        if runner in deps or runner in test_script.split():
            return directory
    return None


def _js_runner_ready(repo_root: Path, adapter) -> bool:
    """러너 플러그인이 깔려 있거나 프로젝트 Stryker 설정이 있으면 게이트가 돈다."""
    base = repo_root / "node_modules" / "@stryker-mutator"
    if any((base / directory).is_dir() for directory, _runner in adapter.module.STRYKER_RUNNER_PLUGINS):
        return True
    return any((repo_root / name).is_file() for name in adapter.module.STRYKER_CONFIG_NAMES)


def _has_tests(language: str, repo_root: Path, files: list, gate) -> bool:
    """묻기 위한 대략 판정 — 테스트가 없으면 도구를 깔아도 못 재므로 묻지 않는다."""
    if language == "python":
        return bool(gate.detect_pytest_paths(repo_root))
    if language == "javascript":
        pkg = _package_json(repo_root)
        deps = {**(pkg.get("devDependencies") or {}), **(pkg.get("dependencies") or {})}
        runners = ("vitest", "jest", "mocha", "jasmine", "karma", "tap")
        return bool((pkg.get("scripts") or {}).get("test")) or any(r in deps for r in runners)
    if language == "go":
        return any(f.name.endswith("_test.go") for f in files)
    if language == "csharp":
        return any(
            (f.suffix.lower() == ".cs" and f.stem.lower().endswith(("test", "tests")))
            or (f.suffix.lower() == ".csproj" and "test" in f.stem.lower())
            for f in files
        )
    return False  # 기본 꺼짐 언어는 묻지 않으므로 계산하지 않는다


def _tool_present(language: str, repo_root: Path, adapter, tools: dict) -> bool:
    present = bool(tools.get(adapter.spec.tool, {}).get("available"))
    if language == "javascript":
        return present and _js_runner_ready(repo_root, adapter)
    return present


def _inside(path: str, repo_root: Path) -> bool:
    """path 가 repo_root 아래인가. 심링크는 풀지 않는다 — 가상환경의 python 은 대개 시스템 인터프리터로의 심링크다."""
    target = os.path.abspath(path)
    roots = {os.path.abspath(str(repo_root)), str(repo_root.resolve())}
    return any(target.startswith(root.rstrip(os.sep) + os.sep) for root in roots)


def _install_plan(language: str, repo_root: Path, adapter, tools: dict, gate) -> tuple:
    """(설치 명령, 범위, 덧붙일 한 줄). 명령은 그대로 실행할 수 있는 한 줄이어야 한다."""
    if language == "python":
        names = [n for n in ("pytest", "mutmut") if not tools.get(n, {}).get("available")]
        python_exe = gate.resolve_python(repo_root)
        cmd = f"{python_exe} -m pip install {' '.join(names)}"
        if os.environ.get("VIRTUAL_ENV") or _inside(python_exe, repo_root):
            return cmd, "project", ""
        # 가상환경이 없으면 pip 는 시스템 파이썬에 깐다. "프로젝트 로컬" 이라고 적으면 거짓이다.
        return cmd, "user", f"프로젝트 가상환경을 찾지 못해 {python_exe} 에 설치됩니다. 가상환경(.venv)을 먼저 만들면 프로젝트 안에 들어갑니다."
    if language == "javascript":
        packages = []
        if not tools.get("stryker", {}).get("available"):
            packages.append("@stryker-mutator/core")
        note = ""
        if not _js_runner_ready(repo_root, adapter):
            plugin = _js_runner_plugin(repo_root, adapter)
            if plugin:
                packages.append(f"@stryker-mutator/{plugin}")
            else:
                note = "테스트 러너에 맞는 플러그인(@stryker-mutator/<러너>-runner)도 따로 필요합니다."
        return f"npm i -D {' '.join(packages)}", "project", note
    hint = getattr(adapter.module, "_INSTALL_HINT", "") or ""
    found = _INSTALL_CMD_IN_PARENS.search(hint)
    return (found.group(1) if found else hint), "user", ""


def read_mutation_decisions(repo_root: Path) -> dict:
    """기록 파일의 언어 → 결정. 없거나 깨졌으면 빈 dict (깨진 파일은 없는 것으로 본다)."""
    try:
        data = json.loads((repo_root / MUTATION_TOOLS_MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for language, entry in data.items():
        decision = entry.get("decision") if isinstance(entry, dict) else None
        if decision in MUTATION_DECISIONS:
            out[str(language)] = decision
    return out


def record_mutation_decision(repo_root: Path, language: str, decision: str) -> Path:
    """언어 하나의 결정을 기록한다. 다른 언어의 기록은 그대로 둔다."""
    if decision not in MUTATION_DECISIONS:
        raise ValueError(f"unknown decision: {decision} (allowed: {', '.join(MUTATION_DECISIONS)})")
    languages = {adapter.language for adapter in _gate()._registered_adapters()}
    if language not in languages:
        raise ValueError(f"unknown language: {language} (allowed: {', '.join(sorted(languages))})")
    path = repo_root / MUTATION_TOOLS_MARKER
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data[language] = {"decision": decision, "at": datetime.now().isoformat(timespec="seconds")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _status_line(status: MutationToolStatus) -> str:
    if status.ask:
        return f"{status.label} ({status.tool} 없음)"
    if status.decision:
        return f"{status.label}: 기록됨 ({_MUTATION_DECISION_KO[status.decision]})"
    if not status.default_enabled:
        return f"{status.label}: 기본 꺼짐"
    if not status.has_tests:
        return f"{status.label}: 테스트 없음"
    return f"{status.label}: {status.tool} 있음"


def mutation_tools_check(repo_root: Path, *, probe=None) -> MutationToolsResult:
    """이 프로젝트에서 뮤테이션 도구를 물을 언어를 고른다.

    묻는 조건은 넷을 모두 만족할 때다 — 지원 언어 파일이 있고, 테스트가 있고, 도구가
    없고, 기록이 없다. 기본이 꺼진 언어(자바 · 러스트)는 묻지 않고 켜는 법만 안내한다.
    `probe` 는 도구 유무를 주는 함수 (기본은 게이트의 `probe_tools`). 파일을 쓰지 않는다.
    """
    gate = _gate()
    repo_root = Path(repo_root)
    files = _project_files(repo_root)
    decisions = read_mutation_decisions(repo_root)
    tools = (probe or gate.probe_tools)(repo_root, gate.resolve_python(repo_root))
    statuses = []
    for adapter in gate._registered_adapters():
        language = adapter.language
        suffixes = _adapter_suffixes(adapter)
        has_files = any(f.suffix.lower() in suffixes for f in files)
        has_tests = has_files and _has_tests(language, repo_root, files, gate)
        present = _tool_present(language, repo_root, adapter, tools)
        decision = decisions.get(language, "")
        default_enabled = bool(getattr(adapter.spec, "default_enabled", True))
        ask = default_enabled and has_files and has_tests and not present and not decision
        install_cmd, scope, note = _install_plan(language, repo_root, adapter, tools, gate) if ask else ("", "", "")
        if not default_enabled and has_files and not decision:
            reason = getattr(adapter.spec, "default_off_reason", "") or "바닥 비용이 커서"
            note = (f"{adapter.label} 파일이 있지만 뮤테이션은 기본 꺼짐입니다 ({reason}). "
                    f"켜려면 .code-gate.json 의 mutation 에 \"{adapter.config_leaf}\": \"{adapter.spec.tool}\" 를 적으십시오.")
        statuses.append(MutationToolStatus(
            language=language, label=adapter.label, tool=adapter.spec.tool,
            default_enabled=default_enabled, has_files=has_files, has_tests=has_tests,
            tool_present=present, install_cmd=install_cmd, install_scope=scope,
            decision=decision, ask=ask, note=note,
        ))
    ask = tuple(s for s in statuses if s.ask)
    notes = tuple(s.note for s in statuses if s.note and not s.ask)
    with_files = [s for s in statuses if s.has_files]
    if ask:
        human = "뮤테이션 도구 확인: 물을 것 있음 — " + ", ".join(_status_line(s) for s in ask)
    elif with_files:
        human = "뮤테이션 도구 확인: 물을 것 없음 (" + " / ".join(_status_line(s) for s in with_files) + ")"
    else:
        human = "뮤테이션 도구 확인: 물을 것 없음 (지원 언어 파일이 없습니다)"
    return MutationToolsResult(ask=ask, notes=notes, statuses=tuple(statuses), human_reason=human)


def _repo_root_of(path: Path) -> Path:
    try:
        proc = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=10)
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return path


def _cli_mutation_tools(argv: list) -> int:
    """`python3 preflight.py mutation-tools [--root DIR] [--record LANG=DECISION]`.

    첫 줄은 항상 MUTATION_TOOLS_ASK 또는 MUTATION_TOOLS_OK 다 — 커맨드 본문이 그 줄로
    분기한다. 기본 꺼짐 언어의 안내는 이 CLI 가 보여준 뒤 `noted` 로 기록해 한 번만 나온다.
    """
    root = None
    record = None
    args = list(argv)
    while args:
        item = args.pop(0)
        if item == "--root" and args:
            root = Path(args.pop(0))
        elif item == "--record" and args:
            record = args.pop(0)
        else:
            print(f"알 수 없는 인자: {item}", file=sys.stderr)
            return 2
    repo_root = root or _repo_root_of(Path.cwd())
    if record is not None:
        language, sep, decision = record.partition("=")
        if not sep:
            print("--record 는 <언어>=<결정> 형식입니다 (예: python=declined).", file=sys.stderr)
            return 2
        try:
            path = record_mutation_decision(repo_root, language, decision)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"기록했습니다: {language} → {_MUTATION_DECISION_KO[decision]} ({path})")
        return 0
    result = mutation_tools_check(repo_root)
    print("MUTATION_TOOLS_ASK" if result.ask else "MUTATION_TOOLS_OK")
    print(result.human_reason)
    scope_ko = {"project": "프로젝트 로컬", "user": "사용자 환경 (프로젝트 밖)"}
    for status in result.ask:
        line = f"- {status.language} | {status.label} | {status.tool} 없음 | 설치 범위: {scope_ko.get(status.install_scope, '')} | 설치 명령: {status.install_cmd}"
        if status.note:
            line += f" | {status.note}"
        print(line)
    for status in result.statuses:
        if status.note and not status.ask:
            print(f"안내: {status.note}")
            record_mutation_decision(repo_root, status.language, "noted")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "mutation-tools":
        sys.exit(_cli_mutation_tools(sys.argv[2:]))
    print("사용법: python3 preflight.py mutation-tools [--root DIR] [--record LANG=DECISION]", file=sys.stderr)
    sys.exit(2)
