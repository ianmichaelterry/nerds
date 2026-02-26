import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from blackboard import Blackboard, Item, Heat
from nerds import Nerd

import random
import colorsys

# ---------------------------------------------------------------------------
# Heuristic lookup tables (evidence cited per entry)
# ---------------------------------------------------------------------------

GENRE_PALETTES = {
    # Evidence: Both winning trajectories converged on near-black background,
    # orange-red primary, cyan secondary, warm ivory text for neo-noir sci-fi
    "sci-fi/neo-noir": {
        "background":       "#0A0A12",
        "primary_accent":   "#E8430A",
        "secondary_accent": "#1ECBE1",
        "tertiary_accent":  "#C47FD5",
        "text_primary":     "#E8E0D0",
        "text_secondary":   "#8899AA",
        "neon_glow":        "#E8430A",
        "fog_mid":          "#1A1A2E",
    },
    # Evidence: General thriller/noir tends toward desaturated blue-green shadows,
    # amber practical lights, off-white title text
    "thriller/noir": {
        "background":       "#0D0D0D",
        "primary_accent":   "#D4870A",
        "secondary_accent": "#2A4A5A",
        "tertiary_accent":  "#8A7A6A",
        "text_primary":     "#F0EAD6",
        "text_secondary":   "#7A8A8A",
        "neon_glow":        "#D4870A",
        "fog_mid":          "#1A1A1A",
    },
    # Evidence: Horror palette gravitates to desaturated crimson, deep shadow,
    # sickly green accent from practical genre convention
    "horror": {
        "background":       "#080808",
        "primary_accent":   "#8B0000",
        "secondary_accent": "#2E4D2E",
        "tertiary_accent":  "#4A3A2A",
        "text_primary":     "#D8D0C0",
        "text_secondary":   "#6A6A6A",
        "neon_glow":        "#8B0000",
        "fog_mid":          "#181010",
    },
    # Evidence: Action posters favor high-contrast orange/blue split complementary
    # scheme derived from blockbuster theatrical convention
    "action": {
        "background":       "#0A0A0A",
        "primary_accent":   "#FF6A00",
        "secondary_accent": "#005FFF",
        "tertiary_accent":  "#C8C820",
        "text_primary":     "#FFFFFF",
        "text_secondary":   "#AAAAAA",
        "neon_glow":        "#FF6A00",
        "fog_mid":          "#1A1A1A",
    },
    # Fallback generic palette
    "default": {
        "background":       "#0A0A12",
        "primary_accent":   "#E8430A",
        "secondary_accent": "#1ECBE1",
        "tertiary_accent":  "#C47FD5",
        "text_primary":     "#E8E0D0",
        "text_secondary":   "#8899AA",
        "neon_glow":        "#E8430A",
        "fog_mid":          "#1A1A2E",
    },
}

TYPEFACES = {
    # Evidence: Both winning trajectories independently chose Eurostile Extended Bold
    # for title and Futura/Helvetica for tagline+credits in sci-fi/neo-noir/1982
    "sci-fi/neo-noir": {
        "title_face":    "Eurostile Extended Bold",
        "tagline_face":  "Futura PT Light",
        "credit_face":   "Futura PT Book",
        "fallback_title": "Arial Black, sans-serif",
        "title_tracking": "0.12em",
        "tagline_tracking": "0.20em",
        "credit_tracking":  "0.15em",
    },
    # Evidence: Thriller/noir convention uses condensed grotesque for impact titles,
    # thin sans for atmospheric tagline
    "thriller/noir": {
        "title_face":    "Trade Gothic Bold Condensed",
        "tagline_face":  "Helvetica Neue Light",
        "credit_face":   "Helvetica Neue Regular",
        "fallback_title": "Impact, sans-serif",
        "title_tracking": "0.08em",
        "tagline_tracking": "0.18em",
        "credit_tracking":  "0.12em",
    },
    # Evidence: Horror titles favor distressed serif or condensed display faces
    "horror": {
        "title_face":    "Trajan Pro Bold",
        "tagline_face":  "Garamond Italic",
        "credit_face":   "Helvetica Neue Regular",
        "fallback_title": "Georgia, serif",
        "title_tracking": "0.10em",
        "tagline_tracking": "0.15em",
        "credit_tracking":  "0.10em",
    },
    # Evidence: Action posters use broad impact-weight sans for maximum legibility
    "action": {
        "title_face":    "Impact",
        "tagline_face":  "Helvetica Neue Condensed Bold",
        "credit_face":   "Helvetica Neue Regular",
        "fallback_title": "Impact, sans-serif",
        "title_tracking": "0.05em",
        "tagline_tracking": "0.12em",
        "credit_tracking":  "0.10em",
    },
    "default": {
        "title_face":    "Eurostile Extended Bold",
        "tagline_face":  "Futura PT Light",
        "credit_face":   "Futura PT Book",
        "fallback_title": "Arial Black, sans-serif",
        "title_tracking": "0.12em",
        "tagline_tracking": "0.20em",
        "credit_tracking":  "0.15em",
    },
}

TITLE_STACKING = {
    # Evidence: Both winners split BLADE / RUNNER onto two stacked lines of
    # identical weight creating a monolithic anchor column
    "two-word/sci-fi": {
        "strategy": "vertical_stacked_equal_weight",
        "primary_size_relative":   "hero",
        "secondary_size_relative": "hero",
        "tagline_position":  "below_title_block",
        "credit_position":   "bottom_strip",
    },
    # Evidence: Single-word titles favor full-width centered treatment
    "one-word": {
        "strategy": "centered",
        "primary_size_relative":   "hero",
        "secondary_size_relative": "hero",
        "tagline_position":  "below_title_block",
        "credit_position":   "bottom_strip",
    },
    # Evidence: Three-or-more-word titles use flush-left vertical stack with
    # descending size to create diagonal visual motion
    "multi-word": {
        "strategy": "vertical_flush_left",
        "primary_size_relative":   "hero",
        "secondary_size_relative": "large",
        "tagline_position":  "below_title_block",
        "credit_position":   "bottom_strip",
    },
    "default": {
        "strategy": "centered",
        "primary_size_relative":   "hero",
        "secondary_size_relative": "large",
        "tagline_position":  "below_title_block",
        "credit_position":   "bottom_strip",
    },
}

MOOD_TO_ATMOSPHERE = {
    # Evidence: Both winners include rain-soaked, neon, urban-decay in mood_keywords
    # and reference Los Angeles 2019 streetscapes
    "dystopian/rain-soaked/neon": {
        "weather": "rain",
        "neon_sources": ["street signage", "searchlights", "reflections in wet pavement"],
        "depth_of_field": "shallow",
        "film_grain": True,
    },
    # Evidence: Fog/smog variants appear in noir and dystopian subgenres
    "fog/smog/decay": {
        "weather": "fog",
        "neon_sources": ["distant streetlamps", "neon bar signs", "vehicle headlights"],
        "depth_of_field": "medium",
        "film_grain": True,
    },
    # Evidence: Action posters often use clear dramatic skies with pyrotechnic lighting
    "explosive/kinetic/daylight": {
        "weather": "clear",
        "neon_sources": ["explosion light", "muzzle flash"],
        "depth_of_field": "deep",
        "film_grain": False,
    },
    "default": {
        "weather": "rain",
        "neon_sources": ["street signage", "neon glow"],
        "depth_of_field": "shallow",
        "film_grain": True,
    },
}

CREDITS_FORMAT = {
    # Evidence: Both winners format credits as uppercase bottom strip with
    # period/dot separators in theatrical style
    "sci-fi/theatrical": {
        "director_template": "A {director} FILM",
        "cast_separator":    "  ·  ",
        "studio_template":   "WARNER BROS. · {year}",
        "position":          "bottom_strip",
        "case":              "upper",
    },
    "default": {
        "director_template": "A {director} FILM",
        "cast_separator":    "  ·  ",
        "studio_template":   "{year}",
        "position":          "bottom_strip",
        "case":              "upper",
    },
}

TEXT_GLOW = {
    # Evidence: Both winners apply orange-red glow shadow to title text matching
    # primary_accent; multi-layer CSS glow with outer diffuse at ~25% opacity
    "neo-noir/neon-text": {
        "glow_template": "0 0 18px {primary_accent}, 0 0 40px {primary_accent}44",
    },
    "default": {
        "glow_template": "0 0 12px {primary_accent}, 0 0 30px {primary_accent}44",
    },
}

COMPOSITION_ZONES = {
    # Evidence: Neo-noir posters anchor figure left-of-center with title tower
    # occupying right third; deep cityscape fills background
    "sci-fi/neo-noir": {
        "layout_structure": "hero-left / title-right / cityscape-background",
        "focal_point":      "lone figure in foreground rain-slicked street",
        "title_zone":       "upper-right third, flush right margin",
        "image_zone":       "left two-thirds, full bleed",
        "depth_layers":     ["foreground: rain-slicked figure", "midground: neon-lit cityscape", "background: smog-diffused skyline"],
    },
    "default": {
        "layout_structure": "hero-center / title-top / environment-background",
        "focal_point":      "central figure or object",
        "title_zone":       "upper third, centered",
        "image_zone":       "center full bleed",
        "depth_layers":     ["foreground: primary subject", "midground: environment", "background: sky/atmosphere"],
    },
}

GENRE_IMAGERY = {
    # Evidence: Blade Runner-lineage sci-fi posters feature lone detective/warrior
    # figure, rain-slicked urban canyon, replicant/android key prop
    "sci-fi/neo-noir": {
        "hero_archetypes":  ["lone detective", "fugitive", "android hunter"],
        "environments":     ["rain-slicked urban canyon", "neon-lit alley", "dystopian megacity street"],
        "key_props":        ["blaster pistol", "trench coat", "rain reflections", "neon signage", "flying vehicles"],
        "atmosphere_fx":    ["rain", "neon bloom", "lens flare", "steam vents", "smog haze"],
        "lighting":         "hard side-light from neon source, low angle",
    },
    "default": {
        "hero_archetypes":  ["protagonist"],
        "environments":     ["dramatic environment"],
        "key_props":        ["genre-appropriate prop"],
        "atmosphere_fx":    ["atmospheric haze"],
        "lighting":         "dramatic three-quarter front lighting",
    },
}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _palette_key(genre: str, subgenre: str) -> str:
    combined = f"{genre}/{subgenre}".lower()
    for k in GENRE_PALETTES:
        if k != "default" and all(part in combined for part in k.split("/")):
            return k
    return "default"

def _typeface_key(genre: str, subgenre: str) -> str:
    combined = f"{genre}/{subgenre}".lower()
    for k in TYPEFACES:
        if k != "default" and all(part in combined for part in k.split("/")):
            return k
    return "default"

def _mood_atm_key(mood_keywords: list) -> str:
    mood_str = "/".join(mood_keywords).lower()
    for k in MOOD_TO_ATMOSPHERE:
        if k == "default":
            continue
        parts = k.split("/")
        if sum(1 for p in parts if p in mood_str) >= 2:
            return k
    return "default"

def _glow_css(primary_accent: str) -> str:
    template = TEXT_GLOW.get("neo-noir/neon-text", TEXT_GLOW["default"])["glow_template"]
    return template.replace("{primary_accent}", primary_accent)

def _credits_string(director: str, actors: list, year: int, genre: str) -> str:
    key = "sci-fi/theatrical" if "sci-fi" in genre.lower() else "default"
    fmt = CREDITS_FORMAT.get(key, CREDITS_FORMAT["default"])
    sep = fmt["cast_separator"]
    cast = sep.join(a.upper() for a in actors[:3])
    director_line = fmt["director_template"].format(director=director.upper())
    studio_line   = fmt["studio_template"].format(year=year)
    return f"{director_line}    {cast}    {studio_line}"


# ---------------------------------------------------------------------------
# Specialist Nerds
# ---------------------------------------------------------------------------

class MoviePicker(Nerd):
    """Enriches raw BRIEF into a full MovieSeed with subgenre + mood_keywords."""

    def can_run(self, bb):
        return bb.has("BRIEF") and not bb.has("MovieSeed")

    def run(self, bb):
        brief = bb.pick("BRIEF").value
        genre    = brief.get("genre", "sci-fi")
        subgenre = brief.get("subgenre", "neo-noir")
        mood_kws = brief.get("mood_keywords") or [
            random.choice(["dystopian", "rain-soaked", "melancholy", "tense"]),
            random.choice(["neon", "fog", "smog", "shadow"]),
            random.choice(["urban-decay", "isolation", "paranoia", "longing"]),
            random.choice(["cinematic", "noir", "moody", "electric"]),
        ]
        seed = {
            "title":         brief.get("title", "Untitled"),
            "genre":         genre,
            "subgenre":      subgenre,
            "year":          brief.get("year", 1982),
            "director":      brief.get("director", "Unknown Director"),
            "tagline":       brief.get("tagline", ""),
            "actors":        brief.get("actors", []),
            "mood_keywords": mood_kws,
        }
        return [Item(type_tag="MovieSeed", value=seed, heat=Heat.HOT, thermal_mass=5)]


class GenrePalette(Nerd):
    """Maps genre+subgenre through GENRE_PALETTES; writes ColorPalette."""

    def can_run(self, bb):
        return bb.has("MovieSeed") and not bb.has("ColorPalette")

    def run(self, bb):
        seed  = bb.pick("MovieSeed").value
        key   = _palette_key(seed["genre"], seed["subgenre"])
        pal   = dict(GENRE_PALETTES[key])
        mood  = " / ".join(seed["mood_keywords"])
        pal["name"] = f"{seed['subgenre'].title()} Night — {mood}"
        pal["rationale_note"] = (
            f"Palette '{key}' selected for {seed['genre']}/{seed['subgenre']}. "
            f"Near-black base ({pal['background']}) with {pal['primary_accent']} "
            f"primary neon accent evokes {mood}."
        )
        pal["heat"] = "HOT"
        return [Item(type_tag="ColorPalette", value=pal, heat=Heat.HOT, thermal_mass=5)]


class TitleParser(Nerd):
    """Splits title words, formats stacking strategy and credit block."""

    def can_run(self, bb):
        return bb.has("MovieSeed") and not bb.has("TitleLayout")

    def run(self, bb):
        seed   = bb.pick("MovieSeed").value
        words  = seed["title"].upper().split()
        genre  = seed["genre"].lower()
        n      = len(words)
        if n == 1:
            stack_key = "one-word"
        elif n == 2 and "sci-fi" in genre:
            stack_key = "two-word/sci-fi"
        elif n >= 3:
            stack_key = "multi-word"
        else:
            stack_key = "default"
        stk = TITLE_STACKING.get(stack_key, TITLE_STACKING["default"])
        layout = {
            "primary_word":            words[0],
            "secondary_word":          words[1] if n > 1 else "",
            "stacking":                stk["strategy"],
            "primary_size_relative":   stk["primary_size_relative"],
            "secondary_size_relative": stk["secondary_size_relative"],
            "tagline_text":            seed["tagline"].upper(),
            "tagline_position":        stk["tagline_position"],
            "credit_block":            _credits_string(seed["director"], seed["actors"], seed["year"], genre),
            "credit_position":         stk["credit_position"],
        }
        return [Item(type_tag="TitleLayout", value=layout, heat=Heat.HOT, thermal_mass=4)]


class TypefacePicker(Nerd):
    """Applies TYPEFACES lookup; derives glow CSS from primary_accent."""

    def can_run(self, bb):
        return (bb.has("MovieSeed") and bb.has("ColorPalette")
                and bb.has("TitleLayout") and not bb.has("TypefaceSpec"))

    def run(self, bb):
        seed  = bb.pick("MovieSeed").value
        pal   = bb.pick("ColorPalette").value
        key   = _typeface_key(seed["genre"], seed["subgenre"])
        tf    = TYPEFACES.get(key, TYPEFACES["default"])
        glow  = _glow_css(pal["primary_accent"])
        spec = {
            "title_face":          tf["title_face"],
            "title_tracking":      tf["title_tracking"],
            "title_color":         pal["text_primary"],
            "title_glow_shadow":   glow,
            "tagline_face":        tf["tagline_face"],
            "tagline_tracking":    tf["tagline_tracking"],
            "tagline_color":       pal["secondary_accent"],
            "tagline_size_relative": "small",
            "credit_face":         tf["credit_face"],
            "credit_tracking":     tf["credit_tracking"],
            "credit_color":        pal["text_secondary"],
            "credit_size_relative": "tiny",
            "fallback_title":      tf["fallback_title"],
        }
        return [Item(type_tag="TypefaceSpec", value=spec, heat=Heat.HOT, thermal_mass=4)]


class CompositionPlanner(Nerd):
    """Divides canvas into named zones; specifies depth layers."""

    def can_run(self, bb):
        return (bb.has("MovieSeed") and bb.has("TitleLayout")
                and bb.has("ColorPalette") and not bb.has("CompositionPlan"))

    def run(self, bb):
        seed  = bb.pick("MovieSeed").value
        key   = _palette_key(seed["genre"], seed["subgenre"])
        zone_key = key if key in COMPOSITION_ZONES else "default"
        z     = COMPOSITION_ZONES[zone_key]
        plan  = {
            "layout_structure": z["layout_structure"],
            "focal_point":      z["focal_point"],
            "title_zone":       z["title_zone"],
            "image_zone":       z["image_zone"],
            "depth_layers":     list(z["depth_layers"]),
        }
        return [Item(type_tag="CompositionPlan", value=plan, heat=Heat.MEDIUM, thermal_mass=3)]


class ImageryDirector(Nerd):
    """Selects hero subject, environment, key props, atmosphere_fx."""

    def can_run(self, bb):
        return (bb.has("MovieSeed") and bb.has("ColorPalette")
                and bb.has("CompositionPlan") and not bb.has("ImagerySpec"))

    def run(self, bb):
        seed   = bb.pick("MovieSeed").value
        key    = _palette_key(seed["genre"], seed["subgenre"])
        img_k  = key if key in GENRE_IMAGERY else "default"
        img    = GENRE_IMAGERY[img_k]
        actors = seed.get("actors", [])
        hero   = actors[0] if actors else random.choice(img["hero_archetypes"])
        spec   = {
            "hero_subject":   f"{hero} as {random.choice(img['hero_archetypes'])}",
            "environment":    random.choice(img["environments"]),
            "lighting_direction": img["lighting"],
            "key_props":      random.sample(img["key_props"], min(3, len(img["key_props"]))),
            "atmosphere_fx":  random.sample(img["atmosphere_fx"], min(3, len(img["atmosphere_fx"]))),
        }
        return [Item(type_tag="ImagerySpec", value=spec, heat=Heat.MEDIUM, thermal_mass=3)]


class AtmosphereDesigner(Nerd):
    """Translates mood_keywords into weather, neon_sources, DOF, film_grain."""

    def can_run(self, bb):
        return (bb.has("MovieSeed") and bb.has("ColorPalette")
                and bb.has("ImagerySpec") and not bb.has("AtmosphereSpec"))

    def run(self, bb):
        seed  = bb.pick("MovieSeed").value
        pal   = bb.pick("ColorPalette").value
        mood  = seed.get("mood_keywords", [])
        key   = _mood_atm_key(mood)
        atm   = dict(MOOD_TO_ATMOSPHERE.get(key, MOOD_TO_ATMOSPHERE["default"]))
        # Enrich neon_sources with palette's primary_accent color note
        atm["neon_sources"] = list(atm["neon_sources"]) + [
            f"neon glow ({pal['primary_accent']})"
        ]
        spec  = {
            "weather":        atm["weather"],
            "neon_sources":   atm["neon_sources"],
            "depth_of_field": atm["depth_of_field"],
            "film_grain":     atm["film_grain"],
        }
        return [Item(type_tag="AtmosphereSpec", value=spec, heat=Heat.COLD, thermal_mass=2)]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_all_nerds():
    return [
        MoviePicker(name="MoviePicker",         heat=Heat.HOT,    cooldown_rate=1),
        GenrePalette(name="GenrePalette",        heat=Heat.HOT,    cooldown_rate=2),
        TitleParser(name="TitleParser",          heat=Heat.HOT,    cooldown_rate=2),
        TypefacePicker(name="TypefacePicker",    heat=Heat.HOT,    cooldown_rate=2),
        CompositionPlanner(name="CompositionPlanner", heat=Heat.MEDIUM, cooldown_rate=3),
        ImageryDirector(name="ImageryDirector",  heat=Heat.MEDIUM, cooldown_rate=3),
        AtmosphereDesigner(name="AtmosphereDesigner", heat=Heat.COLD,   cooldown_rate=3),
    ]
