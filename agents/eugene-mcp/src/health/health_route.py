import logging

from fastmcp import FastMCP
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_health_route(mcp: FastMCP) -> None:
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request):
        return JSONResponse({"status": "OK", "service": "eugene mcp service"})
