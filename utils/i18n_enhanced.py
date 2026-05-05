"""
i18n_enhanced.py — Enhanced translation manager with language switching support.
Loads JSON translation files and provides enhanced tr() function with language switching.
"""
import json
import os
from typing import Dict, Any, List
from utils.logger import log
from utils.settings import settings

class EnhancedI18nManager:
    _instance = None
    _available_languages = {}
    _current_lang = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._translations = {}
            cls._instance._current_lang = ""
            cls._instance._load_available_languages()
            cls._instance.load_language(settings.language)
        return cls._instance

    def _load_available_languages(self):
        """Load available language files."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        lang_dir = os.path.join(base_dir, "resources", "lang")
        
        self._available_languages = {}
        if os.path.exists(lang_dir):
            for file in os.listdir(lang_dir):
                if file.endswith('.json'):
                    lang_code = file[:-5]  # Remove .json extension
                    lang_file_path = os.path.join(lang_dir, file)
                    
                    try:
                        with open(lang_file_path, 'r', encoding='utf-8') as f:
                            lang_data = json.load(f)
                            # Get language name from app_name or use code
                            lang_name = lang_data.get('language_name', lang_code.upper())
                            self._available_languages[lang_code] = {
                                'name': lang_name,
                                'file': file,
                                'path': lang_file_path
                            }
                    except Exception as e:
                        log.warning("Failed to load language file %s: %s", file, e)
        
        log.info("Available languages: %s", list(self._available_languages.keys()))

    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Get list of available languages."""
        return self._available_languages

    def load_language(self, lang_code: str):
        """Load a specific language file."""
        if self._current_lang == lang_code and self._translations:
            return

        if lang_code not in self._available_languages:
            log.warning("Language not found: %s. Falling back to 'en'", lang_code)
            if lang_code != "en":
                self.load_language("en")
            return

        lang_info = self._available_languages[lang_code]
        lang_file = lang_info['path']

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
            self._current_lang = lang_code
            log.info("Loaded language: %s (%s)", lang_code, lang_info['name'])
        except Exception as e:
            log.error("Failed to load language %s: %s", lang_code, e)

    def tr(self, key: str, **kwargs) -> str:
        """Translate a key with optional formatting."""
        text = self._translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                log.warning("Missing format key in translation: %s", key)
                return text
        return text

    def get_current_language(self) -> str:
        """Get current language code."""
        return self._current_lang

    def get_current_language_name(self) -> str:
        """Get current language display name."""
        if self._current_lang in self._available_languages:
            return self._available_languages[self._current_lang]['name']
        return self._current_lang.upper()

    def switch_language(self, lang_code: str) -> bool:
        """Switch to a different language."""
        if lang_code not in self._available_languages:
            return False
        
        self.load_language(lang_code)
        # Save to settings
        settings.language = lang_code
        settings.save()
        return True

# Global instance
_i18n_manager = None

def get_i18n_manager() -> EnhancedI18nManager:
    """Get the global i18n manager instance."""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = EnhancedI18nManager()
    return _i18n_manager

def tr(key: str, **kwargs) -> str:
    """Global translation function."""
    return get_i18n_manager().tr(key, **kwargs)

# Backward compatibility
I18nManager = EnhancedI18nManager
