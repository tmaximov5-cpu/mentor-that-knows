from __future__ import annotations

import argparse

from .course import build_course
from .orchestrator import run_ollama, run_scripted, write_submission


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mentor-that-knows",
        description="Run a mentor/student simulation for the AI School assignment.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run the full ten-lesson course")
    run_parser.add_argument("--backend", choices=["scripted", "ollama"], default="scripted")
    run_parser.add_argument("--model", default="gemma3n:e4b")
    run_parser.add_argument("--ollama-url", default="http://localhost:11434")
    run_parser.add_argument("--seed", type=int, default=7)
    run_parser.add_argument("--out", default="docs/submission_sample.md")

    course_parser = subparsers.add_parser("show-course", help="print the generated course")
    course_parser.add_argument("--seed", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "show-course":
        for card in build_course(args.seed):
            print(f"{card.number}. {card.title}")
            print(f"   Rule: {card.rule_text}")
            print(f"   Practice: {card.practice.prompt} -> {card.practice.answer}")
            print(f"   Transfer: {card.transfer.prompt} -> {card.transfer.answer}")
        return 0

    if args.backend == "scripted":
        result = run_scripted(seed=args.seed)
    else:
        result = run_ollama(seed=args.seed, model=args.model, base_url=args.ollama_url)

    path = write_submission(result, args.out)
    print(f"Wrote {path}")
    return 0

