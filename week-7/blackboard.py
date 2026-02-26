"""
Blackboard: a mostly-unorganized bag of typed data items with heat.

This is the shared workspace that nerds read from and write to.
Items have a type tag, a value, heat (salience), thermal mass,
provenance (which nerd created them), and a birth tick.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Heat(IntEnum):
    """Three-level salience score. Higher = hotter."""
    COLD = 0
    MEDIUM = 1
    HOT = 2


@dataclass
class Item:
    """A single thing on the blackboard."""
    type_tag: str            # e.g. "MovieTitle", "ColorPalette", "RenderedText"
    value: Any               # the actual payload
    heat: Heat = Heat.HOT    # hot off the press by default
    thermal_mass: int = 1    # bulkier things cool slower (1-5)
    created_by: str = ""     # nerd name
    birth_tick: int = 0      # when it appeared
    id: str = ""             # unique id, set by blackboard

    def __repr__(self):
        return f"<{self.type_tag}#{self.id} heat={self.heat.name} by={self.created_by}>"


class Blackboard:
    """
    The shared workspace. A bag of Items.

    Supports:
    - Adding items (they get an id and birth tick)
    - Querying by type tag (optionally filtered by minimum heat)
    - Global heat decay each tick
    - Picking a random item of a given type, weighted by heat
    """

    def __init__(self):
        self.items: list[Item] = []
        self.tick: int = 0
        self._next_id: int = 0

    def add(self, item: Item, created_by: str = "") -> Item:
        """Put a new item on the blackboard. Returns the item with id set."""
        item.id = f"{item.type_tag.lower()}_{self._next_id}"
        item.birth_tick = self.tick
        item.created_by = created_by or item.created_by
        self._next_id += 1
        self.items.append(item)
        return item

    def query(self, type_tag: str, min_heat: Heat = Heat.COLD) -> list[Item]:
        """Get all items of a given type with at least the given heat."""
        return [
            it for it in self.items
            if it.type_tag == type_tag and it.heat >= min_heat
        ]

    def pick(self, type_tag: str, min_heat: Heat = Heat.COLD) -> Item | None:
        """Pick a random item of the given type, weighted by heat."""
        candidates = self.query(type_tag, min_heat)
        if not candidates:
            return None
        weights = [1 + it.heat.value * 3 for it in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def has(self, type_tag: str) -> bool:
        return any(it.type_tag == type_tag for it in self.items)

    def decay_heat(self):
        """Cool everything down one notch, respecting thermal mass.

        Items with higher thermal mass have a chance of resisting decay.
        """
        for item in self.items:
            if item.heat == Heat.COLD:
                continue
            # Thermal mass gives a probability of resisting cooling
            # mass=1 -> always cools, mass=5 -> 20% chance of cooling
            if random.random() < 1.0 / item.thermal_mass:
                item.heat = Heat(item.heat.value - 1)

    def advance_tick(self):
        """Move time forward: decay heat, increment tick."""
        self.tick += 1
        self.decay_heat()

    def dump(self):
        """Print the blackboard state for debugging."""
        print(f"--- Blackboard (tick {self.tick}, {len(self.items)} items) ---")
        for it in self.items:
            print(f"  {it}")
        print("---")
