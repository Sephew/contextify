"""Read a public GitHub repository's files into a text block for the prompt.

Simplest thing that actually reads the files: no git clone, no disk. Hit
GitHub's public REST API for the recursive file tree, then pull a handful of
text files (README first, then the shallowest source files) over raw.github,
budgeted to a character cap so the digest stays promptable. The block is
appended to the problem context so the abstraction/retrieval LLM sees real code
instead of a bare URL.

Unauthenticated GitHub API is rate-limited to 60 req/hr per IP; set GITHUB_TOKEN
to raise that. Non-GitHub URLs (or private/missing repos) return None — the
caller just proceeds without repo context.
"""

from __future__ import annotations

import os
import re

import httpx

_GITHUB_RE = re.compile(r"github\.com[/:]([^/\s]+)/([^/\s#?]+)")

# Actual source code — what we most want the LLM to see.
_CODE_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php",
    ".c", ".h", ".hpp", ".cpp", ".cc", ".cs", ".kt", ".swift", ".scala",
    ".vue", ".svelte", ".sql", ".sh",
}
# Readable but lower priority: docs/config, read only after source.
_OTHER_TEXT_EXT = {
    ".md", ".txt", ".rst", ".json", ".toml", ".yaml", ".yml", ".cfg", ".ini",
    ".html", ".css",
}
_TEXT_EXT = _CODE_EXT | _OTHER_TEXT_EXT
# Boilerplate that adds no signal — never worth spending the budget on.
_NOISE = ("license", "changelog", "changes", "code_of_conduct", "contributing")
# Directories that hold scaffolding/docs, not the code answering the problem.
_NOISE_DIRS = (
    "docs/", "doc/", "example", "sample", "test", "spec/", ".github/",
    ".devcontainer/", "scripts/", "tools/", "benchmark", "vendor/",
    "third_party/", "node_modules/", "dist/", "build/",
)

_CHAR_BUDGET = 9000       # total digest size handed to the prompt
_PER_FILE_CAP = 3000      # per-file slice so one big file can't eat the budget
_MAX_FILES = 8            # cap file fetches to stay under the rate limit

# Cheap in-process cache: the demo calls /abstract then /retrieve back to back,
# and re-reading the same repo per keystroke would burn the rate limit fast.
_CACHE: dict[str, str | None] = {}


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "contextify"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _is_text(path: str) -> bool:
    _, _, ext = path.rpartition(".")
    return f".{ext.lower()}" in _TEXT_EXT if ext else False


async def repo_context_block(url: str) -> str | None:
    """Return a promptable digest of the repo at ``url``, or None if unreadable."""
    if url in _CACHE:
        return _CACHE[url]
    block = await _build(url)
    _CACHE[url] = block
    return block


async def _build(url: str) -> str | None:
    m = _GITHUB_RE.search(url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).removesuffix(".git")

    async with httpx.AsyncClient(
        timeout=10.0, headers=_headers(), follow_redirects=True
    ) as client:
        try:
            meta = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if meta.status_code != 200:
                return None
            branch = meta.json().get("default_branch", "main")

            tree_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"},
            )
            if tree_resp.status_code != 200:
                return None
            blobs = [
                n for n in tree_resp.json().get("tree", [])
                if n.get("type") == "blob"
            ]

            # File listing gives the LLM the project's shape cheaply.
            paths = [n["path"] for n in blobs]
            listing = "\n".join(f"  {p}" for p in paths[:150])
            if len(paths) > 150:
                listing += f"\n  … (+{len(paths) - 150} more)"

            # Pick files to actually read: README first, then real source code
            # (shallowest first — entry points tend to live near the root),
            # then docs/config. Skip tests and pure boilerplate.
            def priority(path: str) -> tuple[int, int]:
                lower = path.lower()
                base = os.path.basename(lower)
                _, _, ext = base.rpartition(".")
                ext = f".{ext}"
                noise_dir = any(d in lower for d in _NOISE_DIRS)
                if base.startswith("readme") and not noise_dir:
                    tier = 0
                elif ext in _CODE_EXT and not noise_dir:
                    tier = 1          # real source — what we most want
                elif ext in _CODE_EXT:
                    tier = 2          # code, but under docs/tests/examples
                else:
                    tier = 3          # docs/config
                return (tier, path.count("/"))

            candidates = sorted(
                (
                    n for n in blobs
                    if _is_text(n["path"]) and n.get("size", 0) < 60_000
                    and not os.path.basename(n["path"]).lower().startswith(_NOISE)
                ),
                key=lambda n: priority(n["path"]),
            )

            parts = [f"=== Repository: {owner}/{repo} (branch {branch}) ===",
                     "File tree:", listing]
            used = 0   # budget the file *contents* only; the listing is bounded above
            for node in candidates[:_MAX_FILES]:
                if used >= _CHAR_BUDGET:
                    break
                path = node["path"]
                raw = await client.get(
                    f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
                )
                if raw.status_code != 200:
                    continue
                text = raw.text[:_PER_FILE_CAP]
                if len(raw.text) > _PER_FILE_CAP:
                    text += "\n… (truncated)"
                parts.append(f"\n--- {path} ---\n{text}")
                used += len(text)
        except httpx.HTTPError:
            return None

    return "\n".join(parts)[: _CHAR_BUDGET + 6000]
