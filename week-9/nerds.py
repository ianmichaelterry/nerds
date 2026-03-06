"""
Nerds: specialist operators that read/write RDF triples on the blackboard.

Week 8 changes from week 7:
- MoviePickerNerd fetches live data from Wikidata via SPARQL CONSTRUCT,
  producing schema:Movie triples that go directly onto the blackboard.
- All nerds produce RDF properties (Schema.org, Dublin Core, custom nerds:)
  instead of ad-hoc Python dicts.
- SHACL shapes (from vocabulary.py) encode preconditions declaratively.
- PROV-O provenance is recorded automatically by the blackboard.

The nerds themselves remain deliberately dumb. The intelligence upgrade
is in the data model, not in the agents.
"""

from __future__ import annotations
import os
import random
import colorsys
import base64
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import BytesIO

from rdflib import Graph, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, PROV, DCTERMS
from SPARQLWrapper import SPARQLWrapper, JSON
from requests_oauthlib import OAuth1
import requests
import numpy as np
from PIL import Image, ImageDraw

from pathlib import Path

from blackboard import Blackboard, Heat
from render import render_poster
from vocabulary import NERDS, SCHEMA, SH

# Types that represent meta-evaluation, not "real" poster assets.
# Critics use this to decide whether anything new has appeared.
_META_TYPES = [NERDS.Critique, NERDS.PosterCritique, NERDS.Completion,
               NERDS.VisibilityCritique, NERDS.ContrastCritique]


def _input_fingerprint(items: list[URIRef | None]) -> str:
    """Deterministic fingerprint from a set of input item URIs."""
    return "|".join(sorted(str(i) for i in items if i is not None))


# ---------------------------------------------------------------------------
# Noun Project API (icon fetching)
# ---------------------------------------------------------------------------

_NP_KEY_PATH = os.path.expanduser("~/.tokens/noun-project-api-key")
_NP_SECRET_PATH = os.path.expanduser("~/.tokens/noun-project-api-secret")
_NP_BASE = "https://api.thenounproject.com/v2"

# Genre -> icon search terms (multiple options for variety)
GENRE_ICON_TERMS = {
    "sci-fi":    ["robot", "spaceship", "planet", "laser", "alien", "circuit"],
    "horror":    ["skull", "ghost", "knife", "bat", "coffin", "eye"],
    "noir":      ["detective", "gun", "fedora", "cigarette", "city", "shadow"],
    "drama":     ["theater", "mask", "curtain", "spotlight", "stage"],
    "action":    ["explosion", "fist", "lightning", "fire", "sword", "shield"],
    "thriller":  ["eye", "lock", "fingerprint", "target", "clock"],
    "romance":   ["heart", "rose", "kiss", "ring", "candle"],
    "fantasy":   ["dragon", "castle", "wizard", "crown", "sword", "crystal"],
    "comedy":    ["laugh", "mask", "microphone", "balloon", "party"],
    "adventure": ["compass", "map", "mountain", "ship", "treasure"],
    "mystery":   ["magnifying glass", "key", "puzzle", "question", "clue"],
    "animation": ["star", "pencil", "palette", "frame", "sparkle"],
    "war":       ["helmet", "tank", "medal", "flag", "shield"],
}


def _get_noun_project_auth() -> OAuth1 | None:
    """Load Noun Project OAuth1 credentials. Returns None if unavailable."""
    try:
        key = open(_NP_KEY_PATH).read().strip()
        secret = open(_NP_SECRET_PATH).read().strip()
        return OAuth1(key, secret)
    except FileNotFoundError:
        return None


def _fetch_icon(term: str, accent_color: str) -> dict | None:
    """
    Search the Noun Project for an icon matching *term* and download it.

    Returns dict with 'png_base64', 'icon_id', 'term', 'attribution'
    or None on failure.
    """
    auth = _get_noun_project_auth()
    if not auth:
        print("  [IconNerd] No Noun Project credentials found, skipping")
        return None

    try:
        # Search for icons
        r = requests.get(f"{_NP_BASE}/icon", params={
            "query": term,
            "limit": 10,
            "limit_to_public_domain": 1,
            "thumbnail_size": 200,
        }, auth=auth, timeout=10)
        r.raise_for_status()
        data = r.json()
        icons = data.get("icons", [])
        if not icons:
            print(f"  [IconNerd] No icons found for '{term}'")
            return None

        icon = random.choice(icons)
        icon_id = icon["id"]

        # Download as PNG, tinted to accent color
        color_hex = accent_color.lstrip("#")
        dl = requests.get(f"{_NP_BASE}/icon/{icon_id}/download", params={
            "filetype": "png",
            "size": 400,
            "color": color_hex,
        }, auth=auth, timeout=10)
        dl.raise_for_status()
        dl_data = dl.json()

        return {
            "png_base64": dl_data["base64_encoded_file"],
            "icon_id": str(icon_id),
            "term": icon.get("term", term),
            "attribution": icon.get("attribution", ""),
        }
    except Exception as e:
        print(f"  [IconNerd] Noun Project fetch failed ({e})")
        return None


# ---------------------------------------------------------------------------
# OMDb API (plot keywords)
# ---------------------------------------------------------------------------

_OMDB_KEY_PATH = os.path.expanduser("~/.tokens/omdb-api")


def _get_omdb_key() -> str | None:
    """Load OMDb API key. Returns None if unavailable."""
    try:
        return open(_OMDB_KEY_PATH).read().strip()
    except FileNotFoundError:
        return None


def _fetch_plot_keywords(title: str, year: int | None) -> list[str] | None:
    """
    Query OMDb for a movie's short plot, then extract nouns as keywords.

    Returns a list of lowercase noun strings, or None on failure.
    """
    api_key = _get_omdb_key()
    if not api_key:
        print("  [KeywordNerd] No OMDb API key found, skipping")
        return None

    params = {"t": title, "apikey": api_key, "plot": "short"}
    if year:
        params["y"] = str(year)

    try:
        r = requests.get("https://www.omdbapi.com/", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("Response") == "False":
            print(f"  [KeywordNerd] OMDb: {data.get('Error', 'not found')}")
            return None

        plot = data.get("Plot", "")
        if not plot or plot == "N/A":
            print("  [KeywordNerd] OMDb returned no plot")
            return None

        print(f"  [KeywordNerd] OMDb plot: {plot}")
        return _extract_nouns(plot)
    except Exception as e:
        print(f"  [KeywordNerd] OMDb fetch failed ({e})")
        return None


def _extract_nouns(text: str) -> list[str]:
    """
    Extract likely nouns from a short plot string using simple heuristics.

    Uses a stop-word filter and part-of-speech-like heuristics rather than
    a full NLP library. Words that survive filtering are likely nouns or
    noun-adjacent terms useful for icon search.
    """
    _STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "has", "have", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "need", "must",
        "it", "its", "he", "she", "they", "them", "his", "her", "their",
        "this", "that", "these", "those", "who", "whom", "which", "what",
        "where", "when", "how", "why", "not", "no", "nor", "so", "if",
        "then", "than", "too", "very", "just", "about", "up", "out", "off",
        "over", "into", "through", "after", "before", "between", "under",
        "again", "once", "here", "there", "all", "each", "every", "both",
        "few", "more", "most", "other", "some", "such", "only", "own",
        "same", "also", "while", "during", "until", "against", "above",
        "below", "him", "himself", "herself", "itself", "themselves",
        "we", "us", "our", "my", "me", "i", "you", "your",
        # Common verbs that survive simple filtering
        "find", "finds", "take", "takes", "make", "makes", "get", "gets",
        "go", "goes", "come", "comes", "know", "knows", "think", "see",
        "become", "becomes", "try", "tries", "set", "sets", "must",
        "begins", "begin", "starts", "start", "ends", "end",
        "along", "across", "around", "among",
    }

    # Also skip words ending in common verb/adjective suffixes
    _VERB_SUFFIXES = ("ing", "tion", "ly", "ed", "ness", "ment", "ous", "ive",
                      "able", "ible", "ful", "less")

    import re
    words = re.findall(r"[a-zA-Z]+", text.lower())
    nouns = []
    for w in words:
        if len(w) <= 2:
            continue
        if w in _STOP_WORDS:
            continue
        # Skip words that look like verbs/adjectives/adverbs
        if any(w.endswith(s) for s in _VERB_SUFFIXES):
            continue
        nouns.append(w)
    return nouns


# ---------------------------------------------------------------------------
# Wikidata SPARQL query for movie data
# ---------------------------------------------------------------------------

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Genre Wikidata IDs -> simple labels for palette mapping
GENRE_QID_MAP = {
    "Q157443": "action",
    "Q130232": "drama",
    "Q471839": "sci-fi",
    "Q200092": "horror",
    "Q959790": "noir",        # film noir
    "Q842256": "noir",        # neo-noir
    "Q21401869": "noir",      # crime thriller
    "Q1341051": "thriller",
    "Q586250": "romance",
    "Q157394": "fantasy",
    "Q52162262": "sci-fi",    # science fiction film
    "Q24925": "sci-fi",       # science fiction film (alt)
    "Q859369": "comedy",
    "Q319221": "adventure",
    "Q2975633": "mystery",
    "Q645928": "animation",
    "Q20442589": "war",
    "Q1535153": "drama",      # coming-of-age
}

# Two-phase Wikidata query strategy:
# Phase 1: Pick a random notable film (fast, no aggregation)
# Phase 2: Get details for that specific film (targeted, fast)
MOVIE_PICK_QUERY = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?film ?name WHERE {{
  ?film wdt:P31 wd:Q11424 ;    # instance of: film
        wdt:P57 ?dir ;           # has director
        wdt:P136 ?genre ;        # has genre
        wdt:P18 ?img .           # has image (notable enough)
  ?film rdfs:label ?name . FILTER(lang(?name) = "en")
  # Randomize via hash of film URI + a caller-provided salt
  BIND(MD5(CONCAT(STR(?film), "{salt}")) AS ?hash)
}}
ORDER BY ?hash
LIMIT 20
"""

MOVIE_DETAIL_QUERY = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?dirName ?genreId ?genreName ?year
       (GROUP_CONCAT(DISTINCT ?castName; SEPARATOR="|") AS ?cast)
WHERE {{
  <{film_uri}> wdt:P57 ?dir ;
               wdt:P161 ?castMember ;
               wdt:P136 ?genre .
  OPTIONAL {{ <{film_uri}> wdt:P577 ?date }}
  ?dir rdfs:label ?dirName . FILTER(lang(?dirName) = "en")
  ?castMember rdfs:label ?castName . FILTER(lang(?castName) = "en")
  ?genre rdfs:label ?genreName . FILTER(lang(?genreName) = "en")
  BIND(REPLACE(STR(?genre), "http://www.wikidata.org/entity/", "") AS ?genreId)
  BIND(YEAR(?date) AS ?year)
}}
GROUP BY ?dirName ?genreId ?genreName ?year
LIMIT 1
"""

# Hardcoded fallback in case Wikidata is unreachable
FALLBACK_MOVIES = [
    {"title": "Blade Runner", "director": "Ridley Scott", "genre": "sci-fi",
     "year": 1982, "actors": ["Harrison Ford", "Rutger Hauer", "Sean Young"],
     "tagline": "Man has made his match... now it's his problem."},
    {"title": "The Shining", "director": "Stanley Kubrick", "genre": "horror",
     "year": 1980, "actors": ["Jack Nicholson", "Shelley Duvall"],
     "tagline": "A masterpiece of modern horror."},
    {"title": "Moonlight", "director": "Barry Jenkins", "genre": "drama",
     "year": 2016, "actors": ["Trevante Rhodes", "Andre Holland", "Janelle Monae"],
     "tagline": "This is the story of a lifetime."},
    {"title": "Mad Max: Fury Road", "director": "George Miller", "genre": "action",
     "year": 2015, "actors": ["Tom Hardy", "Charlize Theron"],
     "tagline": "What a lovely day."},
    {"title": "Drive", "director": "Nicolas Winding Refn", "genre": "noir",
     "year": 2011, "actors": ["Ryan Gosling", "Carey Mulligan"],
     "tagline": "There are no clean getaways."},
]


def _fetch_wikidata_movies() -> list[dict]:
    """Query Wikidata for random notable films using a two-phase approach.

    Phase 1: Fast query to pick random film URIs + titles (no aggregation).
    Phase 2: Targeted detail query for the selected film.
    Returns list of dicts (usually 1 fully detailed + others title-only).
    """
    ua = "NERDS-Semantic/0.8 (academic research; https://github.com/ianmichaelterry/nerds)"
    try:
        # Phase 1: Pick random films (fast -- no GROUP_CONCAT, no cast join)
        salt = str(random.randint(0, 999999))
        sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
        sparql.setQuery(MOVIE_PICK_QUERY.format(salt=salt))
        sparql.setReturnFormat(JSON)
        sparql.addCustomHttpHeader("User-Agent", ua)
        sparql.setTimeout(15)
        pick_results = sparql.query().convert()

        candidates = pick_results["results"]["bindings"]
        if not candidates:
            print("  [Wikidata] No films found, using fallback")
            return FALLBACK_MOVIES

        # Pick one at random
        chosen = random.choice(candidates)
        film_uri = chosen["film"]["value"]
        film_name = chosen["name"]["value"]
        print(f"  [Wikidata] Phase 1: picked '{film_name}' from {len(candidates)} candidates")

        # Phase 2: Get details for this specific film (fast -- single entity)
        detail_query = MOVIE_DETAIL_QUERY.format(film_uri=film_uri)
        sparql2 = SPARQLWrapper(WIKIDATA_ENDPOINT)
        sparql2.setQuery(detail_query)
        sparql2.setReturnFormat(JSON)
        sparql2.addCustomHttpHeader("User-Agent", ua)
        sparql2.setTimeout(15)
        detail_results = sparql2.query().convert()

        detail_rows = detail_results["results"]["bindings"]
        if not detail_rows:
            # Got a name but no details -- use what we have
            return [{"title": film_name, "director": "Unknown", "genre": "drama",
                     "genre_label": "drama", "year": None, "actors": [],
                     "tagline": "", "wikidata_uri": film_uri}]

        row = detail_rows[0]
        genre_qid = row.get("genreId", {}).get("value", "")
        genre = GENRE_QID_MAP.get(genre_qid, "drama")
        year_val = row.get("year", {}).get("value")
        cast_str = row.get("cast", {}).get("value", "")
        actors = [a.strip() for a in cast_str.split("|") if a.strip()][:5]

        movie = {
            "title": film_name,
            "director": row.get("dirName", {}).get("value", "Unknown"),
            "genre": genre,
            "genre_label": row.get("genreName", {}).get("value", genre),
            "year": int(year_val) if year_val else None,
            "actors": actors,
            "tagline": "",
            "wikidata_uri": film_uri,
        }
        print(f"  [Wikidata] Phase 2: {movie['title']} ({movie.get('year', '?')}) "
              f"dir. {movie['director']}, genre: {movie['genre_label']}")
        return [movie]

    except Exception as e:
        print(f"  [Wikidata] Query failed ({e}), using fallback movies")
        return FALLBACK_MOVIES


# ---------------------------------------------------------------------------
# Genre -> color mood associations
# ---------------------------------------------------------------------------

GENRE_PALETTES = {
    "sci-fi":    {"key_hue": 0.58, "accent_hue": 0.10, "sat": 0.7,  "val": 0.3},
    "horror":    {"key_hue": 0.0,  "accent_hue": 0.0,  "sat": 0.6,  "val": 0.15},
    "noir":      {"key_hue": 0.75, "accent_hue": 0.08, "sat": 0.5,  "val": 0.2},
    "drama":     {"key_hue": 0.55, "accent_hue": 0.45, "sat": 0.4,  "val": 0.35},
    "action":    {"key_hue": 0.08, "accent_hue": 0.12, "sat": 0.9,  "val": 0.4},
    "thriller":  {"key_hue": 0.60, "accent_hue": 0.05, "sat": 0.55, "val": 0.18},
    "romance":   {"key_hue": 0.95, "accent_hue": 0.05, "sat": 0.5,  "val": 0.4},
    "fantasy":   {"key_hue": 0.72, "accent_hue": 0.15, "sat": 0.65, "val": 0.35},
    "comedy":    {"key_hue": 0.12, "accent_hue": 0.55, "sat": 0.6,  "val": 0.5},
    "adventure": {"key_hue": 0.10, "accent_hue": 0.35, "sat": 0.7,  "val": 0.4},
    "mystery":   {"key_hue": 0.70, "accent_hue": 0.0,  "sat": 0.4,  "val": 0.2},
    "animation": {"key_hue": 0.30, "accent_hue": 0.60, "sat": 0.8,  "val": 0.5},
    "war":       {"key_hue": 0.10, "accent_hue": 0.0,  "sat": 0.3,  "val": 0.25},
}

TYPEFACES = [
    {"name": "serif-bold",     "style": "serif",  "weight": "bold"},
    {"name": "sans-light",     "style": "sans",   "weight": "light"},
    {"name": "slab-heavy",     "style": "slab",   "weight": "heavy"},
    {"name": "mono-regular",   "style": "mono",   "weight": "regular"},
    {"name": "script-italic",  "style": "script", "weight": "italic"},
]

LAYOUT_TEMPLATES = [
    {"name": "classic-centered",
     "title_y": 0.08, "title_align": "center",
     "image_y": 0.18, "image_h": 0.52,
     "tagline_y": 0.74, "credits_y": 0.88},
    {"name": "bottom-heavy",
     "title_y": 0.58, "title_align": "center",
     "image_y": 0.0,  "image_h": 0.55,
     "tagline_y": 0.76, "credits_y": 0.90},
    {"name": "split-diagonal",
     "title_y": 0.04, "title_align": "left",
     "image_y": 0.14, "image_h": 0.48,
     "tagline_y": 0.66, "credits_y": 0.85},
    {"name": "minimalist",
     "title_y": 0.38, "title_align": "center",
     "image_y": 0.0,  "image_h": 0.35,
     "tagline_y": 0.55, "credits_y": 0.92},
]


# ---------------------------------------------------------------------------
# Image compositing helpers (ImageMagick + XMP sidecars)
# ---------------------------------------------------------------------------

_HERO_RENDER_W, _HERO_RENDER_H = 600, 400

# XMP namespace URIs
_XMP_META_NS = "adobe:ns:meta/"
_XMP_RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_XMP_NERDS_NS = "http://example.org/nerds/"

ET.register_namespace("x", _XMP_META_NS)
ET.register_namespace("rdf", _XMP_RDF_NS)
ET.register_namespace("nerds", _XMP_NERDS_NS)


@dataclass
class _SourceEntry:
    """One original image's logical position inside a composite."""
    item_ref: str
    item_type: str
    x: int
    y: int
    width: int
    height: int


def _find_convert_cmd() -> list[str] | None:
    """Locate the ImageMagick convert binary (IM6) or magick (IM7)."""
    if shutil.which("convert"):
        return ["convert"]
    if shutil.which("magick"):
        return ["magick"]
    return None


def _render_hero_to_file(block_data: str, path: Path):
    """Render HeroImage block data to a standalone RGBA PNG."""
    w, h = _HERO_RENDER_W, _HERO_RENDER_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for block_str in block_data.split(";"):
        parts = block_str.strip().split(",")
        if len(parts) < 6:
            continue
        bx = int(float(parts[0]) * w)
        by = int(float(parts[1]) * h)
        bw = int(float(parts[2]) * w)
        bh = int(float(parts[3]) * h)
        color_hex = parts[4].strip()
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        a = int(float(parts[5]) * 255)
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(r, g, b, a))
    img.save(str(path))


def _materialize_image(bb: Blackboard, item: URIRef,
                       temp_dir: Path) -> Path | None:
    """Turn a blackboard image item into a PNG file on disk."""
    item_type = bb.get_property(item, DCTERMS.type)
    item_id = str(
        bb.get_property(item, DCTERMS.identifier)
        or str(item).split("/")[-1]
    )

    if item_type == NERDS.IconImage:
        b64 = str(bb.get_property(item, NERDS.iconPngBase64) or "")
        if not b64:
            return None
        path = temp_dir / f"mat_{item_id}.png"
        if not path.exists():
            path.write_bytes(base64.b64decode(b64))
        return path

    if item_type == NERDS.HeroImage:
        block_data = str(bb.get_property(item, NERDS.blockData) or "")
        if not block_data:
            return None
        path = temp_dir / f"mat_{item_id}.png"
        if not path.exists():
            _render_hero_to_file(block_data, path)
        return path

    if item_type == NERDS.CompositeImage:
        p = str(bb.get_property(item, NERDS.compositeImagePath) or "")
        if p and Path(p).exists():
            return Path(p)
        return None

    return None


# ---- XMP sidecar read / write / merge ----

def _write_xmp_sidecar(path: Path, sources: list[_SourceEntry]):
    """Write an XMP sidecar recording where each source image sits."""
    root = ET.Element(f"{{{_XMP_META_NS}}}xmpmeta")
    rdf_el = ET.SubElement(root, f"{{{_XMP_RDF_NS}}}RDF")
    desc = ET.SubElement(rdf_el, f"{{{_XMP_RDF_NS}}}Description")
    desc.set(f"{{{_XMP_RDF_NS}}}about", "")

    bag_wrap = ET.SubElement(desc, f"{{{_XMP_NERDS_NS}}}compositeSources")
    bag = ET.SubElement(bag_wrap, f"{{{_XMP_RDF_NS}}}Bag")

    for src in sources:
        li = ET.SubElement(bag, f"{{{_XMP_RDF_NS}}}li")
        li.set(f"{{{_XMP_RDF_NS}}}parseType", "Resource")
        for tag, val in [
            ("sourceItemRef", src.item_ref),
            ("sourceItemType", src.item_type),
            ("sourceX", str(src.x)),
            ("sourceY", str(src.y)),
            ("sourceWidth", str(src.width)),
            ("sourceHeight", str(src.height)),
        ]:
            el = ET.SubElement(li, f"{{{_XMP_NERDS_NS}}}{tag}")
            el.text = val

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), xml_declaration=True, encoding="utf-8")


def _read_xmp_sidecar(image_path: Path) -> list[_SourceEntry]:
    """Read source entries from an XMP sidecar, if one exists."""
    xmp_path = image_path.with_suffix(".xmp")
    if not xmp_path.exists():
        return []
    try:
        tree = ET.parse(str(xmp_path))
        sources: list[_SourceEntry] = []
        for li in tree.iter(f"{{{_XMP_RDF_NS}}}li"):
            ref = li.findtext(f"{{{_XMP_NERDS_NS}}}sourceItemRef", "")
            stype = li.findtext(f"{{{_XMP_NERDS_NS}}}sourceItemType", "")
            x = int(li.findtext(f"{{{_XMP_NERDS_NS}}}sourceX", "0"))
            y = int(li.findtext(f"{{{_XMP_NERDS_NS}}}sourceY", "0"))
            w = int(li.findtext(f"{{{_XMP_NERDS_NS}}}sourceWidth", "0"))
            h = int(li.findtext(f"{{{_XMP_NERDS_NS}}}sourceHeight", "0"))
            sources.append(_SourceEntry(ref, stype, x, y, w, h))
        return sources
    except Exception:
        return []


def _merge_xmp_sources(
    base_sidecar: list[_SourceEntry],
    base_item: URIRef, base_type: URIRef,
    base_x: int, base_y: int, base_w: int, base_h: int,
    overlay_sidecar: list[_SourceEntry],
    overlay_item: URIRef, overlay_type: URIRef,
    overlay_x: int, overlay_y: int,
    overlay_w: int, overlay_h: int,
) -> list[_SourceEntry]:
    """Merge source entries from base and overlay, adjusting positions.

    Both base and overlay positions are given in canvas coordinates.
    If either already has a sidecar, its entries are shifted accordingly;
    otherwise a single entry for the image itself is created.
    """
    sources: list[_SourceEntry] = []

    if base_sidecar:
        for s in base_sidecar:
            sources.append(_SourceEntry(
                s.item_ref, s.item_type,
                s.x + base_x, s.y + base_y,
                s.width, s.height,
            ))
    else:
        sources.append(_SourceEntry(
            str(base_item), str(base_type).split("/")[-1],
            base_x, base_y, base_w, base_h,
        ))

    if overlay_sidecar:
        for s in overlay_sidecar:
            sources.append(_SourceEntry(
                s.item_ref, s.item_type,
                s.x + overlay_x, s.y + overlay_y,
                s.width, s.height,
            ))
    else:
        sources.append(_SourceEntry(
            str(overlay_item), str(overlay_type).split("/")[-1],
            overlay_x, overlay_y, overlay_w, overlay_h,
        ))

    return sources


# ---- Composite critique helpers ----

def _uncritiqued_composites(bb: Blackboard,
                            critique_type: URIRef) -> list[URIRef]:
    """Find CompositeImages not yet assessed by *critique_type*."""
    composites = set(bb.query_items(NERDS.CompositeImage))
    critiqued: set[URIRef] = set()
    for crit in bb.query_items(critique_type):
        t = bb.get_property(crit, NERDS.critiquedItem)
        if t:
            critiqued.add(t)
    return list(composites - critiqued)


def _compute_source_visibility(composite_img: np.ndarray,
                               source_img: np.ndarray,
                               src_x: int, src_y: int,
                               tolerance: int = 10) -> float:
    """Fraction of source's opaque pixels preserved in the composite.

    For each non-transparent pixel in *source_img*, checks whether the
    composite has the same RGB value (within *tolerance* per channel)
    at offset (src_x, src_y).  Pixels that map outside the composite
    bounds count as not visible.
    """
    comp_h, comp_w = composite_img.shape[:2]
    src_h, src_w = source_img.shape[:2]

    opaque = source_img[:, :, 3] > 0
    total = int(opaque.sum())
    if total == 0:
        return 1.0

    ys, xs = np.where(opaque)
    cxs = xs + src_x
    cys = ys + src_y

    valid = (cxs >= 0) & (cxs < comp_w) & (cys >= 0) & (cys < comp_h)
    if valid.sum() == 0:
        return 0.0

    src_px = source_img[ys[valid], xs[valid], :3].astype(np.int16)
    comp_px = composite_img[cys[valid], cxs[valid], :3].astype(np.int16)

    matching = int(np.all(np.abs(src_px - comp_px) <= tolerance, axis=1).sum())
    return matching / total


def _region_mean_color(composite_img: np.ndarray,
                       x: int, y: int, w: int, h: int
                       ) -> np.ndarray | None:
    """Mean RGB of a rectangular region in the composite, clamped to bounds."""
    comp_h, comp_w = composite_img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(comp_w, x + w), min(comp_h, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    return composite_img[y1:y2, x1:x2, :3].astype(np.float64).mean(axis=(0, 1))


# ---------------------------------------------------------------------------
# Base Nerd
# ---------------------------------------------------------------------------

@dataclass
class Nerd:
    """Base class for all nerds."""
    name: str
    heat: Heat = Heat.MEDIUM
    cooldown: int = 0
    cooldown_rate: int = 2
    shacl_shape: URIRef | None = None  # link to SHACL shape in vocabulary

    def can_run(self, bb: Blackboard) -> bool:
        """Base check: cooldown only. SHACL handles structural preconditions."""
        return self.cooldown == 0

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        """
        Do the work. Return list of (type_concept, properties, heat, thermal_mass).
        The caller adds them to the blackboard with provenance.
        """
        raise NotImplementedError

    def call(self, bb: Blackboard) -> list[URIRef]:
        """Called by the scheduler. Runs the nerd and adds results to bb."""
        specs = self.run(bb)
        item_nodes = []
        for type_concept, properties, heat, thermal_mass in specs:
            node = bb.add(type_concept, properties,
                          created_by=self.name, heat=heat,
                          thermal_mass=thermal_mass)
            item_nodes.append(node)
        self.cooldown = self.cooldown_rate
        return item_nodes

    def tick(self):
        if self.cooldown > 0:
            self.cooldown -= 1


# ---------------------------------------------------------------------------
# Concrete Nerds
# ---------------------------------------------------------------------------

class MoviePickerNerd(Nerd):
    """Fetches a movie from Wikidata SPARQL and seeds the blackboard.

    Week 7: random.choice(MOVIES) from a 5-item hardcoded list.
    Week 8: SPARQL CONSTRUCT against Wikidata, producing schema:Movie triples.
    The data goes onto the blackboard as-is -- no parsing, no key mapping.
    """

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and not bb.has(NERDS.MovieData)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        print("  [MoviePicker] Querying Wikidata for films...")
        movies = _fetch_wikidata_movies()
        movie = random.choice(movies)
        print(f"  [MoviePicker] Selected: {movie['title']} "
              f"({movie.get('year', '?')}) dir. {movie['director']}")

        # Build RDF properties using Schema.org vocabulary
        props = {
            SCHEMA.name: Literal(movie["title"]),
            SCHEMA.director: Literal(movie["director"]),
            SCHEMA.genre: Literal(movie["genre"]),
            NERDS.genreLabel: Literal(movie.get("genre_label", movie["genre"])),
        }
        if movie.get("year"):
            props[SCHEMA.datePublished] = Literal(movie["year"], datatype=XSD.gYear)
        if movie.get("tagline"):
            props[SCHEMA.description] = Literal(movie["tagline"])

        # Actors as multiple schema:actor triples
        for actor in movie.get("actors", []):
            # We'll add these separately since props dict can't have dup keys
            pass

        # Store actors as a comma-separated literal for simplicity in rendering
        if movie.get("actors"):
            props[SCHEMA.actor] = Literal(", ".join(movie["actors"][:5]))

        if movie.get("wikidata_uri"):
            props[RDFS.seeAlso] = URIRef(movie["wikidata_uri"])

        return [(NERDS.MovieData, props, Heat.HOT, 5)]


class TitleParserNerd(Nerd):
    """Splits the movie title into primary/secondary chunks."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has(NERDS.MovieData)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        movie = bb.pick(NERDS.MovieData)
        if not movie:
            return []
        title = str(bb.get_property(movie, SCHEMA.name))
        parts = title.split(":", 1) if ":" in title else title.split(" ", 1)
        primary = parts[0].strip()
        secondary = parts[1].strip() if len(parts) > 1 else ""

        props = {
            NERDS.primaryTitle: Literal(primary),
            NERDS.secondaryTitle: Literal(secondary),
        }
        return [(NERDS.TitleChunks, props, Heat.HOT, 3)]


class KeywordNerd(Nerd):
    """Extracts plot-relevant keywords for icon search.

    Queries the OMDb API for the movie's short plot string, then extracts
    nouns as search keywords. If OMDb fails (no API key, movie not found,
    no plot), falls back to genre-based icon terms from GENRE_ICON_TERMS.
    """

    def can_run(self, bb: Blackboard) -> bool:
        return (super().can_run(bb) and bb.has(NERDS.MovieData)
                and not bb.has(NERDS.Keywords))

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        movie = bb.pick(NERDS.MovieData)
        if not movie:
            return []

        title = str(bb.get_property(movie, SCHEMA.name) or "")
        year_lit = bb.get_property(movie, SCHEMA.datePublished)
        year = int(year_lit) if year_lit else None
        genre = str(bb.get_property(movie, SCHEMA.genre) or "drama")

        keywords = _fetch_plot_keywords(title, year)
        source = "omdb"
        if not keywords:
            # Fallback to genre icon terms
            keywords = list(GENRE_ICON_TERMS.get(genre, ["film", "movie", "camera"]))
            source = "genre"
            print(f"  [KeywordNerd] Falling back to genre terms for '{genre}': {keywords}")

        print(f"  [KeywordNerd] Keywords ({source}): {keywords}")
        props = {
            NERDS.keywordList: Literal(",".join(keywords)),
            NERDS.keywordSource: Literal(source),
        }
        return [(NERDS.Keywords, props, Heat.HOT, 5)]


class GenrePaletteNerd(Nerd):
    """Generates a color palette based on genre mood associations."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has(NERDS.MovieData)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        movie = bb.pick(NERDS.MovieData)
        if not movie:
            return []
        genre = str(bb.get_property(movie, SCHEMA.genre) or "drama")
        pal = GENRE_PALETTES.get(genre, GENRE_PALETTES["drama"])

        jitter = random.uniform(-0.05, 0.05)
        key_rgb = colorsys.hsv_to_rgb(
            (pal["key_hue"] + jitter) % 1.0, pal["sat"], pal["val"])
        accent_rgb = colorsys.hsv_to_rgb(
            (pal["accent_hue"] + jitter) % 1.0,
            min(1.0, pal["sat"] + 0.2),
            min(1.0, pal["val"] + 0.3))
        # Third color: midpoint for gradients
        mid_rgb = tuple((k + a) / 2 for k, a in zip(key_rgb, accent_rgb))

        to_hex = lambda c: "#{:02x}{:02x}{:02x}".format(
            *(int(x * 255) for x in c))

        props = {
            NERDS.keyColor: Literal(to_hex(key_rgb)),
            NERDS.accentColor: Literal(to_hex(accent_rgb)),
            NERDS.midColor: Literal(to_hex(mid_rgb)),
            SCHEMA.genre: Literal(genre),
        }
        return [(NERDS.ColorPalette, props, Heat.HOT, 3)]


class TypefaceNerd(Nerd):
    """Picks a typeface, maybe influenced by genre."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        palette = bb.pick(NERDS.ColorPalette)
        genre = str(bb.get_property(palette, SCHEMA.genre)) if palette else "drama"
        preference = {
            "horror": "slab-heavy", "sci-fi": "mono-regular",
            "noir": "sans-light", "action": "serif-bold",
            "drama": "script-italic", "thriller": "sans-light",
            "romance": "script-italic", "fantasy": "serif-bold",
            "comedy": "sans-light", "adventure": "slab-heavy",
            "mystery": "mono-regular", "animation": "slab-heavy",
            "war": "serif-bold",
        }
        preferred = preference.get(genre)
        if preferred and random.random() < 0.6:
            face = next((f for f in TYPEFACES if f["name"] == preferred),
                        random.choice(TYPEFACES))
        else:
            face = random.choice(TYPEFACES)

        props = {
            NERDS.typefaceName: Literal(face["name"]),
            NERDS.typefaceStyle: Literal(face["style"]),
            NERDS.typefaceWeight: Literal(face["weight"]),
        }
        return [(NERDS.Typeface, props, Heat.MEDIUM, 2)]


class LayoutNerd(Nerd):
    """Picks a layout template."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        template = random.choice(LAYOUT_TEMPLATES)
        props = {
            NERDS.layoutName: Literal(template["name"]),
            NERDS.titleY: Literal(template["title_y"], datatype=XSD.float),
            NERDS.titleAlign: Literal(template["title_align"]),
            NERDS.imageY: Literal(template["image_y"], datatype=XSD.float),
            NERDS.imageH: Literal(template["image_h"], datatype=XSD.float),
            NERDS.taglineY: Literal(template["tagline_y"], datatype=XSD.float),
            NERDS.creditsY: Literal(template["credits_y"], datatype=XSD.float),
        }
        return [(NERDS.Layout, props, Heat.HOT, 4)]


class HeroImageNerd(Nerd):
    """Generates procedural color-field imagery for the poster body.

    Week 8 upgrade: more sophisticated shapes -- overlapping translucent
    rectangles, diagonal bars, and gradient-ready color specs.
    """

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has(NERDS.ColorPalette)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        palette = bb.pick(NERDS.ColorPalette)
        if not palette:
            return []
        key_hex = str(bb.get_property(palette, NERDS.keyColor))
        accent_hex = str(bb.get_property(palette, NERDS.accentColor))
        mid_hex = str(bb.get_property(palette, NERDS.midColor))

        num_blocks = random.randint(3, 7)
        # Serialize block data as a structured literal (JSON-ish)
        # Each block: x,y,w,h,color_hex,opacity
        blocks_data = []
        for i in range(num_blocks):
            color = random.choice([key_hex, accent_hex, mid_hex])
            # Vary the color slightly
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            r = max(0, min(255, r + random.randint(-25, 25)))
            g = max(0, min(255, g + random.randint(-25, 25)))
            b = max(0, min(255, b + random.randint(-25, 25)))
            varied = f"#{r:02x}{g:02x}{b:02x}"
            opacity = random.uniform(0.4, 1.0)
            blocks_data.append(
                f"{random.uniform(0.0, 0.5):.3f},"
                f"{random.uniform(0.0, 0.5):.3f},"
                f"{random.uniform(0.2, 1.0):.3f},"
                f"{random.uniform(0.15, 0.7):.3f},"
                f"{varied},{opacity:.2f}"
            )

        props = {
            NERDS.blockData: Literal(";".join(blocks_data)),
            NERDS.blockCount: Literal(num_blocks, datatype=XSD.integer),
        }
        return [(NERDS.HeroImage, props, Heat.HOT, 3)]


class IconNerd(Nerd):
    """Fetches a keyword-relevant icon from the Noun Project.

    Picks a Keywords item from the blackboard, selects a random subset of
    keywords as a search query, and searches the Noun Project API. If the
    search returns no results, retries up to 2 more times with different
    random keyword selections before giving up.
    """

    _MAX_RETRIES = 2

    def can_run(self, bb: Blackboard) -> bool:
        return (super().can_run(bb) and bb.has(NERDS.Keywords)
                and bb.has(NERDS.ColorPalette))

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        kw_item = bb.pick(NERDS.Keywords)
        palette = bb.pick(NERDS.ColorPalette)
        if not kw_item or not palette:
            return []

        kw_str = str(bb.get_property(kw_item, NERDS.keywordList) or "")
        keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
        if not keywords:
            return []

        accent_hex = str(bb.get_property(palette, NERDS.accentColor) or "#cc6644")

        # Try a random selection of keywords, retrying with different picks on failure
        for attempt in range(1 + self._MAX_RETRIES):
            n = min(len(keywords), random.randint(1, 3))
            selected = random.sample(keywords, n)
            term = " ".join(selected)
            print(f"  [IconNerd] Attempt {attempt + 1}: searching Noun Project for '{term}'...")
            icon_data = _fetch_icon(term, accent_hex)
            if icon_data:
                print(f"  [IconNerd] Got icon: '{icon_data['term']}' (id={icon_data['icon_id']})")
                props = {
                    NERDS.iconPngBase64: Literal(icon_data["png_base64"]),
                    NERDS.iconId: Literal(icon_data["icon_id"]),
                    NERDS.iconTerm: Literal(icon_data["term"]),
                    NERDS.iconAttribution: Literal(icon_data["attribution"]),
                    NERDS.iconSearchQuery: Literal(term),
                }
                return [(NERDS.IconImage, props, Heat.HOT, 4)]

        print(f"  [IconNerd] All {1 + self._MAX_RETRIES} attempts failed")
        return []


class GrainNerd(Nerd):
    """Decides on post-processing effects."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has(NERDS.HeroImage)

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        effects = []
        if random.random() < 0.7:
            effects.append("grain")
        if random.random() < 0.5:
            effects.append("vignette")
        if random.random() < 0.3:
            effects.append("posterize")
        if random.random() < 0.4:
            effects.append("chromatic_aberration")

        props = {
            NERDS.effects: Literal(",".join(effects)),
        }
        return [(NERDS.PostEffect, props, Heat.MEDIUM, 1)]


class CompositeNerd(Nerd):
    """Composites two blackboard images using ImageMagick's composite tool.

    Picks two image items (IconImage, HeroImage, or CompositeImage),
    materializes them to temp files, overlays one on the other at a
    random offset, and writes an XMP sidecar tracking where each source
    ended up in the result.  Sidecar integration is transitive: if a
    source was itself a composite, its entries are offset-adjusted and
    merged into the new sidecar.
    """

    _IMAGE_TYPES = [NERDS.IconImage, NERDS.HeroImage, NERDS.CompositeImage]

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        total = sum(len(bb.query_items(t)) for t in self._IMAGE_TYPES)
        return total >= 2

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        convert_cmd = _find_convert_cmd()
        if not convert_cmd:
            print("  [Compositor] ImageMagick not found, skipping")
            return []

        # Gather all image items across types
        all_images = []
        for t in self._IMAGE_TYPES:
            for item in bb.query_items(t):
                all_images.append((item, t))
        if len(all_images) < 2:
            return []

        # Pick two distinct images
        (base_item, base_type), (overlay_item, overlay_type) = \
            random.sample(all_images, 2)

        # Materialize both to temp PNG files
        temp_dir = Path("output") / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        base_path = _materialize_image(bb, base_item, temp_dir)
        overlay_path = _materialize_image(bb, overlay_item, temp_dir)
        if not base_path or not overlay_path:
            return []

        # Get source dimensions
        with Image.open(base_path) as bi:
            base_w, base_h = bi.size
        with Image.open(overlay_path) as oi:
            overlay_w, overlay_h = oi.size

        # Random offset: where overlay's top-left goes relative to base's
        # top-left.  Full range from no-overlap top-left to bottom-right.
        offset_x = random.randint(-overlay_w, base_w)
        offset_y = random.randint(-overlay_h, base_h)

        # Compute a canvas large enough to contain both images
        left = min(0, offset_x)
        top = min(0, offset_y)
        canvas_w = max(base_w, offset_x + overlay_w) - left
        canvas_h = max(base_h, offset_y + overlay_h) - top
        base_cx, base_cy = -left, -top
        overlay_cx = offset_x - left
        overlay_cy = offset_y - top

        result_path = temp_dir / f"composite_tick{bb.tick}_{bb._next_id}.png"
        cmd = convert_cmd + [
            "-size", f"{canvas_w}x{canvas_h}", "xc:none",
            str(base_path), "-geometry", f"+{base_cx}+{base_cy}", "-composite",
            str(overlay_path), "-geometry", f"+{overlay_cx}+{overlay_cy}",
            "-composite", str(result_path),
        ]
        print(f"  [Compositor] {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError) as e:
            print(f"  [Compositor] ImageMagick failed: {e}")
            return []

        if not result_path.exists():
            return []

        with Image.open(result_path) as ri:
            result_w, result_h = ri.size

        # Build XMP sidecar with transitive source tracking
        base_sidecar = _read_xmp_sidecar(base_path)
        overlay_sidecar = _read_xmp_sidecar(overlay_path)
        sources = _merge_xmp_sources(
            base_sidecar, base_item, base_type,
            base_cx, base_cy, base_w, base_h,
            overlay_sidecar, overlay_item, overlay_type,
            overlay_cx, overlay_cy, overlay_w, overlay_h,
        )
        xmp_path = result_path.with_suffix(".xmp")
        _write_xmp_sidecar(xmp_path, sources)

        print(f"  [Compositor] Result: {result_w}x{result_h}, "
              f"{len(sources)} sources tracked in XMP sidecar")

        props = {
            NERDS.compositeImagePath: Literal(str(result_path)),
            NERDS.compositeXmpPath: Literal(str(xmp_path)),
            NERDS.compositeWidth: Literal(result_w, datatype=XSD.integer),
            NERDS.compositeHeight: Literal(result_h, datatype=XSD.integer),
            NERDS.sourceItem1: base_item,
            NERDS.sourceItem2: overlay_item,
            NERDS.overlayOffsetX: Literal(offset_x, datatype=XSD.integer),
            NERDS.overlayOffsetY: Literal(offset_y, datatype=XSD.integer),
        }
        return [(NERDS.CompositeImage, props, Heat.HOT, 3)]


class VisibilityCriticNerd(Nerd):
    """Scores how well each source image is preserved in a composite.

    For each source in the XMP sidecar, materializes the original,
    extracts its region from the composite, and counts how many
    non-transparent source pixels match (within tolerance).
    Overall score = min per-source visibility.

    Low scores  -> composite heat set to COLD.
    High scores -> composite heat set to HOT.
    """

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        return len(_uncritiqued_composites(bb, NERDS.VisibilityCritique)) > 0

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        targets = _uncritiqued_composites(bb, NERDS.VisibilityCritique)
        if not targets:
            return []

        target = random.choice(targets)
        comp_path = str(bb.get_property(target, NERDS.compositeImagePath) or "")
        if not comp_path or not Path(comp_path).exists():
            return []

        comp_img = np.array(Image.open(comp_path).convert("RGBA"))
        sources = _read_xmp_sidecar(Path(comp_path))
        if not sources:
            return []

        temp_dir = Path("output") / "temp"
        per_source: list[float] = []
        score_strs: list[str] = []

        for entry in sources:
            src_uri = URIRef(entry.item_ref)
            src_path = _materialize_image(bb, src_uri, temp_dir)
            if not src_path:
                per_source.append(0.0)
                score_strs.append(f"{entry.item_type}:0.00")
                continue
            src_img = np.array(Image.open(src_path).convert("RGBA"))
            vis = _compute_source_visibility(
                comp_img, src_img, entry.x, entry.y)
            per_source.append(vis)
            score_strs.append(f"{entry.item_type}:{vis:.2f}")

        overall = min(per_source) if per_source else 0.0

        if overall < 0.2:
            bb.set_heat(target, Heat.COLD)
        elif overall >= 0.5:
            bb.set_heat(target, Heat.HOT)

        print(f"  [VisibilityCritic] scores={score_strs}, overall={overall:.2f}")

        props = {
            NERDS.critiquedItem: target,
            NERDS.visibilityScore: Literal(overall, datatype=XSD.float),
            NERDS.sourceScores: Literal(",".join(score_strs)),
            NERDS.critiqueTick: Literal(bb.tick, datatype=XSD.integer),
        }
        return [(NERDS.VisibilityCritique, props, Heat.MEDIUM, 1)]


class ContrastCriticNerd(Nerd):
    """Scores how distinguishable sources are from each other in a composite.

    Computes the mean RGB of each source's region in the composite,
    then measures the minimum pairwise Euclidean distance.  Low
    contrast means the sources blend into an indistinct muddle.

    Low scores  -> composite heat set to COLD.
    High scores -> composite heat set to HOT.
    """

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        return len(_uncritiqued_composites(bb, NERDS.ContrastCritique)) > 0

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        targets = _uncritiqued_composites(bb, NERDS.ContrastCritique)
        if not targets:
            return []

        target = random.choice(targets)
        comp_path = str(bb.get_property(target, NERDS.compositeImagePath) or "")
        if not comp_path or not Path(comp_path).exists():
            return []

        comp_img = np.array(Image.open(comp_path).convert("RGB"))
        sources = _read_xmp_sidecar(Path(comp_path))
        if len(sources) < 2:
            return []

        colors: list[np.ndarray] = []
        for src in sources:
            mean_rgb = _region_mean_color(
                comp_img, src.x, src.y, src.width, src.height)
            if mean_rgb is not None:
                colors.append(mean_rgb)

        if len(colors) < 2:
            overall = 1.0
            min_dist = -1.0
        else:
            min_dist = float("inf")
            for i in range(len(colors)):
                for j in range(i + 1, len(colors)):
                    d = float(np.sqrt(np.sum((colors[i] - colors[j]) ** 2)))
                    min_dist = min(min_dist, d)
            overall = min(1.0, min_dist / 200.0)

        if overall < 0.15:
            bb.set_heat(target, Heat.COLD)
        elif overall >= 0.4:
            bb.set_heat(target, Heat.HOT)

        print(f"  [ContrastCritic] min_dist={min_dist:.1f}, score={overall:.2f}")

        props = {
            NERDS.critiquedItem: target,
            NERDS.contrastScore: Literal(overall, datatype=XSD.float),
            NERDS.minPairwiseDistance: Literal(min_dist, datatype=XSD.float),
            NERDS.critiqueTick: Literal(bb.tick, datatype=XSD.integer),
        }
        return [(NERDS.ContrastCritique, props, Heat.MEDIUM, 1)]


class CritiqueNerd(Nerd):
    """Evaluates completeness of the poster."""

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb) or bb.tick <= 3:
            return False
        # Only run if new (non-meta) material has appeared since our last critique
        last = _latest_tick_of(bb, NERDS.Critique)
        return bb.newest_item_tick(exclude_types=_META_TYPES) > last

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        checks = [
            (NERDS.TitleChunks, "missing_title"),
            (NERDS.ColorPalette, "missing_palette"),
            (NERDS.Layout, "missing_layout"),
            (NERDS.HeroImage, "missing_hero"),
            (NERDS.Typeface, "missing_typeface"),
            (NERDS.IconImage, "missing_icon"),
        ]

        # Fingerprint = sorted set of present types
        present = sorted(str(c) for c, _ in checks if bb.has(c))
        fingerprint = _input_fingerprint(
            [URIRef(t) for t in present])
        if bb.has_fingerprint(NERDS.Critique, fingerprint):
            return []

        issues = [issue for concept, issue in checks
                  if not bb.has(concept)]
        total = len(checks)
        score = (total - len(issues)) / total

        props = {
            NERDS.inputFingerprint: Literal(fingerprint),
            NERDS.issues: Literal(",".join(issues) if issues else "none"),
            NERDS.completeness: Literal(score, datatype=XSD.float),
            NERDS.critiqueTick: Literal(bb.tick, datatype=XSD.integer),
        }
        return [(NERDS.Critique, props, Heat.MEDIUM, 1)]


def _latest_tick_of(bb: Blackboard, type_concept: URIRef) -> int:
    """Return the creation tick of the newest item of *type_concept*, or -1."""
    items = bb.query_items(type_concept)
    if not items:
        return -1
    return max(int(bb.get_property(i, DCTERMS.created) or 0) for i in items)


class PosterCriticNerd(Nerd):
    """Renders a temporary poster from a specific set of picked assets
    and produces a visual critique.

    For now the critique is always "passes" -- the actual evaluation
    logic will be added later.  The nerd records which combination of
    assets it used (via an input fingerprint) so it never critiques
    the same combination twice.
    """

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        if not (bb.has(NERDS.MovieData) and bb.has(NERDS.TitleChunks)
                and bb.has(NERDS.ColorPalette)):
            return False
        last = _latest_tick_of(bb, NERDS.PosterCritique)
        return bb.newest_item_tick(exclude_types=_META_TYPES) > last

    # Maps render pick keys to RDF properties stored on the critique
    _PICK_PROPS = [
        ('movie',   NERDS.usedMovie),
        ('title',   NERDS.usedTitle),
        ('palette', NERDS.usedPalette),
        ('layout',  NERDS.usedLayout),
        ('hero',    NERDS.usedHero),
        ('typeface', NERDS.usedTypeface),
        ('effect',  NERDS.usedEffect),
        ('icon',    NERDS.usedIcon),
        ('composite', NERDS.usedComposite),
    ]

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        # Pick a specific set of assets (heat-weighted)
        picks = {
            'movie':    bb.pick(NERDS.MovieData),
            'title':    bb.pick(NERDS.TitleChunks),
            'palette':  bb.pick(NERDS.ColorPalette),
            'layout':   bb.pick(NERDS.Layout),
            'hero':     bb.pick(NERDS.HeroImage),
            'typeface': bb.pick(NERDS.Typeface),
            'effect':   bb.pick(NERDS.PostEffect),
            'icon':     bb.pick(NERDS.IconImage),
            'composite': bb.pick(NERDS.CompositeImage),
        }

        fingerprint = _input_fingerprint(list(picks.values()))
        if bb.has_fingerprint(NERDS.PosterCritique, fingerprint):
            return []

        # Render a temporary poster from exactly these assets
        temp_dir = Path("output") / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"temp_poster_tick{bb.tick}.png"
        render_poster(bb, temp_path, picks=picks)

        props = {
            NERDS.inputFingerprint: Literal(fingerprint),
            NERDS.passes: Literal(True, datatype=XSD.boolean),
            NERDS.posterImage: Literal(str(temp_path)),
            NERDS.critiqueTick: Literal(bb.tick, datatype=XSD.integer),
        }
        # Record exactly which items were used so the final render
        # can reproduce an approved poster.
        for key, pred in self._PICK_PROPS:
            if picks.get(key) is not None:
                props[pred] = picks[key]

        return [(NERDS.PosterCritique, props, Heat.MEDIUM, 1)]


@dataclass
class CompletionNerd(Nerd):
    """Declares the poster complete when critique score is high enough."""

    min_tick: int = 0

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        if bb.tick < self.min_tick:
            return False
        critiques = bb.query_items(NERDS.Critique)
        if not critiques:
            return False
        # Check the latest critique's completeness
        latest = max(critiques,
                     key=lambda c: int(bb.get_property(c, NERDS.critiqueTick) or 0))
        score = float(bb.get_property(latest, NERDS.completeness) or 0)
        return score >= 0.8

    def run(self, bb: Blackboard) -> list[tuple[URIRef, dict, Heat, int]]:
        props = {
            NERDS.declared: Literal(True, datatype=XSD.boolean),
        }
        return [(NERDS.Completion, props, Heat.HOT, 10)]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def make_all_nerds() -> list[Nerd]:
    """Create the full roster of nerds with SHACL shape links."""
    return [
        MoviePickerNerd(name="MoviePicker", heat=Heat.HOT, cooldown_rate=99,
                        shacl_shape=NERDS.MoviePickerShape),
        TitleParserNerd(name="TitleParser", heat=Heat.MEDIUM, cooldown_rate=3,
                        shacl_shape=NERDS.TitleParserShape),
        KeywordNerd(name="KeywordExtractor", heat=Heat.HOT, cooldown_rate=99,
                    shacl_shape=NERDS.KeywordShape),
        GenrePaletteNerd(name="GenrePalette", heat=Heat.MEDIUM, cooldown_rate=3,
                         shacl_shape=NERDS.GenrePaletteShape),
        TypefaceNerd(name="TypefacePicker", heat=Heat.MEDIUM, cooldown_rate=4,
                     shacl_shape=NERDS.TypefaceShape),
        LayoutNerd(name="LayoutPicker", heat=Heat.MEDIUM, cooldown_rate=3,
                   shacl_shape=NERDS.LayoutShape),
        HeroImageNerd(name="HeroImageGen", heat=Heat.MEDIUM, cooldown_rate=5,
                      shacl_shape=NERDS.HeroImageShape),
        IconNerd(name="IconFetcher", heat=Heat.HOT, cooldown_rate=5,
                 shacl_shape=NERDS.IconShape),
        GrainNerd(name="GrainEffect", heat=Heat.MEDIUM, cooldown_rate=5,
                  shacl_shape=NERDS.GrainShape),
        CompositeNerd(name="Compositor", heat=Heat.MEDIUM, cooldown_rate=4,
                      shacl_shape=NERDS.CompositeShape),
        VisibilityCriticNerd(name="VisibilityCritic", heat=Heat.MEDIUM,
                             cooldown_rate=2,
                             shacl_shape=NERDS.VisibilityCritiqueShape),
        ContrastCriticNerd(name="ContrastCritic", heat=Heat.MEDIUM,
                           cooldown_rate=2,
                           shacl_shape=NERDS.ContrastCritiqueShape),
        CritiqueNerd(name="Critic", heat=Heat.HOT, cooldown_rate=2,
                     shacl_shape=NERDS.CritiqueShape),
        PosterCriticNerd(name="PosterCritic", heat=Heat.MEDIUM, cooldown_rate=3,
                         shacl_shape=NERDS.PosterCriticShape),
        CompletionNerd(name="CompletionJudge", heat=Heat.HOT, cooldown_rate=1,
                       shacl_shape=NERDS.CompletionShape, min_tick=30),
    ]
