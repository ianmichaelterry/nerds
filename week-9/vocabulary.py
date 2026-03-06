"""
Vocabulary: namespace definitions, SKOS concept scheme, and SHACL shapes.

This module defines the shared semantic vocabulary for NERDS:
- Namespace bindings (Schema.org, PROV-O, SKOS, Dublin Core, custom nerds:)
- A SKOS concept scheme for blackboard artifact types
- SHACL shapes for nerd preconditions

By grounding everything in W3C standards, the system becomes self-describing:
any linked-data tool can inspect the blackboard, and any LLM can read the
vocabulary without project-specific documentation.
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, SKOS, DCTERMS, PROV

# ---------------------------------------------------------------------------
# Namespace definitions
# ---------------------------------------------------------------------------

# W3C / community standards
SCHEMA = Namespace("http://schema.org/")
SH = Namespace("http://www.w3.org/ns/shacl#")

# Custom NERDS ontology (the small part that's actually novel)
NERDS = Namespace("http://example.org/nerds/")

# All namespace bindings for graph serialization
NAMESPACE_BINDINGS = {
    "schema": SCHEMA,
    "prov": PROV,
    "skos": SKOS,
    "dcterms": DCTERMS,
    "sh": SH,
    "nerds": NERDS,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}


def bind_namespaces(g: Graph) -> Graph:
    """Bind all standard prefixes to a graph for clean serialization."""
    for prefix, ns in NAMESPACE_BINDINGS.items():
        g.bind(prefix, ns)
    return g


# ---------------------------------------------------------------------------
# SKOS Concept Scheme: artifact types
# ---------------------------------------------------------------------------

def build_concept_scheme() -> Graph:
    """
    Build the SKOS concept scheme for NERDS blackboard artifact types.

    Replaces ad-hoc type_tag strings with a navigable hierarchy:
      PosterArtifact (scheme)
        ├── FoundationalArtifact
        │   └── MovieData
        ├── VisualArtifact
        │   ├── ColorPalette
        │   ├── HeroImage
        │   ├── IconImage    (Noun Project icons)
        │   └── PostEffect
        ├── TypographicArtifact
        │   ├── TitleChunks
        │   └── Typeface
        ├── StructuralArtifact
        │   └── Layout
        └── MetaArtifact
            ├── Critique
            └── Completion
    """
    g = Graph()
    bind_namespaces(g)

    scheme = NERDS.PosterArtifact
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Poster Artifact Types", lang="en")))
    g.add((scheme, RDFS.comment, Literal(
        "Concept scheme for typed items on the NERDS blackboard.")))

    def add_concept(uri, label, broader=None, comment=None):
        g.add((uri, RDF.type, SKOS.Concept))
        g.add((uri, SKOS.inScheme, scheme))
        g.add((uri, SKOS.prefLabel, Literal(label, lang="en")))
        if broader:
            g.add((uri, SKOS.broader, broader))
        if comment:
            g.add((uri, RDFS.comment, Literal(comment)))

    # Top-level groupings
    add_concept(NERDS.FoundationalArtifact, "Foundational Artifact",
                comment="Seed data that everything else derives from.")
    add_concept(NERDS.VisualArtifact, "Visual Artifact",
                comment="Color, imagery, and post-processing data.")
    add_concept(NERDS.TypographicArtifact, "Typographic Artifact",
                comment="Title text and typeface selections.")
    add_concept(NERDS.StructuralArtifact, "Structural Artifact",
                comment="Layout and spatial organization.")
    add_concept(NERDS.MetaArtifact, "Meta Artifact",
                comment="Evaluation, critique, and completion signals.")

    # Leaf concepts (the actual item types nerds produce)
    add_concept(NERDS.MovieData, "Movie Data", NERDS.FoundationalArtifact,
                "A film's metadata: title, director, cast, genre, year.")
    add_concept(NERDS.Keywords, "Keywords", NERDS.FoundationalArtifact,
                "Plot-derived or genre-derived search keywords for icon selection.")
    add_concept(NERDS.ColorPalette, "Color Palette", NERDS.VisualArtifact,
                "Genre-derived key and accent colors.")
    add_concept(NERDS.HeroImage, "Hero Image", NERDS.VisualArtifact,
                "Procedural color-field imagery for the poster body.")
    add_concept(NERDS.IconImage, "Icon Image", NERDS.VisualArtifact,
                "Genre-relevant icon from the Noun Project, composited onto the poster.")
    add_concept(NERDS.CompositeImage, "Composite Image", NERDS.VisualArtifact,
                "Two or more images composited via ImageMagick, tracked by XMP sidecar.")
    add_concept(NERDS.PostEffect, "Post Effect", NERDS.VisualArtifact,
                "Film grain, vignette, or posterization flags.")
    add_concept(NERDS.TitleChunks, "Title Chunks", NERDS.TypographicArtifact,
                "Primary and secondary title text segments.")
    add_concept(NERDS.Typeface, "Typeface", NERDS.TypographicArtifact,
                "Selected typeface name, style, and weight.")
    add_concept(NERDS.Layout, "Layout", NERDS.StructuralArtifact,
                "Poster layout template with y-positions and alignment.")
    add_concept(NERDS.Critique, "Critique", NERDS.MetaArtifact,
                "Completeness evaluation with issue list and score.")
    add_concept(NERDS.PosterCritique, "Poster Critique", NERDS.MetaArtifact,
                "Visual critique of a rendered poster from a specific set of assets.")
    add_concept(NERDS.Completion, "Completion", NERDS.MetaArtifact,
                "Signal that the poster is done.")
    add_concept(NERDS.VisibilityCritique, "Visibility Critique", NERDS.MetaArtifact,
                "Per-source visibility scores for a composite image.")
    add_concept(NERDS.ContrastCritique, "Contrast Critique", NERDS.MetaArtifact,
                "Inter-source contrast measurement for a composite image.")

    return g


# ---------------------------------------------------------------------------
# SHACL Shapes: nerd preconditions
# ---------------------------------------------------------------------------

def build_shacl_shapes() -> Graph:
    """
    Build SHACL shapes that encode nerd activation preconditions.

    Each shape targets the blackboard node and describes what items
    must (or must not) be present for a nerd to fire. This replaces
    Python can_run() methods with declarative, machine-readable constraints.

    The scheduler validates the blackboard against each nerd's shape;
    if the shape conforms, the nerd is eligible.
    """
    g = Graph()
    bind_namespaces(g)

    def _has_type(shape_node, concept_uri, min_count=1, max_count=None):
        """Helper: add a property constraint requiring items of a given type."""
        prop = BNode()
        g.add((shape_node, SH.property, prop))
        g.add((prop, SH.path, NERDS.contains))
        inner = BNode()
        g.add((prop, SH.qualifiedValueShape, inner))
        g.add((inner, SH.hasValue, concept_uri))
        g.add((inner, SH.path, DCTERMS.type))
        g.add((prop, SH.qualifiedMinCount, Literal(min_count, datatype=XSD.integer)))
        if max_count is not None:
            g.add((prop, SH.qualifiedMaxCount, Literal(max_count, datatype=XSD.integer)))

    def _lacks_type(shape_node, concept_uri):
        """Helper: add a constraint requiring NO items of a given type."""
        _has_type(shape_node, concept_uri, min_count=0, max_count=0)

    # MoviePickerNerd: needs nothing, but must not already have MovieData
    movie_shape = NERDS.MoviePickerShape
    g.add((movie_shape, RDF.type, SH.NodeShape))
    g.add((movie_shape, SH.targetNode, NERDS.Blackboard))
    g.add((movie_shape, RDFS.label, Literal("MoviePicker precondition")))
    _lacks_type(movie_shape, NERDS.MovieData)

    # TitleParserNerd: needs MovieData
    title_shape = NERDS.TitleParserShape
    g.add((title_shape, RDF.type, SH.NodeShape))
    g.add((title_shape, SH.targetNode, NERDS.Blackboard))
    g.add((title_shape, RDFS.label, Literal("TitleParser precondition")))
    _has_type(title_shape, NERDS.MovieData)

    # GenrePaletteNerd: needs MovieData
    palette_shape = NERDS.GenrePaletteShape
    g.add((palette_shape, RDF.type, SH.NodeShape))
    g.add((palette_shape, SH.targetNode, NERDS.Blackboard))
    g.add((palette_shape, RDFS.label, Literal("GenrePalette precondition")))
    _has_type(palette_shape, NERDS.MovieData)

    # TypefaceNerd: no strict deps
    typeface_shape = NERDS.TypefaceShape
    g.add((typeface_shape, RDF.type, SH.NodeShape))
    g.add((typeface_shape, SH.targetNode, NERDS.Blackboard))
    g.add((typeface_shape, RDFS.label, Literal("Typeface precondition")))

    # LayoutNerd: no strict deps
    layout_shape = NERDS.LayoutShape
    g.add((layout_shape, RDF.type, SH.NodeShape))
    g.add((layout_shape, SH.targetNode, NERDS.Blackboard))
    g.add((layout_shape, RDFS.label, Literal("Layout precondition")))

    # HeroImageNerd: needs ColorPalette
    hero_shape = NERDS.HeroImageShape
    g.add((hero_shape, RDF.type, SH.NodeShape))
    g.add((hero_shape, SH.targetNode, NERDS.Blackboard))
    g.add((hero_shape, RDFS.label, Literal("HeroImage precondition")))
    _has_type(hero_shape, NERDS.ColorPalette)

    # KeywordNerd: needs MovieData
    keyword_shape = NERDS.KeywordShape
    g.add((keyword_shape, RDF.type, SH.NodeShape))
    g.add((keyword_shape, SH.targetNode, NERDS.Blackboard))
    g.add((keyword_shape, RDFS.label, Literal("Keyword precondition")))
    _has_type(keyword_shape, NERDS.MovieData)

    # IconNerd: needs Keywords + ColorPalette
    icon_shape = NERDS.IconShape
    g.add((icon_shape, RDF.type, SH.NodeShape))
    g.add((icon_shape, SH.targetNode, NERDS.Blackboard))
    g.add((icon_shape, RDFS.label, Literal("Icon precondition")))
    _has_type(icon_shape, NERDS.Keywords)
    _has_type(icon_shape, NERDS.ColorPalette)

    # GrainNerd: needs HeroImage
    grain_shape = NERDS.GrainShape
    g.add((grain_shape, RDF.type, SH.NodeShape))
    g.add((grain_shape, SH.targetNode, NERDS.Blackboard))
    g.add((grain_shape, RDFS.label, Literal("Grain precondition")))
    _has_type(grain_shape, NERDS.HeroImage)

    # CompositeNerd: needs at least a ColorPalette (visual content exists);
    # Python can_run() checks for >= 2 image items.
    composite_shape = NERDS.CompositeShape
    g.add((composite_shape, RDF.type, SH.NodeShape))
    g.add((composite_shape, SH.targetNode, NERDS.Blackboard))
    g.add((composite_shape, RDFS.label, Literal("Composite precondition")))
    _has_type(composite_shape, NERDS.ColorPalette)

    # PosterCriticNerd: needs MovieData, TitleChunks, and ColorPalette
    poster_critic_shape = NERDS.PosterCriticShape
    g.add((poster_critic_shape, RDF.type, SH.NodeShape))
    g.add((poster_critic_shape, SH.targetNode, NERDS.Blackboard))
    g.add((poster_critic_shape, RDFS.label, Literal("PosterCritic precondition")))
    _has_type(poster_critic_shape, NERDS.MovieData)
    _has_type(poster_critic_shape, NERDS.TitleChunks)
    _has_type(poster_critic_shape, NERDS.ColorPalette)

    # CritiqueNerd: needs at least tick > 3 (enforced in Python; shape just
    # requires MovieData to exist so there's something to critique)
    critique_shape = NERDS.CritiqueShape
    g.add((critique_shape, RDF.type, SH.NodeShape))
    g.add((critique_shape, SH.targetNode, NERDS.Blackboard))
    g.add((critique_shape, RDFS.label, Literal("Critique precondition")))
    _has_type(critique_shape, NERDS.MovieData)

    # CompletionNerd: needs a Critique with completeness >= 0.8
    # (The threshold check stays in Python; SHACL just requires Critique exists)
    completion_shape = NERDS.CompletionShape
    g.add((completion_shape, RDF.type, SH.NodeShape))
    g.add((completion_shape, SH.targetNode, NERDS.Blackboard))
    g.add((completion_shape, RDFS.label, Literal("Completion precondition")))
    _has_type(completion_shape, NERDS.Critique)
    _lacks_type(completion_shape, NERDS.Completion)

    # VisibilityCriticNerd: needs a CompositeImage to critique
    vis_crit_shape = NERDS.VisibilityCritiqueShape
    g.add((vis_crit_shape, RDF.type, SH.NodeShape))
    g.add((vis_crit_shape, SH.targetNode, NERDS.Blackboard))
    g.add((vis_crit_shape, RDFS.label, Literal("VisibilityCritique precondition")))
    _has_type(vis_crit_shape, NERDS.CompositeImage)

    # ContrastCriticNerd: needs a CompositeImage to critique
    con_crit_shape = NERDS.ContrastCritiqueShape
    g.add((con_crit_shape, RDF.type, SH.NodeShape))
    g.add((con_crit_shape, SH.targetNode, NERDS.Blackboard))
    g.add((con_crit_shape, RDFS.label, Literal("ContrastCritique precondition")))
    _has_type(con_crit_shape, NERDS.CompositeImage)

    return g
