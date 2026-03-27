"""Trim non-runtime scikit-learn package data from PyInstaller builds."""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files(
    "sklearn",
    excludes=[
        "**/tests",
        "**/tests/**/*",
        "**/*.pyx",
        "**/*.pxd",
        "**/*.tp",
        "**/meson.build",
    ],
)
