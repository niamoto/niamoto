#!/usr/bin/env python3
"""Extract plugin metadata from the Niamoto source tree via AST.

Writes `.marketing/plugins.json` — a sorted list of `{name, type, body,
version}` entries — consumed by the niamoto-site marketing site.

Runs in CI on every push to `main` that touches plugin sources.
"""

from __future__ import annotations

import ast
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = REPO_ROOT / "src" / "niamoto" / "core" / "plugins"
OUTPUT = REPO_ROOT / ".marketing" / "plugins.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _read_package_version() -> str:
    """Extract the project version from pyproject.toml."""
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["version"]


def _decorator_name(decorator: ast.expr) -> str | None:
    """Return the callable name of a decorator, or None."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    return None


def _extract_type_from_register_args(call: ast.Call) -> str | None:
    """If @register has a second positional arg like PluginType.WIDGET, return 'widget'."""
    if len(call.args) < 2:
        return None
    second = call.args[1]
    if isinstance(second, ast.Attribute):
        # e.g., PluginType.WIDGET -> 'widget'
        return second.attr.lower()
    return None


def _extract_type_from_class_body(cls_node: ast.ClassDef) -> str | None:
    """Fallback: look for `type = PluginType.X` inside the class body."""
    for stmt in cls_node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "type":
                    value = stmt.value
                    if isinstance(value, ast.Attribute):
                        return value.attr.lower()
    return None


_BASE_CLASS_TYPE_MAP = {
    "LoaderPlugin": "loader",
    "TransformerPlugin": "transformer",
    "ExporterPlugin": "exporter",
    "WidgetPlugin": "widget",
    "DeployerPlugin": "deployer",
}


def _extract_type_from_base_class(cls_node: ast.ClassDef) -> str | None:
    """Fallback: infer type from the base class name (e.g., DeployerPlugin -> deployer)."""
    for base in cls_node.bases:
        if isinstance(base, ast.Name) and base.id in _BASE_CLASS_TYPE_MAP:
            return _BASE_CLASS_TYPE_MAP[base.id]
        if isinstance(base, ast.Attribute) and base.attr in _BASE_CLASS_TYPE_MAP:
            return _BASE_CLASS_TYPE_MAP[base.attr]
    return None


def _first_paragraph(docstring: str | None) -> str:
    """Return the first paragraph of a docstring, stripped."""
    if not docstring:
        return ""
    return docstring.split("\n\n", 1)[0].strip().replace("\n", " ")


def _plugins_in_file(path: Path) -> list[dict[str, Any]]:
    """Parse a single .py file and return all @register'd plugins."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        print(f"SyntaxError in {path}: {exc}", file=sys.stderr)
        return []

    results: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for deco in node.decorator_list:
            if _decorator_name(deco) != "register":
                continue
            if not isinstance(deco, ast.Call) or not deco.args:
                continue
            first_arg = deco.args[0]
            if not (
                isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)
            ):
                continue
            name = first_arg.value
            ptype = (
                _extract_type_from_register_args(deco)
                or _extract_type_from_class_body(node)
                or _extract_type_from_base_class(node)
            )
            if ptype is None:
                print(
                    f"Skipped {name} in {path}: cannot determine type", file=sys.stderr
                )
                continue
            results.append(
                {
                    "name": name,
                    "type": ptype,
                    "body": _first_paragraph(ast.get_docstring(node)),
                }
            )
    return results


def extract_plugins(plugins_root: Path) -> list[dict[str, Any]]:
    """Walk a plugins directory and collect every registered plugin."""
    collected: list[dict[str, Any]] = []
    for py_file in sorted(plugins_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        collected.extend(_plugins_in_file(py_file))
    collected.sort(key=lambda p: (p["type"], p["name"]))
    return collected


def main() -> int:
    plugins = extract_plugins(PLUGINS_DIR)
    version = _read_package_version()
    for plugin in plugins:
        plugin["version"] = version

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(plugins, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(plugins)} plugins to {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
