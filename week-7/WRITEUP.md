# NERDS: A Computational Caricature of Blackboard Architecture for Movie Poster Design

**A Self-Contained Technical Writeup**

*Adam Smith, 2026*

---

## 1. Introduction

What does it take to build a generative system that produces diverse, genre-appropriate creative output — without an LLM, without an explicit pipeline, and without any planning? This document describes NERDS (Non-pipelined Emergent Rendering by Dumb Specialists), a small Python system that generates movie posters using a blackboard architecture. The system is deliberately simple: nine "nerds" (expert operators) read from and write to a shared blackboard of typed items, coordinated only by a heat-based salience mechanism and weighted random selection. The result is a working generator that produces different posters for different movies, with genre-appropriate color palettes, layout variation, and post-processing effects — all in about 800 lines of code.

NERDS is not meant to be a production poster generator. It is a **computational caricature**: a piece of running software that captures and exaggerates a specific claim about how generative systems can work. The term comes from Smith and Mateas (2011), who argued that researchers should build small, self-contained software artifacts that make theoretical claims tangible and testable. A good caricature, like a good editorial cartoon, exaggerates the essential features of its subject while deliberately oversimplifying everything else. The viewer should instantly recognize the claim being made, overlook the simplifications, and walk away with reusable abstractions.

This writeup covers the full arc of the project: the theoretical framing from the computational caricatures paper, the design of the blackboard architecture, the concrete implementation with code examples, narrated traces of actual poster generation runs, and a discussion of what the caricature reveals about non-pipelined generative design.

## 2. Theoretical Framing: Computational Caricatures

### 2.1 The Caricatures Paper

The methodological foundation for this project is "Computational Caricatures: Probing the Game Design Process with AI" by Adam Smith and Michael Mateas, presented at the Seventh AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment (AIIDE 2011). The paper addresses a gap in how game AI researchers communicate design ideas. Research papers describe algorithms; design documents describe products; but neither format is good at capturing the *process claims* that experienced designers carry in their heads — claims like "emergent narrative arises from systemic interaction" or "level design is constraint satisfaction."

Smith and Mateas propose that these process claims can be captured as **computational caricatures**: small, running programs that make a claim about a design process tangible by implementing it directly. The term "caricature" is chosen deliberately. A caricature is not a photograph; it exaggerates some features and ignores others. A computational caricature exaggerates the *essential mechanism* of a design process while deliberately simplifying everything else. The measure of a good caricature is not fidelity but recognizability: does the viewer instantly see the claim being made?

The paper draws an analogy to editorial cartoons. An editorial cartoon about, say, government bureaucracy doesn't need to accurately depict every office building in Washington. It needs a few exaggerated features — a towering stack of papers, a rubber stamp the size of a desk — that make the point instantly recognizable. Similarly, a computational caricature of level generation doesn't need photorealistic graphics. It needs the core generative mechanism to be visible and its effects to be unmistakable.

### 2.2 The Three-Part Structure

The paper proposes that every computational caricature should be analyzed along three dimensions, directly inspired by how visual caricatures work:

**Claims (to be quickly recognized).** This is the core assertion about a design process. It should be immediately apparent from running the software. If someone has to read a paper to understand what the caricature is claiming, the caricature has failed. The claim is the exaggerated nose in the editorial cartoon — the feature that makes you say "Oh, I see what they're saying about generative systems."

**Oversimplifications (to be overlooked).** These are the aspects of the problem that the caricature deliberately gets wrong or ignores. In a visual caricature, oversimplifications are the features that are drawn as simple lines or left out entirely. The viewer is expected to overlook them. If someone criticizes a caricature for having unrealistic ears, they've missed the point. Similarly, if someone criticizes a computational caricature for using hardcoded data instead of a real database, they're looking at the wrong part of the artifact.

**Abstractions (to be reused in the future).** These are the transferable design patterns that emerge from the caricature — the ideas that someone could take and apply in a completely different context. A good caricature doesn't just make a point; it offers building blocks. The abstractions are what make a caricature useful beyond its immediate demonstration.

### 2.3 Applying the Framework to NERDS

For the NERDS project, the three dimensions are:

**Claim: Diverse generative output can emerge from dumb specialists coordinated by heat-based salience and random selection. No LLM is needed. No explicit pipeline is needed.**

This is the core exaggeration. The system produces different posters with genre-appropriate visual treatments, and it does so without any central planner, without any language model reasoning about aesthetics, and without any fixed sequence of operations. The "nerds" are individually stupid — each one does exactly one thing — but their collective behavior, mediated by the blackboard and the heat mechanism, produces coherent output. The claim is legible in the output: run the system with different seeds and you get different movies, different color palettes, different layouts, different post-processing effects. The system is not a pipeline that always runs step A then step B then step C. The order in which nerds fire varies across runs, and the output still coheres.

**Oversimplifications (to be overlooked):**

- Movie data is a hardcoded dictionary of five films, not a real database or API. The claim is not about data access patterns.
- "Images" are colored rectangles procedurally placed on a canvas, not photographs or illustrations. The claim is not about image generation.
- Typography uses system fonts with no kerning or layout refinement. The claim is not about typographic quality.
- The critique nerd is a checklist counter ("are all the required items present?"), not an aesthetic evaluator. The claim is not about quality assessment.
- There are only five movies, five genres, four layouts, and five typeface descriptors. The claim is not about coverage or scale.

Each of these is a place where a real system would invest significant engineering effort. The caricature ignores all of it because none of it is the point.

**Abstractions (to be reused):**

- **Typed blackboard items with heat-based salience.** The idea that a shared workspace of typed data, where each item has a "temperature" indicating its relevance or recency, can coordinate multiple agents without explicit message-passing.
- **Nerd selection weighted by heat and filtered by preconditions.** The scheduling mechanism: agents are not called in a fixed order; instead, eligible agents are selected randomly with heat-based weighting. This is a reusable pattern for any system that needs flexible, non-deterministic orchestration.
- **Thermal mass affecting cooling rate.** The idea that some data items are more persistent than others. A movie title (thermal mass 5) stays relevant for many ticks; a critique (thermal mass 1) cools quickly and gets replaced. This is a simple but expressive mechanism for managing attention in a multi-agent system.
- **Provenance tracking.** Every item on the blackboard records which nerd created it and when. This makes the generative process inspectable and debuggable — you can reconstruct the full history of how a poster was assembled.

## 3. Architecture Design

### 3.1 Why a Blackboard?

The blackboard architecture was first proposed by Erman et al. (1980) for the HEARSAY-II speech understanding system. The core idea is simple: multiple independent "knowledge sources" (experts, specialists, agents — here called "nerds") communicate not by sending messages to each other, but by reading from and writing to a shared data structure called the blackboard. No expert knows about any other expert. They only know about the blackboard.

This architecture has several properties that make it interesting for generative systems:

1. **No fixed pipeline.** In a traditional pipeline, stage A always runs before stage B, which always runs before stage C. In a blackboard system, any expert can run at any time, as long as its preconditions on the blackboard are met. This means the same system can produce output through many different execution orderings.

2. **Opportunistic behavior.** Experts fire when their conditions are met, not when they're told to. If the palette nerd happens to run before the title parser, that's fine — the system adapts. If a critic fires early and finds items missing, it records that observation and other nerds can respond.

3. **Incremental construction.** The output isn't produced all at once. It's built up incrementally as experts add items to the blackboard. At any point, you can inspect the blackboard and see a partial result.

4. **Easy extensibility.** Adding a new expert doesn't require changing any existing expert. You just add a new nerd with new preconditions, and the scheduler will start calling it when its conditions are met.

These properties align well with creative generative processes, where the order of decisions often matters but shouldn't be rigidly fixed. A human designer working on a movie poster might start with the color palette, or with the title treatment, or with the hero image — depending on the movie, the brief, or just their mood that day. A blackboard architecture captures this flexibility naturally.

### 3.2 The NERDS Vocabulary

The system uses a small, precise vocabulary:

**Blackboard.** A bag of typed data items. Not a database, not a key-value store — just a list. Items accumulate over time and are never deleted (though they cool down and become less likely to be selected). The blackboard also tracks a global tick counter.

**Item.** A single thing on the blackboard. Every item has:
- A **type tag** (string): e.g., "MovieData", "ColorPalette", "TitleChunks", "Layout", "HeroImage", "PostEffect", "Critique", "Completion". This is how nerds find what they need.
- A **value** (any Python object): the actual payload. For MovieData, it's a dictionary with title, tagline, genre, year, director, actors. For ColorPalette, it's key and accent RGB tuples plus genre.
- A **heat** level: HOT (2), MEDIUM (1), or COLD (0). New items are born hot. Heat decays over time. Hotter items are more likely to be picked when a nerd queries the blackboard.
- A **thermal mass** (integer 1–5): how resistant the item is to cooling. An item with thermal mass 5 has only a 20% chance of cooling each tick; an item with thermal mass 1 cools every tick. This models the intuition that some decisions are more foundational than others — the choice of movie is a heavy, persistent decision; a post-processing effect is a light, transient one.
- **Provenance**: which nerd created it and at what tick.

**Heat.** A three-level salience score. Heat is the mechanism by which the system manages attention without explicit priorities. Newly created items are hot, meaning they're salient — they're likely to be noticed by other nerds and to influence downstream decisions. Over time, items cool. A cold item is still on the blackboard and can still be read, but it's less likely to be selected by `pick()`. This creates a natural recency bias without any explicit timestamp comparison.

The decay mechanism works per-tick: every item has a chance of cooling one level (HOT -> MEDIUM -> MEDIUM -> COLD), with the probability inversely proportional to thermal mass. An item with thermal mass 1 cools with probability 1.0 each tick (it always cools). An item with thermal mass 5 cools with probability 0.2 each tick (it usually resists). This means:

- MovieData (thermal mass 5): stays hot for several ticks, influencing many downstream decisions
- ColorPalette (thermal mass 3): warm for a few ticks, then fades
- Critique (thermal mass 1): cools immediately, representing a transient observation
- Completion (thermal mass 10): once declared, it stays hot effectively forever

**Nerd.** An expert operator. Each nerd has:
- A **name** (for logging and provenance)
- A **heat** level (for selection weighting — hotter nerds are more likely to be called)
- A **cooldown** counter (after being called, a nerd can't be called again for some number of ticks)
- A **can_run()** method: checks preconditions on the blackboard. A nerd might require certain items to be present, or certain items to be absent (to avoid duplicate work).
- A **run()** method: the actual work. Reads items from the blackboard, does some computation, and returns new items to be added.

The nerds are "dumb" in a specific technical sense: none of them has any model of the overall poster design process. None of them knows what a good poster looks like. None of them reasons about aesthetics. Each one performs a single, narrow operation: pick a movie, parse a title, generate a palette from genre heuristics, choose a layout template, create colored rectangles, decide on post-effects, count how many items are present. The intelligence, such as it is, emerges from their collective interaction via the blackboard.

### 3.3 The Tick Loop

The main loop runs for up to 30 ticks (configurable). Each tick:

1. **Advance the blackboard**: increment the tick counter and decay heat on all items.
2. **Tick all nerds**: reduce their cooldown counters by 1.
3. **Select a nerd**: from all nerds whose `can_run()` returns true (preconditions met and cooldown is zero), pick one using weighted random selection where the weight is `1 + heat * 3`. A HOT nerd (heat=2) gets weight 7; a MEDIUM nerd gets weight 4; a COLD nerd gets weight 1.
4. **Call the nerd**: it reads from the blackboard, returns new items, which are added to the blackboard.
5. **Check for completion**: if a "Completion" item is on the blackboard, stop.
6. **If max ticks is reached**, render whatever is on the blackboard.

After the loop ends, the renderer reads the blackboard and composites a poster image.

### 3.4 The Nine Nerds

Here is the full roster, in roughly the order they tend to fire (though this varies by seed):

| Nerd | Reads | Writes | Precondition | Cooldown | Notes |
|------|-------|--------|-------------|----------|-------|
| **MoviePicker** | (nothing) | MovieData | No MovieData exists | 99 (fires once) | Picks a random movie from a hardcoded database of 5 films |
| **TitleParser** | MovieData | TitleChunks | MovieData exists, no TitleChunks | 3 | Splits title into primary/secondary (e.g., "Mad Max" / "Fury Road") |
| **GenrePalette** | MovieData | ColorPalette | MovieData exists, no ColorPalette | 3 | Maps genre to HSV color parameters with jitter |
| **TypefacePicker** | ColorPalette (optional) | Typeface | No Typeface exists | 4 | Genre-influenced typeface selection with 60% preference, 40% random |
| **LayoutPicker** | (nothing) | Layout | No Layout exists | 3 | Picks from 4 layout templates (classic-centered, bottom-heavy, split-diagonal, minimalist) |
| **HeroImageGen** | ColorPalette | HeroImage | ColorPalette exists, no HeroImage | 5 | Generates 2-5 colored rectangles using palette colors with jitter |
| **GrainEffect** | HeroImage | PostEffect | HeroImage exists, no PostEffect | 5 | Probabilistically enables grain (70%), vignette (40%), posterize (30%) |
| **Critic** | (all items) | Critique | tick > 3 | 2 | Counts missing items, computes completeness score (present/5) |
| **CompletionJudge** | Critique | Completion | Latest critique has completeness >= 0.8 | 99 (fires once) | Declares the poster done |

Note the dependency structure that emerges from preconditions, not from explicit wiring:

- MoviePicker has no preconditions (except "no MovieData yet"), so it tends to fire early.
- TitleParser and GenrePalette both depend on MovieData, so they fire after MoviePicker.
- HeroImageGen depends on ColorPalette, so it fires after GenrePalette.
- GrainEffect depends on HeroImage, so it fires after HeroImageGen.
- Critic fires after tick 3, giving other nerds time to populate the blackboard.
- CompletionJudge fires only when a critique says the poster is at least 80% complete.

But TypefacePicker and LayoutPicker have weak or no dependencies, so they can fire in any position. And the Critic can fire multiple times (cooldown of 2), generating multiple Critique items as the poster evolves.

This dependency structure is **implicit**, not **explicit**. No nerd knows about any other nerd. The ordering emerges from the interplay of preconditions, cooldowns, and heat-weighted random selection.

## 4. Implementation Walkthrough

The entire system is about 800 lines of Python across four files, managed with `uv` and depending only on Pillow and NumPy. This section walks through the key code structures with excerpts and commentary.

### 4.1 Project Structure

```
nerds/
├── pyproject.toml      # uv project config (pillow, numpy)
├── blackboard.py       # Blackboard, Item, Heat (105 lines)
├── nerds.py            # Base Nerd + 9 concrete nerds + databases (365 lines)
├── render.py           # PIL poster compositor + post-effects (187 lines)
├── main.py             # Main loop, nerd selection, summary (144 lines)
└── output/             # Generated poster PNGs
```

### 4.2 The Blackboard (blackboard.py)

The blackboard module defines three things: a `Heat` enum, an `Item` dataclass, and the `Blackboard` class.

**Heat** is an IntEnum with three levels:

```python
class Heat(IntEnum):
    """Three-level salience score. Higher = hotter."""
    COLD = 0
    MEDIUM = 1
    HOT = 2
```

Using IntEnum means heat levels can be compared with `>=` and used in arithmetic (for weighting), which keeps the code terse.

**Item** is a dataclass carrying a type tag, value, heat, thermal mass, and provenance:

```python
@dataclass
class Item:
    """A single thing on the blackboard."""
    type_tag: str            # e.g. "MovieTitle", "ColorPalette"
    value: Any               # the actual payload
    heat: Heat = Heat.HOT    # hot off the press by default
    thermal_mass: int = 1    # bulkier things cool slower (1-5)
    created_by: str = ""     # nerd name
    birth_tick: int = 0      # when it appeared
    id: str = ""             # unique id, set by blackboard
```

New items default to HOT heat and thermal mass 1. The nerds override these when creating items — for example, MovieData gets thermal mass 5 (it's a heavy, foundational decision) while PostEffect gets thermal mass 1 (it's a light, transient addition).
**The Blackboard class** itself is a list of items with query and selection methods:

```python
class Blackboard:
    def __init__(self):
        self.items: list[Item] = []
        self.tick: int = 0
        self._next_id: int = 0
```

Adding an item stamps it with an ID, a birth tick, and provenance:

```python
def add(self, item: Item, created_by: str = "") -> Item:
    item.id = f"{item.type_tag.lower()}_{self._next_id}"
    item.birth_tick = self.tick
    item.created_by = created_by or item.created_by
    self._next_id += 1
    self.items.append(item)
    return item
```

Querying filters by type tag and minimum heat:

```python
def query(self, type_tag: str, min_heat: Heat = Heat.COLD) -> list[Item]:
    return [
        it for it in self.items
        if it.type_tag == type_tag and it.heat >= min_heat
    ]
```

The most interesting method is `pick()`, which performs weighted random selection among items of a given type. The weight formula is `1 + heat * 3`, which means:

- COLD (0): weight 1
- MEDIUM (1): weight 4
- HOT (2): weight 7

```python
def pick(self, type_tag: str, min_heat: Heat = Heat.COLD) -> Item | None:
    candidates = self.query(type_tag, min_heat)
    if not candidates:
        return None
    weights = [1 + it.heat.value * 3 for it in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]
```

This weighting scheme means hot items are 7x more likely to be picked than cold items — a strong recency bias, but not absolute. A cold item can still be selected, which models the occasional creative revisit of an earlier decision.

**Heat decay** is the mechanism that creates temporal dynamics:

```python
def decay_heat(self):
    for item in self.items:
        if item.heat == Heat.COLD:
            continue
        # mass=1 -> always cools, mass=5 -> 20% chance of cooling
        if random.random() < 1.0 / item.thermal_mass:
            item.heat = Heat(item.heat.value - 1)
```

Each tick, every non-cold item has a `1/thermal_mass` probability of losing one heat level. This means:
- Thermal mass 1: 100% chance of cooling per tick (cools in 2 ticks from HOT to COLD)
- Thermal mass 3: 33% chance per tick (expected ~6 ticks from HOT to COLD)
- Thermal mass 5: 20% chance per tick (expected ~10 ticks from HOT to COLD)

This simple stochastic mechanism creates a rich attention landscape. Early in a run, the blackboard is sparse and everything is hot. As items accumulate, older items cool and newer items dominate attention. But foundational items (high thermal mass) maintain influence longer, creating a natural hierarchy without any explicit priority system.
### 4.3 The Nerds (nerds.py)

The nerds module contains the base `Nerd` class, nine concrete nerd implementations, and the hardcoded databases (movies, palettes, typefaces, layouts).

**Base Nerd** establishes the interface:

```python
@dataclass
class Nerd:
    name: str
    heat: Heat = Heat.MEDIUM
    cooldown: int = 0
    cooldown_rate: int = 2  # ticks to cool down after being called

    def can_run(self, bb: Blackboard) -> bool:
        return self.cooldown == 0

    def run(self, bb: Blackboard) -> list[Item]:
        raise NotImplementedError

    def call(self, bb: Blackboard) -> list[Item]:
        results = self.run(bb)
        self.cooldown = self.cooldown_rate
        return results

    def tick(self):
        if self.cooldown > 0:
            self.cooldown -= 1
```

The `call()` method wraps `run()` with cooldown management. After being called, a nerd can't run again for `cooldown_rate` ticks. This prevents any single nerd from dominating the schedule and gives other nerds time to react to newly posted items.

**MoviePickerNerd** is the simplest nerd — it just picks a random movie from the database:

```python
class MoviePickerNerd(Nerd):
    def can_run(self, bb: Blackboard) -> bool:
        return super().can_run(bb) and not bb.has("MovieData")

    def run(self, bb: Blackboard) -> list[Item]:
        movie = random.choice(MOVIES)
        return [Item("MovieData", movie, Heat.HOT, thermal_mass=5)]
```

Note the thermal mass of 5 — the heaviest in the system. The movie choice is the most foundational decision, and it should remain salient (hot) for many ticks to influence downstream nerds.

The `can_run()` check (`not bb.has("MovieData")`) ensures we only pick one movie per run. Combined with cooldown_rate=99, this nerd effectively fires once.

**GenrePaletteNerd** demonstrates how genre maps to color. This is the caricature's most exaggerated claim: that a movie's visual identity can be reduced to genre-based HSV lookup with random jitter:

```python
GENRE_PALETTES = {
    "sci-fi":  {"key_hue": 0.58, "accent_hue": 0.10, "sat": 0.7, "val": 0.3},
    "horror":  {"key_hue": 0.0,  "accent_hue": 0.0,  "sat": 0.6, "val": 0.15},
    "noir":    {"key_hue": 0.75, "accent_hue": 0.08, "sat": 0.5, "val": 0.2},
    "drama":   {"key_hue": 0.55, "accent_hue": 0.45, "sat": 0.4, "val": 0.35},
    "action":  {"key_hue": 0.08, "accent_hue": 0.12, "sat": 0.9, "val": 0.4},
}
```

Sci-fi gets blue-ish key color (hue 0.58) with amber accent (hue 0.10). Horror gets deep red (hue 0.0) with low value (0.15) for darkness. These are absurdly reductive — and that's exactly the point. The oversimplification makes the claim visible: genre alone, with some noise, produces recognizably different visual treatments.

The palette generation adds jitter to avoid mechanical sameness:

```python
def run(self, bb: Blackboard) -> list[Item]:
    movie = bb.pick("MovieData")
    genre = movie.value.get("genre", "drama")
    pal = GENRE_PALETTES.get(genre, GENRE_PALETTES["drama"])
    jitter = random.uniform(-0.05, 0.05)
    key_rgb = colorsys.hsv_to_rgb(
        (pal["key_hue"] + jitter) % 1.0, pal["sat"], pal["val"])
    accent_rgb = colorsys.hsv_to_rgb(
        (pal["accent_hue"] + jitter) % 1.0,
        min(1.0, pal["sat"] + 0.2),
        min(1.0, pal["val"] + 0.3))
    to255 = lambda c: tuple(int(x * 255) for x in c)
    return [Item("ColorPalette", {
        "key": to255(key_rgb), "accent": to255(accent_rgb), "genre": genre,
    }, Heat.HOT, thermal_mass=3)]
```

**TypefaceNerd** shows genre influence with a probabilistic override: 60% of the time it picks the genre-preferred typeface, 40% of the time it picks randomly. This creates variety without total chaos:

```python
preference = {
    "horror": "slab-heavy", "sci-fi": "mono-regular",
    "noir": "sans-light", "action": "serif-bold",
    "drama": "script-italic",
}
preferred = preference.get(genre)
if preferred and random.random() < 0.6:
    face = next((f for f in TYPEFACES if f["name"] == preferred),
                random.choice(TYPEFACES))
else:
    face = random.choice(TYPEFACES)
```
**HeroImageNerd** is the most visually exaggerated oversimplification. Real movie posters have photographs, illustrations, or digital composites. This nerd generates 2–5 colored rectangles:

```python
def run(self, bb: Blackboard) -> list[Item]:
    palette = bb.pick("ColorPalette")
    key = palette.value["key"]
    accent = palette.value["accent"]
    num_blocks = random.randint(2, 5)
    blocks = []
    for _ in range(num_blocks):
        color = key if random.random() < 0.6 else accent
        color = tuple(max(0, min(255, c + random.randint(-30, 30)))
                       for c in color)
        blocks.append({
            "x": random.uniform(0.0, 0.6),
            "y": random.uniform(0.0, 0.6),
            "w": random.uniform(0.2, 1.0),
            "h": random.uniform(0.2, 0.8),
            "color": color,
        })
    return [Item("HeroImage", {"blocks": blocks}, Heat.HOT, thermal_mass=3)]
```

The blocks use the palette colors (60% key, 40% accent) with per-channel random jitter of ±30. The result is abstract color fields that evoke a mood without depicting anything. This is the oversimplification that viewers should overlook — the claim isn't about image synthesis, it's about coordination.

**CritiqueNerd** is the system's only form of self-evaluation. It simply counts which required items are present:

```python
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
    total = 5
    present = total - len(issues)
    score = present / total
    return [Item("Critique", {
        "issues": issues, "completeness": score, "tick": bb.tick,
    }, Heat.MEDIUM, thermal_mass=1)]
```

The critique has thermal mass 1 — it cools immediately, because it's a transient observation about the *current* state. Multiple critiques accumulate over a run, each reflecting the blackboard's state at a different tick. The CompletionJudge looks at the *latest* critique (by birth tick) to decide whether to declare done.

**CompletionNerd** closes the loop:

```python
class CompletionNerd(Nerd):
    def can_run(self, bb: Blackboard) -> bool:
        if not super().can_run(bb):
            return False
        critiques = bb.query("Critique")
        if not critiques:
            return False
        latest = max(critiques, key=lambda c: c.birth_tick)
        return latest.value["completeness"] >= 0.8

    def run(self, bb: Blackboard) -> list[Item]:
        return [Item("Completion", {"declared": True},
                     Heat.HOT, thermal_mass=10)]
```

When the latest critique reports 80% completeness (4 of 5 required items), the CompletionJudge fires and declares the poster done. The Completion item has thermal mass 10 — it will never cool down, ensuring the main loop's completion check succeeds on the same tick.

### 4.4 The Renderer (render.py)

The renderer is not part of the blackboard architecture — it's a post-hoc consumer that reads the final blackboard state and composites an image. It uses PIL (Pillow) to create a 600×900 pixel image (2:3 aspect ratio, like a real movie poster).

The rendering pipeline is straightforward:
1. Create a base image filled with the key color from the palette.
2. Paint the hero image blocks (colored rectangles) in the region defined by the layout template.
3. Draw the title text (primary and optional secondary) using the layout's positioning.
4. Draw the tagline (from movie data) below a decorative separator line.
5. Draw the credits line (director and actors) near the bottom.
6. Apply post-effects: grain (NumPy noise), vignette (radial darkening), posterize (color quantization).

The post-effects use NumPy for array operations. For example, film grain:

```python
def _apply_grain(img: Image.Image) -> Image.Image:
    import numpy as np
    arr = np.array(img, dtype=np.int16)
    noise = np.random.normal(0, 12, arr.shape).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)
```

And vignette (radial edge darkening):

```python
def _apply_vignette(img: Image.Image) -> Image.Image:
    import numpy as np
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    radius = max(cy, cx) * 1.2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    vignette = 1.0 - np.clip(dist / radius, 0, 1) ** 2 * 0.6
    arr *= vignette[:, :, np.newaxis]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
```

These effects are probabilistically selected by the GrainNerd: 70% chance of grain, 40% chance of vignette, 30% chance of posterization. Different seeds yield different combinations, adding another axis of visual variation.

### 4.5 The Main Loop (main.py)

The main loop ties everything together:

```python
def run(seed=None, max_ticks=30, verbose=False):
    if seed is not None:
        random.seed(seed)

    bb = Blackboard()
    nerds = make_all_nerds()

    for tick in range(max_ticks):
        bb.advance_tick()          # decay heat, increment tick
        for n in nerds:
            n.tick()               # reduce cooldowns

        nerd = select_nerd(nerds, bb)
        if nerd is None:
            continue               # no eligible nerd this tick

        results = nerd.call(bb)
        for item in results:
            bb.add(item, created_by=nerd.name)

        if bb.has("Completion"):
            break

    render_poster(bb, output_path)
```

Nerd selection mirrors the blackboard's `pick()` method — weighted random choice where hotter nerds are more likely:

```python
def select_nerd(nerds, bb):
    eligible = [n for n in nerds if n.can_run(bb)]
    if not eligible:
        return None
    weights = [1 + n.heat.value * 3 for n in eligible]
    return random.choices(eligible, weights=weights, k=1)[0]
```

After rendering, the system prints a **caricature summary table** modeled on Table 1 from Smith and Mateas (2011), making the theoretical framing explicit in the program's output.
## 5. Narrated Generation Traces

The following traces are from actual runs of the system. They show the tick-by-tick execution log, with commentary on what's happening architecturally at each step.

### 5.1 Trace: Blade Runner (seed 42)

This run produces a poster for Blade Runner (1982), a sci-fi film. The trace demonstrates the system's typical flow: an early foundational phase, a mid-run elaboration phase, and a completion phase.

```
=== NERDS: Blackboard Poster Generator ===
Seed: 42  Max ticks: 30

  tick  1: TypefacePicker -> ['Typeface']
  tick  2: MoviePicker    -> ['MovieData']
  tick  3: LayoutPicker   -> ['Layout']
  tick  4: TitleParser    -> ['TitleChunks']
  tick  5: Critic         -> ['Critique']
  tick  6: GenrePalette   -> ['ColorPalette']
  tick  7: Critic         -> ['Critique']
  tick  8: HeroImageGen   -> ['HeroImage']
  tick  9: GrainEffect    -> ['PostEffect']
  tick 10: Critic         -> ['Critique']
  tick 11: CompletionJudge -> ['Completion']

** Completion declared at tick 11! **
```

**Narration:**

**Tick 1: TypefacePicker fires first.** This is an unusual ordering — in many runs, MoviePicker fires first because it has HOT heat while TypefacePicker has MEDIUM. But with seed 42, the random selection picks TypefacePicker. Since no ColorPalette exists yet, the typeface is chosen without genre influence (the nerd's 40% random path). This is the blackboard architecture at work: the TypefacePicker doesn't *know* it's early or that it lacks genre context. It just checks its preconditions (no Typeface exists yet) and runs.

**Tick 2: MoviePicker fires.** It picks Blade Runner from the 5-movie database. The MovieData item is born with Heat.HOT and thermal mass 5, making it the most persistent item on the blackboard. It will stay salient for roughly 10 ticks.

**Tick 3: LayoutPicker fires.** It picks one of 4 layout templates. Like TypefacePicker, LayoutPicker has no dependency on movie data — it can fire at any time. By tick 3, we have three items on the blackboard: a typeface, the movie data, and a layout. None of these were produced in a designed "logical" order.

**Tick 4: TitleParser fires.** Now that MovieData exists, TitleParser can run. It reads "Blade Runner" and splits it into primary="Blade" and secondary="Runner" (splitting on the first space). The TitleChunks item gets thermal mass 3.

**Tick 5: First Critic fires.** The Critic activates after tick 3 (its precondition). It surveys the blackboard: TitleChunks present, Layout present, Typeface present — but ColorPalette and HeroImage are missing. Completeness: 3/5 = 0.6. This critique goes on the blackboard with thermal mass 1, so it will cool immediately. The CompletionJudge checks this critique but 0.6 < 0.8, so it stays dormant.

**Tick 6: GenrePalette fires.** With MovieData available, it reads the genre ("sci-fi") and generates a palette. The sci-fi palette has key_hue=0.58 (blue) and accent_hue=0.10 (amber/gold), with jitter applied. The resulting colors: a deep blue background and a warm amber accent. This is the genre-to-color caricature in action — Blade Runner gets blue and amber because it's sci-fi, with no further aesthetic reasoning.

**Tick 7: Second Critic fires.** The Critic's cooldown of 2 has elapsed. It surveys again: TitleChunks, Layout, Typeface, ColorPalette all present. Only HeroImage is missing. Completeness: 4/5 = 0.8. This meets the CompletionJudge's threshold, but the CompletionJudge has COLD heat (weight 1) and must compete with other eligible nerds for selection.

**Tick 8: HeroImageGen fires.** With ColorPalette available, it generates 2–5 colored rectangles using the blue/amber palette with ±30 jitter per channel. These abstract blocks will become the poster's "hero image" — overlapping color fields that evoke the film's neon-and-shadow aesthetic purely through palette association.

**Tick 9: GrainEffect fires.** With HeroImage present, it rolls the dice on post-effects. For this seed: grain (yes, 70% probability), vignette (varies), posterize (varies). The PostEffect item has thermal mass 1 — it's a light finishing touch.

**Tick 10: Third Critic fires.** All 5 required items are present. Completeness: 5/5 = 1.0.

**Tick 11: CompletionJudge fires.** The latest critique reports completeness >= 0.8. The Completion item is declared with thermal mass 10. The main loop sees the Completion item and breaks. Total: 11 ticks, 11 items on the blackboard (including 3 critiques).

**Final blackboard state:**

```
  <Typeface#typeface_0 heat=COLD by=TypefacePicker>
  <MovieData#moviedata_1 heat=MEDIUM by=MoviePicker>
  <Layout#layout_2 heat=COLD by=LayoutPicker>
  <TitleChunks#titlechunks_3 heat=COLD by=TitleParser>
  <Critique#critique_4 heat=COLD by=Critic>
  <ColorPalette#colorpalette_5 heat=COLD by=GenrePalette>
  <Critique#critique_6 heat=COLD by=Critic>
  <HeroImage#heroimage_7 heat=COLD by=HeroImageGen>
  <PostEffect#posteffect_8 heat=COLD by=GrainEffect>
  <Critique#critique_9 heat=COLD by=Critic>
  <Completion#completion_10 heat=HOT by=CompletionJudge>
```

Notice: by tick 11, almost everything has cooled to COLD except MovieData (still MEDIUM, thanks to thermal mass 5) and Completion (HOT, thermal mass 10). The Typeface that was chosen first (tick 1) has been cold for 10 ticks — but it's still on the blackboard and the renderer can still read it. Heat affects selection probability during generation, not availability during rendering.

The rendered poster has: deep blue background, amber title text reading "BLADE / RUNNER", amber-tinted abstract color blocks in the hero area, the tagline "Man has made his match... now it's his problem.", a credits line, and film grain applied over the whole image. It reads as unmistakably sci-fi — not because any nerd understood sci-fi aesthetics, but because the genre-to-palette mapping (blue + amber) triggers the viewer's own associations.
### 5.2 Trace: The Shining (seed 7)

```
=== NERDS: Blackboard Poster Generator ===
Seed: 7  Max ticks: 30

  tick  1: MoviePicker    -> ['MovieData']
  tick  2: TitleParser    -> ['TitleChunks']
  tick  3: LayoutPicker   -> ['Layout']
  tick  4: GenrePalette   -> ['ColorPalette']
  tick  5: Critic         -> ['Critique']
  tick  6: TypefacePicker -> ['Typeface']
  tick  7: Critic         -> ['Critique']
  tick  8: HeroImageGen   -> ['HeroImage']
  tick  9: GrainEffect    -> ['PostEffect']
  tick 10: Critic         -> ['Critique']
  tick 11: CompletionJudge -> ['Completion']

** Completion declared at tick 11! **
```

**Narration:**

This run follows a more "natural" ordering: movie first, then title, layout, palette, critique, typeface, and so on. The key difference from the Blade Runner run is what happens at tick 4.

**Tick 4: GenrePalette fires for "horror".** The horror palette has key_hue=0.0 (red) with low value (0.15) — this produces a deep, dark crimson. The accent is also red-shifted (accent_hue=0.0) with slightly higher saturation and value, yielding a brighter blood-red accent. The Shining's poster will be dominated by dark reds and blacks.

**Tick 6: TypefacePicker fires with genre context.** Unlike the Blade Runner run where TypefacePicker fired before genre data existed, here it fires after GenrePalette. It reads the palette's genre ("horror") and has a 60% chance of picking "slab-heavy" — the genre preference for horror. If the 60% check succeeds, the poster gets heavy slab type. If it fails, a random typeface is chosen instead. This is a concrete example of how ordering affects output: the same nerd, running at a different point in the process, produces different results because of what's on the blackboard.

**Comparing orderings:** Both runs complete in 11 ticks with 11 items. But the Blade Runner run had TypefacePicker fire at tick 1 (before genre data), while The Shining run had it fire at tick 6 (after genre data). This means Blade Runner's typeface is genre-unaware (random), while The Shining's typeface is genre-influenced (60% chance of horror preference). The blackboard architecture creates this variation naturally through weighted random selection — no branching logic, no conditional pipelines.

**The rendered poster** has: near-black crimson background, bright red title text "THE / SHINING", dark red-tinted overlapping blocks, the tagline "A masterpiece of modern horror.", and potentially film grain with vignette. It reads as horror — dark, red, oppressive — purely from genre-to-color mapping.

### 5.3 Trace: Moonlight (seed 256)

```
=== NERDS: Blackboard Poster Generator ===
Seed: 256  Max ticks: 30

  tick  1: TypefacePicker -> ['Typeface']
  tick  2: MoviePicker    -> ['MovieData']
  tick  3: TitleParser    -> ['TitleChunks']
  tick  4: GenrePalette   -> ['ColorPalette']
  tick  5: Critic         -> ['Critique']
  tick  6: HeroImageGen   -> ['HeroImage']
  tick  7: Critic         -> ['Critique']
  tick  8: GrainEffect    -> ['PostEffect']
  tick  9: Critic         -> ['Critique']
  tick 10: LayoutPicker   -> ['Layout']
  tick 11: Critic         -> ['Critique']
  tick 12: CompletionJudge -> ['Completion']

** Completion declared at tick 12! **
```

**Narration:**

This run has two notable features: the LayoutPicker fires very late (tick 10), and the Critic fires four times instead of three.

**Late LayoutPicker.** In both previous runs, LayoutPicker fired by tick 3. Here it doesn't fire until tick 10. This happens because LayoutPicker has MEDIUM heat (weight 4), and in the earlier ticks, other eligible nerds won the random selection. The system still works fine — the layout is on the blackboard before the Completion is declared, and the renderer reads it at the end regardless of when it was created.

**Four Critic firings.** Because LayoutPicker fires so late, the Critic's tick 5 survey finds Layout missing along with HeroImage: completeness 3/5 = 0.6. The tick 7 survey still finds Layout missing: 4/5 = 0.8 (HeroImage was just added). At this point CompletionJudge could fire, but it has COLD heat (weight 1) and competes with other nerds. GrainEffect wins tick 8 instead. Tick 9: another Critic, still 4/5 = 0.8 (Layout still missing). Finally at tick 10, LayoutPicker fires, and at tick 11 the Critic reports 5/5 = 1.0. CompletionJudge fires at tick 12.

This is a concrete demonstration of the non-pipeline claim: the Layout — something you might think must be decided early to structure everything else — was the second-to-last item added. And the poster still works. The renderer doesn't care *when* items were added, only *that* they're present.

**The rendered poster** uses the drama palette: key_hue=0.55 (blue-teal) with moderate saturation and value, accent_hue=0.45 (teal-green). Softer, quieter colors than either Blade Runner's electric blue or The Shining's oppressive crimson. Title text reads "MOONLIGHT" with tagline "This is the story of a lifetime."

### 5.4 Cross-Run Comparison

| Property | Blade Runner (s42) | The Shining (s7) | Moonlight (s256) |
|----------|-------------------|-------------------|-------------------|
| Genre | sci-fi | horror | drama |
| Key color | Deep blue | Dark crimson | Blue-teal |
| Accent color | Amber/gold | Bright red | Teal-green |
| Ticks to completion | 11 | 11 | 12 |
| Total items | 11 | 11 | 12 |
| Critic firings | 3 | 3 | 4 |
| TypefacePicker order | 1st (no genre) | 6th (genre-aware) | 1st (no genre) |
| LayoutPicker order | 3rd | 3rd | 10th (very late) |
| Nerd firing order | Typeface, Movie, Layout, Title, Critic, Palette, Critic, Hero, Grain, Critic, Done | Movie, Title, Layout, Palette, Critic, Typeface, Critic, Hero, Grain, Critic, Done | Typeface, Movie, Title, Palette, Critic, Hero, Critic, Grain, Critic, Layout, Critic, Done |

The three runs produce visually distinct posters with different color palettes, different nerd orderings, and different numbers of critic evaluations. The claim is visible: the same system, with the same nerds and the same blackboard rules, produces different coherent output through different paths. No run follows the same sequence. No LLM decides the order. The blackboard mediates everything.
## 6. Discussion: What the Caricature Reveals

### 6.1 The Pipeline Assumption

Most generative systems are pipelines. An image generator takes a prompt, encodes it, runs diffusion, decodes pixels. A game level generator places rooms, then corridors, then items, then enemies. A music generator chooses a key, builds a chord progression, lays down a melody, adds accompaniment. Each stage consumes the output of the previous stage, in a fixed order.

Pipelines are efficient, predictable, and easy to debug. They are also rigid. If you want stage C to sometimes influence stage A, you have to add explicit feedback loops, which quickly becomes complex. If you want the system to sometimes skip stage B entirely, you need conditional logic. If you want to add a new stage between B and C, you have to modify the plumbing.

NERDS demonstrates that you can get coherent generative output without any of this. The nerds don't form a pipeline. They don't know about each other. They fire in different orders on different runs. And yet the output coheres — each poster has a movie, a title, a palette, a layout, a hero image, and post-effects, because the precondition/blackboard mechanism ensures all the pieces eventually appear without mandating an order.

This is the caricature's central claim, and the generation traces make it visible: three runs, three different orderings, three different posters, all coherent. The claim is not that pipelines are bad. It's that the assumption that you *need* a pipeline for coherent output is worth questioning.

### 6.2 Heat as Cheap Attention

The heat mechanism is the simplest possible form of attention management. In a system with many items on the blackboard, how does a nerd decide which item to read? In NERDS, it calls `bb.pick("ColorPalette")` and gets a heat-weighted random selection among all ColorPalette items. If there were multiple palettes (from a nerd that generates alternatives), the hottest one would be most likely selected — but not guaranteed. A cold palette could still be picked, modeling the serendipity of revisiting an earlier option.

In this caricature, there's only ever one item per type (except for Critique), so the heat-weighted selection doesn't matter much for picking *between* items of the same type. But the heat mechanism matters enormously for the *nerd scheduling* side: nerds with HOT heat are 7x more likely to be selected than nerds with COLD heat. This creates a natural priority system without explicit priority numbers.

The thermal mass mechanism adds another layer. It's the difference between a sticky note (thermal mass 1) and a whiteboard heading (thermal mass 5). Both are "on the board," but the sticky note will be forgotten quickly while the heading persists. This maps well to creative processes: the choice of movie is a persistent frame; a critique of the current state is a fleeting observation.

### 6.3 Emergence vs. Design

How much of NERDS' output is "emergent" and how much is "designed"? This is a question the caricature framework encourages us to ask.

The genre-to-color mapping is entirely designed. Horror gets red. Sci-fi gets blue. That's a lookup table, not emergence. The fact that The Shining ends up with a dark crimson palette is 100% determined by the genre field in the movie database and the palette table.

But the *ordering* of nerd firings is emergent. No one designed the Blade Runner run to have TypefacePicker fire first. No one designed the Moonlight run to have LayoutPicker fire last. These orderings arise from the interaction of heat-weighted random selection, cooldowns, and preconditions. And they have consequences: a typeface chosen before genre data is available will be different from one chosen after.

The caricature makes this distinction vivid by exaggerating both sides. The designed parts (genre tables, movie data) are absurdly simplistic, making them obviously "designed." The emergent parts (firing order, heat dynamics) are the only source of run-to-run variation, making them obviously "emergent."

A real system would blur this line — emergence and design would be interleaved at every level. The caricature's oversimplification makes the two forces separately visible.

### 6.4 Relation to Other Work

**StoryAssembler** (Garbe et al., 2019) uses a quality-based approach to narrative generation: content fragments are tagged with quality constraints, and the system selects fragments that maximize a quality metric. NERDS' heat mechanism serves a similar function — heat is a rough quality/relevance signal — but without explicit optimization. Where StoryAssembler deliberates, NERDS rolls dice.

**Pewter** and **Layered Selection Prompting** explore how to compose generative operations without rigid pipelines. NERDS pushes this further by removing any notion of "layers" or "stages" — there's just a flat bag of nerds and a flat bag of items, with heat providing the only temporal structure.

**Classical blackboard systems** (HEARSAY-II, BB1, GBB) used more sophisticated control mechanisms: agenda-based scheduling, focus-of-attention heuristics, explicit knowledge source activation records. NERDS deliberately strips all of this away. The scheduler is a single weighted random choice. The focus of attention is implicit in heat. There are no agendas. This is the caricature's exaggeration: showing that even the simplest possible blackboard scheduler can produce interesting behavior.

**LLM-based generative systems** are the implicit foil. Current practice often uses an LLM as the central coordinator: it decides what to do next, reasons about quality, and produces output in an auto-regressive pipeline. NERDS demonstrates that the coordination function — deciding what to do next — can be handled by something far simpler than an LLM, at least for this domain. The claim is not that LLMs are unnecessary for all generative tasks, but that the *coordination* role is separable from the *generation* role, and simpler coordination mechanisms deserve attention.
### 6.5 Limitations and Honest Assessment

The caricature framework asks us to be explicit about oversimplifications, but it's also worth noting genuine limitations that go beyond deliberate simplification:

**No iteration or revision.** Real design processes involve looking at intermediate results, deciding something doesn't work, and going back to change an earlier decision. NERDS' nerds only write to the blackboard; they never delete or modify existing items. The Critic nerd observes but doesn't *act on* its observations — it doesn't reheat a cold item or request a do-over. A more complete caricature might add a "Revisionist" nerd that responds to critiques by removing and regenerating items.

**Single-item-per-type constraint.** Most nerds check `not bb.has("TypeTag")` before running, ensuring only one item of each type is ever created. A richer system would allow multiple competing alternatives (three different palettes, two different layouts) and let the heat mechanism naturally select among them. The current implementation avoids this complexity, but it also makes the heat-weighted `pick()` method less interesting than it could be.

**Cooldown as the only temporal mechanism.** The cooldown system prevents a nerd from firing twice in a row, but it's a blunt instrument. A more sophisticated caricature might give nerds adaptive cooldowns based on blackboard state, or allow nerds to "warm up" when they detect relevant new items.

**The renderer is outside the loop.** The render step happens after the blackboard loop completes. In a more ambitious version, partial renders could be posted back to the blackboard, allowing visual nerds to react to what the poster looks like so far. This would create a genuine perception-action loop within the blackboard framework.

### 6.6 What Could Be Built on These Abstractions

The reusable abstractions from this caricature — typed items with heat, weighted nerd selection, thermal mass, provenance — are not specific to movie posters. They could be applied to:

**Game level generation.** Nerds for room placement, corridor connection, item population, enemy placement, lighting, and playtesting. The blackboard holds a growing spatial description. Heat ensures that recently placed rooms get corridors before older ones. A Critic nerd checks for connectivity and balance.

**Recipe generation.** Nerds for ingredient selection, technique choice, flavor pairing, plating, and nutrition analysis. The blackboard holds a recipe in progress. Thermal mass keeps foundational choices (protein, cuisine style) salient while transient choices (garnish) cool quickly.

**Music composition.** Nerds for key selection, chord progression, melody generation, rhythmic pattern, and instrumentation. The blackboard holds a growing arrangement. A Critic nerd checks for harmonic consistency.

**Document layout.** Nerds for content hierarchy, grid structure, typography, image placement, and whitespace management. This is close to the poster domain but generalized to multi-page documents.

In each case, the pattern is the same: define the typed vocabulary, write the dumb specialists, set thermal masses to reflect the importance hierarchy, and let the heat-weighted scheduler coordinate. The caricature suggests this pattern is worth trying before reaching for more complex orchestration mechanisms.

## 7. Running the System

NERDS is managed with `uv` and requires Python 3.11+. To run:

```bash
# Install dependencies
uv sync

# Generate a poster with a specific seed
uv run python main.py --seed 42 --verbose

# Generate with a random seed
uv run python main.py --verbose

# Generate without verbose logging
uv run python main.py --seed 7
```

Output posters are saved to the `output/` directory as PNG files, named with the movie title and seed (e.g., `poster_blade_runner_s42.png`).

The `--verbose` flag shows the tick-by-tick log, including which nerd fires and what items it creates. The `--seed` flag sets the random seed for reproducibility.

## 8. Conclusion

NERDS is a computational caricature of blackboard architecture applied to movie poster design. Its claim is that diverse, genre-appropriate generative output can emerge from dumb specialists coordinated by heat-based salience and random selection, without an LLM and without an explicit pipeline. The generation traces demonstrate this claim concretely: three different seeds produce three different movies with three different visual treatments through three different execution orderings, all using the same nine nerds and the same blackboard rules.

The oversimplifications — hardcoded movies, colored rectangles for images, checklist critique — are deliberate and should be overlooked. They exist to keep the implementation small enough to hold in your head while making the core mechanism visible.

The abstractions — typed items with heat, thermal mass, weighted nerd selection, provenance tracking — are the takeaway. They describe a general pattern for non-pipelined generative systems that is simpler than LLM orchestration, more flexible than fixed pipelines, and expressive enough to produce varied output from minimal rules. Whether this pattern scales to production-quality creative generation is an open question. The caricature's job is not to answer that question but to make it worth asking.

---

## References

- Smith, A. M., & Mateas, M. (2011). Computational Caricatures: Probing the Game Design Process with AI. *Proceedings of the Seventh AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment (AIIDE)*. https://adamsmith.as/papers/caricatures.pdf
- Erman, L. D., Hayes-Roth, F., Lesser, V. R., & Reddy, D. R. (1980). The Hearsay-II speech-understanding system: Integrating knowledge to resolve uncertainty. *ACM Computing Surveys*, 12(2), 213–253.
- Garbe, J., Kreminski, M., Samuel, B., Wardrip-Fruin, N., & Mateas, M. (2019). StoryAssembler: An Engine for Generating Dynamic Choice-Driven Narratives. *Proceedings of the 14th International Conference on the Foundations of Digital Games (FDG)*.

---

## Appendix: Full Source Listing Reference

| File | Lines | Purpose |
|------|-------|---------|
| `blackboard.py` | 105 | Blackboard, Item, Heat — the shared workspace |
| `nerds.py` | 365 | Base Nerd + 9 nerds + movie/palette/typeface/layout databases |
| `render.py` | 187 | PIL poster compositor with grain/vignette/posterize effects |
| `main.py` | 144 | Main tick loop, nerd selection, caricature summary output |
| **Total** | **801** | |
