from __future__ import annotations

from senai_tools.app import ToolDefinition
from senai_tools.tools.notas import NotasConsolidadorFrame


def get_tools() -> list[ToolDefinition]:
    """Lista de ferramentas disponíveis no aplicativo."""
    return [
        ToolDefinition(
            id="consolidador_notas",
            name="Consolidador de Notas",
            description="Consolida relatórios de notas e aplica formatação de desempenho.",
            frame_factory=NotasConsolidadorFrame,
        )
    ]


__all__ = ["get_tools"]
