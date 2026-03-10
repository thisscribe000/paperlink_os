import os
import qrcode
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    filters,
)

from database import Database
from pulse_generator import deploy_pulse_site

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

db = Database()

BRAND_NAME, TAGLINE, HEADLINE, SUBHEADLINE, CTA_TEXT, CTA_LINK = range(6)


def build_default_pulse_data(user_data: dict) -> dict:
    brand_name = user_data["brand_name"]
    slug = brand_name.lower().replace(" ", "-").strip()

    return {
        "BRAND_NAME": brand_name,
        "TAGLINE": user_data["tagline"],
        "HEADLINE": user_data["headline"],
        "SUBHEADLINE": user_data["subheadline"],
        "CTA_TEXT": user_data["cta_text"],
        "SECONDARY_CTA_TEXT": "Collaborate",
        "CTA_LINK": user_data["cta_link"],
        "SECTION_TITLE": "A faster path from idea to launch",
        "SECTION_BODY": f"{brand_name} helps you move from idea to launch faster with a clean Telegram-native workflow.",
        "FEATURE_1_TITLE": "Fast to launch",
        "FEATURE_1_BODY": "Move from concept to live page in minutes.",
        "FEATURE_2_TITLE": "Telegram native",
        "FEATURE_2_BODY": "Use the platform people already know and use every day.",
        "FEATURE_3_TITLE": "Built for expansion",
        "FEATURE_3_BODY": "Start with a page today and grow into a bigger system later.",
        "CONTACT_TITLE": f"Connect with {brand_name}",
        "CONTACT_BODY": "Drop your Telegram handle and we’ll reach out.",
        "FORM_BUTTON_TEXT": "Get Started",
        "PROJECT_SLUG": slug,
    }


async def pulse_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text("Let’s build your Pulse page.\n\nWhat is the brand name?")
    return BRAND_NAME


async def pulse_brand_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["brand_name"] = update.message.text.strip()
    await update.message.reply_text("Nice. What is the tagline?")
    return TAGLINE


async def pulse_tagline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tagline"] = update.message.text.strip()
    await update.message.reply_text("What is the main headline?")
    return HEADLINE


async def pulse_headline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["headline"] = update.message.text.strip()
    await update.message.reply_text("What is the subheadline?")
    return SUBHEADLINE


async def pulse_subheadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["subheadline"] = update.message.text.strip()
    await update.message.reply_text("What should the main CTA button say?")
    return CTA_TEXT


async def pulse_cta_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cta_text"] = update.message.text.strip()
    await update.message.reply_text("What link should the CTA button open?")
    return CTA_LINK


async def pulse_cta_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cta_link"] = update.message.text.strip()

    data = build_default_pulse_data(context.user_data)
    slug = deploy_pulse_site(data, owner_id=update.message.from_user.id)

    if not slug:
        await update.message.reply_text("Something went wrong while deploying the site.")
        return ConversationHandler.END

    base = PUBLIC_URL.rstrip("/") if PUBLIC_URL else "http://localhost:8000"
    full_url = f"{base}/{slug}/index.html"

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(full_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qr_filename = f"{slug}_qr.png"
    img.save(qr_filename)

    with open(qr_filename, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=f"🚀 *Pulse Live!*\n{full_url}",
            parse_mode="Markdown"
        )

    os.remove(qr_filename)
    context.user_data.clear()
    return ConversationHandler.END


async def pulse_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Pulse creation cancelled.")
    return ConversationHandler.END


async def handle_text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        return

    text = update.message.text

    if text and text.startswith("Delete:"):
        target = text.replace("Delete:", "").strip().lower()
        deleted = db.delete_project(target)
        if deleted:
            await update.message.reply_text(f"🗑 Removed: {target}")
        else:
            await update.message.reply_text(f"Could not find project: {target}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    pulse_handler = ConversationHandler(
        entry_points=[CommandHandler("pulse", pulse_start)],
        states={
            BRAND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_brand_name)],
            TAGLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_tagline)],
            HEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_headline)],
            SUBHEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_subheadline)],
            CTA_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_cta_text)],
            CTA_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_cta_link)],
        },
        fallbacks=[CommandHandler("cancel", pulse_cancel)],
    )

    app.add_handler(pulse_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_commands))

    print("🤖 PaperLink bot is running...")
    app.run_polling()