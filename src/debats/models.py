"""Modèle normalisé d'une séance : pages → blocs → entités, indépendant du format source."""

import datetime as dt
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel

from .text import html_to_text

CHAMBER_NAMES = {
    "chambre": "Chambre des députés",
    "senat": "Sénat",
}


class Entity(BaseModel):
    uuid: str  # répété si l'entité couvre deux blocs
    label: str  # SPK PER FCT ORG LOC COM TITL
    start: int  # offsets dans le HTML du bloc
    end: int
    text: str
    score: float | None = None


class Relation(BaseModel):
    from_uuid: str  # entité FCT
    to_uuid: str  # entité PER / SPK
    labels: list[str]


class Block(BaseModel):
    uuid: str
    label: str  # Text, Section-Header, Page-Header, Image…
    html: str
    page: int
    entities: list[Entity] = []

    def entities_of(self, label: str) -> list[Entity]:
        return [e for e in self.entities if e.label == label]

    @property
    def text(self) -> str:
        return html_to_text(self.html)


class Page(BaseModel):
    index: int
    blocks: list[Block]
    relations: list[Relation] = []


class Session(BaseModel):
    path: Path
    date: dt.date
    chamber: str  # « chambre » ou « senat »
    ark: str
    pages: list[Page]

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def chamber_name(self) -> str:
        return CHAMBER_NAMES.get(self.chamber, self.chamber)

    @cached_property
    def blocks(self) -> list[Block]:
        """Tous les blocs de la séance, dans l'ordre de lecture."""
        return [block for page in self.pages for block in page.blocks]

    def __repr_args__(self):
        # Affichage compact : les pages complètes sont illisibles dans un notebook.
        yield "name", self.name
        yield "pages", len(self.pages)
        yield "blocks", len(self.blocks)
