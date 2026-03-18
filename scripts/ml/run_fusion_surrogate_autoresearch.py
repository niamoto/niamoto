#!/usr/bin/env python
"""Autonomous fusion-only autoresearch runner.

Runs bounded Codex iterations against the surrogate fusion loop and keeps
only candidates that pass the configured metric gates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parent.parent.parent
DEFAULT_CACHE_DIR = (
    ROOT / "data" / "cache" / "ml" / "fusion_surrogate" / "gold_set_splits3"
)
DEFAULT_LOG_DIR = ROOT / ".autoresearch"
DEFAULT_ALLOWED_UNTRACKED = {"ml-detection-dashboard.html"}
DEFAULT_ALLOWED_PATHS = (
    "scripts/ml/train_fusion.py",
    "src/niamoto/core/imports/ml/classifier.py",
    "scripts/ml/evaluate.py",
)


@dataclass
class IterationResult:
    iteration: int
    status: str
    changed_files: list[str]
    fast_score: float | None = None
    mid_score: float | None = None
    stack_score: float | None = None
    baseline_fast: float | None = None
    baseline_mid: float | None = None
    baseline_stack: float | None = None
    commit_sha: str | None = None
    codex_exit_code: int | None = None
    note: str | None = None


def _run(
    args: list[str],
    *,
    input_text: str | None = None,
    cwd: Path = ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        cwd=cwd,
        capture_output=True,
        check=check,
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_status_lines() -> list[str]:
    result = _run(["git", "status", "--short"], check=False)
    return [line for line in result.stdout.splitlines() if line.strip()]


def ensure_clean_worktree(allowed_untracked: set[str]) -> None:
    """Require a clean worktree before starting autoresearch."""
    bad_lines = []
    for line in _git_status_lines():
        path = line[3:]
        if line.startswith("?? ") and path in allowed_untracked:
            continue
        bad_lines.append(line)
    if bad_lines:
        formatted = "\n".join(bad_lines)
        raise RuntimeError(
            "Autoresearch runner requires a clean worktree.\n"
            f"Unexpected git status entries:\n{formatted}"
        )


def current_changed_files(allowed_untracked: set[str]) -> list[str]:
    paths = []
    for line in _git_status_lines():
        path = line[3:]
        if line.startswith("?? ") and path in allowed_untracked:
            continue
        paths.append(path)
    return sorted(paths)


def restore_paths(paths: list[str]) -> None:
    if not paths:
        return
    _run(["git", "restore", "--staged", "--worktree", "--source=HEAD", "--", *paths])


def evaluate_metric(
    metric: str,
    *,
    model: str = "fusion",
    splits: int = 3,
    cache_dir: Path | None = None,
) -> float:
    cmd = [
        str(ROOT / ".venv" / "bin" / "python"),
        "-m",
        "scripts.ml.evaluate",
        "--model",
        model,
        "--metric",
        metric,
        "--splits",
        str(splits),
        "--quiet",
    ]
    if cache_dir is not None:
        cmd.extend(["--cache-dir", str(cache_dir)])
    result = _run(cmd)
    return float(result.stdout.strip())


def current_head() -> str:
    return _run(["git", "rev-parse", "HEAD"]).stdout.strip()


def commit_winner(
    changed_files: list[str],
    *,
    iteration: int,
    fast_score: float,
    baseline_fast: float,
) -> str:
    _run(["git", "add", "--", *changed_files])
    delta = fast_score - baseline_fast
    message = (
        "feat(ml): keep fusion surrogate winner "
        f"(iter {iteration}, fast {baseline_fast:.4f} -> {fast_score:.4f}, "
        f"delta {delta:+.4f})"
    )
    _run(["git", "commit", "-m", message])
    return current_head()


def build_codex_prompt(
    *,
    iteration: int,
    baseline_fast: float,
    baseline_mid: float,
    baseline_stack: float,
    allowed_paths: tuple[str, ...],
    cache_dir: Path,
) -> str:
    allowed = "\n".join(f"- {path}" for path in allowed_paths)
    return f"""Tu travailles dans {ROOT}.

Objectif: itération {iteration} d'autoresearch fusion-only pour la détection ML Niamoto.

Contexte:
- Cache surrogate prêt: {cache_dir}
- Baseline surrogate-fast: {baseline_fast:.4f}
- Baseline surrogate-mid: {baseline_mid:.4f}
- Baseline product-score-fast-fast: {baseline_stack:.4f}

Périmètre autorisé:
{allowed}

Contraintes:
- propose exactement un seul candidat minimal et plausible
- ne touche à aucun autre fichier
- n'exécute aucune évaluation toi-même
- n'effectue aucun commit
- si tu n'as pas de candidat simple et crédible, ne modifie rien
- stoppe-toi juste après avoir appliqué le candidat éventuel

Axes recommandés:
- marges header/value
- désaccord asymétrique
- coded headers
- interactions de confiance locales
"""


def run_codex_iteration(prompt: str) -> subprocess.CompletedProcess[str]:
    return _run(
        ["codex", "exec", "--json", "--full-auto", prompt],
        check=False,
    )


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def run_iteration(
    *,
    iteration: int,
    baseline_fast: float,
    baseline_mid: float,
    baseline_stack: float,
    cache_dir: Path,
    commit_winners: bool,
    allowed_paths: tuple[str, ...],
    allowed_untracked: set[str],
    log_path: Path,
) -> tuple[IterationResult, float, float, float]:
    prompt = build_codex_prompt(
        iteration=iteration,
        baseline_fast=baseline_fast,
        baseline_mid=baseline_mid,
        baseline_stack=baseline_stack,
        allowed_paths=allowed_paths,
        cache_dir=cache_dir,
    )
    codex_result = run_codex_iteration(prompt)
    changed_files = current_changed_files(allowed_untracked)
    result = IterationResult(
        iteration=iteration,
        status="no_candidate",
        changed_files=changed_files,
        baseline_fast=baseline_fast,
        baseline_mid=baseline_mid,
        baseline_stack=baseline_stack,
        codex_exit_code=codex_result.returncode,
    )

    if codex_result.returncode != 0 and not changed_files:
        result.status = "codex_error"
        result.note = codex_result.stderr[-1000:]
        return result, baseline_fast, baseline_mid, baseline_stack

    if not changed_files:
        result.note = "No file changes produced by Codex"
        return result, baseline_fast, baseline_mid, baseline_stack

    fast_score = evaluate_metric(
        "surrogate-fast",
        model="fusion",
        splits=3,
        cache_dir=cache_dir,
    )
    result.fast_score = fast_score
    if fast_score <= baseline_fast:
        restore_paths(changed_files)
        result.status = "reject_fast"
        return result, baseline_fast, baseline_mid, baseline_stack

    mid_score = evaluate_metric(
        "surrogate-mid",
        model="fusion",
        splits=3,
        cache_dir=cache_dir,
    )
    result.mid_score = mid_score
    if mid_score <= baseline_mid:
        restore_paths(changed_files)
        result.status = "reject_mid"
        return result, baseline_fast, baseline_mid, baseline_stack

    stack_score = evaluate_metric(
        "product-score-fast-fast",
        model="all",
        splits=2,
    )
    result.stack_score = stack_score
    if stack_score < baseline_stack:
        restore_paths(changed_files)
        result.status = "reject_stack"
        return result, baseline_fast, baseline_mid, baseline_stack

    result.status = "keep"
    if commit_winners:
        commit_sha = commit_winner(
            changed_files,
            iteration=iteration,
            fast_score=fast_score,
            baseline_fast=baseline_fast,
        )
        result.commit_sha = commit_sha
    else:
        result.note = "Winner kept in worktree without commit; runner should stop here."

    baseline_fast = fast_score
    baseline_mid = mid_score
    baseline_stack = stack_score
    return result, baseline_fast, baseline_mid, baseline_stack


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run fusion-only surrogate autoresearch"
    )
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument(
        "--commit-winners",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Commit winners automatically to keep the worktree clean between iterations",
    )
    args = parser.parse_args()

    ensure_clean_worktree(DEFAULT_ALLOWED_UNTRACKED)

    baseline_fast = evaluate_metric(
        "surrogate-fast",
        model="fusion",
        splits=3,
        cache_dir=args.cache_dir,
    )
    baseline_mid = evaluate_metric(
        "surrogate-mid",
        model="fusion",
        splits=3,
        cache_dir=args.cache_dir,
    )
    baseline_stack = evaluate_metric(
        "product-score-fast-fast",
        model="all",
        splits=2,
    )

    run_id = _timestamp()
    log_path = args.log_dir / f"fusion-surrogate-{run_id}.jsonl"
    append_jsonl(
        log_path,
        {
            "event": "baseline",
            "timestamp": run_id,
            "baseline_fast": baseline_fast,
            "baseline_mid": baseline_mid,
            "baseline_stack": baseline_stack,
            "cache_dir": str(args.cache_dir),
            "head": current_head(),
        },
    )

    for iteration in range(1, args.iterations + 1):
        result, baseline_fast, baseline_mid, baseline_stack = run_iteration(
            iteration=iteration,
            baseline_fast=baseline_fast,
            baseline_mid=baseline_mid,
            baseline_stack=baseline_stack,
            cache_dir=args.cache_dir,
            commit_winners=args.commit_winners,
            allowed_paths=DEFAULT_ALLOWED_PATHS,
            allowed_untracked=DEFAULT_ALLOWED_UNTRACKED,
            log_path=log_path,
        )
        append_jsonl(
            log_path,
            {
                "event": "iteration",
                "timestamp": _timestamp(),
                **result.__dict__,
                "head": current_head(),
            },
        )
        print(
            json.dumps(
                {
                    "iteration": iteration,
                    "status": result.status,
                    "fast_score": result.fast_score,
                    "mid_score": result.mid_score,
                    "stack_score": result.stack_score,
                    "commit_sha": result.commit_sha,
                },
                ensure_ascii=True,
            )
        )
        if result.status == "keep" and not args.commit_winners:
            break


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
