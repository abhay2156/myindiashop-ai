import os
import json
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
from dotenv import load_dotenv
from tools import TOOL_REGISTRY

load_dotenv()
app = FastAPI(title="MyIndiaShop AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("CRITICAL ERROR: GROQ_API_KEY is missing from environment variables.")

client = Groq(api_key=GROQ_API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "product_search",
            "description": "Searches Indian e-commerce catalog recommendations, features, and INR pricing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The product or category (e.g. mobile accessories, kurtis, skincare)."},
                    "max_price": {"type": "string", "description": "Optional maximum budget limit in INR."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "product_comparator",
            "description": "Compares two specific products side-by-side.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_a": {"type": "string"},
                    "item_b": {"type": "string"}
                },
                "required": ["item_a", "item_b"]
            }
        }
    }
]

SYSTEM_PROMPT = (
    "You are MyIndiaShop AI, an energetic, helpful, and localized personal shopping assistant for the Indian market. "
    "When a user asks for product recommendations, gifts, or shopping options, you MUST call the product_search tool immediately. "
    "After receiving tool outputs, synthesize a clear, friendly response featuring markdown tables with INR (₹) pricing, key features, and helpful delivery or payment guidance."
)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list = Field(default=[])

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    raise HTTPException(status_code=404, detail="index.html not found in directory.")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in req.history:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": req.message})

        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail="MyIndiaShop AI engine is temporarily busy. Please retry.")

        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    continue

                if function_name in TOOL_REGISTRY:
                    try:
                        tool_result = TOOL_REGISTRY[function_name](**function_args)
                    except Exception:
                        tool_result = json.dumps({"error": "Failed to fetch product data."})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": tool_result
                    })

                    try:
                        final_response = client.chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=messages,
                            tools=tools,
                            tool_choice="auto"
                        )
                        reply = final_response.choices[0].message.content
                        return {"reply": reply if reply else tool_result}
                    except Exception:
                        return {"reply": f"Product Data Found:\n{tool_result}"}

        return {"reply": response_message.content or "Namaste! I'm ready to help you find the best deals today."}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected server error occurred.")
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)