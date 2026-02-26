# Semantics Nerds: Standards Brief

NERDS works, but it invents names for things the world already has names for. Semantics Nerds replaces the ad-hoc data model with W3C and community standards so the architecture can scale -- from 5 hardcoded movies to live queries against knowledge graphs with millions of films -- while gaining inspectability, provenance, and interop for free.

See STANDARDS.md for the full reference with code examples.

---

**RDF + JSON-LD** -- The blackboard becomes an RDF graph instead of a Python list. Items are triples, not dicts. JSON-LD makes this painless: it's just JSON with a context that gives keys globally unique meaning. Nerds keep producing dicts; the dicts just become self-describing. W3C Recommendation. Python: `rdflib`.
> https://www.w3.org/TR/json-ld11/

**PROV-O** -- Every blackboard item is a `prov:Entity`, every nerd is a `prov:Agent`, every `run()` call is a `prov:Activity`. This replaces the ad-hoc `created_by`/`birth_tick` fields with a standard provenance graph that any PROV viewer can render. After a run, you can ask "why is this poster blue?" by traversing derivation chains -- no custom visualization code needed. W3C Recommendation. Python: `prov`.
> https://www.w3.org/TR/prov-o/

**SKOS** -- Replaces flat type-tag strings with a concept scheme. Instead of checking a hard-coded list of tags, a nerd can query "is there anything that's a kind of visual artifact?" via `skos:broader` traversal. Adding a new artifact type means adding a concept to the scheme, not editing Python. Deliberately lighter than OWL. W3C Recommendation.
> https://www.w3.org/TR/skos-primer/

**SHACL** -- Replaces Python `can_run()` methods with declarative shapes that describe what a nerd needs on the blackboard before it can fire. Machine-readable, composable, separable from code. Overkill for 9 nerds; pays off when you have 50 and want to visualize or reason about the dependency graph without reading source. W3C Recommendation. Python: `pyshacl`.
> https://www.w3.org/TR/shacl/

**Schema.org** -- Replaces the custom movie dict keys (`"title"`, `"genre"`, `"director"`) with `schema:Movie`, the vocabulary that Google, DBpedia, and Wikidata all already speak. Using it means movie data is legible to any linked-data tool without translation. This is the bridge to external data sources.
> https://schema.org/Movie

**Wikidata + DBpedia** -- This is the scaling claim. Replace the 5-movie hardcoded list with a SPARQL query against a public endpoint. Wikidata (CC0, community-curated, good genre coverage) is the recommended primary source; DBpedia (auto-extracted from Wikipedia, already types films as `schema:Movie`) is a useful complement. Both have SPARQL endpoints that can return Schema.org-shaped RDF directly, so the results go straight onto the blackboard with no parsing step.
> https://query.wikidata.org/ and https://dbpedia.org/sparql

**Dublin Core + MIME types** -- Shared names for metadata we already track. `dcterms:creator` instead of `created_by`, `dcterms:format` for payload MIME types. Low-cost, high-interop. ISO 15836.
> https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

---

**What we still invent:** Heat, thermal mass, and the tick-loop scheduler. No standard covers salience dynamics for multi-agent blackboard systems. This stays as a small custom `nerds:` ontology -- the part that's actually novel.

**Reading order:** JSON-LD intro, PROV-O primer, SKOS primer, SHACL Section 2, Schema.org Movie page, Wikidata SPARQL tutorial, rdflib Getting Started.
