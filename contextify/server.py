"""Hosted API wrapper around the retrieve_framework/reflect seams.

v1 constraints, deliberate not accidental: single always-on instance, in-memory
state (Framework Store / MatchHistory / PathCache reset on restart, no
multi-replica support — see contextify/api.py's process-lifetime globals).
Auth is a single static API key checked against CONTEXTIFY_API_KEY.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

import re

from .api import _get_default_store, areflect, aretrieve_framework
from .framework_store import new_provisional_framework
from .llm import LLMClient, MockLLMClient, OpenRouterClient
from .models import Branch, Framework, FrameworkMatch, ReflectionResult
from .problem_abstraction import abstract as _abstract
from .repo_context import repo_context_block

load_dotenv()

app = FastAPI(title="Contextify Framework Retrieval API")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(key: str | None = Security(_api_key_header)) -> None:
    expected = os.getenv("CONTEXTIFY_API_KEY")
    if not expected:
        raise HTTPException(500, "CONTEXTIFY_API_KEY not configured on server")
    if key != expected:
        raise HTTPException(401, "invalid or missing X-API-Key")


def _choose_client() -> LLMClient:
    return OpenRouterClient() if os.getenv("OPENROUTER_API_KEY") else MockLLMClient()


class RetrieveRequest(BaseModel):
    raw_input: str
    problem_id: str | None = None
    repo_url: str | None = None


class ReflectRequest(BaseModel):
    match_id: str
    outcome: str


class AbstractRequest(BaseModel):
    raw_input: str
    repo_url: str | None = None


async def _enrich(raw_input: str, repo_url: str | None) -> str:
    """Append a digest of the repo's files to the problem context, if given.

    Reads the repo server-side (GitHub API) rather than passing the LLM a bare
    URL it can't open. Silently no-ops when repo_url is empty or unreadable
    (non-GitHub, private, missing, rate-limited).
    """
    if not repo_url:
        return raw_input
    block = await repo_context_block(repo_url)
    return f"{raw_input}\n\n{block}" if block else raw_input


class SolveRequest(BaseModel):
    raw_input: str
    framework_id: str


class NewFrameworkRequest(BaseModel):
    name: str
    branch: str
    parent: str
    applicability_condition: list[str] = []


def _match_to_dict(match: FrameworkMatch) -> dict:
    return {
        "match_id": match.match_id,
        "framework_id": match.framework.id,
        "framework_name": match.framework_name,
        "path": match.path,
        "confidence": match.confidence,
        "rationale": match.rationale,
        "low_confidence": match.low_confidence,
        "cache_hit": match.cache_hit,
        "drafted_framework_id": match.drafted_framework_id,
        "abstraction": {
            "symptom": match.abstraction.symptom,
            "reproducibility": match.abstraction.reproducibility.value,
            "evidence_available": [e.value for e in match.abstraction.evidence_available],
            "goal_shape": match.abstraction.goal_shape.value,
        },
    }


def _framework_to_dict(f: Framework) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "branch": f.branch.value,
        "parent": f.parent,
        "status": f.status.value,
        "confidence": f.confidence,
        "validated_successes": f.validated_successes,
        "applicability_condition": f.applicability_condition,
    }


def _reflection_to_dict(result: ReflectionResult) -> dict:
    return {
        "match_id": result.match_id,
        "outcome": result.outcome,
        "success": result.success,
        "store_changed": result.store_changed,
        "note": result.note,
        "confidence_before": result.confidence_before,
        "confidence_after": result.confidence_after,
        "misfit_detected": result.misfit_detected,
        "tree_distance": result.tree_distance,
        "promoted": result.promoted,
    }


@app.post("/retrieve", dependencies=[Depends(_require_api_key)])
async def retrieve(req: RetrieveRequest) -> dict:
    try:
        raw_input = await _enrich(req.raw_input, req.repo_url)
        match = await aretrieve_framework(
            raw_input, llm=_choose_client(), problem_id=req.problem_id, auto_draft=True
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _match_to_dict(match)


@app.post("/reflect", dependencies=[Depends(_require_api_key)])
async def reflect_endpoint(req: ReflectRequest) -> dict:
    try:
        result = await areflect(req.match_id, req.outcome)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _reflection_to_dict(result)


@app.post("/abstract", dependencies=[Depends(_require_api_key)])
async def abstract_endpoint(req: AbstractRequest) -> dict:
    """Runs only the Problem Abstraction stage (stage 1 of retrieve_framework).

    Exposed separately so the demo UI can show a real intermediate step while
    waiting on /retrieve, instead of a single opaque round trip. Costs a
    second LLM call when the UI then calls /retrieve right after — an
    accepted demo-only tradeoff, not how a real integration should call this.
    """
    try:
        result = _abstract(await _enrich(req.raw_input, req.repo_url), _choose_client())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "symptom": result.symptom,
        "reproducibility": result.reproducibility.value,
        "evidence_available": [e.value for e in result.evidence_available],
        "goal_shape": result.goal_shape.value,
    }


@app.post("/solve", dependencies=[Depends(_require_api_key)])
async def solve_endpoint(req: SolveRequest) -> dict:
    """Applies the matched framework to the problem and returns a worked plan.

    This is the "so what" step after /retrieve: retrieval tells you *how to
    think* about the problem; /solve actually thinks it through in that
    framework and returns concrete, tailored steps (markdown). One LLM call.
    """
    store = await _get_default_store()
    framework = await store.get(req.framework_id)
    if framework is None:
        raise HTTPException(400, f"unknown framework id {req.framework_id!r}")
    try:
        solution = _choose_client().solve_with_framework(req.raw_input, framework)
    except Exception as exc:  # keep the demo alive on a model/network hiccup
        raise HTTPException(502, f"solve failed: {exc}") from exc
    return {
        "framework_id": framework.id,
        "framework_name": framework.name,
        "solution": solution,
    }


@app.get("/frameworks", dependencies=[Depends(_require_api_key)])
async def list_frameworks() -> list[dict]:
    store = await _get_default_store()
    tree = await store.read_tree()
    return [_framework_to_dict(f) for f in tree]


@app.post("/frameworks", dependencies=[Depends(_require_api_key)])
async def add_framework(req: NewFrameworkRequest) -> dict:
    """Registers a new provisional Framework (PRD promotion gate) — the demo's
    "generate a new framework" flow. This does not use an LLM to author the
    Framework; it's the human-in-the-loop path already in
    contextify.framework_store.new_provisional_framework, just reachable over
    HTTP for the demo. The new node starts PROVISIONAL / under-weighted and
    only reaches trusted status via reflect()'s promotion gate.
    """
    try:
        branch = Branch(req.branch)
    except ValueError as exc:
        raise HTTPException(
            400, f"unknown branch {req.branch!r}; expected one of {[b.value for b in Branch]}"
        ) from exc

    store = await _get_default_store()
    parent = await store.get(req.parent)
    if parent is None:
        raise HTTPException(400, f"unknown parent framework id {req.parent!r}")

    slug = re.sub(r"[^a-z0-9]+", "_", req.name.lower()).strip("_")
    framework_id = f"fw.{slug}"
    if await store.get(framework_id) is not None:
        raise HTTPException(409, f"a framework with id {framework_id!r} already exists")

    framework = new_provisional_framework(
        id=framework_id,
        name=req.name,
        branch=branch,
        parent=req.parent,
        applicability_condition=req.applicability_condition,
    )
    await store.seed([framework])
    return _framework_to_dict(framework)


@app.delete("/frameworks/{framework_id}", dependencies=[Depends(_require_api_key)])
async def delete_framework(framework_id: str) -> dict:
    store = await _get_default_store()
    try:
        await store.delete(framework_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"deleted": framework_id}


_DEMO_TEMPLATE = Path(__file__).parent / "templates" / "demo.html"
_FAVICON = Path(__file__).parent / "templates" / "favicon.png"


@app.get("/favicon.png", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(_FAVICON, media_type="image/png")


@app.get("/", response_class=HTMLResponse)
async def demo() -> str:
    """Single-page demo UI: paste a problem, get back the matched framework.

    The API key is injected server-side (read from the same env var
    _require_api_key checks) so the page's fetch() calls work without the
    visitor typing it in — fine for a demo, not a substitute for real
    per-user auth if this page is ever exposed beyond that.
    """
    html = _DEMO_TEMPLATE.read_text(encoding="utf-8")
    api_key = os.getenv("CONTEXTIFY_API_KEY", "")
    return html.replace("__API_KEY__", api_key)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
