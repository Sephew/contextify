"""In-memory log of retrieve_framework() outcomes, keyed by match_id.

reflect() needs to resolve a match_id back to which Framework was matched and
which problem it was for. That's retrieval *history*, not Framework Store
state (the store holds the tree, not the log of who asked it what), so it
lives here rather than growing FrameworkStore's contract. Not global by
design: callers thread the same MatchHistory across a session the same way
they already thread the same FrameworkStore, so tests get isolation for free
without needing a reset() method.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchRecord:
    match_id: str
    problem_id: str
    framework_id: str


class MatchHistory:
    def __init__(self) -> None:
        self._records: dict[str, MatchRecord] = {}
        self._by_problem: dict[str, list[str]] = {}

    def record(self, match_id: str, problem_id: str, framework_id: str) -> None:
        self._records[match_id] = MatchRecord(match_id, problem_id, framework_id)
        self._by_problem.setdefault(problem_id, []).append(match_id)

    def get(self, match_id: str) -> MatchRecord | None:
        return self._records.get(match_id)

    def framework_ids_tried(self, problem_id: str) -> list[str]:
        """Distinct framework ids tried for this problem, in first-tried order."""
        seen: list[str] = []
        for match_id in self._by_problem.get(problem_id, []):
            framework_id = self._records[match_id].framework_id
            if framework_id not in seen:
                seen.append(framework_id)
        return seen
