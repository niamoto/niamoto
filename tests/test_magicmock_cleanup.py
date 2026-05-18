from tests.conftest import _cleanup_magicmock_paths


def test_cleanup_magicmock_paths_removes_new_artifacts(tmp_path):
    magicmock_file = tmp_path / "leftover-MagicMock-file.txt"
    magicmock_dir = tmp_path / "MagicMock"
    magicmock_file.write_text("artifact", encoding="utf-8")
    magicmock_dir.mkdir()

    _cleanup_magicmock_paths(tmp_path)

    assert not magicmock_file.exists()
    assert not magicmock_dir.exists()
