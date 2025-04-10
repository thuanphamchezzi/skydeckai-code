import json
import os
from pathlib import Path
from typing import List

from mcp.types import TextContent


# Global state management
class GlobalState:
    def __init__(self):
        self.config_dir = Path.home() / '.skydeckai-code'
        self.config_file = self.config_dir / 'config.json'
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure the config directory exists."""
        self.config_dir.mkdir(exist_ok=True)

    def _load_config(self) -> dict:
        """Load the config file."""
        if not self.config_file.exists():
            return {}
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_config(self, config: dict):
        """Save the config file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, sort_keys=True)
        except OSError:
            pass  # Silently fail if we can't write the config

    @property
    def allowed_directory(self) -> str:
        """Get the allowed directory, falling back to Desktop if not set."""
        config = self._load_config()
        return config.get('allowed_directory', str(Path.home() / "Desktop"))

    @allowed_directory.setter
    def allowed_directory(self, value: str):
        """Set the allowed directory and persist it."""
        self._save_config({'allowed_directory': value})

# Single instance to be shared across modules
state = GlobalState()

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
            "required": []
        },
    }

async def handle_get_allowed_directory(arguments: dict) -> List[TextContent]:
    """Handle getting the allowed directory."""
    allowed_dir = state.allowed_directory
    return [TextContent(
        type="text",
        text=allowed_dir
    )]

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

async def handle_update_allowed_directory(arguments: dict) -> List[TextContent]:
    """Handle updating the allowed directory."""
    directory = arguments.get("directory", "")
    
    if not directory:
        raise ValueError("directory must be provided")
    
    # Expand ~ to user's home directory if present
    if directory.startswith("~"):
        directory = str(Path.home()) + directory[1:]
    
    # Convert to absolute path
    directory_path = Path(directory).resolve()
    
    # Check if the directory exists
    if not directory_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    
    # Check if it's a directory
    if not directory_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    # Check if it's accessible (can read and write)
    if not os.access(directory_path, os.R_OK | os.W_OK):
        raise ValueError(f"Directory is not accessible (read/write): {directory}")
    
    # Update the allowed directory
    state.allowed_directory = str(directory_path)
    
    return [TextContent(
        type="text",
        text=f"Successfully updated allowed directory to: {directory_path}"
    )]
