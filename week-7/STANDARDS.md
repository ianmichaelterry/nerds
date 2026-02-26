# Standards Reference for Semantics Nerds

**For the research team -- standards to evaluate for the NERDS reboot.**

The claim: by grounding the blackboard architecture in existing W3C/IANA standards instead of ad-hoc Python types, we get a system that can scale from a 5-movie hardcoded dict to live SPARQL queries against DBpedia/Wikidata, with inspectable provenance, declarative nerd preconditions, and interoperable data -- without inventing new vocabularies for things the world already has names for.

---

## 1. RDF + JSON-LD (the data layer)

**What it replaces:** `list[Item]` with ad-hoc dicts as values.

RDF is the W3C's graph data model: everything is `<subject> <predicate> <object>` triples forming a directed labeled graph. The blackboard becomes an RDF graph; adding an item means inserting triples; querying means pattern matching or SPARQL.

**JSON-LD** (W3C Rec, 2020) is the serialization that makes this practical. It's just JSON with an `@context` that maps keys to URIs. Existing code that produces dicts can be upgraded to JSON-LD by adding a context -- no structural rewrite needed. A palette item goes from:

```python
{"key": (30, 40, 80), "accent": (200, 100, 50), "genre": "sci-fi"}
```

to:

```json
{
  "@context": "https://example.org/nerds/context.jsonld",
  "@type": "nerds:ColorPalette",
  "nerds:keyColor": "#1e2850",
  "nerds:accentColor": "#c86432",
  "schema:genre": "sci-fi"
}
```

Same data, but now self-describing and parseable by any linked-data tool.

**Python:** `rdflib` 7.x (BSD-3, pure Python, mature). Built-in JSON-LD parser/serializer since v6. Supports in-memory graphs, SPARQL 1.1 query/update, named graphs, and pluggable storage backends.

| | |
|---|---|
| Spec | https://www.w3.org/TR/rdf11-primer/ |
| JSON-LD | https://www.w3.org/TR/json-ld11/ |
| rdflib | https://rdflib.readthedocs.io/ |
| Status | W3C Recommendation |

---

## 2. PROV-O (the provenance layer)

**What it replaces:** `created_by: str` and `birth_tick: int` on Item.

PROV-O (W3C Rec, 2013) models *who did what to which thing and when* using three classes:

| PROV Class | NERDS Mapping |
|---|---|
| `prov:Entity` | A blackboard item |
| `prov:Activity` | A nerd's `run()` invocation |
| `prov:Agent` (subclass: `prov:SoftwareAgent`) | A nerd instance |

Key properties: `prov:wasGeneratedBy` (item -> run), `prov:used` (run -> item it read), `prov:wasAssociatedWith` (run -> nerd), `prov:wasDerivedFrom` (item -> item), `prov:startedAtTime` / `prov:endedAtTime`.

This turns the generation trace from a debug log into a first-class graph artifact. After a run, you can serialize the full provenance as Turtle or JSON-LD and open it in any PROV viewer. You can answer "why is this poster blue?" by traversing `prov:wasDerivedFrom` chains back to the movie's genre.

The **qualified pattern** lets you annotate relationships with roles and timestamps without losing the simple property shortcuts.

**Python:** `prov` 2.x (MIT). Implements full PROV-DM. Serializes to PROV-JSON, PROV-N, RDF, XML. Exports to PNG/SVG via graphviz. Optional `prov[rdf]` extra integrates with rdflib.

| | |
|---|---|
| Spec | https://www.w3.org/TR/prov-o/ |
| Overview | https://www.w3.org/TR/prov-overview/ |
| Python | https://pypi.org/project/prov/ |
| Status | W3C Recommendation |

---

## 3. SKOS (the vocabulary layer)

**What it replaces:** Ad-hoc `type_tag` strings like `"MovieData"`, `"ColorPalette"`, `"Critique"`.

SKOS (W3C Rec, 2009) models concept schemes -- taxonomies, thesauri, classification systems. Concepts are URI-identified, have labels, and can be related hierarchically (`skos:broader`/`skos:narrower`) or associatively (`skos:related`).

Instead of a flat list of string tags, the NERDS vocabulary becomes a concept scheme:

```turtle
nerds:PosterArtifact a skos:ConceptScheme .

nerds:MovieData a skos:Concept ;
    skos:inScheme nerds:PosterArtifact ;
    skos:prefLabel "Movie Data"@en ;
    skos:broader nerds:FoundationalArtifact .

nerds:ColorPalette a skos:Concept ;
    skos:broader nerds:VisualArtifact .

nerds:Critique a skos:Concept ;
    skos:broader nerds:MetaArtifact .
```

Now a nerd can query "give me anything that's a kind of VisualArtifact" via `skos:broaderTransitive` traversal, instead of hard-coding a list of type tags. New artifact types are added to the scheme, not to Python code.

SKOS is deliberately *less formal* than OWL -- concepts are individuals, not classes. This is a feature: you get navigable hierarchy without the complexity of description logic.

Cross-scheme mapping (`skos:exactMatch`, `skos:broadMatch`) would let Semantics Nerds interop with external vocabularies -- e.g. mapping `nerds:ColorPalette` to a design-tools taxonomy.

| | |
|---|---|
| Spec | https://www.w3.org/TR/skos-reference/ |
| Primer | https://www.w3.org/TR/skos-primer/ |
| Status | W3C Recommendation |

---

## 4. SHACL (the preconditions layer)

**What it replaces:** Python `can_run()` methods.

SHACL (W3C Rec, 2017) validates RDF graphs against declarative "shapes." A shape says "a node of type X must have at least 1 property Y of type Z." Validation returns a structured report of conformance/violations.

A nerd's preconditions become a SHACL shape:

```turtle
nerds:GenrePaletteShape a sh:NodeShape ;
    sh:targetNode nerds:Blackboard ;
    sh:property [
        sh:path nerds:contains ;
        sh:qualifiedValueShape [ sh:class schema:Movie ] ;
        sh:qualifiedMinCount 1
    ] ;
    sh:property [
        sh:path nerds:contains ;
        sh:qualifiedValueShape [ sh:class nerds:ColorPalette ] ;
        sh:qualifiedMaxCount 0
    ] .
```

This is more verbose than `bb.has("MovieData") and not bb.has("ColorPalette")`, but it's machine-readable, composable (`sh:and`/`sh:or`/`sh:not`), and separable from Python code. A visual tool could render activation conditions as a diagram. SHACL-SPARQL allows arbitrary constraint complexity when needed.

**Python:** `pyshacl` 0.31.x (Apache 2.0). Validates data graph against shapes graph, returns `(conforms: bool, report_graph, report_text)`. Built on rdflib. Supports SHACL Core, SHACL-SPARQL, and SHACL Advanced (rules).

**Cost/benefit tradeoff:** For 9 nerds with simple preconditions, SHACL is heavier than Python checks. The payoff comes at scale -- when you have 50 nerds and want to reason about which ones *could* fire given a hypothetical blackboard state, or visualize the dependency graph without reading Python.

| | |
|---|---|
| Spec | https://www.w3.org/TR/shacl/ |
| pyshacl | https://pypi.org/project/pyshacl/ |
| Status | W3C Recommendation |

---

## 5. Schema.org (the domain vocabulary)

**What it replaces:** The hardcoded `MOVIES` dict with custom keys.

Schema.org defines `schema:Movie` (a subclass of `CreativeWork`) with properties: `schema:name`, `schema:director` (-> `schema:Person`), `schema:actor`, `schema:genre`, `schema:datePublished`, `schema:description`, `schema:image`, `schema:aggregateRating`.

This is the vocabulary that Google, Bing, and every major search engine already understands. It's RDF-native (JSON-LD is its primary encoding). Using it means NERDS movie data is immediately legible to any Schema.org consumer.

More importantly, Schema.org is the *lingua franca* that DBpedia and Wikidata both map to (see below).

| | |
|---|---|
| Movie type | https://schema.org/Movie |
| Status | Community standard (backed by Google, Microsoft, Yahoo, Yandex) |

---

## 6. DBpedia + Wikidata (the data sources)

**What they replace:** The 5-movie hardcoded list.

This is the scaling claim. Instead of:

```python
MOVIES = [{"title": "Blade Runner", "genre": "sci-fi", ...}, ...]
```

MoviePickerNerd issues a SPARQL `CONSTRUCT` query against a public endpoint and gets back Schema.org-shaped RDF triples for any film in existence.

### DBpedia

Structured data auto-extracted from Wikipedia. Films are typed as *both* `dbo:Film` and `schema:Movie`. Resources carry `owl:sameAs` links to Wikidata, VIAF, Freebase.

- SPARQL endpoint: `https://dbpedia.org/sparql`
- Key class: `dbo:Film`
- Properties: `dbo:director`, `dbo:starring`, `dbo:runtime`, `dbo:thumbnail`, `dbo:budget`, `dbo:abstract`
- License: CC-BY-SA 3.0
- Caveat: Genre coverage is inconsistent (`dbo:genre` is often missing; raw `dbp:genre` is noisy)

### Wikidata

Community-curated, multilingual. Cleaner and more consistent than DBpedia, especially for structured fields like genre. Property URIs are opaque (`wdt:P57` = director) but mapped to Schema.org via `wdt:P1628`.

- SPARQL endpoint: `https://query.wikidata.org/`
- Key item: `wd:Q11424` (film)
- Properties: `P57` (director), `P161` (cast), `P136` (genre), `P577` (publication date), `P345` (IMDb ID)
- License: CC0 (public domain)
- Recommended as primary source: better genre coverage, cleaner data, no attribution requirement

### Practical pattern

```sparql
# Wikidata: get 10 random sci-fi films as Schema.org-shaped triples
CONSTRUCT {
  ?film a schema:Movie ;
        schema:name ?name ;
        schema:director ?dirName ;
        schema:actor ?castName ;
        schema:genre ?genreName ;
        schema:datePublished ?date .
} WHERE {
  ?film wdt:P31 wd:Q11424 ;
        wdt:P136 wd:Q24925 ;  # genre: science fiction film
        wdt:P57 ?dir ;
        wdt:P161 ?cast .
  OPTIONAL { ?film wdt:P577 ?date }
  ?film rdfs:label ?name . FILTER(lang(?name)="en")
  ?dir rdfs:label ?dirName . FILTER(lang(?dirName)="en")
  ?cast rdfs:label ?castName . FILTER(lang(?castName)="en")
  wd:Q24925 rdfs:label ?genreName . FILTER(lang(?genreName)="en")
} LIMIT 10
```

The result is RDF triples that go directly onto the blackboard as `schema:Movie` entities -- no parsing, no key mapping, no custom data structures. The MoviePickerNerd's `run()` method becomes a SPARQL query instead of `random.choice(MOVIES)`.

| | |
|---|---|
| DBpedia | https://www.dbpedia.org/ |
| Wikidata | https://www.wikidata.org/ |
| Wikidata SPARQL | https://query.wikidata.org/ |

---

## 7. Dublin Core + MIME types (the metadata basics)

**What they replace:** Custom field names on Item.

Dublin Core (ISO 15836, DCMI Rec) provides property names for basic metadata that map 1:1 to existing NERDS Item fields:

| DC Term | NERDS Field | Notes |
|---|---|---|
| `dcterms:creator` | `created_by` | Which agent produced this |
| `dcterms:created` | `birth_tick` | When it was created |
| `dcterms:type` | `type_tag` | What kind of thing it is (use SKOS concepts as values) |
| `dcterms:format` | (new) | MIME type of the payload |
| `dcterms:identifier` | `id` | Unique identifier |
| `dcterms:source` | (provenance) | What it was derived from |

These aren't load-bearing -- they're just shared names for things we already track. The value is that any linked-data tool already knows what `dcterms:creator` means.

**MIME types** (IANA media types, RFC 6838) self-describe payload formats. Adding a `dcterms:format` field to blackboard items with values like `application/ld+json`, `image/png`, or `text/css` lets consumers know how to parse a payload without guessing.

| | |
|---|---|
| Dublin Core | https://www.dublincore.org/specifications/dublin-core/dcmi-terms/ |
| IANA Media Types | https://www.iana.org/assignments/media-types/ |

---

## What we'd still invent

Not everything has a standard. The novel parts of NERDS stay as a small custom ontology (`nerds:` namespace):

- **`nerds:heat`** -- Three-level salience score (COLD/MEDIUM/HOT). No standard covers attention dynamics for blackboard systems.
- **`nerds:thermalMass`** -- Cooling resistance. Same.
- **`nerds:contains`** -- Links the blackboard node to its items.
- **The tick loop and scheduler** -- Pure application logic, not data modeling.

The custom ontology should be small enough to fit on a single page of Turtle. Everything else borrows.

---

## Dependency summary

| Package | Version | License | Purpose |
|---|---|---|---|
| `rdflib` | 7.x | BSD-3 | RDF graph, SPARQL, JSON-LD serialization |
| `pyshacl` | 0.31.x | Apache 2.0 | Validate blackboard against nerd precondition shapes |
| `prov` | 2.x | MIT | PROV-DM objects, graphviz export (optional; can use rdflib directly) |
| `SPARQLWrapper` | 2.x | W3C | Query DBpedia/Wikidata endpoints |
| `pillow` | 10.x | MIT-like | Image rendering (unchanged) |
| `numpy` | 1.26+ | BSD-3 | Post-effects (unchanged) |

---

## Reading order for the team

1. **JSON-LD spec, Section 1-3** (https://www.w3.org/TR/json-ld11/) -- understand `@context`, `@type`, `@id`
2. **PROV-O primer** (https://www.w3.org/TR/prov-primer/) -- the Entity/Activity/Agent triangle
3. **SKOS primer** (https://www.w3.org/TR/skos-primer/) -- concept schemes and broader/narrower
4. **SHACL spec, Section 2** (https://www.w3.org/TR/shacl/) -- node shapes and property shapes
5. **Schema.org Movie page** (https://schema.org/Movie) -- the domain vocabulary
6. **Wikidata SPARQL tutorial** (https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial) -- querying for real data
7. **rdflib docs, Getting Started** (https://rdflib.readthedocs.io/) -- Python implementation
