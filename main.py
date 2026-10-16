import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
app = FastAPI()


class QueryRequest(BaseModel):
    prompt: str


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Class 12 NCERT Physics AI Tutor</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-slate-900 text-slate-100 h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-indigo-600 text-white p-4 shadow-lg flex items-center justify-between">
        <div>
            <h1 class="text-xl font-bold">⚡ Class 12 NCERT Physics AI Tutor</h1>
            <p class="text-xs text-indigo-200">Derivations, Numericals & Concepts Made Easy</p>
        </div>
        <span class="text-xs bg-indigo-500 px-3 py-1 rounded-full font-medium">CBSE / NCERT</span>
    </header>

    <!-- Quick Topic Pills -->
    <div class="bg-slate-800 border-b border-slate-700 p-2.5 flex gap-2 overflow-x-auto whitespace-nowrap px-4 shadow-inner">
        <button onclick="askPreset('Explain Gauss Law and its applications')" class="text-xs bg-slate-700 hover:bg-indigo-600 px-3 py-1.5 rounded-lg transition-colors cursor-pointer">📐 Gauss's Law</button>
        <button onclick="askPreset('Derive Lens Maker Formula step by step')" class="text-xs bg-slate-700 hover:bg-indigo-600 px-3 py-1.5 rounded-lg transition-colors cursor-pointer">🔍 Lens Maker Formula</button>
        <button onclick="askPreset('Explain Electromagnetic Induction and Faraday Laws')" class="text-xs bg-slate-700 hover:bg-indigo-600 px-3 py-1.5 rounded-lg transition-colors cursor-pointer">🧲 Faraday's Laws</button>
        <button onclick="askPreset('Explain Bohr Model postulates and hydrogen spectrum frequency')" class="text-xs bg-slate-700 hover:bg-indigo-600 px-3 py-1.5 rounded-lg transition-colors cursor-pointer">⚛️ Bohr's Atomic Model</button>
        <button onclick="askPreset('What is PN Junction Diode and half wave rectification?')" class="text-xs bg-slate-700 hover:bg-indigo-600 px-3 py-1.5 rounded-lg transition-colors cursor-pointer">🔌 PN Junction Diode</button>
    </div>

    <!-- Chat Container -->
    <main id="chat-box" class="flex-1 overflow-y-auto p-4 max-w-3xl w-full mx-auto space-y-4">
        <div class="flex items-start space-x-2">
            <div class="bg-indigo-900 border border-indigo-700 text-indigo-100 p-4 rounded-2xl max-w-[85%] text-sm shadow-md leading-relaxed">
                Namaste! 🙏 I am your Class 12 NCERT Physics Expert. Ask me any physics question, numerical problem, or derivation (e.g., Electric Flux, Ray Optics, Wave Optics, Current Electricity, Atoms & Nuclei), and I will provide clean, step-by-step textbook-style solutions!
            </div>
        </div>
    </main>

    <!-- Input Box -->
    <footer class="bg-slate-800 border-t border-slate-700 p-4 shadow-xl">
        <form id="chat-form" class="max-w-3xl mx-auto flex gap-2">
            <input 
                type="text" 
                id="user-input" 
                placeholder="Ask a physics question or numerical problem..." 
                class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-slate-100 placeholder-slate-500"
                autocomplete="off"
                required
            >
            <button 
                type="submit" 
                class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-medium text-sm transition-colors shadow-md">
                Solve
            </button>
        </form>
    </footer>

    <script>
        const chatBox = document.getElementById('chat-box');
        const chatForm = document.getElementById('chat-form');
        const userInput = document.getElementById('user-input');

        function askPreset(topic) {
            userInput.value = topic;
            chatForm.dispatchEvent(new Event('submit'));
        }

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = userInput.value.trim();
            if (!text) return;

            // Append User Message
            chatBox.innerHTML += `
                <div class="flex justify-end">
                    <div class="bg-indigo-600 text-white p-3.5 rounded-2xl max-w-[80%] text-sm shadow-md">
                        ${escapeHtml(text)}
                    </div>
                </div>`;
            userInput.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            // Loading state
            const loadingId = 'loading-' + Date.now();
            chatBox.innerHTML += `
                <div id="${loadingId}" class="flex items-start space-x-2">
                    <div class="bg-slate-800 border border-slate-700 text-indigo-300 p-3.5 rounded-2xl text-sm animate-pulse">
                        Solving step-by-step according to NCERT guidelines... 📚
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
                            <div class="bg-slate-800 border border-slate-700 text-slate-200 p-4 rounded-2xl max-w-[90%] text-sm shadow-md whitespace-pre-wrap leading-relaxed">
                                ${escapeHtml(data.response)}
                            </div>
                        </div>`;
                } else {
                    chatBox.innerHTML += `
                        <div class="flex items-start space-x-2">
                            <div class="bg-red-900 border border-red-700 text-red-200 p-3.5 rounded-2xl text-sm">
                                Error: ${data.detail || 'Something went wrong.'}
                            </div>
                        </div>`;
                }
            } catch (err) {
                document.getElementById(loadingId).remove();
                chatBox.innerHTML += `
                    <div class="flex items-start space-x-2">
                        <div class="bg-red-900 border border-red-700 text-red-200 p-3.5 rounded-2xl text-sm">
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
    if not client:
        raise HTTPException(status_code=500, detail="Groq client not initialized.")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Class 12 NCERT Physics tutor and professor. "
                        "Your job is to provide accurate, clear, and structured explanations, derivations, "
                        "and numerical solutions strictly aligned with the CBSE Class 12 NCERT Physics syllabus. "
                        "Use clear headings, list formulas clearly, show step-by-step derivations with physical reasoning, "
                        "and solve numerical problems with proper given values, formulas, calculations, and SI units."
                    )
                },
                {"role": "user", "content": req.prompt}
            ],
            max_tokens=1500
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))