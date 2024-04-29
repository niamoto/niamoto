import os
import shutil
import tempfile
import pytest


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
