"""Briques de topic modeling (LDA) sur les prises de parole : vectorisation, cohérence, nommage."""

import re
import unicodedata

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer

# Mots-outils du français + vocabulaire de procédure parlementaire, qui ne disent rien du sujet.
STOPWORDS_FR = set(
    """
    a à afin ai aie aient aies ait alors après as assez au aucun aucune aujourd auprès aussi autant autre autres aux
    avaient avais avait avant avec avez aviez avions avoir avons ayant ayez ayons bien c ça car ce ceci cela celle
    celles celui cependant certain certaine certaines certains ces cet cette ceux chacun chacune chaque chez ci comme
    comment contre d dans de déjà depuis des dès deux devant doit doivent donc dont du durant elle elles en encore
    entre es est et étaient étais était étant été êtes étiez étions être eu eue eues eûmes eurent eus eusse eut eux
    faire fait faites faut fois font furent fus fut ici il ils j je jusqu jusque l la là laquelle le lequel les
    lesquelles lesquels leur leurs lors lorsque lui m ma mais me même mêmes mes moi moins mon n ne ni non nos notre
    nous on ont or ou où par parce parmi pas pendant peu peut peuvent peux plus plusieurs pour pourquoi pourra
    pourrait pouvez pouvons puis puisque qu quand que quel quelle quelles quelque quelques quels qui quoi s sa sans
    sauf se selon sera serai seraient serais serait seront ses si sien soi soient sois soit sommes son sont sous
    soyez suis sur t ta tandis tant te tel telle telles tels tes toi ton tous tout toute toutes très tu un une
    unes uns vers voici voilà vos votre vous y
    avais aurait auraient aurai aura auront avez veux veut voulez voulons vouloir voudrais voudrait dire dit dis disent
    dites disait sais sait savez savons crois croit croyez pense pensez demande demander demandé
    ainsi alors aussi autrement beaucoup certes chose choses cas façon fin manière moment point simplement tellement
    toujours jamais trop tout toutefois vrai vraiment également seulement surtout oui non
    monsieur messieurs madame président présidente collègue collègues honorable mm ministre ministres gouvernement
    chambre sénat assemblée séance parole question questions amendement amendements article articles alinéa texte
    commission rapporteur rapport projet proposition loi lois vote voter voix adopté adoptée adoption scrutin
    discussion débat orateur applaudissements interruptions exclamations bruit rires mouvements très bien gauche
    droite centre extrême sur bancs divers plusieurs voix
    premier première deuxième troisième second seconde dernier dernière
    francs franc millions million milliards milliard cent cents mille
    deux trois quatre cinq six sept huit neuf dix onze douze quinze vingt trente quarante cinquante soixante
    heure heures minute minutes jour jours art chap etc
    """.split()
)

# Mots des topics de procédure (dépôts, renvois, consultation de l'assemblée, fixation de l'ordre du jour).
PROCEDURE_WORDS = set(
    """
    déposer déposé dépôt renvoyée renvoyé renvoi imprimée imprimé distribuée distribué consulte consultée passage
    décide bureau tendant urgence ordre suspendue reprise inscrit inscription délibération assentiment date
    immédiate reçu annexé fixation
    """.split()
)

TOKEN_PATTERN = r"(?u)\b[^\W\d_]{3,}\b"


def make_vectorizer(min_df: int = 5, max_df: float = 0.4, **kwargs) -> CountVectorizer:
    """Sac de mots : mots d'au moins 3 lettres, minuscules, hors `STOPWORDS_FR`."""
    return CountVectorizer(
        lowercase=True,
        token_pattern=TOKEN_PATTERN,
        stop_words=sorted(STOPWORDS_FR),
        min_df=min_df,
        max_df=max_df,
        **kwargs,
    )


def fold_plurals(X: sparse.spmatrix, vocab: np.ndarray) -> tuple[sparse.csr_matrix, np.ndarray]:
    """Fusionne les colonnes « blés », « travaux »… dans « blé », « travail » quand le singulier est au vocabulaire.

    Pluriels réguliers seulement (-s, -x, -aux → -al) : pas de lemmatiseur, mais les mots-clés restent lisibles.
    """
    index = {w: i for i, w in enumerate(vocab)}
    target = np.arange(len(vocab))
    for i, w in enumerate(vocab):
        for singular in (w[:-1] if w[-1] in "sx" else None, w[:-3] + "al" if w.endswith("aux") else None):
            if singular and singular in index:
                target[i] = index[singular]
                break
    keep = np.unique(target)
    remap = np.searchsorted(keep, target)
    M = sparse.csr_matrix((np.ones(len(vocab)), (np.arange(len(vocab)), remap)), shape=(len(vocab), len(keep)))
    return (sparse.csr_matrix(X) @ M).tocsr(), vocab[keep]


def umass_coherence(topic_word: np.ndarray, X: sparse.spmatrix, top_n: int = 10) -> np.ndarray:
    """Cohérence UMass de chaque topic (plus proche de 0 = mots qui co-occurrent davantage dans les documents)."""
    B = (sparse.csc_matrix(X) > 0).astype(np.int64)
    scores = []
    for row in topic_word:
        top = np.argsort(row)[::-1][:top_n]
        cols = B[:, top]
        co = (cols.T @ cols).toarray()
        df = np.diag(co)
        s = [np.log((co[i, j] + 1) / df[j]) for i in range(1, len(top)) for j in range(i) if df[j]]
        scores.append(np.mean(s))
    return np.array(scores)


def top_words(topic_word: np.ndarray, vocab: np.ndarray, word_freq: np.ndarray, n: int = 10, lam: float = 0.6) -> list[list[str]]:
    """Mots les plus caractéristiques de chaque topic, par *relevance* (Sievert & Shirley 2014).

    λ = 1 : mots les plus probables du topic ; λ → 0 : mots les plus spécifiques (lift).
    """
    phi = topic_word / topic_word.sum(axis=1, keepdims=True)
    p_w = word_freq / word_freq.sum()
    with np.errstate(divide="ignore"):
        relevance = lam * np.log(phi) + (1 - lam) * np.log(phi / p_w)
    relevance[:, word_freq == 0] = -np.inf  # mots absents du sous-corpus (LDA sur une partie du vocabulaire)
    return [list(vocab[np.argsort(r)[::-1][:n]]) for r in relevance]


# Formules d'ordre du jour qui précèdent l'objet d'une rubrique (texte sans accents, en majuscules).
_SECTION_BOILERPLATE = [
    r"^(?:SUITE|REPRISE|FIN) DE LA ",
    r"^(?:DISCUSSION|ADOPTION|TRANSMISSION)\b,?\s*",
    r"^APRES (?:DEMANDE DE )?DISCUSSION IMMEDIATE,?\s*",
    r"^(?:DU|DE LA|DE L'|D'UNE|D'UN|DES|DE)(?:\s+|(?<=')(?=\w))",
    r"^(?:PROJET|PROPOSITION)S? DE (?:LOI|RESOLUTION)\b,?\s*",
    r"^(?:ADOPTEE?S?|MODIFIEE?S?)\b[^,]*,\s*",
    r"^(?:PORTANT|RELATIVES? (?:A|AUX|AU)|RELATIFS? (?:A|AUX|AU)|SUR|CONCERNANT|TENDANT A)\s+",
    r"^(?:L'|LA |LE |LES )(?=\w)",
]


def _unaccent(text: str) -> str:
    # Caractère par caractère, pour garder les positions alignées sur le texte d'origine.
    return "".join(unicodedata.normalize("NFKD", c)[0] for c in text).upper()


def _n_accents(text: str) -> int:
    return sum(not c.isascii() for c in text)


def short_section(title: str | None, max_len: int = 70) -> str | None:
    """Objet d'une rubrique, sans la formule d'ordre du jour.

    « SUITE DE LA DISCUSSION DU PROJET DE LOI PORTANT FIXATION DU BUDGET GÉNÉRAL… »
    → « Fixation du budget général de l'exercice 1934 »
    """
    if not title:
        return None
    text = " ".join(unicodedata.normalize("NFC", title).replace("’", "'").split()).strip(" .:-—")
    key = _unaccent(text)
    changed = True
    while changed:
        changed = False
        for pattern in _SECTION_BOILERPLATE:
            if (m := re.match(pattern, key)) and m.end() < len(key):
                text, key, changed = text[m.end() :], key[m.end() :], True
    text = text[0].upper() + text[1:].lower() if text else text
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def short_sections(titles: pd.Series) -> pd.Series:
    """`short_section` de chaque rubrique ; les variantes d'accents de l'OCR prennent la graphie la plus fréquente."""
    short = titles.map(short_section)
    key = short.map(lambda t: _unaccent(t) if t else t)
    # À fréquence comparable, la graphie la plus accentuée (l'OCR perd des accents, n'en invente pas).
    canonical = short.groupby(key).agg(lambda s: max(s.value_counts().items(), key=lambda v: (_n_accents(v[0]), v[1]))[0])
    return key.map(canonical)


def name_topics(
    keywords: list[list[str]],
    doc_topic: np.ndarray,
    sections: pd.Series,
    n_keywords: int = 3,
    min_share: float = 0.2,
    min_lift: float = 1.5,
) -> pd.DataFrame:
    """Un nom lisible par topic : ses mots-clés, précédés de la rubrique d'ordre du jour qui le caractérise.

    `sections` (une rubrique courte par document) est croisée avec le topic dominant de chaque document.
    La rubrique retenue maximise share × log(lift) — part des documents du topic qui en relèvent, pondérée
    par sa sur-représentation par rapport au corpus — si elle couvre au moins `min_share` du topic et y est
    au moins `min_lift` fois plus fréquente qu'ailleurs.
    """
    sections = pd.Series(sections).reset_index(drop=True)
    dominant = doc_topic.argmax(axis=1)
    overall = sections.value_counts(normalize=True)
    rows = []
    for k, words in enumerate(keywords):
        mask = dominant == k
        counts = sections[mask].value_counts()
        shares = counts / max(mask.sum(), 1)
        lift = shares / overall[shares.index]
        candidates = shares[(shares >= min_share) & (lift >= min_lift)]
        section = (candidates * np.log(lift[candidates.index])).idxmax() if len(candidates) else None
        share = shares.get(section, 0.0)
        words_label = ", ".join(words[:n_keywords])
        procedure = sum(w in PROCEDURE_WORDS for w in words[:5]) >= 2
        prefix = "Procédure" if procedure else section
        rows.append(
            {
                "topic": k,
                "name": f"{prefix} · {words_label}" if prefix else words_label,
                "procedure": procedure,
                "section": section,
                "section_share": share,
                "keywords": words,
                "top_sections": counts.head(3).to_dict(),
                "n_docs": int(mask.sum()),
                "weight": float(doc_topic[:, k].sum()),
            }
        )
    return pd.DataFrame(rows).set_index("topic")
