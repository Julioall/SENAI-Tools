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
        self.dividir_por_uc = tk.BooleanVar(value=True)
        self.manter_nome_original = tk.BooleanVar(value=True)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_total = 0
        self.logs: list[str] = []

        self._montar_layout()

    def _montar_layout(self) -> None:
        padding_geral = {"padx": 10, "pady": 5}

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        # Cabeçalho
        header = ttk.Frame(container)
        header.grid(row=0, column=0, columnspan=3, sticky="we")

        ttk.Label(header, text="Consolidador de Notas", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Gera planilha consolidada por UC com formatação visual de desempenho.",
            style="SubTitle.TLabel",
        ).pack(anchor="w", pady=(0, 5))

        ttk.Separator(container, orient="horizontal").grid(
            row=1, column=0, columnspan=3, sticky="we", pady=(5, 10)
        )

        # Seleção de arquivos
        ttk.Label(container, text="Arquivos de relatórios (.xlsx / .ods):").grid(
            row=2, column=0, sticky="w", **padding_geral
        )

        entry_arquivos = ttk.Entry(
            container, textvariable=self.resumo_arquivos, width=60, state="readonly"
        )
        entry_arquivos.grid(row=3, column=0, sticky="we", **padding_geral)

        ttk.Button(container, text="Selecionar arquivos", command=self.selecionar_arquivos).grid(
            row=3, column=1, sticky="we", **padding_geral
        )

        # Opções
        ttk.Checkbutton(
            container,
            text="Gerar uma aba por UC (desmarque para planilha única)",
            variable=self.dividir_por_uc,
        ).grid(row=4, column=0, columnspan=2, sticky="w", **padding_geral)

        ttk.Checkbutton(
            container,
            text="Usar nome original do arquivo para nome da aba (quando dividir por UC)",
            variable=self.manter_nome_original,
        ).grid(row=5, column=0, columnspan=2, sticky="w", **padding_geral)

        # Nome arquivo saída
        ttk.Label(container, text="Nome do arquivo de saída (.xlsx):").grid(
            row=6, column=0, sticky="w", **padding_geral
        )

        ttk.Entry(container, textvariable=self.nome_arquivo_saida, width=60).grid(
            row=7, column=0, sticky="we", **padding_geral
        )

        ttk.Button(container, text="Processar relatórios", command=self.on_processar).grid(
            row=7, column=1, sticky="we", **padding_geral
        )

        # Log
        ttk.Label(container, text="Log de execução:").grid(
            row=8, column=0, sticky="w", **padding_geral
        )
        ttk.Button(container, text="Exportar log", command=self.exportar_log).grid(
            row=8, column=1, sticky="e", padx=(0, 10), pady=5
        )

        self.txt_log = tk.Text(container, height=10, state="disabled", bg="#ffffff", relief="solid", bd=1)
        self.txt_log.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.txt_log.yview)
        scrollbar.grid(row=9, column=2, sticky="ns", pady=(0, 10))
        self.txt_log["yscrollcommand"] = scrollbar.set

        # Progresso
        frame_progress = ttk.Frame(container)
        frame_progress.grid(row=10, column=0, columnspan=3, sticky="we", padx=10, pady=(0, 5))
        ttk.Label(frame_progress, text="Progresso:").pack(side="left")
        self.lbl_prog_contador = ttk.Label(frame_progress, text="0/0")
        self.lbl_prog_contador.pack(side="right")
        self.progressbar = ttk.Progressbar(frame_progress, variable=self.progress_var, maximum=100)
        self.progressbar.pack(fill="x", expand=True, padx=(5, 5))

        self.lbl_status = ttk.Label(container, text="Pronto.", anchor="w")
        self.lbl_status.grid(row=11, column=0, columnspan=3, sticky="we", padx=10, pady=(0, 5))

        container.rowconfigure(9, weight=1)
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

    def log(self, mensagem: str) -> None:
        self.logs.append(mensagem)
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", mensagem + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")
        self.update_idletasks()

    def _set_status(self, msg: str) -> None:
        self.lbl_status.config(text=msg)
        self.update_idletasks()

    def _reset_progress(self, total: int) -> None:
        self.progress_total = max(total, 0)
        self.progress_var.set(0)
        self.lbl_prog_contador.config(text=f"0/{total}")
        self.update_idletasks()

    def _atualizar_progresso(self, atual: int, total: int) -> None:
        total = max(total, 1)
        porcentagem = (atual / total) * 100
        self.progress_var.set(porcentagem)
        self.lbl_prog_contador.config(text=f"{atual}/{total}")
        self.update_idletasks()

    def exportar_log(self) -> None:
        if not self.logs:
            messagebox.showinfo("Log", "Nenhum log para exportar.", parent=self)
            return

        caminho = filedialog.asksaveasfilename(
            title="Salvar log",
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt"), ("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
            initialfile="log_processamento.txt",
        )
        if not caminho:
            return

        try:
            Path(caminho).write_text("\n".join(self.logs), encoding="utf-8")
            messagebox.showinfo("Log", f"Log salvo em:\n{caminho}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o log:\n{e}", parent=self)

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
            # limpa log anterior e reseta progresso
            self.logs.clear()
            self.txt_log.configure(state="normal")
            self.txt_log.delete("1.0", "end")
            self.txt_log.configure(state="disabled")

            total = len(self.arquivos_selecionados)
            self._reset_progress(total)

            self.log("Iniciando processamento...")
            self._set_status("Processando relatórios...")
            processar_arquivos(
                self.arquivos_selecionados,
                str(caminho_saida),
                dividir_por_uc=self.dividir_por_uc.get(),
                manter_nome_original=self.manter_nome_original.get(),
                log_callback=self.log,
                progress_callback=self._atualizar_progresso,
            )
            self.log("Processamento concluído com sucesso.")
            self._set_status("Processamento concluído.")
            messagebox.showinfo("Sucesso", f"Arquivo gerado:\n{caminho_saida}", parent=self)
        except Exception as e:
            self.log(f"Erro: {e}")
            self._set_status("Erro no processamento.")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{e}", parent=self)
