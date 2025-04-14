"""Command-line interface for the SkyDeckAI Code MCP server."""

import argparse
import asyncio
import json
import sys
import traceback
from contextlib import AsyncExitStack
from typing import Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, TextContent


class MCPClient:
    """Client for interacting with the SkyDeckAI Code MCP server."""

    def __init__(self):
        """Initialize the client."""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.debug = False

    async def connect(self):
        """Connect to the SkyDeckAI Code server."""
        server_params = StdioServerParameters(command="skydeckai-code", args=[], env=None)
        transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*transport))
        await self.session.initialize()

    async def list_tools(self):
        """List all available tools."""

        response = await self.session.list_tools()
        print("\nAvailable tools:")
        for tool in sorted(response.tools, key=lambda x: x.name):
            print(f"\n{tool.name}:")
            print(f"  Description: {tool.description}")
            print("  Arguments:")
            if tool.inputSchema and "properties" in tool.inputSchema:
                for prop_name, prop_info in tool.inputSchema["properties"].items():
                    required = (
                        "required" in tool.inputSchema
                        and prop_name in tool.inputSchema["required"]
                    )
                    req_str = "(required)" if required else "(optional)"
                    desc = prop_info.get("description", "No description available")
                    print(f"    {prop_name} {req_str}: {desc}")
            else:
                print("    No arguments required")

    async def call_tool(self, tool_name: str, args_str: Optional[str] = None) -> None:
        """Call a specific tool with arguments.

        Args:
            tool_name: Name of the tool to call
            args_str: JSON string of tool arguments
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        args = {}
        if args_str:
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError as e:
                print(f"Error parsing arguments: {e}")
                return

        try:
            result = await self.session.call_tool(tool_name, args or {})
            if isinstance(result, CallToolResult):
                for content in result.content:
                    if isinstance(content, TextContent):
                        print(content.text)
        except Exception as e:
            print(f"Result type: {type(result)}")
            print(f"Error calling tool: {e}")
            if self.debug:
                traceback.print_exc()

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="CLI for the SkyDeckAI Code MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available tools
  skydeckai-code-cli --list-tools

  # List directory contents
  skydeckai-code-cli --tool list_directory --args '{"path": "."}'

  # Update allowed directory
  skydeckai-code-cli --tool update_allowed_directory --args '{"directory": "~/Code/project"}'

  # Read a file
  skydeckai-code-cli --tool read_file --args '{"path": "README.md"}'

  # Enable debug output
  skydeckai-code-cli --debug --tool read_file --args '{"path": "README.md"}'""")
    parser.add_argument("--list-tools", action="store_true", help="List available tools")
    parser.add_argument("--tool", help="Tool to call")
    parser.add_argument("--args", help='Tool arguments in JSON format (e.g. \'{"directory":"/path/to/dir"}\')')
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    async def run(args):
        client = MCPClient()
        client.debug = args.debug
        try:
            async with AsyncExitStack() as _:
                await client.connect()
                if args.list_tools:
                    await client.list_tools()
                elif args.tool:
                    if args.debug and args.args:
                        print(f"Parsing JSON arguments: {args.args}")
                    await client.call_tool(args.tool, args.args)
                else:
                    parser.print_help()
        finally:
            await client.cleanup()

    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
