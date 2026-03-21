from ml.scripts.research.run_fusion_surrogate_autoresearch import (
    DEFAULT_ALLOWED_PATHS,
    build_codex_prompt,
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
