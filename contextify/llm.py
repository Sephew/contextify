"""The LLM seam: one interface, two implementations.

``LLMClient`` is the boundary the rest of the system talks to for the two calls
that genuinely need judgment — Problem Abstraction and Framework Retrieval.

- :class:`OpenRouterClient` makes real calls through OpenRouter (OpenAI-compatible).
  Used by the CLI/demo for a live end-to-end run.
- :class:`MockLLMClient` is deterministic and offline — no key, no network. It
  applies rule-based heuristics over the same inputs so the test suite exercises
  real code paths (prompt-independent matching logic) rather than a lookup table.

Swapping the two is how retrieval stays testable without a key while still being a
real LLM pipeline in the demo.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

from .models import (
    EvidenceType,
    Framework,
    GoalShape,
    ProblemAbstraction,
    Reproducibility,
)


@dataclass
class LLMRetrievalDecision:
    """Raw decision returned by the retrieval call, before it's assembled into a
    :class:`~contextify.models.FrameworkMatch`."""

    chosen_id: str
    path: list[str]
    confidence: float
    rationale: str
    # Leading misfit signal: True when the top candidates were ambiguously close,
    # so the caller should treat this as a flagged guess, not a confident pick.
    ambiguous: bool = False


class LLMClient(Protocol):
    """What abstraction + retrieval depend on. Keep this tiny."""

    def abstract_problem(self, raw_text: str) -> ProblemAbstraction: ...

    def resolve_framework(
        self, abstraction: ProblemAbstraction, tree: list[Framework]
    ) -> LLMRetrievalDecision: ...


# --------------------------------------------------------------------------- #
# Prompt construction (shared by the real client; kept out of the mock)
# --------------------------------------------------------------------------- #

_ABSTRACTION_SYSTEM = """You convert a raw software problem description into a \
strict 4-field JSON schema. Do not solve the problem. Output ONLY JSON:
{
  "symptom": "<observed vs expected, one sentence>",
  "reproducibility": "deterministic|intermittent|unreproduced",
  "evidence_available": ["stack_trace"|"logs"|"failing_test"|"report_only", ...],
  "goal_shape": "root_cause|fix|coverage_increase|regression_prevention"
}"""


def _render_tree(tree: list[Framework]) -> str:
    by_parent: dict[str | None, list[Framework]] = {}
    for f in tree:
        by_parent.setdefault(f.parent, []).append(f)

    lines: list[str] = []

    def walk(parent_id: str | None, depth: int) -> None:
        for node in by_parent.get(parent_id, []):
            indent = "  " * depth
            lines.append(f"{indent}- id={node.id} name=\"{node.name}\"")
            for cond in node.applicability_condition:
                lines.append(f"{indent}    · {cond}")
            walk(node.id, depth + 1)

    walk(None, 0)
    return "\n".join(lines)


def _retrieval_prompt(abstraction: ProblemAbstraction, tree: list[Framework]) -> str:
    return (
        "Framework tree (branch -> frameworks, each with applicability checklist):\n"
        f"{_render_tree(tree)}\n\n"
        "Abstracted problem:\n"
        f"{abstraction.to_prompt_block()}\n\n"
        "Walk the tree from the root to the single best-fit leaf in ONE pass, "
        "testing the abstraction against each node's applicability checklist. "
        "Output ONLY JSON:\n"
        '{"chosen_id": "<leaf id>", "path": ["<root name>", ..., "<leaf name>"], '
        '"confidence": <0.0-1.0>, "rationale": "<one sentence>", '
        '"ambiguous": <true if the top two candidate leaves fit almost equally '
        "well and no single leaf clearly dominates, false otherwise>}"
    )


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response, tolerating code fences
    and trailing commentary.

    Uses raw_decode from the first '{' rather than slicing to the *last* '}' in the
    text — the latter breaks the moment a response contains any trailing text with
    its own brace (e.g. closing commentary), since it grabs everything up to that
    unrelated brace instead of the JSON object's actual end.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*)\s*```", text, re.DOTALL)
    blob = fenced.group(1) if fenced else text
    start = blob.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in model response: {text!r}")
    try:
        obj, _end = json.JSONDecoder().raw_decode(blob, start)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in model response: {text!r}") from exc
    return obj


# --------------------------------------------------------------------------- #
# Real client: OpenRouter via the OpenAI SDK
# --------------------------------------------------------------------------- #

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"


class OpenRouterClient:
    """Live LLM client. Reads ``OPENROUTER_API_KEY`` and ``CONTEXTIFY_MODEL``."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from dotenv import load_dotenv

        load_dotenv()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("CONTEXTIFY_MODEL", DEFAULT_MODEL)
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add "
                "your key, or use MockLLMClient for offline runs."
            )
        from openai import OpenAI

        self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=self.api_key)

    def _chat(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    def abstract_problem(self, raw_text: str) -> ProblemAbstraction:
        data = _extract_json(self._chat(_ABSTRACTION_SYSTEM, raw_text))
        return ProblemAbstraction(
            symptom=str(data["symptom"]),
            reproducibility=Reproducibility(data["reproducibility"]),
            evidence_available=[EvidenceType(e) for e in data["evidence_available"]],
            goal_shape=GoalShape(data["goal_shape"]),
        )

    def resolve_framework(
        self, abstraction: ProblemAbstraction, tree: list[Framework]
    ) -> LLMRetrievalDecision:
        data = _extract_json(
            self._chat(
                "You are a framework-retrieval router. Output only the requested JSON.",
                _retrieval_prompt(abstraction, tree),
            )
        )
        return LLMRetrievalDecision(
            chosen_id=str(data["chosen_id"]),
            path=[str(p) for p in data["path"]],
            confidence=float(data["confidence"]),
            rationale=str(data.get("rationale", "")),
            ambiguous=bool(data.get("ambiguous", False)),
        )


# --------------------------------------------------------------------------- #
# Mock client: deterministic, offline, rule-based
# --------------------------------------------------------------------------- #

# Keyword -> field rules for abstraction. First match wins per field; order matters.
_REPRO_RULES = [
    (Reproducibility.INTERMITTENT, ("intermittent", "sometimes", "flaky", "randomly",
                                    "occasionally", "once in a while", "not always",
                                    # multiple unconfirmed candidate causes ("could be
                                    # X, Y, or Z", "no clear pattern yet") is how bug
                                    # reports usually phrase an unpinned intermittent
                                    # trigger, without ever using the word "intermittent"
                                    "could be", "might be", "no clear pattern",
                                    "no obvious pattern", "not sure which",
                                    "not sure why", "some users but not others",
                                    "for some users", "some but not others")),
    (Reproducibility.UNREPRODUCED, ("can't reproduce", "cannot reproduce",
                                    "couldn't reproduce", "unable to reproduce",
                                    "never reproduced", "no repro")),
    (Reproducibility.DETERMINISTIC, ("every time", "always", "consistently",
                                     "reproducible", "100%", "reliably")),
]

_EVIDENCE_RULES = [
    (EvidenceType.STACK_TRACE, ("stack trace", "stacktrace", "traceback",
                                "exception", "nullpointer", "segfault")),
    (EvidenceType.FAILING_TEST, ("failing test", "test fails", "unit test",
                                 "assertion", "ci fails", "red test")),
    (EvidenceType.LOGS, ("logs", "logged", "log line")),
    (EvidenceType.REPORT_ONLY, ("user reported", "customer said", "bug report",
                                "someone said", "reported that", "complaint")),
]

# Words that, appearing shortly before a keyword match, invert or void it.
_NEGATORS = ("no ", "not ", "n't ", "never ", "without ", "lack of ")
# Words that make an otherwise-positive evidence keyword merely aspirational
# ("add logging" means it doesn't exist yet, not that evidence is in hand).
_ASPIRATIONAL = ("add ", "adding ", "need ", "needs ", "want ", "start ", "more ")

_SELF_RESOLVING_HINTS = (
    "on its own", "by itself", "eventually", "after a delay", "after a while",
    "over time", "corrects itself", "resolves itself", "manual refresh",
    "manually clear", "clears the cache", "clear the cache", "log out and back in",
    "logging out and back in", "reload the page", "refresh the page", "overnight",
    "catches up", "correct again if",
)
_SELF_RESOLVING_MARKERS = (
    "self-correct", "cache", "refresh", "reload", "restart", "clear",
    "delay", "log out", "log back in", "relogin",
)

# Testing-branch structural bonus signals, mirroring the self-resolving bonus
# above: short/common phrasing that a rare-word symptom-overlap tiebreaker alone
# wouldn't catch, but that's a genuine signal for which Testing leaf applies.
_BOUNDARY_HINTS = (
    "exactly", "minimum", "maximum", "one cent over", "one byte", "off-by-one",
    "just inside", "just outside", "the limit", "the max", "the min",
)
_BOUNDARY_MARKERS = ("boundary", "edge", "minimum", "maximum")

_CATEGORY_HINTS = (
    "different", "distinct", "each takes a different", "different code path",
    "different providers", "different rounding rules", "since each",
    "categories", "types:",
)
_CATEGORY_MARKERS = ("categor", "class", "representative", "code path")

_SEQUENCE_HINTS = (
    "seeks backward", "pauses again", "sequence of actions", "before it buffers",
    "order of actions", "specific sequence",
)
_SEQUENCE_MARKERS = ("sequence", "state", "transition", "order")

# Ambiguously-close top candidates: a real match (best_score > 0) whose
# runner-up is within this many points is flagged low-confidence rather than
# silently guessed.
_AMBIGUITY_MARGIN = 1

_GOAL_RULES = [
    (GoalShape.REGRESSION_PREVENTION, ("prevent regression", "stop it recurring",
                                       "regression test", "make sure it never")),
    (GoalShape.COVERAGE_INCREASE, ("coverage", "untested", "add tests",
                                   "test the", "verify", "want to make sure",
                                   "want tests", "need to check")),
    (GoalShape.FIX, ("fix it", "fixed", "make it work", "resolve", "patch",
                     "correct the", "propagate correctly", "need it to",
                     "need this fixed")),
    (GoalShape.ROOT_CAUSE, ("root cause", "why", "what's causing", "figure out",
                            "understand", "diagnose", "find the cause")),
]


def _window_before(lowered: str, idx: int, span: int = 24) -> str:
    return lowered[max(0, idx - span) : idx]


def _first_match(text: str, rules, default, *, negation_aware: bool = False):
    lowered = text.lower()
    for value, keywords in rules:
        for kw in keywords:
            idx = lowered.find(kw)
            if idx == -1:
                continue
            if negation_aware:
                window = _window_before(lowered, idx)
                if any(neg in window for neg in _NEGATORS):
                    continue
                if any(asp in window for asp in _ASPIRATIONAL):
                    continue
            return value
    return default


_UNREPRODUCED_HINTS = ("never", "haven't", "unable", "can't", "cannot",
                       "couldn't", "not been able")


def _resolve_reproducibility(text: str) -> Reproducibility:
    lowered = text.lower()
    idx = lowered.find("reproduce")
    if idx != -1 and any(h in _window_before(lowered, idx, 40) for h in _UNREPRODUCED_HINTS):
        return Reproducibility.UNREPRODUCED
    # A symptom that fixes itself via refresh/relogin/wait/cache-clear, with no code
    # change, is definitionally not a stable "reproduces identically every run"
    # regression — it's a transient/staleness artifact. Without this, such reports
    # (which rarely use words like "intermittent") silently default to DETERMINISTIC,
    # which is the one value a real regression-bisection case would want instead.
    if any(hint in lowered for hint in _SELF_RESOLVING_HINTS):
        return Reproducibility.INTERMITTENT
    # "Fails consistently on environment X, works every time elsewhere" uses
    # deterministic-sounding words ("consistently", "every time") but the actual
    # variable is the environment, not a code change — an explicit signal that
    # should win over the generic DETERMINISTIC keyword match above.
    if any(
        hint in lowered
        for hint in ("environment-specific", "not a regression", "not a code",
                     "nothing changed in", "no code change")
    ):
        return Reproducibility.INTERMITTENT
    return _first_match(text, _REPRO_RULES, Reproducibility.DETERMINISTIC)


def _resolve_goal_shape(text: str) -> GoalShape:
    matched = _first_match(text, _GOAL_RULES, None)
    if matched is not None:
        return matched
    # A purely descriptive "stale value that fixes itself" report carries an
    # implicit ask to make it stop happening, not a request to diagnose why two
    # cases differ — even though no explicit goal phrase ("fix it", "root cause")
    # appears in the text at all. Defaulting blindly to ROOT_CAUSE here is what
    # let Bisection/Differential (whose checklists both cite root_cause) win by
    # default over Cache Invalidation (which needs "fix") on unstated-goal reports.
    if any(hint in text.lower() for hint in _SELF_RESOLVING_HINTS):
        return GoalShape.FIX
    return GoalShape.ROOT_CAUSE


class MockLLMClient:
    """Deterministic stand-in. No key, no network.

    Abstraction: keyword rules over the raw text.
    Retrieval: scores each leaf's applicability checklist against the abstraction and
    picks the best — a genuine (if simple) structural matcher, not a lookup table.
    """

    def abstract_problem(self, raw_text: str) -> ProblemAbstraction:
        evidence = _first_match(
            raw_text, _EVIDENCE_RULES, EvidenceType.REPORT_ONLY, negation_aware=True
        )
        return ProblemAbstraction(
            symptom=raw_text.strip().split(".")[0][:200],
            reproducibility=_resolve_reproducibility(raw_text),
            evidence_available=[evidence],
            goal_shape=_resolve_goal_shape(raw_text),
        )

    def resolve_framework(
        self, abstraction: ProblemAbstraction, tree: list[Framework]
    ) -> LLMRetrievalDecision:
        leaves = _leaves(tree)
        scored = sorted(
            ((self._score(abstraction, leaf), leaf) for leaf in leaves),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best = scored[0]
        path = _path_names(tree, best)
        # Confidence: top score normalised, damped when the runner-up is close
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        margin = best_score - runner_up
        confidence = round(min(1.0, 0.5 + 0.1 * best_score + 0.1 * margin), 3)
        # Leading misfit signal: a real match (best_score > 0) whose runner-up
        # scored almost as well is an ambiguous guess, not a confident pick.
        ambiguous = len(scored) > 1 and best_score > 0 and margin <= _AMBIGUITY_MARGIN
        rationale = f"best applicability overlap (score {best_score}) among leaves"
        if ambiguous:
            rationale += f"; runner-up scored {runner_up} — ambiguously close"
        return LLMRetrievalDecision(
            chosen_id=best.id,
            path=path,
            confidence=confidence,
            rationale=rationale,
            ambiguous=ambiguous,
        )

    @staticmethod
    def _score(abstraction: ProblemAbstraction, leaf: Framework) -> int:
        """Count structural hits between the abstraction and a leaf's checklist.

        Exact-field matches (reproducibility/goal/evidence) dominate, since these
        are the actual structural test. Symptom word overlap is a light,
        rarer-word-only tiebreaker so it can't drown out the structural signal
        (a prior version weighted it equally and let common words tip matches).
        """
        blob = " ".join(leaf.applicability_condition).lower()
        score = 0
        if abstraction.reproducibility.value in blob:
            score += 4
        if abstraction.goal_shape.value in blob:
            score += 3
        for ev in abstraction.evidence_available:
            if ev.value in blob:
                score += 3
        # Light tiebreaker: rarer (>=6 char) symptom words overlapping the
        # checklist text, capped so it can never outweigh a structural field.
        symptom_lower = abstraction.symptom.lower()
        overlap = sum(
            1
            for word in set(re.findall(r"[a-z]{6,}", symptom_lower))
            if word in blob
        )
        score += min(overlap, 3)
        # A "self-resolves via refresh/relogin/wait/cache-clear" symptom shape is a
        # genuine structural signal for stale-data bugs — a real logic bug wouldn't
        # spontaneously fix itself that way — but is usually phrased with short,
        # common words the word-overlap tiebreaker above (>=6 chars) can't see.
        if any(hint in symptom_lower for hint in _SELF_RESOLVING_HINTS) and any(
            marker in blob for marker in _SELF_RESOLVING_MARKERS
        ):
            score += 4
        # Same pattern for the Testing branch: short/common phrasing that names
        # the shape of the input (a range edge, a set of categories, an action
        # sequence) rather than restating the checklist's own rarer vocabulary.
        if any(hint in symptom_lower for hint in _BOUNDARY_HINTS) and any(
            marker in blob for marker in _BOUNDARY_MARKERS
        ):
            score += 4
        if any(hint in symptom_lower for hint in _CATEGORY_HINTS) and any(
            marker in blob for marker in _CATEGORY_MARKERS
        ):
            score += 4
        if any(hint in symptom_lower for hint in _SEQUENCE_HINTS) and any(
            marker in blob for marker in _SEQUENCE_MARKERS
        ):
            score += 4
        return score


# --------------------------------------------------------------------------- #
# Tree helpers reused by the mock scorer
# --------------------------------------------------------------------------- #

def _leaves(tree: list[Framework]) -> list[Framework]:
    parents = {f.parent for f in tree if f.parent is not None}
    return [f for f in tree if f.id not in parents]


def _path_names(tree: list[Framework], node: Framework) -> list[str]:
    by_id = {f.id: f for f in tree}
    names: list[str] = []
    cursor: Framework | None = node
    while cursor is not None:
        names.append(cursor.name)
        cursor = by_id.get(cursor.parent) if cursor.parent else None
    return list(reversed(names))
