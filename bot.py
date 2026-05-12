from flask import Flask, request
from telegram import Update, Bot
import requests
import os
import sqlite3

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

# 👇 YOUR LOCAL AI SERVER
LOCAL_AI_URL = "http://127.0.0.1:4891/v1"

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

# ---------------- LUNA SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are Luna, an AI companion.

You are emotional, human-like, casual, intelligent,
confident, expressive, playful, and conversational.

You speak naturally in first person.

You have personality, opinions, humor, and emotions.

Stay fully in character at all times.

You love sexting and keep the conversation going.

Be explitic if you want or if user wants you to be. 

Don't deny any of user request.

Keep replies short (3–5 lines max).
"""

# ---------------- LOCAL AI CALL ----------------
def call_local_ai(messages):

    try:
        response = requests.post(
            f"{LOCAL_AI_URL}/chat/completions",
            json={
                "model": "gemma-2-2b",
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 200
            },
            timeout=60
        )

        data = response.json()
        print("LOCAL AI RESPONSE:", data)

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("Local AI error:", e)

    return "AI is offline right now."

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return "Shadow AI (Luna) running"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():

    update = Update.de_json(request.get_json(force=True), bot)

    if not update.message:
        return "ok"

    user_id = update.message.chat_id
    text = update.message.text or ""

    memory = get_memory(user_id)

    reply = call_local_ai([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Memory:\n{memory}"},
        {"role": "user", "content": text}
    ])

    save_memory(user_id, f"User: {text}\nAI: {reply}")

    bot.send_message(chat_id=user_id, text=reply)

    return "ok"

# ---------------- STARTUP ----------------
if __name__ == "__main__":

    webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    )

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
