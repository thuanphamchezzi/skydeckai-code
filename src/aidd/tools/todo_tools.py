import json
from .todo_store import todo_store
from mcp.types import TextContent


def todo_read_tool():
    """Define the todo_read tool."""
    return {
        "name": "todo_read",
        "description": "Read the current task list from the workspace-specific todo storage. "
        "MANDATORY: This tool MUST be called before any workspace operations (file reads, code analysis, development tasks). "
        "WHEN TO USE: When you need to check the current status of tasks, review what's pending "
        "or completed, or get context about ongoing work in this workspace. "
        "You can also use this tool to pick up your previous progress. "
        "WHEN NOT TO USE: When you want to update tasks (use todo_write instead). "
        "or you do not want to interact with current workspace. "
        "RETURNS: A list of todo objects with their current status, priority, and metadata. "
        "Each workspace maintains its own isolated todo list."
        "CRITICAL: Skipping this tool when doing workspace operations violates the protocol. "
        "EXAMPLE: for a create an app/project or related requests, do read todos to pick up the progress.",
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
        "description": "Update the entire task list (complete replacement) for the current workspace. "
        "MANDATORY: This tool MUST be called when adding new tasks or updating task progress during workspace operations. "
        "WHEN TO USE: When you need to add new tasks, update task status, modify priorities, "
        "or reorganize the task list. This replaces the entire list with validation. "
        "WHEN NOT TO USE: When you only want to read current tasks (use todo_read instead), "
        "or you do not want to interact with current workspace. "
        "RETURNS: Success status and count of tasks written. Enforces business rules like "
        "unique IDs and single in-progress task constraint. "
        "CRITICAL: Task management is required for all workspace development activities. "
        "EXAMPLE: for a create an app/project or requests, do write todos to create the tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Complete list of todo items to replace the current list. Each todo must contain id, content, status, and priority fields.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique identifier for the task. Must be unique across all todos."},
                            "content": {"type": "string", "description": "Task description or content. Cannot be empty."},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Current status of the task. Only one task can be 'in_progress' at a time."},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "Task priority level."},
                            "metadata": {"type": "object", "description": "Optional additional data for the task.", "additionalProperties": True},
                        },
                        "required": ["id", "content", "status", "priority"],
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
        "description": "Update a specific todo item by ID without replacing the entire list. "
        "MANDATORY: This tool MUST be called when updating task progress during workspace operations. "
        "WHEN TO USE: When you need to update specific fields of a single todo (status, priority, content, etc.). "
        "More efficient than todo_write when only updating one task. "
        "WHEN NOT TO USE: When you need to update multiple todos at once (use todo_write instead). "
        "or you do not want to interact with current workspace. "
        "RETURNS: The updated todo and status counts (pending, in_progress, completed). "
        "Enforces business rules like unique IDs and single in-progress task constraint. "
        "CRITICAL: Task management is required for all workspace development activities. "
        "EXAMPLE: for a create an app/project or related request, do update todos to update the task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "The unique ID of the todo to update."},
                "updates": {
                    "type": "object",
                    "description": "Fields to update in the todo. Can include content, status, priority, or metadata.",
                    "properties": {
                        "content": {"type": "string", "description": "New task description or content."},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New status of the task."},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "New priority level."},
                        "metadata": {"type": "object", "description": "Additional data for the task.", "additionalProperties": True},
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
