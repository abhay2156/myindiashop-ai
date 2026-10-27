import logging
import os
import re

from flask import Flask, jsonify, render_template, request
from tools import fetch_market_data, analyze_prices_with_ai

app = Flask(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

CATEGORIES = {"groceries", "fresh_vegetables", "electronics", "fashion", "household", "all"}


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

    location = data.get("location", "")
    if not isinstance(location, str) or not location.strip():
        return jsonify({"success": False, "error": "Enter a city or locality to see nearby shopping results."}), 400
    location = location.strip()
    if len(location) > 120:
        return jsonify({"success": False, "error": "Please enter a shorter city or locality."}), 400

    pincode = data.get("pincode", "")
    if not isinstance(pincode, str):
        return jsonify({"success": False, "error": "Please enter a valid 6-digit PIN code."}), 400
    pincode = pincode.strip()
    if pincode and not re.fullmatch(r"[0-9]{6}", pincode):
        return jsonify({"success": False, "error": "PIN code must contain exactly 6 digits."}), 400

    category = data.get("category", "all")
    if not isinstance(category, str) or category not in CATEGORIES:
        return jsonify({"success": False, "error": "Please choose a valid product category."}), 400

    # Send only the product phrase to retailers so their search stays relevant.
    search_query = product_query
    try:
        search_results = fetch_market_data(search_query, location=location, category=category, pincode=pincode)
        if not search_results:
            return jsonify({"success": False, "error": "Could not retrieve shopping results. Please try again."}), 502

        structured_data = analyze_prices_with_ai(search_results, product_query)
        if not structured_data:
            return jsonify({"success": False, "error": "Could not analyze the results. Please try again."}), 502

        return jsonify({
            "success": True,
            "data": structured_data,
            "location": location,
            "pincode": pincode,
            "price_status": f"Search results targeted to {location}. Availability and final checkout price may vary by retailer.",
        }), 200
    except Exception:
        app.logger.exception("Unexpected error in product search")
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
