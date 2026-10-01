import argparse
import asyncio
import logging

from fastmcp import FastMCP
from fastmcp.server.auth import require_auth
from fastmcp.server.middleware import AuthMiddleware


from conf.conf import eugene_jwt_verifier
from health.health_route import register_health_route
from resources.eugene_greeting_resources import EugeneGreetingResource
from tools.eugene_drug_tools import EugeneDrugTools
from tools.eugene_fact_tools import EugeneFactTools
from tools.eugene_fetch_tools import EugeneFetchTools
from tools.eugene_graph_tools import EugeneGraphTools
from tools.eugene_identity_tools import EugeneIdentityTools
from tools.eugene_node_tools import EugeneNodeTools
from tools.eugene_organization_tools import EugeneOrganizationTools
from tools.eugene_stats_tools import EugeneStatsTools
from tools.eugene_vector_tools import EugeneVectorTools
from util.register import register_resources, register_tools

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def _registration(mcp: FastMCP) -> None:
    _register_tools(mcp)

    logger.info("registering resources...")
    register_resources(mcp, [*EugeneGreetingResource.as_resources()])

    logger.info("registering health route...")
    register_health_route(mcp)


def _register_tools(mcp: FastMCP) -> None:
    logger.info("registering tools...")
    register_tools(
        mcp,
        [
            EugeneIdentityTools.fetch_identity,
            EugeneFetchTools.fetch_by_label,
            EugeneFetchTools.fetch_similar,
            EugeneNodeTools.lookup_node_by_value,
            EugeneNodeTools.fetch_node_details,
            EugeneDrugTools.fetch_drug_aliases,
            EugeneFactTools.fetch_facts,
            EugeneGraphTools.fetch_node_relationships,
            EugeneGraphTools.has_reachable_path,
            EugeneGraphTools.fetch_paths,
            EugeneOrganizationTools.find_organization_names,
            EugeneOrganizationTools.find_organization_assets,
            EugeneVectorTools.search_summaries,
            EugeneVectorTools.search_fused,
            EugeneStatsTools.fetch_graph_stats,
            EugeneStatsTools.fetch_top_connected_proteins,
            EugeneStatsTools.fetch_shared_gene_diseases,
        ],
    )
    logger.info("listing registered tools...")
    _print_loaded_tool_names(mcp)


def _print_loaded_tool_names(mcp: FastMCP) -> None:
    if not logger.isEnabledFor(logging.INFO):
        return
    tools = asyncio.run(mcp.list_tools())
    names = sorted([tool.name for tool in tools])
    for name in names:
        logger.info(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="The EUGENE webservice MCP server")
    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default="127.0.0.1",
        required=False,
        help="Host address",
    )
    parser.add_argument(
        "--port", "-P", type=str, default="8000", required=False, help="Port"
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    mcp = FastMCP(
        name="EUGENE Knowledge Graph MCP Server",
        host=args.host,
        port=args.port,
        stateless_http=True,
        auth=eugene_jwt_verifier(),
        middleware=[AuthMiddleware(auth=require_auth)],
    )
    _registration(mcp)
    logger.info("starting mcp server...")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
