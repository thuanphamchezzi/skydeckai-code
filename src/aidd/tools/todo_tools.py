import json
from .todo_store import todo_store
from mcp.types import TextContent


def todo_read_tool():
    """Define the todo_read tool."""
    return {
        "name": "todo_read",
        "description": "MANDATORY: Read workspace todo list. MUST be called FIRST before ANY workspace operations. "
        "WORKSPACE-FIRST RULE: Required for all development tasks, file operations, project work. "
        "USE: Check task status, understand project context, resume work. "
        "NOT: Pure informational queries unrelated to workspace. "
        "RETURNS: Sequential task list with status. Each workspace has isolated todos. "
        "Examples: Project setup, code development, file modifications, analysis",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


def todo_write_tool():
    """Define the todo_write tool."""
    return {
        "name": "todo_write",
        "description": "MANDATORY: Replace entire todo list for workspace planning. Sequential execution model. "
        "USE: Plan projects, organize development phases, batch task updates. "
        "NOT: Single task updates (use todo_update), reading (use todo_read). "
        "CRITICAL: Only one task can be 'in_progress' at a time. Tasks execute in array order. "
        "Examples: Project setup, feature development, bug fixing, refactoring",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Complete todo list for sequential execution. Tasks execute in array order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique task identifier."},
                            "content": {"type": "string", "description": "Task description (required)."},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Task status (only one 'in_progress' allowed)."},
                            "metadata": {"type": "object", "description": "Optional task metadata.", "additionalProperties": True},
                        },
                        "required": ["id", "content", "status"],
                        "additionalProperties": True,
                    },
                }
            },
            "required": ["todos"],
        },
    }


def todo_update_tool():
    """Define the todo_update tool."""
    return {
        "name": "todo_update",
        "description": "MANDATORY: Update specific todo by ID for workflow progression. "
        "USE: Mark in-progress when starting, completed when finished. "
        "NOT: Multiple updates (use todo_write), adding tasks. "
        "Enforces sequential workflow - one active task only. "
        "Example: todo_id='123', updates={\"status\": \"completed\"}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "Todo ID to update."},
                "updates": {
                    "type": "object",
                    "description": "Fields to update (content, status, metadata).",
                    "properties": {
                        "content": {"type": "string", "description": "New task description."},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New task status."},
                        "metadata": {"type": "object", "description": "Additional task data.", "additionalProperties": True},
                    },
                    "additionalProperties": True,
                },
            },
            "required": ["todo_id", "updates"],
        },
    }


async def handle_todo_read(arguments: dict) -> list[TextContent]:
    """Handle reading todos from storage."""
    try:
        todos = todo_store.read_todos()

        result = {"todos": todos, "count": len(todos), "workspace": str(todo_store.workspace_path)}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": {"code": "READ_ERROR", "message": f"Failed to read todos: {str(e)}"}}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def handle_todo_write(arguments: dict) -> list[TextContent]:
    """Handle writing todos to storage."""
    try:
        todos = arguments.get("todos", [])

        if not isinstance(todos, list):
            raise ValueError("Todos must be provided as a list")

        count = todo_store.write_todos(todos)

        result = {"success": True, "count": count, "workspace": str(todo_store.workspace_path)}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": {"code": "VALIDATION_ERROR" if "validation" in str(e).lower() or "invalid" in str(e).lower() or "duplicate" in str(e).lower() else "WRITE_ERROR", "message": str(e)}}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def handle_todo_update(arguments: dict) -> list[TextContent]:
    """Handle updating a specific todo."""
    try:
        todo_id = arguments.get("todo_id")
        updates = arguments.get("updates", {})

        if not todo_id:
            raise ValueError("todo_id is required")

        if not isinstance(updates, dict):
            raise ValueError("Updates must be provided as a dictionary")

        if not updates:
            raise ValueError("Updates cannot be empty")

        result = todo_store.update_todo(todo_id, updates)
        result["success"] = True
        result["workspace"] = str(todo_store.workspace_path)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": {"code": "VALIDATION_ERROR" if "validation" in str(e).lower() or "invalid" in str(e).lower() or "not found" in str(e).lower() else "UPDATE_ERROR", "message": str(e)}}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
