from scripts.ml.run_fusion_surrogate_autoresearch import (
    DEFAULT_ALLOWED_PATHS,
    build_codex_prompt,
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
    )

    assert "itération 7" in prompt
    assert "55.6326" in prompt
    assert "59.2746" in prompt
    assert "69.8965" in prompt
    assert str(cache_dir) in prompt
    for path in DEFAULT_ALLOWED_PATHS:
        assert path in prompt
    assert "n'exécute aucune évaluation toi-même" in prompt


def test_build_codex_prompt_allows_deferred_stack_baseline(tmp_path):
    cache_dir = tmp_path / "cache"
    prompt = build_codex_prompt(
        iteration=3,
        baseline_fast=55.6326,
        baseline_mid=59.2746,
        baseline_stack=None,
        allowed_paths=DEFAULT_ALLOWED_PATHS,
        cache_dir=cache_dir,
    )

    assert "itération 3" in prompt
    assert "55.6326" in prompt
    assert "59.2746" in prompt
    assert "deferred until a candidate passes surrogate-mid" in prompt
