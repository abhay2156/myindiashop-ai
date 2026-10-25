import json
import logging
import os
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parent / ".env")
QUICKCOMMERCE_API_KEY = (
    os.getenv("QUICKCOMMERCE_API_KEY")
    or os.getenv("X_API_KEY")
    or os.getenv("X-API-Key")
    or os.getenv("X-API-KEY")
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
logger = logging.getLogger(__name__)
PLATFORMS = ("Amazon", "Flipkart", "BigBasket", "BlinkIt", "Zepto")
_LOCATION_CACHE = {}


def _valid_http_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _coordinates_for_location(location):
    """Resolve an Indian city/locality to coordinates required by the API."""
    cache_key = location.strip().casefold()
    if cache_key in _LOCATION_CACHE:
        return _LOCATION_CACHE[cache_key]
    search_name = location.strip()
    if "india" not in search_name.casefold():
        search_name = f"{search_name}, India"
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": search_name, "count": 10, "language": "en", "format": "json"},
            headers={"User-Agent": "MyIndiaShop/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("results") if isinstance(data, dict) else None
        if not isinstance(candidates, list):
            return None
        place = next((item for item in candidates if isinstance(item, dict) and str(item.get("country_code", "")).upper() == "IN"), None)
        if not place:
            return None
        coordinates = (float(place["latitude"]), float(place["longitude"]))
        _LOCATION_CACHE[cache_key] = coordinates
        return coordinates
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.exception("Could not resolve the requested shopping location")
        return None


def fetch_market_data(product_query, location=None):
    """Fetch live offers from Amazon, Flipkart, BigBasket, Blinkit, and Zepto."""
    if not QUICKCOMMERCE_API_KEY:
        logger.error("QuickCommerce API key is not configured")
        return None
    if not location:
        return None
    coordinates = _coordinates_for_location(location)
    if not coordinates:
        logger.warning("No India location match found for %r", location)
        return None
    try:
        response = requests.get(
            "https://api.quickcommerceapi.com/v1/groupsearch",
            headers={"X-API-Key": QUICKCOMMERCE_API_KEY.strip()},
            params={
                "q": product_query,
                "lat": coordinates[0],
                "lon": coordinates[1],
                "platforms": ",".join(PLATFORMS),
            },
            timeout=35,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, dict):
            logger.error("QuickCommerce API returned an unexpected search response")
            return None

        offers = []
        for platform in PLATFORMS:
            listings = results.get(platform, [])
            if isinstance(listings, dict):
                listings = listings.get("products", [])
            if not isinstance(listings, list):
                continue
            for item in listings:
                if not isinstance(item, dict) or item.get("available") is False:
                    continue
                title = item.get("name") or item.get("title")
                price_value = item.get("offer_price", item.get("price"))
                if isinstance(price_value, bool) or price_value is None:
                    continue
                price = f"₹{price_value:,.2f}".rstrip("0").rstrip(".") if isinstance(price_value, (int, float)) else str(price_value).strip()
                if not isinstance(title, str) or not title.strip() or not price:
                    continue
                quantity = item.get("quantity")
                if isinstance(quantity, str) and quantity.strip():
                    title = f"{title.strip()} · {quantity.strip()}"
                platform_data = item.get("platform")
                source = platform_data.get("name", platform) if isinstance(platform_data, dict) else platform
                deeplink = _valid_http_url(item.get("deeplink") or item.get("url"))
                fallback_links = {
                    "Amazon": "https://www.amazon.in/s?k=",
                    "Flipkart": "https://www.flipkart.com/search?q=",
                    "BigBasket": "https://www.bigbasket.com/ps/?q=",
                    "BlinkIt": "https://blinkit.com/s/?q=",
                    "Zepto": "https://www.zepto.com/search?query=",
                }
                offer = {
                    "title": title.strip(),
                    "price": price,
                    "source": str(source),
                    "productLink": deeplink or fallback_links[platform] + quote_plus(title.strip()),
                }
                if isinstance(platform_data, dict) and isinstance(platform_data.get("sla"), str):
                    offer["delivery"] = platform_data["sla"]
                if isinstance(item.get("rating"), (int, float)):
                    offer["rating"] = item["rating"]
                count = item.get("rating_count", item.get("ratingCount"))
                if isinstance(count, int) and count >= 0:
                    offer["ratingCount"] = count
                offers.append(offer)
        return {"shopping": offers}
    except requests.RequestException:
        logger.exception("QuickCommerce product search request failed")
        return None
    except ValueError:
        logger.exception("QuickCommerce API returned invalid JSON")
        return None


def _retailer_product_url(item, title, source):
    """Prefer a direct product URL; use the retailer search page as fallback."""
    for key in ("productLink", "product_link", "url"):
        direct = _valid_http_url(item.get(key))
        if direct:
            return direct
    return _valid_http_url(item.get("link"))


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
