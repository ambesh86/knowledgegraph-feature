from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_shared_agent_imports() -> None:
    """Expose the existing Eugene agent source tree to this runtime package."""
    configured_path = os.environ.get("EUGENE_AGENT_WS_SRC")
    if configured_path:
        source_path = Path(configured_path)
    else:
        source_path = (
            Path(__file__).resolve().parents[2].parent
            / "eugene-agent-ws"
            / "src"
        )
    if not source_path.is_dir():
        raise RuntimeError(
            "Eugene agent sources are not available. Set EUGENE_AGENT_WS_SRC "
            "to agents/eugene-agent-ws/src."
        )
    source = str(source_path.resolve())
    if source not in sys.path:
        sys.path.insert(0, source)