# Zepto Data & AI Platform
**Capstone Project — Certificate Program in Artificial Intelligence and Machine Learning**

An end-to-end AI/ML engineer moves comfortably across the full stack: pulling raw data from the wild, cleaning and storing it properly, understanding it visually, building and evaluating predictive models on it, and wrapping intelligence around it with a deployed GenAI service. This repository is that platform, built as an incoming AI/ML engineer joining Zepto's analytics guild — one connected submission made of three internally-linked capabilities:

1. A **data-engineering pipeline** that turns raw scraped data into a clean relational store.
2. An **analytics pipeline** that profiles and models a customer-style dataset end to end.
3. A **GenAI support assistant** that answers policy questions grounded in Zepto's own documents.

This is a single, coherent submission, not three unrelated exercises — all three modules live in, and are submitted as, one public GitHub repository.

**Total marks: 100** · Modules: 3 (`/data_pipeline` — 25, `/analytics` — 50, `/support_assistant` — 25)

---

## Repository Structure

```
.
├── data_pipeline/
│   ├── (scraping + cleaning + DB-loading code)
│   ├── books.db                # SQLite database (or its recreation script)
│   └── README.md                # module-level notes
├── analytics/
│   ├── 01_eda.ipynb
│   ├── 02_modeling.ipynb
│   ├── titanic.csv              # committed offline fallback
│   ├── pipeline.joblib          # saved fitted pipeline
│   └── README.md                # module-level notes
├── support_assistant/
│   ├── docs/                    # doc_01.txt … doc_08.txt (Zepto policy corpus)
│   ├── main.py                  # FastAPI app
│   ├── graph.py                 # LangGraph StateGraph
│   ├── Dockerfile
│   └── README.md                # module-level notes
├── requirements.txt              # or one requirements.txt per module — state your choice below
└── README.md                     # this file
```

---

## Module Summaries

### Module 1 — Data Pipeline (`/data_pipeline`, 25 marks)
Scrapes ≥ 60 books across ≥ 3 categories from books.toscrape.com, cleans and types the fields (`price_gbp`, `rating`, `in_stock`), converts to `price_inr` at the fixed baseline rate **1 GBP = 105.50 INR**, and loads everything into a normalized two-table SQLite schema (`categories` ⟷ `books`, PK/FK). Includes ≥ 5 SQL queries covering `SELECT/WHERE`, `ORDER BY`, `LIMIT`, `DISTINCT`, `IN`/`BETWEEN`, and a `JOIN`, cross-checked against equivalent `pd.read_sql` / `pd.merge` results.

### Module 2 — Analytics Pipeline (`/analytics`, 50 marks)
Loads the Titanic dataset once (`sns.load_dataset('titanic')`, cached to `titanic.csv`), profiles and cleans it per a percentage-based missing-value threshold rule, and builds a full EDA data story (univariate/bivariate/multivariate analysis, correlation heatmap). Continues into a modeling pipeline: stratified split, leak-free `Pipeline`/`ColumnTransformer` preprocessing, three classifiers (Logistic Regression, Decision Tree, Random Forest) evaluated on the full metric suite, a class-imbalance comparison (baseline vs. `class_weight='balanced'` vs. SMOTE), `GridSearchCV` tuning with OOB score, a linear-regression side-task predicting `fare`, and a final saved end-to-end `joblib` pipeline.

### Module 3 — Support Assistant (`/support_assistant`, 25 marks)
An 8-document Zepto policy corpus, embedded locally with `sentence-transformers` (`all-MiniLM-L6-v2`) and stored in ChromaDB. A LangGraph `StateGraph` (`classify_intent` → `retrieve_and_answer` / `direct_answer`) routes each query, with a structured Pydantic output schema (`answer`, `sources`, `confidence`). Graded entirely through a deterministic, offline `MOCK_LLM` mode — no signup, API key, or network call to any LLM provider required. Wrapped in a FastAPI `POST /ask` endpoint and a locally buildable/runnable Dockerfile. A real LLM call (Groq free tier) and a Hugging Face Spaces deployment are optional, ungraded extensions.

---

## Setup

> State here which you used: **one consolidated `requirements.txt`** at the repo root, or **one `requirements.txt` per module**.

```bash
git clone <your-repo-url>
cd <your-repo>

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt # or: pip install -r data_pipeline/requirements.txt, etc.
```

No paid services are required anywhere in this project — every external dependency (scraping target, embeddings, vector store, LLM mock mode) has an explicitly free or fully local path; see each module's own note.

---

## How to Run Each Module End to End

### 1. Data Pipeline
```bash
cd data_pipeline
python scrape_and_load.py        # scrapes, cleans, converts, builds books.db
python run_queries.py            # executes the 5+ SQL queries and prints output
```

### 2. Analytics Pipeline
```bash
cd analytics
jupyter nbconvert --to notebook --execute 01_eda.ipynb
jupyter nbconvert --to notebook --execute 02_modeling.ipynb
# or run as plain scripts if you used .py files instead of notebooks
```

### 3. Support Assistant
```bash
cd support_assistant
python ingest.py                 # embeds the 8 docs into ChromaDB

# graded baseline — MOCK_LLM defaults to mock mode:
uvicorn main:app --host 0.0.0.0 --port 7860

# example calls (see module README for full recorded transcripts):
curl -X POST http://localhost:7860/ask -H "Content-Type: application/json" \
     -d '{"query": "What is your return policy?"}'

# Docker (locally buildable/runnable — required baseline):
docker build -t zepto-support-assistant .
docker run -p 7860:7860 zepto-support-assistant
```

---

## Design Decisions

> Short summary per module — fill in as you build.

**Data Pipeline:** _(scraping scope chosen, malformed-row handling strategy, schema naming, etc.)_

**Analytics Pipeline:** _(missing-value strategy per column, model/imbalance-handling conclusions, final classifier recommendation, etc.)_

**Support Assistant:** _(chunking scheme, prompt template design, retry logic for the optional real-LLM path, etc.)_

---

## Submission Guidelines

- **One repository only.** All three module folders (`/data_pipeline`, `/analytics`, `/support_assistant`) live at the repo root alongside this single root `README.md` — no separate repos per module.
- **All deliverables are textual.** Code as `.py`/`.ipynb`; every write-up as Markdown text (this README, a module README, or notebook Markdown cells). No screenshots, PDFs, slide decks, video, or audio are required or accepted. Saved chart `.png` files may live in the repo as supporting artifacts but never substitute for the required written interpretation — a grader must be able to assess the work from text alone.
- **Academic integrity:** code, analysis, and written interpretations are the author's own; documentation may be referenced, but authorship may not be delegated.
- **Git workflow** (scored once, against the whole repository, under the `/data_pipeline` rubric): commit history must show at least one feature branch created, committed to at least twice, and merged back into `main` — visible via `git log --graph --all` or the repo's branch/merge history. This can be demonstrated anywhere in the repo; it is not required separately per module and is not double-counted.
- **No paid services** are required anywhere in the project — each module's fallback note is specific to that module and does not carry over to another module's dependency.
- **Deadline:** per the date/time communicated on the LMS for this evaluation.

---

## Grading Breakdown

| Module | Path | Marks |
|---|---|---|
| Data Pipeline | `/data_pipeline` | 25 |
| Analytics Pipeline | `/analytics` | 50 |
| Support Assistant | `/support_assistant` | 25 |
| **Total** | | **100** |