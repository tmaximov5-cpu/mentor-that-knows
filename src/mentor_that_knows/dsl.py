from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

GLYPHS = ("nul", "avo", "bex", "cyn", "dax", "emi", "fen", "gup", "hex")
HOT_VALUES = frozenset({2, 5, 7})
SPINS = ("calm", "keen", "wild")


def normalize(value: int) -> int:
    return value % len(GLYPHS)


def glyph(value: int) -> str:
    return GLYPHS[normalize(value)]


def parse_glyph(token: str) -> int:
    clean = token.strip().lower()
    if clean not in GLYPHS:
        raise ValueError(f"unknown Flux-9 glyph: {token!r}")
    return GLYPHS.index(clean)


def tilt(value: int, amount: int) -> int:
    return normalize(value + amount)


def mirror(value: int) -> int:
    return normalize(8 - value)


def braid(left: int, right: int) -> int:
    return normalize((2 * left) + right + 3)


def spark(left: int, right: int) -> int:
    if left <= right:
        return normalize(left + (2 * right))
    return normalize((2 * left) + right)


def cool_if_hot(value: int) -> tuple[int, bool]:
    if normalize(value) in HOT_VALUES:
        return normalize(value - 1), True
    return normalize(value), False


@dataclass(frozen=True)
class Step:
    name: str
    amount: int | None = None
    other: int | None = None

    def apply(self, value: int) -> int:
        if self.name == "tilt":
            if self.amount is None:
                raise ValueError("tilt requires amount")
            return tilt(value, self.amount)
        if self.name == "mirror":
            return mirror(value)
        if self.name == "braid":
            if self.other is None:
                raise ValueError("braid requires other")
            return braid(value, self.other)
        if self.name == "spark":
            if self.other is None:
                raise ValueError("spark requires other")
            return spark(value, self.other)
        raise ValueError(f"unknown step: {self.name!r}")

    def render(self) -> str:
        if self.name == "tilt":
            sign = "+" if (self.amount or 0) >= 0 else ""
            return f"tilt {sign}{self.amount}"
        if self.name == "mirror":
            return "mirror"
        if self.name == "braid":
            return f"braid with {glyph(self.other or 0)}"
        if self.name == "spark":
            return f"spark against {glyph(self.other or 0)}"
        return self.name


@dataclass(frozen=True)
class TraceEntry:
    before: int
    step: Step
    raw_after: int
    after: int
    cooled: bool = False

    def render(self) -> str:
        cool_note = ""
        if self.cooled:
            cool_note = f", heat slip cools {glyph(self.raw_after)} to {glyph(self.after)}"
        return f"{glyph(self.before)} -> {self.step.render()} -> {glyph(self.raw_after)}{cool_note}"


@dataclass(frozen=True)
class ChainTrace:
    start: int
    entries: tuple[TraceEntry, ...]

    @property
    def final(self) -> int:
        if not self.entries:
            return normalize(self.start)
        return self.entries[-1].after

    def compact(self) -> str:
        values = [glyph(self.start)]
        values.extend(glyph(entry.after) for entry in self.entries)
        return " -> ".join(values)

    def detailed(self) -> str:
        return "; ".join(entry.render() for entry in self.entries)

    def snag(self) -> str:
        for entry in self.entries:
            if entry.cooled:
                return (
                    f"I almost missed the heat slip: raw {glyph(entry.raw_after)} "
                    f"had to cool to {glyph(entry.after)}."
                )
        for entry in self.entries:
            if entry.raw_after < entry.before and entry.step.name == "tilt":
                return f"The wrap-around happened on {entry.step.render()}, so I checked the glyph ring."
        return f"I had to keep the glyph order nearby and not treat {glyph(self.final)} as a normal number."


def evaluate_chain(start: int, steps: Iterable[Step], heat_slip: bool = False) -> ChainTrace:
    value = normalize(start)
    entries: list[TraceEntry] = []
    for step in steps:
        raw_after = step.apply(value)
        after = raw_after
        cooled = False
        if heat_slip:
            after, cooled = cool_if_hot(raw_after)
        entries.append(
            TraceEntry(
                before=value,
                step=step,
                raw_after=raw_after,
                after=after,
                cooled=cooled,
            )
        )
        value = after
    return ChainTrace(start=normalize(start), entries=tuple(entries))


@dataclass(frozen=True)
class Particle:
    mass: int
    spin: int

    def render(self) -> str:
        return f"{glyph(self.mass)}:{SPINS[self.spin % len(SPINS)]}"


@dataclass(frozen=True)
class CollisionTrace:
    left: Particle
    right: Particle
    raw_mass: int
    spin: int
    mass: int
    cooled: bool

    @property
    def final(self) -> Particle:
        return Particle(self.mass, self.spin)

    def detailed(self) -> str:
        cool = ""
        if self.cooled:
            cool = f"; wild spin cools {glyph(self.raw_mass)} to {glyph(self.mass)}"
        return (
            f"{self.left.render()} collides with {self.right.render()} -> "
            f"raw mass {glyph(self.raw_mass)}, spin {SPINS[self.spin]}{cool}"
        )

    def snag(self) -> str:
        if self.cooled:
            return f"I forgot once that wild spin cools the mass from {glyph(self.raw_mass)} to {glyph(self.mass)}."
        return f"I checked the spin before changing the mass; it stayed {SPINS[self.spin]}."


def collide(left: Particle, right: Particle) -> CollisionTrace:
    raw_mass = braid(left.mass, right.mass)
    spin = (left.spin + right.spin + raw_mass) % len(SPINS)
    cooled_mass = raw_mass
    cooled = False
    if spin == 2:
        cooled_mass, cooled = cool_if_hot(raw_mass)
    return CollisionTrace(
        left=left,
        right=right,
        raw_mass=raw_mass,
        spin=spin,
        mass=cooled_mass,
        cooled=cooled,
    )

