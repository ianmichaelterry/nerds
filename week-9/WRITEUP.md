# NERDS Week 9: Idempotent Nerds and the Multi-Alternative Blackboard

**Continuing from Week 8: Semantic NERDS**

---

## Where we were: Week 7

Week 7 established the core NERDS system as a computational caricature (after Smith & Mateas, AIIDE 2011). Nine specialist "nerds" read from and wrote to a shared blackboard, coordinated by heat-based salience and random selection. No LLM at runtime, no explicit pipeline.

The system worked, but had two architectural limitations that kept it closer to a pipeline than a true blackboard:

1. **Ad-hoc data model.** The blackboard was a `list[Item]` with Python dicts as payloads. Type tags were strings. Provenance was a `created_by: str` field. There was no way for an external tool to inspect the blackboard, no standard vocabulary, and no formal schema for what items looked like.

2. **Run-once nerds.** Every nerd's `can_run()` method contained a gate like `not bb.has("ColorPalette")`. Once a nerd produced its artifact type, it was permanently locked out. The blackboard accumulated exactly one item of each type, and the generation always converged on a single linear path through the artifact space. Despite the random selection mechanism, the system always produced the same *kinds* of artifacts in roughly the same order -- just with different values.

3. **Hardcoded movie data.** Five films lived in a Python list. The claim about diverse generative output rang hollow when the input space was five dictionaries.

Week 7 also produced planning documents for the semantic upgrade (STANDARDS.md, STANDARDS-BRIEF.md) and for a distillation pipeline (DISTILLATION.md) that would use Training-Free GRPO to extract nerd designs from LLM-simulated trajectories.

---

## What changed in Week 8: The Semantic Upgrade

Week 8 replaced the ad-hoc data model with W3C semantic web standards. The code changed substantially; the architecture stayed the same.

### Blackboard: list[Item] -> RDF graph

The blackboard went from a Python list of dataclass instances to an `rdflib.Graph`. Every item became a set of RDF triples:

| Before (Week 7) | After (Week 8) |
|---|---|
| `Item(type_tag="ColorPalette", value={"key": (30, 40, 80), ...})` | `nerds:item_5 dcterms:type nerds:ColorPalette ; nerds:keyColor "#1e2850" .` |
| `item.created_by = "GenrePalette"` | `nerds:item_5 prov:wasAttributedTo nerds:agent_GenrePalette .` |
| `item.birth_tick = 6` | `nerds:item_5 dcterms:created "6"^^xsd:integer .` |
| `item.heat = Heat.HOT` | `nerds:item_5 nerds:heat nerds:Hot .` |
| `bb.has("ColorPalette")` | SPARQL pattern match against `dcterms:type` |

The standards in play:

- **RDF** (W3C Rec 2014): The graph data model. Items are triples, not dicts.
- **PROV-O** (W3C Rec 2013): Every item is a `prov:Entity`, every nerd a `prov:SoftwareAgent`, every `run()` invocation a `prov:Activity`. Full derivation chains.
- **SKOS** (W3C Rec 2009): Artifact types became a concept scheme with hierarchy (`nerds:ColorPalette skos:broader nerds:VisualArtifact`).
- **SHACL** (W3C Rec 2017): Nerd preconditions became declarative shapes. The scheduler validates the blackboard against each nerd's SHACL shape to check eligibility.
- **Schema.org**: Movie data uses `schema:Movie` vocabulary -- `schema:name`, `schema:director`, `schema:genre`, `schema:actor`.
- **Dublin Core** (ISO 15836): Metadata fields -- `dcterms:type`, `dcterms:created`, `dcterms:identifier`.

### MoviePicker: hardcoded list -> Wikidata SPARQL

The five-film Python list was replaced with a two-phase Wikidata query:

1. **Phase 1**: A fast SPARQL SELECT picks 20 random notable films (filtered by having a director, genre, and image -- proxies for "notable enough"). Randomization uses MD5 hash of the film URI plus a random salt.
2. **Phase 2**: A targeted SPARQL SELECT fetches director, cast, genre, and year for the selected film.

Fallback to the original five hardcoded films if Wikidata is unreachable.

The data goes onto the blackboard as `schema:Movie`-shaped RDF triples. No parsing, no key mapping -- Wikidata speaks Schema.org, the blackboard speaks Schema.org.

### IconFetcher: colored rectangles -> Noun Project API

A new nerd (`IconNerd`) fetches genre-relevant icons from the Noun Project via OAuth1 API. The icon is downloaded as a tinted PNG (colored to match the accent color) and stored as base64 on the blackboard. The renderer composites it as the central visual element.

Genre-to-icon-term mappings cover 13 genres with multiple search terms each (e.g., `"sci-fi" -> ["robot", "spaceship", "planet", "laser", "alien", "circuit"]`).

### New files

- **`vocabulary.py`**: Namespace definitions, SKOS concept scheme, SHACL shape builder.
- **`narrator.py`**: A "Showboat-style" narrative document generator (inspired by Simon Willison's approach). Accumulates a markdown story of the run: which nerd fired, what it produced, data excerpts, provenance graph, blackboard summary.

### Post-processing

Week 8 added a `chromatic_aberration` post-effect (RGB channel offset) to the existing grain, vignette, and posterize effects.

### What didn't change

The core architecture -- tick loop, heat decay, thermal mass, cooldown, random weighted selection -- was identical to week 7. The nerds themselves stayed deliberately dumb. The intelligence upgrade was in the data model, not the agents.

---

## What changed in Week 9: Idempotent Nerds

### The problem

In weeks 7 and 8, almost every nerd was run-once. The gates took two forms:

1. **Python `can_run()` gates**: `not bb.has(NERDS.ColorPalette)` in GenrePaletteNerd, `not bb.has(NERDS.Layout)` in LayoutNerd, etc.
2. **SHACL `_lacks_type` constraints**: `sh:qualifiedMaxCount 0` for the nerd's output type on the blackboard.

These gates meant the blackboard always had exactly one of each artifact type. The heat-weighted `bb.pick()` method -- the mechanism designed to select among alternatives -- never had alternatives to select from. The system's randomness was limited to *which values* a nerd produced, not *which of several competing items* downstream nerds would choose.

This also meant the generation order was essentially fixed. MoviePicker had to go first (nothing else could run without MovieData). TitleParser and GenrePalette could only go after MoviePicker. And so on. The heat-weighted random selection was choosing among nerds that happened to be eligible at that moment, but eligibility was so constrained that there was usually only one or two real choices.

### The fix

Remove the run-once gates. Keep the positive dependency checks.

**`nerds.py` changes -- `can_run()` methods:**

| Nerd | Before | After |
|---|---|---|
| MoviePicker | *(unchanged -- run-once, queries Wikidata)* | `not bb.has(NERDS.MovieData)` |
| TitleParser | `bb.has(MovieData) and not bb.has(TitleChunks)` | `bb.has(MovieData)` |
| GenrePalette | `bb.has(MovieData) and not bb.has(ColorPalette)` | `bb.has(MovieData)` |
| TypefacePicker | `not bb.has(Typeface)` | *(removed -- just cooldown)* |
| LayoutPicker | `not bb.has(Layout)` | *(removed -- just cooldown)* |
| HeroImageGen | `bb.has(ColorPalette) and not bb.has(HeroImage)` | `bb.has(ColorPalette)` |
| IconFetcher | `bb.has(MovieData) and bb.has(ColorPalette) and not bb.has(IconImage)` | `bb.has(MovieData) and bb.has(ColorPalette)` |
| GrainEffect | `bb.has(HeroImage) and not bb.has(PostEffect)` | `bb.has(HeroImage)` |
| Critic | *(no change -- already repeatable)* | *(no change)* |
| CompletionJudge | *(no change -- gated by critique score)* | *(no change)* |

**`vocabulary.py` changes -- SHACL shapes:**

All `_lacks_type()` constraints removed from SHACL shapes, except on MoviePickerShape (run-once, since it queries Wikidata) and CompletionShape (the main loop ends when Completion appears, so there's no point in producing duplicates).

**`nerds.py` changes -- cooldown rates:**

IconFetcher had `cooldown_rate=99`, which was a hack to enforce run-once (99 ticks of cooldown effectively meant "never again" in a 30-tick run). Reduced to `cooldown_rate=5` so it can fire multiple times with reasonable spacing. MoviePicker keeps its `cooldown_rate=99` since it remains run-once.

### The result

A run with `--seed 42` now produces 23 items across 23 ticks:

```
  tick 1: TypefacePicker -> ['Typeface']
  tick 2: MoviePicker -> ['MovieData']       # The Tarantula (1916)
  tick 3: TitleParser -> ['TitleChunks']
  tick 4: Critic -> ['Critique']             # 33% complete
  tick 5: TypefacePicker -> ['Typeface']      # second typeface
  tick 6: GenrePalette -> ['ColorPalette']
  tick 7: HeroImageGen -> ['HeroImage']
  tick 8: Critic -> ['Critique']             # 67% complete
  tick 9: IconFetcher -> ['IconImage']
  tick 10: GrainEffect -> ['PostEffect']
  tick 11: LayoutPicker -> ['Layout']
  tick 12: HeroImageGen -> ['HeroImage']      # second hero image
  tick 13: PosterCritic -> ['PosterCritique'] # renders temp poster, "passes"
  tick 14: GenrePalette -> ['ColorPalette']   # second palette
  tick 15: IconFetcher -> ['IconImage']        # second icon
  tick 16: GrainEffect -> ['PostEffect']      # second post-effect
  tick 17: TypefacePicker -> ['Typeface']     # third typeface
  tick 18: TitleParser -> ['TitleChunks']     # second title parse
  tick 19: Critic -> ['Critique']             # 100% complete
  tick 20: LayoutPicker -> ['Layout']         # second layout
  tick 21: IconFetcher -> ['IconImage']        # third icon
  tick 22: GenrePalette -> ['ColorPalette']   # third palette
  tick 23: CompletionJudge -> ['Completion']
```

The blackboard has multiple items of most types: 3 Typefaces, 3 ColorPalettes, 3 IconImages, 2 HeroImages, 2 Layouts, 2 TitleChunks, 2 PostEffects. The heat system gives downstream nerds and the renderer genuine choices -- `bb.pick()` selects among candidates weighted by heat, so recently produced items are preferred but older alternatives aren't excluded. The final poster is rendered using the exact assets approved by the PosterCritic at tick 13.

### Why this matters for the caricature

The original NERDS claim was: "Diverse generative output emerges from dumb specialists + heat-driven salience + random selection." But with run-once nerds, the heat system was decorative. Items cooled off, but nothing competed with them. The poster was always built from exactly one palette, one layout, one typeface.

With idempotent nerds, the blackboard becomes a genuine marketplace of alternatives. Multiple palettes coexist, each cooling at different rates. The renderer picks the hottest one, but might grab an older palette if it has high thermal mass and the newer one has already cooled. Different runs produce not just different values but different *compositions of alternatives*. The heat system now does real work.

This also makes the system more robust. If a nerd produces a bad result (e.g., a palette with poor contrast), the system can route around it -- another palette will appear in a few ticks, and the heat system will naturally prefer the newer one.

---

## Critique fingerprinting and deduplication

With idempotent nerds, critic nerds face a new problem: they might re-evaluate the same state repeatedly and waste ticks producing duplicate critiques. Two mechanisms prevent this.

### Input fingerprinting

Every critique now carries a `nerds:inputFingerprint` property -- a deterministic string derived from the specific inputs the critic examined. Before producing a critique, the nerd checks whether any existing critique of the same type already has that fingerprint. If so, it returns empty (nothing new to say).

The fingerprint is computed differently depending on what the critic examines:

- **CritiqueNerd** (completeness checker): fingerprint is the sorted set of *type concepts* currently present on the blackboard. Since types only accumulate (we never remove items), the fingerprint only changes when a new artifact type first appears. Once the Critic has assessed a given combination of present/absent types, it won't repeat itself.
- **PosterCriticNerd** (visual critic): fingerprint is the sorted set of *specific item URIs* that were picked for the poster. Even if the same types are present, different items (e.g., a different palette or layout) produce a different fingerprint.

### "Nothing new" eligibility check

Both critic nerds also check in `can_run()` whether any non-meta item has been added to the blackboard since their most recent critique. Meta items (Critique, PosterCritique, Completion) don't count as "new material." If nothing new has appeared, the critic declines to run, saving the tick for a productive nerd.

This uses two new Blackboard helpers:

- `newest_item_tick(exclude_types)`: returns the creation tick of the most recent item, ignoring specified types.
- `has_fingerprint(type_concept, fingerprint)`: checks if any item of a given type carries a matching fingerprint.

### Interaction between the two mechanisms

The `can_run()` check is a fast heuristic: "has anything changed?" The fingerprint check in `run()` is the authoritative guard: "have I already said this?" A critic can pass the `can_run()` check (a new item appeared) but still find that the randomly picked combination matches a previous fingerprint. In that case it returns empty and goes on cooldown. This costs one tick but is rare.

---

## PosterCriticNerd: intermediate render and visual critique

### Motivation

With multiple alternatives on the blackboard, the final poster depends on which items get picked. Before week 9, the system had no way to evaluate a poster *before* the final render. The PosterCriticNerd closes this loop: it picks a specific set of assets, renders a temporary poster, and produces a critique of the result.

### How it works

1. **Pick assets**: heat-weighted `bb.pick()` for each item type (MovieData, TitleChunks, ColorPalette, Layout, HeroImage, Typeface, PostEffect, IconImage). Some may be None if that type hasn't been produced yet.
2. **Fingerprint check**: compute fingerprint from the picked item URIs. If a PosterCritique with this fingerprint already exists, return empty.
3. **Render temp poster**: call `render_poster(bb, temp_path, picks=picks)` with the specific items. The temp image goes to `output/temp/`, which is cleared at the start of each run.
4. **Produce critique**: for now, always "passes." The critique item stores:
   - `nerds:inputFingerprint` -- the dedup key
   - `nerds:passes` -- boolean (always True for now)
   - `nerds:posterImage` -- path to the temp poster file
   - `nerds:usedMovie`, `nerds:usedTitle`, `nerds:usedPalette`, etc. -- URIs of the exact items used

The `render_poster` function gained an optional `picks` parameter (a dict mapping item-type keys to specific URIRef nodes). When provided, these override the default `bb.pick()` for each slot. This lets both the PosterCriticNerd and the final render use an exact set of items.

### SHACL shape

The PosterCriticNerd's SHACL shape requires MovieData, TitleChunks, and ColorPalette. These are the minimum needed to render a recognizable poster. Layout, HeroImage, Typeface, PostEffect, and IconImage are used if available but not required.

### Approved-assets final render

The final poster render in `main.py` now looks for the latest (heat-weighted) passing PosterCritique and extracts the `nerds:used*` properties to reconstruct the exact picks dict. This guarantees the final output reproduces an approved combination of assets, not a random re-roll.

If no PosterCritique exists (e.g., the system completed before the PosterCriticNerd fired), the render falls back to regular `bb.pick()` behavior.

### CompletionJudge heat bump

With more nerds eligible to run at any given tick, the CompletionJudge (which has `cooldown_rate=1` and is eligible every tick once the Critic scores >= 0.8) was getting crowded out by random selection. Its heat was bumped from `MEDIUM` to `HOT` to give it better odds of being selected promptly once the poster is ready.

---

## Bug fix: Font rendering on Linux

### The problem

A poster generated for "Ott Tanak: The Movie" (with an umlaut: a) rendered with no visible title. The title text was being drawn but was essentially invisible.

### Root cause

All font paths in `render.py` were macOS-specific (`/System/Library/Fonts/...`). On this Linux/WSL2 system, every candidate font failed silently, falling through to `ImageFont.load_default()` -- which returns a 10-pixel bitmap font regardless of the requested size. A 10px title on a 900px poster is a speck.

The umlaut wasn't the direct cause (PIL's default font does handle basic Latin Extended characters), but the tiny size made it invisible. Any title would have been nearly invisible on Linux.

### The fix

1. Added Linux font paths to all three font-loading functions, prioritizing DejaVu Sans (present on virtually all Linux systems, excellent Unicode coverage including Latin Extended, Cyrillic, Greek, etc.).
2. Changed the fallback from `ImageFont.load_default()` to `ImageFont.load_default(size=size)`, so even the last-resort font respects the requested size.

The font candidate order is now: Linux paths first (DejaVu Sans Bold/Regular), then macOS paths (Arial, Helvetica), then PIL's built-in font at the correct size.

---

## File inventory

| File | Purpose | Lines | New in week 9? |
|---|---|---|---|
| `main.py` | Tick loop, SHACL validation, nerd selection, approved-asset final render | ~410 | Modified |
| `blackboard.py` | RDF graph-backed blackboard with PROV-O provenance, fingerprint queries | ~215 | Modified |
| `nerds.py` | 11 specialist nerds reading/writing RDF triples | ~810 | Modified (PosterCriticNerd added) |
| `vocabulary.py` | Namespaces, SKOS concept scheme, SHACL shapes | ~260 | Modified (PosterCritique concept + shape) |
| `render.py` | PIL-based poster compositor (supports explicit picks) | ~410 | Modified |
| `narrator.py` | Showboat-style markdown narrative generator | ~165 | No (from week 8) |
| `output/temp/` | Temp poster images from PosterCriticNerd (cleared each run) | -- | New directory |

---

## What the caricature claims now

**Claim (to be quickly recognized):** Diverse generative output emerges from dumb specialists + heat-driven salience + random selection among multiple competing alternatives, with critique-driven approval ensuring the final output is a vetted combination. No LLM at runtime. No explicit pipeline.

**Oversimplifications (to be overlooked):**
- "Images" are Noun Project icons + colored rectangles, not photographs or illustrations.
- Typography uses system fonts, not curated typefaces.
- The completeness critic is a checklist, not aesthetic judgment.
- The poster critic always says "passes" -- real visual evaluation is not yet implemented.
- Multiple alternatives don't yet influence each other (no "this palette is better *because* of that layout").

**Abstractions (to be reused in the future):**
- RDF graph blackboard with SKOS-typed items and PROV-O provenance.
- SHACL preconditions: declarative, machine-readable nerd activation rules.
- Schema.org vocabulary: movie data is web-standard, sourced from Wikidata SPARQL.
- Noun Project API: real curated icons via OAuth1.
- Heat + thermal mass driving selection among competing alternatives.
- Idempotent nerds: specialists that can run repeatedly, producing alternatives rather than filling slots.
- Input fingerprinting: critics track what they've already evaluated, preventing duplicate work.
- Approved-asset rendering: the final output reproduces an approved combination rather than re-rolling.
