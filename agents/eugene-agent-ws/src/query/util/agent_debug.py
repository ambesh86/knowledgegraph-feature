import logging

logger = logging.getLogger(__name__)


def debugger_callback_handler(**kwargs):
    if not logger.isEnabledFor(logging.INFO):
        return

    # logger.info(f"Debug tool result: {kwargs}")
    keys = ["name", "input", "tool_result", "status"]
    for key in keys:
        if key in kwargs:
            logger.info(f"{key}: {kwargs[key]}")


def data_callback_handler(**kwargs):
    # Process stream data
    if "data" in kwargs:
        logger.info(f"MODEL OUTPUT: {kwargs['data']}")
    elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        logger.info(f"\nUSING TOOL: {kwargs['current_tool_use']['name']}")


def event_loop_tracker(**kwargs):
    # Track event loop lifecycle
    if kwargs.get("init_event_loop", False):
        logger.info("🔄 Event loop initialized")
    elif kwargs.get("start_event_loop", False):
        logger.info("▶️ Event loop cycle starting")
    elif "message" in kwargs:
        logger.info(f"📬 New message created: {kwargs['message']['role']}")
    elif kwargs.get("complete", False):
        logger.info("✅ Cycle completed")
    elif kwargs.get("force_stop", False):
        logger.info(
            f"🛑 Event loop force-stopped: {kwargs.get('force_stop_reason', 'unknown reason')}"
        )

    # Track tool usage
    if "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        current_tool = kwargs["current_tool_use"]
        # tool_name = kwargs["current_tool_use"]["name"]
        logger.info(f"🔧 Using tool: {current_tool}")

    # Show only a snippet of text to keep output clean
    if "data" in kwargs:
        n = 12
        # Only show first N chars of each chunk for demo purposes
        data_snippet = kwargs["data"][:n] + ("..." if len(kwargs["data"]) > n else "")
        logger.info(f"📟 Text: {data_snippet}")
