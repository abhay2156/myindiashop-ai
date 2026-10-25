"""Compatibility entry point for AIC Cloud's Python launcher.

The deployed product is MyIndiaShop, defined as a Flask app in app.py.
AIC Cloud currently invokes `python main.py`, so this file runs that app.
"""
import os

from app import app


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
