import os

from mcp.types import TextContent
from .state import state


def get_allowed_directory_tool():
    """Define the get_allowed_directory tool."""
    return {
        "name": "get_allowed_directory",
        "description": "Get the current working directory that this server is allowed to access. "
                      "WHEN TO USE: When you need to understand the current workspace boundaries, determine "
                      "the root directory for relative paths, or verify where file operations are permitted. "
                      "Useful for commands that need to know the allowed workspace root. "
                      "WHEN NOT TO USE: When you already know the current working directory or when you need "
                      "to actually list files in the directory (use directory_listing instead). "
                      "RETURNS: A string containing the absolute path to the current allowed working directory. "
                      "This is the root directory within which all file operations must occur.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }

def update_allowed_directory_tool():
    """Define the update_allowed_directory tool."""
    return {
            "name": "update_allowed_directory",
            "description": "Change the working directory that this server is allowed to access. "
                        "WHEN TO USE: When you need to switch between different projects, change the workspace "
                        "root to a different directory, or expand/modify the boundaries of allowed file operations. "
                        "Useful when working with multiple projects or repositories in different locations. "
                        "WHEN NOT TO USE: When you only need to create a subdirectory within the current workspace "
                        "(use create_directory instead), or when you just want to list files in a different directory "
                        "(use directory_listing instead). "
                        "RETURNS: A confirmation message indicating that the allowed directory has been successfully "
                        "updated to the new path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to allow access to. Must be an absolute path that exists on the system. "
                                    "Use ~ to refer to the user's home directory. Examples: '/Users/username/projects', "
                                    "'~/Documents/code', '/home/user/repositories'. The directory must exist and be "
                                    "accessible to the user running the application."
                    }
                },
                "required": ["directory"]
            },
        }

async def handle_get_allowed_directory(arguments: dict):
    """Handle getting the allowed directory."""
    return [TextContent(
        type="text",
        text=f"Allowed directory: {state.allowed_directory}"
    )]

async def handle_update_allowed_directory(arguments: dict):
    """Handle updating the allowed directory."""
    directory = arguments.get("directory")
    if not directory:
        raise ValueError("directory must be provided")

    # Handle home directory expansion
    if directory.startswith("~"):
        directory = os.path.expanduser(directory)

    # Must be an absolute path
    if not os.path.isabs(directory):
        raise ValueError("Directory must be an absolute path")

    # Normalize the path
    directory = os.path.abspath(directory)

    # Verify directory exists
    if not os.path.isdir(directory):
        raise ValueError(f"Path is not a directory: {directory}")

    state.allowed_directory = directory
    return [TextContent(
        type="text",
        text=f"Successfully updated allowed directory to: {state.allowed_directory}"
    )]
