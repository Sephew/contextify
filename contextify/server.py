"""Hosted API wrapper around the retrieve_framework/reflect seams.

v1 constraints, deliberate not accidental: single always-on instance, in-memory
state (Framework Store / MatchHistory / PathCache reset on restart, no
multi-replica support — see contextify/api.py's process-lifetime globals).
Auth is a single static API key checked against CONTEXTIFY_API_KEY.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from .api import areflect, aretrieve_framework
from .llm import LLMClient, MockLLMClient, OpenRouterClient
from .models import FrameworkMatch, ReflectionResult

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


class ReflectRequest(BaseModel):
    match_id: str
    outcome: str


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
        "abstraction": {
            "symptom": match.abstraction.symptom,
            "reproducibility": match.abstraction.reproducibility.value,
            "evidence_available": [e.value for e in match.abstraction.evidence_available],
            "goal_shape": match.abstraction.goal_shape.value,
        },
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
        match = await aretrieve_framework(
            req.raw_input, llm=_choose_client(), problem_id=req.problem_id
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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
