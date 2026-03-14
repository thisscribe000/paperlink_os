import os
import qrcode
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from database import Database
from telegram import Update
from telegram.ext import MessageHandler, filters

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000")
# Note: ADMIN_ID is now used for global broadcasts or maintenance, 
# but not to block standard users from /pulse.

db = Database()
builder_sessions = {}

def generate_pulse_html(title, headline, sub, about, contact_link, style="midnight"):
    # --- YOUR ORIGINAL TAILWIND HTML GENERATOR (UNCHANGED) ---
    slug = title.lower().replace(" ", "-").strip()
    is_dark = style == "midnight"
    bg, text, sub_t, card_bg, border = (
        ("bg-black", "text-white", "text-gray-400", "bg-zinc-950", "border-zinc-800")
        if is_dark else ("bg-white", "text-black", "text-gray-500", "bg-white", "border-zinc-200")
    )
    btn_bg, btn_t = (("bg-white", "text-black") if is_dark else ("bg-black", "text-white"))
    input_bg = "bg-gray-900" if is_dark else "bg-gray-50"
    telegram_href = f"https://t.me/{contact_link.strip('@')}" if contact_link.startswith("@") else contact_link

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="{bg} {text} font-sans transition-all">
        <div class="max-w-6xl mx-auto px-6 py-10">
            <nav class="mb-16 font-black text-xl uppercase tracking-tighter">{title}</nav>
            <section class="text-center py-16">
                <h1 class="text-5xl md:text-7xl font-black tracking-tight mb-6">{headline}</h1>
                <p class="text-xl md:text-2xl {sub_t} max-w-2xl mx-auto mb-12">{sub}</p>
                <a href="{telegram_href}" class="{btn_bg} {btn_t} inline-block px-8 py-4 rounded-full font-bold text-lg">Message Us On Telegram</a>
            </section>
            <section class="py-16">
                <div class="max-w-3xl mx-auto text-center">
                    <p class="text-xs uppercase tracking-[0.25em] opacity-50 font-bold mb-4">About</p>
                    <p class="text-lg md:text-xl {sub_t} leading-8">{about}</p>
                </div>
            </section>
            <section class="py-16">
                <div class="max-w-2xl mx-auto rounded-[2rem] border {border} {card_bg} p-10 text-center">
                    <h2 class="text-3xl md:text-4xl font-black mb-4">Contact Us</h2>
                    <p class="text-base {sub_t} mb-8">Send us a message directly on Telegram, or leave your handle and we'll reach out.</p>
                    <a href="{telegram_href}" class="block {btn_bg} {btn_t} p-4 rounded-full font-bold mb-6">Message Us Now</a>
                    <form action="/submit-lead" method="POST">
                        <input type="hidden" name="slug" value="{slug}">
                        <input type="text" name="handle" placeholder="Telegram Handle" required class="w-full p-4 {input_bg} border {border} rounded-full mb-4 text-center">
                        <button class="w-full {btn_bg} {btn_t} p-4 rounded-full font-bold">Request a Reply</button>
                    </form>
                </div>
            </section>
        </div>
    </body>
    </html>
    """

async def send_qr_reply(update: Update, full_url: str, slug: str) -> None:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(full_url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qr_filename = f"{slug}_qr.png"
    img.save(qr_filename)
    try:
        with open(qr_filename, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=f"🚀 *Pulse Live!*\n[Open Site]({full_url})", parse_mode="Markdown")
    finally:
        if os.path.exists(qr_filename): os.remove(qr_filename)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text, user_id = update.message.text.strip(), update.message.from_user.id

    # --- 1. MY PROJECTS LIST ---
    if text == "/myprojects":
        projs = db.get_user_projects(user_id)
        if not projs:
            await update.message.reply_text("No projects yet. Type /pulse to build one!")
            return
        msg = "📂 *Your Active Links:*\n\n"
        for p in projs:
            msg += f"🔗 {p['name']}\n`{PUBLIC_URL}/{p['slug']}/index.html`\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # --- 2. GUIDED BUILDER (/pulse) ---
    if text == "/pulse":
        builder_sessions[user_id] = {"step": "title", "data": {}}
        await update.message.reply_text("🚀 Let's build. What is the Name of the project?")
        return

    if user_id in builder_sessions:
        session = builder_sessions[user_id]
        step = session["step"]
        if step == "title":
            potential_slug = text.lower().replace(" ", "-").strip()
            # SLUG CHECK
            if db.get_project_owner(potential_slug):
                await update.message.reply_text("⚠️ That name is taken. Try a different project name.")
                return
            session["data"]["title"], session["step"] = text, "headline"
            await update.message.reply_text("Main Headline?")
        elif step == "headline":
            session["data"]["headline"], session["step"] = text, "sub"
            await update.message.reply_text("Short Description?")
        elif step == "sub":
            session["data"]["sub"], session["step"] = text, "about"
            await update.message.reply_text("About Text?")
        elif step == "about":
            session["data"]["about"], session["step"] = text, "contact"
            await update.message.reply_text("Telegram @username or Link?")
        elif step == "contact":
            session["data"]["contact"], session["step"] = text, "style"
            await update.message.reply_text("Style: midnight or light?")
        elif step == "style":
            style = text.lower() if text.lower() in ["midnight", "light"] else "midnight"
            d = session["data"]
            html = generate_pulse_html(d['title'], d['headline'], d['sub'], d['about'], d['contact'], style)
            # Create
            success, result = db.create_project(d['title'], user_id, {"index.html": html.encode("utf-8")})
            if success:
                db.save_project_config(result, {**d, "style": style})
                await send_qr_reply(update, f"{PUBLIC_URL}/{result}/index.html", result)
            else:
                await update.message.reply_text(f"❌ Error: {result}")
            del builder_sessions[user_id]
        return

    # --- 3. EDIT LOGIC (WITH OWNERSHIP CHECK) ---
    if text.startswith("Edit:"):
        parts = [p.strip() for p in text.replace("Edit:", "", 1).split("|")]
        if len(parts) < 3:
            await update.message.reply_text("Format: Edit: slug | field | value")
            return
        slug, field, new_val = parts[0].lower(), parts[1], parts[2]
        
        # OWNERSHIP CHECK
        if db.get_project_owner(slug) != str(user_id):
            await update.message.reply_text("🚫 Access Denied: This project belongs to someone else.")
            return

        config = db.get_project_config(slug)
        if not config:
            await update.message.reply_text("❌ Config error.")
            return

        config[field] = new_val
        new_html = generate_pulse_html(config['title'], config['headline'], config['sub'], config['about'], config['contact_link'] if 'contact_link' in config else config['contact'], config['style'])
        db.update_project_file(slug, "index.html", new_html.encode("utf-8"))
        db.save_project_config(slug, config)
        await update.message.reply_text(f"✅ Updated {slug}!")
        return

    # --- 4. DELETE LOGIC (WITH OWNERSHIP CHECK) ---
    if text.startswith("Delete:"):
        target = text.replace("Delete:", "", 1).strip().lower()
        if db.get_project_owner(target) != str(user_id):
            await update.message.reply_text("🚫 You can only delete your own projects.")
            return
        db.delete_project(target)
        await update.message.reply_text(f"🗑 Project '{target}' has been deleted.")
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    
    # Create an assets folder if it doesn't exist
    if not os.path.exists("assets"):
        os.makedirs("assets")
        
    file_name = f"assets/{photo_file.file_unique_id}.jpg"
    await photo_file.download_to_drive(file_name)
    
    # Register in DB
    asset_id = db.save_asset(user_id, photo_file.file_id, "image/jpeg", file_name)
    
    asset_url = f"{PUBLIC_URL}/{file_name}"
    await update.message.reply_text(
        f"✅ **Asset Saved to PaperLink OS**\n\n"
        f"Asset ID: `{asset_id}`\n"
        f"Public URL: {asset_url}\n\n"
        "You can now use this URL in your Pulse pages or Store items.",
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    print("🤖 PaperLink OS Bot Ready...")
    app.run_polling()