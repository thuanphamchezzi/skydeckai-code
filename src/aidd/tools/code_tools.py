import os
import re
import fnmatch
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple

from mcp.types import TextContent
from .state import state


def search_code_tool():
    return {
        "name": "search_code",
        "description": "Fast content search tool using regular expressions. "
                    "WHEN TO USE: When you need to search for specific patterns within file contents across a codebase. "
                    "Useful for finding function definitions, variable usages, import statements, or any text pattern "
                    "in source code files. "
                    "WHEN NOT TO USE: When you need to find files by name (use search_files instead), when you need "
                    "semantic code understanding (use codebase_mapper instead), or when analyzing individual file "
                    "structure. "
                    "RETURNS: Lines of code matching the specified pattern, grouped by file with line numbers. "
                    "Results are sorted by file modification time with newest files first. Respects file filtering "
                    "and ignores binary files. Search is restricted to the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for in file contents. Supports full regex syntax. "
                                   "Examples: 'function\\s+\\w+' to find function declarations, 'import\\s+.*from' to find "
                                   "import statements, 'console\\.log.*Error' to find error logs."
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include in the search. Supports glob patterns including wildcards and braces. "
                                   "Examples: '*.js' for all JavaScript files, '*.{ts,tsx}' for TypeScript files, "
                                   "'src/**/*.py' for Python files in the src directory and subdirectories.",
                    "default": "*"
                },
                "exclude": {
                    "type": "string",
                    "description": "File pattern to exclude from the search. Supports glob patterns including wildcards and braces. "
                                   "Examples: 'node_modules/**' to exclude node_modules directory, '*.min.js' to exclude minified JS.",
                    "default": ""
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matching results to return. Use to limit output size for common patterns. "
                                   "Default is 100, which is sufficient for most searches while preventing excessive output.",
                    "default": 100
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether to perform a case-sensitive search. When true, 'Error' will not match 'error'. "
                                   "Default is false, which makes searches case-insensitive.",
                    "default": False
                },
                "path": {
                    "type": "string",
                    "description": "Base directory to search from. This is the starting point for the search. "
                                   "Examples: '.' for current directory, 'src' to search only within src directory. "
                                   "Default is the root of the allowed directory.",
                    "default": "."
                }
            },
            "required": ["pattern"]
        }
    }


async def handle_search_code(arguments: dict) -> List[TextContent]:
    """Handle searching for patterns in code files."""
    pattern = arguments.get("pattern")
    include = arguments.get("include", "*")
    exclude = arguments.get("exclude", "")
    max_results = arguments.get("max_results", 100)
    case_sensitive = arguments.get("case_sensitive", False)
    path = arguments.get("path", ".")

    if not pattern:
        raise ValueError("Pattern must be provided")

    # Determine full path for search start
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")
    if not os.path.isdir(full_path):
        raise ValueError(f"Path is not a directory: {path}")

    try:
        # Use ripgrep if available for faster results
        try:
            return await _search_with_ripgrep(
                pattern, include, exclude, max_results, case_sensitive, full_path
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback to Python implementation if ripgrep not available
            return await _search_with_python(
                pattern, include, exclude, max_results, case_sensitive, full_path
            )
    except Exception as e:
        raise ValueError(f"Error searching code: {str(e)}")


async def _search_with_ripgrep(
    pattern: str,
    include: str,
    exclude: str,
    max_results: int,
    case_sensitive: bool,
    full_path: str
) -> List[TextContent]:
    """Search using ripgrep for better performance."""
    cmd = ["rg", "--line-number"]

    # Add case sensitivity flag
    if not case_sensitive:
        cmd.append("--ignore-case")

    # Add include patterns if provided
    if include and include != "*":
        # Convert glob pattern to ripgrep glob
        cmd.extend(["--glob", include])

    # Add exclude patterns if provided
    if exclude:
        # Convert glob pattern to ripgrep glob
        cmd.extend(["--glob", f"!{exclude}"])

    # Add max results
    cmd.extend(["--max-count", str(max_results)])

    # Add pattern and path
    cmd.extend([pattern, full_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.strip()
        if not output:
            return [TextContent(
                type="text",
                text="No matches found."
            )]

        # Process output to add file modification times
        files_with_matches = {}
        current_file = None

        for line in output.split('\n'):
            if not line.strip():
                continue

            # ripgrep output format: file:line:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                file_path, line_num, content = parts[0], parts[1], parts[2]

                # Get relative path for display
                rel_path = os.path.relpath(file_path, state.allowed_directory)

                if rel_path not in files_with_matches:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    files_with_matches[rel_path] = {
                        "mod_time": mod_time,
                        "matches": []
                    }

                files_with_matches[rel_path]["matches"].append(f"{line_num}: {content}")

        # Sort files by modification time (newest first)
        sorted_files = sorted(
            files_with_matches.items(),
            key=lambda x: x[1]["mod_time"],
            reverse=True
        )

        # Format output
        formatted_output = []
        for file_path, data in sorted_files:
            formatted_output.append(f"\n{file_path} (modified: {datetime.fromtimestamp(data['mod_time']).strftime('%Y-%m-%d %H:%M:%S')})")
            formatted_output.extend(data["matches"])

        return [TextContent(
            type="text",
            text="\n".join(formatted_output)
        )]

    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stderr:
            # ripgrep returns 1 when no matches are found
            return [TextContent(
                type="text",
                text="No matches found."
            )]
        raise


async def _search_with_python(
    pattern: str,
    include: str,
    exclude: str,
    max_results: int,
    case_sensitive: bool,
    full_path: str
) -> List[TextContent]:
    """Fallback search implementation using Python's regex and file operations."""
    # Compile the regex pattern
    try:
        if case_sensitive:
            regex = re.compile(pattern)
        else:
            regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regular expression: {str(e)}")

    # Convert glob patterns to regex patterns for matching
    include_pattern = fnmatch.translate(include)
    include_regex = re.compile(include_pattern)

    exclude_regex = None
    if exclude:
        exclude_pattern = fnmatch.translate(exclude)
        exclude_regex = re.compile(exclude_pattern)

    # Dictionary to store files with matches and their modification times
    files_with_matches = {}
    match_count = 0

    # Walk the directory tree
    for root, _, files in os.walk(full_path):
        if match_count >= max_results:
            break

        for filename in files:
            if match_count >= max_results:
                break

            file_path = os.path.join(root, filename)

            # Get path relative to the search root for pattern matching
            rel_path = os.path.relpath(file_path, full_path)

            # Check if file matches include pattern
            if not include_regex.match(filename) and not include_regex.match(rel_path):
                continue

            # Check if file matches exclude pattern
            if exclude_regex and (exclude_regex.match(filename) or exclude_regex.match(rel_path)):
                continue

            # Get file modification time
            try:
                mod_time = os.path.getmtime(file_path)
            except (OSError, IOError):
                continue

            # Skip binary files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        # Try to read the first few bytes to check if it's a text file
                        f.read(4096)
                        # Rewind to beginning of file
                        f.seek(0)
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue

                    # Get relative path for display
                    display_path = os.path.relpath(file_path, state.allowed_directory)

                    # Initialize entry for this file
                    if display_path not in files_with_matches:
                        files_with_matches[display_path] = {
                            "mod_time": mod_time,
                            "matches": []
                        }

                    # Search for pattern in each line
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            files_with_matches[display_path]["matches"].append(f"{line_num}: {line.rstrip()}")
                            match_count += 1

                            if match_count >= max_results:
                                break

            except (OSError, IOError):
                # Skip files that can't be read
                continue

    # No matches found
    if not files_with_matches:
        return [TextContent(
            type="text",
            text="No matches found."
        )]

    # Sort files by modification time (newest first)
    sorted_files = sorted(
        files_with_matches.items(),
        key=lambda x: x[1]["mod_time"],
        reverse=True
    )

    # Format output
    formatted_output = []
    for file_path, data in sorted_files:
        if data["matches"]:  # Only include files that actually have matches
            formatted_output.append(f"\n{file_path} (modified: {datetime.fromtimestamp(data['mod_time']).strftime('%Y-%m-%d %H:%M:%S')})")
            formatted_output.extend(data["matches"])

    return [TextContent(
        type="text",
        text="\n".join(formatted_output)
    )]
