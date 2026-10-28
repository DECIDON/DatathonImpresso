"""Découpage d'une séance en prises de parole (chunks).

Règles :
- une prise de parole commence à une entité SPK valide (« M. X. », « M. le président. »…)
  et court jusqu'à la SPK valide suivante ;
- un intertitre (bloc Section-Header ou bloc portant une entité TITL) clôt la prise de parole
  en cours : le texte qui suit sans nouvel orateur est ignoré ;
- la rubrique est la dernière entité TITL rencontrée ; les Section-Header sans TITL qui la
  suivent sont les sous-rubriques ;
- les en-têtes/pieds de page et images ne coupent rien et ne sont pas repris dans le texte.
"""

import re
from dataclasses import dataclass, field

from .reader import Block, Entity, Session, html_to_text

SKIPPED_LABELS = {"Page-Header", "Page-Footer", "Image", "Caption", "Footnote"}
SECTION_LABEL = "Section-Header"

# Civilité (et article) précédant le nom de l'orateur, balises <b> comprises.
_HONORIFIC_RE = re.compile(
    r"(?:<b>\s*)?(?:MM?\.|Mmes?|Mlle)(?:\s|</?b>)*(?:(?:le|la)\s+|l['’]\s*)?(?:</?b>\s*)*$"
)
# Une SPK en milieu de paragraphe n'est acceptée qu'après une fin de phrase
# (paragraphes fusionnés par l'OCR : « M. Leblanc. Non ! M. Borgeot. … »).
_SENTENCE_END_RE = re.compile(r"[.!?)…]$")
_PARAGRAPH_START_RE = re.compile(r"<(?:p|br|li|td)\b[^>]*>$", re.IGNORECASE)
# Une TITL dans un bloc Text n'est un intertitre que si elle couvre l'essentiel du bloc.
TITLE_MIN_COVERAGE = 0.5


@dataclass
class Turn:
    spk: Entity
    section: str | None
    subsections: list[str]
    blocks: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)

    def add(self, block: Block, fragment: str) -> None:
        text = html_to_text(fragment)
        if not text:
            return
        if block.uuid not in self.blocks:
            self.blocks.append(block.uuid)
        if self.parts and _continues(self.parts[-1]):
            # Paragraphe coupé entre deux blocs (changement de colonne ou de page).
            self.parts[-1] = f"{self.parts[-1]} {text}"
        else:
            self.parts.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.parts)


def _continues(text: str) -> bool:
    last = text[-1]
    return last.islower() or last in ",;"


def speaker_cut(block: Block, spk: Entity) -> int | None:
    """Offset HTML où commence la prise de parole introduite par `spk`, ou None si la SPK
    n'est qu'une mention (« … demande à M. le ministre », « 7250. — M. X »)."""
    prefix = block.html[: spk.start]
    m = _HONORIFIC_RE.search(prefix)
    if m is None:
        return None
    head = prefix[: m.start()].rstrip()
    if not head or _PARAGRAPH_START_RE.search(head):
        return m.start()
    before = html_to_text(head).rsplit("\n", 1)[-1]
    if not _SENTENCE_END_RE.search(before):
        return None
    return m.start()


def section_title(block: Block) -> str | None:
    titles = block.entities_of("TITL")
    if not titles:
        return None
    title = " ".join(" ".join(t.text.split()) for t in titles)
    if block.label != SECTION_LABEL:
        visible = html_to_text(block.html)
        if len(title) < TITLE_MIN_COVERAGE * len(visible):
            return None
    return title


@dataclass
class ChunkingStats:
    turns: int = 0
    rejected_spk: int = 0
    orphan_blocks: int = 0


def split_turns(session: Session) -> tuple[list[Turn], ChunkingStats]:
    turns: list[Turn] = []
    stats = ChunkingStats()
    section: str | None = None
    subsections: list[str] = []
    current: Turn | None = None

    def close() -> None:
        nonlocal current
        if current is not None and current.parts:
            turns.append(current)
        current = None

    for block in session.blocks:
        if block.label in SKIPPED_LABELS:
            continue

        title = section_title(block)
        if title is not None:
            close()
            section, subsections = title, []
            continue
        if block.label == SECTION_LABEL:
            close()
            subtitle = html_to_text(block.html).replace("\n", " ")
            if subtitle:
                subsections.append(subtitle)
            continue

        cuts: list[tuple[int, Entity]] = []
        for spk in block.entities_of("SPK"):
            cut = speaker_cut(block, spk)
            if cut is None:
                stats.rejected_spk += 1
            elif not cuts or cut > cuts[-1][0]:
                cuts.append((cut, spk))

        head_end = cuts[0][0] if cuts else len(block.html)
        if current is not None:
            current.add(block, block.html[:head_end])
        elif html_to_text(block.html[:head_end]):
            stats.orphan_blocks += 1

        for i, (cut, spk) in enumerate(cuts):
            close()
            end = cuts[i + 1][0] if i + 1 < len(cuts) else len(block.html)
            current = Turn(spk=spk, section=section, subsections=list(subsections))
            current.add(block, block.html[cut:end])

    close()
    stats.turns = len(turns)
    return turns, stats
