"""Spike v2: does recall(query_type=SearchType.CHUNKS) return raw document
text (vs. GRAPH_COMPLETION's LLM-synthesized answer seen in spike v1)?
Also re-verifies forget() dataset scoping in isolation (v1 crashed on
DatasetNotFoundError before reaching the scoping check)."""

import asyncio
import json
import os

from dotenv import load_dotenv


def configure_from_openrouter() -> None:
    load_dotenv()
    key = os.getenv("OPENROUTER_API_KEY")
    endpoint = "https://openrouter.ai/api/v1"
    os.environ.setdefault("LLM_PROVIDER", "openai")
    os.environ.setdefault("LLM_MODEL", "openai/gpt-4o-mini")
    os.environ.setdefault("LLM_ENDPOINT", endpoint)
    os.environ.setdefault("LLM_API_KEY", key)
    os.environ.setdefault("EMBEDDING_PROVIDER", "openai")
    os.environ.setdefault("EMBEDDING_MODEL", "openai/text-embedding-3-small")
    os.environ.setdefault("EMBEDDING_ENDPOINT", endpoint)
    os.environ.setdefault("EMBEDDING_API_KEY", key)
    os.environ.setdefault("EMBEDDING_DIMENSIONS", "1536")


DATASET = "contextify_recall_spike2"
OTHER_DATASET = "contextify_recall_spike2_other"


async def main() -> None:
    configure_from_openrouter()
    import cognee
    from cognee.modules.search.types import SearchType

    doc = json.dumps(
        {
            "id": "root-cause-isolation",
            "name": "Root-Cause Isolation",
            "branch": "debugging",
            "parent": None,
            "applicability_condition": ["bug is reproducible", "evidence available"],
            "status": "seeded",
            "confidence": 1.0,
        }
    )
    await cognee.remember(doc, dataset_name=DATASET, node_set=["root-cause-isolation"])
    doc2 = json.dumps(
        {
            "id": "binary-search-bisection",
            "name": "Binary Search Bisection",
            "branch": "debugging",
            "parent": None,
            "applicability_condition": ["large search space"],
            "status": "seeded",
            "confidence": 1.0,
        }
    )
    await cognee.remember(doc2, dataset_name=DATASET, node_set=["binary-search-bisection"])

    print("=== recall(query_type=CHUNKS), node_name filtered ===")
    results = await cognee.recall(
        query_text="root cause isolation",
        query_type=SearchType.CHUNKS,
        datasets=[DATASET],
        node_name=["root-cause-isolation"],
        top_k=10,
    )
    print(f"{len(results)} result(s)")
    for i, r in enumerate(results):
        print(f"--- [{i}] type={type(r).__name__} ---")
        try:
            print(r.model_dump())
        except Exception as e:
            print("dump failed", e)

    print("\n=== recall(query_type=CHUNKS), no node_name filter (both docs) ===")
    results_all = await cognee.recall(
        query_text="debugging framework",
        query_type=SearchType.CHUNKS,
        datasets=[DATASET],
        top_k=10,
    )
    print(f"{len(results_all)} result(s)")
    for i, r in enumerate(results_all):
        d = r.model_dump()
        print(f"[{i}]", {k: d.get(k) for k in ("kind", "text", "metadata")})

    print("\n=== forget(dataset=...) scoping, isolated ===")
    await cognee.remember(
        json.dumps({"id": "sentinel", "name": "sentinel"}),
        dataset_name=OTHER_DATASET,
        node_set=["sentinel"],
    )
    forget_result = await cognee.forget(dataset=DATASET)
    print("forget() ->", forget_result)

    try:
        after = await cognee.recall(
            query_text="root cause isolation",
            query_type=SearchType.CHUNKS,
            datasets=[DATASET],
            node_name=["root-cause-isolation"],
            top_k=10,
        )
        print(f"recall() on forgotten dataset returned {len(after)} results (no error)")
    except Exception as e:
        print(f"recall() on forgotten dataset RAISED {type(e).__name__}: {e}")

    other = await cognee.recall(
        query_text="sentinel",
        query_type=SearchType.CHUNKS,
        datasets=[OTHER_DATASET],
        node_name=["sentinel"],
        top_k=10,
    )
    print(f"recall() on OTHER dataset returned {len(other)} results (expect >=1, untouched)")

    await cognee.forget(dataset=OTHER_DATASET)
    print("cleaned up OTHER_DATASET")


if __name__ == "__main__":
    asyncio.run(main())
