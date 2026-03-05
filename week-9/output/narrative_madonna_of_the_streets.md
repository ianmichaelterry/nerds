# Semantic NERDS: Poster Generation Narrative

*Generated 2026-03-04 16:56:28 &mdash; seed random, max 30 ticks*

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

**MoviePicker**, **TitleParser**, **GenrePalette**, **TypefacePicker**, **LayoutPicker**, **HeroImageGen**, **IconFetcher**, **GrainEffect**, **Critic**, **CompletionJudge**

---

## The run

### Tick 1: LayoutPicker

Produced: `Layout`

Chose layout template **"bottom-heavy"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 2: TypefacePicker

Produced: `Typeface`

Selected typeface **script-italic** (style: script, weight: italic). Genre preference had a 60% influence on the pick.

### Tick 3: MoviePicker

Produced: `MovieData`

The MoviePicker queried **Wikidata** via SPARQL for notable films, then selected one at random.

| Field | Value |
|---|---|
| `schema:name` | **Madonna of the Streets** |
| `schema:director` | Edwin Carewe |
| `schema:genre` | drama |
| `schema:datePublished` | 1924 |
| `schema:actor` | Alla Nazimova, Wallace Beery, Milton Sills, Claude Gillingwater, Courtenay Foote |

This data arrived as `schema:Movie`-shaped RDF triples, the same vocabulary Google and Wikidata speak. No parsing, no key mapping -- it went straight onto the graph.

### Tick 4: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#355359` |
| Accent (text, lines) | `#42a579` |
| Mid (gradients) | `#3b7c69` |

### Tick 5: LayoutPicker

Produced: `Layout`

Chose layout template **"split-diagonal"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 6: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"theater-book"** (icon #3647440) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 7: Critic

Produced: `Critique`

Completeness: **66%**. Still missing: `missing_title`, `missing_hero`.

### Tick 8: LayoutPicker

Produced: `Layout`

Chose layout template **"minimalist"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 9: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#355159` |
| Accent (text, lines) | `#42a580` |
| Mid (gradients) | `#3b7b6c` |

### Tick 10: TitleParser

Produced: `TitleChunks`

Split the title into primary **"Madonna"** and secondary **"of the Streets"**.

### Tick 11: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"Flashlight"** (icon #5308770) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 12: Critic

Produced: `Critique`

Completeness: **83%**. Still missing: `missing_hero`.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 13: LayoutPicker

Produced: `Layout`

Chose layout template **"classic-centered"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 14: Critic

Produced: `Critique`

Completeness: **83%**. Still missing: `missing_hero`.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 15: HeroImageGen

Produced: `HeroImage`

Generated **3 overlapping color-field blocks** with varying opacity, derived from the palette. These form the abstract background texture behind the icon.

### Tick 16: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#354a59` |
| Accent (text, lines) | `#42a593` |
| Mid (gradients) | `#3b7876` |

### Tick 17: TitleParser

Produced: `TitleChunks`

Split the title into primary **"Madonna"** and secondary **"of the Streets"**.

### Tick 18: CompletionJudge

Produced: `Completion`

The CompletionJudge reviewed the latest critique, found the score >= 80%, and **declared the poster complete**.

---

## Completion

**Poster declared complete at tick 18.**

- 18 items on the blackboard
- 383 RDF triples in the graph

## The poster

![Generated poster](poster_madonna_of_the_streets.png)

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
        nerds:item_2,
        nerds:item_3,
        nerds:item_4,
        nerds:item_5,
        nerds:item_6,
        nerds:item_7,
        nerds:item_8,
        nerds:item_9 .

nerds:PostEffect a skos:Concept ;
    rdfs:comment "Film grain, vignette, or posterization flags." ;
    skos:broader nerds:VisualArtifact ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Post Effect"@en .

nerds:Completion a skos:Concept ;
    rdfs:comment "Signal that the poster is done." ;
    skos:broader nerds:MetaArtifact ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Completion"@en .

nerds:FoundationalArtifact a skos:Concept ;
```

## Blackboard summary

| Artifact type | Count |
|---|---|
| ColorPalette | 3 |
| Completion | 1 |
| Critique | 3 |
| HeroImage | 1 |
| IconImage | 2 |
| Layout | 4 |
| MovieData | 1 |
| TitleChunks | 2 |
| Typeface | 1 |

---

*Total wall-clock time: 10.8s*

*Generated by Semantic NERDS (week 8) &mdash; a computational caricature
of a blackboard architecture, grounded in W3C semantic web standards.*

*No LLM was used at runtime. Every decision was made by a dumb specialist
reading RDF triples off a shared graph.*
