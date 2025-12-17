from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from senai_tools.tools.questionarios.exporter import to_gift
from senai_tools.tools.questionarios.generator import (
    GGUFGenerator,
    GenerationError,
    OllamaGenerator,
)
from senai_tools.tools.questionarios.validator import ValidationError, validate_quiz


class QuestionariosGiftFrame(ttk.Frame):
    """
    Aba de geracao de questionarios em formato GIFT.
    Usa threads para nao travar o Tkinter durante chamadas de LLM.
    """

    def __init__(self, master: tk.Misc):
        super().__init__(master, padding=10)

        self.topic_var = tk.StringVar()
        self.level_var = tk.StringVar(value="basico")
        self.num_questions_var = tk.IntVar(value=5)
        self.backend_var = tk.StringVar(value="GGUF")

        self.gguf_path_var = tk.StringVar()
        self.n_ctx_var = tk.StringVar(value="4096")
        self.n_threads_var = tk.StringVar()

        self.ollama_host_var = tk.StringVar(value="http://localhost:11434")
        self.ollama_model_var = tk.StringVar(value="mistral:latest")

        self.progress_var = tk.DoubleVar(value=0)
        self.queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.current_json: dict | None = None
        self.current_gift: str | None = None
        self._action_buttons: list[ttk.Widget] = []

        self._build_layout()

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        # Linha 1: campos gerais
        top_frame = ttk.Frame(container)
        top_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(top_frame, text="Tema:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(top_frame, textvariable=self.topic_var, width=30).grid(row=0, column=1, sticky="we")

        ttk.Label(top_frame, text="Nivel:").grid(row=0, column=2, sticky="e", padx=(10, 5))
        level_cb = ttk.Combobox(top_frame, textvariable=self.level_var, values=["basico", "intermediario", "avancado"])
        level_cb.state(["readonly"])
        level_cb.grid(row=0, column=3, sticky="we")

        ttk.Label(top_frame, text="N de questoes:").grid(row=0, column=4, sticky="e", padx=(10, 5))
        ttk.Spinbox(top_frame, textvariable=self.num_questions_var, from_=1, to=50, width=5).grid(
            row=0, column=5, sticky="w"
        )

        # Backend
        ttk.Label(top_frame, text="Backend:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        backend_cb = ttk.Combobox(top_frame, textvariable=self.backend_var, values=["GGUF", "Ollama"])
        backend_cb.state(["readonly"])
        backend_cb.grid(row=1, column=1, sticky="we", pady=(5, 0))
        backend_cb.bind("<<ComboboxSelected>>", lambda _: self._toggle_backend_frames())

        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(3, weight=1)

        # Backend configs
        self.backend_frames = {}
        self.backend_frames["GGUF"] = self._build_gguf_frame(container)
        self.backend_frames["Ollama"] = self._build_ollama_frame(container)
        self._toggle_backend_frames()

        # Conteudo base + botoes
        content_frame = ttk.LabelFrame(container, text="Conteudo base")
        content_frame.pack(fill="both", expand=True, pady=(8, 8))

        self.content_text = tk.Text(content_frame, height=10, wrap="word")
        self.content_text.pack(fill="both", expand=True, side="left", padx=(5, 0), pady=5)
        content_scroll = ttk.Scrollbar(content_frame, orient="vertical", command=self.content_text.yview)
        content_scroll.pack(fill="y", side="right", pady=5)
        self.content_text.configure(yscrollcommand=content_scroll.set)

        btns_frame = ttk.Frame(container)
        btns_frame.pack(fill="x", pady=(0, 8))

        for text, cmd in [
            ("Carregar arquivo", self._on_load_file),
            ("Gerar", self._on_generate),
            ("Validar", self._on_validate),
            ("Exportar .gift", self._on_export_gift),
            ("Salvar JSON", self._on_save_json),
        ]:
            btn = ttk.Button(btns_frame, text=text, command=cmd)
            btn.pack(side="left", padx=5 if text != "Carregar arquivo" else 0)
            self._action_buttons.append(btn)

        # Progresso + log
        prog_log_frame = ttk.Frame(container)
        prog_log_frame.pack(fill="x", pady=(0, 5))
        self.progressbar = ttk.Progressbar(prog_log_frame, variable=self.progress_var, maximum=100, mode="indeterminate")
        self.progressbar.pack(fill="x", expand=True, side="left", padx=(0, 8))
        ttk.Button(prog_log_frame, text="Limpar log", command=self._clear_log).pack(side="right")

        log_frame = ttk.LabelFrame(container, text="Log")
        log_frame.pack(fill="both", expand=False, pady=(0, 8))
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word", bg="#ffffff", relief="solid", bd=1)
        self.log_text.pack(fill="both", expand=True, side="left", padx=(5, 0), pady=5)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(fill="y", side="right", pady=5)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # Preview
        preview_frame = ttk.LabelFrame(container, text="Preview .gift")
        preview_frame.pack(fill="both", expand=True)
        self.preview_text = tk.Text(preview_frame, height=10, state="disabled", wrap="word", bg="#f9f9f9")
        self.preview_text.pack(fill="both", expand=True, side="left", padx=(5, 0), pady=5)
        prev_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        prev_scroll.pack(fill="y", side="right", pady=5)
        self.preview_text.configure(yscrollcommand=prev_scroll.set)

    def _build_gguf_frame(self, parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.LabelFrame(parent, text="Config. GGUF (llama-cpp-python)")

        ttk.Label(frame, text="Modelo (.gguf):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.gguf_path_var).grid(row=0, column=1, sticky="we", padx=5, pady=2)
        ttk.Button(frame, text="Selecionar", command=self._on_select_gguf).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(frame, text="n_ctx:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.n_ctx_var, width=8).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(frame, text="n_threads:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.n_threads_var, width=8).grid(row=1, column=3, sticky="w", padx=5, pady=2)

        frame.columnconfigure(1, weight=1)
        return frame

    def _build_ollama_frame(self, parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.LabelFrame(parent, text="Config. Ollama (HTTP)")

        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.ollama_host_var).grid(row=0, column=1, sticky="we", padx=5, pady=2)

        ttk.Label(frame, text="Model:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.ollama_model_var).grid(row=1, column=1, sticky="we", padx=5, pady=2)

        frame.columnconfigure(1, weight=1)
        return frame

    def _toggle_backend_frames(self) -> None:
        chosen = self.backend_var.get()
        for name, frame in self.backend_frames.items():
            if chosen == name:
                frame.pack(fill="x", pady=(8, 0))
            else:
                frame.pack_forget()

    # ------------------------------------------------------------------ util
    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _set_preview(self, text: str) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("end", text)
        self.preview_text.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        state = "disabled" if running else "!disabled"
        for btn in self._action_buttons:
            try:
                btn.state([state])  # type: ignore[arg-type]
            except Exception:
                pass
        if running:
            self.progressbar.start(10)
        else:
            self.progressbar.stop()

    # ------------------------------------------------------------------ handlers
    def _on_load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione um arquivo de texto",
            filetypes=[("Text/Markdown", "*.txt *.md"), ("Todos", "*.*")],
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            self.content_text.delete("1.0", "end")
            self.content_text.insert("end", text)
            self._append_log(f"Conteudo carregado de {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro", f"Nao foi possivel ler o arquivo:\n{exc}", parent=self)

    def _on_select_gguf(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione o modelo GGUF",
            filetypes=[("GGUF", "*.gguf"), ("Todos", "*.*")],
        )
        if path:
            self.gguf_path_var.set(path)

    def _on_generate(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Aguarde", "Uma geracao ja esta em andamento.", parent=self)
            return

        content = self.content_text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Campo obrigatorio", "Preencha o conteudo base.", parent=self)
            return

        topic = self.topic_var.get().strip() or "Questionario"
        level = self.level_var.get().strip() or "basico"
        try:
            n = int(self.num_questions_var.get())
            if n <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Campo obrigatorio", "N de questoes invalido.", parent=self)
            return

        backend = self.backend_var.get()
        if backend == "GGUF" and not self.gguf_path_var.get().strip():
            messagebox.showwarning("Campo obrigatorio", "Selecione um modelo GGUF.", parent=self)
            return
        if backend == "Ollama" and not self.ollama_host_var.get().strip():
            messagebox.showwarning("Campo obrigatorio", "Informe o host do Ollama.", parent=self)
            return

        params = {
            "content": content,
            "topic": topic,
            "level": level,
            "n": n,
            "backend": backend,
        }
        self._append_log("Iniciando geracao...")
        self._set_running(True)

        self.worker = threading.Thread(target=self._worker_generate, args=(params,), daemon=True)
        self.worker.start()
        self.after(100, self._poll_queue)

    def _build_generator(self, backend: str):
        if backend == "GGUF":
            n_ctx = int(self.n_ctx_var.get() or 4096)
            n_threads = int(self.n_threads_var.get()) if self.n_threads_var.get().strip() else None
            return GGUFGenerator(Path(self.gguf_path_var.get()), n_ctx=n_ctx, n_threads=n_threads)

        host = self.ollama_host_var.get().strip() or "http://localhost:11434"
        model = self.ollama_model_var.get().strip() or "mistral:latest"
        return OllamaGenerator(host=host, model=model)

    def _worker_generate(self, params: dict) -> None:
        try:
            generator = self._build_generator(params["backend"])
            data = generator.generate(
                content=params["content"],
                n=params["n"],
                level=params["level"],
                topic=params["topic"],
            )
            self.queue.put(("log", "JSON gerado. Validando..."))
            validate_quiz(data)
            gift_text = to_gift(data)
            self.queue.put(("result", data, gift_text))
            self.queue.put(("log", "Validacao ok. Preview gerado."))
        except (GenerationError, ValidationError) as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001
            self.queue.put(("error", f"Erro inesperado: {exc}"))
        finally:
            self.queue.put(("done", None))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload, *rest = self.queue.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "error":
                    self._append_log(str(payload))
                    messagebox.showerror("Erro", str(payload), parent=self)
                elif kind == "result":
                    json_data = payload
                    gift_text = rest[0] if rest else ""
                    self.current_json = json_data
                    self.current_gift = gift_text
                    self._set_preview(gift_text)
                elif kind == "done":
                    self._set_running(False)
        except queue.Empty:
            pass

        if self.worker and self.worker.is_alive():
            self.after(150, self._poll_queue)

    def _on_validate(self) -> None:
        if not self.current_json:
            messagebox.showinfo("Info", "Nenhum JSON carregado. Gere primeiro.", parent=self)
            return
        try:
            validate_quiz(self.current_json)
            gift_text = to_gift(self.current_json)
            self.current_gift = gift_text
            self._set_preview(gift_text)
            self._append_log("Validacao concluida e preview atualizado.")
        except ValidationError as exc:
            messagebox.showerror("Erro de validacao", str(exc), parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro", f"Nao foi possivel validar/exportar: {exc}", parent=self)

    def _on_export_gift(self) -> None:
        if not self.current_json:
            messagebox.showwarning("Aviso", "Nenhum questionario para exportar. Gere primeiro.", parent=self)
            return
        try:
            gift_text = self.current_gift or to_gift(self.current_json)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro", f"Falha ao gerar GIFT: {exc}", parent=self)
            return

        path = filedialog.asksaveasfilename(
            title="Salvar GIFT",
            defaultextension=".gift.txt",
            filetypes=[("GIFT", "*.gift.txt *.gift"), ("Texto", "*.txt"), ("Todos", "*.*")],
            initialfile="questionarios.gift.txt",
        )
        if not path:
            return
        try:
            Path(path).write_text(gift_text, encoding="utf-8")
            self._append_log(f"GIFT salvo em {path}")
            messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{path}", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro", f"Nao foi possivel salvar:\n{exc}", parent=self)

    def _on_save_json(self) -> None:
        if not self.current_json:
            messagebox.showwarning("Aviso", "Nenhum JSON para salvar. Gere primeiro.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Salvar JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
            initialfile="questionarios.json",
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.current_json, ensure_ascii=False, indent=2), encoding="utf-8")
            self._append_log(f"JSON salvo em {path}")
            messagebox.showinfo("Sucesso", f"JSON salvo em:\n{path}", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro", f"Nao foi possivel salvar o JSON:\n{exc}", parent=self)


__all__ = ["QuestionariosGiftFrame"]
