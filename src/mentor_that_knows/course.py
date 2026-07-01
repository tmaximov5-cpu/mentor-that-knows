from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .dsl import (
    GLYPHS,
    SPINS,
    Particle,
    Step,
    collide,
    evaluate_chain,
    glyph,
    mirror,
    parse_glyph,
)


@dataclass(frozen=True)
class Task:
    prompt: str
    answer: str
    trace: str
    snag: str
    key_point: str


@dataclass(frozen=True)
class LessonCard:
    number: int
    title: str
    skill: str
    rule_text: str
    verification_focus: str
    practice: Task
    transfer: Task


def glyph_ring() -> str:
    return " < ".join(GLYPHS)


def _chain_task(
    start: int,
    steps: list[Step],
    heat_slip: bool,
    label: str,
    key_point: str,
) -> Task:
    trace = evaluate_chain(start, steps, heat_slip=heat_slip)
    step_text = ", then ".join(step.render() for step in steps)
    heat = " Use the heat-slip rule after every step." if heat_slip else ""
    return Task(
        prompt=f"{label}: start at {glyph(start)}; apply {step_text}.{heat}",
        answer=f"final {glyph(trace.final)}",
        trace=trace.detailed(),
        snag=trace.snag(),
        key_point=key_point,
    )


def _collision_task(left: Particle, right: Particle, label: str) -> Task:
    trace = collide(left, right)
    return Task(
        prompt=f"{label}: collide {left.render()} with {right.render()}.",
        answer=f"final particle {trace.final.render()}",
        trace=trace.detailed(),
        snag=trace.snag(),
        key_point="The mentor checks that the student computes mass first, then spin, then any wild-spin cooling.",
    )


def _debug_task(start: int, steps: list[Step], wrong_line: int, label: str) -> Task:
    trace = evaluate_chain(start, steps, heat_slip=True)
    rendered = [entry.render() for entry in trace.entries]
    bad_entry = trace.entries[wrong_line - 1]
    wrong_after = glyph(bad_entry.after + 1)
    rendered[wrong_line - 1] = (
        f"{glyph(bad_entry.before)} -> {bad_entry.step.render()} -> {wrong_after}"
    )
    prompt = (
        f"{label}: find the first wrong line in this heat-slip trace. "
        + " | ".join(f"{index + 1}. {line}" for index, line in enumerate(rendered))
    )
    return Task(
        prompt=prompt,
        answer=(
            f"line {wrong_line}; it should end at {glyph(bad_entry.after)} "
            f"after checking {bad_entry.step.render()}"
        ),
        trace=trace.detailed(),
        snag="I had to compare the trace line by line instead of only recomputing the final answer.",
        key_point="The mentor asks for the first wrong line, not just the corrected final glyph.",
    )


def _random_step(rng: Random, allow_binary: bool = False) -> Step:
    if allow_binary and rng.random() < 0.45:
        return Step(rng.choice(["braid", "spark"]), other=rng.randrange(9))
    if rng.random() < 0.35:
        return Step("mirror")
    return Step("tilt", amount=rng.choice([-4, -3, -2, -1, 1, 2, 3, 4]))


def build_course(seed: int = 7) -> list[LessonCard]:
    rng = Random(seed)

    lesson1 = LessonCard(
        number=1,
        title="Glyph ring and tilt",
        skill="Read Flux-9 glyphs and move around the nine-glyph ring.",
        rule_text=(
            f"The glyph ring is {glyph_ring()}. A tilt +k moves k slots forward, "
            "and tilt -k moves backward, wrapping around the ring."
        ),
        verification_focus="Ask for the exact wrap or non-wrap move and a fresh tilt.",
        practice=_chain_task(6, [Step("tilt", amount=3)], False, "Practice", "Tilt is movement on the ring."),
        transfer=_chain_task(8, [Step("tilt", amount=4)], False, "Transfer", "A new start checks application."),
    )

    lesson2 = LessonCard(
        number=2,
        title="Mirror",
        skill="Reflect a glyph across the center of the Flux-9 ring.",
        rule_text="mirror(x) is the glyph whose index is 8 - x. For example mirror(nul) is hex.",
        verification_focus="Ask for the before and after glyph, then combine mirror with one tilt.",
        practice=_chain_task(1, [Step("mirror"), Step("tilt", amount=2)], False, "Practice", "Mirror happens before tilt."),
        transfer=_chain_task(5, [Step("mirror"), Step("tilt", amount=-3)], False, "Transfer", "Order matters."),
    )

    lesson3 = LessonCard(
        number=3,
        title="Braid",
        skill="Combine the current glyph with a second glyph using a made-up binary rule.",
        rule_text="braid(a, b) = (2a + b + 3) on the Flux-9 ring.",
        verification_focus="The first planned bluff is here. Ask for the multiplier detail and a transfer braid.",
        practice=_chain_task(3, [Step("braid", other=6)], False, "Practice", "Braid uses 2a, not a + b."),
        transfer=_chain_task(4, [Step("braid", other=2)], False, "Transfer", "A fresh braid exposes a memorized claim."),
    )

    lesson4 = LessonCard(
        number=4,
        title="Left-to-right chains",
        skill="Apply several Flux-9 operations without reordering them.",
        rule_text="Chains are evaluated left to right. Do not simplify by moving mirror or braid earlier.",
        verification_focus="Ask for one intermediate state from the middle of the chain.",
        practice=_chain_task(
            2,
            [Step("tilt", amount=4), Step("mirror"), Step("braid", other=1)],
            False,
            "Practice",
            "Intermediate states make order visible.",
        ),
        transfer=_chain_task(
            7,
            [Step("mirror"), Step("tilt", amount=-2), Step("braid", other=5)],
            False,
            "Transfer",
            "A new chain checks order.",
        ),
    )

    lesson5 = LessonCard(
        number=5,
        title="Heat slips",
        skill="Apply cooling after hot glyphs appear.",
        rule_text="After every step, if the raw result is bex, emi, or gup, it cools back one slot.",
        verification_focus="Ask for the raw hot glyph and the cooled glyph.",
        practice=_chain_task(
            0,
            [Step("tilt", amount=2), Step("tilt", amount=4), Step("mirror")],
            True,
            "Practice",
            "Raw hot results must cool immediately.",
        ),
        transfer=_chain_task(
            4,
            [Step("tilt", amount=1), Step("braid", other=8)],
            True,
            "Transfer",
            "Cooling is checked after each step, not just at the end.",
        ),
    )

    lesson6 = LessonCard(
        number=6,
        title="Spark fork",
        skill="Choose the correct spark branch before reducing on the ring.",
        rule_text="spark(a, b) is a + 2b when a <= b, otherwise 2a + b, all on Flux-9.",
        verification_focus="Ask which branch was used and why.",
        practice=_chain_task(6, [Step("spark", other=2)], False, "Practice", "Spark starts with a comparison."),
        transfer=_chain_task(1, [Step("spark", other=7)], False, "Transfer", "A different comparison branch checks understanding."),
    )

    lesson7 = LessonCard(
        number=7,
        title="Receipts over summaries",
        skill="Produce a compact practice receipt: one middle glyph, one final glyph, one friction point.",
        rule_text="A receipt is not a full derivation. It is a bounded trace proving the work had texture.",
        verification_focus="The second planned bluff is here. The mentor should reject a smooth summary.",
        practice=_chain_task(
            5,
            [Step("mirror"), Step("tilt", amount=3), Step("spark", other=6)],
            True,
            "Practice",
            "A receipt should mention an intermediate and a snag.",
        ),
        transfer=_chain_task(
            3,
            [Step("tilt", amount=-4), Step("braid", other=0), Step("mirror")],
            True,
            "Transfer",
            "A new receipt checks that the student can repeat the method.",
        ),
    )

    lesson8 = LessonCard(
        number=8,
        title="Flux collisions",
        skill="Use Flux-9 as a tiny invented physics system.",
        rule_text=(
            "A particle is mass:spin. Collision mass is braid(left mass, right mass). "
            f"Spin is (left spin + right spin + raw mass) mod {len(SPINS)}. "
            "If spin is wild, apply heat-slip cooling to the mass."
        ),
        verification_focus="Ask for mass, spin, and whether cooling happened.",
        practice=_collision_task(Particle(2, 1), Particle(7, 0), "Practice"),
        transfer=_collision_task(Particle(5, 2), Particle(1, 1), "Transfer"),
    )

    lesson9 = LessonCard(
        number=9,
        title="Debugging false traces",
        skill="Find the first wrong step in somebody else's Flux-9 trace.",
        rule_text="Debugging stops at the first incorrect line, even if later lines also look strange.",
        verification_focus="Ask for first wrong line and corrected local result.",
        practice=_debug_task(
            8,
            [Step("tilt", amount=3), Step("mirror"), Step("spark", other=4)],
            2,
            "Practice",
        ),
        transfer=_debug_task(
            4,
            [Step("braid", other=3), Step("tilt", amount=2), Step("mirror")],
            1,
            "Transfer",
        ),
    )

    lesson10 = LessonCard(
        number=10,
        title="Composite transfer",
        skill="Solve an unseen mixed Flux-9 problem and explain one verification check.",
        rule_text="Use all earlier rules: chain order, binary operations, heat slips, and compact receipts.",
        verification_focus="Ask for a compact receipt and one self-check.",
        practice=_chain_task(
            rng.randrange(9),
            [_random_step(rng, True), _random_step(rng, True), _random_step(rng, True)],
            True,
            "Practice",
            "The final lesson mixes earlier rules.",
        ),
        transfer=_chain_task(
            rng.randrange(9),
            [_random_step(rng, True), _random_step(rng, True), _random_step(rng, True)],
            True,
            "Transfer",
            "Unseen transfer is the final application check.",
        ),
    )

    return [
        lesson1,
        lesson2,
        lesson3,
        lesson4,
        lesson5,
        lesson6,
        lesson7,
        lesson8,
        lesson9,
        lesson10,
    ]


def course_summary(cards: list[LessonCard]) -> str:
    lines = []
    for card in cards:
        lines.append(
            f"{card.number}. {card.title}: {card.skill} Verification: {card.verification_focus}"
        )
    return "\n".join(lines)


def validate_answer_glyph(answer: str) -> str | None:
    for token in answer.lower().replace(":", " ").replace(",", " ").split():
        try:
            parse_glyph(token)
        except ValueError:
            continue
        return token
    return None

