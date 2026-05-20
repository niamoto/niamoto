from tests.conftest import _cleanup_magicmock_paths, _cleanup_magicmock_root_entries


def test_cleanup_magicmock_paths_removes_new_artifacts(tmp_path):
    magicmock_file = tmp_path / "leftover-MagicMock-file.txt"
    magicmock_dir = tmp_path / "MagicMock"
    magicmock_file.write_text("artifact", encoding="utf-8")
    magicmock_dir.mkdir()

    _cleanup_magicmock_paths(tmp_path)

    assert not magicmock_file.exists()
    assert not magicmock_dir.exists()


def test_cleanup_magicmock_root_entries_removes_direct_project_artifacts(tmp_path):
    magicmock_file = tmp_path / "leftover-MagicMock-file.txt"
    nested_file = tmp_path / "nested" / "leftover-MagicMock-file.txt"
    magicmock_file.write_text("artifact", encoding="utf-8")
    nested_file.parent.mkdir()
    nested_file.write_text("artifact", encoding="utf-8")

    _cleanup_magicmock_root_entries(tmp_path)

    assert not magicmock_file.exists()
    assert nested_file.exists()
