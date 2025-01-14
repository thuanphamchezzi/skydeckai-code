import os

from .state import state


def get_allowed_directory_tool():
    return {
        "name": "get_allowed_directory",
        "description": "Get the current working directory that this server is allowed to access.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }

def update_allowed_directory_tool():
    return {
        "name": "update_allowed_directory",
        "description": "Change the working directory that this server is allowed to access. "
                    "Use this to switch between different projects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to allow access to. Must be an absolute path. Use ~ to refer to the user's home directory.",
                },
            },
            "required": ["directory"],
        },
    }

async def handle_get_allowed_directory(arguments: dict):
    from mcp.types import TextContent
    return [TextContent(
        type="text",
        text=f"Allowed directory: {state.allowed_directory}"
    )]

async def handle_update_allowed_directory(arguments: dict):
    from mcp.types import TextContent

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
        text=f"Updated allowed directory to: {state.allowed_directory}"
    )]
