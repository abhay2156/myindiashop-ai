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


# Unified HTML UI embedded directly to avoid file-path issues on cloud servers
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MyIndiaShop AI - Price Comparison Assistant</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-slate-50 h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-indigo-600 text-white p-4 shadow-md flex items-center justify-between">
        <h1 class="text-xl font-bold">🇮🇳 MyIndiaShop AI Assistant</h1>
        <span class="text-xs bg-indigo-500 px-2.5 py-1 rounded-full">Live Comparison</span>
    </header>

    <!-- Chat Container -->
    <main id="chat-box" class="flex-1 overflow-y-auto p-4 max-w-2xl w-full mx-auto space-y-4">
        <div class="flex items-start space-x-2">
            <div class="bg-indigo-100 text-indigo-900 p-3 rounded-2xl max-w-[80%] text-sm shadow-sm">
                Namaste! 🙏 I am your Indian e-commerce shopping and price comparison assistant. What product are you looking to buy today (e.g., smartphones, pressure cookers, running shoes)?
            </div>
        </div>
    </main>

    <!-- Input Box -->
    <footer class="bg-white border-t border-slate-200 p-4 shadow-lg">
        <form id="chat-form" class="max-w-2xl mx-auto flex gap-2">
            <input 
                type="text" 
                id="user-input" 
                placeholder="Ask about prices, products, or deals..." 
                class="flex-1 border border-slate-300 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                autocomplete="off"
                required
            >
            <button 
                type="submit" 
                class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-xl font-medium text-sm transition-colors shadow-sm">
                Send
            </button>
        </form>
    </footer>

    <script>
        const chatBox = document.getElementById('chat-box');
        const chatForm = document.getElementById('chat-form');
        const userInput = document.getElementById('user-input');

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = userInput.value.trim();
            if (!text) return;

            // Append User Message
            chatBox.innerHTML += `
                <div class="flex justify-end">
                    <div class="bg-indigo-600 text-white p-3 rounded-2xl max-w-[80%] text-sm shadow-sm">
                        ${escapeHtml(text)}
                    </div>
                </div>`;
            userInput.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            // Loading state
            const loadingId = 'loading-' + Date.now();
            chatBox.innerHTML += `
                <div id="${loadingId}" class="flex items-start space-x-2">
                    <div class="bg-slate-200 text-slate-600 p-3 rounded-2xl text-sm animate-pulse">
                        Searching best prices across India... 🛍️
                    </div>
                </div>`;
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: text })
                });
                const data = await res.json();

                document.getElementById(loadingId).remove();

                if (res.ok) {
                    chatBox.innerHTML += `
                        <div class="flex items-start space-x-2">
                            <div class="bg-white border border-slate-200 text-slate-800 p-3 rounded-2xl max-w-[85%] text-sm shadow-sm whitespace-pre-wrap">
                                ${escapeHtml(data.response)}
                            </div>
                        </div>`;
                } else {
                    chatBox.innerHTML += `
                        <div class="flex items-start space-x-2">
                            <div class="bg-red-100 text-red-700 p-3 rounded-2xl text-sm">
                                Error: ${data.detail || 'Something went wrong.'}
                            </div>
                        </div>`;
                }
            } catch (err) {
                document.getElementById(loadingId).remove();
                chatBox.innerHTML += `
                    <div class="flex items-start space-x-2">
                        <div class="bg-red-100 text-red-700 p-3 rounded-2xl text-sm">
                            Network error. Please try again.
                        </div>
                    </div>`;
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        });

        function escapeHtml(text) {
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT

@app.post("/chat")
def chat_with_agent(req: QueryRequest):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are MyIndiaShop AI, a friendly and expert e-commerce comparison assistant "
                        "specialized in the Indian market (Flipkart, Amazon India, Myntra, Croma, etc.). "
                        "Help users find the best deals, compare product prices, features, and provide practical shopping advice."
                    )
                },
                {"role": "user", "content": req.prompt}
            ]
        )
        answer = completion.choices[0].message.content
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
