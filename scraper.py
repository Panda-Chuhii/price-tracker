import requests
from bs4 import BeautifulSoup
import re
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def clean_price(text):
    digits = re.sub(r'[^\d.]', '', text)
    if digits:
        return float(digits)
    return None

def get_image_from_search(product_name):
    try:
        query = requests.utils.quote(product_name)
        response = requests.get(
            f"https://api.duckduckgo.com/?q={query}&format=json&pretty=1",
            headers=HEADERS,
            timeout=5
        )
        data = response.json()
        if data.get("Image"):
            return data["Image"]
    except Exception:
        pass
    return None

def scrape_product(url, retries=3):
    result = {"price": None, "image_url": None}

    for attempt in range(retries):
        try:
            time.sleep(random.uniform(1, 3))

            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_extra_http_headers(HEADERS)
                    page.goto(url, timeout=20000)
                    page.wait_for_timeout(3000)
                    html = page.content()
                    browser.close()
            except Exception:
                session = requests.Session()
                session.headers.update(HEADERS)
                response = session.get(url, timeout=15)
                html = response.text

            soup = BeautifulSoup(html, "html.parser")

            # Amazon India
            for selector in [".a-price-whole", ".priceToPay .a-price-whole",
                             "#priceblock_ourprice", "#priceblock_dealprice",
                             ".apexPriceToPay .a-price-whole"]:
                tag = soup.select_one(selector)
                if tag:
                    price = clean_price(tag.text)
                    if price and price > 0:
                        result["price"] = price
                        break

            # Flipkart
            if not result["price"]:
                for selector in ["._30jeq3", "._16Jk6d", "._25b18"]:
                    tag = soup.select_one(selector)
                    if tag:
                        price = clean_price(tag.text)
                        if price and price > 0:
                            result["price"] = price
                            break

            # Croma
            if not result["price"]:
                for selector in [".pdp-price", ".crm-product-price",
                                 ".new-price", ".offer-price"]:
                    tag = soup.select_one(selector)
                    if tag:
                        price = clean_price(tag.text)
                        if price and price > 0:
                            result["price"] = price
                            break

            # Myntra
            if not result["price"]:
                for selector in [".pdp-price strong", ".pdp-discount-container .pdp-price",
                                 ".pdp-mrp"]:
                    tag = soup.select_one(selector)
                    if tag:
                        price = clean_price(tag.text)
                        if price and price > 0:
                            result["price"] = price
                            break

            # Nykaa
            if not result["price"]:
                for selector in [".post-card__content-price", ".price-container",
                                 "span.price"]:
                    tag = soup.select_one(selector)
                    if tag:
                        price = clean_price(tag.text)
                        if price and price > 0:
                            result["price"] = price
                            break

            # Snapdeal
            if not result["price"]:
                for selector in ["#selling-price-id", ".payBlkBig",
                                 "span.lfloat.product-price"]:
                    tag = soup.select_one(selector)
                    if tag:
                        price = clean_price(tag.text)
                        if price and price > 0:
                            result["price"] = price
                            break

            # Generic fallback
            if not result["price"]:
                for el in soup.find_all(class_=lambda c: c and "price" in c.lower()):
                    price = clean_price(el.get_text(strip=True))
                    if price and 100 < price < 10000000:
                        result["price"] = price
                        break

            # Try meta og:image first
            meta = soup.select_one('meta[property="og:image"]')
            if meta and meta.get("content"):
                result["image_url"] = meta["content"]

            # Amazon specific
            if not result["image_url"]:
                img = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
                if img:
                    result["image_url"] = img.get("src") or img.get("data-old-hires")
# Flipkart
            if not result["price"]:
                for selector in ["._30jeq3", "._16Jk6d", "._25b18",
                                 "._1psv1zeb9", ".v1zwn21k", ".yRaY8j"]:
                    tag = soup.select_one(selector)
                    if tag:
                        price = clean_price(tag.text)
                        if price and price > 0:
                            result["price"] = price
                            break

            # DuckDuckGo fallback
            if not result["image_url"]:
                title_tag = soup.select_one("title")
                if title_tag:
                    result["image_url"] = get_image_from_search(title_tag.text.strip())

            if result["price"]:
                break

        except Exception as e:
            print(f"[Scraper] Attempt {attempt+1} failed: {e}")
            time.sleep(2)

    return result

def scrape_price(url):
    return scrape_product(url)["price"]