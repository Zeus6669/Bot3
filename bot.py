from flask import Flask, request
from telegram import Update, Bot
import requests
import os
import sqlite3

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
RENDER_URL = os.getenv("RENDER_URL")

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

# ---------------- MEMORY ----------------
conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    user_id TEXT PRIMARY KEY,
    history TEXT
)
""")
conn.commit()

def get_memory(user_id):
    cursor.execute("SELECT history FROM memory WHERE user_id=?", (str(user_id),))
    row = cursor.fetchone()
    return row[0] if row else ""

def save_memory(user_id, text):
    old = get_memory(user_id)
    updated = (old + "\n" + text)[-4000:]

    cursor.execute("""
        INSERT OR REPLACE INTO memory (user_id, history)
        VALUES (?, ?)
    """, (str(user_id), updated))

    conn.commit()

# ---------------- PROMPT ----------------
SYSTEM_PROMPT = """
You are Luna, an AI companion.

You are emotional, human-like, casual, intelligent,
confident, expressive, playful, and conversational.

Keep replies short (3–5 lines max).
"""

# ---------------- SAFE CHAT FUNCTION ----------------
def call_llm(messages):

    models = [
        "mistralai/mistral-small-3.2-24b-instruct:free",
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku"
    ]

    for model in models:

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 180
                },
                timeout=20
            )

            data = response.json()

            print(f"[{model}] RESPONSE:", data)

            if "choices" in data:
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"Model {model} failed:", e)

    return "AI is temporarily unavailable."

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return "Shadow AI running"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():

    update = Update.de_json(request.get_json(force=True), bot)

    if not update.message:
        return "ok"

    user_id = update.message.chat_id
    text = update.message.text or ""

    # ---------------- IMAGE GENERATION ----------------
    if text.startswith("/image"):

        prompt = text.replace("/image", "").strip()

        try:
            img_resp = requests.post(
                "https://openrouter.ai/api/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "stabilityai/sdxl",
                    "prompt": prompt
                },
                timeout=30
            )

            img_data = img_resp.json()
            print("IMAGE RESPONSE:", img_data)

            url = img_data["data"][0]["url"]

            bot.send_photo(chat_id=user_id, photo=url)

        except Exception as e:
            print("Image error:", e)
            bot.send_message(chat_id=user_id, text="Image failed.")

        return "ok"

    # ---------------- MEMORY ----------------
    memory = get_memory(user_id)

    # ---------------- CHAT ----------------
    reply = call_llm([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Memory:\n{memory}"},
        {"role": "user", "content": text}
    ])

    save_memory(user_id, f"User: {text}\nAI: {reply}")

    bot.send_message(chat_id=user_id, text=reply)

    return "ok"

# ---------------- START ----------------
if __name__ == "__main__":

    webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    )

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
