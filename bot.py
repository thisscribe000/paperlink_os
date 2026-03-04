import os
import qrcode
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from database import Database

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
ADMIN_ID = os.getenv("ADMIN_ID")
db = Database()

def generate_pulse_html(title, headline, sub, style="midnight"):
    slug = title.lower().replace(" ", "-")
    is_dark = style == "midnight"
    bg, text, sub_t = ("bg-black", "text-white", "text-gray-400") if is_dark else ("bg-white", "text-black", "text-gray-500")
    btn_bg, btn_t = ("bg-white", "text-black") if is_dark else ("bg-black", "text-white")
    input_bg = "bg-gray-900" if is_dark else "bg-gray-50"

    return f"""
    <html>
    <head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="{bg} {text} p-10 font-sans text-center transition-all selection:bg-blue-500">
        <nav class="mb-20 font-black text-xl uppercase tracking-tighter">PaperLink</nav>
        <div class="max-w-4xl mx-auto py-20">
            <h1 class="text-6xl md:text-8xl font-bold mb-6 tracking-tight">{headline}</h1>
            <p class="text-xl md:text-2xl {sub_t} mb-12 max-w-2xl mx-auto">{sub}</p>
            
            <form action="/submit-lead" method="POST" class="max-w-md mx-auto">
                <input type="hidden" name="slug" value="{slug}">
                <input type="text" name="handle" placeholder="Telegram Handle (e.g. pilot_1)" required 
                       class="w-full p-5 {input_bg} border border-gray-800 rounded-full mb-4 outline-none text-center text-lg">
                <button class="w-full {btn_bg} {btn_t} p-5 rounded-full font-bold text-xl hover:scale-105 transition-transform">Collaborate</button>
            </form>
            
            <footer class="mt-40 opacity-30 text-[10px] uppercase tracking-widest font-bold">
                Built in PaperLink | Hosted on Barraos
            </footer>
        </div>
    </body>
    </html>
    """

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID: return
    text = update.message.text
    
    # PULSE COMMAND
    if text and text.startswith("Pulse:"):
        parts = [p.strip() for p in text.replace("Pulse:", "").split("|")]
        style = parts[0].lower() if len(parts) >= 1 else "light"
        title = parts[1] if len(parts) >= 2 else "Untitled"
        head = parts[2] if len(parts) >= 3 else "No Headline"
        sub = parts[3] if len(parts) >= 4 else ""
        
        slug = title.lower().replace(' ', '-')
        html = generate_pulse_html(title, head, sub, style)
        db.create_project(title, update.message.from_user.id, {"index.html": html.encode('utf-8')})
        
        full_url = f"{PUBLIC_URL.rstrip('/')}/{slug}/index.html"
        
        # QR Code Engine
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(full_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_filename = f"{slug}_qr.png"
        img.save(qr_filename)
        
        await update.message.reply_photo(photo=open(qr_filename, 'rb'), caption=f"🚀 *Pulse Live!*\n{full_url}")
        os.remove(qr_filename)

    # DELETE COMMAND
    if text and text.startswith("Delete:"):
        target = text.replace("Delete:", "").strip().lower()
        db.cursor.execute("DELETE FROM projects WHERE slug=?", (target,))
        db.conn.commit()
        await update.message.reply_text(f"🗑 Removed: {target}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()