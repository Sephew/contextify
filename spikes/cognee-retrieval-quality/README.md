# Cognee retrieval-quality spike

Answers issue 01's question: does Cognee's embedding space handle abstract/structural
similarity well enough to retrieve the right reasoning Framework? See `VERDICT.md` for
the conclusion, `results.json` for raw numbers.

## Files

- `frameworks.py` — 6 seeded Frameworks (3 Debugging, 3 Testing), importable by later slices.
- `fixtures.py` — 20 adversarial cases (false-friend + disguised-twin pairs), importable as regression fixtures.
- `run_spike.py` — seeds Cognee once, queries it twice per case (raw text vs. hand-abstracted schema), writes `results.json`.

## Running it

```
pip install "cognee[fastembed]" python-dotenv
python run_spike.py --top-k 3
```

Requires a `.env` (repo root, gitignored) with:

```
LLM_PROVIDER=openai
LLM_MODEL=openai/<model>          # e.g. openai/gpt-4o-mini
LLM_ENDPOINT=<openai-compatible endpoint>   # e.g. an OpenRouter/OpenAI base URL
LLM_API_KEY=<key for that endpoint>
LLM_ARGS={"max_tokens": 2000}     # cap output tokens to fit low-credit accounts; adjust/remove if unconstrained

EMBEDDING_PROVIDER=fastembed       # local, no API key/credits needed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384

# Windows only: Cognee's default data dirs live deep under site-packages, which
# blows past the 260-char MAX_PATH once LanceDB's own nested paths are appended.
# Point them somewhere short instead.
DATA_ROOT_DIRECTORY=C:\cognee_data\data
SYSTEM_ROOT_DIRECTORY=C:\cognee_data\system
CACHE_ROOT_DIRECTORY=C:\cognee_data\cache

# Cognee's pre-flight connection test uses instructor structured-output mode,
# which can retry-loop past the 30s timeout on some OpenAI-compatible proxies
# even though plain completions work fine. Skip it once you've verified
# connectivity another way (see below).
COGNEE_SKIP_CONNECTION_TEST=true
```

Sanity-check LLM connectivity directly (bypasses Cognee's flaky pre-flight check):

```python
import litellm
litellm.completion(model="openai/<model>", api_base="<endpoint>", api_key="<key>",
                    messages=[{"role": "user", "content": "say hi"}], max_tokens=20)
```
