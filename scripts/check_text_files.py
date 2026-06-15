#!/usr/bin/env -S uv run

"""
Check tracked text files for final newlines and trailing whitespace.

Binary files such as PDFs are intentionally skipped because text formatting
rules do not apply to them.

Workflow:
1. Read Git-tracked files.
2. Keep only known text/source file extensions and text-like dotfiles.
3. Validate final newline and trailing whitespace policy.

Usage:
    python scripts/check_text_files.py --check final-newline
    python scripts/check_text_files.py --check trailing-whitespace
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = frozenset(
    {
        ".csv",
        ".json",
        ".md",
        ".py",
        ".sql",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
TEXT_FILENAMES = frozenset(
    {
        ".editorconfig",
        ".env.example",
        ".gitattributes",
        ".gitignore",
        ".pre-commit-config.yaml",
        "justfile",
    }
)


def list_tracked_files() -> list[Path]:
    """
    List Git-tracked files in the current repository.

    Returns:
        Paths tracked by Git.

    Raises:
        subprocess.CalledProcessError: If Git cannot list tracked files.
    """
    output = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(line) for line in output.splitlines() if line]


def is_text_file(path: Path) -> bool:
    """
    Determine whether a tracked path should be checked as text.

    Args:
        path: Repository-relative file path.

    Returns:
        True when the file should be checked for text formatting.
    """
    return path.name in TEXT_FILENAMES or path.suffix in TEXT_SUFFIXES


def find_files_missing_final_newline(paths: list[Path]) -> list[Path]:
    """
    Find text files that do not end with a newline.

    Args:
        paths: Candidate file paths.

    Returns:
        Files missing a final newline.
    """
    return [path for path in paths if path.is_file() and is_text_file(path) and not path.read_bytes().endswith(b"\n")]


def find_files_with_trailing_whitespace(paths: list[Path]) -> list[Path]:
    """
    Find text files containing trailing spaces or tabs.

    Args:
        paths: Candidate file paths.

    Returns:
        Files containing trailing whitespace.
    """
    bad_paths: list[Path] = []
    for path in paths:
        if not path.is_file() or not is_text_file(path):
            continue
        if any(line.rstrip(b"\n\r").endswith((b" ", b"\t")) for line in path.read_bytes().splitlines(True)):
            bad_paths.append(path)
    return bad_paths


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Check tracked text files for formatting issues.")
    parser.add_argument("--check", choices=["final-newline", "trailing-whitespace"], required=True)
    return parser.parse_args()


def main() -> int:
    """
    Run the requested text-file check.

    Returns:
        Exit code 0 when the check passes, otherwise 1.
    """
    args = parse_args()
    tracked_files = list_tracked_files()
    if args.check == "final-newline":
        bad_paths = find_files_missing_final_newline(tracked_files)
    else:
        bad_paths = find_files_with_trailing_whitespace(tracked_files)

    if bad_paths:
        print("\n".join(str(path) for path in bad_paths))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
