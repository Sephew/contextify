"""CLI demo: pipe a raw bug description through the retrieve seam and print it.

    python -m contextify "my report shows stale totals after saving"
    python -m contextify --mock "..."     # force the offline heuristic client

Picks the live OpenRouter client automatically when OPENROUTER_API_KEY is set,
otherwise falls back to the deterministic mock so the demo always runs.
"""

from __future__ import annotations

import argparse
import os
import sys

from .api import retrieve_framework
from .llm import MockLLMClient, OpenRouterClient
from .models import FrameworkMatch

_DEFAULT_EXAMPLE = (
    "After we upgraded the ORM library, the report page throws on every run. "
    "A failing unit test reproduces it and I want the root cause of the regression."
)


def _choose_client(force_mock: bool):
    """Return (client, label). Prefer OpenRouter; degrade gracefully to mock."""
    if force_mock:
        return MockLLMClient(), "mock (forced)"
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            return OpenRouterClient(), "openrouter (live)"
        except Exception as exc:  # missing dep, bad key, etc. — don't crash the demo
            print(f"[warn] OpenRouter unavailable ({exc}); using mock", file=sys.stderr)
    return MockLLMClient(), "mock (offline)"


def _render(match: FrameworkMatch, llm_label: str) -> str:
    a = match.abstraction
    evidence = ", ".join(e.value for e in a.evidence_available) or "none"
    return "\n".join(
        [
            "",
            "  Contextify — Framework Retrieval (Debugging branch)",
            f"  llm: {llm_label}",
            "  " + "-" * 60,
            "  Problem abstraction:",
            f"    symptom            : {a.symptom}",
            f"    reproducibility    : {a.reproducibility.value}",
            f"    evidence_available : {evidence}",
            f"    goal_shape         : {a.goal_shape.value}",
            "  " + "-" * 60,
            f"  Matched framework : {match.framework_name}",
            f"  Branch            : {match.branch.value}",
            f"  Tree path         : {' -> '.join(match.path)}",
            f"  Confidence        : {match.confidence}",
            f"  Rationale         : {match.rationale}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contextify",
        description="Retrieve the right debugging framework for a raw problem.",
    )
    parser.add_argument("problem", nargs="*", help="raw bug description")
    parser.add_argument(
        "--mock", action="store_true", help="force the offline mock LLM client"
    )
    args = parser.parse_args(argv)

    raw = " ".join(args.problem).strip() or _DEFAULT_EXAMPLE
    client, label = _choose_client(args.mock)
    try:
        match = retrieve_framework(raw, llm=client)
    except ValueError as exc:
        print(f"[error] retrieval failed ({label}): {exc}", file=sys.stderr)
        return 1
    print(_render(match, label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
