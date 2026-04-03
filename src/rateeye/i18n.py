import json
import os


def load_translations():
    """Loads the JSON data into a dictionary once at startup."""
    path = os.path.join(os.path.dirname(__file__), "locales", "translations.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback if file is missing
        return {"en": {"title": "RateEye"}}


TRANSLATIONS = load_translations()


def get_text(lang_code="en"):
    """
    Detects the base language from the Accept-Language header.
    Defaults to English if the language is not supported.
    """
    # Normalize header (e.g., 'en-US,en;q=0.9' -> 'en')
    base_lang = lang_code.split(",")[0].split("-")[0].lower() if lang_code else "en"
    return TRANSLATIONS.get(base_lang, TRANSLATIONS.get("en"))
