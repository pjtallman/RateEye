import json
import os


def load_translations():
    """Loads the JSON data into a dictionary from the translations.json file."""
    path = os.path.join(os.path.dirname(__file__), "locales", "translations.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Fallback if file is missing or invalid
        return {"en": {"title": "RateEye"}}


# Cache translations once at startup
TRANSLATIONS = load_translations()


def get_text(lang_code="en"):
    """
    Detects the base language from the Accept-Language header.
    Uses cached TRANSLATIONS for performance.
    """
    # Normalize header (e.g., 'en-US,en;q=0.9' -> 'en')
    base_lang = lang_code.split(",")[0].split("-")[0].lower() if lang_code else "en"
    return TRANSLATIONS.get(base_lang, TRANSLATIONS.get("en"))
