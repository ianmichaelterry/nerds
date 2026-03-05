# Semantic NERDS: Poster Generation Narrative

*Generated 2026-03-04 17:28:42 &mdash; seed random, max 30 ticks*

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
| `schema:name` | **Death Wish 4: The Crackdown** |
| `schema:director` | J. Lee Thompson |
| `schema:genre` | noir |
| `schema:datePublished` | 1987 |
| `schema:actor` | Charles Bronson, Perry Lopez, Mark Pellegrino, Kay Lenz, Tim Russ |

This data arrived as `schema:Movie`-shaped RDF triples, the same vocabulary Google and Wikidata speak. No parsing, no key mapping -- it went straight onto the graph.

### Tick 3: TitleParser

Produced: `TitleChunks`

Split the title into primary **"Death Wish 4"** and secondary **"The Crackdown"**.

### Tick 4: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **noir**:

| Role | Hex |
|---|---|
| Key (background) | `#2d1933` |
| Accent (text, lines) | `#7f6b26` |
| Mid (gradients) | `#56422c` |

### Tick 5: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"Magnifying Glass"** (icon #5386) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 6: HeroImageGen

Produced: `HeroImage`

Generated **3 overlapping color-field blocks** with varying opacity, derived from the palette. These form the abstract background texture behind the icon.

### Tick 7: PosterCritic

Produced: `PosterCritique`

Rendered a temporary poster
(`output/temp/temp_poster_tick7.png`) 
and critiqued it: **passes**.

### Tick 8: TypefacePicker

Produced: `Typeface`

Selected typeface **sans-light** (style: sans, weight: light). Genre preference had a 60% influence on the pick.

### Tick 9: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **noir**:

| Role | Hex |
|---|---|
| Key (background) | `#241933` |
| Accent (text, lines) | `#7f4b26` |
| Mid (gradients) | `#52322c` |

### Tick 10: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"elipse"** (icon #687556) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 11: Critic

Produced: `Critique`

Completeness: **83%**. Still missing: `missing_layout`.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 12: LayoutPicker

Produced: `Layout`

Chose layout template **"split-diagonal"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 13: TypefacePicker

Produced: `Typeface`

Selected typeface **sans-light** (style: sans, weight: light). Genre preference had a 60% influence on the pick.

### Tick 14: GrainEffect

Produced: `PostEffect`

Post-processing effects selected: **grain**, **vignette**.

### Tick 15: Critic

Produced: `Critique`

Completeness: **100%**. All artifact types present.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 16: TitleParser

Produced: `TitleChunks`

Split the title into primary **"Death Wish 4"** and secondary **"The Crackdown"**.

### Tick 17: CompletionJudge

Produced: `Completion`

The CompletionJudge reviewed the latest critique, found the score >= 80%, and **declared the poster complete**.

---

## Completion

**Poster declared complete at tick 17.**

- 17 items on the blackboard
- 371 RDF triples in the graph

## The poster

![Generated poster](poster_death_wish_4_the_crackdown.png)

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
        nerds:item_2,
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
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Foundational Artifact"@en .

nerds:HeroImage a skos:Concept ;
    rdfs:comment "Procedural color-field imagery for the poster body." ;
    skos:broader nerds:VisualArtifact ;
```

## Blackboard summary

| Artifact type | Count |
|---|---|
| ColorPalette | 2 |
| Completion | 1 |
| Critique | 2 |
| HeroImage | 1 |
| IconImage | 2 |
| Layout | 1 |
| MovieData | 1 |
| PostEffect | 1 |
| PosterCritique | 1 |
| TitleChunks | 2 |
| Typeface | 3 |

---

*Total wall-clock time: 8.9s*

*Generated by Semantic NERDS (week 8) &mdash; a computational caricature
of a blackboard architecture, grounded in W3C semantic web standards.*

*No LLM was used at runtime. Every decision was made by a dumb specialist
reading RDF triples off a shared graph.*
