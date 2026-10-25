# MyIndiaShop AI

A Flask shopping comparison app. The browser posts product searches to `/api/search`; the server resolves the requested Indian city or locality to coordinates and fetches live offers from QuickCommerce API for Amazon, Flipkart, BigBasket, Blinkit, and Zepto. Groq can add general buying tips, but it does not create prices or listings.

## Local setup

1. Use Python 3.10–3.13.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set `QUICKCOMMERCE_API_KEY`. Set `GROQ_API_KEY` only if you want optional buying tips. Never commit `.env`.
5. Run `python app.py` and open http://127.0.0.1:5000.

The search accepts a free-form product name and optional category: groceries, electronics, fashion, household, or all. Categories add search hints without restricting product names. The QuickCommerce group search charges one credit per retailer requested, so the five selected retailers use five credits per search.

`GROQ_MODEL` is optional and defaults to `openai/gpt-oss-20b`. `PORT` defaults to 5000; `FLASK_DEBUG` defaults to false; `LOG_LEVEL` defaults to INFO.

## AIC Cloud

Connect this GitHub repository and choose the intended branch in AIC Cloud. Add `QUICKCOMMERCE_API_KEY` in the dashboard environment settings. Optionally set `GROQ_API_KEY` and `GROQ_MODEL` for buying tips. Do not put API keys in Git. Python app hosting supports Python 3.10–3.13 and Gunicorn. If a start command is requested, use `gunicorn --bind 0.0.0.0:$PORT app:app`. The app uses the platform-provided `PORT` and keeps Flask debug off unless `FLASK_DEBUG=true`. Check app health in the dashboard after deployment.

## Other deployment configuration

`Procfile` and `render.yaml` target the Flask WSGI app with Gunicorn. `render.yaml` is for Render and is not required by AIC Cloud.
