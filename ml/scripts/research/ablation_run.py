"""Run a single value-feature ablation variant and report stack metrics."""

from __future__ import annotations

import os
import re
import subprocess
import sys

ABLATION_FEATURES = {
    "bimodality_coefficient",
    "positive_log_skew",
    "pct_round_values",
    "pct_sequential",
    "range_ratio",
}


def _variant_env(feature: str) -> dict[str, str]:
    env = os.environ.copy()
    if feature == "baseline":
        env["NIAMOTO_VALUE_ABLATION_FEATURES"] = "baseline"
    else:
        env["NIAMOTO_VALUE_ABLATION_FEATURES"] = feature
    return env


def _run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        cmd = " ".join(command)
        raise RuntimeError(
            f"Command failed ({result.returncode}): {cmd}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    return result


def _extract_last_float(text: str) -> str:
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    return matches[-1] if matches else "ERROR"


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: uv run python ml/scripts/research/ablation_run.py "
            "<baseline|feature_name>",
            file=sys.stderr,
        )
        return 2

    feature = sys.argv[1]
    if feature != "baseline" and feature not in ABLATION_FEATURES:
        valid = ", ".join(["baseline", *sorted(ABLATION_FEATURES)])
        print(f"Unknown feature '{feature}'. Valid values: {valid}", file=sys.stderr)
        return 2

    env = _variant_env(feature)

    print(f"\n{'=' * 60}", flush=True)
    print(f"ABLATION: +{feature}", flush=True)
    print(f"{'=' * 60}", flush=True)

    print("\n--- train_value_model ---", flush=True)
    values_run = _run(
        ["uv", "run", "python", "-m", "ml.scripts.train.train_value_model"],
        env,
    )
    values_f1 = _extract_last_float(values_run.stdout)
    print(f"Values F1: {values_f1}", flush=True)

    print("--- train_fusion ---", flush=True)
    _run(["uv", "run", "python", "-m", "ml.scripts.train.train_fusion"], env)
    print("Fusion done", flush=True)

    print("--- product-score ---", flush=True)
    product_run = _run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "ml.scripts.eval.evaluate",
            "--model",
            "all",
            "--metric",
            "product-score",
            "--splits",
            "3",
        ],
        env,
    )
    product_score = _extract_last_float(product_run.stdout)
    print(f"ProductScore: {product_score}", flush=True)

    print("--- niamoto-score ---", flush=True)
    global_run = _run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "ml.scripts.eval.evaluate",
            "--model",
            "all",
            "--metric",
            "niamoto-score",
            "--splits",
            "3",
        ],
        env,
    )
    global_score = _extract_last_float(global_run.stdout)
    print(f"GlobalScore: {global_score}", flush=True)

    print(
        f"\nRESULT | {feature} | {values_f1} | {product_score} | {global_score} |",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
