#!/usr/bin/env python3
"""스킬 검증 환경 진입점.

1차 범위는 Claude 를 띄우지 않는 층위만 돈다.
  - 결합 룰 (CLAUDE.md + fixture README 를 실행 시점에 파싱)
  - 기존 pytest (scripts/tests + evals/tests)
  - 정적 산출물 케이스

사용법:
  python3 evals/run.py                이번 상태를 보고만 한다
  python3 evals/run.py --accept       지금 결과를 기준선으로 굳힌다 (분류 필수)
  python3 evals/run.py --quiet        요약만 출력
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.runner import assertions, baseline, cases, coupling, lint, report  # noqa: E402

BASELINE_PATH = REPO_ROOT / "evals" / "baseline.json"
LABELS_PATH = REPO_ROOT / "evals" / "labels.json"

# 러너가 자기 자신을 다시 부르는 것을 막는 표시.
NESTED_FLAG = "JS_SUPER_EVAL_NESTED"


def collect_coupling(base: dict, rules: list) -> list[baseline.Classified]:
    """결합 룰을 전부 돌린다. 격리 없이 저장소를 읽기만 한다."""
    rows: list[baseline.Classified] = []

    for rule in rules:
        case_id = rule.key

        outcome = assertions.run_shell_rule(rule.command, REPO_ROOT)
        if outcome.status == "BLOCKED":
            rows.append(baseline.classify(case_id, "BLOCKED", base, f"[{rule.source}] {outcome.reason}"))
            continue
        if rule.expected is None:
            rows.append(baseline.classify(case_id, "PENDING", base, f"[{rule.source}] 기대값 주석 없음"))
            continue
        if not rule.expected_is_numeric:
            rows.append(
                baseline.classify(case_id, "PENDING", base, f"[{rule.source}] 자연어 기대값: {rule.expected}")
            )
            continue

        op, _mode = coupling.infer_check(rule)
        if op == "pending":
            rows.append(
                baseline.classify(
                    case_id, "PENDING", base,
                    f"[{rule.source}] 파일별 기대값이라 기계 판정 불가: {rule.expected}",
                )
            )
            continue
        verdict = assertions.compare(op, outcome.actual, rule.expected_int)
        detail = "" if verdict.status == "PASS" else (
            f"[{rule.source}] {verdict.reason} (실제 {verdict.actual!r})"
        )
        rows.append(baseline.classify(case_id, verdict.status, base, detail))

    return rows


def collect_pytest(base: dict) -> list[baseline.Classified]:
    """기존 pytest 를 항상 전수로 돌린다.

    러너가 pytest 를 돌리고 그 pytest 안의 테스트가 다시 러너를 부르면
    끝없이 반복된다. 환경 변수로 깊이를 표시해 한 번만 돌게 막는다.
    """
    if os.environ.get(NESTED_FLAG):
        return [
            baseline.classify(
                "pytest/scripts+evals", "NOT-SELECTED", base,
                "러너 안에서 다시 불려 건너뜀 (재귀 방지)",
            )
        ]

    env = dict(os.environ, **{NESTED_FLAG: "1"})
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "scripts/tests", "evals/tests", "-q"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=env,
    )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return [baseline.classify("pytest/scripts+evals", status, base, tail)]


def collect_cases(base: dict, loaded: list) -> list[baseline.Classified]:
    """정적 케이스를 돌린다. run 이 있는 케이스는 1차 범위 밖이다."""
    rows: list[baseline.Classified] = []

    for case in loaded:
        if case.status != "active":
            rows.append(baseline.classify(case.id, "BLOCKED", base, f"status={case.status}"))
            continue
        if case.needs_claude:
            rows.append(
                baseline.classify(case.id, "NOT-SELECTED", base, "1차 범위 밖 (실행 층위)")
            )
            continue

        failures: list[str] = []
        for item in case.expect:
            if item.get("kind") != "shell":
                failures.append(f"1차가 모르는 단언 종류: {item.get('kind')}")
                continue
            argv = item["argv"]
            _, out = assertions.run_argv(argv, REPO_ROOT)
            verdict = assertions.compare(item["op"], out, item.get("value"))
            if verdict.status != "PASS":
                shown = " ".join(argv)[:60]
                failures.append(f"{shown} → {verdict.reason} (실제 {verdict.actual!r})")

        status = "PASS" if not failures else "FAIL"
        rows.append(baseline.classify(case.id, status, base, "; ".join(failures)))

    return rows


def accept(rows: list[baseline.Classified]) -> int:
    """지금 결과를 기준선으로 굳힌다. 미분류가 있으면 거부한다.

    통과한 항목은 그대로 굳힌다. 통과하지 않은 항목은 `evals/labels.json` 에
    사람이 판단(회귀인지 낡음인지)을 적어둬야 한다. 관측만 굳히면
    지금 실패 중인 진짜 회귀가 정답으로 박제된다 (요구사항 결정 8).
    """
    labels = baseline.load_labels(LABELS_PATH)
    pending = baseline.unclassified(rows, labels)
    if pending:
        print(f"미분류 {len(pending)}건이 있어 기준선을 굳히지 않습니다.")
        print(f"각 항목을 {LABELS_PATH.name} 에 회귀 또는 낡음으로 적어주세요.")
        for row in pending[:15]:
            print(f"  {row.case_id} — {(row.detail or row.status)[:80]}")
        if len(pending) > 15:
            print(f"  … 외 {len(pending) - 15}건")
        return 3

    data = baseline.load_baseline(BASELINE_PATH)
    data.setdefault("cases", {})
    for row in rows:
        entry = labels.get(row.case_id, {})
        data["cases"][row.case_id] = {
            "verdict": row.verdict,
            "label": entry.get("label") or row.label or "confirmed",
            "reason": entry.get("reason") or row.detail,
        }
    baseline.save_baseline(BASELINE_PATH, data)
    print(f"기준선을 갱신했습니다 — {len(rows)}건.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="스킬 검증 환경")
    parser.add_argument("--accept", action="store_true", help="지금 결과를 기준선으로 굳힌다")
    parser.add_argument("--quiet", action="store_true", help="요약만 출력")
    args = parser.parse_args(argv)

    started = time.time()
    base = baseline.load_baseline(BASELINE_PATH)
    loaded, case_errors = cases.load_all(REPO_ROOT / "evals" / "cases")
    rules = coupling.collect_rules(REPO_ROOT)
    lint_report = lint.run_lint(REPO_ROOT, rules, loaded, case_errors)

    if lint_report.must_refuse:
        print(report.render([], lint_report, time.time() - started))
        print("검사 단계에서 막혔습니다. 위 항목을 먼저 정리해주세요.")
        return 2

    rows = collect_cases(base, loaded) + collect_coupling(base, rules) + collect_pytest(base)

    if args.quiet:
        counts = baseline.summarize(rows)
        print(f"{len(rows)}건 — " + " / ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    else:
        print(report.render(rows, lint_report, time.time() - started))

    if args.accept:
        return accept(rows)

    return 1 if baseline.has_blocking_failure(rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
