# MyIndiaShop AI

A Flask shopping comparison assistant. The browser posts product searches to the /api/search endpoint; the server fetches results with Serper and summarizes them with Groq.

## Local setup

1. Use Python 3.10–3.13.
2. Create and activate a virtual environment.
3. Install dependencies with pip install -r requirements.txt.
4. Copy .env.example to .env and add SERPER_API_KEY and GROQ_API_KEY. Never commit .env.
5. Run python app.py and open http://127.0.0.1:5000.

GROQ_MODEL is optional and defaults to openai/gpt-oss-20b. PORT defaults to 5000; FLASK_DEBUG defaults to false; LOG_LEVEL defaults to INFO.

The endpoint accepts a free-form product name and optional category: groceries, electronics, fashion, household, or all. Categories add search hints without restricting product names.

## AIC Cloud

Connect this GitHub repository and choose the intended branch in AIC Cloud. Add SERPER_API_KEY and GROQ_API_KEY in the dashboard environment settings; optionally set GROQ_MODEL. Do not put API keys in Git. Python app hosting supports Python 3.10–3.13 and Gunicorn. If a start command is requested, use gunicorn --bind 0.0.0.0:$PORT app:app. The app uses the platform-provided PORT and keeps Flask debug off unless FLASK_DEBUG=true. Check app health in the dashboard after deployment.

## Other deployment configuration

Procfile and render.yaml target the Flask WSGI app with Gunicorn. render.yaml is for Render and is not required by AIC Cloud. The built-in Flask server is for local development only.
