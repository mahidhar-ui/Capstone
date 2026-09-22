df["price_inr"] = (df["price_gbp"] * 105.50).round(2)

price_check = (
    df["price_inr"].round(2)
    == (df["price_gbp"] * 105.50).round(2)
).all()

print("Price conversion correct:", price_check)

print("Final rows:", len(df))
print("Categories:", df["category"].nunique())
print("price_gbp dtype:", df["price_gbp"].dtype)
print("price_inr dtype:", df["price_inr"].dtype)
print("rating dtype:", df["rating"].dtype)
print("in_stock dtype:", df["in_stock"].dtype)