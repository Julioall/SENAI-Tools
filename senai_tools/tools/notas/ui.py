from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .processor import processar_arquivos


class NotasConsolidadorFrame(ttk.Frame):
    """
    Ferramenta de consolidação de notas.
    Estruturada como Frame para ser encaixada no container principal do app.
    """

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.configure(padding=10)

        self.arquivos_selecionados: list[str] = []
        self.resumo_arquivos = tk.StringVar(value="Nenhum arquivo selecionado.")
        self.nome_arquivo_saida = tk.StringVar(value="notas_consolidadas.xlsx")
        self.btn_processar = None

        self._montar_layout()

    def _montar_layout(self) -> None:
        padding_geral = {"padx": 10, "pady": 5}

        container = ttk.Frame(self)
        container.pack(fill="both", expand=False)

        # Cabeçalho
        header = ttk.Frame(container)
        header.grid(row=0, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 5))

        ttk.Label(header, text="Consolidador de Notas", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Selecione relatórios e gere o consolidado com notas e pendências.",
            style="SubTitle.TLabel",
        ).pack(anchor="w", pady=(0, 5))

        ttk.Separator(container, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky="we", pady=(5, 15)
        )

        # Seleção de arquivos
        ttk.Label(container, text="Arquivos:").grid(
            row=2, column=0, sticky="w", **padding_geral
        )

        frame_arquivos = ttk.Frame(container)
        frame_arquivos.grid(row=3, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 15))

        entry_arquivos = ttk.Entry(
            frame_arquivos, textvariable=self.resumo_arquivos, width=50, state="readonly"
        )
        entry_arquivos.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(frame_arquivos, text="Selecionar", command=self.selecionar_arquivos).pack(side="left")

        # Nome arquivo saída
        ttk.Label(container, text="Saída:").grid(
            row=4, column=0, sticky="w", **padding_geral
        )

        frame_saida = ttk.Frame(container)
        frame_saida.grid(row=5, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 20))

        ttk.Entry(frame_saida, textvariable=self.nome_arquivo_saida, width=50).pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Botão Processar (verde quando houver arquivos)
        self.btn_processar = tk.Button(
            container, text="▶ Processar", command=self.on_processar,
            font=("Segoe UI", 10, "bold"), padx=20, pady=8, cursor="hand2",
            relief="raised", bd=2
        )
        self.btn_processar.grid(row=6, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 15))
        self._atualizar_cor_botao()

        ttk.Separator(container, orient="horizontal").grid(
            row=7, column=0, columnspan=2, sticky="we", pady=(5, 10)
        )

        self.lbl_status = ttk.Label(container, text="Pronto.", anchor="w", style="SubTitle.TLabel")
        self.lbl_status.grid(row=8, column=0, columnspan=2, sticky="we", padx=10, pady=5)

        container.columnconfigure(0, weight=1)

    def selecionar_arquivos(self) -> None:
        caminhos = filedialog.askopenfilenames(
            title="Selecione os relatórios",
            filetypes=[
                ("Planilhas Excel/ODS", "*.xlsx *.xls *.ods"),
                ("Excel (.xlsx)", "*.xlsx"),
                ("ODS (.ods)", "*.ods"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if caminhos:
            self.arquivos_selecionados = list(caminhos)
            qtd = len(self.arquivos_selecionados)
            resumo = Path(self.arquivos_selecionados[0]).name if qtd == 1 else f"{qtd} arquivos selecionados."
            self.resumo_arquivos.set(resumo)
            self._set_status("Arquivos selecionados.")
            self._atualizar_cor_botao()

    def _set_status(self, msg: str) -> None:
        self.lbl_status.config(text=msg)
        self.update_idletasks()

    def _atualizar_cor_botao(self) -> None:
        if self.btn_processar:
            if self.arquivos_selecionados:
                self.btn_processar.configure(bg="#27ae60", fg="white", activebackground="#229954", activeforeground="white")
            else:
                self.btn_processar.configure(bg="#cccccc", fg="#666666", activebackground="#bbbbbb", activeforeground="#666666")

    def _validar_nome_saida(self, nome_saida: str) -> str:
        nome_saida = nome_saida.strip()
        if not nome_saida:
            raise ValueError("Informe o nome do arquivo de saída.")

        # impede uso de caminhos/pastas no campo do nome
        if Path(nome_saida).name != nome_saida:
            raise ValueError("Não use caminhos ou pastas no nome do arquivo de saída.")

        if not nome_saida.lower().endswith(".xlsx"):
            raise ValueError("Extensão inválida. Use apenas .xlsx.")

        base = nome_saida[:-5]  # remove .xlsx
        caracteres_invalidos = r'\\/:*?"<>|'
        if any(ch in base for ch in caracteres_invalidos):
            raise ValueError("O nome do arquivo não pode conter \\ / : * ? \" < > |")

        if len(base) == 0:
            raise ValueError("Informe um nome válido antes da extensão .xlsx.")

        return nome_saida

    def on_processar(self) -> None:
        if not self.arquivos_selecionados:
            messagebox.showwarning("Validação", "Selecione pelo menos um arquivo de relatório.", parent=self)
            return

        try:
            nome_saida = self._validar_nome_saida(self.nome_arquivo_saida.get())
        except ValueError as e:
            messagebox.showwarning("Validação", str(e), parent=self)
            return

        pasta_base = Path(self.arquivos_selecionados[0]).parent
        caminho_saida = pasta_base / nome_saida

        try:
            self._set_status("Processando relatórios...")
            
            # Auto-detectar: múltiplos arquivos = dividir por turma
            dividir_por_uc = len(self.arquivos_selecionados) > 1
            
            processar_arquivos(
                self.arquivos_selecionados,
                str(caminho_saida),
                dividir_por_uc=dividir_por_uc,
            )
            self._set_status("Processamento concluído.")
            messagebox.showinfo("Sucesso", f"Arquivo gerado:\n{caminho_saida}", parent=self)
        except Exception as e:
            self._set_status("Erro no processamento.")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{e}", parent=self)
