import pandas as pd
df = pd.read_csv("books_raw.csv")
df.isnull().sum()
import re


df['price_gbp'] = df['price'].apply(lambda s: re.sub(r'[^\d.]', '', str(s)))
df['price_gbp'] = pd.to_numeric(df['price_gbp'], errors='coerce')

rating_map = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
df['rating'] = df['star_rating'].map(rating_map)

df['in_stock'] = df['availability'].str.contains('In stock', case=False, na=False)

df.isnull().sum()

median = df['price_gbp'].median()
df['price_gbp'] = df['price_gbp'].fillna(median)
print(f"Median-imputed price_gbp with {median:.2f}")

n_before = len(df)
df = df.dropna(subset=['rating'])
df['rating'] = df['rating'].astype(int)
print(f"Dropped {n_before - len(df)} row(s) with an unparseable rating")

df['price_inr'] = df['price_gbp'] * 105.50

df = df[['title', 'price_gbp', 'price_inr', 'rating', 'in_stock', 'category']]
df.to_csv("books_clean.csv", index=False)
df