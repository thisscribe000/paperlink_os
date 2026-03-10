from pathlib import Path
from database import Database

TEMPLATE_PATH = Path("templates/pulse/index.html")


def generate_pulse_html(data: dict) -> str:
    html = TEMPLATE_PATH.read_text()

    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        html = html.replace(placeholder, str(value))

    return html


def deploy_pulse_site(data: dict, owner_id: int = 0):
    db = Database()

    html = generate_pulse_html(data)

    files = {
        "index.html": html.encode("utf-8")
    }

    slug = db.create_project(
        name=data["BRAND_NAME"],
        owner_id=owner_id,
        files_dict=files
    )

    if slug:
        db.save_project_config(slug, "pulse", data)
        print(f"Site deployed: http://localhost:8000/{slug}/index.html")

    return slug


if __name__ == "__main__":
    test_data = {
        "BRAND_NAME": "Barraos",
        "TAGLINE": "Telegram-native operating system",
        "HEADLINE": "Build the web from chat.",
        "SUBHEADLINE": "Turn ideas into hosted landing pages directly from Telegram.",
        "CTA_TEXT": "Start Building",
        "SECONDARY_CTA_TEXT": "Collaborate",
        "CTA_LINK": "https://t.me/PaperLinkBuilders",
        "SECTION_TITLE": "A faster path from idea to launch",
        "SECTION_BODY": "Instead of setting up hosting manually, Barraos lets builders launch quickly.",
        "FEATURE_1_TITLE": "Fast to launch",
        "FEATURE_1_BODY": "Move from concept to live page in minutes.",
        "FEATURE_2_TITLE": "Telegram native",
        "FEATURE_2_BODY": "Use the platform people already open every day.",
        "FEATURE_3_TITLE": "Built for expansion",
        "FEATURE_3_BODY": "Pages today. Tools tomorrow.",
        "CONTACT_TITLE": "Join the builders circle",
        "CONTACT_BODY": "Drop your Telegram handle and get redirected.",
        "FORM_BUTTON_TEXT": "Join Now",
        "PROJECT_SLUG": "barraos"
    }

    deploy_pulse_site(test_data)