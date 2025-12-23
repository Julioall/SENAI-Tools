from __future__ import annotations

from senai_tools.app import ToolDefinition
from senai_tools.tools.notas import NotasConsolidadorFrame
from senai_tools.tools.questionarios import QuestionariosGiftFrame


def get_tools() -> list[ToolDefinition]:
    """Lista de ferramentas disponiveis no aplicativo."""
    return [
        ToolDefinition(
            id="consolidador_notas",
            name="Consolidador de Notas",
            description="Consolida relatorios de notas e aplica formatacao de desempenho.",
            frame_factory=NotasConsolidadorFrame,
        ),
        ToolDefinition(
            id="questionarios_gift",
            name="Gerador de Questionarios (GIFT)",
            description="Gera questionarios via API do GPT e exporta no formato Moodle GIFT.",
            frame_factory=QuestionariosGiftFrame,
        ),
    ]


__all__ = ["get_tools"]
