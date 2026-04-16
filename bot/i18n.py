import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.config import get_settings


@lru_cache(maxsize=2)
def _load_locale(lang: str) -> dict[str, Any]:
    """Load locale JSON file with caching."""
    locales_dir = Path(__file__).parent.parent / "locales"
    file_path = locales_dir / f"{lang}.json"

    if not file_path.exists():
        # Fallback to Russian if locale file doesn't exist
        if lang != "ru":
            return _load_locale("ru")
        # If Russian also missing, return empty dict
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.

    Args:
        key: dot‑separated key (e.g., "commands.start")
        **kwargs: placeholders to replace in the string (e.g., {name: "John"})

    Returns:
        Translated string with placeholders replaced, or the key itself if not found.
    """
    settings = get_settings()
    lang = getattr(settings, "language", "ru")
    locale = _load_locale(lang)

    # Navigate nested dicts using dot notation
    parts = key.split(".")
    value = locale
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            # Key not found – fallback to Russian
            if lang != "ru":
                ru_locale = _load_locale("ru")
                ru_value = ru_locale
                for ru_part in parts:
                    if isinstance(ru_value, dict) and ru_part in ru_value:
                        ru_value = ru_value[ru_part]
                    else:
                        return key  # fallback to key itself
                value = ru_value
                break
            else:
                return key

    # If value is still a dict (incomplete key), return the key
    if isinstance(value, dict):
        return key

    result = str(value)

    # Replace placeholders like {name}
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return result


# Singleton for convenient import
i18n = t