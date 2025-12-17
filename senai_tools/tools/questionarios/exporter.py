from __future__ import annotations

from typing import Any, Dict, List

from gift_wrapper import gift as gift_utils

from senai_tools.tools.questionarios.validator import validate_quiz


ESCAPE_MAP = {
    "{": r"\{",
    "}": r"\}",
    "=": r"\=",
    "~": r"\~",
    "#": r"\#",
}


def _clean_text(text: str) -> str:
    """Escapa caracteres criticos e converte quebras de linha para <br>."""
    safe = text.replace("\r", "").strip()
    for src, dst in ESCAPE_MAP.items():
        safe = safe.replace(src, dst)
    safe = gift_utils.process_new_lines(safe)
    return safe


def _build_answers(choices: List[str], answer_index: int, fb_correct: str, fb_incorrect: str) -> List[str]:
    answers: List[str] = []
    for idx, choice in enumerate(choices):
        text = _clean_text(choice)
        if idx == answer_index:
            ans = gift_utils.from_perfect_answer(text)
            if fb_correct:
                ans += f" #{_clean_text(fb_correct)}"
        else:
            ans = gift_utils.from_wrong_answer(text)
            if fb_incorrect:
                ans += f" #{_clean_text(fb_incorrect)}"
        answers.append(ans)
    return answers


def to_gift(data: Dict[str, Any]) -> str:
    """
    Converte JSON validado em texto GIFT.
    Usa gift_wrapper (dependencia do py2gift) para montar sintaxe.
    """
    validate_quiz(data)

    title = data.get("title", "Questionario")
    lines = [gift_utils.from_category(title)]

    for idx, q in enumerate(data["questions"]):
        name = f"{title} Q{idx + 1}"
        stem = _clean_text(q.get("stem", ""))
        fb_c = q.get("feedback_correct", "") or ""
        fb_i = q.get("feedback_incorrect", "") or ""

        answers = _build_answers(q["choices"], q["answer_index"], fb_c, fb_i)

        block = f"{gift_utils.from_question_name(name)}{stem} {{\n  " + "\n  ".join(answers) + "\n}"
        lines.append(block)

    return "\n\n".join(lines)


__all__ = ["to_gift"]
