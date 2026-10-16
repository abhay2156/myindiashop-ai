import os
import json
import traceback
import requests
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

# Explicitly find and load the .env file from the project root
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def fetch_market_data(product_query):
    """Fetches live search results for Indian retail stores via Serper API."""
    url = "https://google.serper.dev/search"

    if not SERPER_API_KEY:
        print("ERROR: SERPER_API_KEY is missing!")
        return None

    payload = json.dumps({
        "q": f"{product_query} price buy online India Amazon Flipkart Croma Reliance Digital",
        "gl": "in",
        "hl": "en",
        "num": 10
    })

    headers = {
        'X-API-KEY': SERPER_API_KEY.strip(),
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching search data: {e}")
        traceback.print_exc()
        return None


def analyze_prices_with_ai(search_results, product_query):
    """Uses Groq LLM to dynamically construct structured product & store deal data."""
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is missing!")
        return None

    client = Groq(api_key=GROQ_API_KEY.strip())

    prompt = f"""
    You are 'MyIndiaShop AI' / 'TolMolKe', an intelligent market price aggregator for India.
    Analyze the raw organic search data provided below for the search: '{product_query}'.

    Construct a structured JSON response following this EXACT JSON schema:
    {{
      "product_name": "{product_query}",
      "best_recommendation": "A short, crisp 1-2 sentence recommendation on where to get the best deal.",
      "comparisons": [
        {{
          "platform": "Platform Name (e.g., Amazon India, Flipkart, Croma, Reliance Digital)",
          "price": "Price in INR (e.g. ₹69,900)",
          "link": "Direct link from search results or homepage",
          "remarks": "Brief stock state, discount, or payment benefit"
        }}
      ],
      "buying_tips": [
        "Tip 1 regarding credit card discounts or exchange offers",
        "Tip 2 regarding warranty, trade-in, or refurbished deals"
      ]
    }}

    Raw Search Data:
    {json.dumps(search_results)}
    """

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",  # Using the primary versatile Groq model
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error executing Groq AI Data Binding: {e}")
        traceback.print_exc()
        return None
