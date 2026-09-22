import requests
from bs4 import BeautifulSoup
import csv
import time
from urllib.parse import urljoin
import pandas as pd
import sqlite3
BASE_URL = "https://books.toscrape.com/"

# 6 categories comfortably clears the >=60 book / >=3 category requirement
CATEGORIES = {
    "Travel": "catalogue/category/books/travel_2/index.html",
    "Mystery": "catalogue/category/books/mystery_3/index.html",
    "Historical Fiction": "catalogue/category/books/historical-fiction_4/index.html",
    "Classics": "catalogue/category/books/classics_6/index.html",
    "Philosophy": "catalogue/category/books/philosophy_7/index.html",
    "Romance": "catalogue/category/books/romance_8/index.html",
}

RATING_WORDS = {"One", "Two", "Three", "Four", "Five"}
all_books = []

for category_name, start_path in CATEGORIES.items():
    page_url = urljoin(BASE_URL, start_path)

    while page_url:
        response = requests.get(page_url, timeout=10)
        response.encoding = "utf-8"  # books.toscrape.com sometimes gets mis-detected as latin-1,
                                      # which turns "£" into "Ã‚£" (mojibake) in response.text
        soup = BeautifulSoup(response.text, "html.parser")

        for article in soup.select("article.product_pod"):
            title = article.h3.a["title"]
            price_text = article.select_one("p.price_color").get_text(strip=True)

            # star rating isn't in any text -- it's a CSS class like "star-rating Three"
            rating_tag = article.select_one("p.star-rating")
            rating_word = None
            for css_class in rating_tag.get("class", []):
                if css_class in RATING_WORDS:
                    rating_word = css_class

            availability_text = article.select_one("p.instock.availability").get_text(strip=True)

            all_books.append({
                "title": title,
                "price": price_text,
                "star_rating": rating_word,
                "availability": availability_text,
                "category": category_name
            })

        next_link = soup.select_one("li.next a")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None
        time.sleep(0.3)

print(f"Scraped {len(all_books)} books")
df = pd.DataFrame(all_books)
df.to_csv("books_raw.csv", index=False)
df