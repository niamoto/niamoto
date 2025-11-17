from pathlib import Path

# PROJECT_ROOT points to the niamoto package directory
# Works in both source and frozen (PyInstaller) modes because
# __file__ is always relative to the package structure
PROJECT_ROOT = Path(__file__).resolve().parents[1]
