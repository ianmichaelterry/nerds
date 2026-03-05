# Semantic NERDS: Poster Generation Narrative

*Generated 2026-03-04 17:24:35 &mdash; seed 42, max 30 ticks*

---

## Standards in play

| Standard | Role | Source |
|---|---|---|
| **RDF + JSON-LD** | Blackboard is an RDF graph; items are triples | W3C Rec 2014/2020 |
| **PROV-O** | Every item traces back to the nerd that made it | W3C Rec 2013 |
| **SKOS** | Item types are concepts in a navigable hierarchy | W3C Rec 2009 |
| **SHACL** | Nerd preconditions are declarative shapes | W3C Rec 2017 |
| **Schema.org** | Movie data uses `schema:Movie` vocabulary | Community std |
| **Dublin Core** | Metadata fields: `dcterms:creator`, `dcterms:type`, etc. | ISO 15836 |
| **Wikidata SPARQL** | Live movie data from the world's knowledge graph | CC0 |
| **Noun Project API** | Genre-relevant icons via OAuth1 | Commercial API |

## Nerds roster

**MoviePicker**, **TitleParser**, **GenrePalette**, **TypefacePicker**, **LayoutPicker**, **HeroImageGen**, **IconFetcher**, **GrainEffect**, **Critic**, **PosterCritic**, **CompletionJudge**

---

## The run

### Tick 1: TypefacePicker

Produced: `Typeface`

Selected typeface **script-italic** (style: script, weight: italic). Genre preference had a 60% influence on the pick.

### Tick 2: MoviePicker

Produced: `MovieData`

The MoviePicker queried **Wikidata** via SPARQL for notable films, then selected one at random.

| Field | Value |
|---|---|
| `schema:name` | **The Tarantula** |
| `schema:director` | George D. Baker |
| `schema:genre` | drama |
| `schema:datePublished` | 1916 |
| `schema:actor` | Antonio Moreno, Charles Kent, Edith Storey |

This data arrived as `schema:Movie`-shaped RDF triples, the same vocabulary Google and Wikidata speak. No parsing, no key mapping -- it went straight onto the graph.

### Tick 3: TitleParser

Produced: `TitleChunks`

Split the title into primary **"The"** and secondary **"Tarantula"**.

### Tick 4: Critic

Produced: `Critique`

Completeness: **33%**. Still missing: `missing_palette`, `missing_layout`, `missing_hero`, `missing_icon`.

### Tick 5: TypefacePicker

Produced: `Typeface`

Selected typeface **script-italic** (style: script, weight: italic). Genre preference had a 60% influence on the pick.

### Tick 6: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#354859` |
| Accent (text, lines) | `#42a597` |
| Mid (gradients) | `#3b7778` |

### Tick 7: HeroImageGen

Produced: `HeroImage`

Generated **3 overlapping color-field blocks** with varying opacity, derived from the palette. These form the abstract background texture behind the icon.

### Tick 8: Critic

Produced: `Critique`

Completeness: **66%**. Still missing: `missing_layout`, `missing_icon`.

### Tick 9: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"mask"** (icon #5571757) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 10: GrainEffect

Produced: `PostEffect`

Post-processing effects selected: **vignette**.

### Tick 11: LayoutPicker

Produced: `Layout`

Chose layout template **"minimalist"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 12: HeroImageGen

Produced: `HeroImage`

Generated **3 overlapping color-field blocks** with varying opacity, derived from the palette. These form the abstract background texture behind the icon.

### Tick 13: PosterCritic

Produced: `PosterCritique`

Rendered a temporary poster
(`output/temp/temp_poster_tick13.png`) 
and critiqued it: **passes**.

### Tick 14: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#354d59` |
| Accent (text, lines) | `#42a58b` |
| Mid (gradients) | `#3b7972` |

### Tick 15: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"Boxing Ring"** (icon #137363) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 16: GrainEffect

Produced: `PostEffect`

Post-processing effects selected: **vignette**.

### Tick 17: TypefacePicker

Produced: `Typeface`

Selected typeface **script-italic** (style: script, weight: italic). Genre preference had a 60% influence on the pick.

### Tick 18: TitleParser

Produced: `TitleChunks`

Split the title into primary **"The"** and secondary **"Tarantula"**.

### Tick 19: Critic

Produced: `Critique`

Completeness: **100%**. All artifact types present.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 20: LayoutPicker

Produced: `Layout`

Chose layout template **"minimalist"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 21: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"Theater"** (icon #3769) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 22: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#355659` |
| Accent (text, lines) | `#42a572` |
| Mid (gradients) | `#3b7d65` |

### Tick 23: CompletionJudge

Produced: `Completion`

The CompletionJudge reviewed the latest critique, found the score >= 80%, and **declared the poster complete**.

---

## Completion

**Poster declared complete at tick 23.**

- 23 items on the blackboard
- 467 RDF triples in the graph

## The poster

![Generated poster](poster_the_tarantula_s42.png)

## Provenance (excerpt)

The full provenance graph is exported as Turtle RDF. Here's a sample showing
how PROV-O traces items back through activities to their nerd agents:

```turtle
nerds:Blackboard a nerds:BlackboardSystem ;
    rdfs:label "NERDS Blackboard" ;
    nerds:contains nerds:item_0,
        nerds:item_1,
        nerds:item_10,
        nerds:item_11,
        nerds:item_12,
        nerds:item_13,
        nerds:item_14,
        nerds:item_15,
        nerds:item_16,
        nerds:item_17,
        nerds:item_18,
        nerds:item_19,
        nerds:item_2,
        nerds:item_20,
        nerds:item_21,
        nerds:item_22,
        nerds:item_3,
        nerds:item_4,
        nerds:item_5,
        nerds:item_6,
        nerds:item_7,
        nerds:item_8,
        nerds:item_9 .

nerds:Completion a skos:Concept ;
    rdfs:comment "Signal that the poster is done." ;
    skos:broader nerds:MetaArtifact ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Completion"@en .

nerds:FoundationalArtifact a skos:Concept ;
    rdfs:comment "Seed data that everything else derives from." ;
```

## Blackboard summary

| Artifact type | Count |
|---|---|
| ColorPalette | 3 |
| Completion | 1 |
| Critique | 3 |
| HeroImage | 2 |
| IconImage | 3 |
| Layout | 2 |
| MovieData | 1 |
| PostEffect | 2 |
| PosterCritique | 1 |
| TitleChunks | 2 |
| Typeface | 3 |

---

*Total wall-clock time: 10.7s*

*Generated by Semantic NERDS (week 8) &mdash; a computational caricature
of a blackboard architecture, grounded in W3C semantic web standards.*

*No LLM was used at runtime. Every decision was made by a dumb specialist
reading RDF triples off a shared graph.*
