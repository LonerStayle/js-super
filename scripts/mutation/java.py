"""C7 뮤테이션 — 자바 어댑터 (PIT / pitest, Gradle init script 주입).

이 어댑터의 사실관계는 pitest 1.22.0 을 Gradle 9.7.1 + JDK 26 에서 실물로 돌려
확인한 것이다. 네 가지가 구현을 좌우한다.
  - PIT 는 **바이트코드를 메모리에서** 변이한다. 사용자 소스를 여는 단계가 없어,
    중간에 강제 종료해도 소스가 변이된 채 남지 않는다 (실측: SIGTERM·SIGKILL 양쪽).
  - 도구는 init script(`gradle -I`)로 밖에서 붙인다. `build.gradle` 을 고치지 않는다.
  - `targetTests` 를 안 주면 Gradle 플러그인이 그 값을 `targetClasses` 로 채워,
    변경분만 재려 할 때 같은 코드가 통째로 "덮은 테스트 없음" 으로 뒤집힌다 (실측:
    같은 입력에 NO_COVERAGE 8 ↔ SURVIVED 7 / KILLED 1). 그래서 늘 넓게 잡는다.
  - 사용자 `build.gradle` 에 임계값이 있으면 그 값이 살아남아 종료 코드 1 이 된다.
    init script 안에서 임계값 셋을 0 으로 덮는다 (R2). 덮는 것은 우리 스크립트 안이고
    사용자 파일은 그대로다.

버전을 못박는 이유: pitest 1.20.0 이하는 자바 26 바이트코드를 못 읽고(`Unsupported
class file major version 70`), 1.23.0 이상은 내장 증분이 상용 플러그인으로 빠졌다
(`History has been enabled but no history plugin has been installed`). 1.22.0 이
둘 다 되는 마지막 판이다 (실측으로 경계를 찍었다).

서브프로세스는 뼈대의 `gate._run` 만 쓴다. 형제 어댑터는 import 하지 않는다.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts import code_gate as gate
from scripts.mutation import score as score_mod

MUTATION_JAVA_SUFFIXES = frozenset({".java"})

# "대상이 없다" 안내에 실을 대상 설명 (레지스트리가 읽는다).
MUTATION_TARGET_KO = "자바 (Gradle 프로젝트만)"

# 못박은 버전 셋. 위 파일 머리말의 실측 경계에서 왔다.
PITEST_VERSION = "1.22.0"
PITEST_GRADLE_PLUGIN = "1.19.0"
PITEST_JUNIT5_PLUGIN = "1.2.1"

# PIT 어휘 → 게이트 어휘. **실물로 관측한 넷만** 넣는다 (실측: KILLED / SURVIVED /
# NO_COVERAGE / TIMED_OUT). PIT 소스의 DetectionStatus 에는 NON_VIABLE /
# MEMORY_ERROR / NOT_STARTED / STARTED / RUN_ERROR / EQUIVALENT 도 있지만 실물을
# 만들어 보지 못해 대응을 정하지 않았다. 짐작으로 채우면 잘못 센다 — 표 밖 낱말은
# 원어 그대로 통과해 unknown 경로가 잡고 분모에서 뺀다 (R4).
PIT_STATUS_TO_GATE = {
    "KILLED": "Killed",
    "SURVIVED": "Survived",
    "NO_COVERAGE": "NoCoverage",
    "TIMED_OUT": "Timeout",
}

_INSTALL_HINT = "Gradle 을 설치하십시오 (예: brew install gradle)."

# 변이 대상에서 빼는 자리와 이름 — 테스트 코드와 선언 전용 파일.
_JAVA_TEST_DIR = re.compile(r"(^|/)src/(test|integrationTest|testFixtures)/")
_JAVA_TEST_STEMS = ("Test", "Tests", "IT", "TestCase")
_JAVA_DECLARATION_STEMS = frozenset({"package-info", "module-info"})

_JAVA_PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_$][\w.$]*)\s*;", re.MULTILINE)
# 중괄호와 타입 선언을 **한 번에 순서대로** 훑는다. 둘을 따로 찾으면 어느 선언이 어느
# 깊이에 있었는지 알 수 없어 최상위 판정이 성립하지 않는다.
_JAVA_SCAN_RE = re.compile(r"[{}]|\b(?:class|interface|enum|record)\s+([A-Za-z_$][\w$]*)")
# (여는 표시, 닫는 표시, 닫는 표시를 몇 글자 건너뛸지). `//` 는 줄바꿈을 남긴다.
_JAVA_SKIP_SPANS = (("//", "\n", 0), ("/*", "*/", 2), ('"""', '"""', 3))
# JUnit5 고유 식별자에서 사람이 읽을 부분만 꺼낸다.
_PIT_TEST_CLASS_RE = re.compile(r"\[class:([^\]]+)\]")
_PIT_TEST_METHOD_RE = re.compile(r"\[method:([^\]]+)\]")

_PIT_NO_MUTATIONS = "No mutations found"
_PIT_RED_SUITE = "did not pass without mutation"
_PIT_NO_HISTORY_PLUGIN = "no history plugin"
_PIT_OLD_ASM = "Unsupported class file major version"


def _gate_status(word):
    """도구가 쓴 낱말을 게이트 어휘로. 표에 없으면 원어 그대로 (unknown 경로)."""
    return PIT_STATUS_TO_GATE.get(word, word)


# ---------------------------------------------------------------------------
# 대상 고르기 — 파일 경로를 PIT 가 아는 클래스 이름으로 옮긴다
# ---------------------------------------------------------------------------

def _java_is_test(rel: str) -> bool:
    """테스트 파일인가. 자리(src/test)와 이름(…Test) 둘 다 본다."""
    stem = Path(rel).stem
    return bool(_JAVA_TEST_DIR.search(rel)) or any(stem.endswith(s) for s in _JAVA_TEST_STEMS)


def _java_skip_span(text: str, i: int) -> int | None:
    """i 자리에서 시작하는 주석·텍스트 블록이 끝난 다음 자리. 시작이 아니면 None."""
    for opener, closer, keep in _JAVA_SKIP_SPANS:
        if text.startswith(opener, i):
            end = text.find(closer, i + len(opener))
            return len(text) if end < 0 else end + keep
    return None


def _java_skip_quoted(text: str, i: int) -> int:
    """따옴표 리터럴이 끝난 다음 자리. 역슬래시 이스케이프를 건너뛴다."""
    quote = text[i]
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
        elif text[j] in (quote, "\n"):
            return j + 1
        else:
            j += 1
    return len(text)


def _java_strip_literals(text: str) -> str:
    """주석과 문자열·문자 리터럴을 지운 사본.

    중괄호 깊이로 최상위 여부를 가르는데, 문자열 안의 중괄호가 깊이를 흔들면 그 판정이
    통째로 어긋난다. 그래서 깊이를 세기 전에 먼저 지운다.
    """
    out: list = []
    i = 0
    while i < len(text):
        end = _java_skip_span(text, i)
        if end is not None:
            i = end
        elif text[i] in "\"'":
            i = _java_skip_quoted(text, i)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _java_top_level_types(text: str) -> tuple:
    """파일이 선언한 최상위 타입 이름 전부. 중첩·지역 타입은 여기 없다.

    중첩 타입은 PIT 가 `바깥$안` 이라는 별개 이름으로 보므로 대상 목록에서 `$*` 로 덮는다
    (`_pit_target_classes`). 이 함수는 그 `바깥` 만 모은다.
    """
    names: list = []
    depth = 0
    for found in _JAVA_SCAN_RE.finditer(_java_strip_literals(text)):
        name = found.group(1)
        if name is None:
            depth += 1 if found.group(0) == "{" else -1
        elif depth == 0:
            names.append(name)
    return tuple(dict.fromkeys(names))


def _java_class_names(repo_root: Path, rel: str) -> tuple:
    """파일이 선언한 최상위 타입의 `패키지.이름` 전부. 파일을 못 읽으면 빈 튜플.

    파일 이름에서 클래스 이름을 짐작하던 때는 두 가지가 조용히 빠졌다 (실측). 파일 이름과
    다른 최상위 클래스가 든 파일은 한 줄도 재지 못했고, 파일 이름과 같은 클래스가 함께
    있으면 그 하나만 재고 **나머지는 대조에도 안 걸렸다** — `_mutation_gaps` 는 파일
    단위라, 그 파일에 기록이 하나라도 있으면 "쟀다" 로 분류하기 때문이다. 한 파일에 변이
    12개가 있는데 2개만 재고 "통과 100%" 가 나왔다.
    """
    try:
        text = (repo_root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ()
    package = _JAVA_PACKAGE_RE.search(text)
    prefix = f"{package.group(1)}." if package else ""
    return tuple(prefix + name for name in _java_top_level_types(text))


def _java_targets(repo_root: Path, files) -> tuple:
    """(대상 [(경로, 클래스 이름들)], 뺀 경로). 테스트·선언 전용·삭제된 파일은 뺀다."""
    targets: list = []
    dropped: list = []
    for rel in files:
        names = _java_class_names(repo_root, rel) if (repo_root / rel).is_file() else ()
        if not names or _java_is_test(rel) or Path(rel).stem in _JAVA_DECLARATION_STEMS:
            dropped.append(rel)
        else:
            targets.append((rel, names))
    return tuple(targets), tuple(dropped)


def _java_class_index(targets) -> dict:
    """클래스 이름 → 저장소 상대 경로. 리포트가 경로를 안 줘서 되돌리는 표다."""
    return {name: rel for rel, names in targets for name in names}


def _pit_target_classes(targets) -> list:
    """init script 의 targetClasses 목록. 최상위 이름마다 중첩 몫(`$*`)을 함께 싣는다.

    PIT 는 중첩 클래스를 `바깥$안` 이라는 별개 이름으로 본다. 최상위 이름만 주면 중첩
    클래스의 변이가 통째로 빠진다 (실측: 같은 파일에서 대상 `demo.MathX` 는 변이 2개,
    `demo.MathX` + `demo.MathX$*` 는 7개).
    대상은 **변경된 파일이 선언한 이름들**로만 넓힌다. 패키지 전체(`demo.*`)로 넓히면
    변경분 밖 클래스까지 변이돼 R3 와 R1 이 함께 흔들린다.
    """
    return [text for _rel, names in targets for name in names
            for text in (name, name + "$*")]


# ---------------------------------------------------------------------------
# 리포트 읽기 — mutations.xml
# ---------------------------------------------------------------------------

def _pit_short_test(raw: str) -> str:
    """JUnit5 고유 식별자를 사람이 읽는 이름으로. 형식이 다르면 원문 그대로."""
    found_class = _PIT_TEST_CLASS_RE.search(raw)
    found_method = _PIT_TEST_METHOD_RE.search(raw)
    if not found_class:
        return raw
    return f"{found_class.group(1)}.{found_method.group(1)}" if found_method else found_class.group(1)


def _pit_text(node, tag: str) -> str:
    """자식 태그의 텍스트. 없거나 비어 있으면 빈 문자열."""
    child = node.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _pit_line_number(node) -> int | None:
    raw = _pit_text(node, "lineNumber")
    return int(raw) if raw.isdigit() else None


def _pit_source_line(lines, line) -> str:
    """변이가 앉은 소스 줄. 자리를 벗어나면 빈 문자열.

    PIT 는 바꾼 텍스트를 주지 않고 줄 번호와 설명만 준다. 원본 자리라도 보여 줘야
    살아남은 변이 한 줄만 보고 고칠 수 있다 (R9).
    """
    if line is None or not 1 <= line <= len(lines):
        return ""
    return lines[line - 1].strip()


def _pit_record(node, index: dict, sources: dict) -> dict | None:
    """변이 하나를 게이트 기록으로. 이번 대상이 아닌 클래스면 None (R3).

    `column` 은 없다 — PIT 는 줄까지만 준다. 없는 것을 지어내지 않고 비운다.
    `tests` 는 **죽인 테스트 하나**뿐이다. Stryker 의 전체 목록과도 mutmut 의 함수
    단위와도 다른 세 번째 모양이라, 살아남은 변이에서는 알 수 없음(None)이다.
    """
    outer = _pit_text(node, "mutatedClass").split("$", 1)[0]
    rel = index.get(outer)
    if rel is None:
        return None
    line = _pit_line_number(node)
    killing = _pit_text(node, "killingTest")
    return {
        "file": rel,
        "line": line,
        "column": None,
        "mutator": _pit_text(node, "mutator").rsplit(".", 1)[-1] or None,
        "original": _pit_source_line(sources.get(rel) or [], line),
        "replacement": _pit_text(node, "description"),
        "status": _gate_status(node.get("status")),
        # 목록을 못 받은 것과 목록이 빈 것은 다르다. PIT 는 **죽인 테스트 하나**만 주고
        # 덮은 테스트 전체는 주지 않아, 살아남은 변이에서는 알 수 없음(None)이 맞다.
        "tests": [_pit_short_test(killing)] if killing else None,
        "method": _pit_text(node, "mutatedMethod"),
    }


def _pit_salvage(text: str) -> str:
    """중단돼 잘린 XML 을 파싱 가능한 데까지 되살린다.

    PIT 는 변이를 하나씩 흘려 쓴다. 예산을 넘겨 죽이면 닫는 태그가 없는 파일이 남고,
    그대로 파싱하면 `no element found` 로 통째로 버려진다 — 본 만큼은 살려서 D4 의
    "몇 개까지 봤다" 를 말할 수 있어야 한다. 마지막으로 온전히 닫힌 변이까지만 자른다.
    """
    stripped = text.rstrip()
    if stripped.endswith("</mutations>"):
        return stripped
    end = stripped.rfind("</mutation>")
    if end < 0:
        return ""
    return stripped[: end + len("</mutation>")] + "\n</mutations>"


def _pit_root(text: str):
    """되살린 XML 의 뿌리. 살릴 것이 없거나 파싱이 깨지면 None (예외로 게이트를 죽이지 않는다)."""
    body = _pit_salvage(text)
    if not body:
        return None
    try:
        return ET.fromstring(body)
    except ET.ParseError:
        return None


def _pit_records(text: str, index: dict, sources: dict) -> list:
    """mutations.xml 한 벌 → 기록 목록. 파싱이 깨지면 그 파일만 비운다."""
    root = _pit_root(text)
    if root is None:
        return []
    found = [_pit_record(node, index, sources) for node in root.iter("mutation")]
    return [record for record in found if record is not None]


def _pit_sources(repo_root: Path, targets) -> dict:
    """대상 파일의 줄 목록. 원본 자리를 보여 주려면 파일을 직접 읽어야 한다."""
    sources: dict = {}
    for rel, _name in targets:
        try:
            sources[rel] = (repo_root / rel).read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
    return sources


def parse_pit_reports(texts, index: dict, sources: dict) -> dict:
    """리포트 여러 벌(여러 모듈)을 하나의 요약으로 — 서브프로세스 없이 검증되는 순수 함수."""
    records: list = []
    for text in texts:
        records += _pit_records(text, index, sources)
    return score_mod.summarize_mutants(records)


# ---------------------------------------------------------------------------
# 실행 준비
# ---------------------------------------------------------------------------

def _groovy_quote(value) -> str:
    """Groovy 홑따옴표 문자열로 감싼다. 경로에 든 역슬래시와 따옴표를 문자 그대로 만든다."""
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def java_history_dir(repo_root: Path, notes: list) -> Path | None:
    """증분 상태(history)를 둘 자리. 만들지 못하면 None (증분 없이 전체를 돌린다).

    게이트 임시 디렉토리는 실행이 끝나면 지워져 증분이 성립하지 않고, 대상 프로젝트
    안에는 두지 않는다. 그래서 사용자 캐시 아래에 저장소별로 나눠 둔다.
    pitest 판을 이름에 넣는다 — 판이 바뀌면 기록 형식도 바뀔 수 있어 섞이면 안 된다.
    """
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    key = hashlib.sha256(str(Path(repo_root).resolve()).encode("utf-8")).hexdigest()[:16]
    target = Path(base) / "code-gate" / "mutation" / key / f"pit-{PITEST_VERSION}"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        notes.append(
            f"자바 증분 상태를 둘 캐시 디렉토리를 만들지 못해 이번에는 전체를 다시 돌렸습니다 ({type(exc).__name__})."
        )
        return None
    return target.resolve()


def _pit_paths(ctx: gate.GateContext) -> dict:
    """init script 와 리포트 자리 — 전부 게이트 임시 디렉토리 안이다.

    리포트 자리가 회차마다 새것이라 Gradle 이 `pitest` 작업을 UP-TO-DATE 로 건너뛰지
    않는다. 건너뛰면 직전 회차 리포트를 이번 결과로 착각한다 (실측).
    """
    work = (ctx.tmpdir / "mutation" / "java")
    work.mkdir(parents=True, exist_ok=True)
    work = work.resolve()
    return {"init": work / "gate-pitest.gradle", "report": work / "report"}


def pit_init_script(class_names, report_root: Path, history_root: Path | None) -> str:
    """주입할 init script 본문. 프로젝트 파일은 한 줄도 고치지 않는다.

    자리(reportDir / history)를 모듈마다 나눈다. 여러 모듈 프로젝트에서 한 자리를
    같이 쓰면 뒤 모듈이 앞 모듈의 리포트를 덮어써 조용히 한 벌만 남는다.
    임계값 셋은 0 으로 덮는다 — 사용자 설정이 살아남으면 점수가 낮을 때 종료 코드가
    1 이 되어 R2 가 깨진다. `failWhenNoMutations` 도 끈다: 변경분이 인터페이스뿐이면
    변이가 0 개인 것이 정상인데 PIT 는 그것을 오류로 본다 (실측).
    """
    targets = ", ".join(_groovy_quote(name) for name in class_names)
    history = [
        f"                historyInputLocation = file({_groovy_quote(history_root)} + '/' + slug + '.bin')",
        f"                historyOutputLocation = file({_groovy_quote(history_root)} + '/' + slug + '.bin')",
    ] if history_root is not None else []
    return "\n".join([
        "initscript {",
        "    repositories { gradlePluginPortal() }",
        "    dependencies { classpath "
        f"'info.solidsoft.gradle.pitest:gradle-pitest-plugin:{PITEST_GRADLE_PLUGIN}' }}",
        "}",
        "allprojects {",
        "    afterEvaluate { p ->",
        "        if (p.plugins.hasPlugin('java')) {",
        "            p.apply plugin: info.solidsoft.gradle.pitest.PitestPlugin",
        "            def slug = p.path.replace(':', '_')",
        "            p.pitest {",
        f"                targetClasses = [{targets}]",
        # 대상 목록과 테스트 목록은 서로 다른 자리다. 좁히면 판정이 뒤집힌다 (머리말 참조).
        "                targetTests = ['*']",
        f"                pitestVersion = '{PITEST_VERSION}'",
        f"                junit5PluginVersion = '{PITEST_JUNIT5_PLUGIN}'",
        "                outputFormats = ['XML']",
        "                timestampedReports = false",
        f"                reportDir = file({_groovy_quote(report_root)} + '/' + slug)",
        *history,
        "                mutationThreshold = 0",
        "                coverageThreshold = 0",
        "                testStrengthThreshold = 0",
        "                failWhenNoMutations = false",
        "            }",
        "        }",
        "    }",
        "}",
        "",
    ])


def _java_build_system(repo_root: Path) -> str:
    """gradle / maven / none. Maven 은 아직 지원하지 않아 이름을 갈라 둔다."""
    gradle = ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")
    if any((repo_root / name).is_file() for name in gradle):
        return "gradle"
    return "maven" if (repo_root / "pom.xml").is_file() else "none"


_JAVA_BUILD_SKIP = {
    "maven": ("Maven 프로젝트라 자바 뮤테이션을 재지 않았습니다. 지금은 Gradle 프로젝트만 지원합니다.",
              "maven project unsupported"),
    "none": ("Gradle 빌드 파일을 찾지 못해 자바 뮤테이션을 재지 않았습니다 "
             "(build.gradle / build.gradle.kts / settings.gradle 중 하나가 저장소 최상위에 있어야 합니다).",
             "no gradle build file"),
}


def _java_preconditions(ctx: gate.GateContext) -> dict | None:
    """자바 경로만의 사유. 있으면 그 결과를, 없으면 None (R4).

    설정 자리와 다룰 줄 아는 도구 이름은 선언부(config_key / tool)에서 읽는다 — 같은
    사실을 여기 또 적으면 선언과 동작이 조용히 갈린다.
    """
    configured = ctx.config.mutation_tool(JAVA_ADAPTER.language)
    if configured != JAVA_ADAPTER.tool:
        return gate._skip(
            f"설정의 {JAVA_ADAPTER.config_key} 값 '{configured}' 을 다룰 줄 몰라 재지 않았습니다.",
            f"unsupported java mutation tool: {configured}",
        )
    tool = gate._tool(ctx, "gradle")
    if not tool["available"]:
        # 뼈대의 도구 표에는 설치 문구가 없다 (PATH 조회만 한다). 어댑터가 자기 것을 낸다.
        return gate._skip("Gradle 이 설치돼 있지 않습니다.", "gradle missing",
                          tool["install_hint"] or _INSTALL_HINT)
    build = _java_build_system(ctx.repo_root)
    if build != "gradle":
        return gate._skip(*_JAVA_BUILD_SKIP[build])
    return None


def _java_scope(ctx: gate.GateContext, java_files) -> tuple:
    """변이시킬 (경로, 클래스) 목록과, 남는 것이 없을 때의 건너뜀 결과."""
    targets, dropped = _java_targets(ctx.repo_root, java_files)
    if dropped:
        ctx.notes.append(
            f"자바 뮤테이션 대상에서 테스트·선언 전용·삭제된 파일 {len(dropped)}개를 뺐습니다: "
            + score_mod._sample_list(list(dropped)))
    if not targets:
        return (), gate._skip(
            f"변경된 자바 파일 {len(java_files)}개가 모두 변이 대상이 아닙니다 "
            "(테스트·선언 전용·삭제된 파일).",
            "no mutable java targets",
        )
    return targets, None


def _pit_setup(ctx: gate.GateContext, targets) -> tuple:
    """(자리, 실행할 명령, 결과가 나온 뒤에 남길 안내). init script 를 써 두고 명령을 만든다."""
    paths = _pit_paths(ctx)
    history = java_history_dir(ctx.repo_root, ctx.notes)
    paths["init"].write_text(
        pit_init_script(_pit_target_classes(targets), paths["report"], history),
        encoding="utf-8")
    cmd = [gate._tool(ctx, "gradle")["path"], "-I", str(paths["init"]),
           "pitest", "--console=plain"]
    notes = [
        f"자바 뮤테이션은 변경된 파일 {len(targets)}개를 클래스 단위로 변이시켰습니다. "
        "그 클래스 안에서 이번에 바뀌지 않은 줄도 함께 변이됩니다. "
        f"pitest {PITEST_VERSION} 을 Gradle init script 로 밖에서 붙였고 프로젝트 빌드 파일은 "
        "고치지 않았습니다 (Gradle 이 원래 만드는 .gradle / build 디렉토리는 그대로 생깁니다).",
    ]
    notes.append(
        # 재사용되는 것은 **변이 실행**뿐이다. 덮은 테스트를 찾는 커버리지 수집은 매 회차
        # 프로젝트 테스트 전체를 다시 돌린다 (targetTests 를 좁히면 판정이 뒤집혀 넓게
        # 잡는다 — 위 target_syntax 참조). 그래서 이 항목의 바닥 비용은 프로젝트 테스트
        # 시간과 거의 1:1 이다. 통제 실험 — 변이 대상과 **무관한** 테스트에 6초를 더했더니
        # 증분 회차가 1.53초에서 7.61초가 됐다 (콜드는 2.50 → 20.60초). 변이 수는 4개로
        # 같았다. "증분" 을 그냥 빠르다는 뜻으로 읽으면 안 된다 — 테스트가 5분인 저장소면
        # 한 줄만 고쳐도 이 항목이 매 회차 5분 넘게 든다 (R1).
        "자바 뮤테이션은 증분 실행입니다. 지난 회차의 변이 결과는 재사용하지만, 덮은 테스트를 "
        "찾으려고 프로젝트 테스트 전체를 매 회차 다시 돌립니다. 그래서 이 항목의 바닥 시간은 "
        "프로젝트 테스트 시간만큼 듭니다."
        if history is not None else
        "자바 증분 상태를 둘 자리가 없어 이번에는 전체를 돌렸습니다.")
    return paths, cmd, notes


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------

def _pit_report_texts(report_root: Path) -> list:
    """모듈마다 나뉜 mutations.xml 을 전부 읽는다. 없으면 빈 목록."""
    texts: list = []
    for path in sorted(report_root.glob("*/mutations.xml")):
        try:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return texts


_PIT_CAUSES = (
    (_PIT_NO_HISTORY_PLUGIN,
     f"pitest 판이 내장 증분을 지원하지 않습니다 (게이트는 {PITEST_VERSION} 을 못박습니다). "
     "프로젝트 설정이 다른 판을 강제하고 있는지 확인하십시오."),
    (_PIT_OLD_ASM,
     "pitest 가 이 자바 판의 바이트코드를 읽지 못했습니다. 컴파일 대상 판을 낮추거나 "
     "더 새 pitest 를 쓰는 프로젝트 설정이 필요합니다."),
    (_PIT_RED_SUITE,
     "자바 테스트가 통과하지 않아 뮤테이션을 재지 못했습니다 "
     "(PIT 는 기준 스위트가 통과해야 돌아갑니다). 테스트를 먼저 고치십시오."),
)


def _pit_failure_cause(detail: str) -> str:
    """출력에서 짚이는 원인을 한국어로. 못 짚으면 빈 문자열."""
    for marker, sentence in _PIT_CAUSES:
        if marker in detail:
            return sentence
    return ""


def _pit_detail(proc) -> str:
    """실패 원문. 원인 낱말을 찾는 쪽은 개행이 살아 있는 원문을 본다."""
    return ((proc.stdout or "") + (proc.stderr or "")) if proc is not None else ""


def _pit_tail(detail: str) -> str:
    """사람용 표에 실을 꼬리. 줄바꿈과 연속 공백을 한 칸으로 접는다.

    표는 항목 하나가 한 줄이라는 전제 위에 있다. Gradle 의 컴파일 오류처럼 여러 줄인
    원문을 그대로 실으면 그 전제가 깨진다 (실측). JSON 의 human_reason 에도 개행이
    그대로 들어간다. 자바스크립트·파이썬 어댑터가 쓰는 것과 같은 방법이다.
    """
    return " ".join(detail.split())[-500:]


def _pit_no_report(proc, elapsed: float) -> dict:
    """리포트가 없을 때. 변이 0개는 정상이고 나머지는 오류다 (R4).

    `failWhenNoMutations` 를 꺼 두어 변이가 하나도 없는 회차는 종료 코드 0 으로 끝난다.
    그 경우와 진짜 실패를 종료 코드만으로는 가를 수 없어 출력을 함께 본다 (실측).
    """
    detail = _pit_detail(proc)
    if _PIT_NO_MUTATIONS in detail:
        return gate._skip(
            f"변경된 자바 클래스에서 변이가 하나도 만들어지지 않았습니다. 실행 {elapsed:.1f}초",
            "no mutants for changed java classes")
    cause = _pit_failure_cause(detail)
    code = proc.returncode if proc is not None else "?"
    return {
        "status": "error",
        "reason": f"pitest produced no report (exit {code})",
        "human_reason": (f"자바 뮤테이션 리포트가 나오지 않았습니다 (종료 코드 {code}). "
                         f"{cause} 실행 {elapsed:.1f}초  {_pit_tail(detail)}"),
        "findings": [],
    }


def _pit_partial(ctx: gate.GateContext, summary, targets, elapsed: float, budget: int) -> dict:
    """예산을 넘겨 중단됐을 때 — 본 만큼만 낸다 (D4).

    잘린 XML 에서 되살린 결과다. 완주한 회차와 문장을 다르게 해 어디까지 봤는지 말한다.
    리포트가 한 벌도 안 나온 채 끊길 수도 있다 (준비 단계에서 시간을 다 쓴 경우) —
    그때도 오류가 아니라 중단이라고 말해야 사용자가 예산을 늘릴 생각을 한다.
    """
    if summary is None:
        return {
            "status": "timeout",
            "reason": f"java mutation timed out after {budget}s (no report written)",
            "human_reason": (f"{budget}초 예산을 넘겨 중단했습니다. 리포트가 나오기 전에 끊겨 "
                             f"대상 파일 {len(targets)}개를 하나도 재지 못했습니다. "
                             "예산을 늘리십시오 (.code-gate.json 의 mutation.timeout_seconds)."),
            "findings": [],
        }
    rels = [rel for rel, _name in targets]
    total = summary["total"]
    score = summary["score"]
    score_text = f"점수 {score:.1f}%" if score is not None else "점수를 낼 변이가 없었습니다"
    return {
        "status": "timeout",
        "reason": f"java mutation timed out after {budget}s ({total} mutants seen)",
        "human_reason": (
            f"{budget}초 예산을 넘겨 중단했습니다. 변이 {total}개까지 봤고 나머지는 재지 못했습니다. "
            f"{score_text}. {score_mod._mutation_timing(elapsed, total)}"
            f"{score_mod._mutation_partial_gaps(summary, rels)}"),
        "findings": summary["survivors"],
    }


def _pit_run(ctx: gate.GateContext, paths: dict, cmd: list, targets, scope_notes: list) -> tuple:
    """실행하고 (결과, 요약) 을 만든다. 걸린 시간은 리포트를 다 읽은 뒤에 잰다.

    시간을 서브프로세스가 끝난 자리에서 재면 리포트를 읽는 시간이 보고 밖으로 샌다.
    예산은 항목 하나의 것이라 남은 만큼만 쓴다.
    """
    budget = score_mod._mutation_budget(ctx)
    # 범위 안내는 실행 **전에** 남긴다. 완주 분기에만 두었더니 중단·리포트 없음 회차에서
    # 통째로 사라졌다 (실측). 무엇을 어떻게 재려 했는지는 실패한 회차에서 더 필요하다 (R4).
    ctx.notes.extend(scope_notes)
    started = time.perf_counter()
    proc = None
    timed_out = False
    try:
        proc = gate._run(cmd, cwd=ctx.repo_root, timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out = True

    summary = _pit_summary(ctx, paths, targets)
    elapsed = time.perf_counter() - started
    if timed_out:
        return _pit_partial(ctx, summary, targets, elapsed, budget), summary
    if summary is None:
        return _pit_no_report(proc, elapsed), None
    return score_mod._mutation_outcome(ctx, summary, elapsed,
                                       [rel for rel, _name in targets]), summary


def _pit_summary(ctx: gate.GateContext, paths: dict, targets):
    """리포트에서 요약을 만든다. 리포트가 한 벌도 없으면 None.

    리포트는 있는데 기록이 0건인 것과, 리포트 자체가 없는 것은 다른 일이다 —
    앞은 "변이가 만들어지지 않았다"(정상), 뒤는 준비 단계 실패다.
    """
    texts = _pit_report_texts(paths["report"])
    if not texts:
        return None
    return parse_pit_reports(texts, _java_class_index(targets),
                             _pit_sources(ctx.repo_root, targets))


def _check_mutation_java(ctx: gate.GateContext, java_files) -> dict:
    """자바 경로 하나를 끝까지. 반환은 언어 한 조각(part)이다."""
    outcome, summary = _run_mutation_java(ctx, java_files)
    return {"language": "java", "label": "자바", "outcome": outcome, "summary": summary}


def _run_mutation_java(ctx: gate.GateContext, java_files) -> tuple:
    blocked = _java_preconditions(ctx)
    if blocked is not None:
        return blocked, None
    targets, blocked = _java_scope(ctx, java_files)
    if blocked is not None:
        return blocked, None

    paths, cmd, scope_notes = _pit_setup(ctx, targets)
    return _pit_run(ctx, paths, cmd, targets, scope_notes)


def _mutation_changed_java(ctx: gate.GateContext) -> list:
    """C7 이 볼 자바 변경 파일. 변경분의 단일 출처는 그대로 ctx.change.files 다."""
    return [rel for rel in ctx.change.files if Path(rel).suffix.lower() in MUTATION_JAVA_SUFFIXES]


# ---------------------------------------------------------------------------
# 선언부 — 이 어댑터가 규격에 신고하는 사실 (계약 테스트가 동작과의 일치를 검사한다)
# ---------------------------------------------------------------------------

JAVA_ADAPTER = score_mod.AdapterSpec(
    language="java",
    label="자바",
    tool="gradle",                         # 실행 파일은 Gradle 이다 — PIT 는 init script 로 붙는다
    config_key="mutation.java",
    # 변환표 = PIT_STATUS_TO_GATE. 실물로 관측한 넷만 담았다 (비항등이라 적용을 지우면
    # 계약 테스트가 잡는다). 표에 없는 상태는 원어 그대로 통과해 unknown 경로로 간다 (R4).
    status_map=PIT_STATUS_TO_GATE,
    measure_unit="expression",             # 한 줄에서 여러 변이가 나온다 (실측)
    skip_report=None,                      # 통째로 건너뛰는 단위를 관측하지 못했다
    incremental=True,                      # historyInput/OutputLocation (실측)
    # 이 자리는 "무엇이 바뀌면 지난 상태를 버리는가" 이고, 실제보다 넓게 적으면 낡은
    # 결과가 굳는 것을 못 본다 — 좁게 적는 쪽이 보수적이다.
    # 실측(통제 실험, 같은 history 자리에 매 회차 --rerun-tasks): 콜드는 `Ran 3 tests`,
    # 아무것도 안 고친 회차는 `Ran 0`, 대상 클래스 바이트코드를 고친 회차는 다시 `Ran 3`.
    # 의존 라이브러리(로컬 jar) 하나를 더한 회차는 **무변경 회차와 같았다**(`Ran 0`) —
    # 클래스패스는 무효화 축이 아니다. 넷 다 변이 5개로 같았다.
    # 테스트 본문을 고치면 관련 변이를 다시 돈다 (실측: 확인문을 전부 지운 뒤 증분과 콜드가
    # 같은 점수를 냈다 — mutmut 은 여기서 100% 를 냈다).
    # 남는 위험: 의존성만 올린 회차는 지난 점수를 그대로 쓴다. 상태 파일 이름에 의존성
    # 지문을 넣어야 막히는데 그건 이 단계 범위 밖이다.
    incremental_triggers=("대상 클래스 바이트코드", "테스트 클래스 변경", "pitest 판"),
    target_syntax=("클래스 이름 목록 (`패키지.클래스`), 와일드카드는 `*` 뿐. 자바 클래스 "
                   "이름에는 글롭 문자가 못 들어가 이스케이프가 필요 없다. **대상 목록"
                   "(targetClasses)과 테스트 목록(targetTests)은 서로 다른 자리다** — "
                   "테스트 목록을 대상과 같이 좁히면 같은 코드가 통째로 덮은 테스트 없음이 된다"),
    field_confidence={"line": "tool", "column": "absent", "mutator": "tool",
                      "tests": "per-mutant"},
    requires=(),                           # 게이트에 자바 테스트 항목이 없다 — PIT 자신의 기준 검사에 맡긴다
    workspace=("게이트 임시 디렉토리의 init script·리포트(매 실행 삭제) + 캐시에 증분 "
               "상태 파일(java_history_dir). 대상 프로젝트에는 Gradle 이 원래 만드는 "
               ".gradle / build 만 남는다. 만료·정리 정책: 없음"),
    copy_limitations=(),                   # 사본을 만들지 않는다 — 변이는 메모리 안 바이트코드다
)
