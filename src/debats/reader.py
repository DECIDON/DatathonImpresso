"""Lecture des fichiers de séance `<date>_<chambre>_<ark>.json`.

Deux formats coexistent dans data/ (cf. data/README.md) :
- `pages` : {"pages": [{"blocks": [...], "entities": [...], "relations": [...]}]}
- manifeste IIIF v3 : {"items": [canvas]} avec les blocs dans canvas.annotations[].items[]
  (body.value = "<Label>: <html>").

Seuls les champs utiles sont modélisés ; le reste est ignoré.
"""

import re
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

from .models import Block, Entity, Page, Relation, Session

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"

FILENAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<chamber>[a-z]+)_(?P<ark>\w+)$")


# --- Formats sources -------------------------------------------------------------------


class RawEntityValue(BaseModel):
    start: int
    end: int
    text: str
    labels: list[str]


class RawEntity(BaseModel):
    block: str
    uuid: str
    value: RawEntityValue
    score: float | None = None


class RawRelation(BaseModel):
    from_uuid: str
    to_uuid: str
    labels: list[str]


class RawBlock(BaseModel):
    uuid: str
    label: str
    content: str


class RawPage(BaseModel):
    blocks: list[RawBlock] = []
    entities: list[RawEntity] = []
    relations: list[RawRelation] = []


class PagesDocument(BaseModel):
    pages: list[RawPage]


class IIIFBody(BaseModel):
    value: str


class IIIFAnnotation(BaseModel):
    uuid: str
    body: IIIFBody


class IIIFAnnotationPage(BaseModel):
    items: list[IIIFAnnotation] = []


class IIIFCanvas(BaseModel):
    annotations: list[IIIFAnnotationPage] = []
    entities: list[RawEntity] = []
    relations: list[RawRelation] = []

    def to_raw_page(self) -> RawPage:
        blocks = []
        for annotation_page in self.annotations:
            for item in annotation_page.items:
                label, _, content = item.body.value.partition(": ")
                blocks.append(RawBlock(uuid=item.uuid, label=label, content=content))
        return RawPage(blocks=blocks, entities=self.entities, relations=self.relations)


class IIIFManifest(BaseModel):
    items: list[IIIFCanvas]


# --- Normalisation ---------------------------------------------------------------------


def _normalize_page(index: int, raw: RawPage) -> Page:
    blocks = [Block(uuid=b.uuid, label=b.label, html=b.content, page=index) for b in raw.blocks]
    by_uuid = {b.uuid: b for b in blocks}
    for e in raw.entities:
        block = by_uuid.get(e.block)
        if block is None:
            continue
        # Une entité multi-étiquette donne une Entity par étiquette.
        for label in e.value.labels:
            block.entities.append(
                Entity(
                    uuid=e.uuid,
                    label=label,
                    start=e.value.start,
                    end=e.value.end,
                    text=e.value.text,
                    score=e.score,
                )
            )
    for block in blocks:
        block.entities.sort(key=lambda ent: ent.start)
    relations = [Relation(**r.model_dump()) for r in raw.relations]
    return Page(index=index, blocks=blocks, relations=relations)


def parse_filename(path: Path) -> dict[str, str] | None:
    m = FILENAME_RE.match(Path(path).stem)
    return m.groupdict() if m else None


def load_session(path: Path | str) -> Session:
    path = Path(path)
    meta = parse_filename(path)
    if meta is None:
        raise ValueError(f"nom de fichier inattendu : {path.name}")
    raw = path.read_bytes()
    # Le format `pages` se repère à sa clé de tête ; sinon manifeste IIIF.
    if b'"pages"' in raw[:2000]:
        raw_pages = PagesDocument.model_validate_json(raw).pages
    else:
        raw_pages = [c.to_raw_page() for c in IIIFManifest.model_validate_json(raw).items]
    return Session(
        path=path,
        date=meta["date"],
        chamber=meta["chamber"],
        ark=meta["ark"],
        pages=[_normalize_page(i, p) for i, p in enumerate(raw_pages)],
    )


def session_paths(data_dir: Path | str = DATA_DIR) -> list[Path]:
    """Fichiers de séance de `data_dir` (les autres fichiers sont ignorés), triés."""
    return [p for p in sorted(Path(data_dir).glob("*.json")) if parse_filename(p)]


def iter_sessions(data_dir: Path | str = DATA_DIR) -> Iterator[Session]:
    for path in session_paths(data_dir):
        yield load_session(path)
