"""Tests for the pipeline benchmark helper."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.dev import bench_pipeline


def test_main_keeps_reported_logs_by_default(monkeypatch, tmp_path):
    source_instance = tmp_path / "instance"
    source_instance.mkdir()
    json_out = tmp_path / "summary.json"

    monkeypatch.setattr(
        bench_pipeline,
        "parse_args",
        lambda: SimpleNamespace(
            instance=source_instance,
            export_target="web_pages",
            json_out=json_out,
            keep_workdir=False,
            cleanup_logs=False,
        ),
    )

    def fake_run_step(name, command, cwd, logs_dir):
        log_file = logs_dir / f"{name}.log"
        log_file.write_text(f"{name} log\n", encoding="utf-8")
        return bench_pipeline.StepResult(
            ok=True,
            duration_s=0.01,
            returncode=0,
            log_file=str(log_file),
        )

    monkeypatch.setattr(bench_pipeline, "run_step", fake_run_step)

    assert bench_pipeline.main() == 0

    summary = json.loads(json_out.read_text(encoding="utf-8"))
    log_path = Path(summary["transform"]["log_file"])
    assert log_path.exists()
    assert log_path.read_text(encoding="utf-8") == "transform log\n"
    assert Path(summary["export"]["log_file"]).exists()
