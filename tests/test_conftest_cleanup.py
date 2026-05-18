from pathlib import Path

import tests.conftest as conftest


def test_session_cleanup_preserves_unowned_root_database(tmp_path, monkeypatch):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    monkeypatch.setattr(conftest, "__file__", str(tests_dir / "conftest.py"))

    project_database = tmp_path / "important.duckdb"
    test_database = tmp_path / "test.duckdb"
    project_database.touch()
    test_database.touch()

    conftest.pytest_sessionfinish(session=None, exitstatus=0)

    assert project_database.exists()
    assert not test_database.exists()


def test_test_database_artifact_prefixes_cover_auxiliary_files():
    assert conftest.is_test_database_artifact(Path("test.duckdb-wal"))
    assert not conftest.is_test_database_artifact(Path("important.duckdb-wal"))
