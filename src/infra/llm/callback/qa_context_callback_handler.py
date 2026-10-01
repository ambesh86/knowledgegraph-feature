from langchain_core.callbacks import BaseCallbackHandler

from typing import Any, Optional


class QaContextCallbackHandler(BaseCallbackHandler):
    """Callback Handler that prints to std out."""

    def __init__(self, color: Optional[str] = None) -> None:
        """Initialize callback handler.

        Args:
            color: The color to use for the text. Defaults to None.
        """
        self.color = color

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        """Print out that we are entering a chain.

        Args:
            serialized (Dict[str, Any]): The serialized chain.
            inputs (Dict[str, Any]): The inputs to the chain.
            **kwargs (Any): Additional keyword arguments.
        """
        if "name" in kwargs:
            name = kwargs["name"]
        else:
            if serialized:
                name = serialized.get("name", serialized.get("id", ["<unknown>"])[-1])
            else:
                name = "<unknown>"
        print(f"\n\n\033[1m> Entering new {name} chain...\033[0m")  # noqa: T201

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        """Print out that we finished a chain.

        Args:
            outputs (Dict[str, Any]): The outputs of the chain.
            **kwargs (Any): Additional keyword arguments.
        """
        print("\n\033[1m> Finished chain.\033[0m")  # noqa: T201
