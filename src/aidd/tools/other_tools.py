import asyncio
from typing import List, Dict, Any, Callable

from mcp.types import TextContent

from .state import state


def batch_tools_tool():
    return {
        "name": "batch_tools",
        "description": "Execute multiple tool invocations in parallel or serially. "
                    "WHEN TO USE: When you need to run multiple operations efficiently in a single request, "
                    "combine related operations, or gather results from different tools. Useful for bulk operations, "
                    "coordinated tasks, or performing multiple queries simultaneously. "
                    "WHEN NOT TO USE: When operations need to be performed strictly in sequence where each step depends "
                    "on the previous step's result, when performing simple operations that don't benefit from batching, "
                    "or when you need fine-grained error handling. "
                    "RETURNS: Results from all tool invocations grouped together. Each result includes the tool name "
                    "and its output. If any individual tool fails, its error is included but other tools continue execution. "
                    "Parallelizable tools are executed concurrently for performance. Each tool's output is presented in "
                    "a structured format along with the description you provided. "
                    "IMPORTANT NOTE: All tools in the batch execute in the same working directory context. If a tool creates a directory "
                    "and a subsequent tool needs to work inside that directory, you must either use paths relative to the current working directory "
                    "or include an explicit tool invocation to change directories (e.g., update_allowed_directory).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A short (3-5 word) description of the batch operation. This helps identify the purpose "
                                   "of the batch and provides context for the results. Examples: 'Setup new project', "
                                   "'Analyze codebase', 'Gather system info'."
                },
                "sequential": {
                    "type": "boolean",
                    "description": "Whether to run tools in sequential order (true) or parallel when possible (false). "
                                  "Use sequential mode when tools need to build on the results of previous tools. "
                                  "Default is false (parallel execution).",
                    "default": False
                },
                "invocations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Name of the tool to invoke. Must be a valid tool name registered in the system."
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Arguments to pass to the tool. These should match the required arguments "
                                               "for the specified tool."
                            }
                        },
                        "required": ["tool", "arguments"]
                    },
                    "description": "List of tool invocations to execute. Each invocation specifies a tool name and its arguments. "
                                  "These will be executed in parallel when possible, or serially when necessary."
                }
            },
            "required": ["description", "invocations"]
        }
    }


async def handle_batch_tools(arguments: dict) -> List[TextContent]:
    """Handle executing multiple tools in batch."""
    # Import TOOL_HANDLERS here to avoid circular imports
    from . import TOOL_HANDLERS

    description = arguments.get("description")
    invocations = arguments.get("invocations", [])
    sequential = arguments.get("sequential", False)

    if not description:
        raise ValueError("Description must be provided")
    if not invocations:
        raise ValueError("Invocations list must not be empty")

    # Validate that all tools exist before running any
    for idx, invocation in enumerate(invocations):
        tool_name = invocation.get("tool")
        if not tool_name:
            raise ValueError(f"Tool name missing in invocation #{idx+1}")

        if tool_name not in TOOL_HANDLERS:
            raise ValueError(f"Unknown tool '{tool_name}' in invocation #{idx+1}")

    # Format the results header
    header = f"Batch Operation: {description}\n"
    execution_mode = "Sequential" if sequential else "Parallel"
    header += f"Execution Mode: {execution_mode}\n"

    # Combine all results
    all_contents = [TextContent(type="text", text=header)]

    if sequential:
        # Sequential execution
        for idx, invocation in enumerate(invocations):
            tool_name = invocation.get("tool")
            tool_args = invocation.get("arguments", {})

            # Get the handler for this tool
            handler = TOOL_HANDLERS[tool_name]

            # Execute the tool and process results
            result = await _execute_tool_with_error_handling(handler, tool_args, tool_name, idx)

            # Add the result to our output
            status = "SUCCESS" if result["success"] else "ERROR"
            section_header = f"[{idx+1}] {tool_name} - {status}\n"
            all_contents.append(TextContent(type="text", text=f"\n{section_header}{'=' * len(section_header)}\n"))

            if result["success"]:
                all_contents.extend(result["content"])
            else:
                all_contents.append(TextContent(
                    type="text",
                    text=f"Error: {result['error']}"
                ))

                # If a tool fails in sequential mode, we stop execution
                if idx < len(invocations) - 1:
                    all_contents.append(TextContent(
                        type="text",
                        text=f"\nExecution stopped after failure. Remaining {len(invocations) - idx - 1} tools were not executed."
                    ))
                break
    else:
        # Parallel execution
        tasks = []

        for idx, invocation in enumerate(invocations):
            tool_name = invocation.get("tool")
            tool_args = invocation.get("arguments", {})

            # Create a task for each invocation
            handler = TOOL_HANDLERS[tool_name]
            task = asyncio.create_task(
                _execute_tool_with_error_handling(handler, tool_args, tool_name, idx)
            )
            tasks.append(task)

        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks)

        # Process results
        for tool_result in completed_results:
            tool_name = tool_result["tool_name"]
            idx = tool_result["index"]
            status = "SUCCESS" if tool_result["success"] else "ERROR"

            # Add separator and header for this tool's results
            section_header = f"[{idx+1}] {tool_name} - {status}\n"
            all_contents.append(TextContent(type="text", text=f"\n{section_header}{'=' * len(section_header)}\n"))

            # Add the actual content from the tool
            if tool_result["success"]:
                all_contents.extend(tool_result["content"])
            else:
                all_contents.append(TextContent(
                    type="text",
                    text=f"Error: {tool_result['error']}"
                ))

    return all_contents


async def _execute_tool_with_error_handling(handler, arguments, tool_name, index):
    """Execute a single tool with error handling."""
    try:
        content = await handler(arguments)
        return {
            "tool_name": tool_name,
            "index": index,
            "success": True,
            "content": content
        }
    except Exception as e:
        return {
            "tool_name": tool_name,
            "index": index,
            "success": False,
            "error": str(e)
        }


def think_tool():
    return {
        "name": "think",
        "description": "Use the tool to methodically think through a complex problem step-by-step. "
                    "WHEN TO USE: When tackling complex reasoning tasks that benefit from breaking down problems, exploring multiple perspectives, "
                    "or reasoning through chains of consequences. Ideal for planning system architecture, debugging complex issues, "
                    "anticipating edge cases, weighing tradeoffs, or making implementation decisions. "
                    "WHEN NOT TO USE: For simple explanations, direct code writing, retrieving information, or when immediate action is needed. "
                    "RETURNS: Your structured thinking process formatted as markdown. This tool helps you methodically document your reasoning "
                    "without making repository changes. Structuring your thoughts with this tool can lead to more reliable reasoning "
                    "and better decision-making, especially for complex problems where it's easy to overlook important considerations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Your step-by-step thinking process, including: breaking down problems, exploring alternatives, "
                                   "considering pros/cons, examining assumptions, listing requirements, or working through edge cases. "
                                   "Structure your thinking using markdown elements like bullet points, numbered lists, headings, or code blocks. "
                                   "The more systematic your thinking, the better the outcome."
                }
            },
            "required": ["thought"]
        }
    }


async def handle_think(arguments: dict) -> List[TextContent]:
    """Handle recording a thought without making any changes."""
    thought = arguments.get("thought")

    if not thought:
        raise ValueError("Thought must be provided")

    # Format the thought in markdown
    formatted_thought = f"""# Thought Process

{thought}

---
*Note: This is a thinking tool used for reasoning and brainstorming. No changes were made to the repository.*
"""

    return [TextContent(
        type="text",
        text=formatted_thought
    )]
