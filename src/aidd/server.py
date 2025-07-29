import asyncio
import json
from typing import Any, Dict

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS

server = Server("skydeckai-code")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [types.Tool(**tool) for tool in TOOL_DEFINITIONS]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    if not arguments:
        arguments = {}

    handler = TOOL_HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")

    # Preprocess arguments to handle JSON strings passed as objects
    tool_definition: dict = next(filter(lambda d: d["name"] == name, TOOL_DEFINITIONS))
    processed_arguments = _preprocess_arguments(arguments, tool_definition.get("inputSchema", {}))

    return await handler(processed_arguments)


def _preprocess_arguments(arguments: Dict[str, Any], input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess tool arguments to handle cases where LLMs pass JSON strings instead of objects.

    This function analyzes the tool's input schema and converts string parameters back to their
    expected types (objects/arrays) when they appear to be JSON-encoded strings.

    Args:
        arguments: The raw arguments passed by the LLM
        input_schema: The JSON schema definition for the tool's expected input

    Returns:
        Processed arguments with JSON strings converted to appropriate objects
    """
    if not arguments or not input_schema:
        return arguments

    # Get the properties definition from the schema
    properties = input_schema.get("properties", {})
    if not properties:
        return arguments

    # Create a copy to avoid mutating the original
    processed = arguments.copy()

    # Process each argument according to its expected schema
    for param_name, param_value in arguments.items():
        if param_name not in properties:
            continue

        expected_schema = properties[param_name]
        processed[param_name] = _process_parameter(param_value, expected_schema)

    return processed


def _process_parameter(value: Any, schema: Dict[str, Any]) -> Any:
    """
    Process a single parameter according to its schema definition.

    Args:
        value: The parameter value to process
        schema: The JSON schema for this parameter

    Returns:
        The processed parameter value
    """
    expected_type = schema.get("type")

    # If the value is a string but we expect an object or array, try to parse it as JSON
    if isinstance(value, str) and expected_type in ("object", "array"):
        # Try multiple approaches for JSON parsing to handle various escaping scenarios
        parsed_value = _attempt_json_parsing(value)
        if parsed_value is not None:
            # Recursively process the parsed object if it has nested structure
            if expected_type == "object" and isinstance(parsed_value, dict):
                return _process_nested_object(parsed_value, schema)
            elif expected_type == "array" and isinstance(parsed_value, list):
                return _process_nested_array(parsed_value, schema)
            else:
                return parsed_value
        # If all parsing attempts fail, return the original value
        return value

    # For objects, recursively process nested properties
    elif isinstance(value, dict) and expected_type == "object":
        return _process_nested_object(value, schema)

    # For arrays, recursively process items
    elif isinstance(value, list) and expected_type == "array":
        return _process_nested_array(value, schema)

    # For all other cases, return the value unchanged
    return value


def _attempt_json_parsing(value: str) -> Any:
    """
    Attempt to parse a string as JSON using multiple strategies to handle various escaping scenarios.
    
    Args:
        value: String value to parse as JSON
        
    Returns:
        Parsed JSON value or None if parsing fails
    """
    # Strategy 1: Direct JSON parsing
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Strategy 2: Handle double-escaped quotes by unescaping once
    try:
        # Replace \\\" with \" and \\\\ with \\
        unescaped = value.replace('\\"', '"').replace('\\\\', '\\')
        return json.loads(unescaped)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Strategy 3: Handle cases where the entire string might be over-escaped
    try:
        # Try to decode as if it was encoded multiple times
        decoded = value.encode().decode('unicode_escape')
        return json.loads(decoded)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        pass
    
    # If all strategies fail, return None
    return None


def _process_nested_object(obj: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively process nested object properties according to their schema.

    Args:
        obj: The object to process
        schema: The JSON schema for this object

    Returns:
        The processed object with nested parameters handled
    """
    properties = schema.get("properties", {})
    if not properties:
        return obj

    processed = obj.copy()
    for prop_name, prop_value in obj.items():
        if prop_name in properties:
            processed[prop_name] = _process_parameter(prop_value, properties[prop_name])

    return processed


def _process_nested_array(arr: list, schema: Dict[str, Any]) -> list:
    """
    Recursively process array items according to their schema.

    Args:
        arr: The array to process
        schema: The JSON schema for this array

    Returns:
        The processed array with items handled according to their schema
    """
    items_schema = schema.get("items", {})
    if not items_schema:
        return arr

    return [_process_parameter(item, items_schema) for item in arr]


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="skydeckai-code",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


# This is needed if you'd like to connect to a custom client
if __name__ == "__main__":
    asyncio.run(main())
