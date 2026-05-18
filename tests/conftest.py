import os
import shutil
import tempfile
import pytest
import re
from pathlib import Path


@pytest.fixture(scope="function")
def niamoto_home(request):
    temp_dir = tempfile.mkdtemp(prefix="niamoto_test_")
    os.environ["NIAMOTO_HOME"] = temp_dir

    def cleanup():
        os.environ.pop("NIAMOTO_HOME", None)
        shutil.rmtree(temp_dir)

    request.addfinalizer(cleanup)
    return temp_dir


@pytest.fixture(scope="function")
def cli_runner():
    from click.testing import CliRunner

    return CliRunner()


# Cache for known MagicMock paths to avoid excessive glob operations
_known_magicmock_paths = set()
TEST_DATABASE_ARTIFACT_PREFIXES = (
    "test.",
    "test-",
    "test_",
    "temp.",
    "temp-",
    "temp_",
    "tmp.",
    "tmp-",
    "tmp_",
    "mock.",
    "mock-",
    "mock_",
    "niamoto_test_",
    "niamoto-test-",
)
MAGICMOCK_SCAN_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "target",
}

NIAMOTO_SUBSET_INSTANCE = (
    Path(__file__).parent.parent / "test-instance" / "niamoto-subset"
)


@pytest.fixture(autouse=True)
def cleanup_magicmocks():
    """Clean up MagicMock files before and after each test."""
    # Only clean up known paths from previous runs
    for item_path in _known_magicmock_paths.copy():
        item = Path(item_path)
        try:
            if item.exists():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                _known_magicmock_paths.remove(item_path)
        except Exception:
            pass

    # Run the test
    yield

    _cleanup_magicmock_paths(Path(__file__).parent.parent)


def is_magicmock_file(name):
    """Check if a file or directory name matches MagicMock patterns."""
    patterns = [
        r"^<MagicMock.*>$",
        r"^MagicMock$",
        r".*MagicMock.*",
    ]

    return any(re.match(pattern, name) for pattern in patterns)


def _cleanup_magicmock_paths(root_dir: Path, *, verbose: bool = False) -> None:
    """Remove MagicMock artifacts under root_dir."""
    for current_root, dir_names, file_names in os.walk(root_dir):
        dir_names[:] = [
            name for name in dir_names if name not in MAGICMOCK_SCAN_EXCLUDED_DIRS
        ]

        for name in list(dir_names) + file_names:
            if not is_magicmock_file(name):
                continue

            item = Path(current_root) / name
            try:
                if item.is_file():
                    if verbose:
                        print(f"Cleaning up MagicMock file: {item}")
                    item.unlink()
                    _known_magicmock_paths.add(str(item))
                elif item.is_dir():
                    if verbose:
                        print(f"Cleaning up MagicMock directory: {item}")
                    shutil.rmtree(item)
                    _known_magicmock_paths.add(str(item))
                    if name in dir_names:
                        dir_names.remove(name)
            except Exception as e:
                if verbose:
                    print(f"Error cleaning up {item}: {e}")


def is_test_database_artifact(path: Path) -> bool:
    """Check whether a root database file is clearly owned by tests."""
    return path.name.startswith(TEST_DATABASE_ARTIFACT_PREFIXES)


def pytest_sessionfinish(session, exitstatus):
    """Clean up MagicMock files, mock_db_path, and database test artifacts after test session."""
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent

    # Clean up mock_db_path if it exists
    mock_db_path = root_dir / "mock_db_path"
    if mock_db_path.exists():
        try:
            if mock_db_path.is_file():
                print(f"Cleaning up mock_db_path file: {mock_db_path}")
                mock_db_path.unlink()
            else:
                print(f"Cleaning up mock_db_path directory: {mock_db_path}")
                shutil.rmtree(mock_db_path)
        except Exception as e:
            print(f"Error cleaning up mock_db_path: {e}")

    # Clean up any database files created at project root (test artifacts)
    db_patterns = ["*.db", "*.duckdb", "*.sqlite", "*.sqlite3"]
    for pattern in db_patterns:
        for db_file in root_dir.glob(pattern):
            # Only clean up files at the root, not in subdirectories
            if db_file.parent == root_dir and is_test_database_artifact(db_file):
                try:
                    print(f"Cleaning up test database artifact: {db_file}")
                    db_file.unlink()
                except Exception as e:
                    print(f"Error cleaning up {db_file}: {e}")

    # Clean up auxiliary database files (WAL and shared memory files)
    aux_patterns = ["*.db-shm", "*.db-wal", "*.duckdb-shm", "*.duckdb-wal"]
    for pattern in aux_patterns:
        for aux_file in root_dir.glob(pattern):
            # Only clean up files at the root, not in subdirectories
            if aux_file.parent == root_dir and is_test_database_artifact(aux_file):
                try:
                    print(f"Cleaning up test database auxiliary file: {aux_file}")
                    aux_file.unlink()
                except Exception as e:
                    print(f"Error cleaning up {aux_file}: {e}")

    # Find and remove MagicMock files
    _cleanup_magicmock_paths(root_dir, verbose=True)


@pytest.fixture(scope="function")
def niamoto_subset_instance_dir() -> Path:
    """Return the checked-in benchmark instance used for integration-like tests."""
    if not NIAMOTO_SUBSET_INSTANCE.exists():
        pytest.skip("test-instance/niamoto-subset not available")
    return NIAMOTO_SUBSET_INSTANCE


@pytest.fixture(scope="function")
def stage_niamoto_subset(tmp_path: Path, niamoto_subset_instance_dir: Path):
    """Copy a selected subset of the benchmark instance into a temporary project."""

    def _stage(rel_paths: list[str]) -> Path:
        for rel_path in rel_paths:
            source = niamoto_subset_instance_dir / rel_path
            destination = tmp_path / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)
        return tmp_path

    return _stage
