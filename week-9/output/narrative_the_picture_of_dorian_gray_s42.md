# Semantic NERDS: Poster Generation Narrative

*Generated 2026-03-04 16:47:33 &mdash; seed 42, max 30 ticks*

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
| `schema:name` | **The Tarantula** |
| `schema:director` | George D. Baker |
| `schema:genre` | drama |
| `schema:datePublished` | 1916 |
| `schema:actor` | Edith Storey, Antonio Moreno, Charles Kent |

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

### Tick 7: LayoutPicker

Produced: `Layout`

Chose layout template **"split-diagonal"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 8: TitleParser

Produced: `TitleChunks`

Split the title into primary **"The"** and secondary **"Tarantula"**.

### Tick 9: MoviePicker

Produced: `MovieData`

The MoviePicker queried **Wikidata** via SPARQL for notable films, then selected one at random.

| Field | Value |
|---|---|
| `schema:name` | **The Explorer** |
| `schema:director` | George Melford |
| `schema:genre` | adventure |
| `schema:datePublished` | 1915 |
| `schema:actor` | Lou Tellegen, Dorothy Davenport, Tom Forman |

This data arrived as `schema:Movie`-shaped RDF triples, the same vocabulary Google and Wikidata speak. No parsing, no key mapping -- it went straight onto the graph.

### Tick 10: LayoutPicker

Produced: `Layout`

Chose layout template **"split-diagonal"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 11: TypefacePicker

Produced: `Typeface`

Selected typeface **sans-light** (style: sans, weight: light). Genre preference had a 60% influence on the pick.

### Tick 12: Critic

Produced: `Critique`

Completeness: **66%**. Still missing: `missing_hero`, `missing_icon`.

### Tick 13: HeroImageGen

Produced: `HeroImage`

Generated **7 overlapping color-field blocks** with varying opacity, derived from the palette. These form the abstract background texture behind the icon.

### Tick 14: LayoutPicker

Produced: `Layout`

Chose layout template **"bottom-heavy"**. This sets y-positions for the title, image area, tagline, and credits.

### Tick 15: Critic

Produced: `Critique`

Completeness: **83%**. Still missing: `missing_icon`.
Score is >= 80% -- the CompletionJudge can now fire.

### Tick 16: MoviePicker

Produced: `MovieData`

The MoviePicker queried **Wikidata** via SPARQL for notable films, then selected one at random.

| Field | Value |
|---|---|
| `schema:name` | **The Picture of Dorian Gray** |
| `schema:director` | Albert Lewin |
| `schema:genre` | drama |
| `schema:datePublished` | 1945 |
| `schema:actor` | Angela Lansbury, Donna Reed, George Sanders, Hurd Hatfield, Lilian Bond |

This data arrived as `schema:Movie`-shaped RDF triples, the same vocabulary Google and Wikidata speak. No parsing, no key mapping -- it went straight onto the graph.

### Tick 17: CompletionJudge

Produced: `Completion`

The CompletionJudge reviewed the latest critique, found the score >= 80%, and **declared the poster complete**.

---

## Completion

**Poster declared complete at tick 17.**

- 17 items on the blackboard
- 366 RDF triples in the graph

## The poster

![Generated poster](poster_the_picture_of_dorian_gray_s42.png)

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

nerds:IconImage a skos:Concept ;
    rdfs:comment "Genre-relevant icon from the Noun Project, composited onto the poster." ;
    skos:broader nerds:VisualArtifact ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Icon Image"@en .

nerds:PostEffect a skos:Concept ;
    rdfs:comment "Film grain, vignette, or posterization flags." ;
    skos:broader nerds:VisualArtifact ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Post Effect"@en .

nerds:ColorPalette a skos:Concept ;
    rdfs:comment "Genre-derived key and accent colors." ;
```

## Blackboard summary

| Artifact type | Count |
|---|---|
| ColorPalette | 1 |
| Completion | 1 |
| Critique | 3 |
| HeroImage | 1 |
| Layout | 3 |
| MovieData | 3 |
| TitleChunks | 2 |
| Typeface | 3 |

---

*Total wall-clock time: 20.7s*

*Generated by Semantic NERDS (week 8) &mdash; a computational caricature
of a blackboard architecture, grounded in W3C semantic web standards.*

*No LLM was used at runtime. Every decision was made by a dumb specialist
reading RDF triples off a shared graph.*
