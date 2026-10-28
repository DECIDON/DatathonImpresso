"""Lecture des fichiers de séance (format `pages` ou manifeste IIIF) en une suite de blocs ordonnés."""

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

FILENAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<chamber>[a-z]+)_(?P<ark>\w+)$")

CHAMBER_NAMES = {
    "chambre": "Chambre des députés",
    "senat": "Sénat",
}


@dataclass
class Entity:
    uuid: str
    label: str
    start: int  # offset dans le HTML du bloc
    end: int
    text: str


@dataclass
class Block:
    uuid: str
    label: str
    html: str
    page: int
    entities: list[Entity] = field(default_factory=list)

    def entities_of(self, label: str) -> list[Entity]:
        return [e for e in self.entities if e.label == label]


@dataclass
class Session:
    path: Path
    name: str
    date: str
    chamber: str
    ark: str
    blocks: list[Block]

    @property
    def chamber_name(self) -> str:
        return CHAMBER_NAMES.get(self.chamber, self.chamber)


def parse_filename(path: Path) -> dict[str, str] | None:
    m = FILENAME_RE.match(path.stem)
    return m.groupdict() if m else None


def _iter_raw_pages(doc: dict):
    """Renvoie (blocs [(uuid, label, html)], entités) page par page, quel que soit le format."""
    if "pages" in doc:
        for page in doc["pages"]:
            blocks = [(b["uuid"], b["label"], b["content"]) for b in page.get("blocks", [])]
            yield blocks, page.get("entities", [])
    else:
        for canvas in doc.get("items", []):
            blocks = []
            for annotation_page in canvas.get("annotations", []):
                for item in annotation_page.get("items", []):
                    label, _, content = item["body"]["value"].partition(": ")
                    blocks.append((item["uuid"], label, content))
            yield blocks, canvas.get("entities", [])


def load_session(path: Path) -> Session:
    meta = parse_filename(path)
    if meta is None:
        raise ValueError(f"nom de fichier inattendu : {path.name}")
    doc = json.loads(path.read_text(encoding="utf-8"))

    blocks: list[Block] = []
    for page_idx, (raw_blocks, raw_entities) in enumerate(_iter_raw_pages(doc)):
        by_uuid: dict[str, Block] = {}
        for uuid, label, content in raw_blocks:
            block = Block(uuid=uuid, label=label, html=content, page=page_idx)
            by_uuid[uuid] = block
            blocks.append(block)
        for e in raw_entities:
            block = by_uuid.get(e["block"])
            if block is None:
                continue
            value = e["value"]
            for label in value["labels"]:
                block.entities.append(
                    Entity(e["uuid"], label, value["start"], value["end"], value["text"])
                )
        for block in by_uuid.values():
            block.entities.sort(key=lambda ent: ent.start)

    return Session(
        path=path,
        name=path.stem,
        date=meta["date"],
        chamber=meta["chamber"],
        ark=meta["ark"],
        blocks=blocks,
    )


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
