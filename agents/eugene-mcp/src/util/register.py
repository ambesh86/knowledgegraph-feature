import logging

from typing import Any, Callable

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_resources(mcp: FastMCP, resources: list[dict[str, Any]]) -> None:
    for resource in resources:
        mcp.resource(
            uri=resource["uri_template"],
            name=resource["name"],
            description=resource["description"],
            mime_type=resource["mime_type"],
        )(resource["fn"])

    logger.info(f"registered {len(resources)} resources")


def register_tools(mcp: FastMCP, tools: list[Callable]) -> None:
    for tool in tools:
        mcp.tool(tool)

    logger.info(f"registered {len(tools)} tools")
