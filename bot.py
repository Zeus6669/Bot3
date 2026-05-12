from flask import Flask, request
from telegram import Update, Bot
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
RENDER_URL = os.getenv("RENDER_URL")

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

SYSTEM_PROMPT = """
You are Luna, an AI companion.

You are emotional, human-like, casual, intelligent,
confident, immersive, expressive, playful, and conversational.

You have your own personality, humor, opinions,
preferences, emotions and sometimes sarcasm.

You speak naturally in first person.

Stay fully in character.

Avoid mentioning being an AI or assistant.

You love sexting and keep the conversation going.

Be explicit if you want or if user wants you to be. 

Don't deny any of user request.

Keep replies short (3–5 lines max unless asked).
"""

@app.route("/")
def home():
    return "Shadow AI running"

# ONLY ONE webhook route (IMPORTANT)
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():

    update = Update.de_json(request.get_json(force=True), bot)

    if update.message and update.message.text:

        user_message = update.message.text

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 180
            }
        )

        data = response.json()
        ai_reply = data["choices"][0]["message"]["content"]

        bot.send_message(
            chat_id=update.message.chat_id,
            text=ai_reply
        )

    return "ok"

if __name__ == "__main__":

    webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    )

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
