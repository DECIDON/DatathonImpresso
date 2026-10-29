"""Utilitaires texte sur le HTML produit par l'OCR (Chandra)."""

import html
import re

_BREAK_TAGS = re.compile(r"<br\s*/?>|</p>|</li>|</tr>|</h\d>", re.IGNORECASE)
_CELL_TAGS = re.compile(r"</t[dh]>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]*>")


def html_to_text(fragment: str) -> str:
    """Texte visible d'un fragment HTML : une ligne par paragraphe, espaces normalisés."""
    text = _BREAK_TAGS.sub("\n", fragment)
    text = _CELL_TAGS.sub(" ", text)
    text = html.unescape(_TAGS.sub("", text))
    lines = (" ".join(line.split()) for line in text.split("\n"))
    return "\n".join(line for line in lines if line)
