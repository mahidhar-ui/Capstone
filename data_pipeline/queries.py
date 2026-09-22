from IPython.display import display
import pandas as pd
import sqlite3
conn = sqlite3.connect("zepto_catalog.db")

query = """
SELECT title, rating, price_inr
FROM books
WHERE rating >= 4 AND in_stock = 1
ORDER BY price_inr DESC
LIMIT 10
"""
result = pd.read_sql(query, conn)
conn.close()
result

conn = sqlite3.connect("zepto_catalog.db")

query = "SELECT DISTINCT category_name FROM categories"
result = pd.read_sql(query, conn)
conn.close()
result

conn = sqlite3.connect("zepto_catalog.db")

query = """
SELECT title, price_gbp
FROM books
WHERE price_gbp BETWEEN 20 AND 40
ORDER BY price_gbp ASC
"""
result = pd.read_sql(query, conn)
conn.close()
result

conn = sqlite3.connect("zepto_catalog.db")

query = """
SELECT b.title, c.category_name
FROM books AS b
JOIN categories AS c ON b.category_id = c.category_id
WHERE c.category_name IN ('Travel', 'Mystery', 'Classics')
ORDER BY c.category_name, b.title
"""
result = pd.read_sql(query, conn)
conn.close()
result

join_query = """
SELECT
    c.category_name,
    b.title,
    b.rating,
    b.price_inr
FROM books AS b
JOIN categories AS c ON b.category_id = c.category_id
WHERE b.rating = (
    SELECT MAX(rating) FROM books WHERE category_id = b.category_id
)
ORDER BY c.category_name, b.title
"""

conn = sqlite3.connect("zepto_catalog.db")
df_join_sql = pd.read_sql(join_query, conn)
df_join_sql

result1 = pd.read_sql("""
SELECT title, rating, price_inr
FROM books
WHERE rating >= 4 AND in_stock = 1
ORDER BY price_inr DESC
LIMIT 10
""", conn)
result1

books_df = pd.read_sql("SELECT * FROM books", conn)
categories_df = pd.read_sql("SELECT * FROM categories", conn)
conn.close()

merged = pd.merge(books_df, categories_df, on='category_id', how='inner')

max_rating = merged.groupby('category_name')['rating'].transform('max')
df_join_merge = merged[merged['rating'] == max_rating][['category_name', 'title', 'rating', 'price_inr']]
df_join_merge = df_join_merge.sort_values(['category_name', 'title']).reset_index(drop=True)
df_join_merge


print(f"SQL JOIN rows: {len(df_join_sql)}")
print(f"pd.merge rows: {len(df_join_merge)}")



comparison = pd.concat(
    [
        df_join_sql.reset_index(drop=True).add_prefix("SQL_"),
        df_join_merge.reset_index(drop=True).add_prefix("MERGE_")
    ],
    axis=1
)

display(comparison)

print("Results equivalent:",
      df_join_sql.reset_index(drop=True).equals(
          df_join_merge.reset_index(drop=True)
      ))

