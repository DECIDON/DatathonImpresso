# DatathonImpresso

Extraction des prises de parole (*chunks*) des débats parlementaires du JORF (OCR + NER), en vue d'un plongement vectoriel.

## Installation

```bash
uv sync
```

## Utilisation

Placer les fichiers de séance (`<date>_<chambre>_<ark>.json`) dans `data/`, puis :

```bash
uv run impresso-chunks                      # traite data/ → output/
uv run impresso-chunks data/1934-01-25_chambre_bpt6k64285569.json -o output -v
uv run impresso-chunks --dry-run            # découpe sans écrire
```

Les chunks sont écrits dans `output/<chambre>/<ark>/chunk_NNNN.json` :

```json
{
  "session": "1934-01-25_chambre_bpt6k64285569",
  "chamber": "Chambre des députés",
  "date": "1934-01-25",
  "created": "2026-10-28T15:35:19+00:00",
  "blocks": ["<uuid des blocs>"],
  "spk_uuid": "<uuid de l'entité SPK>",
  "content": {
    "section": "<entité TITL>",
    "subsections": ["<Section-Header intermédiaires>"],
    "text": "<texte de la prise de parole>"
  }
}
```
