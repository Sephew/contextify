"""Cognee retrieval-quality spike runner (Slice 0).

Seeds the Framework Store (frameworks.py) into Cognee once, then queries it
twice per fixture case (fixtures.py): once with the raw problem text, once
with a hand-written abstracted-schema string. Records whether the correct
Framework lands in the top-k CHUNKS search results for each pass, so a gap
between the two passes can be attributed to embedding-space weakness vs.
missing abstraction.

Usage: python run_spike.py [--top-k N]
Writes results.json next to this file and prints a summary table.
"""

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import cognee
from cognee.modules.search.types import SearchType

from fixtures import FIXTURES
from frameworks import FRAMEWORKS

DATASET = "framework_store_spike"
RESULTS_PATH = Path(__file__).parent / "results.json"


def rank_of_correct_framework(search_results: list[dict], correct_framework: str) -> int | None:
    """1-indexed rank of the first chunk belonging to correct_framework, or None if absent."""
    for i, chunk in enumerate(search_results, start=1):
        if correct_framework in (chunk.get("belongs_to_set") or []):
            return i
    return None


async def seed_framework_store() -> None:
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    for fw in FRAMEWORKS:
        await cognee.add([fw.description], dataset_name=DATASET, node_set=[fw.id])

    await cognee.cognify(datasets=[DATASET])


async def run_pass(query_field: str, top_k: int) -> list[dict]:
    """query_field is 'raw_text' or 'abstracted_text' (a FixtureCase attribute/method)."""
    results = []
    for case in FIXTURES:
        query_text = case.raw_text if query_field == "raw_text" else case.abstracted_text()

        search_results = await cognee.search(
            query_text=query_text,
            query_type=SearchType.CHUNKS,
            datasets=[DATASET],
            top_k=top_k,
        )
        chunks = search_results[0]["search_result"] if search_results else []
        rank = rank_of_correct_framework(chunks, case.correct_framework)

        results.append(
            {
                "case_id": case.id,
                "kind": case.kind,
                "pair_id": case.pair_id,
                "branch": case.branch,
                "correct_framework": case.correct_framework,
                "rank": rank,
                "hit_top_1": rank == 1,
                "hit_top_k": rank is not None,
            }
        )
    return results


def summarize(results: list[dict], top_k: int) -> dict:
    total = len(results)
    top1 = sum(r["hit_top_1"] for r in results)
    topk = sum(r["hit_top_k"] for r in results)

    def by(key):
        groups = {}
        for r in results:
            groups.setdefault(r[key], []).append(r)
        return {
            k: {
                "n": len(v),
                "top_1_accuracy": sum(x["hit_top_1"] for x in v) / len(v),
                f"top_{top_k}_accuracy": sum(x["hit_top_k"] for x in v) / len(v),
            }
            for k, v in groups.items()
        }

    return {
        "n": total,
        "top_1_accuracy": top1 / total,
        f"top_{top_k}_accuracy": topk / total,
        "by_kind": by("kind"),
        "by_branch": by("branch"),
    }


async def main(top_k: int) -> None:
    print(f"Seeding {len(FRAMEWORKS)} frameworks into Cognee dataset '{DATASET}'...")
    await seed_framework_store()

    print(f"Running raw-text pass over {len(FIXTURES)} cases (top_k={top_k})...")
    raw_results = await run_pass("raw_text", top_k)

    print(f"Running abstracted-schema pass over {len(FIXTURES)} cases (top_k={top_k})...")
    abstracted_results = await run_pass("abstracted_text", top_k)

    output = {
        "top_k": top_k,
        "raw_text": {"results": raw_results, "summary": summarize(raw_results, top_k)},
        "abstracted_schema": {
            "results": abstracted_results,
            "summary": summarize(abstracted_results, top_k),
        },
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2))

    print("\n=== SUMMARY ===")
    print(f"raw_text        top-1: {output['raw_text']['summary']['top_1_accuracy']:.0%}"
          f"  top-{top_k}: {output['raw_text']['summary'][f'top_{top_k}_accuracy']:.0%}")
    print(f"abstracted_text top-1: {output['abstracted_schema']['summary']['top_1_accuracy']:.0%}"
          f"  top-{top_k}: {output['abstracted_schema']['summary'][f'top_{top_k}_accuracy']:.0%}")
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(main(args.top_k))
