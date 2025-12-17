from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Callable

from senai_tools import __app_name__


@dataclass(frozen=True)
class ToolDefinition:
    """Metadados mínimos para registrar uma ferramenta na aplicação."""

    id: str
    name: str
    description: str
    frame_factory: Callable[[tk.Misc], tk.Widget]


class SENAIToolsApp(tk.Tk):
    def __init__(self, tools: list[ToolDefinition], icon_path: Path | str | None = None):
        super().__init__()
        self.title(__app_name__)
        self.geometry("900x600")
        self.minsize(780, 520)

        self._tools = tools
        self._configure_style()
        self._set_icon(icon_path)
        self._montar_shell()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg = "#f5f5f5"
        self.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("Tool.TFrame", background=bg)
        style.configure("TLabel", background=bg, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=bg, font=("Segoe UI", 13, "bold"))
        style.configure("SubTitle.TLabel", background=bg, font=("Segoe UI", 9, "italic"))
        style.configure("TButton", padding=6, font=("Segoe UI", 9))
        style.configure("TEntry", padding=3)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", padding=(12, 6))

    def _set_icon(self, icon_path: Path | str | None) -> None:
        if not icon_path:
            return
        path = Path(icon_path)
        if not path.exists():
            return
        try:
            self.iconbitmap(str(path))
        except Exception:
            # Silenciosamente ignora falha de ícone para não quebrar o app.
            pass

    def _montar_shell(self) -> None:
        wrapper = ttk.Frame(self, padding=(10, 10, 10, 0))
        wrapper.pack(fill="both", expand=True)

        header = ttk.Frame(wrapper)
        header.pack(fill="x")
        ttk.Label(header, text=__app_name__, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Coleção de utilitários para acelerar o trabalho do SENAI.",
            style="SubTitle.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self.desc_label = ttk.Label(
            wrapper,
            text=self._tools[0].description if self._tools else "Nenhuma ferramenta disponível.",
            style="SubTitle.TLabel",
        )
        self.desc_label.pack(fill="x", anchor="w")

        self.notebook = ttk.Notebook(wrapper)
        self.notebook.pack(fill="both", expand=True, pady=(5, 10))

        if not self._tools:
            vazio = ttk.Frame(self.notebook)
            ttk.Label(vazio, text="Nenhuma ferramenta cadastrada.", style="SubTitle.TLabel").pack(
                expand=True, pady=40
            )
            self.notebook.add(vazio, text="Sem ferramentas")
            return

        for tool in self._tools:
            frame = tool.frame_factory(self.notebook)
            frame.configure(style="Tool.TFrame")
            self.notebook.add(frame, text=tool.name)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        self._atualizar_descricao()

    def _on_tab_change(self, event) -> None:
        self._atualizar_descricao()

    def _atualizar_descricao(self) -> None:
        try:
            idx = self.notebook.index("current")
            tool = self._tools[idx]
            self.desc_label.config(text=tool.description)
        except Exception:
            self.desc_label.config(text="")


def run_app(tools: list[ToolDefinition], icon_path: Path | str | None = None) -> None:
    """Instancia o Tk e executa o loop principal."""
    app = SENAIToolsApp(tools, icon_path=icon_path)
    app.mainloop()
