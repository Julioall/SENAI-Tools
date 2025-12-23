from __future__ import annotations

from senai_tools.app import ToolDefinition
from senai_tools.tools.notas import NotasConsolidadorFrame


def get_tools() -> list[ToolDefinition]:
    """Lista de ferramentas disponiveis no aplicativo."""
    return [
        ToolDefinition(
            id="consolidador_notas",
            name="Consolidador de Notas",
            description="Consolida relatorios de notas e aplica formatacao de desempenho.",
            frame_factory=NotasConsolidadorFrame,
        ),
    ]


__all__ = ["get_tools"]
