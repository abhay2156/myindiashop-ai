from flask import Flask, render_template, request, jsonify
from tools import fetch_market_data, analyze_prices_with_ai

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search_api():
    """API endpoint for Dynamic Data Binding (AJAX/Fetch requests)."""
    data = request.get_json() or {}
    product_query = data.get('query', '').strip()

    if not product_query:
        return jsonify({"success": False, "error": "Please enter a product query."}), 400

    search_results = fetch_market_data(product_query)
    if not search_results:
        return jsonify({"success": False, "error": "Failed to retrieve market data."}), 500

    structured_data = analyze_prices_with_ai(search_results, product_query)
    if not structured_data:
        return jsonify({"success": False, "error": "Failed to parse deals with AI."}), 500

    return jsonify({"success": True, "data": structured_data})


if __name__ == '__main__':
    app.run(debug=True, port=5000)