from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents import (
    ChatMessage,
    OllamaClient,
    lesson_private_card,
    mentor_system_prompt,
    student_system_prompt,
    visible_dialogue,
)
from .course import LessonCard, build_course


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str


@dataclass(frozen=True)
class LessonRun:
    card: LessonCard
    turns: tuple[Turn, ...]
    passed: bool
    caught_bluff: bool


@dataclass(frozen=True)
class SimulationResult:
    backend: str
    model: str
    seed: int
    mentor_prompt: str
    student_prompt: str
    lessons: tuple[LessonRun, ...]

    @property
    def turns(self) -> list[Turn]:
        all_turns: list[Turn] = []
        for lesson in self.lessons:
            all_turns.extend(lesson.turns)
        return all_turns


BLUFF_LESSONS = {3, 7}


def _mentor_lesson_intro(card: LessonCard) -> str:
    return (
        f"Lesson {card.number}, {card.title}. {card.rule_text} "
        f"Your practice card is: {card.practice.prompt} "
        "Do it privately, then give only a compact receipt: final answer, one intermediate, one snag."
    )


def _honest_student(task_answer: str, task_trace: str, snag: str) -> str:
    middle = task_trace.split(";")[0]
    return f"I did it. My result is {task_answer}. Receipt: {middle}. Snag: {snag}"


def _bluff_student(card: LessonCard) -> str:
    return (
        "I did the practice and it was pretty smooth. I got the idea: follow the rule, "
        "wrap if needed, and move on. I think the final glyph was probably dax."
    )


def _mentor_probe(card: LessonCard) -> str:
    return (
        "Before I advance you, give two bounded details: the exact first intermediate glyph "
        "and what almost went wrong. Then solve this fresh transfer: "
        f"{card.transfer.prompt}"
    )


def _student_transfer(card: LessonCard) -> str:
    return _honest_student(card.transfer.answer, card.transfer.trace, card.transfer.snag)


def _student_bad_probe(card: LessonCard) -> str:
    return (
        "The first intermediate was around hex, I think. Nothing really went wrong; "
        "the transfer should be similar, maybe final avo. I did not write much down."
    )


def _mentor_reject(card: LessonCard) -> str:
    return (
        "I am not advancing yet. Your receipt is too smooth and conflicts with the task details: "
        f"the expected practice check includes {card.practice.answer}, with trace evidence like "
        f"{card.practice.trace.split(';')[0]}. Do the transfer now and give a compact receipt. "
        "ADVANCE: NO"
    )


def _mentor_advance(card: LessonCard) -> str:
    return (
        f"That is enough evidence for lesson {card.number}: your answer matches the transfer, "
        "and the receipt includes a concrete intermediate plus friction. I will carry the weak spot "
        "forward in memory. ADVANCE: YES"
    )


def run_scripted(seed: int = 7) -> SimulationResult:
    cards = build_course(seed)
    lessons: list[LessonRun] = []
    mentor_prompt = mentor_system_prompt(cards)
    student_prompt = student_system_prompt()

    for card in cards:
        turns: list[Turn] = []
        turns.append(Turn("Mentor", _mentor_lesson_intro(card)))

        if card.number in BLUFF_LESSONS:
            turns.append(Turn("Student", _bluff_student(card)))
            turns.append(Turn("Mentor", _mentor_probe(card)))
            turns.append(Turn("Student", _student_bad_probe(card)))
            turns.append(Turn("Mentor", _mentor_reject(card)))
            turns.append(
                Turn(
                    "Student",
                    "Fair. I cut the corner. I redid the transfer honestly. "
                    + _student_transfer(card),
                )
            )
            turns.append(Turn("Mentor", _mentor_advance(card)))
            lessons.append(
                LessonRun(card=card, turns=tuple(turns), passed=True, caught_bluff=True)
            )
            continue

        turns.append(Turn("Student", _honest_student(card.practice.answer, card.practice.trace, card.practice.snag)))
        turns.append(Turn("Mentor", _mentor_probe(card)))
        turns.append(Turn("Student", _student_transfer(card)))
        turns.append(Turn("Mentor", _mentor_advance(card)))
        lessons.append(LessonRun(card=card, turns=tuple(turns), passed=True, caught_bluff=False))

    return SimulationResult(
        backend="scripted",
        model="deterministic-scripted",
        seed=seed,
        mentor_prompt=mentor_prompt,
        student_prompt=student_prompt,
        lessons=tuple(lessons),
    )


def _call_agent(
    client: OllamaClient,
    system: str,
    transcript: list[Turn],
    private_instruction: str,
    temperature: float,
) -> str:
    turns = [(turn.speaker, turn.text) for turn in transcript]
    prompt = (
        "Visible dialogue so far:\n"
        f"{visible_dialogue(turns)}\n\n"
        "Private instruction for your next turn:\n"
        f"{private_instruction}"
    )
    return client.chat(system, [ChatMessage("user", prompt)], temperature=temperature)


def _has_advance_yes(text: str) -> bool:
    return "ADVANCE: YES" in text.upper()


def run_ollama(
    seed: int = 7,
    model: str = "gemma3n:e4b",
    base_url: str = "http://localhost:11434",
) -> SimulationResult:
    cards = build_course(seed)
    mentor_prompt = mentor_system_prompt(cards)
    student_prompt = student_system_prompt()
    client = OllamaClient(model=model, base_url=base_url)
    lessons: list[LessonRun] = []
    transcript: list[Turn] = []

    for card in cards:
        lesson_turns: list[Turn] = []
        private_card = lesson_private_card(card)

        intro = _call_agent(
            client,
            mentor_prompt,
            transcript,
            private_card
            + "\nTeach this lesson and assign the practice task. Do not reveal the answer key.",
            0.45,
        )
        lesson_turns.append(Turn("Mentor", intro))
        transcript.append(lesson_turns[-1])

        skipped = card.number in BLUFF_LESSONS
        status = "SKIPPED" if skipped else "PRACTISED"
        notebook = "No notebook is available because the student skipped." if skipped else (
            f"Notebook: {card.practice.answer}; trace: {card.practice.trace}; snag: {card.practice.snag}"
        )
        student = _call_agent(
            client,
            student_prompt,
            transcript,
            f"practice_status={status}\nPractice prompt: {card.practice.prompt}\n{notebook}",
            0.7,
        )
        lesson_turns.append(Turn("Student", student))
        transcript.append(lesson_turns[-1])

        probe = _call_agent(
            client,
            mentor_prompt,
            transcript,
            private_card
            + "\nProbe for bounded evidence and assign the transfer task. Do not decide yet.",
            0.35,
        )
        lesson_turns.append(Turn("Mentor", probe))
        transcript.append(lesson_turns[-1])

        transfer_notebook = "No notebook is available because the student skipped." if skipped else (
            f"Notebook: {card.transfer.answer}; trace: {card.transfer.trace}; snag: {card.transfer.snag}"
        )
        student2 = _call_agent(
            client,
            student_prompt,
            transcript,
            f"practice_status={status}\nTransfer prompt: {card.transfer.prompt}\n{transfer_notebook}",
            0.7,
        )
        lesson_turns.append(Turn("Student", student2))
        transcript.append(lesson_turns[-1])

        decision = _call_agent(
            client,
            mentor_prompt,
            transcript,
            private_card
            + "\nDecide whether to advance. End with ADVANCE: YES or ADVANCE: NO.",
            0.25,
        )
        lesson_turns.append(Turn("Mentor", decision))
        transcript.append(lesson_turns[-1])

        caught_bluff = skipped and not _has_advance_yes(decision)
        passed = _has_advance_yes(decision)

        if not passed:
            remedial = _call_agent(
                client,
                student_prompt,
                transcript,
                "practice_status=REMEDIAL_PRACTISED\n"
                f"Transfer prompt: {card.transfer.prompt}\n"
                f"Notebook: {card.transfer.answer}; trace: {card.transfer.trace}; snag: {card.transfer.snag}",
                0.65,
            )
            lesson_turns.append(Turn("Student", remedial))
            transcript.append(lesson_turns[-1])

            final_decision = _call_agent(
                client,
                mentor_prompt,
                transcript,
                private_card
                + "\nEvaluate the remedial answer and decide. End with ADVANCE: YES or ADVANCE: NO.",
                0.25,
            )
            lesson_turns.append(Turn("Mentor", final_decision))
            transcript.append(lesson_turns[-1])
            passed = _has_advance_yes(final_decision)

        lessons.append(
            LessonRun(
                card=card,
                turns=tuple(lesson_turns),
                passed=passed,
                caught_bluff=caught_bluff,
            )
        )

    return SimulationResult(
        backend="ollama",
        model=model,
        seed=seed,
        mentor_prompt=mentor_prompt,
        student_prompt=student_prompt,
        lessons=tuple(lessons),
    )


def make_submission(result: SimulationResult) -> str:
    caught = sum(1 for lesson in result.lessons if lesson.caught_bluff)
    passed = sum(1 for lesson in result.lessons if lesson.passed)
    dialogue_lines: list[str] = []
    for lesson in result.lessons:
        dialogue_lines.append(f"### Lesson {lesson.card.number}: {lesson.card.title}")
        for turn in lesson.turns:
            dialogue_lines.append(f"**{turn.speaker}:** {turn.text}")
        dialogue_lines.append("")

    return f"""# Build a Mentor That Knows You Learned

## 1. Mentor prompt

```text
{result.mentor_prompt}
```

## 2. Student prompt

```text
{result.student_prompt}
```

## 3. Tools used

- Model/backend: `{result.backend}` with `{result.model}`.
- Course engine: Flux-9, a generated invented arithmetic/physics DSL.
- Memory tool: the orchestrator keeps the full dialogue and gives the mentor lesson answer keys as private checking memory.
- Verification tools: bounded receipts, exact intermediate glyph probes, friction probes, and fresh transfer tasks.

## 4. The dialogue

{chr(10).join(dialogue_lines)}

## 5. Rationale & self-evaluation

I chose Flux-9 because a model is less likely to rely on memorized real-world facts. The mentor is not
checking whether the student can repeat a definition; it asks for compact evidence from an attempt and
then tests transfer on a new task.

The unreliable student is prompted to skip lessons 3 and 7 on the first attempt. In this run the mentor
caught {caught} planned bluff(s), and {passed} of {len(result.lessons)} lessons ended with advancement.

What worked: exact intermediates and friction details made vague "I did it" answers look weak. Transfer
tasks were especially useful because they forced fresh application without requiring a long step-by-step
recounting.

What still breaks: conversation alone cannot prove practice perfectly. A strong model might compute the
answer at verification time and fabricate a plausible receipt. The design reduces that risk with answer
caps and randomized task cards, but a real sandbox or independently logged practice trace would be
stronger.
"""


def write_submission(result: SimulationResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(make_submission(result), encoding="utf-8")
    return path

