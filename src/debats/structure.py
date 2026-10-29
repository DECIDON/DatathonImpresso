"""Repérage de la structure d'une séance : orateurs (`SPK`) et intertitres (`TITL`, `Section-Header`)."""

import re

from .models import Block, Entity
from .text import html_to_text

# Blocs hors du fil du texte : ils ne coupent rien et ne sont pas repris.
SKIPPED_LABELS = {"Page-Header", "Page-Footer", "Image", "Caption", "Footnote"}
SECTION_LABEL = "Section-Header"
# Une TITL dans un bloc Text n'est un intertitre que si elle couvre l'essentiel du bloc.
TITLE_MIN_COVERAGE = 0.5

# Civilité (et article) précédant le nom de l'orateur, balises <b> comprises.
HONORIFIC_RE = re.compile(
    r"(?:<b>\s*)?(?:MM?\.|Mmes?|Mlle)(?:\s|</?b>)*(?:(?:le|la)\s+|l['’]\s*)?(?:</?b>\s*)*$"
)
SENTENCE_END_RE = re.compile(r"[.!?)…]$")
PARAGRAPH_START_RE = re.compile(r"<(?:p|br|li|td)\b[^>]*>$", re.IGNORECASE)


def speaker_cut(block: Block, spk: Entity) -> int | None:
    """Offset HTML où commence la prise de parole introduite par `spk`, ou None si simple mention.

    Une `SPK` n'ouvre une prise de parole que si elle est précédée d'une civilité en début de
    paragraphe, ou après une fin de phrase (paragraphes fusionnés par l'OCR).
    """
    prefix = block.html[: spk.start]
    m = HONORIFIC_RE.search(prefix)
    if m is None:
        return None
    head = prefix[: m.start()].rstrip()
    if not head or PARAGRAPH_START_RE.search(head):
        return m.start()
    before = html_to_text(head).rsplit("\n", 1)[-1]
    if not SENTENCE_END_RE.search(before):
        return None
    return m.start()


def section_title(block: Block) -> str | None:
    """Intertitre porté par une entité `TITL`, ou None."""
    titles = block.entities_of("TITL")
    if not titles:
        return None
    title = " ".join(" ".join(t.text.split()) for t in titles)
    if block.label != SECTION_LABEL and len(title) < TITLE_MIN_COVERAGE * len(block.text):
        return None
    return title
