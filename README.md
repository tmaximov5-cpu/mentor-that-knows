# Mentor That Knows You Learned

This repository is a runnable solution scaffold for the "Build a Mentor That
Knows You Learned" assignment.

It creates two agents:

- a mentor who teaches a ten-lesson course in an invented DSL called Flux-9
- an unreliable student who sometimes claims to have practised when they did not

The core idea is to make "practice" harder to fake by combining:

- short answer caps
- generated practice cards
- specific trace/receipt probes
- fresh transfer tasks
- mentor memory of weak spots and previous bluffs

The live backend uses Ollama and defaults to `gemma3n:e4b`. A deterministic
scripted backend is included so the project can be smoke-tested and can generate
a complete sample submission without a local model.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python -m mentor_that_knows run --backend scripted --out docs/submission_sample.md
python -m unittest discover -s tests
```

To run with Gemma through Ollama:

```bash
ollama serve
ollama pull gemma3n:e4b
python -m mentor_that_knows run --backend ollama --model gemma3n:e4b --out docs/submission_ollama.md
```

## Why Flux-9?

The assignment asks for a mentor that verifies application rather than simple
recall. A familiar domain lets a language model lean on pretraining. Flux-9 is a
small invented arithmetic/physics DSL with generated exercises, so the student
has to work with rules introduced inside the course.

The mentor still cannot prove practice perfectly through conversation alone.
The design narrows the gap by asking for bounded evidence that is cheap for a
real practitioner and awkward for a bluff:

- one exact intermediate glyph
- one friction point from the attempt
- one transfer answer on a fresh problem

## Project layout

```text
src/mentor_that_knows/
  agents.py        Ollama client and system prompts
  cli.py           command-line interface
  course.py        ten-lesson Flux-9 course generator
  dsl.py           Flux-9 evaluator and trace formatter
  orchestrator.py  two-agent course loop and submission writer
tests/
  test_course.py
  test_dsl.py
```
