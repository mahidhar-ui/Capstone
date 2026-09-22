# Module 1 — Data Pipeline (`/data_pipeline`)
**Marks: 25**

Zepto's analysts need a way to benchmark catalog-style pricing and availability data before it ever reaches a dashboard. This module plays that data-engineering role: scrape live product data from a public scraping-practice site, clean it, enrich it with the project's baseline fixed-rate currency conversion, and load it into a properly normalized relational database that's then queried with both SQL and pandas — a raw-to-relational pipeline exactly like a catalog/competitive-intelligence workflow needs.

## Data Source

**books.toscrape.com** — a public site built specifically for scraping practice. No login, no API key, no paid tier — free to scrape. The catalogue is books rather than groceries; that's fine, the exercise is about pipeline mechanics: **scrape → clean → convert → store → query**, identical regardless of product category.

---

## Tasks

### 1. Scrape

- Use `requests` + `BeautifulSoup`.
- Scrape all books across **at least 3 different categories**, OR the first 5 paginated listing pages of the "All products" catalogue — either scope is acceptable as long as the final dataset has **≥ 60 books**.
- For each book, capture:
  - `title`
  - `price` (as listed, in GBP)
  - `star_rating` (as text, e.g. "Three")
  - `availability` (as listed text)
  - `category`

### 2. Clean the scraped fields into proper types

- Strip the currency symbol from `price` and convert to a float column `price_gbp`.
- Convert the text star rating (One…Five) into an integer column `rating` (1–5).
- Parse the availability text into a boolean column `in_stock`.
- If any field fails to parse for a given row (e.g. unexpected text), handle it with **median imputation** (numeric fields) or **drop the row** — state and justify the choice. The pipeline must not crash on messy rows.

### 3. Currency conversion

- Convert `price_gbp` to a `price_inr` column using the project's **fixed baseline rate: 1 GBP = 105.50 INR**.
- This is an artificial, project-defined constant for this assignment — not a live or historical market rate — so it never needs a lookup or a date reference.
- This fixed-rate conversion is the **required, keyless baseline** and is what gets graded. It needs no external API call and no network access — state the exact rate in the README.
- **Optional, ungraded stretch** (must not affect the required submission): for extra practice with `requests` and explicit HTTP status-code handling, you may additionally look up any free, keyless currency-conversion API of your choosing, check its response status code explicitly, and fall back to the fixed rate on any failure. This is entirely optional — `price_inr` must be fully correct using only the required fixed-rate baseline, since that path alone is graded.

### 4. Normalized SQLite schema

Design a schema with **at least two tables sharing a primary/foreign key relationship**, for example:

```sql
categories(category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)
books(book_id INTEGER PRIMARY KEY, title TEXT, price_gbp REAL, price_inr REAL,
      rating INTEGER, in_stock INTEGER, category_id INTEGER REFERENCES categories(category_id))
```

Columns/tables may be renamed, but the two-table PK/FK structure is required.

### 5. Load and query

- Insert the cleaned, converted data into this schema using Python's `sqlite3` (or `pandas.DataFrame.to_sql`).
- Write and execute **at least 5 SQL queries** that collectively demonstrate:
  - `SELECT` / `WHERE`
  - `ORDER BY`
  - `LIMIT`
  - `DISTINCT`
  - `IN` or `BETWEEN`
  - plus **at least one `JOIN`** between the two tables (e.g. "list the 10 highest-rated books per category")
- Save each query string and its output.

### 6. pandas cross-check

- Read back **at least two** of the above query results into pandas DataFrames using `pd.read_sql(...)`.
- Separately reproduce the join-query's result using `pd.merge(...)` directly on the in-memory DataFrames (no SQL).
- Show that both approaches produce equivalent output.

---

## Acceptance Criteria

Submission is complete when:

- [ ] The scraping script/notebook runs end to end without manual copy-pasting and yields **≥ 60 book rows across ≥ 3 categories**.
- [ ] `price_gbp`, `rating` (int 1–5), `in_stock` (bool), and `price_inr` are all present and correctly typed; `price_inr` is computed from the required fixed-rate baseline (1 GBP = 105.50 INR, a fixed project-defined constant, no date reference), with that exact rate stated in the README.
- [ ] The repository includes the SQLite database file **or** the exact script that regenerates it from scratch, implementing the two-table PK/FK schema.
- [ ] **≥ 5 SQL queries** are present with their printed/logged output, collectively covering every required clause, plus at least one `JOIN`.
- [ ] The `pd.read_sql` and `pd.merge` outputs for the join query are shown side by side and match.
- [ ] README documents install/run steps and any parsing/cleaning decisions made.
- [ ] The **overall repository's** commit history shows a feature branch created, committed to at least twice, and merged back into main — checked once across the whole repository, not per module.

---

## Submission

This module lives at `/data_pipeline` inside the single project repository:

- The scraping + cleaning + database-loading code (script(s) or a single organized notebook)
- The SQLite database (or its exact recreation script)
- The executed SQL queries with output
- A short module-level note (in `/data_pipeline/README.md` or the root README) covering install/run steps and design decisions.