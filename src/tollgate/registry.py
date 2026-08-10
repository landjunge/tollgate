"""Minimal ToolSpec for optional registry registration (MCP / host apps)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: dict[str, Any] = field(default_factory=dict)
    plugin: str = "tollgate"
    retries: int = 0
    tags: tuple[str, ...] = ()


class ToolRegistry:
    """Tiny registry for hosts that don't use gnom ToolRegistry."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def mcp_manifest(self) -> dict[str, Any]:
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema or {"type": "object", "properties": {}},
                }
                for t in sorted(self._tools.values(), key=lambda x: x.name)
            ]
        }

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        spec = self._tools.get(name)
        if not spec:
            raise KeyError(name)
        return spec.handler(**(arguments or {}))
