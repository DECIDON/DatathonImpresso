# Schéma « IIIF » — manifeste Gallica + NER

Un fichier = **un numéro du JORF Débats** (une séance d'une chambre).
Nom : `<date>_<chambre>_<ark>.json`, ex. `1934-01-25_senat_bpt6k6395756r.json`.

- **Origine** : manifeste [IIIF Presentation v3](https://iiif.io/api/presentation/3.0/) de Gallica (openapi.bnf.fr) fourni pour le datathon Impresso × BnF, dans lequel les blocs OCR Chandra ont été ajoutés comme annotations, puis enrichi par le pipeline NER Decidon.
- **Reconnaître le format** : la racine a `@context` et `items` (pas de `pages`).
- **Dans `data/`** : 27 fichiers, 728 pages (canvas), 31 086 blocs, 63 010 entités, 2 258 relations.
- **Légende** : 🟦 champ IIIF standard livré par Gallica · 🟩 ajouté par le datathon (blocs Chandra) · 🟧 ajouté par le NER Decidon.
- **Fichiers compagnons** : `data/_RUN_INFO.json` (= le contenu de `ner_runs.<run_id>`) et `data/_PIVOT.json` (résumé du lot : comptes, md5, définition des offsets).

Voir aussi [schema_zenodo.md](schema_zenodo.md) : la partie NER (`ner`, `entities`, `relations`) y est identique ; ici un « bloc » est une annotation IIIF au lieu d'un objet `blocks[]`.

---

## Vue d'ensemble

```text
📄 <date>_<chambre>_<ark>.json                     manifeste IIIF v3 = un numéro
├── 🟦 @context           str     contexte JSON-LD IIIF v3
├── 🟦 id                 str     URL du manifeste (contient l'ark)
├── 🟦 type               str     "Manifest"
├── 🟦 label              lang    cote du document                         {"fr": ["Bibliothèque du Sénat, 2012-23800"]}
├── 🟦 summary            lang    titre de la publication
├── 🟦 metadata[]         obj     notice : 16 paires {label, value} (Date, Titre, Taux OCR…)
├── 🟦 provider[]         obj     fournisseur (BnF Gallica) : id, label, homepage, logo, seeAlso
├── 🟦 homepage[]         obj     page Gallica du document
├── 🟦 thumbnail[]        obj     vignette de la 1re page
├── 🟦 seeAlso[]          obj     notice OAI-PMH Dublin Core (XML)
├── 🟦 rights             str     licence (rightsstatements.org)
├── 🟦 requiredStatement  obj     mention de source obligatoire
├── 🟦 behavior[]         str     ["paged"]
├── 🟦 start              obj     canvas d'ouverture (absent d'un fichier)
├── 🟦 items[]            obj     CANVAS = une page, dans l'ordre
│   ├── 🟦 id             str     URL du canvas (…/f<n>/canvas)
│   ├── 🟦 type           str     "Canvas"
│   ├── 🟦 label          lang    numéro de page imprimé                  {"fr": ["76", "76"]}
│   ├── 🟦 height, width  int     taille du canvas en pixels (repère des #xywh)
│   ├── 🟦 thumbnail[]    obj     vignette de la page
│   ├── 🟦 seeAlso[]      obj     ALTO XML de la page (OCR BnF)
│   ├── 🟦 items[0].items[0]  obj  annotation "painting" = l'image de la page
│   │   ├── body.id       str     URL de l'image pleine résolution
│   │   ├── body.service[] obj    service IIIF Image (pour zoomer/découper)
│   │   └── metadata[]    obj     résolution (PPP / DPI)
│   ├── 🟩 annotations[0].items[]  obj  BLOCS Chandra (ordre de lecture)
│   │   ├── id            str     URL de l'annotation (…/annotations/<n>)
│   │   ├── 🟧 uuid       str     identifiant stable du bloc
│   │   ├── type          str     "Annotation"
│   │   ├── motivation    str     "commenting"
│   │   ├── body.type     str     "TextualBody"
│   │   ├── body.format   str     "text/html"
│   │   ├── body.value    str     "<Label>: <html>"                       "Page-Header: <p>★ Année 1934…</p>"
│   │   └── target        str     URL du canvas + #xywh=x,y,w,h
│   ├── 🟧 ner            obj     métadonnées du passage NER sur la page
│   │   ├── run           str     id du run → clé de ner_runs
│   │   ├── timestamp     str     fin du traitement (ISO 8601)
│   │   ├── texte         obj     { blocs_traites[], separateur, offsets }
│   │   ├── blocs_non_traites[]  obj  { block, label, raison }
│   │   ├── qc_ocr        obj     { version, flags[], couverture, exclue_du_ner }
│   │   ├── n_entites     int
│   │   └── n_relations   int
│   ├── 🟧 entities[]     obj     entités nommées
│   │   ├── block         str     uuid du bloc (annotation)
│   │   ├── value         obj     { start, end, text, labels[] }
│   │   ├── uuid          str     identifiant de l'entité
│   │   ├── producer      obj     { type: "auto", run, membres[] }
│   │   ├── score         float   confiance du vote
│   │   └── from_name, to_name, type, origin   champs techniques Label Studio
│   └── 🟧 relations[]    obj     liens FCT → PER/SPK
│       ├── from_uuid, to_uuid  str
│       ├── type, direction     str   "relation", "right"
│       ├── labels[]      str     ["function_of"]
│       └── producer      obj     { type: "auto", run, methode: "regle_meme_ligne" }
└── 🟧 ner_runs           obj     provenance du traitement NER
    └── <run_id>          obj     = contenu de _RUN_INFO.json (voir détail)
```

`lang` = objet de langue IIIF : `{"fr": ["…"], "en": ["…"]}` (une liste de chaînes par code langue ; `none` si sans langue).

---

## Détail des champs

### Racine — description du document (IIIF, livré)

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `@context` | `str` | Contexte JSON-LD IIIF Presentation 3. | `"http://iiif.io/api/presentation/3/context.json"` |
| `id` | `str` | URL du manifeste ; contient l'identifiant ark Gallica. | `"https://openapi.bnf.fr/iiif/presentation/v3/ark:/12148/bpt6k6395756r/manifest.json"` |
| `type` | `str` | Toujours `"Manifest"`. | |
| `label` | `lang` | Cote de l'exemplaire numérisé. | `{"fr": ["Bibliothèque du Sénat, 2012-23800"]}` |
| `summary` | `lang` | Titre de la publication. | `"Journal officiel … Sénat : compte rendu in-extenso"` |
| `metadata` | `obj[]` | Notice bibliographique, liste de `{label: lang, value: lang}`. Libellés : Langue, Dépôt, Numérisation par, Source images, Source métadonnées, Titre, Relation, Cote, Format, Type, Description, Editeur, **Date** (`"1934-01-25"`), Date de mise en ligne, **Taux OCR** (`"98.51 %"`, OCR BnF, pas Chandra), Classification Dewey. | |
| `provider` | `obj[]` | Fournisseur (BnF Gallica) : `id`, `type: "Agent"`, `label`, `homepage[]`, `logo[]`, `seeAlso[]` (CGU). | |
| `homepage` | `obj[]` | Lien vers la page Gallica du document (`id`, `type`, `label`). | `"https://gallica.bnf.fr/ark:/12148/bpt6k6395756r"` |
| `thumbnail` | `obj[]` | Vignette de la 1re page : `id` (URL webp), `type`, `format`, `service[]` (service IIIF Image ; absent d'un fichier). | |
| `seeAlso` | `obj[]` | Notice Dublin Core via OAI-PMH : `id`, `type: "Dataset"`, `label`, `format: "application/xml"`, `profile`. | |
| `rights` | `str` | URI de licence. | `"http://rightsstatements.org/vocab/NoC-CR/1.0/"` |
| `requiredStatement` | `obj` | Mention de source obligatoire (`label` + `value`). | `"Source : Bibliothèque du Sénat, 2012-23800"` |
| `behavior` | `str[]` | Mode d'affichage pour les visionneuses. | `["paged"]` |
| `start` | `obj` | Canvas d'ouverture `{id, type: "Canvas"}`. Absent d'un fichier (1934-03-31). | |
| `items` | `obj[]` | Les pages (canvas), dans l'ordre. | |
| `ner_runs` | `obj` | 🟧 Dictionnaire `run_id → description du run NER`. | |

### `items[]` — un canvas (= une page)

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `id` | `str` | URL du canvas ; `f<n>` = numéro de vue Gallica (commence à 1). | `"…/bpt6k6395756r/f2/canvas"` |
| `type` | `str` | Toujours `"Canvas"`. | |
| `label` | `lang` | Numéro de page **imprimé** (souvent répété deux fois ; une seule valeur pour 14 pages). | `{"fr": ["76", "76"]}` |
| `height`, `width` | `int` | Dimensions du canvas en pixels = image pleine résolution. Repère des coordonnées `#xywh`. | `4948`, `3545` |
| `thumbnail` | `obj[]` | Vignette de la page (`id`, `type`, `format`). | |
| `seeAlso` | `obj[]` | OCR ALTO XML de la BnF pour la page (`profile` ALTO). Absent sur 16 pages. | `"…/f1/alto.xml"` |
| `items` | `obj[]` | `AnnotationPage` contenant l'annotation `painting` qui « peint » l'image sur le canvas (voir ci-dessous). | |
| `annotations` | `obj[]` | 🟩 `AnnotationPage` des blocs Chandra (un seul élément). **Liste vide sur 17 pages** (pages blanches…). | |
| `ner` | `obj` | 🟧 Bilan du passage NER sur la page. | |
| `entities` | `obj[]` | 🟧 Entités nommées de la page. | |
| `relations` | `obj[]` | 🟧 Relations entre entités de la page. | |

### `items[].items[0].items[0]` — l'image de la page (IIIF, livré)

| Clé | Type | Description |
| --- | --- | --- |
| `id`, `type`, `motivation` | `str` | Annotation `"painting"` (l'image). |
| `body.id` | `str` | URL de l'image pleine résolution (webp). |
| `body.label`, `body.format`, `body.height`, `body.width` | | Nom de fichier image (`"T0000001"`), format, dimensions. |
| `body.service[]` | `obj[]` | Service IIIF Image v3 (`id`, `type: "ImageService3"`, `profile: "level2"`) : permet de demander une région, ex. `<service.id>/<x,y,w,h>/max/0/default.jpg`. |
| `metadata[]` | `obj[]` | Résolution de numérisation (`PPP` / `DPI`, ex. `400`). |
| `target` | `str` | Canvas visé. |

### `items[].annotations[0].items[]` — un bloc Chandra

C'est l'équivalent de `blocks[]` dans le format Zenodo.

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `id` | `str` | URL de l'annotation (`…/f<n>/annotations/<k>`). | |
| `uuid` | `str` | 🟧 Identifiant UUID du bloc, clé utilisée par `entities[].block`. | `"76098587-ef28-…"` |
| `type` | `str` | `"Annotation"`. | |
| `motivation` | `str` | `"commenting"`. | |
| `body.type` | `str` | `"TextualBody"`. | |
| `body.format` | `str` | `"text/html"`. | |
| `body.value` | `str` | **`"<Label>: <html>"`** : label Chandra du bloc, deux-points, espace, puis le HTML brut du bloc. Labels observés : `Text` (87 %), `Section-Header`, `Page-Header`, `List-Group`, `Table`, `Page-Footer`, `Footnote`, `Image`, `Caption`. | `"Page-Header: SENAT — SEANCE DU 25 JANVIER 1934"` |
| `target` | `str` | URL du canvas + fragment `#xywh=x,y,largeur,hauteur` en pixels du canvas. | `"…/f2/canvas#xywh=1370,419,953,60"` |

### `items[].ner` — bilan NER de la page

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `run` | `str` | Identifiant du run NER (clé dans `ner_runs`). | `"decidon_ner_n2mix5relex_html_20261028T151809"` |
| `timestamp` | `str` | Date-heure ISO de fin du run. | `"2026-10-28T15:28:36+01:00"` |
| `texte.blocs_traites` | `str[]` | UUID des blocs envoyés aux modèles, dans l'ordre. | |
| `texte.separateur` | `str` | Séparateur entre blocs pour former le texte de page. | `"\n"` |
| `texte.offsets` | `str` | Définition en toutes lettres des offsets (voir [Offsets](#offsets--comment-retrouver-une-entité)). | |
| `blocs_non_traites` | `obj[]` | Blocs exclus du NER : `block` (uuid), `label`, `raison`. Motifs : `Page-Header`, `Page-Footer`, `Image`, `Table-prose`. | |
| `qc_ocr.version` | `str` | Version de l'algorithme de QC OCR. | `"qc_boucles v1 (2026-09-29), …"` |
| `qc_ocr.flags` | `obj[]` | Anomalies OCR détectées (voir ci-dessous). Vide en général. | `[]` |
| `qc_ocr.couverture` | `float` | Proportion (0 à 1) du texte de la page couverte par les anomalies. | `0.0` |
| `qc_ocr.exclue_du_ner` | `bool` | `true` si la page a été écartée du NER à cause du QC. | `false` |
| `n_entites`, `n_relations` | `int` | Nombre d'entités / de relations de la page. | `70`, `5` |

**`qc_ocr.flags[]`** — champs selon `type` :

| `type` | Signification | Champs spécifiques |
| --- | --- | --- |
| `boucle_segment` | L'OCR a bouclé : un même segment répété plusieurs fois. | `periode_mots`, `repetitions`, `extrait` |
| `compteur` | Suite numérique hallucinée (« 200, 201, … 300 »). | `longueur`, `de`, `a` |
| `langue_etrangere` | Texte détecté comme non français. | `mots_outils_en`, `mots_outils_fr` |

Tous portent `fragments[]` : `{block, start, end}` = zones concernées (uuid + offsets intra-bloc).

### `items[].entities[]` — une entité nommée

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `block` | `str` | UUID du bloc (annotation) contenant l'entité. | |
| `value.start` | `int` | Offset de début dans le HTML du bloc, **après** le préfixe `"<Label>: "`. | `4` |
| `value.end` | `int` | Offset de fin, exclu. | `20` |
| `value.text` | `str` | Texte visible (balises retirées, `<br/>` → `\n`, entités HTML décodées). | `"JOURNAL OFFICIEL"` |
| `value.labels` | `str[]` | Catégorie (une seule valeur), voir [Catégories](#catégories-dentités). | `["TITL"]` |
| `uuid` | `str` | Identifiant de l'entité ; répété si l'entité est à cheval sur deux blocs. | |
| `producer.type` | `str` | `"auto"` = prédiction machine. | |
| `producer.run` | `str` | Run NER producteur. | |
| `producer.membres` | `str[]` | Modèles ayant voté pour l'entité : `sp_flat`, `sp_grouped`, `rx_flat`, `gl_grouped`, `regex`. | `["rx_flat", "sp_flat"]` |
| `score` | `float` | Score de confiance du vote (≈ 0.2 à 1). | `0.2003` |
| `from_name`, `to_name`, `type`, `origin` | `str` | Constantes Label Studio : `"label"`, `"text"`, `"labels"`, `"prediction"`. | |

### `items[].relations[]` — une relation

| Clé | Type | Description | Exemple |
| --- | --- | --- | --- |
| `from_uuid` | `str` | Entité source, de type `FCT`. | « secrétaires » |
| `to_uuid` | `str` | Entité cible, `PER` ou `SPK`. | « Farjon » |
| `type`, `direction` | `str` | Constantes Label Studio `"relation"`, `"right"`. | |
| `labels` | `str[]` | Seule valeur : `function_of`. | `["function_of"]` |
| `producer` | `obj` | `type: "auto"`, `run`, `methode: "regle_meme_ligne"` (FCT et PER/SPK sur la même ligne). | |

### `ner_runs` — provenance du traitement

Dictionnaire `run_id → run` ; son contenu est aussi dans `data/_RUN_INFO.json`. Utile pour la traçabilité, ignorable pour l'analyse.

| Clé | Type | Description |
| --- | --- | --- |
| `run_id` | `str` | Identifiant du run (= la clé). |
| `role` | `str` | Description en clair du run. |
| `date_debut`, `date_fin` | `str` | Début / fin du run. |
| `machine` | `str` | Machine d'exécution. |
| `commande` | `str` | Commande principale lancée. |
| `commandes[]` | `obj[]` | Historique des lancements : `date`, `commande`, `issue` (résultat, ex. interruption). |
| `entree` | `str` | Dossier d'entrée des modèles. |
| `entree_des_modeles` | `str` | Comment le texte de page est construit (HTML des blocs joints par `\n`). |
| `shards`, `pages_par_shard` | `str[]`, `obj` | Découpage en lots (ici un seul lot de 728 pages). |
| `source.format` | `str` | Description du format d'entrée (manifestes IIIF à annotations Chandra). |
| `source.manifestes`, `source.manifestes_md5` | `str`, `obj` | Dossier des manifestes et md5 de chacun. |
| `source.uuid_blocs` | `str` | Table d'attribution des uuid de blocs + md5. |
| `source.preparation` | `obj` | Étape de préparation : `role`, `date`, `source`, `uuid_table` / `uuid_table_md5`, `shards`, `docs`, `qc`, `scripts_md5`, `stats` (pages, pages_texte_vide, blocs_traites, blocs_non_traites, caracteres, docs, pages_signalees_qc — sur le lot des 27 numéros). |
| `systeme` | `str` | Description du système d'ensemble (« N2 mix5 relex »). |
| `membres` | `obj` | Un texte par membre de l'ensemble (`sp_flat/sp_grpC/sp_grpE`, `rx_flat`, `gl_flat_conteneurs/gl_flat_entites`, `regex`, `vote`, `relations`) : code, commit, modèle, options. |
| `devices` | `obj` | Matériel effectif par membre (CPU / GPU) ; corrige le texte de `membres`. |
| `empreintes_modeles` | `str[]` | Empreinte (hash, epochs, nom) de chaque modèle. |
| `versions` | `obj` | Versions Python / librairies par environnement, et GPU. |
| `code` | `obj` | `depot_deploiement` (texte) et `scripts_md5` (md5 des scripts utilisés). |

---

## Offsets : comment retrouver une entité

Les offsets sont **intra-bloc**, en caractères Unicode dans le HTML brut du bloc (balises comprises), fin exclue. Le « contenu » du bloc est `body.value` **privé de son préfixe `"<Label>: "`** :

```python
ann = next(a for a in canvas["annotations"][0]["items"] if a["uuid"] == ent["block"])
label, content = ann["body"]["value"].split(": ", 1)
content[ent["value"]["start"]:ent["value"]["end"]]     # HTML brut de l'entité
ent["value"]["text"]                                    # même chose, balises retirées
```

Pour localiser un bloc sur l'image : `target` → `#xywh=x,y,w,h` en pixels du canvas (`width` × `height`), directement utilisable avec le service IIIF Image (`body.service[0].id + "/x,y,w,h/max/0/default.jpg"`).

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
