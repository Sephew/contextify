"""Tree distance between two Framework nodes (PRD user story 12): quantifies how
severe a misfit was instead of just flagging that one happened.

Frameworks form a forest — one root per Branch (Debugging, Testing) — not a
single tree, so distance is computed against a virtual super-root that every
Branch root implicitly shares (``None``, the same sentinel Framework.parent
already uses for "no parent"). That makes cross-branch distance well-defined
too, which matters here: the PRD picked Debugging/Testing as a pair
specifically so tree distance could demonstrate cross-branch misfit severity.
"""

from __future__ import annotations

from ..models import Framework


def _path_to_virtual_root(by_id: dict[str, Framework], framework_id: str) -> list[str | None]:
    path: list[str | None] = []
    cursor: str | None = framework_id
    while cursor is not None:
        path.append(cursor)
        cursor = by_id[cursor].parent
    path.append(None)  # virtual super-root shared by every Branch root
    return path


def tree_distance(tree: list[Framework], id_a: str, id_b: str) -> int:
    """Number of edges on the tree path between two Framework nodes (0 if equal)."""
    if id_a == id_b:
        return 0
    by_id = {f.id: f for f in tree}
    path_a = _path_to_virtual_root(by_id, id_a)
    path_b = _path_to_virtual_root(by_id, id_b)
    depth_b = {node: depth for depth, node in enumerate(path_b)}
    for depth_a, node in enumerate(path_a):
        if node in depth_b:
            return depth_a + depth_b[node]
    raise ValueError(f"{id_a!r} and {id_b!r} share no common ancestor in this tree")
