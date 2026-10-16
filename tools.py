import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parent / ".env")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
logger = logging.getLogger(__name__)


def fetch_market_data(product_query, location=None):
    """Fetch Google Shopping listings targeted to the requested locality."""
    if not SERPER_API_KEY:
        logger.error("SERPER_API_KEY is not configured")
        return None
    payload = {"q": f"{product_query} price India", "gl": "in", "hl": "en", "num": 20}
    if location:
        location_parts = [part.strip() for part in location.split(",")]
        if location_parts[-1].casefold() != "india":
            location_parts.append("India")
        payload["location"] = ", ".join(location_parts)
    try:
        response = requests.post(
            "https://google.serper.dev/shopping",
            headers={"X-API-KEY": SERPER_API_KEY.strip(), "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return None
        data["shopping"] = data.get("shopping") or []
        return data
    except requests.RequestException:
        logger.exception("Shopping search provider request failed")
        return None
    except ValueError:
        logger.exception("Shopping search provider returned invalid JSON")
        return None


def _valid_http_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value

def _retailer_product_url(item, title, source):
    """Prefer a direct product URL; replace Google Shopping links with retailer search URLs."""
    for key in ("productLink", "product_link", "url"):
        direct = _valid_http_url(item.get(key))
        if direct:
            return direct

    provider_link = _valid_http_url(item.get("link"))
    if not provider_link:
        return None
    host = (urlparse(provider_link).hostname or "").lower()
    if not (host == "google.com" or host.endswith(".google.com") or host == "google.co.in" or host.endswith(".google.co.in")):
        return provider_link

    query = quote_plus(str(title or "").strip())
    retailer = str(source or "").casefold()
    if "bigbasket" in retailer:
        return f"https://www.bigbasket.com/ps/?q={query}"
    if "flipkart" in retailer:
        return f"https://www.flipkart.com/search?q={query}"
    if "amazon" in retailer:
        return f"https://www.amazon.in/s?k={query}"
    retailer_search_urls = {
        "jiomart": f"https://www.jiomart.com/products?q={query}",
        "zepto": f"https://www.zepto.com/search?query={query}",
        "blinkit": f"https://blinkit.com/s/?q={query}",
        "myntra": f"https://www.myntra.com/search/{query}",
        "ajio": f"https://www.ajio.com/search/?text={query}",
        "croma": f"https://www.croma.com/search/?text={query}",
        "reliance digital": f"https://www.reliancedigital.in/search?q={query}",
        "nykaa": f"https://www.nykaa.com/search/result/?q={query}",
        "tata cliq": f"https://www.tatacliq.com/search/?searchCategory=all&text={query}",
        "meesho": f"https://www.meesho.com/search?q={query}",
        "snapdeal": f"https://www.snapdeal.com/search?keyword={query}",
        "starquik": f"https://www.starquik.com/search?q={query}",
    }
    for retailer_name, search_url in retailer_search_urls.items():
        if retailer_name in retailer:
            return search_url
    return provider_link


def _provider_offers(search_results):
    """Keep only offers with an explicit title, price, seller, and safe link."""
    offers = []
    for item in search_results.get("shopping", []):
        if not isinstance(item, dict):
            continue
        title, price, source = item.get("title"), item.get("price"), item.get("source")
        link = _retailer_product_url(item, title, source)
        
        if not all(isinstance(value, str) and value.strip() for value in (title, price, source)) or not link:
            continue
        offer = {"title": title.strip(), "platform": source.strip(), "price": price.strip(), "link": link}
        delivery = item.get("delivery")
        if isinstance(delivery, str) and delivery.strip():
            offer["delivery"] = delivery.strip()
        rating = item.get("rating")
        if isinstance(rating, (int, float)) and 0 <= rating <= 5:
            offer["rating"] = rating
        review_count = item.get("ratingCount") or item.get("reviews")
        if isinstance(review_count, int) and review_count >= 0:
            offer["review_count"] = review_count
        offers.append(offer)
    return offers


def _ai_shopping_guidance(product_query, offers):
    """Use Groq for cautious general guidance, never to create offer facts."""
    if not GROQ_API_KEY:
        return []
    client = Groq(api_key=GROQ_API_KEY.strip())
    safe_items = [{"title": item["title"], "seller": item["platform"]} for item in offers[:10]]
    prompt = (
        "Give up to two concise shopping checks for this product query. "
        "Do not state or infer prices, discounts, stock, delivery promises, "
        "seller policies, or product specifications. Do not recommend a seller. "
        "Use general checks such as matching pack size/model/size and confirming "
        "the final delivered price. Return JSON with one key, buying_tips, an array of strings. "
        f"Query: {product_query}. Listings: {json.dumps(safe_items, ensure_ascii=False)}"
    )
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=180,
        )
        result = json.loads(completion.choices[0].message.content)
        tips = result.get("buying_tips", [])
        if not isinstance(tips, list):
            return []
        return [tip.strip() for tip in tips[:2] if isinstance(tip, str) and tip.strip()]
    except Exception:
        logger.exception("Groq guidance unavailable; returning provider data without AI tips")
        return []


def analyze_prices_with_ai(search_results, product_query):
    """Return provider-grounded offers; Groq may add general checks only."""
    if not isinstance(search_results, dict):
        return None
    offers = _provider_offers(search_results)
    comparisons = []
    for offer in offers:
        remarks = offer.get("delivery", "")
        if offer.get("rating") is not None:
            rating_note = f"Rated {offer['rating']}/5"
            if offer.get("review_count"):
                rating_note += f" from {offer['review_count']} ratings"
            remarks = f"{remarks} · {rating_note}" if remarks else rating_note
        comparisons.append({
            "title": offer["title"],
            "platform": offer["platform"],
            "price": offer["price"],
            "link": offer["link"],
            "remarks": remarks,
            "rating": offer.get("rating"),
            "review_count": offer.get("review_count"),
        })
    if comparisons:
        recommendation = (
            f"Found {len(comparisons)} shopping listings for {product_query}. "
            "Match the exact product or pack size, then confirm delivery and final price with the retailer."
        )
    else:
        recommendation = (
            "No listings with a verifiable displayed price and retailer link were found. "
            "Try adding a brand, model, or pack size."
        )
    return {
        "product_name": product_query,
        "best_recommendation": recommendation,
        "comparisons": comparisons,
        "buying_tips": _ai_shopping_guidance(product_query, offers),
    }
