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

    # No need to clean up after as pytest_sessionfinish will handle it


def is_magicmock_file(name):
    """Check if a file or directory name matches MagicMock patterns."""
    patterns = [
        r"^<MagicMock.*>$",
        r"^MagicMock$",
        r".*MagicMock.*",
    ]

    return any(re.match(pattern, name) for pattern in patterns)


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
            if db_file.parent == root_dir:
                try:
                    print(f"Cleaning up test database artifact: {db_file}")
                    db_file.unlink()
                except Exception as e:
                    print(f"Error cleaning up {db_file}: {e}")

    # Find and remove MagicMock files
    for item in root_dir.glob("**/*"):
        if is_magicmock_file(item.name):
            try:
                if item.is_file():
                    print(f"Cleaning up MagicMock file: {item}")
                    item.unlink()
                    _known_magicmock_paths.add(str(item))
                elif item.is_dir():
                    print(f"Cleaning up MagicMock directory: {item}")
                    shutil.rmtree(item)
                    _known_magicmock_paths.add(str(item))
            except Exception as e:
                print(f"Error cleaning up {item}: {e}")
