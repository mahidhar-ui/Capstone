"""
Zepto Support Assistant — a small RAG service.

Pipeline: ingestion -> embedding -> retrieval -> generation, orchestrated
with LangGraph and served over FastAPI.

MOCK_LLM toggle (read once at import time):
  - Unset, or "1"  -> MOCK MODE (required, graded baseline). No LLM calls of
    any kind are made anywhere in the graph. classify_intent uses a keyword
    heuristic, retrieve_and_answer returns a canned templated string built
    from the top retrieved chunk, and direct_answer returns a fixed canned
    string. The structured answer/sources/confidence schema is populated
    deterministically by this code.
  - "0" (must be set explicitly) -> OPTIONAL real-LLM extension. The same
    three nodes instead call Groq's chat-completions API (OpenAI-compatible)
    using the structured prompt templates in prompts.py, and the raw LLM
    output is validated against the Pydantic schema with up to 2 retries.

Retrieval itself (embedding the query + ChromaDB similarity search) always
runs for real in both modes, since it needs no API key and no network call.
"""

import json
import os
from typing import List, Optional, TypedDict

import chromadb
import requests
from chromadb.utils import embedding_functions
from fastapi import FastAPI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from prompts import ANSWER_PROMPT_TEMPLATE, DIRECT_PROMPT_TEMPLATE

# ---------------------------------------------------------------------------
# Config / toggle
# ---------------------------------------------------------------------------

# Mock mode is the default: only an EXPLICIT "0" turns it off.
MOCK_LLM = os.environ.get("MOCK_LLM", "1") != "0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "zepto_policies"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

POLICY_KEYWORDS = [
    "delivery",
    "return",
    "refund",
    "membership",
    "tracking",
    "cancel",
    "gift card",
    "support hours",
]

# ---------------------------------------------------------------------------
# Embedding + ChromaDB (Task 1: ingestion / embedding — always real, no API)
# ---------------------------------------------------------------------------

# sentence-transformers, all-MiniLM-L6-v2, run entirely locally.
# Lazily constructed (not at import time) so the model is only loaded -
# and, on first run only, downloaded and cached to disk - when it's
# actually needed, rather than blocking module import / app startup.
_embedding_fn = None
_chroma_client = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    return _embedding_fn


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def get_collection():
    return _get_chroma_client().get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=_get_embedding_fn()
    )


def ingest_documents() -> None:
    """Load the 8 corpus docs, chunk (one chunk per document, given their
    short length), embed each chunk with all-MiniLM-L6-v2, and store the
    embeddings in the ChromaDB collection. Idempotent: skips re-ingesting
    if the collection is already fully populated."""
    collection = get_collection()
    doc_files = sorted(f for f in os.listdir(DOCS_DIR) if f.endswith(".txt"))
    if collection.count() >= len(doc_files):
        return

    ids, docs = [], []
    for fname in doc_files:
        doc_id = os.path.splitext(fname)[0]  # e.g. "doc_01"
        with open(os.path.join(DOCS_DIR, fname), "r", encoding="utf-8") as fh:
            text = fh.read().strip()
        ids.append(doc_id)
        docs.append(text)

    # upsert so re-running ingestion is safe
    collection.upsert(ids=ids, documents=docs)


# ---------------------------------------------------------------------------
# Pydantic schemas (Task 5: structured output guarantee)
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: float


class _LLMAnswerSchema(BaseModel):
    """Schema the raw LLM JSON output is validated against in the
    MOCK_LLM=0 extension, before it is turned into an AskResponse."""

    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: float


# ---------------------------------------------------------------------------
# LangGraph state (Task 3)
# ---------------------------------------------------------------------------


class GraphState(TypedDict):
    query: str
    intent: Optional[str]
    retrieved_chunks: Optional[List[dict]]
    answer: Optional[str]
    sources: List[str]
    confidence: float


# ---------------------------------------------------------------------------
# Real-LLM helpers (Groq, OpenAI-compatible) — optional MOCK_LLM=0 extension
# ---------------------------------------------------------------------------


def _call_groq(messages: list, temperature: float = 0.2) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "MOCK_LLM=0 but GROQ_API_KEY is not set. Export a free-tier Groq "
            "API key (console.groq.com) to use the real-LLM extension."
        )
    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def call_llm_classify(query: str) -> str:
    """Optional MOCK_LLM=0 extension for classify_intent: ask the LLM to
    classify instead of using the keyword heuristic. Falls back to the
    heuristic if the API call itself fails, so the endpoint stays usable."""
    messages = [
        {
            "role": "system",
            "content": (
                "Classify the user's question as exactly one word: "
                "policy_question or general_question. A policy_question is "
                "about Zepto's delivery, returns, refunds, membership, "
                "order tracking, cancellation, gift cards, or support "
                "hours. Respond with only the single classification word, "
                "nothing else."
            ),
        },
        {"role": "user", "content": query},
    ]
    try:
        raw = _call_groq(messages).strip().lower()
        return "policy_question" if "policy" in raw else "general_question"
    except Exception:
        query_lower = query.lower()
        if any(kw in query_lower for kw in POLICY_KEYWORDS):
            return "policy_question"
        return "general_question"


def _validated_llm_call(build_messages, max_retries: int = 2):
    """Calls the LLM and validates its JSON output against
    _LLMAnswerSchema, retrying up to `max_retries` additional times with a
    corrective instruction appended to the prompt on failure. Returns
    (answer, sources, confidence) on success, or a clearly marked error
    response after all attempts are exhausted."""
    last_error: Optional[Exception] = None
    correction = ""
    for _ in range(max_retries + 1):
        messages = build_messages(correction)
        try:
            raw = _call_groq(messages)
            parsed = _extract_json(raw)
            validated = _LLMAnswerSchema(**parsed)
            return validated.answer, validated.sources, validated.confidence
        except Exception as exc:  # noqa: BLE001 - deliberately broad, retried
            last_error = exc
            correction = (
                "\n\nIMPORTANT: Your previous response was invalid "
                f"({exc}). Respond with ONLY a valid JSON object with "
                "exactly the keys 'answer' (string), 'sources' (list of "
                "strings), and 'confidence' (float between 0 and 1). No "
                "markdown fences, no extra text before or after the JSON."
            )
    return (
        f"[ERROR] Could not get a valid structured response from the LLM "
        f"after {max_retries + 1} attempts: {last_error}",
        [],
        0.0,
    )


def call_llm_answer(query: str, chunks: List[dict]):
    context = "\n\n".join(f"[{c['id']}] {c['text']}" for c in chunks)

    def build_messages(correction: str):
        prompt = ANSWER_PROMPT_TEMPLATE.format(context=context, query=query)
        return [{"role": "user", "content": prompt + correction}]

    answer, sources, confidence = _validated_llm_call(build_messages)
    # Prefer the LLM's own cited sources when it gave any valid ones;
    # otherwise fall back to all retrieved chunk ids.
    valid_ids = {c["id"] for c in chunks}
    cited = [s for s in sources if s in valid_ids]
    final_sources = cited if cited else [c["id"] for c in chunks]
    return answer, final_sources, confidence


def call_llm_direct(query: str):
    def build_messages(correction: str):
        prompt = DIRECT_PROMPT_TEMPLATE.format(query=query)
        return [{"role": "user", "content": prompt + correction}]

    answer, _sources, confidence = _validated_llm_call(build_messages)
    return answer, confidence


# ---------------------------------------------------------------------------
# LangGraph nodes (Task 3)
# ---------------------------------------------------------------------------


def classify_intent(state: GraphState) -> GraphState:
    if MOCK_LLM:
        query_lower = state["query"].lower()
        intent = (
            "policy_question"
            if any(kw in query_lower for kw in POLICY_KEYWORDS)
            else "general_question"
        )
    else:
        intent = call_llm_classify(state["query"])
    return {**state, "intent": intent}


def retrieve_and_answer(state: GraphState) -> GraphState:
    collection = get_collection()
    results = collection.query(query_texts=[state["query"]], n_results=3)
    ids = results["ids"][0]
    docs = results["documents"][0]
    chunks = [{"id": i, "text": d} for i, d in zip(ids, docs)]

    if not chunks:
        return {
            **state,
            "retrieved_chunks": [],
            "answer": "I don't have any policy information to answer that.",
            "sources": [],
            "confidence": 0.0,
        }

    if MOCK_LLM:
        top_snippet = chunks[0]["text"][:200]
        answer = f"Based on the retrieved context: {top_snippet}"
        sources = [c["id"] for c in chunks]
        confidence = 1.0
    else:
        answer, sources, confidence = call_llm_answer(state["query"], chunks)

    return {
        **state,
        "retrieved_chunks": chunks,
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def direct_answer(state: GraphState) -> GraphState:
    if MOCK_LLM:
        answer = "I can only answer questions about Zepto policies right now."
        confidence = 1.0
    else:
        answer, confidence = call_llm_direct(state["query"])
    return {**state, "answer": answer, "sources": [], "confidence": confidence}


def route_intent(state: GraphState) -> str:
    return "retrieve_and_answer" if state["intent"] == "policy_question" else "direct_answer"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

_graph_builder = StateGraph(GraphState)
_graph_builder.add_node("classify_intent", classify_intent)
_graph_builder.add_node("retrieve_and_answer", retrieve_and_answer)
_graph_builder.add_node("direct_answer", direct_answer)
_graph_builder.set_entry_point("classify_intent")
_graph_builder.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "retrieve_and_answer": "retrieve_and_answer",
        "direct_answer": "direct_answer",
    },
)
_graph_builder.add_edge("retrieve_and_answer", END)
_graph_builder.add_edge("direct_answer", END)
graph = _graph_builder.compile()


# ---------------------------------------------------------------------------
# FastAPI app (Task 6)
# ---------------------------------------------------------------------------

app = FastAPI(title="Zepto Support Assistant", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    ingest_documents()


@app.get("/health")
def health():
    return {"status": "ok", "mock_llm": MOCK_LLM}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    initial_state: GraphState = {
        "query": req.query,
        "intent": None,
        "retrieved_chunks": None,
        "answer": None,
        "sources": [],
        "confidence": 0.0,
    }
    result = graph.invoke(initial_state)
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
    )


if __name__ == "__main__":
    import uvicorn

    ingest_documents()
    uvicorn.run(app, host="0.0.0.0", port=7860)