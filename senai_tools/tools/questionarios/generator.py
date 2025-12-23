from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Dict

from openai import OpenAI

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
class OpenAIGenerator:
    api_key: str
    model: str = "gpt-4o-mini"

    def generate(self, content: str, n: int, level: str, topic: str) -> Dict[str, Any]:
        api_key = self.api_key.strip()
        if not api_key:
            raise GenerationError("Chave da API do GPT nao informada.")

        client = OpenAI(api_key=api_key)
        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompts.SYSTEM},
                    {"role": "user", "content": _build_user_prompt(content, n, level, topic)},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"Falha na chamada da API do GPT: {exc}") from exc

        text = ""
        try:
            text = completion.choices[0].message.content or ""
        except Exception:
            pass

        if not text.strip():
            raise GenerationError("Resposta da API do GPT vazia.")

        return _extract_json(text)


__all__ = [
    "OpenAIGenerator",
    "GenerationError",
]
