from typing import Any, Dict

import mcp.types as types


class Tool:
    """Base class for all tools"""
    name: str
    description: str
    input_schema: Dict[str, Any]

    @classmethod
    def get_definition(cls) -> types.Tool:
        return types.Tool(
            name=cls.name,
            description=cls.description,
            inputSchema=cls.input_schema
        )
