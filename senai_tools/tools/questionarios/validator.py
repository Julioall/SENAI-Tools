from __future__ import annotations

from typing import Any, Dict


class ValidationError(ValueError):
    """Erro de validacao de questionario."""


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_quiz(data: Dict[str, Any]) -> None:
    """Valida estrutura de quiz. Lanca ValidationError em caso de falha."""
    _ensure(isinstance(data, dict), "JSON raiz deve ser um objeto.")
    _ensure("title" in data and isinstance(data["title"], str) and data["title"].strip(), "Campo 'title' obrigatorio.")
    _ensure("questions" in data and isinstance(data["questions"], list) and data["questions"], "Campo 'questions' deve ser lista com itens.")

    for idx, q in enumerate(data["questions"]):
        prefix = f"Questao {idx + 1}: "
        _ensure(isinstance(q, dict), prefix + "cada questao deve ser um objeto.")
        stem = q.get("stem", "")
        _ensure(isinstance(stem, str) and stem.strip(), prefix + "campo 'stem' obrigatorio.")

        choices = q.get("choices")
        _ensure(isinstance(choices, list), prefix + "'choices' deve ser lista.")
        _ensure(len(choices) == 4, prefix + "'choices' deve ter exatamente 4 alternativas.")
        for choice in choices:
            _ensure(isinstance(choice, str) and choice.strip(), prefix + "todas as alternativas devem ser strings nao vazias.")

        answer_index = q.get("answer_index")
        _ensure(isinstance(answer_index, int), prefix + "'answer_index' deve ser inteiro.")
        _ensure(0 <= answer_index < 4, prefix + "'answer_index' deve estar entre 0 e 3.")

        fb_c = q.get("feedback_correct", "")
        fb_i = q.get("feedback_incorrect", "")
        _ensure(isinstance(fb_c, str), prefix + "'feedback_correct' deve ser string.")
        _ensure(isinstance(fb_i, str), prefix + "'feedback_incorrect' deve ser string.")


__all__ = ["validate_quiz", "ValidationError"]
