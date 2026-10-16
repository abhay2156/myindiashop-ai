import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("CRITICAL ERROR: GROQ_API_KEY is missing from environment variables.")

client = Groq(api_key=GROQ_API_KEY)
app = FastAPI()

class QueryRequest(BaseModel):
    prompt: str

@app.get("/", response_class=HTMLResponse)
def home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>MyIndiaShop AI E-Commerce Assistant is online!</h1>"

@app.post("/chat")
def chat_with_agent(req: QueryRequest):
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Active, fast production model
            messages=[
                {
                    {
                    "role": "system",
                    "content": "You are MyIndiaShop AI, an expert e-commerce comparison assistant for India."
                },
                {"role": "user", "content": req.prompt}
                },
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        answer = completion.choices[0].message.content
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))