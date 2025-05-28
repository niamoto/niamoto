"""Base test class for Niamoto tests.

This module provides a base test class with common setup and teardown methods
for Niamoto tests.
"""

import os
import unittest
from unittest import mock


class NiamotoTestCase(unittest.TestCase):
    """Base test case for Niamoto tests.

    This class provides common setup and teardown methods for Niamoto tests.
    It ensures that all mocks are properly cleaned up after each test.
    """

    # Track active patches to avoid calling stopall() unnecessarily
    _active_patches = []

    def setUp(self):
        """Set up test environment."""
        # Set test mode to prevent config file creation
        os.environ["NIAMOTO_TEST_MODE"] = "1"
        super().setUp()

    def tearDown(self):
        """Clean up test fixtures and stop all patches.

        This method is called after each test method to clean up any resources
        created during the test. It ensures that all mocks are properly stopped
        to prevent memory leaks and test interference.
        """
        # Only stop patches that were created by this test instance
        for patch in self._active_patches:
            try:
                if patch:
                    patch.stop()
            except Exception:
                pass

        self._active_patches = []

        # Clean up test environment variable
        os.environ.pop("NIAMOTO_TEST_MODE", None)

        super().tearDown()

    def create_mock(self, spec_class):
        """Create a mock with proper spec_set to avoid file creation.

        This helper method creates a mock with spec_set to prevent
        the creation of attributes that don't exist in the original class,
        which can lead to MagicMock files being created on disk.

        Args:
            spec_class: The class to use as a specification

        Returns:
            A properly configured mock object
        """
        return mock.create_autospec(spec_class, spec_set=True, instance=True)

    def patch(self, *args, **kwargs):
        """Create a patch and register it for automatic cleanup.

        This method wraps unittest.mock.patch and registers the patch
        for automatic cleanup in tearDown.

        Returns:
            The patch object
        """
        patcher = mock.patch(*args, **kwargs)
        self._active_patches.append(patcher)
        return patcher
