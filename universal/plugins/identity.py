"""Identity plugin: report who the agent is and list its capabilities.

Native on every agent. The canonical identity lives in ``universal/identity.py``;
this plugin only surfaces it as two tools.
"""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.identity import (
    IDENTITY_NAME,
    capabilities_text,
    identity_payload,
    identity_prompt_block,
)


class IdentityPlugin(Plugin):
    def __init__(self) -> None:
        self._name = "identity"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="show_identity",
                description="Return this agent's identity: the injected prompt block and the JSON payload.",
                parameters={"type": "object", "properties": {}},
            ),
            ToolSpec(
                name="list_capabilities",
                description="List this agent's capabilities as readable text.",
                parameters={"type": "object", "properties": {}},
            ),
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name == "show_identity":
            return json.dumps(
                {"prompt": identity_prompt_block(), "payload": identity_payload()},
                indent=2,
            )
        if call.name == "list_capabilities":
            return f"{IDENTITY_NAME} capabilities:\n{capabilities_text()}"
        return None
