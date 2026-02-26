"""
Main loop: the blackboard scheduler.

Each tick:
1. Decay heat on all items.
2. Tick all nerd cooldowns.
3. Select a nerd (weighted by heat, filtered by cooldown + preconditions).
4. Call the nerd: it reads from the blackboard, writes new items.
5. Check for Completion item.
6. If max ticks exceeded, force render anyway.

This is the core of the caricature's claim: no pipeline, no LLM,
just random nerd selection + heat dynamics = emergent poster.

Usage:
    uv run python main.py [--seed 42] [--max-ticks 30] [--verbose]
"""

from __future__ import annotations
import argparse
import random
import sys
from pathlib import Path

from blackboard import Blackboard, Heat
from nerds import Nerd, make_all_nerds
from render import render_poster


def select_nerd(nerds: list[Nerd], bb: Blackboard) -> Nerd | None:
    """Pick a nerd to call, weighted by heat, filtered by preconditions."""
    eligible = [n for n in nerds if n.can_run(bb)]
    if not eligible:
        return None
    weights = [1 + n.heat.value * 3 for n in eligible]
    return random.choices(eligible, weights=weights, k=1)[0]


def run(seed: int | None = None, max_ticks: int = 30, verbose: bool = False) -> Path:
    if seed is not None:
        random.seed(seed)

    bb = Blackboard()
    nerds = make_all_nerds()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    print(f"=== NERDS: Blackboard Poster Generator ===")
    print(f"Seed: {seed}  Max ticks: {max_ticks}")
    print(f"Nerds: {', '.join(n.name for n in nerds)}")
    print()

    for tick in range(max_ticks):
        bb.advance_tick()
        for n in nerds:
            n.tick()

        nerd = select_nerd(nerds, bb)
        if nerd is None:
            if verbose:
                print(f"  tick {bb.tick}: no eligible nerd, idling")
            continue

        results = nerd.call(bb)
        for item in results:
            bb.add(item, created_by=nerd.name)

        if verbose:
            types_added = [it.type_tag for it in results]
            print(f"  tick {bb.tick}: {nerd.name} -> {types_added}")

        # Check for completion
        if bb.has("Completion"):
            print(f"\n** Completion declared at tick {bb.tick}! **")
            break
    else:
        print(f"\n** Max ticks reached ({max_ticks}). Rendering what we have. **")

    if verbose:
        bb.dump()

    # Always render
    movie_item = bb.pick("MovieData")
    movie_name = "unknown"
    if movie_item:
        movie_name = movie_item.value["title"].lower().replace(" ", "_").replace(":", "")
    seed_tag = f"_s{seed}" if seed is not None else ""
    out_path = output_dir / f"poster_{movie_name}{seed_tag}.png"

    print(f"\nRendering poster -> {out_path}")
    render_poster(bb, out_path)
    print("Done.")

    # Print the caricature summary table
    _print_summary(bb)

    return out_path


def _print_summary(bb: Blackboard):
    """Print a table inspired by Table 1 in Smith & Mateas 2011."""
    print()
    print("=" * 64)
    print("CARICATURE SUMMARY (after Smith & Mateas, AIIDE 2011)")
    print("=" * 64)
    print()
    print("CLAIM (to be quickly recognized):")
    print("  Diverse generative output emerges from dumb specialists")
    print("  + heat-driven salience + random selection.")
    print("  No LLM. No explicit pipeline.")
    print()
    print("OVERSIMPLIFICATIONS (to be overlooked):")
    print("  - Movie data is a hardcoded dict, not a real database.")
    print("  - 'Images' are colored rectangles, not photographs.")
    print("  - Typography is system fonts, not curated typefaces.")
    print("  - Critique is a checklist, not aesthetic judgment.")
    print()
    print("ABSTRACTIONS (to be reused in the future):")
    print("  - Typed blackboard items with heat-based salience.")
    print("  - Nerd selection weighted by heat + preconditions.")
    print("  - Thermal mass affecting cooling rate.")
    print("  - Provenance tracking (which nerd created what).")
    print()
    print(f"Blackboard: {len(bb.items)} items across {bb.tick} ticks")
    type_counts = {}
    for it in bb.items:
        type_counts[it.type_tag] = type_counts.get(it.type_tag, 0) + 1
    for tag, count in sorted(type_counts.items()):
        print(f"  {tag}: {count}")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="NERDS: Blackboard Poster Generator")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--max-ticks", type=int, default=30, help="Maximum ticks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show tick-by-tick log")
    args = parser.parse_args()
    run(seed=args.seed, max_ticks=args.max_ticks, verbose=args.verbose)


if __name__ == "__main__":
    main()
