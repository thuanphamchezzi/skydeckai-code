import difflib
import json
import os
import re
import stat
import subprocess
from datetime import datetime
from typing import List

import mcp.types as types

from .state import state


def read_file_tool():
    return {
        "name": "read_file",
        "description": "Read the complete contents of a file from the file system. "
                    "Handles various text encodings and provides detailed error messages "
                    "if the file cannot be read. Use this tool when you need to examine "
                    "the contents of a single file. Only works within the allowed directory."
                    "Example: Enter 'src/main.py' to read a Python file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read",
                }
            },
            "required": ["path"]
        },
    }

def write_file_tool():
    return {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing file with new content. "
                    "Use this to save changes, create new files, or update existing ones. "
                    "Use with caution as it will overwrite existing files without warning. "
                    "Path must be relative to the allowed directory. Creates parent directories if needed. "
                    "Example: Path='notes.txt', Content='Meeting notes for project X'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path where to write the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        },
    }

def move_file_tool():
    return {
        "name": "move_file",
        "description": "Move or rename a file or directory to a new location. "
                    "This tool can be used to reorganize files and directories. "
                    "Both source and destination must be within the allowed directory. "
                    "If the destination already exists, the operation will fail. "
                    "Parent directories of the destination will be created if they don't exist. "
                    "Example: source='old.txt', destination='new/path/new.txt'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source path of the file or directory to move"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path where to move the file or directory"
                }
            },
            "required": ["source", "destination"]
        },
    }

def search_files_tool():
    return {
        "name": "search_files",
        "description": "Search for files and directories matching a pattern. "
                    "The search is recursive and case-insensitive. "
                    "Only searches within the allowed directory. "
                    "Returns paths relative to the allowed directory. "
                    "Searches in file and directory names, not content. "
                    "For searching within file contents, use the tree_sitter_map tool which can locate specific code elements like functions and classes. "
                    "Example: pattern='.py' finds all Python files, "
                    "pattern='test' finds all items with 'test' in the name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Starting directory for the search (defaults to allowed directory)"
                },
                "pattern": {
                    "type": "string",
                    "description": "Pattern to search for in file and directory names"
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Whether to include hidden files and directories (defaults to false)"
                }
            },
            "required": ["pattern"]
        },
    }

def get_file_info_tool():
    return {
        "name": "get_file_info",
        "description": "Get detailed information about a file or directory. "
                    "Returns size, creation time, modification time, access time, "
                    "type (file/directory), and permissions. "
                    "All times are in ISO 8601 format. "
                    "This tool is perfect for understanding file characteristics without reading the actual content. "
                    "Only works within the allowed directory. "
                    "Example: path='src/main.py' returns details about main.py",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory"
                }
            },
            "required": ["path"]
        },
    }

def delete_file_tool():
    return {
        "name": "delete_file",
        "description": "Delete a file or empty directory from the file system. "
                    "Use with caution as this operation cannot be undone. "
                    "For safety, this tool will not delete non-empty directories. "
                    "Only works within the allowed directory. "
                    "Example: path='old_file.txt' removes the specified file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or empty directory to delete"
                }
            },
            "required": ["path"]
        },
    }

def read_multiple_files_tool():
    return {
        "name": "read_multiple_files",
        "description": "Read the contents of multiple files simultaneously. "
                    "This is more efficient than reading files one by one when you need to analyze "
                    "or compare multiple files. Each file's content is returned with its "
                    "path as a reference. Failed reads for individual files won't stop "
                    "the entire operation. Only works within the allowed directory."
                    "Example: Enter ['src/main.py', 'README.md'] to read both files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to read",
                }
            },
            "required": ["paths"]
        },
    }

def edit_file_tool():
    return {
        "name": "edit_file",
        "description": "Make line-based edits to a text file. Each edit replaces exact line sequences "
            "with new content. Returns a git-style diff showing the changes made. "
            "Only works within the allowed directory. "
            "Always use dryRun first to preview changes before applying them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File to edit"
                },
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "oldText": {
                                "type": "string",
                                "description": "Text to search for (can be substring)"
                            },
                            "newText": {
                                "type": "string",
                                "description": "Text to replace with"
                            }
                        },
                        "required": ["oldText", "newText"]
                    },
                    "description": "List of edit operations"
                },
                "dryRun": {
                    "type": "boolean",
                    "description": "Preview changes without applying",
                    "default": False
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "preserveIndentation": {
                            "type": "boolean",
                            "description": "Keep existing indentation",
                            "default": True
                        },
                        "normalizeWhitespace": {
                            "type": "boolean",
                            "description": "Normalize spaces while preserving structure",
                            "default": True
                        },
                        "partialMatch": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching",
                            "default": True
                        }
                    }
                }
            },
            "required": ["path", "edits"]
        }
    }

async def _read_single_file(path: str) -> List[types.TextContent]:
    """Helper function to read a single file with proper validation."""
    from mcp.types import TextContent

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    if not os.path.exists(full_path):
        raise ValueError(f"File does not exist: {full_path}")
    if not os.path.isfile(full_path):
        raise ValueError(f"Path is not a file: {full_path}")

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return [TextContent(
                type="text",
                text=content
            )]
    except UnicodeDecodeError:
        raise ValueError(f"File is not a text file or has unknown encoding: {full_path}")
    except PermissionError:
        raise ValueError(f"Permission denied reading file: {full_path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

async def handle_write_file(arguments: dict):
    """Handle writing content to a file."""
    from mcp.types import TextContent

    path = arguments.get("path")
    content = arguments.get("content")

    if not path:
        raise ValueError("path must be provided")
    if content is None:
        raise ValueError("content must be provided")

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    try:
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return [TextContent(
            type="text",
            text=f"Successfully wrote to {path}"
        )]
    except Exception as e:
        raise ValueError(f"Error writing file: {str(e)}")


async def handle_read_file(arguments: dict):
    path = arguments.get("path")
    if not path:
        raise ValueError("path must be provided")

    return await _read_single_file(path)

async def handle_read_multiple_files(arguments: dict):
    paths = arguments.get("paths", [])
    if not isinstance(paths, list):
        raise ValueError("paths must be a list of strings")
    if not all(isinstance(p, str) for p in paths):
        raise ValueError("all paths must be strings")
    if not paths:
        raise ValueError("paths list cannot be empty")

    from mcp.types import TextContent
    results = []
    for path in paths:
        try:
            # Add file path header first
            results.append(TextContent(
                type="text",
                text=f"\n==> {path} <==\n"
            ))
            # Then add file contents
            file_contents = await _read_single_file(path)
            results.extend(file_contents)
        except Exception as e:
            results.append(TextContent(
                type="text",
                text=f"Error: {str(e)}\n"
            ))
    return results

async def handle_move_file(arguments: dict):
    """Handle moving a file or directory to a new location."""
    from mcp.types import TextContent

    source = arguments.get("source")
    destination = arguments.get("destination")

    if not source:
        raise ValueError("source must be provided")
    if not destination:
        raise ValueError("destination must be provided")

    # Determine full paths based on whether inputs are absolute or relative
    if os.path.isabs(source):
        full_source = os.path.abspath(source)
    else:
        full_source = os.path.abspath(os.path.join(state.allowed_directory, source))

    if os.path.isabs(destination):
        full_destination = os.path.abspath(destination)
    else:
        full_destination = os.path.abspath(os.path.join(state.allowed_directory, destination))

    # Security checks
    if not full_source.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Source path ({full_source}) must be within allowed directory")
    if not full_destination.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Destination path ({full_destination}) must be within allowed directory")

    # Validate source exists
    if not os.path.exists(full_source):
        raise ValueError(f"Source path does not exist: {source}")

    # Create parent directories of destination if they don't exist
    os.makedirs(os.path.dirname(full_destination), exist_ok=True)

    try:
        # Perform the move operation
        os.rename(full_source, full_destination)
        return [TextContent(
            type="text",
            text=f"Successfully moved {source} to {destination}"
        )]
    except OSError as e:
        raise ValueError(f"Error moving file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")

async def handle_search_files(arguments: dict):
    """Handle searching for files matching a pattern."""
    from mcp.types import TextContent

    pattern = arguments.get("pattern")
    start_path = arguments.get("path", ".")
    include_hidden = arguments.get("include_hidden", False)

    if not pattern:
        raise ValueError("pattern must be provided")

    # Determine full path for search start
    if os.path.isabs(start_path):
        full_start_path = os.path.abspath(start_path)
    else:
        full_start_path = os.path.abspath(os.path.join(state.allowed_directory, start_path))

    # Security check
    if not full_start_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_start_path}) must be within allowed directory")

    if not os.path.exists(full_start_path):
        raise ValueError(f"Start path does not exist: {start_path}")
    if not os.path.isdir(full_start_path):
        raise ValueError(f"Start path is not a directory: {start_path}")

    matches = []
    pattern = pattern.lower()  # Case-insensitive search

    # Try git ls-files first
    try:
        # First, check if this is a git repository and get tracked files
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=full_start_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Also get git directories (excluding .git itself)
        dirs_result = subprocess.run(
            ['git', 'ls-tree', '-d', '-r', '--name-only', 'HEAD'],
            cwd=full_start_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Process git-tracked files
        files = result.stdout.splitlines()
        dirs = dirs_result.stdout.splitlines()

        # Process directories first
        for dir_path in dirs:
            if pattern in dir_path.lower():
                if include_hidden or not any(part.startswith('.') for part in dir_path.split(os.sep)):
                    matches.append(f"[DIR] {dir_path}")

        # Then process files
        for file_path in files:
            if pattern in file_path.lower():
                if include_hidden or not any(part.startswith('.') for part in file_path.split(os.sep)):
                    matches.append(f"[FILE] {file_path}")

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to regular directory walk if git is not available or not a git repository
        try:
            for root, dirs, files in os.walk(full_start_path):
                # Get paths relative to allowed directory
                rel_root = os.path.relpath(root, state.allowed_directory)

                # Skip hidden directories if not included
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                # Process directories
                for dir_name in dirs:
                    if pattern in dir_name.lower():
                        rel_path = os.path.join(rel_root, dir_name)
                        if include_hidden or not any(part.startswith('.') for part in rel_path.split(os.sep)):
                            matches.append(f"[DIR] {rel_path}")

                # Process files
                for file_name in files:
                    if pattern in file_name.lower():
                        rel_path = os.path.join(rel_root, file_name)
                        if include_hidden or not any(part.startswith('.') for part in rel_path.split(os.sep)):
                            matches.append(f"[FILE] {rel_path}")

        except Exception as e:
            raise ValueError(f"Error searching files: {str(e)}")

    # Sort matches for consistent output
    matches.sort()

    if not matches:
        return [TextContent(
            type="text",
            text="No matches found"
        )]

    return [TextContent(
        type="text",
        text="\n".join(matches)
    )]

async def handle_get_file_info(arguments: dict):
    """Handle getting detailed information about a file or directory."""
    from mcp.types import TextContent

    path = arguments.get("path")
    if not path:
        raise ValueError("path must be provided")

    # Determine full path
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")

    try:
        stat_info = os.stat(full_path)

        # Format file type
        file_type = "directory" if os.path.isdir(full_path) else "file"

        # Format permissions in octal
        perms = stat.filemode(stat_info.st_mode)

        info = f"""Type: {file_type}
Size: {stat_info.st_size:,} bytes
Created: {datetime.fromtimestamp(stat_info.st_ctime).isoformat()}
Modified: {datetime.fromtimestamp(stat_info.st_mtime).isoformat()}
Accessed: {datetime.fromtimestamp(stat_info.st_atime).isoformat()}
Permissions: {perms}"""

        return [TextContent(type="text", text=info)]

    except Exception as e:
        raise ValueError(f"Error getting file info: {str(e)}")

async def handle_delete_file(arguments: dict):
    """Handle deleting a file or empty directory."""
    from mcp.types import TextContent

    path = arguments.get("path")
    if not path:
        raise ValueError("path must be provided")

    # Determine full path
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")

    try:
        if os.path.isdir(full_path):
            # Check if directory is empty
            if os.listdir(full_path):
                raise ValueError(f"Cannot delete non-empty directory: {path}")
            os.rmdir(full_path)
            return [TextContent(
                type="text",
                text=f"Successfully deleted empty directory: {path}"
            )]
        else:
            os.remove(full_path)
            return [TextContent(
                type="text",
                text=f"Successfully deleted file: {path}"
            )]
    except Exception as e:
        raise ValueError(f"Error deleting {path}: {str(e)}")

def normalize_whitespace(text: str, preserve_indentation: bool = True) -> str:
    """Normalize whitespace while optionally preserving indentation."""
    lines = text.splitlines()
    normalized_lines = []

    for line in lines:
        if preserve_indentation:
            # Preserve leading whitespace
            indent = re.match(r'^\s*', line).group(0)
            # Normalize other whitespace
            content = re.sub(r'\s+', ' ', line.lstrip())
            normalized_lines.append(f"{indent}{content}")
        else:
            # Normalize all whitespace
            normalized_lines.append(re.sub(r'\s+', ' ', line.strip()))

    return '\n'.join(normalized_lines)

def create_unified_diff(original: str, modified: str, filepath: str) -> str:
    """Create a unified diff between two texts."""
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f'a/{filepath}',
        tofile=f'b/{filepath}',
        n=0,  # No context lines needed for single line changes
        lineterm=''  # Don't add newlines here
    )

    # Join lines with single newlines and strip any extra whitespace
    return '\n'.join(line.rstrip() for line in diff)

def find_substring_position(content: str, pattern: str) -> tuple[int, int]:
    """Find the position of a substring in content."""
    pos = content.find(pattern)
    if pos >= 0:
        return pos, pos + len(pattern)
    return -1, -1

def find_best_match(content: str, pattern: str, partial_match: bool = True) -> tuple[int, int, float]:
    """Find the best matching position for a pattern in content."""
    if not partial_match:
        # Exact matching only
        pos = content.find(pattern)
        if pos >= 0:
            return pos, pos + len(pattern), 1.0
        return -1, -1, 0.0

    # Try exact substring match first
    start, end = find_substring_position(content, pattern)
    if start >= 0:
        return start, end, 1.0

    # If no exact substring match, try line-based fuzzy matching

    # Split into lines for line-based matching
    content_lines = content.splitlines()
    pattern_lines = pattern.splitlines()

    best_score = 0.0
    best_start = -1
    best_end = -1

    for i in range(len(content_lines) - len(pattern_lines) + 1):
        # Compare each potential match position
        window = content_lines[i:i + len(pattern_lines)]
        score = sum(difflib.SequenceMatcher(None, a, b).ratio()
                   for a, b in zip(window, pattern_lines)) / len(pattern_lines)

        if score > best_score:
            best_score = score
            best_start = sum(len(line) + 1 for line in content_lines[:i])
            best_end = best_start + sum(len(line) + 1 for line in window)

    return best_start, best_end, best_score

async def apply_file_edits(file_path: str, edits: List[dict], dry_run: bool = False, options: dict = None) -> str:
    """Apply edits to a file with optional formatting and return diff."""
    # Set default options
    options = options or {}
    preserve_indentation = options.get('preserveIndentation', True)
    normalize_ws = options.get('normalizeWhitespace', True)
    partial_match = options.get('partialMatch', True)

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track modifications
    modified_content = content
    failed_matches = []

    # Apply each edit
    for edit in edits:
        old_text = edit['oldText']
        new_text = edit['newText']

        # Normalize texts if requested
        if normalize_ws:
            search_text = normalize_whitespace(old_text, preserve_indentation)
            working_content = normalize_whitespace(modified_content, preserve_indentation)
        else:
            search_text = old_text
            working_content = modified_content

        # Find best match
        start, end, confidence = find_best_match(working_content, search_text, partial_match)

        if confidence >= 0.8:
            # Preserve indentation of first line if requested
            if preserve_indentation and start >= 0:
                indent = re.match(r'^\s*', modified_content[start:].splitlines()[0]).group(0)
                replacement = '\n'.join(indent + line.lstrip()
                                      for line in new_text.splitlines())
            else:
                replacement = new_text

            # Apply the edit
            modified_content = modified_content[:start] + replacement + modified_content[end:]
        else:
            failed_matches.append({
                'oldText': old_text,
                'confidence': confidence,
                'bestMatch': working_content[start:end] if start >= 0 and end > start else None
            })

    # Create diff
    diff = create_unified_diff(content, modified_content, os.path.basename(file_path))

    # Write changes if not dry run
    if not dry_run and not failed_matches:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

    # Return results
    failed_matches_text = '=== Failed Matches ===\n' + json.dumps(failed_matches, indent=2) + '\n\n' if failed_matches else ''
    diff_text = f'=== Diff ===\n{diff}'
    return failed_matches_text + diff_text

async def handle_edit_file(arguments: dict):
    """Handle editing a file with pattern matching and formatting."""
    from mcp.types import TextContent

    path = arguments.get("path")
    edits = arguments.get("edits")
    dry_run = arguments.get("dryRun", False)
    options = arguments.get("options", {})

    if not path:
        raise ValueError("path must be provided")
    if not edits or not isinstance(edits, list):
        raise ValueError("edits must be a non-empty list")

    # Validate edits structure
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("each edit must be an object")
        if 'oldText' not in edit or 'newText' not in edit:
            raise ValueError("each edit must have oldText and newText properties")

    # Determine full path and validate
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    try:
        result = await apply_file_edits(full_path, edits, dry_run, options)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        raise ValueError(f"Error editing file: {str(e)}")

