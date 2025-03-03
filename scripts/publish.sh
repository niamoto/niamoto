#!/bin/bash
# script publish.sh
VERSION=$(grep -o 'version = "[^"]*"' pyproject.toml | cut -d'"' -f2)
rm -rf dist/
uv build
uv publish
