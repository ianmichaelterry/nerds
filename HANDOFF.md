# The Poster Room: Project Handoff Document

**Date:** 2026-02-11  
**Status:** Linear pipeline working, ready for heat-based scheduler implementation  
**Last Working Commit:** Nerd-based data fetching + markdown logging implemented

---

## 1. Project Overview

**The Poster Room** is a demonstration of the **Nerds Architecture** - an alternative to LLM-based generative systems that uses specialized "nerds" (expert agents) operating on a shared blackboard with a heat-based salience system.

**Key Concept:** Instead of a monolithic LLM pipeline, we have multiple specialized nerds that:
- Each have a specific domain expertise (titles, colors, typography, etc.)
- Read from and write to a shared "blackboard" (filesystem-based JSON store)
- Are selected based on "heat" (salience/temperature) rather than explicit sequencing
- Can critique and revise each other's work

**Application Domain:** Movie poster generation for *Blade Runner 2049*

---

## 2. What We've Built

### Core System (`poster_room.py`)

**Current Implementation:** Linear pipeline with 13 nerds in hardcoded sequence

**Architecture Components:**

```
┌─────────────────────────────────────────────────────────────┐
│  BLACKBOARD (filesystem JSON store)                         │
│  - Items have: id, type, data, source_nerd, timestamp       │
│  - Cleared on each run                                      │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ read/write
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
   │  NERD 1 │        │  NERD 2 │        │  NERD N │
   │(Research│        │(Image   │        │(Various)│
   │ Nerd)   │        │Fetcher) │        │         │
   └────┬────┘        └────┬────┘        └────┬────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  SCHEDULER     │
                    │ (currently:    │
                    │  linear list)  │
                    └────────────────┘
```

**Nerd Inventory (13 total):**

**Phase 1: Data Fetching**
1. `ResearchNerd` - Loads movie metadata from `metadata.json`
2. `ImageFetcherNerd` - Scans `stills/` directory, loads images
3. `TypefaceArchivistNerd` - Consults `typeface_database.json`
4. `TemplateArchivistNerd` - Loads `template_library.json`
5. `ColorPaletteNerd` - Reads `color_reference.json`

**Phase 2: Analysis**
6. `TitleNerd` - Decomposes title into primary/secondary chunks
7. `ColorAnalyzerNerd` - Analyzes image colors (uses ColorPaletteNerd's reference)
8. `TypographyNerd` - Creates typography specification
9. `TemplateSelectorNerd` - Selects poster template

**Phase 3: Critique & Revision**
10. `CritiqueNerd` - Evaluates color analysis, writes critiques
11. `ColorReviserNerd` - **Separate nerd** that fixes issues (not the same as CritiqueNerd!)

**Phase 4: Production**
12. `CompositorNerd` - Renders final poster image
13. `CompletionNerd` - Decides when poster is complete

**Key Design Decision:** CritiqueNerd identifies problems but DOES NOT fix them. A separate ColorReviserNerd makes corrections. This separation is intentional.

---

## 3. Sample Data Created

Located in `sample_movie/` directory:

```
sample_movie/
├── metadata.json              # Comprehensive movie metadata
├── stills_index.json          # Index of still images with metadata
├── typeface_database.json     # Typography options (6 fonts)
├── template_library.json      # 4 poster layout templates
├── color_reference.json       # Official color palettes
├── README.md                  # Data documentation
└── stills/                    # 4 actual images downloaded
    ├── still_01.jpg          # Jared Leto (2048x1365)
    ├── still_02.jpg          # Ana de Armas (2048x854)
    ├── still_03.jpg          # Roy Batty tribute (640x924)
    └── still_04.jpg          # Timeline graphic (640x271)
```

**Image Sources:** IMDB (official production stills), Reddit r/bladerunner

---

## 4. How to Run

**Prerequisites:** `uv` (Python package manager)

**Basic run:**
```bash
uv run --script poster_room.py --movie ./sample_movie
```

**Create sample data (if needed):**
```bash
uv run --script poster_room.py --create-sample
```

**Outputs:**
- `output/final_poster.png` - Generated poster image
- `output/blackboard/` - JSON files for all 14 blackboard items
- `output/nerd_log.md` - Human-readable markdown log of all nerd activations

---

## 5. Current Behavior

**What happens when you run it:**

1. Blackboard is cleared
2. Single query item seeded: `{title: "Blade Runner 2049"}`
3. 13 nerds run in sequence, each:
   - Checking if required inputs exist
   - Selecting inputs from blackboard
   - Processing
   - Writing results back
4. Log file written in markdown format
5. Poster saved if CompletionNerd declares success

**Example log entry:**
```markdown
## ResearchNerd

**Time:** 16:35:12

**Inputs:**
- `movie_query`: item_0001 (movie_query)

**Output:** item_0002 (movie_metadata)

**Data Summary:**
```json
{
  "title": "Blade Runner 2049",
  "director": "Denis Villeneuve",
  ...
}
```

**Notes:**
- Found metadata for 'Blade Runner 2049'

---
```

---

## 6. What's Missing (Next Steps)

### Priority 1: Heat-Based Scheduler ⭐ CRITICAL

**Current:** Linear sequence hardcoded in `run_linear_pipeline()`

**Goal:** Replace with probabilistic selection based on:
- Item "heat" (salience/temperature)
- Nerd "heat" (how eager they are to work)
- Time-based cooling

**Key Concepts from Design Fiction:**
- **Heat levels:** HOT → MEDIUM → COLD
- **Thermal dynamics:** Items cool over time, newly created items start HOT
- **Thermal mass:** Some items are "heavier" and retain heat longer
- **Activation:** Nerd selection weighted by heat of their preferred inputs

**Implementation Sketch:**
```python
class HeatManager:
    def __init__(self):
        self.items: Dict[str, float]  # item_id -> heat (0.0-1.0)
        self.nerds: Dict[str, float]  # nerd_name -> heat
        self.decay_rate = 0.1
    
    def cool_all(self):
        # Reduce heat over time
        pass
    
    def reheat(self, item_id: str, amount: float):
        # Boost heat (e.g., when critiqued)
        pass
    
    def select_nerd(self, available_nerds: List[Nerd]) -> Nerd:
        # Boltzmann distribution selection
        pass
```

### Priority 2: More Data-Fetching Nerds

**Current:** All data is local (JSON files, downloaded images)

**Future:** Nerds that fetch from external APIs:
- `IMDBNerd` - Queries OMDB/IMDB API for metadata
- `TMDBNerd` - Fetches from The Movie Database
- `ImageScraperNerd` - Downloads stills from web
- `FontDownloaderNerd` - Fetches actual font files

### Priority 3: Enhanced Critique System

**Current:** Single CritiqueNerd checks color genre match

**Future:** Multiple specialized critique nerds:
- `ReadabilityNerd` - Checks text contrast
- `GenreCoherenceNerd` - Ensures visual elements match genre
- `BillingOrderNerd` - Verifies actor credits are correct
- `BalanceNerd` - Checks visual composition balance

Each writes critiques, heating the target items, triggering revision nerds.

### Priority 4: Iterative Generation

**Current:** One pass through each nerd

**Future:** Loop until completion:
```python
while not complete:
    nerd = heat_manager.select_nerd(available_nerds)
    result = nerd.run(blackboard)
    heat_manager.cool_all()
    
    if CompletionNerd declares done:
        break
```

### Priority 5: Designer Intervention

Add "MetaNerds" that can:
- Override heat values ("I want to see more typography work")
- Lock certain items ("Don't change this color")
- Inject new queries mid-process

---

## 7. Key Design Principles

1. **Nerds are specialists with blinders** - Each only sees their domain
2. **Separation of critique and revision** - Different nerds for each
3. **Blackboard is dumb** - Just storage, no intelligence
4. **Heat drives attention** - What's hot gets worked on
5. **Emergent coordination** - No central planner, just local interactions
6. **Completion is arbitrary** - Configurable criteria for "done"

---

## 8. Technical Details

**File Locations:**
- Main system: `/Users/nainai/Documents/nerds/poster_room.py`
- Sample data: `/Users/nainai/Documents/nerds/sample_movie/`
- Design fiction: `/Users/nainai/Documents/nerds/design_fiction.md`

**Dependencies (managed by uv inline script metadata):**
```python
# /// script
# dependencies = [
#   "Pillow>=10.0.0",
#   "colorthief>=0.2.1",
#   "numpy>=1.24.0",
# ]
# ///
```

**Base Classes:**
- `Nerd` - Abstract base with `can_activate()`, `select_inputs()`, `process()`
- `Blackboard` - Filesystem JSON store with query/write operations
- `MarkdownLogger` - Human-readable activity logging

---

## 9. Known Issues

1. **LSP Error:** `Cannot access attribute "_last_rendered_image"` in `save_final_poster()` - runtime works fine, just type checking complaint
2. **Images:** Color extraction is simulated, not using actual colorthief library yet
3. **Fonts:** Using system Helvetica instead of Eurostile Extended
4. **Templates:** Not actually rendering images into template blocks (just drawing rectangles)

---

## 10. Running Example

```bash
$ uv run --script poster_room.py --movie ./sample_movie

============================================================
THE POSTER ROOM
Nerds Architecture - Linear Pipeline Demo
============================================================

[System] Registered nerd: ResearchNerd
[System] Registered nerd: ImageFetcherNerd
...

============================================================
SEEDING BLACKBOARD with query: 'Blade Runner 2049'
============================================================

  [Blackboard] System wrote item_0001 (movie_query)
[System] Seeded 1 query item. Nerds will fetch the rest.


============================================================
RUNNING LINEAR PIPELINE
============================================================


[ResearchNerd] Activating...
  Input 'movie_query': item_0001 (movie_query)
  [ResearchNerd] Found metadata for 'Blade Runner 2049'
  [Blackboard] ResearchNerd wrote item_0002 (movie_metadata)

[ImageFetcherNerd] Activating...
  Input 'metadata': item_0002 (movie_metadata)
  [ImageFetcherNerd] Found 5 stills for 'Blade Runner 2049'
  [Blackboard] ImageFetcherNerd wrote item_0003 (movie_still)
...

============================================================
✓ POSTER COMPLETE!
============================================================
Output: rendered_poster
Rationale: Poster has 3 elements rendered

[Output] Final poster saved to: output/final_poster.png
```

---

## 11. Questions for Next Developer

1. Should we implement actual heat-based scheduling next, or add more data-fetching nerds first?
2. How should critiques "reheat" items? Immediate boost or gradual?
3. Should nerds have "memory" to avoid re-processing the same items?
4. How do we prevent starvation (nerds that never get selected because their inputs are never hot)?
5. Should we add a visual heat map visualization of the blackboard?

---

## 12. References

- **Blackboard systems:** https://en.wikipedia.org/wiki/Blackboard_system
- **Design Fiction:** `design_fiction.md` in this directory
- **Original Concept:** UCSC StoryAssembler (https://dl.acm.org/doi/10.1145/3337722.3337732)
- **Pewter (LLM-based):** https://github.com/collectioncard/Layered-Selection-Prompting

---

**End of Handoff Document**

*Good luck! The foundation is solid. The heat system is the exciting part.*
