import subprocess

from ml.scripts.research import ablation_run
from ml.scripts.research import run_fusion_surrogate_autoresearch as runner
from ml.scripts.research.run_fusion_surrogate_autoresearch import (
    DEFAULT_ALLOWED_PATHS,
    build_codex_prompt,
    evaluate_metric,
    restore_paths,
    summarize_recent_iterations,
)


def test_build_codex_prompt_includes_baselines_and_allowed_paths(tmp_path):
    cache_dir = tmp_path / "cache"
    prompt = build_codex_prompt(
        iteration=7,
        baseline_fast=55.6326,
        baseline_mid=59.2746,
        baseline_stack=69.8965,
        allowed_paths=DEFAULT_ALLOWED_PATHS,
        cache_dir=cache_dir,
        recent_history="- iter 5: reject_fast, fast=55.5850",
    )

    assert "itération 7" in prompt
    assert "55.6326" in prompt
    assert "59.2746" in prompt
    assert "69.8965" in prompt
    assert str(cache_dir) in prompt
    for path in DEFAULT_ALLOWED_PATHS:
        assert path in prompt
    assert "n'exécute aucune évaluation toi-même" in prompt
    assert "Historique recent" in prompt
    assert "55.5850" in prompt
    assert "regularisation globale" in prompt


def test_default_allowed_paths_exclude_metric_evaluator():
    assert "ml/scripts/eval/evaluate.py" not in DEFAULT_ALLOWED_PATHS


def test_build_codex_prompt_allows_deferred_stack_baseline(tmp_path):
    cache_dir = tmp_path / "cache"
    prompt = build_codex_prompt(
        iteration=3,
        baseline_fast=55.6326,
        baseline_mid=59.2746,
        baseline_stack=None,
        allowed_paths=DEFAULT_ALLOWED_PATHS,
        cache_dir=cache_dir,
        recent_history="Aucun historique récent.",
    )

    assert "itération 3" in prompt
    assert "55.6326" in prompt
    assert "59.2746" in prompt
    assert "deferred until a candidate passes surrogate-mid" in prompt
    assert "Aucun historique récent." in prompt


def test_summarize_recent_iterations_reports_recent_rejects(tmp_path):
    log_path = tmp_path / "run.jsonl"
    log_path.write_text(
        "\n".join(
            [
                '{"event":"baseline","baseline_fast":55.6326}',
                '{"event":"iteration","iteration":1,"status":"reject_fast","fast_score":55.5192}',
                '{"event":"iteration","iteration":2,"status":"no_candidate","note":"No file changes produced by Codex"}',
                '{"event":"iteration","iteration":3,"status":"reject_fast","fast_score":55.5850}',
            ]
        )
        + "\n"
    )

    summary = summarize_recent_iterations(log_path, limit=3)

    assert "iter 1: reject_fast, fast=55.5192" in summary
    assert "iter 2: no_candidate, note=No file changes produced by Codex" in summary
    assert "55.5192" in summary
    assert "55.5850" in summary


def test_evaluate_metric_uses_current_python_executable(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **_kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="12.5\n", stderr="")

    monkeypatch.setattr(runner, "_run", fake_run)
    monkeypatch.setattr(runner.sys, "executable", "/custom/python")

    score = evaluate_metric("fast", model="fusion", splits=2, cache_dir=tmp_path)

    assert score == 12.5
    assert calls[0][0] == "/custom/python"
    assert str(runner.ROOT / ".venv" / "bin" / "python") not in calls[0]


def test_run_codex_iteration_uses_codex_exec(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner.run_codex_iteration("try one candidate")

    assert result.returncode == 0
    args, kwargs = calls[0]
    assert args[:2] == ["/usr/local/bin/codex", "exec"]
    assert "--cd" in args
    assert str(runner.ROOT) in args
    assert "--sandbox" in args
    assert "workspace-write" in args
    assert "try one candidate" == args[-1]
    assert kwargs == {"check": False}


def test_run_codex_iteration_reports_missing_codex(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)

    result = runner.run_codex_iteration("try one candidate")

    assert result.returncode == 127
    assert result.args == ["codex", "exec"]
    assert "Codex CLI not found" in result.stderr


def test_ablation_run_uses_uv_python_commands(monkeypatch):
    calls = []

    def fake_run(command, env):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="F1 1.0\n", stderr="")

    monkeypatch.setattr(ablation_run.sys, "argv", ["ablation_run.py", "baseline"])
    monkeypatch.setattr(ablation_run, "_run", fake_run)

    assert ablation_run.main() == 0
    assert len(calls) == 4
    assert all(command[:3] == ["uv", "run", "python"] for command in calls)
    assert all(".venv" not in " ".join(command) for command in calls)


def test_restore_paths_removes_untracked_files_and_directories(
    tmp_path,
    monkeypatch,
):
    untracked_file = tmp_path / "candidate.txt"
    untracked_dir = tmp_path / "candidate_dir"
    untracked_file.write_text("temporary candidate", encoding="utf-8")
    untracked_dir.mkdir()
    (untracked_dir / "nested.txt").write_text("nested", encoding="utf-8")

    def fake_run(args, **_kwargs):
        assert args == ["git", "status", "--short"]
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="?? candidate.txt\n?? candidate_dir/\n",
            stderr="",
        )

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_run", fake_run)

    restore_paths(["candidate.txt", "candidate_dir/"])

    assert not untracked_file.exists()
    assert not untracked_dir.exists()
