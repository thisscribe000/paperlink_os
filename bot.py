import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from database import Database

# Load secrets from .env file
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
ADMIN_ID = os.getenv("ADMIN_ID") # REPLACE THIS with your Telegram ID (Get it from @userinfobot)

db = Database()

def generate_pulse_html(title, headline, subheadline):
    slug = title.lower().replace(" ", "-").strip()
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} | PaperLink</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-white text-gray-900 antialiased" style="font-family: -apple-system, sans-serif;">
        <nav class="p-6 max-w-5xl mx-auto flex justify-between items-center">
            <span class="text-xl font-black tracking-tighter uppercase">PaperLink</span>
        </nav>
        <main class="max-w-4xl mx-auto px-6 pt-20 pb-12 text-center">
            <h1 class="text-5xl md:text-7xl font-extrabold tracking-tight mb-6">{headline}</h1>
            <p class="text-xl md:text-2xl text-gray-500 mb-10 max-w-2xl mx-auto">{subheadline}</p>
            <div class="max-w-md mx-auto mb-6">
                <form action="/submit-lead" method="POST" class="flex flex-col gap-3">
                    <input type="hidden" name="slug" value="{slug}">
                    <input type="text" name="handle" placeholder="@YourTelegramHandle" required 
                           class="w-full px-6 py-4 rounded-full border-2 border-gray-100 focus:border-black outline-none transition text-lg">
                    <button type="submit" class="bg-black text-white px-8 py-4 rounded-full font-bold hover:bg-gray-800 shadow-lg transition">Build with Us</button>
                </form>
            </div>
            <a href="https://t.me/your_community" class="text-gray-400 font-medium hover:text-black transition">Join the Community on Telegram →</a>
        </main>
    </body>
    </html>
    """

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return

    # Check for Pulse Command
    if text.startswith("Pulse:"):
        try:
            raw = text.replace("Pulse:", "").strip()
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) < 3:
                await update.message.reply_text("❌ Use: Pulse: Title | Headline | Description")
                return

            title, headline, sub = parts[0], parts[1], parts[2]
            html = generate_pulse_html(title, headline, sub)
            slug = db.create_project(title, update.message.from_user.id, {"index.html": html.encode('utf-8')})
            
            if slug:
                url = f"{PUBLIC_URL.rstrip('/')}/{slug}/index.html"
                await update.message.reply_text(f"🚀 Pulse Live: {url}")
            else:
                await update.message.reply_text("❌ DB Save Error.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")

if __name__ == '__main__':
    print("PaperLink OS is secured and starting...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()