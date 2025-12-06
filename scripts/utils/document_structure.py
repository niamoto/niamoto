import os
import pathspec

try:
    import pyperclip

    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("pyperclip not available. Clipboard functionality disabled.")


def list_files(startpath: str) -> str:
    """
    Recursively list all files and directories under the given startpath,
    ignoring those that match patterns in .gitignore.

    Args:
        startpath (str): The path to start the search from.

    Returns:
        str: A string representation of the directory tree, including all files
        and directories that were found.
    """
    with open(".gitignore", "r", encoding="utf-8") as f:
        gitignore = f.read()
    spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore.splitlines())

    output = []
    for root, dirs, files in os.walk(startpath):
        # Ignore directories and files that match .gitignore
        dirs[:] = [d for d in dirs if not spec.match_file(f"{os.path.join(root, d)}/")]
        files = [f for f in files if not spec.match_file(os.path.join(root, f))]

        level = root.replace(startpath, "").count(os.sep)
        indent = "│   " * (level - 1) + "├── "
        output.append(f"{indent}{os.path.basename(root)}/")
        subindent = "│   " * level + "├── "
        output.extend(f"{subindent}{f}" for f in files if f != ".DS_Store")
    return "\n".join(output)


if __name__ == "__main__":
    RESULT = list_files("src/")
    print(RESULT)

    if PYPERCLIP_AVAILABLE:
        pyperclip.copy(RESULT)
        print("The output has been copied to the clipboard!")
    else:
        print("Clipboard functionality is disabled because pyperclip is not installed.")
