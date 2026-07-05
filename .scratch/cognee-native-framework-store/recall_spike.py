"""Throwaway spike script (not production code) for cognee-store-01-recall-spike.

Confirms live remember()/recall()/forget() behavior against real Cognee +
OpenRouter, so Slice 2 (CogneeMemoryStore) can build against confirmed
response shapes instead of a guess. Findings written to
recall-spike-findings.md alongside this script.

Run: python .scratch/cognee-native-framework-store/recall_spike.py
"""

import asyncio
import json
import os

from dotenv import load_dotenv


def configure_from_openrouter() -> None:
    load_dotenv()
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY required for this spike")
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


DATASET = "contextify_recall_spike"
OTHER_DATASET = "contextify_recall_spike_other"


async def main() -> None:
    configure_from_openrouter()
    import cognee
    from cognee.modules.recall.types import RecallResponse

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

    print("=== 1. remember() ===")
    remember_result = await cognee.remember(
        doc, dataset_name=DATASET, node_set=["root-cause-isolation"]
    )
    print("remember() returned:", type(remember_result), remember_result)

    # second doc in the SAME dataset, different node_set, to confirm node_name
    # filtering actually narrows results instead of returning everything.
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

    print("\n=== 2. recall() filtered by node_name ===")
    results = await cognee.recall(
        query_text="root cause isolation debugging framework",
        datasets=[DATASET],
        node_name=["root-cause-isolation"],
        top_k=10,
    )
    print(f"recall() returned {len(results)} result(s)")
    for i, r in enumerate(results):
        print(f"--- result[{i}] ---")
        print("type:", type(r).__name__)
        print("source discriminator:", getattr(r, "source", None))
        try:
            print("dump:", r.model_dump())
        except Exception as e:
            print("model_dump failed:", e)

    print("\n=== 3. forget(dataset=...) scoping ===")
    # seed a second, unrelated dataset so we can confirm forget() doesn't
    # touch it.
    await cognee.remember(
        json.dumps({"id": "sentinel", "name": "sentinel"}),
        dataset_name=OTHER_DATASET,
        node_set=["sentinel"],
    )

    forget_result = await cognee.forget(dataset=DATASET)
    print("forget() returned:", forget_result)

    after_forget = await cognee.recall(
        query_text="root cause isolation debugging framework",
        datasets=[DATASET],
        node_name=["root-cause-isolation"],
        top_k=10,
    )
    print(f"recall() on forgotten dataset returned {len(after_forget)} result(s) (expect 0)")

    other_still_there = await cognee.recall(
        query_text="sentinel",
        datasets=[OTHER_DATASET],
        node_name=["sentinel"],
        top_k=10,
    )
    print(
        f"recall() on OTHER dataset returned {len(other_still_there)} result(s) "
        "(expect >=1, i.e. untouched by forget)"
    )

    # cleanup the sentinel dataset too
    await cognee.forget(dataset=OTHER_DATASET)


if __name__ == "__main__":
    asyncio.run(main())
