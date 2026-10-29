# DatathonImpresso

Expérimentations du datathon [Impresso](https://impresso-project.ch/) sur les débats parlementaires du JORF (OCR Chandra + NER).

Le dépôt est une collection de notebooks (`notebooks/`) qui s'appuient sur une petite lib commune (`src/debats/`).

## Installation

```bash
uv sync
uv run jupyter lab
```

Les fichiers de séance (`<date>_<chambre>_<ark>.json`, format `pages` ou manifeste IIIF, cf. `data/README.md`) sont attendus dans `data/` ; les sorties vont dans `output/` (tous deux hors git).

## Lib `debats`

Lecture des séances en un modèle pydantic normalisé, quel que soit le format source :
`Session → pages: list[Page] → blocks: list[Block] → entities: list[Entity]` (+ `Page.relations`).

```python
from debats import iter_sessions, load_session, session_paths

session = load_session(session_paths()[0])
for block in session.blocks:          # tous les blocs, dans l'ordre de lecture
    block.label, block.text, block.entities_of("SPK")
```

## Notebooks

| Notebook | Objet |
| --- | --- |
| `01_chunks.ipynb` | Découpage des séances en prises de parole → `output/<chambre>/<ark>/chunk_NNNN.json` |
| `02_timeline_rubriques.ipynb` | Timeline interactive des rubriques de l'ordre du jour et de leurs orateurs, par chambre → `output/timeline/` |
