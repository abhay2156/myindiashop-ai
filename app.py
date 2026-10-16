import logging
import os

from flask import Flask, jsonify, render_template, request
from tools import fetch_market_data, analyze_prices_with_ai

app = Flask(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

CATEGORY_HINTS = {
    "groceries": "groceries food pantry",
    "electronics": "electronics gadget",
    "fashion": "fashion clothing apparel",
    "household": "household essentials home cleaning",
    "all": "",
}


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search_api():
    """Search for a product and return structured comparison results."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Please send a valid JSON request."}), 400

    product_query = data.get("query", "")
    if not isinstance(product_query, str) or not product_query.strip():
        return jsonify({"success": False, "error": "Please enter a product name."}), 400
    product_query = product_query.strip()

    category = data.get("category", "all")
    if not isinstance(category, str) or category not in CATEGORY_HINTS:
        return jsonify({"success": False, "error": "Please choose a valid product category."}), 400

    category_hint = CATEGORY_HINTS[category]
    search_query = f"{category_hint} {product_query}".strip()
    try:
        search_results = fetch_market_data(search_query)
        if not search_results:
            return jsonify({"success": False, "error": "Could not retrieve shopping results. Please try again."}), 502

        structured_data = analyze_prices_with_ai(search_results, product_query)
        if not structured_data:
            return jsonify({"success": False, "error": "Could not analyze the results. Please try again."}), 502

        return jsonify({
            "success": True,
            "data": structured_data,
            "price_status": "Prices come from search results and may change. Verify the final price on the retailer's website.",
        }), 200
    except Exception:
        app.logger.exception("Unexpected error in product search")
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
