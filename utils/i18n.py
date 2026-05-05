"""
i18n.py — Translation manager.
Loads JSON translation files and provides a global tr() function.
"""
import json
import os
from typing import Dict, Any
from utils.logger import log
from utils.settings import settings

class I18nManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._translations = {}
            cls._instance._current_lang = ""
            cls._instance.load_language(settings.language)
        return cls._instance

    def load_language(self, lang_code: str):
        if self._current_lang == lang_code and self._translations:
            return

        # Base directory for languages
        base_dir = os.path.dirname(os.path.dirname(__file__))
        lang_file = os.path.join(base_dir, "resources", "lang", f"{lang_code}.json")

        if not os.path.exists(lang_file):
            log.warning("Language file not found: %s. Falling back to 'en'.", lang_file)
            if lang_code != "en":
                self.load_language("en")
            return

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
            self._current_lang = lang_code
            log.info("Loaded language: %s", lang_code)
        except Exception as e:
            log.error("Failed to load language %s: %s", lang_code, e)

    def tr(self, key: str, **kwargs) -> str:
        """Translate a key with optional formatting."""
        text = self._translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

# Global instance
i18n = I18nManager()

def tr(key: str, **kwargs) -> str:
    return i18n.tr(key, **kwargs)
