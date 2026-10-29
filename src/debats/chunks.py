"""Lecture des prises de parole (*chunks*) produites par `01_chunks` et de leurs plongements."""

import base64
import gzip
import json
import re

import numpy as np
import pandas as pd

from .reader import DATA_DIR, OUTPUT_DIR

EMBEDDINGS_PATH = DATA_DIR / "chunk_embeddings.jsonl.gz"

# « M. Robert Schuman. », « M. le ministre des finances. », « Mme X. » en tête de prise de parole.
_SPEAKER_RE = re.compile(r"^\s*(?:M\.|MM\.|Mme|Mmes|Mlle)\s[^.]{0,80}?\.\s*(?=\S|$)")


def strip_speaker(text: str) -> str:
    """Texte d'une prise de parole sans le nom de l'orateur qui l'ouvre."""
    return _SPEAKER_RE.sub("", text, count=1)


def load_chunks() -> pd.DataFrame:
    """Une ligne par prise de parole de `output/<chambre>/<ark>/chunk_NNNN.json`.

    `key` = (séance, premier bloc) relie un chunk à son plongement (`load_embeddings`).
    """
    rows = []
    for path in sorted(OUTPUT_DIR.glob("*/*/chunk_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        content = record["content"]
        rows.append(
            {
                "key": (record["session"], record["blocks"][0]),
                "session": record["session"],
                "chamber": path.parts[-3],
                "chamber_name": record["chamber"],
                "date": pd.Timestamp(record["date"]),
                "chunk": int(path.stem.removeprefix("chunk_")),
                "section": content["section"],
                "speaker": content["text"][: len(content["text"]) - len(strip_speaker(content["text"]))].strip(),
                "text": content["text"],
            }
        )
    return pd.DataFrame(rows)


def load_embeddings(path=EMBEDDINGS_PATH) -> tuple[pd.Index, np.ndarray]:
    """Plongements de `chunk_embeddings.jsonl.gz` : (clés des chunks, matrice float32 n × d).

    Chaque `embedding` est `"<modèle>:<base64 de float32 little-endian>"`.
    """
    keys, vectors = [], []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            _, data = record["embedding"].split(":", 1)
            keys.append((record["session"], record["blocks"][0]))
            vectors.append(np.frombuffer(base64.b64decode(data), dtype="<f4"))
    return pd.Index(keys, name="key", tupleize_cols=False), np.vstack(vectors)
