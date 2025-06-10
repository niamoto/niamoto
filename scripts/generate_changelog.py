#!/usr/bin/env python3
"""
Script to generate CHANGELOG.md from git history and tags.
"""

import subprocess
import re
from datetime import datetime
from typing import List, Dict
import sys


def run_git_command(command: str) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            command.split(), capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {command}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def get_tags() -> List[str]:
    """Get all tags sorted by version."""
    output = run_git_command("git tag --sort=-version:refname")
    return output.split("\n") if output else []


def get_tag_date(tag: str) -> str:
    """Get the date of a tag."""
    try:
        output = run_git_command(f"git log -1 --format=%ai {tag}")
        # Parse the date and format it as YYYY-MM-DD
        date_str = output.split()[0]
        return date_str
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def get_commits_between_tags(tag1: str, tag2: str = None) -> List[Dict]:
    """Get commits between two tags."""
    if tag2:
        range_spec = f"{tag2}..{tag1}"
    else:
        # For the first tag, get all commits up to that tag
        range_spec = tag1

    # Get commit hashes and messages
    output = run_git_command(f"git log --pretty=format:%H|%s {range_spec}")

    commits = []
    for line in output.split("\n"):
        if line.strip():
            hash_msg = line.split("|", 1)
            if len(hash_msg) == 2:
                commits.append({"hash": hash_msg[0], "message": hash_msg[1]})

    return commits


def categorize_commit(message: str) -> str:
    """Categorize a commit based on its message."""
    message_lower = message.lower()

    # Skip version bump commits
    if "bump version" in message_lower or "version:" in message_lower:
        return "skip"

    # Skip merge commits
    if message.startswith("Merge "):
        return "skip"

    # Categorize based on conventional commit patterns
    if message.startswith("feat:") or message.startswith("feat("):
        return "Features"
    elif message.startswith("fix:") or message.startswith("fix("):
        return "Bug Fixes"
    elif message.startswith("docs:") or message.startswith("docs("):
        return "Documentation"
    elif message.startswith("refactor:") or message.startswith("refactor("):
        return "Refactoring"
    elif message.startswith("test:") or message.startswith("test("):
        return "Tests"
    elif message.startswith("chore:") or message.startswith("chore("):
        return "Chores"
    elif message.startswith("style:") or message.startswith("style("):
        return "Style"
    elif message.startswith("perf:") or message.startswith("perf("):
        return "Performance"
    elif (
        "feat:" in message_lower
        or "add" in message_lower
        or "implement" in message_lower
    ):
        return "Features"
    elif "fix" in message_lower or "bug" in message_lower:
        return "Bug Fixes"
    elif (
        "refactor" in message_lower
        or "improve" in message_lower
        or "enhance" in message_lower
    ):
        return "Improvements"
    elif "update" in message_lower or "upgrade" in message_lower:
        return "Updates"
    else:
        return "Other Changes"


def clean_commit_message(message: str) -> str:
    """Clean and format commit message for changelog."""
    # Remove conventional commit prefixes
    message = re.sub(
        r"^(feat|fix|docs|refactor|test|chore|style|perf)(\([^)]+\))?: ", "", message
    )

    # Capitalize first letter
    if message:
        message = message[0].upper() + message[1:]

    return message


def generate_changelog():
    """Generate the changelog."""
    print("Generating CHANGELOG.md from git history...")

    tags = get_tags()
    if not tags:
        print("No tags found in repository")
        return

    changelog_content = ["# Changelog", ""]
    changelog_content.append(
        "All notable changes to this project will be documented in this file."
    )
    changelog_content.append("")
    changelog_content.append(
        "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),"
    )
    changelog_content.append(
        "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."
    )
    changelog_content.append("")

    # Process each tag
    for i, tag in enumerate(tags):
        print(f"Processing {tag}...")

        # Get the previous tag
        prev_tag = tags[i + 1] if i + 1 < len(tags) else None

        # Get commits for this version
        commits = get_commits_between_tags(tag, prev_tag)

        if not commits:
            continue

        # Get tag date
        tag_date = get_tag_date(tag)

        # Add version header
        changelog_content.append(f"## [{tag}] - {tag_date}")
        changelog_content.append("")

        # Categorize commits
        categorized_commits = {}
        for commit in commits:
            category = categorize_commit(commit["message"])
            if category == "skip":
                continue

            if category not in categorized_commits:
                categorized_commits[category] = []

            clean_message = clean_commit_message(commit["message"])
            categorized_commits[category].append(clean_message)

        # Add categorized commits to changelog
        category_order = [
            "Features",
            "Bug Fixes",
            "Improvements",
            "Updates",
            "Refactoring",
            "Performance",
            "Documentation",
            "Tests",
            "Style",
            "Chores",
            "Other Changes",
        ]

        for category in category_order:
            if category in categorized_commits:
                changelog_content.append(f"### {category}")
                changelog_content.append("")
                for message in categorized_commits[category]:
                    changelog_content.append(f"- {message}")
                changelog_content.append("")

    # Write changelog
    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write("\n".join(changelog_content))

    print("CHANGELOG.md generated successfully!")


if __name__ == "__main__":
    generate_changelog()
