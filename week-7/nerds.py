"""
Nerds: the expert operators that read from and write to the blackboard.

Each Nerd has:
- A name
- A heat level (for selection weighting)
- A cooldown counter
- A call() method that inspects the blackboard and maybe writes new items

Nerds are deliberately dumb. No LLM. No planning. Just typed lookup,
random choice within constraints, and deterministic transforms.
This is the caricature's core exaggeration.
"""

from __future__ import annotations
import random
import colorsys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from blackboard import Blackboard, Item, Heat

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Movie databases (hardcoded -- an oversimplification to be overlooked)
# ---------------------------------------------------------------------------

MOVIES = [
    {
        "title": "Blade Runner",
        "tagline": "Man has made his match... now it's his problem.",
        "genre": "sci-fi",
        "year": 1982,
        "director": "Ridley Scott",
        "actors": ["Harrison Ford", "Rutger Hauer", "Sean Young"],
    },
    {
        "title": "The Shining",
        "tagline": "A masterpiece of modern horror.",
        "genre": "horror",
        "year": 1980,
        "director": "Stanley Kubrick",
        "actors": ["Jack Nicholson", "Shelley Duvall"],
    },
    {
        "title": "Drive",
        "tagline": "There are no clean getaways.",
        "genre": "noir",
        "year": 2011,
        "director": "Nicolas Winding Refn",
        "actors": ["Ryan Gosling", "Carey Mulligan", "Bryan Cranston"],
    },
    {
        "title": "Moonlight",
        "tagline": "This is the story of a lifetime.",
        "genre": "drama",
        "year": 2016,
        "director": "Barry Jenkins",
        "actors": ["Trevante Rhodes", "Andre Holland", "Janelle Monae"],
    },
    {
        "title": "Mad Max: Fury Road",
        "tagline": "What a lovely day.",
        "genre": "action",
        "year": 2015,
        "director": "George Miller",
        "actors": ["Tom Hardy", "Charlize Theron"],
    },
]

# Genre -> color mood associations (hue in 0-1, saturation, value)
GENRE_PALETTES = {
    "sci-fi":  {"key_hue": 0.58, "accent_hue": 0.10, "sat": 0.7, "val": 0.3},
    "horror":  {"key_hue": 0.0,  "accent_hue": 0.0,  "sat": 0.6, "val": 0.15},
    "noir":    {"key_hue": 0.75, "accent_hue": 0.08, "sat": 0.5, "val": 0.2},
    "drama":   {"key_hue": 0.55, "accent_hue": 0.45, "sat": 0.4, "val": 0.35},
    "action":  {"key_hue": 0.08, "accent_hue": 0.12, "sat": 0.9, "val": 0.4},
}

TYPEFACES = [
    {"name": "serif-bold", "style": "serif", "weight": "bold"},
    {"name": "sans-light", "style": "sans", "weight": "light"},
    {"name": "slab-heavy", "style": "slab", "weight": "heavy"},
    {"name": "mono-regular", "style": "mono", "weight": "regular"},
    {"name": "script-italic", "style": "script", "weight": "italic"},
]

LAYOUT_TEMPLATES = [
    {
        "name": "classic-centered",
        "title_y": 0.10, "title_align": "center",
        "image_y": 0.20, "image_h": 0.50,
        "tagline_y": 0.75, "credits_y": 0.88,
    },
    {
        "name": "bottom-heavy",
        "title_y": 0.60, "title_align": "center",
        "image_y": 0.0, "image_h": 0.55,
        "tagline_y": 0.78, "credits_y": 0.90,
    },
    {
        "name": "split-diagonal",
        "title_y": 0.05, "title_align": "left",
        "image_y": 0.15, "image_h": 0.45,
        "tagline_y": 0.65, "credits_y": 0.85,
    },
    {
        "name": "minimalist",
        "title_y": 0.40, "title_align": "center",
        "image_y": 0.0, "image_h": 0.35,
        "tagline_y": 0.55, "credits_y": 0.92,
    },
]


# ---------------------------------------------------------------------------
# Base Nerd
# ---------------------------------------------------------------------------

@dataclass
class Nerd:
    """Base class for all nerds."""
    name: str
    heat: Heat = Heat.MEDIUM
    cooldown: int = 0
    cooldown_rate: int = 2  # ticks to cool down after being called

    def can_run(self, bb: Blackboard) -> bool:
        """Override to check if preconditions on the blackboard are met."""
        return self.cooldown == 0

    def run(self, bb: Blackboard) -> list[Item]:
        """Do the work. Return new items to be added."""
        raise NotImplementedError

    def call(self, bb: Blackboard) -> list[Item]:
        """Called by the scheduler. Runs the nerd and manages cooldown."""
        results = self.run(bb)
        self.cooldown = self.cooldown_rate
        return results

    def tick(self):
        """Reduce cooldown each tick."""
        if self.cooldown > 0:
            self.cooldown -= 1


# ---------------------------------------------------------------------------
# Concrete Nerds
# ---------------------------------------------------------------------------

class MoviePickerNerd(Nerd):
    """Picks a movie from the database and seeds the blackboard."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and not bb.has("MovieData")

    def run(self, bb: Blackboard) -> list[Item]:
        movie = random.choice(MOVIES)
        return [Item("MovieData", movie, Heat.HOT, thermal_mass=5)]


class TitleParserNerd(Nerd):
    """Splits the movie title into primary/secondary chunks."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has("MovieData") and not bb.has("TitleChunks")

    def run(self, bb: Blackboard) -> list[Item]:
        movie = bb.pick("MovieData")
        if not movie:
            return []
        title = movie.value["title"]
        parts = title.split(":", 1) if ":" in title else title.split(" ", 1)
        primary = parts[0].strip()
        secondary = parts[1].strip() if len(parts) > 1 else ""
        return [Item("TitleChunks", {"primary": primary, "secondary": secondary},
                      Heat.HOT, thermal_mass=3)]


class GenrePaletteNerd(Nerd):
    """Generates a color palette based on genre mood associations."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has("MovieData") and not bb.has("ColorPalette")

    def run(self, bb: Blackboard) -> list[Item]:
        movie = bb.pick("MovieData")
        if not movie:
            return []
        genre = movie.value.get("genre", "drama")
        pal = GENRE_PALETTES.get(genre, GENRE_PALETTES["drama"])
        # Add some randomness -- caricature: genre = color destiny
        jitter = random.uniform(-0.05, 0.05)
        key_rgb = colorsys.hsv_to_rgb(
            (pal["key_hue"] + jitter) % 1.0, pal["sat"], pal["val"])
        accent_rgb = colorsys.hsv_to_rgb(
            (pal["accent_hue"] + jitter) % 1.0,
            min(1.0, pal["sat"] + 0.2),
            min(1.0, pal["val"] + 0.3))
        to255 = lambda c: tuple(int(x * 255) for x in c)
        return [Item("ColorPalette", {
            "key": to255(key_rgb),
            "accent": to255(accent_rgb),
            "genre": genre,
        }, Heat.HOT, thermal_mass=3)]


class TypefaceNerd(Nerd):
    """Picks a typeface from the database, maybe influenced by genre."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and not bb.has("Typeface")

    def run(self, bb: Blackboard) -> list[Item]:
        palette = bb.pick("ColorPalette")
        genre = palette.value["genre"] if palette else "drama"
        # Dumb heuristic: horror likes slab, sci-fi likes mono, etc.
        preference = {
            "horror": "slab-heavy", "sci-fi": "mono-regular",
            "noir": "sans-light", "action": "serif-bold",
            "drama": "script-italic",
        }
        preferred = preference.get(genre)
        if preferred and random.random() < 0.6:
            face = next((f for f in TYPEFACES if f["name"] == preferred), random.choice(TYPEFACES))
        else:
            face = random.choice(TYPEFACES)
        return [Item("Typeface", face, Heat.MEDIUM, thermal_mass=2)]


class LayoutNerd(Nerd):
    """Picks a layout template."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and not bb.has("Layout")

    def run(self, bb: Blackboard) -> list[Item]:
        template = random.choice(LAYOUT_TEMPLATES)
        return [Item("Layout", dict(template), Heat.HOT, thermal_mass=4)]


class HeroImageNerd(Nerd):
    """Generates a synthetic 'hero image' -- colored rectangles and shapes.

    This is the most exaggerated oversimplification: no real images,
    just procedural color fields that evoke a mood.
    """

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has("ColorPalette") and not bb.has("HeroImage")

    def run(self, bb: Blackboard) -> list[Item]:
        palette = bb.pick("ColorPalette")
        if not palette:
            return []
        key = palette.value["key"]
        accent = palette.value["accent"]
        # Describe the hero image as a set of rectangles and gradients
        # The renderer will interpret these
        num_blocks = random.randint(2, 5)
        blocks = []
        for _ in range(num_blocks):
            color = key if random.random() < 0.6 else accent
            # Vary the color slightly
            color = tuple(max(0, min(255, c + random.randint(-30, 30))) for c in color)
            blocks.append({
                "x": random.uniform(0.0, 0.6),
                "y": random.uniform(0.0, 0.6),
                "w": random.uniform(0.2, 1.0),
                "h": random.uniform(0.2, 0.8),
                "color": color,
            })
        return [Item("HeroImage", {"blocks": blocks}, Heat.HOT, thermal_mass=3)]


class GrainNerd(Nerd):
    """Decides to add film grain to the final image."""

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.has("HeroImage") and not bb.has("PostEffect")

    def run(self, bb: Blackboard) -> list[Item]:
        effects = []
        if random.random() < 0.7:
            effects.append("grain")
        if random.random() < 0.4:
            effects.append("vignette")
        if random.random() < 0.3:
            effects.append("posterize")
        return [Item("PostEffect", {"effects": effects}, Heat.MEDIUM, thermal_mass=1)]


class CritiqueNerd(Nerd):
    """Evaluates the current state and may heat up cold items.

    The critique nerd is the 'meta' operator: it looks at what's on
    the blackboard and stirs things up if something seems missing.
    """

    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and bb.tick > 3

    def run(self, bb: Blackboard) -> list[Item]:
        issues = []
        if not bb.has("TitleChunks"):
            issues.append("missing_title")
        if not bb.has("ColorPalette"):
            issues.append("missing_palette")
        if not bb.has("Layout"):
            issues.append("missing_layout")
        if not bb.has("HeroImage"):
            issues.append("missing_hero")
        if not bb.has("Typeface"):
            issues.append("missing_typeface")

        # If things are looking good, generate a completeness score
        total = 5
        present = total - len(issues)
        score = present / total

        return [Item("Critique", {
            "issues": issues,
            "completeness": score,
            "tick": bb.tick,
        }, Heat.MEDIUM, thermal_mass=1)]


class CompletionNerd(Nerd):
    """Declares a poster complete if the critique score is high enough."""

    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        critiques = bb.query("Critique")
        if not critiques:
            return False
        latest = max(critiques, key=lambda c: c.birth_tick)
        return latest.value["completeness"] >= 0.8

    def run(self, bb: Blackboard) -> list[Item]:
        return [Item("Completion", {"declared": True}, Heat.HOT, thermal_mass=10)]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def make_all_nerds() -> list[Nerd]:
    """Create the full roster of nerds."""
    return [
        MoviePickerNerd(name="MoviePicker", heat=Heat.HOT, cooldown_rate=99),
        TitleParserNerd(name="TitleParser", heat=Heat.MEDIUM, cooldown_rate=3),
        GenrePaletteNerd(name="GenrePalette", heat=Heat.MEDIUM, cooldown_rate=3),
        TypefaceNerd(name="TypefacePicker", heat=Heat.MEDIUM, cooldown_rate=4),
        LayoutNerd(name="LayoutPicker", heat=Heat.MEDIUM, cooldown_rate=3),
        HeroImageNerd(name="HeroImageGen", heat=Heat.MEDIUM, cooldown_rate=5),
        GrainNerd(name="GrainEffect", heat=Heat.MEDIUM, cooldown_rate=5),
        CritiqueNerd(name="Critic", heat=Heat.HOT, cooldown_rate=2),
        CompletionNerd(name="CompletionJudge", heat=Heat.COLD, cooldown_rate=99),
    ]
