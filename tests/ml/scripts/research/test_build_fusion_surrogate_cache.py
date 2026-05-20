from pathlib import Path

import pytest

from ml.scripts.research import build_fusion_surrogate_cache as cache_builder


def test_build_cache_preserves_existing_cache_when_payload_build_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_dir = tmp_path / "cache"
    output_dir.mkdir()
    old_fold = output_dir / "fold_01.npz"
    old_manifest = output_dir / "manifest.json"
    old_fold.write_bytes(b"existing fold")
    old_manifest.write_text('{"existing": true}\n', encoding="utf-8")

    records = [
        {
            "source_dataset": "dataset_a",
            "concept_coarse": "taxonomy",
            "is_anonymous": False,
        },
        {
            "source_dataset": "dataset_b",
            "concept_coarse": "location",
            "is_anonymous": False,
        },
    ]

    monkeypatch.setattr(cache_builder, "_load_records", lambda _path: records)
    monkeypatch.setattr(cache_builder, "_is_real_record", lambda _record: True)
    monkeypatch.setattr(
        cache_builder,
        "_train_branch_models",
        lambda _train_records: (None, None),
    )

    def fail_build_payload(*_args, **_kwargs):
        raise RuntimeError("payload failed")

    monkeypatch.setattr(cache_builder, "_build_payload", fail_build_payload)

    with pytest.raises(RuntimeError, match="payload failed"):
        cache_builder.build_cache(tmp_path / "gold.json", output_dir, n_splits=2)

    assert old_fold.read_bytes() == b"existing fold"
    assert old_manifest.read_text(encoding="utf-8") == '{"existing": true}\n'
    assert list(tmp_path.glob(".cache.*.tmp")) == []


def test_replace_cache_dir_restores_existing_cache_when_backup_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_dir = tmp_path / "cache"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text("old\n", encoding="utf-8")

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    (staging_dir / "manifest.json").write_text("new\n", encoding="utf-8")

    real_rmtree = cache_builder.shutil.rmtree
    failed_backup_cleanup = False

    def fail_backup_cleanup(path, *args, **kwargs):
        nonlocal failed_backup_cleanup
        target = Path(path)
        if ".cache.backup." in target.name and not failed_backup_cleanup:
            failed_backup_cleanup = True
            raise OSError("simulated backup cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(cache_builder.shutil, "rmtree", fail_backup_cleanup)

    with pytest.raises(OSError, match="simulated backup cleanup failure"):
        cache_builder._replace_cache_dir(staging_dir, output_dir)

    assert (output_dir / "manifest.json").read_text(encoding="utf-8") == "old\n"
    assert not any(
        path.read_text(encoding="utf-8") == "new\n"
        for path in tmp_path.glob("*/manifest.json")
    )
