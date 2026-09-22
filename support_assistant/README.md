# Zepto Support Assistant — RAG service

A small, fully local-by-default RAG service for Zepto's delivery, returns,
membership, tracking, cancellation, gift card, and support-hours policies,
orchestrated with LangGraph and served over FastAPI.

## 1. Setup

```bash
cd support_assistant
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

The **first time** you run the app, `sentence-transformers` downloads and
caches `all-MiniLM-L6-v2` (~90 MB) from Hugging Face. This needs a normal
internet connection once; every run after that is fully offline for
embeddings (no API key, no cost).

## 2. Run locally

```bash
# MOCK_LLM defaults to "1" (mock mode) if left unset — this is the graded baseline.
uvicorn main:app --host 0.0.0.0 --port 7860
```

Then, in another terminal:

```powershell
$body1 = @{ query = "Can I cancel my order after it's already been packed?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:7860/ask -Method Post -Body $body1 -ContentType "application/json" | ConvertTo-Json

$body2 = @{ query = "What's the capital of France?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:7860/ask -Method Post -Body $body2 -ContentType "application/json" | ConvertTo-Json
```

## 3. Run with Docker (required baseline — local build/run only)

```powershell
docker build -t zepto-support-assistant .
docker run -p 7860:7860 zepto-support-assistant
```

Docker image runs mock mode by default (`MOCK_LLM=1` baked into the image).
No push to a registry is required or performed — build-and-run locally
satisfies the graded requirement.

## 4. Optional, ungraded extension — real LLM via Groq's free tier

```powershell
$env:MOCK_LLM = "0"
$env:GROQ_API_KEY = "your_free_groq_key"   # console.groq.com, free tier, no card
uvicorn main:app --host 0.0.0.0 --port 7860
```

With `MOCK_LLM=0`, `classify_intent`, `retrieve_and_answer`, and
`direct_answer` all call the LLM instead of using canned/heuristic logic
(see "MOCK_LLM toggle" below). This path is entirely optional; the required
submission is graded with `MOCK_LLM` left at its default.

---

## Architecture: ingestion → embedding → retrieval → generation

**Ingestion** (`ingest_documents()` in `main.py`): on FastAPI startup, the 8
corpus files under `docs/doc_01.txt` … `docs/doc_08.txt` are read from disk.
Given how short each policy document is, chunking is one chunk per document
(no further splitting) — each file's full text becomes a single chunk, IDs
`doc_01` … `doc_08`.

**Embedding**: each chunk is embedded locally with `sentence-transformers`'
`all-MiniLM-L6-v2` model, wired in via `chromadb.utils.embedding_functions
.SentenceTransformerEmbeddingFunction`. No API key or network call is made
for embedding (beyond the one-time model download on first use). Vectors
are stored in a persistent ChromaDB collection named `zepto_policies`
(`get_collection()` in `main.py`), backed by a `PersistentClient` writing to
`./chroma_db`.

**Retrieval**: the LangGraph node `retrieve_and_answer` embeds the incoming
query with the same model and asks ChromaDB for the top-3 chunks by cosine
similarity (`collection.query(query_texts=..., n_results=3)`). This step
always runs for real, in both mock and real-LLM modes, since it needs no
API key.

**Generation**: the *final answer text* is the only part gated by
`MOCK_LLM`:
- **Mock mode (default, graded baseline)**: `retrieve_and_answer` returns
  `f"Based on the retrieved context: {top_chunk[:200]}"` built directly
  from the top retrieved chunk — no LLM call. `direct_answer` (used for
  `general_question` queries, which skip retrieval entirely) returns a
  fixed string, "I can only answer questions about Zepto policies right
  now." — also no LLM call. `classify_intent` uses a keyword heuristic
  (checks for "delivery", "return", "refund", "membership", "tracking",
  "cancel", "gift card", "support hours" in the lowercased query) instead
  of calling an LLM.
- **Optional `MOCK_LLM=0` extension**: `classify_intent` asks the LLM to
  classify the query; `retrieve_and_answer` prompts the LLM with the
  structured template in `prompts.py` (`ANSWER_PROMPT_TEMPLATE`), grounded
  only in the 3 retrieved chunks; `direct_answer` prompts the LLM directly
  (`DIRECT_PROMPT_TEMPLATE`) with no retrieved context. Both real-LLM
  generation paths call Groq's OpenAI-compatible chat-completions endpoint
  and validate the raw JSON output against a Pydantic schema
  (`_LLMAnswerSchema`), retrying up to 2 additional times with a corrective
  instruction appended to the prompt if validation fails, before returning
  a response clearly marked `[ERROR] ...`.

**Routing**: `classify_intent` sets `state["intent"]` to `policy_question`
or `general_question`. A conditional edge (`route_intent`, wired via
`add_conditional_edges`) sends `policy_question` queries to
`retrieve_and_answer` and everything else to `direct_answer`. This routing
logic is identical in both modes — only what happens *inside* the chosen
node depends on `MOCK_LLM`.

**Structured output**: every path — mock or real — ends by populating an
`AskResponse` Pydantic model (`answer: str`, `sources: list[str]`,
`confidence: float`), returned by the `POST /ask` FastAPI endpoint. In mock
mode this is populated deterministically by the node code itself (e.g.
`sources` = ids of the chunks that were retrieved, `confidence = 1.0`) —
there's no LLM output to fail validation because none was generated.

```
 docs/doc_01.txt ... doc_08.txt
          │  (ingest_documents)
          ▼
 all-MiniLM-L6-v2 embeddings ──▶ ChromaDB collection "zepto_policies"
                                          │
 query ──▶ classify_intent ──▶ (keyword   │  cosine top-3
              │  heuristic /              ▼
              │   LLM)          retrieve_and_answer ──▶ AskResponse
              │                  (canned tmpl / LLM+schema)
              ▼
         direct_answer ──▶ AskResponse
          (canned string / LLM+schema)
```

---

## MOCK_LLM toggle — what changes

| Stage | `MOCK_LLM` unset / `1` (default, graded) | `MOCK_LLM=0` (optional extension) |
|---|---|---|
| `classify_intent` | keyword heuristic, no LLM call | LLM call to classify, falls back to heuristic on API failure |
| `retrieve_and_answer` (retrieval) | real ChromaDB cosine search, always | same — unchanged |
| `retrieve_and_answer` (generation) | canned `"Based on the retrieved context: ..."` string | LLM call using `ANSWER_PROMPT_TEMPLATE`, schema-validated with retries |
| `direct_answer` | fixed canned string | LLM call using `DIRECT_PROMPT_TEMPLATE`, schema-validated with retries |
| Network / API key needed | none | Groq API key (`GROQ_API_KEY` env var) |

---

## Example calls (recorded output)

Run locally with `MOCK_LLM` left at its default, via
`uvicorn main:app --host 0.0.0.0 --port 7860`, on Windows / Python 3.10,
with the real `all-MiniLM-L6-v2` model (auto-downloaded on first run).

### Call 1 — triggers retrieval (`policy_question`)

Request:
```json
POST /ask
{"query": "Can I cancel my order after it's already been packed?"}
```

Response:
```json
{
  "answer": "Based on the retrieved context: Orders can be cancelled free of cost any time before the order status changes to 'Packed', typically within the first 2 minutes of placing the order. Once an order has been packed, it can no longer be",
  "sources": ["doc_05", "doc_02", "doc_06"],
  "confidence": 1.0
}
```
`classify_intent` matched the keyword "cancel" → routed to
`retrieve_and_answer`. The top retrieved chunk is `doc_05` (Order
Cancellation Policy) — the correct source document for this question,
confirmed by real MiniLM cosine similarity search against ChromaDB.

### Call 2 — skips retrieval (`general_question`)

Request:
```json
POST /ask
{"query": "What's the capital of France?"}
```

Response:
```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```
No keyword matched → routed to `direct_answer`, fixed canned string, no
retrieval, no LLM call.

---

## Files

```
support_assistant/
├── docs/doc_01.txt ... doc_08.txt   # Zepto policy corpus (verbatim, per spec)
├── prompts.py                       # role/context/task/format/length prompt templates
├── main.py                          # ingestion, ChromaDB, LangGraph graph, FastAPI app
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md                        # this file
```