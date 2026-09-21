"""
title: Custom Tool Template
author: Your Name
version: 0.1.0
license: MIT
description: A starter Open WebUI tool template for creating your own functions.

This file is intentionally commented so you can see each section of a working tool.
It follows the same class-based pattern used by Open WebUI custom tools.
"""

# ---------------------------------------------------------------------------
# 1) Imports
# ---------------------------------------------------------------------------
# Import only what you need. Keep dependencies light and standard-library-first.
# You can add third-party libraries if your tool needs them.
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 2) Tool class definition
# ---------------------------------------------------------------------------
# Every Open WebUI custom tool should define a class named Tools.
# Inside it, define a nested Valves model to provide configurable settings.
# The actual callable methods are the functions the agent can use.
class Tools:
    # -------------------------------------------------------------------
    # 2a) Valves
    # -------------------------------------------------------------------
    # These are configuration values exposed in the Open WebUI admin UI.
    # Use them for defaults, timeouts, path settings, feature toggles, etc.
    class Valves(BaseModel):
        example_timeout: float = Field(
            default=5.0,
            description="Example timeout setting for a tool call.",
        )
        example_flag: bool = Field(
            default=True,
            description="Example boolean toggle for a tool behavior.",
        )
        example_prefix: str = Field(
            default="demo",
            description="Example string value used by helper functions.",
        )

    # -------------------------------------------------------------------
    # 2b) Constructor
    # -------------------------------------------------------------------
    # Initialize tool state here.
    # `self.citation = True` is often useful in Open WebUI to allow citations.
    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    # -------------------------------------------------------------------
    # 3) Internal helper methods
    # -------------------------------------------------------------------
    # These are private methods (underscore prefix) used by the public methods.
    # They help keep the tool organized and readable.
    # Keep them simple and focused on one task.
    def _helper_example(self, value: str) -> str:
        """Example private helper that formats a string."""
        prefix = self.valves.example_prefix
        return f"{prefix}:{value}"

    # -------------------------------------------------------------------
    # 4) Public tool methods
    # -------------------------------------------------------------------
    # These are the functions the agent calls from Open WebUI.
    # Each method should:
    #   - validate input
    #   - perform one focused action
    #   - return a plain dict or simple string
    #   - avoid surprising side effects
    def example_action(
        self,
        text: str,
        timeout: Optional[float] = None,
        flag: Optional[bool] = None,
    ):
        """
        Example public tool method.

        This is a good template for your own functions.

        :param text: Input string to process.
        :param timeout: Optional override for the configured timeout.
        :param flag: Optional override for the configured boolean flag.
        :return: A dictionary with machine-readable output.
        """
        if not text or not text.strip():
            return {"ok": False, "error": "Text input is required."}

        effective_timeout = self.valves.example_timeout if timeout is None else timeout
        effective_flag = self.valves.example_flag if flag is None else flag

        formatted = self._helper_example(text.strip())

        return {
            "ok": True,
            "input": text.strip(),
            "formatted_output": formatted,
            "timeout": effective_timeout,
            "flag": effective_flag,
            "message": "Example action completed successfully.",
        }

    # -------------------------------------------------------------------
    # 5) Add your own methods below
    # -------------------------------------------------------------------
    # Copy the pattern above for each new function you want the agent to call.
    # A few guidelines:
    #   - Keep each method focused on one capability.
    #   - Validate required arguments.
    #   - Return JSON-friendly structures.
    #   - Keep the docstring clear for the model.
    #
    # Example:
    #
    # def my_custom_check(self, host: str):
    #     if not host or not host.strip():
    #         return {"ok": False, "error": "Host is required."}
    #     return {"ok": True, "host": host.strip(), "status": "ready"}
    #
    # You can also add more valves for settings like timeouts, API endpoints, or
    # feature toggles. Add them in the Valves class above.

    def ping(self, target: str):
        """Simple placeholder method you can replace with your own logic."""
        if not target or not target.strip():
            return {"ok": False, "error": "Target is required."}

        return {
            "ok": True,
            "target": target.strip(),
            "message": "This is a placeholder. Replace with your real implementation.",
        }
