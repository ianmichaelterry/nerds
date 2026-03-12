# NERDS Week 10: LLM-Powered Critique and Intelligent Refinement

**Continuing from Week 9: Idempotent Nerds and the Multi-Alternative Blackboard**

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
| KeywordExtractor | *(new in week 9)* | `bb.has(MovieData) and not bb.has(Keywords)` |
| GenrePalette | `bb.has(MovieData) and not bb.has(ColorPalette)` | `bb.has(MovieData)` |
| TypefacePicker | `not bb.has(Typeface)` | *(removed -- just cooldown)* |
| LayoutPicker | `not bb.has(Layout)` | *(removed -- just cooldown)* |
| HeroImageGen | `bb.has(ColorPalette) and not bb.has(HeroImage)` | `bb.has(ColorPalette)` |
| IconFetcher | `bb.has(MovieData) and bb.has(ColorPalette) and not bb.has(IconImage)` | `bb.has(Keywords) and bb.has(ColorPalette)` |
| GrainEffect | `bb.has(HeroImage) and not bb.has(PostEffect)` | `bb.has(HeroImage)` |
| Critic | *(no change -- already repeatable)* | *(no change)* |
| CompletionJudge | *(gated by critique score)* | *(+ min_tick=30)* |

**`vocabulary.py` changes -- SHACL shapes:**

All `_lacks_type()` constraints removed from SHACL shapes, except on MoviePickerShape (run-once, since it queries Wikidata) and CompletionShape (the main loop ends when Completion appears, so there's no point in producing duplicates).

**`nerds.py` changes -- cooldown rates:**

IconFetcher had `cooldown_rate=99`, which was a hack to enforce run-once (99 ticks of cooldown effectively meant "never again" in a 30-tick run). Reduced to `cooldown_rate=5` so it can fire multiple times with reasonable spacing. MoviePicker and KeywordExtractor keep their `cooldown_rate=99` since they remain run-once (one movie per run, one set of keywords per movie).

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

### CompletionJudge heat bump and minimum tick

With more nerds eligible to run at any given tick, the CompletionJudge (which has `cooldown_rate=1` and is eligible every tick once the Critic scores >= 0.8) was getting crowded out by random selection. Its heat was bumped from `MEDIUM` to `HOT` to give it better odds of being selected promptly once the poster is ready.

The CompletionJudge also gained a `min_tick` parameter (set to 30). It will not become eligible until the blackboard reaches tick 30, regardless of critique score. This guarantees the system has time to iterate on content -- producing multiple alternatives, re-rendering poster critiques, accumulating competing palettes and icons -- before jumping to completion. The max tick budget was raised to 50 to match, giving 20 ticks of runway after the CompletionJudge becomes eligible.

---

## KeywordNerd: plot-derived icon search terms

### The problem

In week 8, IconNerd searched the Noun Project using a hardcoded `GENRE_ICON_TERMS` mapping (e.g., `"sci-fi" -> ["robot", "spaceship", "planet", ...]`). This produced genre-appropriate icons but nothing specific to the actual movie. A sci-fi film about time travel and a sci-fi film about alien contact would get the same pool of search terms.

### The fix: OMDb API + noun extraction

A new `KeywordNerd` queries the [Open Movie Database API](https://www.omdbapi.com/) for the movie's short plot string, using both title and year to disambiguate (many titles are reused across decades). It then extracts likely nouns from the plot via stop-word filtering and verb/adjective suffix removal -- a lightweight heuristic that avoids an NLP dependency.

The extracted keywords go onto the blackboard as a `Keywords` item with:
- `nerds:keywordList` -- comma-separated keyword strings
- `nerds:keywordSource` -- `"omdb"` or `"genre"` (indicating which path produced them)

If the OMDb lookup fails (no API key, movie not found, no plot available), the nerd falls back to the existing `GENRE_ICON_TERMS` for the movie's genre. This is a graceful degradation: the system never fails to produce keywords, it just produces less specific ones.

The KeywordNerd is run-once (`cooldown_rate=99`, gated by `not bb.has(Keywords)`) since there's one movie per run and the plot doesn't change.

### IconNerd: keyword-driven search with retries

The IconNerd now depends on `Keywords` + `ColorPalette` (was `MovieData` + `ColorPalette`). Instead of picking from a hardcoded genre term list, it:

1. Picks a `Keywords` item from the blackboard.
2. Selects a random subset of 1-3 keywords as a compound search query.
3. Searches the Noun Project API with that query.
4. If the search returns no results, retries up to **2 more times** with a different random keyword selection.
5. If all 3 attempts fail, returns empty (goes on cooldown, will try again later with fresh keyword picks).

This means the same movie can produce different icons on different IconNerd firings -- one run might search "robot planet", another "alien circuit" -- and each successful search adds a competing `IconImage` to the blackboard for the heat system to select among.

### SHACL shape changes

- New `KeywordShape` requires `MovieData` on the blackboard.
- `IconShape` updated to require `Keywords` (was `MovieData`) + `ColorPalette`.

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
| `main.py` | Tick loop, SHACL validation, nerd selection, approved-asset final render | ~440 | Modified |
| `blackboard.py` | RDF graph-backed blackboard with PROV-O provenance, fingerprint queries | ~215 | Modified |
| `nerds.py` | 12 specialist nerds reading/writing RDF triples | ~975 | Modified (PosterCriticNerd, KeywordNerd added; IconNerd reworked) |
| `vocabulary.py` | Namespaces, SKOS concept scheme, SHACL shapes | ~260 | Modified (Keywords + PosterCritique concepts + shapes) |
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
- Keyword extraction uses stop-word filtering, not real NLP -- it works well enough for short plot strings but wouldn't scale to longer text.

**Abstractions (to be reused in the future):**
- RDF graph blackboard with SKOS-typed items and PROV-O provenance.
- SHACL preconditions: declarative, machine-readable nerd activation rules.
- Schema.org vocabulary: movie data is web-standard, sourced from Wikidata SPARQL.
- OMDb API: plot-derived keywords for content-aware icon search, with graceful fallback to genre terms.
- Noun Project API: keyword-driven icon search via OAuth1, with retry on different keyword subsets.
- Heat + thermal mass driving selection among competing alternatives.
- Idempotent nerds: specialists that can run repeatedly, producing alternatives rather than filling slots.
- Input fingerprinting: critics track what they've already evaluated, preventing duplicate work.
- Approved-asset rendering: the final output reproduces an approved combination rather than re-rolling.
- Minimum-tick gating: the CompletionJudge defers until tick 30, ensuring content iteration before wrap-up.

---

## Addendum: Compositing and Composite Critics

### CompositeNerd ("Compositor")

With icons and hero images coexisting on the blackboard as separate items, the poster renderer was the only place they were combined -- and it used fixed layout positions. The CompositeNerd introduces a pre-render compositing step: pick two image items from the blackboard, overlay them with a random offset using ImageMagick, and put the result back on the blackboard as a new `CompositeImage`.

**How it works:**

1. **Pick two images.** Any `HeroImage`, `IconImage`, or existing `CompositeImage` on the blackboard qualifies. The nerd picks two distinct items via `bb.pick()` (heat-weighted).
2. **Materialize to files.** Images live on the blackboard in different formats: HeroImage as block-color data, IconImage as base64 PNG, CompositeImage as a file path. A `_materialize_image()` helper renders each to a temporary RGBA PNG.
3. **Compute expanded canvas.** The overlay offset is chosen randomly, ranging from fully off the top-left edge to fully off the bottom-right. Rather than clipping to the base image bounds (as `composite` would), the nerd computes the minimum bounding canvas that contains both images at their positions:
   ```python
   left = min(0, offset_x)
   top  = min(0, offset_y)
   canvas_w = max(base_w, offset_x + overlay_w) - left
   canvas_h = max(base_h, offset_y + overlay_h) - top
   ```
4. **ImageMagick `convert`.** The compositor uses `convert -size WxH xc:none` to create a transparent canvas, then composites both images onto it at their computed positions. This avoids clipping and preserves the full extent of both sources.
5. **XMP sidecar.** An RDF/XML sidecar file records where each source image landed in the result, using `nerds:compositeSources` as an `rdf:Bag` of source entries. Each entry stores the source item URI, type, and bounding box (x, y, width, height) in the composite coordinate system.

**Transitive source tracking:** If either input is itself a `CompositeImage`, its XMP sidecar is read and its source entries are merged into the new sidecar with adjusted positions. Compositing A+B→C and then C+D→E produces a sidecar for E that describes where A, B, and D all are -- not just "C and D." This is essential for the visibility and contrast critics, which need to reason about original sources.

The CompositeNerd runs with `cooldown_rate=4`, producing competing composites across the run. The heat system selects among them for downstream use.

### VisibilityCriticNerd

The VisibilityCriticNerd assesses whether each source image is actually visible in a composite. A composite where one source is entirely occluded or placed off-canvas is wasted work.

**How it works:**

1. Find `CompositeImage` items that have no `VisibilityCritique` yet (using `_uncritiqued_composites()`).
2. For each source in the XMP sidecar, materialize the original image and compare it pixel-by-pixel against the corresponding region of the composite. A pixel "matches" if all RGB channels are within tolerance (10 per channel). Transparent source pixels are excluded.
3. Visibility score per source = matching pixels / total non-transparent source pixels.
4. Overall score = minimum across all sources (the weakest link).
5. **Heat adjustment:** score < 0.2 → set composite heat to `COLD`; score ≥ 0.5 → set to `HOT`.

The numpy-vectorized comparison handles large images efficiently.

### ContrastCriticNerd

The ContrastCriticNerd measures whether the sources in a composite are visually distinguishable from each other. Two images composited together that happen to be similar colors produce a muddy result.

**How it works:**

1. Find uncritiqued `CompositeImage` items (same pattern as VisibilityCritic).
2. For each source, compute the mean RGB color of its region in the composite (clamped to canvas bounds).
3. Compute the minimum pairwise Euclidean distance between all source mean colors.
4. Score = min_distance / 200, capped at 1.0. A score of 1.0 means the closest pair of sources still has an RGB distance of 200+ (very distinct). A score near 0 means two sources blend together.
5. **Heat adjustment:** score < 0.15 → `COLD`; score ≥ 0.4 → `HOT`.

### Scale-to-fit rendering

Composites can be larger than the poster's image area (since the canvas expands to contain both sources at any offset). The renderer now scales composites down to fit, preserving aspect ratio and never scaling up:

```python
scale = min(target_w / comp_w, target_h / comp_h, 1.0)
```

The scaled composite is centered in the image area.

### Vocabulary and SHACL additions

Three new SKOS concepts:
- `nerds:CompositeImage` (broader: `VisualArtifact`) -- two or more images composited via ImageMagick, tracked by XMP sidecar.
- `nerds:VisibilityCritique` (broader: `MetaArtifact`) -- per-source visibility scores for a composite.
- `nerds:ContrastCritique` (broader: `MetaArtifact`) -- inter-source contrast measurement for a composite.

Three new SHACL shapes:
- `CompositeShape` -- requires `ColorPalette` (ensures visual content exists); Python `can_run()` further requires ≥ 2 image items.
- `VisibilityCritiqueShape` -- requires `CompositeImage`.
- `ContrastCritiqueShape` -- requires `CompositeImage`.

Both critic types are added to `_META_TYPES`, preventing them from triggering other critics' "has anything new appeared?" checks.

### Integration with existing nerds

- **PosterCriticNerd** now includes `composite` in its picks (via `bb.pick(NERDS.CompositeImage)`), and the approved-asset final render in `main.py` extracts `nerds:usedComposite` from passing critiques.
- **Narrator** (`main.py`) gained narration cases for "Compositor", "VisibilityCritic", and "ContrastCritic".

### Updated file inventory

| File | Purpose | Lines | Changed in addendum? |
|---|---|---|---|
| `main.py` | Tick loop, SHACL validation, nerd selection, approved-asset final render | ~475 | Yes (narration, composite asset extraction) |
| `blackboard.py` | RDF graph-backed blackboard with PROV-O provenance | ~225 | Yes (`set_heat()` method) |
| `nerds.py` | 15 specialist nerds + compositing helpers | ~1490 | Yes (CompositeNerd, VisibilityCriticNerd, ContrastCriticNerd, helpers) |
| `vocabulary.py` | Namespaces, SKOS concept scheme, SHACL shapes | ~285 | Yes (3 concepts, 3 shapes) |
| `render.py` | PIL-based poster compositor (supports explicit picks + composite scale-to-fit) | ~450 | Yes (composite rendering) |
| `narrator.py` | Showboat-style markdown narrative generator | ~165 | No |

### Sample run (seed 100)

```
  tick 24: Compositor -> ['CompositeImage']    # 978x687, hero + icon
  tick 29: ContrastCritic -> ['ContrastCritique']  # min_dist=59.1, score=0.30
  tick 30: Compositor -> ['CompositeImage']    # 853x555, hero + icon
  tick 34: CompletionJudge -> ['Completion']
```

Two composites produced, one contrast-critiqued (score 0.30 — moderate contrast, heat stays MEDIUM). The system now has 15 nerds producing 33 items across 34 ticks, with composites competing on the blackboard alongside raw images for use in the final poster.

---

## What changed in Week 10: LLM-Powered Poster Critique and Critique-Responsive Nerds

### The problem

The PosterCriticNerd (added in Week 9) always returned "passes" — it was a placeholder. Without real visual evaluation, the system couldn't improve posters based on feedback. Additionally, nerds produced alternatives but had no mechanism to respond to specific critiques.

### The fix: Bayleaf API integration

We connected to the Bayleaf API (an OpenAI-compatible proxy backed by OpenRouter) to get LLM-powered visual critique. The current system uses `z-ai/glm-5` model.

**Challenges and solutions:**

1. **No vision support in chat completions.** Bayleaf's chat completions endpoint doesn't support base64 image inputs. We work around this by sending a detailed *text description* of the poster components instead of the actual image.

2. **Rate limiting.** The free tier has limited requests. The system gracefully falls back to "pass" when the API is unavailable.

3. **JSON parsing.** The LLM sometimes outputs markdown-wrapped JSON. We extract the JSON block using regex.

### PosterCriticNerd now calls the LLM

The critic now sends a structured prompt describing:
- Movie title, genre, and director
- Color palette (key, accent, mid colors)
- Title text and subtitle
- Typeface name and style
- Layout template name
- Composite image contents (from XMP sidecar metadata)
- Post-effects applied

Example critique request:
```
You are a movie poster design critic. Critique this poster for a drama film 
titled "The Tarantula" directed by George D. Baker.

Poster description: background color: #355259; accent color: #42a56f; 
genre-based palette for drama; title: The - Tarantula; typeface: serif-bold; 
composite image containing: icon(s): Theater in #42a56f; hero image with 
color blocks: #42a56f, #3b7e64

Evaluate: visual appeal, typography, color harmony, composition, genre appropriateness.
Respond with JSON: {"passes": bool, "score": 0-1, "issues": [], "strengths": [], "summary": "..."}
```

The LLM returns structured feedback that gets stored on the blackboard:
- `nerds:passes` — boolean
- `nerds:critiqueScore` — float 0-1
- `nerds:critiqueIssues` — comma-separated issues
- `nerds:critiqueStrengths` — comma-separated strengths  
- `nerds:critiqueSummary` — brief assessment

### Critique-responsive nerds

Added `bb.get_recent_critique_issues()` to the Blackboard, returning issues from recent failing PosterCritiques. Three nerds now respond to specific critique feedback:

**TypefaceNerd:**
- If critique mentions "typeface", "font", or "typography", avoids the problematic style
- Picks a different typeface family
- Gets bumped to HOT heat when responding

**GenrePaletteNerd:**
- If critique mentions "color", "palette", or "contrast", switches genre palette
- Example: "analogous colors" issue triggers action palette

**IconNerd:**
- If critique mentions "imagery", "visual", or "icon", tries different keywords
- Gets bumped to HOT heat when responding

### Updated CompletionNerd

Now requires both:
1. Completeness score >= 80% (from CritiqueNerd)
2. A passing PosterCritique with score >= 0.5

### Composite-focused rendering

**Problem:** A composite can contain hero images and icons, but the renderer was using both separate hero/icon AND composite.

**Solution:**
- `render.py` now prefers composite over separate hero/icon
- If composite exists, it's used as the primary visual element
- Falls back to separate hero+icon only if no composite exists

**CritiqueNerd updated completeness check:**
- "Visual element" requirement: HeroImage OR CompositeImage
- "Icon element" requirement: IconImage OR CompositeImage
- Issues now say "missing_hero_or_composite" or "missing_icon_or_composite"

**PosterCriticNerd describes composite contents:**
- Reads XMP sidecar to find source items
- For icons: shows search term and accent color
- For hero images: shows colors used in blocks
- Example: "composite image containing: icon(s): Theater in #42a56f; hero image with color blocks: #42a56f, #3b7e64"

### Updated file inventory

| File | Purpose | Changes |
|---|---|---|
| `nerds.py` | Specialist nerds | Added Bayleaf API client, LLM critique in PosterCriticNerd, critique-responsive nerds (Typeface, Palette, Icon) |
| `blackboard.py` | RDF blackboard | Added `get_recent_critique_issues()` method |
| `render.py` | Poster rendering | Prefers composite over separate hero/icon |
| `main.py` | Tick loop | Updated narration for LLM critique, selects highest-scoring passing PosterCritique |

### Sample run (seed 42, 35 ticks)

```
  tick 7: PosterCritic -> LLM critique: passes=False, score=0.35
  tick 14: CompletionJudge -> Completion (passing PosterCritique found)
```

The first PosterCritique got a real LLM assessment:
- passes: false
- score: 0.35
- Issues: "Script-italic typeface is fundamentally wrong for a drama", "Title hierarchy is confusing", "No imagery"

The system continues to iterate and can now respond to specific critiques by producing better alternatives.

### What the caricature claims now

**Claim:** Diverse generative output emerges from dumb specialists + heat-driven salience + random selection + LLM-powered critique + critique-responsive refinement. No explicit pipeline.

**Oversimplifications:**
- LLM critique is text-based (no actual vision)
- Critique responses are simple keyword matching, not semantic understanding
- The system still produces basic posters (icons + color blocks)

**Abstractions:**
- Bayleaf API integration (OpenAI-compatible)
- Text-to-critique pipeline with JSON parsing
- Critique issue extraction and nerd response triggers
- Composite-as-primary-visual rendering
- XMP metadata for composite content description

---

## Week 10 Part 2: Sophisticated Critique Responses

### The problem

The initial critique response system used simple keyword matching (if critique says "typeface", avoid script fonts). This was brittle and one-dimensional.

### Solution: Structured Issue Extraction

Added an LLM-powered issue extraction function that converts critique text into structured, actionable remediation instructions:

```
{
  "issue_type": "typeface_mismatch",
  "severity": "high",
  "confidence": 0.9,
  "remediation": "switch_to",
  "target": "serif-bold",
  "nerd": "TypefaceNerd"
}
```

The LLM analyzes both the issue string and summary to extract:
- **issue_type**: Categorized issue (typeface_mismatch, color_palette_weak, title_hierarchy_confusing, etc.)
- **severity**: high/medium/low
- **confidence**: 0-1 certainty measure
- **remediation**: switch_to, add, remove, modify, none
- **target**: Specific target for remediation
- **nerd**: Which nerd should respond

### Fallback: Keyword-based extraction

If the LLM fails (rate limiting), falls back to keyword matching for basic responses.

### Multiple responding nerds

Enhanced existing nerds and added new ones:

**TypefaceNerd:**
- Checks structured issues for typeface_mismatch
- Uses confidence threshold (0.7+) for strong responses
- Falls back to keyword matching if no structured issues

**GenrePaletteNerd:**
- Checks structured issues for color_palette_weak
- Switches to target genre palette
- Uses successful remediation patterns

**LayoutNerd:**
- New: Responds to composition_poor issues
- Picks layouts matching the target style

**TitleParserNerd:**
- New: Responds to title_hierarchy_confusing issues
- Simplifies title structure when criticized

### Tracking successful remediations

Added methods to the Blackboard:
- `record_remediation(issue_type, target, success)`: Records whether a remediation worked
- `get_successful_remediations(issue_type)`: Gets successful patterns to reuse

When CompletionNerd declares success, it records which remediations led to the passing critique, enabling the system to learn from successful fixes.

### Confidence-based responses

Nerds now weigh issue confidence:
- High confidence (>=0.7): Strong response, break immediately
- Medium confidence: Consider but continue looking
- Low confidence: Prefer fallback patterns

### Updated file inventory

| File | Purpose | Changes |
|---|---|---|
| `nerds.py` | Specialist nerds | Added `_extract_structured_issues()`, updated all responding nerds |
| `blackboard.py` | RDF blackboard | Added `get_structured_issues()`, `record_remediation()`, `get_successful_remediations()` |

### What the caricature claims now

**Claim:** Diverse generative output emerges from dumb specialists + heat-driven salience + random selection + LLM-powered critique + **intelligent critique-responsive refinement with learning**. No explicit pipeline.

**Oversimplifications:**
- LLM critique is text-based (no actual vision)
- Structured extraction can fail on rate limiting
- Learning patterns require multiple successful runs

**Abstractions:**
- Structured issue extraction pipeline
- Confidence-weighted response selection
- Remediation pattern learning and reuse

---

## Week 10 Part 3: Improved Title Parsing

### The problem

The TitleParserNerd was naively splitting titles on the first space, which caused issues like:
- "The Tarantula" → "The" (primary), "Tarantula" (secondary) — bad!
- "Star Wars" → "Star" (primary), "Wars" (secondary) — bad!

### The fix

Rewrote `_split_title()` with smarter strategies:

1. **Articles kept with title**: "The", "A", "An" stay with the main title
2. **Colon separator**: "Star Wars: Episode IV" → "Star Wars", "Episode IV"
3. **Dash separator**: "Movie - Subtitle" → "Movie", "Subtitle"
4. **Natural phrase splits**: "In the Mood for Love" stays together
5. **Long title handling**: Only splits at natural boundaries for long titles

### Results

| Before | After |
|--------|-------|
| "The Tarantula" → "The", "Tarantula" | "The Tarantula", "" |
| "A Clockwork Orange" → "A", "Clockwork Orange" | "A Clockwork Orange", "" |
| "Star Wars: Episode IV" → "Star", "Wars: Episode IV" | "Star Wars", "Episode IV" |
| "In the Mood for Love" → "In", "the Mood for Love" | "In the Mood for Love", "" |

### Multiple title variations (word-balanced splits)

**The problem:** The TitleParserNerd produced only one title split, so there was no variety for the critic to evaluate.

**The fix:** TitleParserNerd now generates multiple title split variations using word-balanced strategies (never splitting a word in half):

```
"The Voice from the Minaret":
  full_title: 'The Voice from the Minaret' | ''
  two_line: 'The Voice from' | 'the Minaret'
  three_line: 'The Voice\nfrom the' | 'Minaret'
  natural_phrase: 'The Voice' | 'from the Minaret'
```

Strategies:
1. **full_title**: no split
2. **subtitle**: colon/dash separator ("Star Wars" | "Episode IV")
3. **two_line**: distribute words evenly across 2 lines
4. **three_line**: for long titles (5+ words), 3 lines
5. **natural_phrase**: split at prepositions ("of", "in", "with", etc.)

The renderer was updated to handle newlines in titles for proper multi-line display.

**Benefits:**
- Critic can evaluate different title layouts
- System learns which title strategies work for different genres
- "A Clockwork Orange" → "A Clockwork" | "Orange" (not "A" | "Clockwork Orange")
- "In the Mood for Love" → "In the Mood" | "for Love" (natural break)

---

## Week 10 Part 4: Bug Fixes and Quality Improvements

### 1. Title fitting

**Problem:** Long titles could go outside the poster bounds.

**Solution:** Added font size auto-shrinking in render.py:
- Start at max font size (52pt)
- Shrink by 4pt increments if title exceeds poster width
- Minimum font size: 24pt
- If even minimum doesn't fit, mark title as not fitting

### 2. Composite offsets

**Problem:** Icons were overlapping when composited because offsets were too small.

**Solution:** Updated Compositor to prefer non-overlapping placement:
- 60% chance: side-by-side placement (no overlap)
- 30% chance: partial overlap (at most 50%)
- 10% chance: full random

### 3. Critic approval for final poster

**Problem:** Even composites that failed VisibilityCritic or ContrastCritic could be used in the final poster.

**Solution:** Modified final asset selection in main.py to require:
- Composite must have passed VisibilityCritic (score >= 0.7)
- Composite must have passed ContrastCritic (score >= 0.3)

### 4. TitleContrastCritic

**Problem:** Title color might not contrast well with background or composite.

**Solution:** Added TitleContrastCriticNerd that:
- Compares title color (accent) to background (key) color
- Also checks distance to composite colors
- Sets heat based on contrast score (low contrast -> COLD, high -> HOT)
- Example output: `min_dist=89.0, score=0.59`

### File changes

| File | Change |
|---|---|
| render.py | Title font auto-shrink to fit |
| nerds.py | Composite offset strategy, TitleContrastCriticNerd |
| main.py | Require critic approval for final assets |
