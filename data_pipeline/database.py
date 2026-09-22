import pandas as pd
import sqlite3
conn = sqlite3.connect("zepto_catalog.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    price_gbp REAL NOT NULL,
    price_inr REAL NOT NULL,
    rating INTEGER NOT NULL,
    in_stock INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
)
""")

conn.commit()

df = pd.read_csv("books_clean.csv")

category_names = df["category"].unique().tolist()

cursor.executemany(
    """
    INSERT OR IGNORE INTO categories (category_name)
    VALUES (?)
    """,
    [(name,) for name in category_names]
)

conn.commit()

print("Categories inserted successfully.")

name_to_id = dict(cursor.execute("SELECT category_name, category_id FROM categories").fetchall())

book_rows = []
for row in df.itertuples(index=False):
    book_rows.append(
        (row.title, row.price_gbp, row.price_inr, row.rating, int(row.in_stock), name_to_id[row.category])
    )

cursor.executemany(
    "INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, category_id) VALUES (?, ?, ?, ?, ?, ?)",
    book_rows
)
conn.commit()
conn.close()

print(f"Loaded {len(book_rows)} books across {len(category_names)} categories")