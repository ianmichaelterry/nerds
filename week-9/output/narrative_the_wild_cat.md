# Semantic NERDS: Poster Generation Narrative

*Generated 2026-03-04 16:40:28 &mdash; seed random, max 30 ticks*

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

### Tick 1: TypefacePicker

Produced: `Typeface`

Selected typeface **script-italic** (style: script, weight: italic). Genre preference had a 60% influence on the pick.

### Tick 2: MoviePicker

Produced: `MovieData`

The MoviePicker queried **Wikidata** via SPARQL for notable films, then selected one at random.

| Field | Value |
|---|---|
| `schema:name` | **The Wild Cat** |
| `schema:director` | Ernst Lubitsch |
| `schema:genre` | drama |
| `schema:datePublished` | 1921 |
| `schema:actor` | Hermann Thimig, Victor Janson, Paul Graetz, Paul Biensfeldt, Edith Meller |

This data arrived as `schema:Movie`-shaped RDF triples, the same vocabulary Google and Wikidata speak. No parsing, no key mapping -- it went straight onto the graph.

### Tick 3: GenrePalette

Produced: `ColorPalette`

Derived a color palette from genre **drama**:

| Role | Hex |
|---|---|
| Key (background) | `#354859` |
| Accent (text, lines) | `#42a599` |
| Mid (gradients) | `#3b7679` |

### Tick 4: IconFetcher

Produced: `IconImage`

Searched the **Noun Project API** (OAuth1) for genre-relevant icons. Found and downloaded **"Flashlight"** (icon #5308770) as a tinted PNG.

This is the visual quality leap: a professionally designed icon from a curated library of millions, replacing the colored rectangles of week 7.

### Tick 5: Critic

Produced: `Critique`

Completeness: **50%**. Still missing: `missing_title`, `missing_layout`, `missing_hero`.

### Tick 6: TitleParser

Produced: `TitleChunks`

Split the title into primary **"The"** and secondary **"Wild Cat"**.

### Tick 7: LayoutPicker

Produced: `Layout`

Chose layout template **"split-diagonal"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 8: HeroImageGen

Produced: `HeroImage`

Generated **7 overlapping color-field blocks** with varying opacity, derived from the palette. These form the abstract background texture behind the icon.

### Tick 9: GrainEffect

Produced: `PostEffect`

Post-processing effects selected: **vignette**.

### Tick 10: Critic

Produced: `Critique`

Completeness: **100%**. All artifact types present.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 11: CompletionJudge

Produced: `Completion`

The CompletionJudge reviewed the latest critique, found the score >= 80%, and **declared the poster complete**.

---

## Completion

**Poster declared complete at tick 11.**

- 11 items on the blackboard
- 264 RDF triples in the graph

## The poster

![Generated poster](poster_the_wild_cat.png)

## Provenance (excerpt)

The full provenance graph is exported as Turtle RDF. Here's a sample showing
how PROV-O traces items back through activities to their nerd agents:

```turtle
nerds:Blackboard a nerds:BlackboardSystem ;
    rdfs:label "NERDS Blackboard" ;
    nerds:contains nerds:item_0,
        nerds:item_1,
        nerds:item_10,
        nerds:item_2,
        nerds:item_3,
        nerds:item_4,
        nerds:item_5,
        nerds:item_6,
        nerds:item_7,
        nerds:item_8,
        nerds:item_9 .

nerds:ColorPalette a skos:Concept ;
    rdfs:comment "Genre-derived key and accent colors." ;
    skos:broader nerds:VisualArtifact ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Color Palette"@en .

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
| ColorPalette | 1 |
| Completion | 1 |
| Critique | 2 |
| HeroImage | 1 |
| IconImage | 1 |
| Layout | 1 |
| MovieData | 1 |
| PostEffect | 1 |
| TitleChunks | 1 |
| Typeface | 1 |

---

*Total wall-clock time: 11.0s*

*Generated by Semantic NERDS (week 8) &mdash; a computational caricature
of a blackboard architecture, grounded in W3C semantic web standards.*

*No LLM was used at runtime. Every decision was made by a dumb specialist
reading RDF triples off a shared graph.*
