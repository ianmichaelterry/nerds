"""
Blackboard: an RDF graph-backed shared workspace with PROV-O provenance.

Replaces the week-7 list[Item] with an rdflib Graph. Every item added
becomes a set of RDF triples: its type is a SKOS concept, its metadata
uses Dublin Core terms, its provenance uses PROV-O, and its payload
properties use Schema.org or the custom nerds: namespace.

Heat and thermal mass -- the novel parts with no W3C standard -- live
in the nerds: namespace.
"""

from __future__ import annotations
import random
from datetime import datetime
from enum import IntEnum

from rdflib import Graph, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, PROV, DCTERMS

from vocabulary import NERDS, SCHEMA, bind_namespaces, build_concept_scheme


class Heat(IntEnum):
    """Three-level salience score. Higher = hotter."""
    COLD = 0
    MEDIUM = 1
    HOT = 2


# RDF representations of heat levels
HEAT_URIS = {
    Heat.COLD: NERDS.Cold,
    Heat.MEDIUM: NERDS.Medium,
    Heat.HOT: NERDS.Hot,
}

URI_TO_HEAT = {v: k for k, v in HEAT_URIS.items()}


class Blackboard:
    """
    RDF graph-backed blackboard with PROV-O provenance.

    The graph contains:
    - A nerds:Blackboard node linked to items via nerds:contains
    - Each item as a blank node with dcterms:type, nerds:heat, etc.
    - PROV-O triples: items are prov:Entity, nerds are prov:SoftwareAgent,
      run() calls are prov:Activity
    - The SKOS concept scheme (loaded at init)

    Querying uses SPARQL or direct rdflib pattern matching.
    """

    def __init__(self):
        self.graph: Graph = Graph()
        bind_namespaces(self.graph)

        # Load the concept scheme into the graph
        self.graph += build_concept_scheme()

        # The blackboard node itself
        self.bb_node = NERDS.Blackboard
        self.graph.add((self.bb_node, RDF.type, NERDS.BlackboardSystem))
        self.graph.add((self.bb_node, RDFS.label, Literal("NERDS Blackboard")))

        self.tick: int = 0
        self._next_id: int = 0

    def add(self, type_concept: URIRef, properties: dict,
            created_by: str = "", heat: Heat = Heat.HOT,
            thermal_mass: int = 1) -> URIRef:
        """
        Add an item to the blackboard as RDF triples.

        Args:
            type_concept: SKOS concept URI (e.g. NERDS.MovieData)
            properties: dict of (predicate, object) pairs for the item
            created_by: name of the nerd that produced this
            heat: initial heat level
            thermal_mass: cooling resistance (1-10)

        Returns:
            The URI of the new item node.
        """
        # Create a URI for this item
        item_id = f"item_{self._next_id}"
        item_node = NERDS[item_id]
        self._next_id += 1

        # Core typing: this is a prov:Entity with a SKOS-typed dcterms:type
        self.graph.add((item_node, RDF.type, PROV.Entity))
        self.graph.add((item_node, DCTERMS.type, type_concept))
        self.graph.add((item_node, DCTERMS.identifier, Literal(item_id)))
        self.graph.add((item_node, DCTERMS.created, Literal(self.tick, datatype=XSD.integer)))

        # Heat and thermal mass (custom nerds: namespace)
        self.graph.add((item_node, NERDS.heat, HEAT_URIS[heat]))
        self.graph.add((item_node, NERDS.thermalMass,
                        Literal(thermal_mass, datatype=XSD.integer)))

        # Link to blackboard
        self.graph.add((self.bb_node, NERDS.contains, item_node))

        # Payload properties
        for pred, obj in properties.items():
            self.graph.add((item_node, pred, obj))

        # PROV-O provenance
        if created_by:
            agent = NERDS[f"agent_{created_by}"]
            self.graph.add((agent, RDF.type, PROV.SoftwareAgent))
            self.graph.add((agent, RDFS.label, Literal(created_by)))

            activity = NERDS[f"activity_{created_by}_tick{self.tick}_{item_id}"]
            self.graph.add((activity, RDF.type, PROV.Activity))
            self.graph.add((activity, PROV.wasAssociatedWith, agent))
            self.graph.add((activity, PROV.startedAtTime,
                            Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
            self.graph.add((item_node, PROV.wasGeneratedBy, activity))
            self.graph.add((item_node, PROV.wasAttributedTo, agent))

        return item_node

    def query_items(self, type_concept: URIRef,
                    min_heat: Heat = Heat.COLD) -> list[URIRef]:
        """Get all item URIs of a given type with at least the given heat."""
        results = []
        for item in self.graph.subjects(DCTERMS.type, type_concept):
            heat_uri = self.graph.value(item, NERDS.heat)
            if heat_uri and URI_TO_HEAT.get(heat_uri, Heat.COLD) >= min_heat:
                results.append(item)
        return results

    def has(self, type_concept: URIRef) -> bool:
        """Check if any item of the given type exists."""
        return len(self.query_items(type_concept)) > 0

    def pick(self, type_concept: URIRef,
             min_heat: Heat = Heat.COLD) -> URIRef | None:
        """Pick a random item of the given type, weighted by heat."""
        candidates = self.query_items(type_concept, min_heat)
        if not candidates:
            return None
        weights = []
        for item in candidates:
            heat_uri = self.graph.value(item, NERDS.heat)
            h = URI_TO_HEAT.get(heat_uri, Heat.COLD)
            weights.append(1 + h.value * 3)
        return random.choices(candidates, weights=weights, k=1)[0]

    def get_property(self, item: URIRef, predicate: URIRef):
        """Get a single property value from an item."""
        return self.graph.value(item, predicate)

    def get_properties(self, item: URIRef, predicate: URIRef) -> list:
        """Get all values for a property on an item."""
        return list(self.graph.objects(item, predicate))

    def decay_heat(self):
        """Cool everything down one notch, respecting thermal mass."""
        for item in self.graph.subjects(RDF.type, PROV.Entity):
            heat_uri = self.graph.value(item, NERDS.heat)
            if not heat_uri or heat_uri == HEAT_URIS[Heat.COLD]:
                continue
            current = URI_TO_HEAT.get(heat_uri, Heat.COLD)
            mass_lit = self.graph.value(item, NERDS.thermalMass)
            mass = int(mass_lit) if mass_lit else 1
            if random.random() < 1.0 / mass:
                new_heat = Heat(current.value - 1)
                self.graph.set((item, NERDS.heat, HEAT_URIS[new_heat]))

    def advance_tick(self):
        """Move time forward: decay heat, increment tick."""
        self.tick += 1
        self.decay_heat()

    def dump(self):
        """Print a human-readable summary of blackboard contents."""
        items = list(self.graph.subjects(RDF.type, PROV.Entity))
        print(f"--- Blackboard (tick {self.tick}, {len(items)} items) ---")
        for item in items:
            type_c = self.graph.value(item, DCTERMS.type)
            heat_uri = self.graph.value(item, NERDS.heat)
            heat_name = URI_TO_HEAT.get(heat_uri, Heat.COLD).name if heat_uri else "?"
            agent = self.graph.value(item, PROV.wasAttributedTo)
            agent_name = self.graph.value(agent, RDFS.label) if agent else "?"
            item_id = self.graph.value(item, DCTERMS.identifier) or "?"
            type_label = type_c.split("/")[-1] if type_c else "?"
            print(f"  <{type_label}#{item_id} heat={heat_name} by={agent_name}>")
        print("---")

    def has_fingerprint(self, type_concept: URIRef, fingerprint: str) -> bool:
        """Check if any item of the given type has the specified input fingerprint."""
        for item in self.graph.subjects(DCTERMS.type, type_concept):
            fp = self.graph.value(item, NERDS.inputFingerprint)
            if fp and str(fp) == fingerprint:
                return True
        return False

    def newest_item_tick(self, exclude_types: list[URIRef] | None = None) -> int:
        """Get the creation tick of the most recent item, optionally excluding certain types."""
        latest = -1
        for item in self.graph.subjects(RDF.type, PROV.Entity):
            if exclude_types:
                item_type = self.graph.value(item, DCTERMS.type)
                if item_type in exclude_types:
                    continue
            created = self.graph.value(item, DCTERMS.created)
            if created:
                latest = max(latest, int(created))
        return latest

    def serialize_provenance(self, format: str = "turtle") -> str:
        """Export the full graph (including provenance) in the given RDF format."""
        return self.graph.serialize(format=format)

    def item_count(self) -> int:
        """Count items on the blackboard."""
        return len(list(self.graph.subjects(RDF.type, PROV.Entity)))
