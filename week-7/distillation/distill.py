#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["llm", "llm-openrouter", "pyyaml"]
# ///
"""
NERDS Distillation Pipeline — Training-Free GRPO approach.

Phases:
  1. Explore  — LLM narrates G design trajectories per brief
  2. Extract  — LLM compares winners/losers, extracts NERDS-shaped insights
  3. Crystallize — LLM emits nerds_distilled.py from the experience library

Usage:
  uv run --script distill.py [--model MODEL] [--epochs E] [--group-size G]
                              [--briefs-file briefs.yaml] [--out nerds_distilled.py]
                              [--phase {1,2,3,all}] [--verbose]

Defaults: model=claude-sonnet-4.6 (via openrouter), epochs=1, G=3,
          briefs=5 built-in movie briefs, phase=all.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

import llm
import yaml


# ---------------------------------------------------------------------------
# Built-in movie briefs (same 5 as DISTILLATION.md §8.1)
# ---------------------------------------------------------------------------

BUILTIN_BRIEFS = [
    {"title": "Blade Runner", "genre": "sci-fi", "year": 1982,
     "tagline": "Man has made his match... now it's his problem.",
     "director": "Ridley Scott", "actors": ["Harrison Ford", "Rutger Hauer"]},
    {"title": "The Shining", "genre": "horror", "year": 1980,
     "tagline": "A masterpiece of modern horror.",
     "director": "Stanley Kubrick", "actors": ["Jack Nicholson", "Shelley Duvall"]},
    {"title": "Moonlight", "genre": "drama", "year": 2016,
     "tagline": "This is the story of a lifetime.",
     "director": "Barry Jenkins", "actors": ["Trevante Rhodes", "Andre Holland"]},
    {"title": "Chinatown", "genre": "noir", "year": 1974,
     "tagline": "You may think you know what's going on...",
     "director": "Roman Polanski", "actors": ["Jack Nicholson", "Faye Dunaway"]},
    {"title": "Mad Max: Fury Road", "genre": "action", "year": 2015,
     "tagline": "What a lovely day.",
     "director": "George Miller", "actors": ["Tom Hardy", "Charlize Theron"]},
]

SPECIALIST_SUGGESTIONS = """\
- MoviePicker: selects the source movie and seeds initial data
- TitleParser: splits the title into primary/secondary display chunks
- GenrePalette: derives a color palette from genre mood associations
- TypefacePicker: selects a typeface appropriate for the genre
- LayoutPicker: chooses a spatial composition template
- HeroImageGen: specifies the central visual element (colors, shapes, mood)
- GrainEffect: decides on post-processing texture effects
- Critic: evaluates completeness and coherence
- CompletionJudge: declares the design done when quality is sufficient
"""


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SIM_SYSTEM = """\
You are simulating a collaborative design session for a movie poster.
The session uses a blackboard architecture:

BLACKBOARD RULES:
- The blackboard is a shared workspace of typed items.
- Each item has: a type tag, a value, and a "heat" (HOT/MEDIUM/COLD)
  indicating how recently it was created.
- Specialists take turns. Each turn, one specialist:
  1. Reads relevant items from the blackboard
  2. Performs their narrow expertise
  3. Posts new item(s) to the blackboard
- No specialist knows about any other specialist. They only see the blackboard.
- Items cool over time. Recent items are HOT, older items are MEDIUM or COLD.

SPECIALIST TYPES (suggest but don't limit yourself to these):
{specialist_suggestions}

SESSION CONSTRAINTS:
- Run for 8-15 turns.
- Each turn must identify: which specialist acts, what they read, what they write
  (with explicit type tags and values).
- End with a CompletionJudge step when all major elements are present.
- Be concrete: give actual hex color values, actual text, actual layout
  coordinates — not vague descriptions.

For each turn, output exactly:

TICK <n>: <SpecialistName>
  READS: <type_tag> -> <summary of what they read, or NOTHING>
  WRITES: <type_tag> = <concrete value as YAML>
  RATIONALE: <one sentence on why this specialist made this choice>

After all ticks, output:
FINAL_ARTIFACT: <one paragraph describing the finished poster>
"""

SIM_USER = """\
Design brief:
{brief_yaml}

Narrate the full session.
"""

JUDGE_SYSTEM = """\
You are rating a movie poster design trajectory produced by a blackboard-based
multi-agent system. Rate on three criteria (1-5 each):

1. COHERENCE: Do the specialist decisions build on each other logically?
2. DOMAIN_FIT: Are the specific values (colors, fonts, layouts) appropriate
   for the genre?
3. SPECIFICITY: Are the outputs concrete enough to implement (actual hex
   colors, actual coordinates, actual text)?

Output ONLY valid YAML (no markdown fences):
coherence: N
domain_fit: N
specificity: N
total: N

where total = coherence + domain_fit + specificity (range 3-15).
"""

JUDGE_USER = """\
Movie brief:
{brief_yaml}

Trajectory:
{trajectory}
"""

EXTRACT_SYSTEM = """\
You are analyzing a group of design trajectories for the same movie poster brief.
Each trajectory simulates specialists collaborating on a blackboard.
Some trajectories scored higher than others.

Your job: identify what WINNING trajectories did differently from LOSING ones,
expressed as specific, reusable design patterns for a blackboard-based system.

Focus on:
1. TYPE VOCABULARY: What item types appeared consistently in winners?
2. DATA SCHEMAS: For each type, what fields did winners include that losers omitted?
3. HEURISTIC ENTRIES: What domain-specific mappings (genre->color, etc.) appeared
   in winning trajectories? Express as lookup table rows.
4. PRECONDITION RULES: What ordering dependencies made winners more coherent?
   Express as: "<Specialist> REQUIRES <ItemType> [ABSENT <ItemType>]"
5. THERMAL MASS: Which item types were foundational (many later reads) vs transient?
   Use integers 1-5 only (1=transient, 5=foundational).
6. SPECIALIST PATTERNS: What specialist archetypes appeared in winners?

Output ONLY valid YAML (no markdown fences) matching this structure:

type_vocabulary:
  - TypeName

data_schemas:
  TypeName:
    field_name: description

heuristic_entries:
  - table: TABLE_NAME
    key: key_string
    value:
      field: value
    evidence: "..."

precondition_rules:
  - "Specialist REQUIRES X ABSENT Y"

thermal_mass_assignments:
  TypeName: 1   # integer 1-5 only

specialist_patterns:
  - name: SpecialistName
    reads:
      - TypeTag
    writes:
      - TypeTag
    heuristic: brief description of its logic
    cooldown_rate: 2
    fires_once: false

narrative_insight: "one paragraph summarizing the key lesson"
"""

EXTRACT_USER = """\
Brief:
{brief_yaml}

{trajectories_block}

Current experience library (may be empty):
{experience_library_yaml}
"""

CRYSTALLIZE_SYSTEM = """\
You are a Python code generator. Given an experience library extracted from
movie poster design trajectories, generate a complete Python module that
implements a NERDS blackboard system.

CRITICAL Heat enum constraint:
  Heat is an IntEnum with exactly three values:
    Heat.COLD   = 0
    Heat.MEDIUM = 1
    Heat.HOT    = 2
   NEVER use Heat(3), Heat(5), Heat(10), etc. — they will raise ValueError.
  Use only Heat.HOT, Heat.MEDIUM, or Heat.COLD in all Item() constructors.
  thermal_mass is a SEPARATE integer field (1-5) on Item, not related to Heat.

Item constructor signature (exact field names):
  Item(type_tag="TypeName", value={...}, heat=Heat.HOT, thermal_mass=3)
  Fields are: type_tag (str), value (Any), heat (Heat), thermal_mass (int 1-5).
  Use bb.has("TypeName"), bb.pick("TypeName"), bb.query("TypeName") to inspect.

Nerd base class is a dataclass — ALWAYS instantiate with keyword args:
  MyNerd(name="MyNerd", heat=Heat.MEDIUM, cooldown_rate=2)
  Override can_run(self, bb) and run(self, bb) -> list[Item] in each subclass.

The module MUST:
1. Be importable as a standalone file
2. Start with these EXACT import lines (parent dir has both files):
     import sys, os
     sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
     from blackboard import Blackboard, Item, Heat
     from nerds import Nerd
3. Define all lookup tables as module-level dicts (e.g. GENRE_PALETTES, TYPEFACES, etc.)
4. Define one Nerd subclass per specialist pattern, each with:
   - can_run(bb) checking precondition rules
   - run(bb) implementing the specialist's behavior using heuristic tables
   - Appropriate cooldown_rate and heat (Heat.HOT, Heat.MEDIUM, or Heat.COLD only)
5. Define make_all_nerds() returning a list of all nerd instances.
   Nerd is a dataclass — instantiate with keyword args:
     MyNerd(name="MyNerd", heat=Heat.MEDIUM, cooldown_rate=2)
6. Assign thermal_mass (integer 1-5) to each Item based on the thermal_mass_assignments

Style constraints:
- Keep each nerd under 30 lines. Dumb is good.
- Use random.choice / random.uniform for variation, not complex logic.
- No LLM calls. No network calls. Pure Python + stdlib.
- Include a comment on each heuristic table entry citing its evidence.
- Import colorsys for color conversion.

Output ONLY the Python source code, no markdown fences, no explanation.
"""

CRYSTALLIZE_USER = """\
Experience library ({n_trajectories} trajectories across {n_briefs} briefs, {epochs} epochs):

{experience_library_yaml}

Domain: movie posters
Artifact type: movie poster
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str, verbose: bool = True):
    if verbose:
        print(f"[distill] {msg}", file=sys.stderr)


def call_llm(model_name: str, system: str, user: str, verbose: bool = False,
             stream_prefix: str = "", append_to: Path | None = None) -> str:
    """
    Single LLM call via the `llm` library.
    Streams chunks to `append_to` file if given (so you can tail -f it).
    Prints a dot per chunk to stderr to show liveness.
    """
    model = llm.get_model(model_name)
    response = model.prompt(user, system=system)
    chunks = []
    if verbose and stream_prefix:
        print(f"[distill] {stream_prefix} ", end="", flush=True, file=sys.stderr)
    fh = append_to.open("a") if append_to else None
    try:
        for chunk in response:
            chunks.append(chunk)
            if fh:
                fh.write(chunk)
                fh.flush()
            if verbose:
                print(".", end="", flush=True, file=sys.stderr)
    finally:
        if fh:
            fh.close()
    if verbose:
        print(file=sys.stderr)  # newline after dots
    return "".join(chunks)


def to_yaml(data: Any) -> str:
    """Serialize data to clean YAML using | block scalars for multiline strings."""
    return yaml.dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        default_style=None,
        width=88,
        Dumper=_BlockDumper,
    )


class _BlockDumper(yaml.Dumper):
    """YAML dumper that always uses | block style for multiline strings."""
    def represent_scalar(self, tag, value, style=None):
        if style is None and isinstance(value, str) and "\n" in value:
            style = "|"
        return super().represent_scalar(tag, value, style=style)


def extract_yaml(text: str) -> Any:
    """
    Parse YAML from a model response.
    Strips markdown fences if present, then tries yaml.safe_load.
    Falls back to JSON parse (models sometimes emit JSON anyway).
    """
    stripped = text.strip()
    # Strip ```yaml ... ``` or ``` ... ``` fences
    stripped = re.sub(r'^```(?:yaml|json)?\n?', '', stripped, flags=re.MULTILINE)
    stripped = re.sub(r'\n?```\s*$', '', stripped, flags=re.MULTILINE)
    stripped = stripped.strip()

    # Try YAML first
    try:
        result = yaml.safe_load(stripped)
        if result is not None:
            return result
    except yaml.YAMLError:
        pass

    # Fallback: JSON (some models ignore the YAML instruction)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Could not parse YAML or JSON from response:\n{text[:500]}")


def merge_experience(library: dict, new_insights: dict) -> dict:
    """
    Fold new_insights into library using Add/Modify/Keep logic.
    Simple prototype version: union lists, update dicts, keep narrative.
    """
    if not library:
        return dict(new_insights)

    merged = dict(library)

    # type_vocabulary: union
    existing_types = set(merged.get("type_vocabulary", []))
    for t in new_insights.get("type_vocabulary", []):
        existing_types.add(t)
    merged["type_vocabulary"] = sorted(existing_types)

    # data_schemas: merge fields
    schemas = dict(merged.get("data_schemas", {}))
    for type_name, fields in new_insights.get("data_schemas", {}).items():
        if type_name in schemas:
            schemas[type_name] = {**schemas[type_name], **fields}
        else:
            schemas[type_name] = fields
    merged["data_schemas"] = schemas

    # heuristic_entries: add new, update existing by (table, key)
    entries = {(e["table"], e["key"]): e
               for e in merged.get("heuristic_entries", [])}
    for e in new_insights.get("heuristic_entries", []):
        key = (e["table"], e["key"])
        if key in entries:
            old = entries[key]
            entries[key] = {**old, "value": e["value"],
                            "evidence": old.get("evidence", "") + " | " + e.get("evidence", "")}
        else:
            entries[key] = e
    merged["heuristic_entries"] = list(entries.values())

    # precondition_rules: union
    rules = set(merged.get("precondition_rules", []))
    for r in new_insights.get("precondition_rules", []):
        rules.add(r)
    merged["precondition_rules"] = sorted(rules)

    # thermal_mass_assignments: average if conflict, clamp to 1-5
    masses = dict(merged.get("thermal_mass_assignments", {}))
    for type_name, mass in new_insights.get("thermal_mass_assignments", {}).items():
        raw = int(mass)
        if type_name in masses:
            masses[type_name] = max(1, min(5, round((masses[type_name] + raw) / 2)))
        else:
            masses[type_name] = max(1, min(5, raw))
    merged["thermal_mass_assignments"] = masses

    # specialist_patterns: merge by name
    patterns = {p["name"]: p for p in merged.get("specialist_patterns", [])}
    for p in new_insights.get("specialist_patterns", []):
        patterns[p["name"]] = p  # newer overwrites
    merged["specialist_patterns"] = list(patterns.values())

    # narrative_insight: append
    old_narrative = merged.get("narrative_insight", "")
    new_narrative = new_insights.get("narrative_insight", "")
    merged["narrative_insight"] = (old_narrative + "\n\n" + new_narrative).strip()

    return merged


# ---------------------------------------------------------------------------
# Phase 1: Narrative simulation
# ---------------------------------------------------------------------------

def simulate_trajectory(model: str, brief: dict, verbose: bool,
                        stream_to: Path | None = None) -> str:
    """Ask the LLM to narrate one blackboard design session for this brief."""
    system = SIM_SYSTEM.format(specialist_suggestions=SPECIALIST_SUGGESTIONS)
    user = SIM_USER.format(brief_yaml=to_yaml(brief))
    return call_llm(model, system, user, verbose,
                    stream_prefix=f"SIM '{brief['title']}'",
                    append_to=stream_to)


def judge_trajectory(model: str, brief: dict, trajectory: str, verbose: bool,
                     stream_to: Path | None = None) -> dict:
    """Score a trajectory with the LLM-as-judge."""
    user = JUDGE_USER.format(
        brief_yaml=to_yaml(brief),
        trajectory=trajectory[:6000],  # cap to avoid runaway context
    )
    raw = call_llm(model, JUDGE_SYSTEM, user, verbose,
                   stream_prefix="JUDGE",
                   append_to=stream_to)
    try:
        scores = extract_yaml(raw)
        scores["total"] = scores.get("coherence", 0) + scores.get("domain_fit", 0) + scores.get("specificity", 0)
        return scores
    except ValueError:
        log(f"  WARNING: could not parse judge scores, defaulting to 0", verbose)
        return {"coherence": 0, "domain_fit": 0, "specificity": 0, "total": 0}


def phase1(model: str, briefs: list[dict], G: int, verbose: bool,
           traj_file: Path | None = None) -> list[dict]:
    """
    For each brief, generate G trajectories and score them.
    Streams raw LLM output into traj_file as it arrives (so you can tail -f),
    then appends a structured YAML record once each trajectory+scores are done.
    Returns a list of groups: [{brief, trajectories: [{text, scores}]}]
    """
    results = []
    for brief in briefs:
        log(f"\nPhase 1: '{brief['title']}' — {G} rollouts", verbose)
        group = []
        for g in range(G):
            log(f"  rollout {g+1}/{G}", verbose)
            # Write a human-readable header into the file before streaming
            if traj_file is not None:
                with traj_file.open("a") as f:
                    f.write(f"\n---\n# {brief['title']} — rollout {g+1}/{G}\n\n")
            traj_text = simulate_trajectory(model, brief, verbose, stream_to=traj_file)
            if traj_file is not None:
                with traj_file.open("a") as f:
                    f.write("\n\n# --- JUDGE ---\n\n")
            scores = judge_trajectory(model, brief, traj_text, verbose, stream_to=traj_file)
            log(f"  scores: coherence={scores['coherence']} domain_fit={scores['domain_fit']} "
                f"specificity={scores['specificity']} total={scores['total']}/15", verbose)
            # Append structured metadata record after the raw text
            if traj_file is not None:
                with traj_file.open("a") as f:
                    f.write("\n# --- SCORES ---\n")
                    f.write(to_yaml({"scores": scores}))
            group.append({"text": traj_text, "scores": scores})
        results.append({"brief": brief, "trajectories": group})
    return results


# ---------------------------------------------------------------------------
# Phase 2: Semantic advantage extraction
# ---------------------------------------------------------------------------

def phase2(model: str, groups: list[dict], experience_library: dict,
           verbose: bool, library_out: Path | None = None) -> dict:
    """
    For each group of G trajectories, extract NERDS-shaped insights and
    merge them into the experience library.
    """
    for group in groups:
        brief = group["brief"]
        trajs = group["trajectories"]
        log(f"Phase 2: extracting insights for '{brief['title']}'", verbose)

        sorted_trajs = sorted(trajs, key=lambda t: t["scores"]["total"], reverse=True)

        traj_blocks = []
        for i, t in enumerate(sorted_trajs):
            s = t["scores"]
            header = (f"TRAJECTORY {i+1} (reward: {s['total']}/15  "
                      f"coherence={s['coherence']} domain_fit={s['domain_fit']} "
                      f"specificity={s['specificity']})")
            block = f"{header}\n{t['text'][:3000]}"
            traj_blocks.append(block)

        user = EXTRACT_USER.format(
            brief_yaml=to_yaml(brief),
            trajectories_block="\n\n---\n\n".join(traj_blocks),
            experience_library_yaml=to_yaml(experience_library) if experience_library else "{}",
        )
        raw = call_llm(model, EXTRACT_SYSTEM, user, verbose,
                       stream_prefix=f"--- EXTRACTION: {brief['title']} ---")
        try:
            insights = extract_yaml(raw)
            experience_library = merge_experience(experience_library, insights)
            log(f"  merged. Library: "
                f"{len(experience_library.get('specialist_patterns', []))} specialists, "
                f"{len(experience_library.get('heuristic_entries', []))} heuristics, "
                f"{len(experience_library.get('precondition_rules', []))} rules.", verbose)
        except ValueError as e:
            log(f"  WARNING: could not parse extraction response: {e}", verbose)

        # Write library after each brief so you can watch it grow
        if library_out is not None:
            library_out.write_text(to_yaml(experience_library))

    return experience_library


# ---------------------------------------------------------------------------
# Phase 3: Crystallization
# ---------------------------------------------------------------------------

def phase3(model: str, experience_library: dict, n_trajectories: int,
           n_briefs: int, epochs: int, out_path: Path, verbose: bool) -> str:
    """
    Ask the LLM to compile the experience library into a Python nerds module.
    Write the result to out_path.
    """
    log("Phase 3: crystallizing experience library into Python...", verbose)
    user = CRYSTALLIZE_USER.format(
        experience_library_yaml=to_yaml(experience_library),
        n_trajectories=n_trajectories,
        n_briefs=n_briefs,
        epochs=epochs,
    )
    code = call_llm(model, CRYSTALLIZE_SYSTEM, user, verbose,
                    stream_prefix="--- CRYSTALLIZATION ---")

    # Strip markdown fences if the model wrapped it anyway
    code = re.sub(r'^```(?:python)?\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n?```\s*$', '', code, flags=re.MULTILINE)
    code = code.strip() + "\n"

    out_path.write_text(code)
    log(f"  wrote {len(code)} chars to {out_path}", verbose)
    return code


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_distilled(out_path: Path, verbose: bool) -> bool:
    """
    Quick smoke test: import the module, call make_all_nerds(),
    run a short blackboard loop.
    """
    import importlib.util
    import sys as _sys

    log(f"Validating {out_path}...", verbose)

    # Add both the output file's dir and the nerds/ parent to sys.path
    for p in [str(out_path.parent), str(out_path.parent.parent)]:
        if p not in _sys.path:
            _sys.path.insert(0, p)

    spec = importlib.util.spec_from_file_location("nerds_distilled", out_path)
    if spec is None or spec.loader is None:
        log("  FAIL: could not create module spec", verbose)
        return False
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as e:
        log(f"  FAIL: import error: {e}", verbose)
        return False

    if not hasattr(mod, "make_all_nerds"):
        log("  FAIL: make_all_nerds() not found", verbose)
        return False

    nerds = mod.make_all_nerds()
    if not isinstance(nerds, list) or len(nerds) == 0:
        log("  FAIL: make_all_nerds() returned empty list", verbose)
        return False

    log(f"  OK: {len(nerds)} nerds loaded", verbose)

    # Run a short loop
    from blackboard import Blackboard
    import random as _random
    _random.seed(42)
    bb = Blackboard()
    found_completion = False
    for tick in range(50):
        bb.advance_tick()
        for n in nerds:
            n.tick()
        eligible = [n for n in nerds if n.can_run(bb)]
        if not eligible:
            continue
        weights = [1 + n.heat.value * 3 for n in eligible]
        chosen = _random.choices(eligible, weights=weights, k=1)[0]
        items = chosen.call(bb)
        for item in items:
            bb.add(item, created_by=chosen.name)
        if bb.has("Completion"):
            found_completion = True
            log(f"  OK: Completion reached at tick {tick+1}", verbose)
            break

    if not found_completion:
        log(f"  WARNING: no Completion after 50 ticks (may still be usable)", verbose)

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="openrouter/anthropic/claude-sonnet-4.6",
                        help="llm model name (default: openrouter/anthropic/claude-sonnet-4.6)")
    parser.add_argument("--epochs", type=int, default=1,
                        help="number of epochs (default: 1; paper uses 3)")
    parser.add_argument("--group-size", type=int, default=3,
                        help="trajectories per brief G (default: 3; paper uses 5)")
    parser.add_argument("--briefs-file", type=Path, default=None,
                        help="YAML file with list of brief dicts (default: built-in 5 movies)")
    parser.add_argument("--out", type=Path, default=Path("nerds_distilled.py"),
                        help="output Python file (default: nerds_distilled.py)")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="all",
                        help="run only a specific phase (default: all)")
    parser.add_argument("--library-in", type=Path, default=None,
                        help="load existing experience library YAML (skip phases 1+2)")
    parser.add_argument("--library-out", type=Path, default=Path("experience_library.yaml"),
                        help="save experience library YAML (default: experience_library.yaml)")
    parser.add_argument("--no-validate", action="store_true",
                        help="skip post-crystallization validation")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="verbose logging (default: on)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress verbose logging")
    args = parser.parse_args()

    verbose = args.verbose and not args.quiet

    # Load briefs
    if args.briefs_file:
        briefs = yaml.safe_load(args.briefs_file.read_text())
        log(f"Loaded {len(briefs)} briefs from {args.briefs_file}", verbose)
    else:
        briefs = BUILTIN_BRIEFS
        log(f"Using {len(briefs)} built-in movie briefs", verbose)

    # Load existing library if requested
    experience_library: dict = {}
    if args.library_in:
        experience_library = yaml.safe_load(args.library_in.read_text()) or {}
        log(f"Loaded experience library from {args.library_in}", verbose)

    all_groups: list[dict] = []
    n_trajectories = 0

    if args.phase in ("1", "2", "all"):
        for epoch in range(args.epochs):
            log(f"\n=== EPOCH {epoch+1}/{args.epochs} ===", verbose)

            epoch_groups: list[dict] = []

            # Phase 1
            if args.phase in ("1", "all"):
                traj_dump = args.library_out.parent / f"trajectories_epoch{epoch+1}.yaml"
                traj_dump.write_text("")  # truncate/create fresh for this epoch
                log(f"Streaming trajectories to {traj_dump} (tail -f to watch)", verbose)
                epoch_groups = phase1(args.model, briefs, args.group_size, verbose,
                                      traj_file=traj_dump)
                all_groups.extend(epoch_groups)
                n_trajectories += len(briefs) * args.group_size

            # Phase 2
            if args.phase in ("2", "all"):
                experience_library = phase2(
                    args.model, epoch_groups,
                    experience_library, verbose,
                    library_out=args.library_out)
                log(f"Experience library saved to {args.library_out}", verbose)

        log(f"\nExperience library summary:", verbose)
        log(f"  type_vocabulary: {experience_library.get('type_vocabulary', [])}", verbose)
        log(f"  heuristic_entries: {len(experience_library.get('heuristic_entries', []))}", verbose)
        log(f"  specialist_patterns: {len(experience_library.get('specialist_patterns', []))}", verbose)
        log(f"  precondition_rules: {len(experience_library.get('precondition_rules', []))}", verbose)

    # Phase 3
    if args.phase in ("3", "all"):
        if not experience_library and args.library_in is None:
            log("WARNING: experience library is empty — crystallizing from nothing.", verbose)

        n_briefs = len(briefs)
        code = phase3(args.model, experience_library,
                      n_trajectories=n_trajectories,
                      n_briefs=n_briefs,
                      epochs=args.epochs,
                      out_path=args.out,
                      verbose=verbose)

        print(f"\n--- nerds_distilled.py ({len(code.splitlines())} lines) ---")
        print(code[:3000])
        if len(code) > 3000:
            print(f"... [{len(code)-3000} more chars]")

        if not args.no_validate:
            ok = validate_distilled(args.out, verbose)
            if ok:
                log("Validation passed.", verbose)
            else:
                log("Validation failed. Check the generated file.", verbose)
                sys.exit(1)

    log("\nDone.", verbose)


if __name__ == "__main__":
    main()
