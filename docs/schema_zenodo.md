# Schéma « Zenodo » (`pages`) — JSON Chandra + NER

Un fichier = **un numéro du JORF Débats** (une séance d'une chambre).
Nom : `<date>_<chambre>_<ark>.json`, ex. `1934-01-09_chambre_bpt6k6428548r.json`.

- **Origine** : sortie OCR [Chandra](https://github.com/datalab-to/chandra) publiée sur Zenodo ([10.5281/zenodo.23019428](https://doi.org/10.5281/zenodo.23019428)), enrichie par le pipeline NER Decidon.
- **Reconnaître le format** : la racine a une clé `pages` (pas de `@context`).
- **Dans `data/`** : 13 fichiers, 456 pages, 20 108 blocs, 46 476 entités, 1 348 relations.
- **Légende** : 🟦 champ livré par Zenodo (non modifié) · 🟧 champ ajouté par le NER Decidon.

Voir aussi [schema_iiif.md](schema_iiif.md) pour l'autre format : la partie NER (`ner`, `entities`, `relations`, `ner_runs`) est identique, seul l'habillage change.

---

## Vue d'ensemble

```text
📄 <date>_<chambre>_<ark>.json
├── 🟦 sources[]            str     archive(s) Chandra d'origine            "6428548.zip"
├── 🟦 num_pages            int     nombre de pages du numéro               26
├── 🟦 pages[]              obj     une entrée par page, dans l'ordre
│   ├── 🟦 page_num         int     index de la page (commence à 0)         0
│   ├── 🟦 source           str     archive dont vient la page              "6428548.zip"
│   ├── 🟦 page_box         int[4]  cadre de la page [0, 0, largeur, hauteur]  [0,0,2048,2741]
│   ├── 🟦 blocks[]         obj     blocs de mise en page détectés par Chandra (ordre de lecture)
│   │   ├── 🟧 uuid         str     identifiant stable du bloc
│   │   ├── 🟦 bbox         int[4]  boîte [x0, y0, x1, y1] dans le repère de page_box
│   │   ├── 🟦 label        str     type de bloc : Text, Section-Header, Page-Header…
│   │   └── 🟦 content      str     contenu du bloc en HTML brut
│   ├── 🟧 ner              obj     métadonnées du passage NER sur cette page
│   │   ├── run             str     id du run → clé de ner_runs
│   │   ├── timestamp       str     date de fin du traitement (ISO 8601)
│   │   ├── texte           obj     comment le texte a été soumis aux modèles
│   │   │   ├── blocs_traites[]  str  uuid des blocs envoyés au NER, dans l'ordre
│   │   │   ├── separateur  str     séparateur entre blocs ("\n")
│   │   │   └── offsets     str     définition (en clair) des offsets start/end
│   │   ├── blocs_non_traites[]  obj  blocs exclus du NER
│   │   │   ├── block       str     uuid du bloc
│   │   │   ├── label       str     label Chandra du bloc
│   │   │   └── raison      str     motif d'exclusion
│   │   ├── qc_ocr          obj     contrôle qualité de l'OCR
│   │   │   ├── version     str     version de l'algorithme de QC
│   │   │   ├── flags[]     obj     anomalies détectées (voir détail)
│   │   │   ├── couverture  float   part du texte de la page touchée (0–1)
│   │   │   └── exclue_du_ner bool  page écartée du NER à cause du QC ?
│   │   ├── n_entites       int     nombre d'entités sur la page
│   │   └── n_relations     int     nombre de relations sur la page
│   ├── 🟧 entities[]       obj     entités nommées détectées
│   │   ├── block           str     uuid du bloc qui contient l'entité
│   │   ├── value           obj
│   │   │   ├── start       int     offset de début dans blocks[].content
│   │   │   ├── end         int     offset de fin (exclu)
│   │   │   ├── text        str     texte visible de l'entité
│   │   │   └── labels[]    str     catégorie : SPK PER FCT ORG LOC COM TITL
│   │   ├── uuid            str     identifiant de l'entité
│   │   ├── producer        obj     qui a produit l'entité
│   │   │   ├── type        str     "auto" (prédiction machine)
│   │   │   ├── run         str     id du run
│   │   │   └── membres[]   str     modèles ayant voté pour l'entité
│   │   ├── score           float   score de confiance du vote (0.2–1)
│   │   └── from_name, to_name, type, origin   str   champs techniques Label Studio
│   └── 🟧 relations[]      obj     liens entre entités
│       ├── from_uuid       str     entité source (une FCT)
│       ├── to_uuid         str     entité cible (une PER ou SPK)
│       ├── type            str     "relation"
│       ├── direction       str     "right"
│       ├── labels[]        str     ["function_of"]
│       └── producer        obj     { type: "auto", run, methode: "regle_meme_ligne" }
└── 🟧 ner_runs             obj     provenance complète du traitement NER
    └── <run_id>            obj     une entrée par run (une seule en pratique)
        └── …               (voir détail plus bas)
```

---

## Détail des champs

### Racine

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `sources` | `str[]` | Nom de la ou des archives Chandra dont le numéro est issu. Le nombre = identifiant Gallica sans le préfixe `bpt6k` ni la clé finale. | `["6428548.zip"]` |
| `num_pages` | `int` | Nombre total de pages du numéro (= `len(pages)`). | `26` |
| `pages` | `obj[]` | Les pages, dans l'ordre du fascicule. | |
| `ner_runs` | `obj` | 🟧 Dictionnaire `run_id → description du run NER`. Voir [ner_runs](#ner_runs--provenance-du-traitement). | |

### `pages[]` — une page

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `page_num` | `int` | Index de la page dans le numéro, **à partir de 0**. Ce n'est pas le numéro de page imprimé. | `0` |
| `source` | `str` | Archive Chandra d'origine (identique à `sources[0]`). | `"6428548.zip"` |
| `page_box` | `int[4]` | Cadre de la page `[0, 0, largeur, hauteur]` en pixels de l'image traitée par Chandra. Repère des `bbox`. | `[0, 0, 2048, 2741]` |
| `blocks` | `obj[]` | Blocs de mise en page, dans l'ordre de lecture. | |
| `ner` | `obj` | 🟧 Bilan du passage NER sur la page. | |
| `entities` | `obj[]` | 🟧 Entités nommées de la page (tous blocs confondus). | |
| `relations` | `obj[]` | 🟧 Relations entre entités de la page. | |

### `pages[].blocks[]` — un bloc Chandra

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `uuid` | `str` | 🟧 Identifiant UUID du bloc, stable d'un run à l'autre. C'est la clé utilisée par `entities[].block`. | `"39a21322-cc90-…"` |
| `bbox` | `int[4]` | Boîte englobante `[x0, y0, x1, y1]` (coin haut-gauche, coin bas-droit) en pixels, repère `page_box`. | `[24, 32, 2043, 2708]` |
| `label` | `str` | Type de bloc. Valeurs observées : `Text` (88 %), `Section-Header`, `Page-Header`, `List-Group`, `Table`, `Page-Footer`, `Footnote`, `Image`, `Caption`. | `"Text"` |
| `content` | `str` | Contenu du bloc en **HTML brut** (`<p>`, `<b>`, `<table>`…). Pour une `Image`, un `<img alt="…">` décrivant l'image. Les offsets des entités sont comptés dans cette chaîne. | `"<p>M. le président. …</p>"` |

### `pages[].ner` — bilan NER de la page

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `run` | `str` | Identifiant du run NER (clé dans `ner_runs`). | `"decidon_ner_n2mix5relex_html_20261020T093653"` |
| `timestamp` | `str` | Date-heure ISO de fin du run. | `"2026-10-27T07:32:10"` |
| `texte.blocs_traites` | `str[]` | UUID des blocs dont le texte a été envoyé aux modèles, dans l'ordre. | |
| `texte.separateur` | `str` | Chaîne insérée entre deux blocs pour former le texte de page. | `"\n"` |
| `texte.offsets` | `str` | Définition en toutes lettres des offsets `start`/`end` (voir [Offsets](#offsets--comment-retrouver-une-entité)). | |
| `blocs_non_traites` | `obj[]` | Blocs exclus du NER : `block` (uuid), `label` (label Chandra), `raison` (motif). Motifs observés : `Page-Header`, `Page-Footer`, `Image`, `Table-prose`. | `{"block": "…", "label": "Image", "raison": "Image"}` |
| `qc_ocr.version` | `str` | Version de l'algorithme de contrôle qualité OCR. | `"qc_boucles v1 (2026-09-29), …"` |
| `qc_ocr.flags` | `obj[]` | Anomalies OCR détectées, voir ci-dessous. Vide dans l'immense majorité des pages. | `[]` |
| `qc_ocr.couverture` | `float` | Proportion (0 à 1) du texte de la page couverte par les anomalies. | `0.0` |
| `qc_ocr.exclue_du_ner` | `bool` | `true` si la page a été écartée du NER à cause du QC. | `false` |
| `n_entites` | `int` | Nombre d'entités de la page (= `len(entities)`). | `70` |
| `n_relations` | `int` | Nombre de relations de la page (= `len(relations)`). | `5` |

**`qc_ocr.flags[]`** — champs selon `type` :

| `type` | Signification | Champs spécifiques |
| --- | --- | --- |
| `boucle_segment` | L'OCR a bouclé : un même segment répété plusieurs fois. | `periode_mots` (longueur du motif, en mots), `repetitions` (nb de répétitions), `extrait` (début du passage) |
| `compteur` | Suite numérique hallucinée (« 200, 201, … 300 »). | `longueur`, `de`, `a` (bornes de la suite) |
| `langue_etrangere` | Texte détecté comme non français. | `mots_outils_en`, `mots_outils_fr` (comptes de mots-outils) |

Tous portent `fragments[]` : `{block, start, end}` = zones concernées (uuid du bloc + offsets dans `content`).

### `pages[].entities[]` — une entité nommée

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `block` | `str` | UUID du bloc contenant l'entité. | |
| `value.start` | `int` | Offset de début dans `blocks[].content` du bloc (HTML brut). | `3` |
| `value.end` | `int` | Offset de fin, **exclu**. | `21` |
| `value.text` | `str` | Texte visible de l'entité (balises retirées, `<br/>` → `\n`, entités HTML décodées). | `"DU 10 JANVIER 1934"` |
| `value.labels` | `str[]` | Catégorie (toujours une seule valeur), voir [Catégories](#catégories-dentités). | `["TITL"]` |
| `uuid` | `str` | Identifiant de l'entité. **Répété** si l'entité est à cheval sur deux blocs (une ligne par bloc). | |
| `producer.type` | `str` | `"auto"` = prédiction machine (pas d'annotation humaine). | `"auto"` |
| `producer.run` | `str` | Run NER qui a produit l'entité. | |
| `producer.membres` | `str[]` | Modèles de l'ensemble ayant voté pour l'entité : `sp_flat`, `sp_grouped` (spaCy), `rx_flat` (GLiNER relex), `gl_grouped` (GLiNER-bi), `regex`. | `["sp_flat", "rx_flat"]` |
| `score` | `float` | Score de confiance issu du vote (≈ 0.2 à 1). | `0.2366` |
| `from_name`, `to_name`, `type`, `origin` | `str` | Champs techniques au format [Label Studio](https://labelstud.io/), constants : `"label"`, `"text"`, `"labels"`, `"prediction"`. | |

### `pages[].relations[]` — une relation

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `from_uuid` | `str` | Entité source, de type `FCT` (fonction). | « sénateur » |
| `to_uuid` | `str` | Entité cible, de type `PER` ou `SPK`. | « Jean Odin » |
| `type` | `str` | Constante Label Studio `"relation"`. | |
| `direction` | `str` | Constante Label Studio `"right"`. | |
| `labels` | `str[]` | Type de relation ; seul `function_of` existe. | `["function_of"]` |
| `producer` | `obj` | `type: "auto"`, `run`, `methode: "regle_meme_ligne"` (règle : une FCT et une PER/SPK sur la même ligne). | |

### `ner_runs` — provenance du traitement

`ner_runs` est un dictionnaire dont la clé est le `run_id`. Utile surtout pour la traçabilité ; on peut l'ignorer pour l'analyse.

| Clé | Type | Description |
| --- | --- | --- |
| `run_id` | `str` | Identifiant du run (= la clé). |
| `role` | `str` | Description en clair du run. |
| `date_debut`, `date_fin` | `str` | Début / fin du run (ISO 8601). |
| `machine` | `str` | Machine d'exécution. |
| `commande` | `null` | Inutilisé ici (voir `commandes`). |
| `commandes[]` | `obj[]` | Commandes lancées : `date`, `partie` (quels membres, CPU/GPU), `commande` (ligne de commande), `confinement` (limites mémoire). |
| `entree` | `str` | Dossier d'entrée des modèles. |
| `entree_des_modeles` | `str` | Comment le texte de page est construit (blocs HTML joints par `\n`). |
| `shards`, `pages_par_shard` | `str[]`, `obj` | Découpage du corpus en lots et nombre de pages par lot. |
| `source.zenodo` | `str` | DOI du dépôt Zenodo source. |
| `source.archive` | `str` | Archive Zenodo + md5. |
| `source.uuid_blocs` | `str` | Table d'attribution des uuid de blocs + md5. |
| `source.preparation` | `obj` | Étape de préparation : `role`, `date`, `source`, `csv` / `csv_md5` (liste des documents), `uuid_table` / `uuid_table_md5`, `shards`, `qc`, `scripts_md5`, `stats` (pages, pages_texte_vide, blocs_traites, blocs_non_traites, caracteres, docs, pages_signalees_qc — **sur tout le corpus Zenodo**, pas seulement ce fichier). |
| `systeme` | `str` | Description du système d'ensemble (« N2 mix5 relex »). |
| `membres` | `obj` | Un texte par membre de l'ensemble (`sp_flat/sp_grpC/sp_grpE`, `rx_flat`, `gl_flat_conteneurs/gl_flat_entites`, `regex`, `vote`, `relations`) : code, commit, modèle, options. |
| `empreintes_modeles` | `str[]` | Empreinte (hash, epochs, nom) de chaque modèle utilisé. |
| `versions` | `obj` | Versions Python / librairies par environnement, et GPU. |
| `code` | `obj` | Code figé : `archive` + `archive_md5`, `contenu`, `depot_deploiement` (`depot`, `commit`, `tag`), `copies_figees` (commit par dépôt), `params_vote`. |
| `pivot_version` | `obj` | Version du format pivot : `version` (int), `date`, `note`. |

---

## Offsets : comment retrouver une entité

Les offsets sont **intra-bloc**, comptés en caractères Unicode dans le **HTML brut** du bloc (balises comprises), fin exclue :

```python
block = next(b for b in page["blocks"] if b["uuid"] == ent["block"])
block["content"][ent["value"]["start"]:ent["value"]["end"]]   # HTML brut de l'entité
ent["value"]["text"]                                            # même chose, balises retirées
```

## Catégories d'entités

| Label | Sens | Exemples |
| --- | --- | --- |
| `SPK` | Orateur (personne qui prend la parole) | « Farjon », « président » |
| `PER` | Personne citée | « général Hirschauer », « ministre de la guerre » |
| `FCT` | Fonction / qualité | « sénateur », « secrétaires » |
| `ORG` | Organisation, institution | « Sénat », « Chambre des députés » |
| `LOC` | Lieu | « Paris », « FRANCE » |
| `COM` | Commentaire / didascalie entre parenthèses | « (Adhésion.) », « (La séance est levée…) » |
| `TITL` | Titre, intertitre | « JOURNAL OFFICIEL », « QUESTIONS ÉCRITES… » |
