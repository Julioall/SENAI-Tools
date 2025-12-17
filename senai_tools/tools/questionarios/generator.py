from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import requests

from senai_tools.tools.questionarios import prompts


class GenerationError(RuntimeError):
    """Erro generico de geracao/parse do LLM."""


def _build_user_prompt(content: str, n: int, level: str, topic: str) -> str:
    return prompts.USER_TEMPLATE.format(content=content.strip(), n=n, level=level, topic=topic)


def _extract_json(text: str) -> Dict[str, Any]:
    """Extrai o primeiro objeto JSON de um texto possivelmente com ruido."""
    candidates: list[str] = []

    # Blocos cercados por ```json ... ```
    for fenced in re.findall(r"```json(.*?)```", text, re.DOTALL | re.IGNORECASE):
        candidates.append(fenced)

    # Varre todas as substrings balanceadas com { } e contem ':' (evita {name})
    stack: list[int] = []
    for idx, ch in enumerate(text):
        if ch == "{":
            stack.append(idx)
        elif ch == "}" and stack:
            start = stack.pop()
            if not stack:  # apenas quando fecha o primeiro nivel
                snippet = text[start : idx + 1]
                if ":" in snippet:
                    candidates.append(snippet)

    # Ordena por tamanho decrescente para tentar blocos mais completos primeiro
    unique_candidates: list[str] = []
    seen = set()
    for cand in sorted(candidates, key=len, reverse=True):
        key = cand.strip()
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(key)

    last_error: Exception | None = None
    last_candidate: str | None = None
    for raw in unique_candidates:
        cleaned = raw.strip()
        cleaned = cleaned.strip("`")
        try:
            return json.loads(cleaned)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            last_candidate = cleaned
            # fallback: alguns modelos retornam aspas simples -> tenta literal_eval
            try:
                obj = ast.literal_eval(cleaned)
                if isinstance(obj, dict):
                    return obj
            except Exception as exc2:  # noqa: BLE001
                last_error = exc2
                last_candidate = cleaned
                continue

    snippet = (last_candidate or text or "").strip().replace("\n", " ")
    snippet = snippet[:400]
    raise GenerationError(
        f"Nao foi possivel extrair JSON do retorno do modelo: {last_error or 'conteudo vazio'}. "
        f"Trecho da resposta: {snippet}"
    )


@dataclass
class GGUFGenerator:
    model_path: Path
    n_ctx: int = 4096
    n_threads: int | None = None

    def __post_init__(self) -> None:
        self.model_path = Path(self.model_path)

    def generate(self, content: str, n: int, level: str, topic: str) -> Dict[str, Any]:
        try:
            from llama_cpp import Llama
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"llama-cpp-python indisponivel: {exc}") from exc

        if not self.model_path.exists():
            raise GenerationError(f"Modelo GGUF nao encontrado: {self.model_path}")

        try:
            llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
            completion = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": prompts.SYSTEM},
                    {"role": "user", "content": _build_user_prompt(content, n, level, topic)},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
            text = completion["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"Falha na geracao com GGUF: {exc}") from exc

        return _extract_json(text)


@dataclass
class OllamaGenerator:
    host: str = "http://localhost:11434"
    model: str = "mistral:latest"

    def _host_url(self, path: str) -> str:
        base = self.host.rstrip("/")
        return f"{base}{path}"

    def generate(self, content: str, n: int, level: str, topic: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompts.SYSTEM},
                {"role": "user", "content": _build_user_prompt(content, n, level, topic)},
            ],
            "stream": False,
        }
        try:
            resp = requests.post(self._host_url("/api/chat"), json=payload, timeout=120)
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"Falha ao chamar Ollama: {exc}") from exc

        if resp.status_code >= 400:
            raise GenerationError(f"Ollama respondeu com status {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"Resposta Ollama nao e JSON: {exc}") from exc

        content_resp = (
            data.get("message", {}).get("content")
            or data.get("response")
            or "".join(chunk.get("content", "") for chunk in data.get("messages", []))
        )
        if not content_resp:
            raise GenerationError("Resposta Ollama vazia ou sem campo 'message.content'.")

        return _extract_json(content_resp)


__all__ = [
    "GGUFGenerator",
    "OllamaGenerator",
    "GenerationError",
]
