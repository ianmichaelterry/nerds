"""
Main loop: the semantic blackboard scheduler.

Week 8 upgrade: nerd eligibility is checked via SHACL shape validation
against the RDF blackboard graph. After the run, the full provenance
graph (PROV-O + SKOS + Schema.org) is exported as Turtle, and a
Showboat-style narrated markdown document tells the story of the run.

Each tick:
1. Decay heat on all items (RDF graph update).
2. Tick all nerd cooldowns.
3. For each nerd with a SHACL shape, validate the blackboard.
4. Select an eligible nerd (weighted by heat).
5. Call the nerd: it reads RDF, writes new triples.
6. Check for Completion.

Usage:
    cd week-8
    uv run python main.py [--seed 42] [--max-ticks 30] [--verbose]
"""

from __future__ import annotations
import argparse
import random
import sys
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import DCTERMS, PROV, RDF
from pyshacl import validate as shacl_validate

from blackboard import Blackboard, Heat
from nerds import Nerd, make_all_nerds
from render import render_poster
from vocabulary import NERDS, SCHEMA, build_shacl_shapes, bind_namespaces
from narrator import Narrator


# ---------------------------------------------------------------------------
# Narrative detail generators: produce rich markdown for each nerd type
# ---------------------------------------------------------------------------

def _narrate_nerd(nerd_name: str, bb: Blackboard, result_nodes: list) -> str:
    """Generate a detail paragraph for the narrative, based on what the nerd did."""
    details = []

    if nerd_name == "MoviePicker" and result_nodes:
        node = result_nodes[0]
        title = bb.get_property(node, SCHEMA.name)
        director = bb.get_property(node, SCHEMA.director)
        genre = bb.get_property(node, SCHEMA.genre)
        year = bb.get_property(node, SCHEMA.datePublished)
        actors = bb.get_property(node, SCHEMA.actor)
        tagline = bb.get_property(node, SCHEMA.description)
        wiki = bb.get_property(node, None)  # seeAlso

        details.append(f"The MoviePicker queried **Wikidata** via SPARQL for notable films, "
                       f"then selected one at random.")
        details.append("")
        details.append(f"| Field | Value |")
        details.append(f"|---|---|")
        details.append(f"| `schema:name` | **{title}** |")
        details.append(f"| `schema:director` | {director} |")
        details.append(f"| `schema:genre` | {genre} |")
        if year:
            details.append(f"| `schema:datePublished` | {year} |")
        if actors:
            details.append(f"| `schema:actor` | {actors} |")
        if tagline:
            details.append(f"| `schema:description` | *{tagline}* |")
        details.append("")
        details.append("This data arrived as `schema:Movie`-shaped RDF triples, "
                       "the same vocabulary Google and Wikidata speak. "
                       "No parsing, no key mapping -- it went straight onto the graph.")

    elif nerd_name == "TitleParser" and result_nodes:
        node = result_nodes[0]
        primary = bb.get_property(node, NERDS.primaryTitle)
        secondary = bb.get_property(node, NERDS.secondaryTitle)
        if secondary:
            details.append(f'Split the title into primary **"{primary}"** and '
                           f'secondary **"{secondary}"**.')
        else:
            details.append(f'Title is a single chunk: **"{primary}"**. No subtitle.')

    elif nerd_name == "KeywordExtractor" and result_nodes:
        node = result_nodes[0]
        kw_list = bb.get_property(node, NERDS.keywordList)
        source = bb.get_property(node, NERDS.keywordSource)
        keywords = str(kw_list).split(",") if kw_list else []
        details.append(f"Extracted **{len(keywords)} keywords** (source: {source}):")
        details.append(f"`{', '.join(keywords[:10])}`"
                       + (f" ... (+{len(keywords)-10} more)" if len(keywords) > 10 else ""))
        if str(source) == "omdb":
            details.append("")
            details.append("Keywords were extracted from the OMDb short plot by "
                           "filtering stop words and verb/adjective suffixes.")
        else:
            details.append("")
            details.append("OMDb lookup failed; fell back to genre-based icon terms.")

    elif nerd_name == "GenrePalette" and result_nodes:
        node = result_nodes[0]
        key_c = bb.get_property(node, NERDS.keyColor)
        accent_c = bb.get_property(node, NERDS.accentColor)
        mid_c = bb.get_property(node, NERDS.midColor)
        genre = bb.get_property(node, SCHEMA.genre)
        details.append(f"Derived a color palette from genre **{genre}**:")
        details.append("")
        details.append(f"| Role | Hex |")
        details.append(f"|---|---|")
        details.append(f"| Key (background) | `{key_c}` |")
        details.append(f"| Accent (text, lines) | `{accent_c}` |")
        details.append(f"| Mid (gradients) | `{mid_c}` |")

    elif nerd_name == "TypefacePicker" and result_nodes:
        node = result_nodes[0]
        name = bb.get_property(node, NERDS.typefaceName)
        style = bb.get_property(node, NERDS.typefaceStyle)
        weight = bb.get_property(node, NERDS.typefaceWeight)
        details.append(f"Selected typeface **{name}** (style: {style}, weight: {weight}). "
                       f"Genre preference had a 60% influence on the pick.")

    elif nerd_name == "LayoutPicker" and result_nodes:
        node = result_nodes[0]
        name = bb.get_property(node, NERDS.layoutName)
        details.append(f'Chose layout template **"{name}"**. '
                       f"This sets y-positions for the title, image area, tagline, and credits.")

    elif nerd_name == "HeroImageGen" and result_nodes:
        node = result_nodes[0]
        count = bb.get_property(node, NERDS.blockCount)
        details.append(f"Generated **{count} overlapping color-field blocks** "
                       f"with varying opacity, derived from the palette. "
                       f"These form the abstract background texture behind the icon.")

    elif nerd_name == "IconFetcher" and result_nodes:
        node = result_nodes[0]
        term = bb.get_property(node, NERDS.iconTerm)
        icon_id = bb.get_property(node, NERDS.iconId)
        query = bb.get_property(node, NERDS.iconSearchQuery)
        details.append(f'Searched the **Noun Project API** for keyword-derived icons '
                       f'(query: "{query or term}"). '
                       f'Found and downloaded **"{term}"** (icon #{icon_id}) as a tinted PNG.')

    elif nerd_name == "GrainEffect" and result_nodes:
        node = result_nodes[0]
        effects = str(bb.get_property(node, NERDS.effects) or "")
        effects_list = [e.strip() for e in effects.split(",") if e.strip()]
        if effects_list:
            details.append(f"Post-processing effects selected: "
                           f"{', '.join(f'**{e}**' for e in effects_list)}.")
        else:
            details.append("No post-processing effects this time (all coin flips came up tails).")

    elif nerd_name == "Compositor" and result_nodes:
        node = result_nodes[0]
        w = bb.get_property(node, NERDS.compositeWidth)
        h = bb.get_property(node, NERDS.compositeHeight)
        ox = bb.get_property(node, NERDS.overlayOffsetX)
        oy = bb.get_property(node, NERDS.overlayOffsetY)
        xmp = bb.get_property(node, NERDS.compositeXmpPath)
        details.append(f"Composited two images using **ImageMagick** "
                       f"(overlay offset: {ox}, {oy}) producing a {w}\u00d7{h} result.")
        if xmp:
            details.append(f"XMP sidecar tracking source positions: `{xmp}`")

    elif nerd_name == "VisibilityCritic" and result_nodes:
        node = result_nodes[0]
        score = bb.get_property(node, NERDS.visibilityScore)
        scores_str = bb.get_property(node, NERDS.sourceScores)
        pct = f"{float(score):.0%}" if score else "?"
        details.append(f"Analyzed source visibility in a composite: "
                       f"overall **{pct}**.")
        if scores_str:
            details.append(f"Per-source scores: `{scores_str}`")
        if score and float(score) < 0.2:
            details.append("Poor visibility — composite demoted to COLD.")

    elif nerd_name == "ContrastCritic" and result_nodes:
        node = result_nodes[0]
        score = bb.get_property(node, NERDS.contrastScore)
        dist = bb.get_property(node, NERDS.minPairwiseDistance)
        pct = f"{float(score):.0%}" if score else "?"
        dist_str = f"{float(dist):.1f}" if dist else "?"
        details.append(f"Measured inter-source contrast in a composite: "
                       f"score **{pct}** (min RGB distance: {dist_str}).")
        if score and float(score) < 0.15:
            details.append("Low contrast — composite demoted to COLD.")

    elif nerd_name == "Critic" and result_nodes:
        node = result_nodes[0]
        completeness = bb.get_property(node, NERDS.completeness)
        issues = str(bb.get_property(node, NERDS.issues) or "")
        score = float(completeness) if completeness else 0
        pct = int(score * 100)
        if issues and issues != "none":
            issue_list = issues.split(",")
            details.append(f"Completeness: **{pct}%**. Still missing: "
                           f"{', '.join(f'`{i.strip()}`' for i in issue_list)}.")
        else:
            details.append(f"Completeness: **{pct}%**. All artifact types present.")
        if score >= 0.8:
            details.append("Score is >= 80% -- the CompletionJudge can now fire.")

    elif nerd_name == "PosterCritic" and result_nodes:
        node = result_nodes[0]
        passes = bb.get_property(node, NERDS.passes)
        img_path = bb.get_property(node, NERDS.posterImage)
        details.append(f"Rendered a temporary poster")
        if img_path:
            details.append(f"(`{img_path}`) ")
        details.append(f"and critiqued it: **{'passes' if passes else 'fails'}**.")

    elif nerd_name == "CompletionJudge" and result_nodes:
        details.append("The CompletionJudge reviewed the latest critique, "
                       "found the score >= 80%, and **declared the poster complete**.")

    return "\n".join(details)


# ---------------------------------------------------------------------------
# SHACL eligibility check
# ---------------------------------------------------------------------------

def check_shacl_eligibility(nerd: Nerd, bb: Blackboard,
                            shapes_graph: Graph) -> bool:
    """
    Validate the blackboard against a nerd's SHACL shape.

    Returns True if the blackboard conforms to the shape (preconditions met).
    If the nerd has no SHACL shape, returns True (no constraints).
    """
    if not nerd.shacl_shape:
        return True

    # Extract just this nerd's shape subgraph
    nerd_shapes = Graph()
    bind_namespaces(nerd_shapes)
    for s, p, o in shapes_graph.triples((nerd.shacl_shape, None, None)):
        nerd_shapes.add((s, p, o))
        if hasattr(o, 'n3') and str(o).startswith('_:'):
            for s2, p2, o2 in shapes_graph.triples((o, None, None)):
                nerd_shapes.add((s2, p2, o2))
                if hasattr(o2, 'n3') and str(o2).startswith('_:'):
                    for s3, p3, o3 in shapes_graph.triples((o2, None, None)):
                        nerd_shapes.add((s3, p3, o3))

    try:
        conforms, _, _ = shacl_validate(
            data_graph=bb.graph,
            shacl_graph=nerd_shapes,
            abort_on_first=True,
        )
        return conforms
    except Exception:
        return True


def select_nerd(nerds: list[Nerd], bb: Blackboard,
                shapes_graph: Graph, verbose: bool = False) -> Nerd | None:
    """Pick a nerd to call, filtered by cooldown + SHACL + Python can_run."""
    eligible = []
    for n in nerds:
        if not n.can_run(bb):
            continue
        if not check_shacl_eligibility(n, bb, shapes_graph):
            if verbose:
                print(f"    [{n.name}] SHACL precondition not met")
            continue
        eligible.append(n)

    if not eligible:
        return None
    weights = [1 + n.heat.value * 3 for n in eligible]
    return random.choices(eligible, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(seed: int | None = None, max_ticks: int = 50,
        verbose: bool = False) -> Path:
    if seed is not None:
        random.seed(seed)

    bb = Blackboard()
    nerds = make_all_nerds()
    shapes_graph = build_shacl_shapes()
    narrator = Narrator()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    temp_dir = output_dir / "temp"
    if temp_dir.exists():
        for f in temp_dir.iterdir():
            f.unlink()
    temp_dir.mkdir(exist_ok=True)

    nerd_names = [n.name for n in nerds]

    print("=" * 64)
    print("SEMANTIC NERDS: Blackboard Poster Generator (Week 8)")
    print("=" * 64)
    print(f"Seed: {seed}  Max ticks: {max_ticks}")
    print(f"Nerds: {', '.join(nerd_names)}")
    print()

    narrator.header(seed, max_ticks, nerd_names)

    completed = False
    for tick in range(max_ticks):
        bb.advance_tick()
        for n in nerds:
            n.tick()

        nerd = select_nerd(nerds, bb, shapes_graph, verbose)
        if nerd is None:
            if verbose:
                print(f"  tick {bb.tick}: no eligible nerd, idling")
            narrator.tick_idle(bb.tick)
            continue

        results = nerd.call(bb)

        # Figure out what types were produced for logging
        types_added = []
        for node in results:
            t = bb.get_property(node, DCTERMS.type)
            types_added.append(str(t).split("/")[-1] if t else "?")

        if verbose:
            print(f"  tick {bb.tick}: {nerd.name} -> {types_added}")

        # Narrate this tick
        detail = _narrate_nerd(nerd.name, bb, results)
        narrator.tick_nerd(bb.tick, nerd.name, types_added, detail)

        # Check for completion
        if bb.has(NERDS.Completion):
            print(f"\n** Completion declared at tick {bb.tick}! **")
            narrator.completion(bb.tick, bb.item_count(), len(bb.graph))
            completed = True
            break

    if not completed:
        print(f"\n** Max ticks reached ({max_ticks}). Rendering what we have. **")
        narrator.timeout(bb.tick, max_ticks)

    if verbose:
        bb.dump()

    # --- Build picks from the latest approved PosterCritique (if any) ---
    approved = bb.pick(NERDS.PosterCritique)
    picks: dict | None = None
    if approved:
        picks = {}
        for key, pred in [
            ('movie',   NERDS.usedMovie),
            ('title',   NERDS.usedTitle),
            ('palette', NERDS.usedPalette),
            ('layout',  NERDS.usedLayout),
            ('hero',    NERDS.usedHero),
            ('typeface', NERDS.usedTypeface),
            ('effect',  NERDS.usedEffect),
            ('icon',    NERDS.usedIcon),
            ('composite', NERDS.usedComposite),
        ]:
            val = bb.get_property(approved, pred)
            if val:
                picks[key] = val
        print(f"Using assets from approved PosterCritique (tick "
              f"{bb.get_property(approved, NERDS.critiqueTick)})")

    # --- Render the poster ---
    movie_node = (picks or {}).get('movie') or bb.pick(NERDS.MovieData)
    movie_name = "unknown"
    if movie_node:
        name = bb.get_property(movie_node, SCHEMA.name)
        if name:
            movie_name = str(name).lower().replace(" ", "_").replace(":", "")
    seed_tag = f"_s{seed}" if seed is not None else ""
    out_path = output_dir / f"poster_{movie_name}{seed_tag}.png"

    print(f"\nRendering poster -> {out_path}")
    render_poster(bb, out_path, picks=picks)
    print("Done.")

    # Embed poster in narrative
    narrator.poster_image(out_path.name)

    # --- Export provenance graph ---
    prov_path = output_dir / f"provenance_{movie_name}{seed_tag}.ttl"
    prov_turtle = bb.serialize_provenance(format="turtle")
    prov_path.write_text(prov_turtle)
    print(f"Provenance graph -> {prov_path}")
    print(f"  ({bb.item_count()} items, "
          f"{len(bb.graph)} triples in the RDF graph)")

    # Add provenance excerpt to narrative (first ~40 lines of turtle)
    turtle_lines = prov_turtle.strip().split("\n")
    # Find some interesting provenance triples (skip prefix declarations)
    interesting = [l for l in turtle_lines if not l.startswith("@prefix")]
    excerpt = "\n".join(interesting[:35]).strip()
    if excerpt:
        narrator.provenance_excerpt(excerpt)

    # --- Blackboard summary in narrative ---
    items = list(bb.graph.subjects(RDF.type, PROV.Entity))
    type_counts: dict[str, int] = {}
    for item in items:
        t = bb.graph.value(item, DCTERMS.type)
        label = str(t).split("/")[-1] if t else "unknown"
        type_counts[label] = type_counts.get(label, 0) + 1
    narrator.blackboard_summary(type_counts)

    narrator.footer()

    # Save narrative
    narrative_path = output_dir / f"narrative_{movie_name}{seed_tag}.md"
    narrator.save(narrative_path)
    print(f"Narrative -> {narrative_path}")

    # Print the caricature summary table
    _print_summary(bb, type_counts)

    return out_path


def _print_summary(bb: Blackboard, type_counts: dict[str, int]):
    """Print a table inspired by Table 1 in Smith & Mateas 2011."""
    print()
    print("=" * 64)
    print("CARICATURE SUMMARY (after Smith & Mateas, AIIDE 2011)")
    print("=" * 64)
    print()
    print("CLAIM (to be quickly recognized):")
    print("  Diverse generative output emerges from dumb specialists")
    print("  + heat-driven salience + random selection.")
    print("  No LLM at runtime. No explicit pipeline.")
    print()
    print("OVERSIMPLIFICATIONS (to be overlooked):")
    print("  - 'Images' are Noun Project icons + colored rectangles.")
    print("  - Typography is system fonts, not curated typefaces.")
    print("  - Critique is a checklist, not aesthetic judgment.")
    print()
    print("ABSTRACTIONS (to be reused in the future):")
    print("  - RDF graph blackboard with SKOS-typed items.")
    print("  - PROV-O provenance: every item traces back to its nerd.")
    print("  - SHACL preconditions: declarative nerd activation rules.")
    print("  - Schema.org vocabulary: movie data is web-standard.")
    print("  - Wikidata SPARQL: any film in existence, not 5 hardcoded.")
    print("  - Noun Project API: real icons, not colored rectangles.")
    print("  - Heat + thermal mass in a custom nerds: ontology.")
    print()
    print(f"Blackboard: {bb.item_count()} items across {bb.tick} ticks")
    for tag, count in sorted(type_counts.items()):
        print(f"  {tag}: {count}")
    print(f"RDF graph: {len(bb.graph)} triples total")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic NERDS: Blackboard Poster Generator (Week 8)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--max-ticks", type=int, default=50, help="Maximum ticks")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show tick-by-tick log")
    args = parser.parse_args()
    run(seed=args.seed, max_ticks=args.max_ticks, verbose=args.verbose)


if __name__ == "__main__":
    main()
