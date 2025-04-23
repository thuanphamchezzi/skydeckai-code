import difflib
import json
import os
import re
import stat
import subprocess
import shutil
from datetime import datetime
from typing import List

import mcp.types as types
from mcp.types import TextContent

from .state import state


def read_file_tool():
    return {
        "name": "read_file",
        "description": "Read the contents of one or more files from the file system. "
                    "WHEN TO USE: When you need to examine the actual content of one or more files, view source code, check configuration files, or analyze text data. "
                    "This is the primary tool for accessing file contents directly. "
                    "WHEN NOT TO USE: When you only need file metadata like size or modification date (use get_file_info instead), when you need to list directory contents "
                    "(use directory_listing instead). "
                    "RETURNS: The complete text content of the specified file(s) or the requested portion if offset/limit are specified. Binary files or files with unknown encodings will return an error message. "
                    "Each file's content is preceded by a header showing the file path (==> path/to/file <==). "
                    "Handles various text encodings and provides detailed error messages if a file cannot be read. Only works within the allowed directory. "
                    "Example: Use 'files: [{\"path\": \"src/main.py\"}]' to read a Python file, or add offset/limit to read specific line ranges. "
                    "For multiple files, use 'files: [{\"path\": \"file1.txt\"}, {\"path\": \"file2.txt\"}]' with optional offset/limit for each file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to read. This must be a path to a file, not a directory. Examples: 'README.md', 'src/main.py', 'config.json'. Both absolute and relative paths are supported, but must be within the allowed workspace."
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Line number to start reading from (1-indexed). If specified, the file will be read starting from this line. Default is to start from the beginning of the file."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of lines to read after the offset. If specified along with offset, only this many lines will be read. Default is to read to the end of the file."
                            }
                        },
                        "required": ["path"]
                    },
                    "description": "List of files to read with optional offset and limit for each file."
                }
            },
            "required": ["files"]
        },
    }

def write_file_tool():
    return {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing file with new content. "
                    "WHEN TO USE: When you need to save changes, create new files, or update existing ones with new content. "
                    "Useful for generating reports, creating configuration files, or saving edited content. "
                    "WHEN NOT TO USE: When you want to make targeted edits to parts of a file while preserving the rest (use edit_file instead), "
                    "when you need to append to a file without overwriting existing content, or when you need to preserve the original file. "
                    "RETURNS: A confirmation message indicating that the file was successfully written. "
                    "Creates parent directories automatically if they don't exist. "
                    "Use with caution as it will overwrite existing files without warning. Only works within the allowed directory. "
                    "Example: Path='notes.txt', Content='Meeting notes for project X'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path where to write the file. Both absolute and relative paths are supported, but must be within the allowed workspace. Examples: 'README.md', 'logs/debug.log', 'reports/report.txt'. Parent directories will be created automatically if they don't exist."
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file. The complete text content that should be saved to the file. This will completely replace any existing content if the file already exists."
                }
            },
            "required": ["path", "content"]
        },
    }

def move_file_tool():
    return {
        "name": "move_file",
        "description": "Move or rename a file or directory to a new location. "
                    "WHEN TO USE: When you need to reorganize files or directories, rename files or folders, or move items to a different location within the allowed workspace. "
                    "Useful for organizing project files, restructuring directories, or for simple renaming operations. "
                    "WHEN NOT TO USE: When you want to copy a file while keeping the original (copying functionality is not available in this tool set), "
                    "when destination already exists (the operation will fail), or when either source or destination is outside the allowed workspace. "
                    "RETURNS: A confirmation message indicating that the file or directory was successfully moved. "
                    "Parent directories of the destination will be created automatically if they don't exist. "
                    "Both source and destination must be within the allowed directory. "
                    "Example: source='old.txt', destination='new/path/new.txt'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source path of the file or directory to move. This file or directory must exist. Both absolute and relative paths are supported, but must be within the allowed workspace. Examples: 'document.txt', 'src/utils.js', 'config/old-settings/'"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path where to move the file or directory. If this path already exists, the operation will fail. Parent directories will be created automatically if they don't exist. Both absolute and relative paths are supported, but must be within the allowed workspace. Examples: 'renamed.txt', 'backup/document.txt', 'src/new-location/'"
                }
            },
            "required": ["source", "destination"]
        },
    }

def copy_file_tool():
    return {
        "name": "copy_file",
        "description": "Copy a file or directory to a new location. "
                    "WHEN TO USE: When you need to duplicate files or directories while keeping the original intact, create backups, "
                    "or replicate configuration files for different environments. Useful for testing changes without risking original files, "
                    "creating template files, or duplicating project structures. "
                    "WHEN NOT TO USE: When you want to move a file without keeping the original (use move_file instead), when the destination "
                    "already exists (the operation will fail), or when either source or destination is outside the allowed workspace. "
                    "RETURNS: A confirmation message indicating that the file or directory was successfully copied. "
                    "For directories, the entire directory structure is copied recursively. Parent directories of the destination "
                    "will be created automatically if they don't exist. Both source and destination must be within the allowed directory. "
                    "Example: source='config.json', destination='config.backup.json'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source path of the file or directory to copy. This file or directory must exist. Both absolute and relative paths are supported, but must be within the allowed workspace. Examples: 'document.txt', 'src/utils.js', 'config/settings/'"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path where to copy the file or directory. If this path already exists, the operation will fail. Parent directories will be created automatically if they don't exist. Both absolute and relative paths are supported, but must be within the allowed workspace. Examples: 'document.backup.txt', 'backup/document.txt', 'src/new-project/'"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to copy directories recursively. If set to true and the source is a directory, all subdirectories and files will be copied. If set to false and the source is a directory, the operation will fail. Defaults to true.",
                    "default": True
                }
            },
            "required": ["source", "destination"]
        },
    }

def search_files_tool():
    return {
        "name": "search_files",
        "description": "Search for files and directories matching a pattern in their names. "
                    "WHEN TO USE: When you need to find files or directories by name pattern across a directory tree, locate files with specific extensions, "
                    "or find items containing certain text in their names. Useful for locating configuration files, finding all files of a certain type, "
                    "or gathering files related to a specific feature. "
                    "WHEN NOT TO USE: When searching for content within files (use search_code tool for that), when you need a flat listing of a single directory "
                    "(use list_directory instead), or when you need to analyze code structure (use codebase_mapper instead). "
                    "RETURNS: A list of matching files and directories with their types ([FILE] or [DIR]) and relative paths. "
                    "For Git repositories, only shows tracked files and directories by default. "
                    "The search is recursive and case-insensitive. Only searches within the allowed directory. "
                    "Example: pattern='.py' finds all Python files, pattern='test' finds all items with 'test' in the name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Pattern to search for in file and directory names. The search is case-insensitive and matches substrings. Examples: '.js' to find all JavaScript files, 'test' to find all items containing 'test' in their name, 'config' to find configuration files and directories."
                },
                "path": {
                    "type": "string",
                    "description": "Starting directory for the search (defaults to allowed directory). This is the root directory from which the recursive search begins. Examples: '.' for current directory, 'src' to search only in the src directory tree. Both absolute and relative paths are supported, but must be within the allowed workspace."
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Whether to include hidden files and directories (defaults to false). On Unix-like systems, hidden items start with a dot (.). Set to true to include them in the search results."
                }
            },
            "required": ["pattern"]
        },
    }

def get_file_info_tool():
    return {
        "name": "get_file_info",
        "description": "Get detailed information about a file or directory. "
                    "WHEN TO USE: When you need to check file metadata like size, timestamps, permissions, or file type without reading the contents. "
                    "Useful for determining when files were modified, checking file sizes, verifying file existence, or distinguishing between files and directories. "
                    "WHEN NOT TO USE: When you need to read the actual content of a file (use read_file instead), or when you need to list all files in a directory (use directory_listing instead). "
                    "RETURNS: Text with information about the file or directory including type (file/directory), size in bytes, creation time, modification time, access time (all in ISO 8601 format), and permissions. "
                    "Only works within the allowed directory. "
                    "Example: path='src/main.py' returns details about main.py",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory to get information about. Can be either a file or directory path. Examples: 'README.md', 'src/components', 'package.json'. Both absolute and relative paths are supported, but must be within the allowed workspace."
                }
            },
            "required": ["path"]
        },
    }

def delete_file_tool():
    return {
        "name": "delete_file",
        "description": "Delete a file or empty directory from the file system. "
                    "WHEN TO USE: When you need to remove unwanted files, clean up temporary files, or delete empty directories. "
                    "Useful for cleaning up workspaces, removing intermediate build artifacts, or deleting temporary files. "
                    "WHEN NOT TO USE: When you need to delete non-empty directories (the operation will fail), when you want to move files instead of deleting them (use move_file instead), "
                    "or when you need to preserve the file for later use. "
                    "RETURNS: A confirmation message indicating that the file or empty directory was successfully deleted. "
                    "For safety, this tool will not delete non-empty directories. "
                    "Use with caution as this operation cannot be undone. Only works within the allowed directory. "
                    "Example: path='old_file.txt' removes the specified file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or empty directory to delete. For directories, they must be completely empty or the operation will fail. Examples: 'temp.txt', 'build/cache.json', 'empty-dir/'. Both absolute and relative paths are supported, but must be within the allowed workspace."
                }
            },
            "required": ["path"]
        },
    }

def edit_file_tool():
    return {
        "name": "edit_file",
        "description": "Make line-based edits to a text file. "
            "WHEN TO USE: When you need to make selective changes to specific parts of a file while preserving the rest of the content. "
            "Useful for modifying configuration values, updating text while maintaining file structure, or making targeted code changes. "
            "WHEN NOT TO USE: When you want to completely replace a file's contents (use write_file instead), when you need to create a new file (use write_file instead), "
            "or when you want to apply highly complex edits with context. "
            "RETURNS: A git-style diff showing the changes made, along with information about any failed matches. "
            "The response includes sections for failed matches (if any) and the unified diff output. "
            "Always use dryRun first to preview changes before applying them. Only works within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File to edit. Must be a text file that exists within the allowed workspace. Examples: 'README.md', 'src/config.js', 'settings.json'. Both absolute and relative paths are supported, but must be within the allowed workspace."
                },
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "oldText": {
                                "type": "string",
                                "description": "Text to search for in the file. This should be a unique segment of text to identify where the change should be made. Include enough context (lines before/after) to ensure the right match is found."
                            },
                            "newText": {
                                "type": "string",
                                "description": "Text to replace the matched section with. This will completely replace the oldText section. To delete text, use an empty string."
                            }
                        },
                        "required": ["oldText", "newText"]
                    },
                    "description": "List of edit operations to perform on the file. Each edit specifies text to find (oldText) and text to replace it with (newText). The edits are applied in sequence, and each one can modify the result of previous edits."
                },
                "dryRun": {
                    "type": "boolean",
                    "description": "Preview changes without applying them to the file. Set to true to see what changes would be made without actually modifying the file. Highly recommended before making actual changes.",
                    "default": False
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "partialMatch": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching for finding text. When true, the tool will try to find the best match even if it's not an exact match, using a confidence threshold of 80%.",
                            "default": True
                        }
                    }
                }
            },
            "required": ["path", "edits"]
        }
    }

async def _read_single_file(path: str, offset: int = None, limit: int = None) -> List[TextContent]:
    """Helper function to read a single file with proper validation."""
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
            # If we have offset/limit parameters, read only the specified lines
            if offset is not None or limit is not None:
                lines = f.readlines()

                # Determine start line - convert from 1-indexed to 0-indexed
                start_idx = 0
                if offset is not None:
                    start_idx = max(0, offset - 1)  # Convert 1-indexed to 0-indexed

                # Determine end line
                end_idx = len(lines)
                if limit is not None:
                    end_idx = min(len(lines), start_idx + limit)

                # Read only the specified range
                content = ''.join(lines[start_idx:end_idx])

                # Add summary information about the file before and after the selected range
                total_lines = len(lines)
                summary = []

                if start_idx > 0:
                    summary.append(f"[...{start_idx} lines before...]")

                if end_idx < total_lines:
                    summary.append(f"[...{total_lines - end_idx} lines after...]")

                if summary:
                    content = '\n'.join(summary) + '\n' + content

            else:
                # Read the entire file
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
    files = arguments.get("files")
    if not files:
        raise ValueError("files must be provided")
    if not isinstance(files, list):
        raise ValueError("files must be an array")
    if not files:
        raise ValueError("files array cannot be empty")

    # Validate each file entry
    for file_entry in files:
        if not isinstance(file_entry, dict):
            raise ValueError("each file entry must be an object")
        if "path" not in file_entry:
            raise ValueError("each file entry must have a path property")

    # Read each file with its own offset/limit
    results = []
    for file_entry in files:
        path = file_entry.get("path")
        offset = file_entry.get("offset")
        limit = file_entry.get("limit")

        try:
            # Add file path header first
            results.append(TextContent(
                type="text",
                text=f"\n==> {path} <==\n"
            ))
            # Then add file contents with specific offset/limit
            file_contents = await _read_single_file(path, offset, limit)
            results.extend(file_contents)
        except Exception as e:
            results.append(TextContent(
                type="text",
                text=f"Error: {str(e)}\n"
            ))

    return results

async def handle_move_file(arguments: dict):
    """Handle moving a file or directory to a new location."""
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

async def handle_copy_file(arguments: dict):
    """Handle copying a file or directory to a new location."""
    source = arguments.get("source")
    destination = arguments.get("destination")
    recursive = arguments.get("recursive", True)

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

    # Check if destination already exists
    if os.path.exists(full_destination):
        raise ValueError(f"Destination already exists: {destination}")

    # Create parent directories of destination if they don't exist
    os.makedirs(os.path.dirname(full_destination), exist_ok=True)

    try:
        if os.path.isdir(full_source):
            if not recursive:
                raise ValueError(f"Cannot copy directory without recursive flag: {source}")
            # Copy directory recursively
            shutil.copytree(full_source, full_destination)
            return [TextContent(
                type="text",
                text=f"Successfully copied directory {source} to {destination}"
            )]
        else:
            # Copy file
            shutil.copy2(full_source, full_destination)
            return [TextContent(
                type="text",
                text=f"Successfully copied file {source} to {destination}"
            )]
    except Exception as e:
        raise ValueError(f"Error copying {source} to {destination}: {str(e)}")

async def handle_search_files(arguments: dict):
    """Handle searching for files matching a pattern."""
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

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving indentation."""
    lines = text.splitlines()
    normalized_lines = []

    for line in lines:
        # Preserve leading whitespace
        indent = re.match(r'^\s*', line).group(0)
        # Normalize other whitespace
        content = re.sub(r'\s+', ' ', line.lstrip())
        normalized_lines.append(f"{indent}{content}")

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

        # Use original text for matching
        search_text = old_text
        working_content = modified_content

        # Find best match
        start, end, confidence = find_best_match(working_content, search_text, partial_match)

        if confidence >= 0.8:
            # Fix indentation while preserving relative structure
            if start >= 0:
                # Get the indentation of the first line of the matched text
                base_indent = re.match(r'^\s*', modified_content[start:].splitlines()[0]).group(0)

                # Split the new text into lines
                new_lines = new_text.splitlines()

                # If there are multiple lines, adjust indentation while preserving structure
                if len(new_lines) > 1:
                    # Find the minimum indentation level in the new text (ignoring empty lines)
                    non_empty_lines = [line for line in new_lines if line.strip()]
                    if non_empty_lines:
                        min_indent_length = min(len(re.match(r'^\s*', line).group(0)) for line in non_empty_lines)
                    else:
                        min_indent_length = 0

                    # Process each line to preserve relative indentation
                    processed_lines = []
                    for line in new_lines:
                        if line.strip():  # If line is not empty
                            # Get current indentation
                            current_indent = re.match(r'^\s*', line).group(0)
                            # Calculate relative indentation
                            relative_indent = len(current_indent) - min_indent_length
                            # Apply base indent plus relative indent
                            processed_lines.append(base_indent + ' ' * relative_indent + line.lstrip())
                        else:
                            # For empty lines, just use base indentation
                            processed_lines.append(base_indent)

                    replacement = '\n'.join(processed_lines)
                else:
                    # Single line - just use base indentation
                    replacement = base_indent + new_text.lstrip()
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

