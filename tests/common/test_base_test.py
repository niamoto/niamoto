import os

from tests.common.base_test import NiamotoTestCase


class _MinimalNiamotoTestCase(NiamotoTestCase):
    __test__ = False

    def runTest(self):
        pass


def test_active_patches_are_isolated_per_test_instance():
    first = _MinimalNiamotoTestCase()
    first.setUp()
    try:
        first.patch("tests.common.base_test.os.environ", {})
        assert len(first._active_patches) == 1
    finally:
        first.tearDown()

    second = _MinimalNiamotoTestCase()
    second.setUp()
    try:
        assert second._active_patches == []
        assert second._active_patches is not NiamotoTestCase._active_patches
    finally:
        second.tearDown()


def test_niamoto_test_mode_is_restored_after_test_case(monkeypatch):
    monkeypatch.setenv("NIAMOTO_TEST_MODE", "external")

    case = _MinimalNiamotoTestCase()
    case.setUp()
    try:
        assert os.environ["NIAMOTO_TEST_MODE"] == "1"
    finally:
        case.tearDown()

    assert os.environ["NIAMOTO_TEST_MODE"] == "external"
