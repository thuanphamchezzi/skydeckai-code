import json
import os
import subprocess
from datetime import datetime

from mcp.types import TextContent

from .state import state


def list_directory_tool():
    return {
        "name": "list_directory",
        "description": "Get a detailed listing of files and directories in the specified path, including type, size, and modification "
                    "date. WHEN TO USE: When you need to explore the contents of a directory, understand what files are available, check file sizes or "
                    "modification dates, or locate specific files by name. WHEN NOT TO USE: When you need to read the contents of files (use read_file "
                    "instead), when you need a recursive listing of all subdirectories (use directory_tree instead), or when searching for files by name pattern "
                    "(use search_files instead). RETURNS: Text with each line containing file type ([DIR]/[FILE]), name, size (in B/KB/MB), and "
                    "modification date. Only works within the allowed directory. Example: Enter 'src' to list contents of the src directory, or '.' for "
                    "current directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of the directory to list. Examples: '.' for current directory, 'src' for src directory, 'docs/images' for a nested directory. The path must be within the allowed workspace.",
                }
            },
            "required": ["path"]
        },
    }

async def handle_list_directory(arguments: dict):
    from mcp.types import TextContent

    path = arguments.get("path", ".")

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")
    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {full_path}")
    if not os.path.isdir(full_path):
        raise ValueError(f"Path is not a directory: {full_path}")

    # List directory contents
    entries = []
    try:
        with os.scandir(full_path) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                    # Format size to be human readable
                    size = stat.st_size
                    if size >= 1024 * 1024:  # MB
                        size_str = f"{size / (1024 * 1024):.1f}MB"
                    elif size >= 1024:  # KB
                        size_str = f"{size / 1024:.1f}KB"
                    else:  # bytes
                        size_str = f"{size}B"

                    entry_type = "[DIR]" if entry.is_dir() else "[FILE]"
                    mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    entries.append(f"{entry_type} {entry.name:<30} {size_str:>8} {mod_time}")
                except (OSError, PermissionError):
                    continue

        entries.sort()  # Sort entries alphabetically
        return [TextContent(type="text", text="\n".join(entries))]

    except PermissionError:
        raise ValueError(f"Permission denied accessing: {full_path}")

def create_directory_tool():
    return {
        "name": "create_directory",
        "description": "Create a new directory or ensure a directory exists. "
                    "Can create multiple nested directories in one operation. "
                    "WHEN TO USE: When you need to set up project structure, organize files, create output directories before saving files, or establish a directory hierarchy. "
                    "WHEN NOT TO USE: When you only want to check if a directory exists (use get_file_info instead), or when trying to create directories outside the allowed workspace. "
                    "RETURNS: Text message confirming either that the directory was successfully created or that it already exists. "
                    "The operation succeeds silently if the directory already exists. "
                    "Only works within the allowed directory. "
                    "Example: Enter 'src/components' to create nested directories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of the directory to create. Can include nested directories which will all be created. Examples: 'logs' for a simple directory, 'src/components/buttons' for nested directories. Both absolute and relative paths are supported, but must be within the allowed workspace."
                }
            },
            "required": ["path"]
        },
    }

async def handle_create_directory(arguments: dict):
    """Handle creating a new directory."""
    from mcp.types import TextContent

    path = arguments.get("path")
    if not path:
        raise ValueError("path must be provided")

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check: ensure path is within allowed directory
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(
            f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})"
        )

    already_exists = os.path.exists(full_path)

    try:
        # Create directory and any necessary parent directories
        os.makedirs(full_path, exist_ok=True)

        if already_exists:
            return [TextContent(type="text", text=f"Directory already exists: {path}")]
        return [TextContent(
            type="text",
            text=f"Successfully created directory: {path}"
        )]
    except PermissionError:
        raise ValueError(f"Permission denied creating directory: {path}")
    except Exception as e:
        raise ValueError(f"Error creating directory: {str(e)}")

def directory_tree_tool():
    return {
        "name": "directory_tree",
        "description": "Get a recursive tree view of files and directories in the specified path as a JSON structure. "
                    "WHEN TO USE: When you need to understand the complete structure of a directory tree, visualize the hierarchy of files and directories, or get a comprehensive overview of a project's organization. "
                    "Particularly useful for large projects where you need to see nested relationships. "
                    "WHEN NOT TO USE: When you only need a flat list of files in a single directory (use directory_listing instead), or when you're only interested in specific file types (use search_files instead). "
                    "RETURNS: JSON structure where each entry includes 'name', 'type' (file/directory), and 'children' for directories. "
                    "Files have no children array, while directories always have a children array (which may be empty). "
                    "The output is formatted with 2-space indentation for readability. For Git repositories, shows tracked files only. "
                    "Only works within the allowed directory. "
                    "Example: Enter '.' for current directory, or 'src' for a specific directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root directory to analyze. This is the starting point for the recursive tree generation. Examples: '.' for current directory, 'src' for the src directory. Both absolute and relative paths are supported, but must be within the allowed workspace."
                }
            },
            "required": ["path"]
        },
    }

async def build_directory_tree(dir_path: str) -> dict:
    """Build directory tree as a JSON structure."""
    try:
        entries = list(os.scandir(dir_path))
        # Sort entries by name
        entries.sort(key=lambda e: e.name.lower())

        result = {
            "name": os.path.basename(dir_path) or dir_path,
            "type": "directory",
            "children": []
        }

        for entry in entries:
            if entry.is_dir():
                # Recursively process subdirectories
                child_tree = await build_directory_tree(entry.path)
                result["children"].append(child_tree)
            else:
                result["children"].append({
                    "name": entry.name,
                    "type": "file"
                })

        return result
    except PermissionError:
        raise ValueError(f"Access denied: {dir_path}")
    except Exception as e:
        raise ValueError(f"Error processing directory {dir_path}: {str(e)}")

async def handle_directory_tree(arguments: dict):
    """Handle building a directory tree."""
    path = arguments.get("path", ".")

    # Validate and get full path
    full_path = os.path.abspath(os.path.join(state.allowed_directory, path))
    if not os.path.abspath(full_path).startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")
    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {full_path}")
    if not os.path.isdir(full_path):
        raise ValueError(f"Path is not a directory: {full_path}")

    # Try git ls-files first
    try:
        # Get list of all files tracked by git
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=full_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # If git command was successful
        files = [f for f in result.stdout.split('\n') if f.strip()]
        files.sort()

        # Build tree from git files
        directory_map = {}
        root_name = os.path.basename(full_path) or full_path

        # First pass: collect all directories and files
        for file in files:
            parts = file.split(os.sep)
            # Add all intermediate directories
            for i in range(len(parts)):
                parent = os.sep.join(parts[:i])
                os.sep.join(parts[:i+1])
                if i < len(parts) - 1:  # It's a directory
                    directory_map.setdefault(parent, {"dirs": set(), "files": set()})["dirs"].add(parts[i])
                else:  # It's a file
                    directory_map.setdefault(parent, {"dirs": set(), "files": set()})["files"].add(parts[i])

        async def build_git_tree(current_path: str) -> dict:
            dir_name = current_path.split(os.sep)[-1] if current_path else ''
            result = {
                "name": dir_name or root_name,
                "type": "directory",
                "children": [],
            }

            if current_path not in directory_map:
                return result

            entry = directory_map[current_path]

            # Add directories first
            for dir_name in sorted(entry["dirs"]):
                child_path = os.path.join(current_path, dir_name) if current_path else dir_name
                child_tree = await build_git_tree(child_path)
                result["children"].append(child_tree)

            # Then add files
            for file_name in sorted(entry["files"]):
                result["children"].append({
                    "name": file_name,
                    "type": "file",
                })

            return result

        # Build the tree structure starting from root
        tree = await build_git_tree('')
        return [TextContent(type="text", text=json.dumps(tree, indent=2))]

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or not a git repository, use fallback implementation
        pass
    except Exception as e:
        # Log the error but continue with fallback
        print(f"Error using git ls-files: {e}")
        pass

    # Fallback to regular directory traversal
    try:
        # Build the directory tree structure
        tree = await build_directory_tree(full_path)

        # Convert to JSON with pretty printing
        json_tree = json.dumps(tree, indent=2)

        return [TextContent(type="text", text=json_tree)]
    except Exception as e:
        raise ValueError(f"Error building directory tree: {str(e)}")
