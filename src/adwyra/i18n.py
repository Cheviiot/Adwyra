# -*- coding: utf-8 -*-
"""Система локализации Adwyra.

Использует gettext для перевода интерфейса.
Язык определяется по настройке «language» в config.json:
  - "auto" — системная локаль
  - "ru", "en" и т.д. — конкретный язык

Файлы переводов ищутся в порядке:
  1. <package_dir>/locale/ (встроенные)
  2. /usr/share/locale/ (системные)

Использование:
    from adwyra.i18n import _
    label = Gtk.Label(label=_("Настройки"))
"""

import gettext
import json
import locale
import os

DOMAIN = "adwyra"

# Пути поиска переводов
_package_dir = os.path.dirname(os.path.abspath(__file__))
_locale_dir = os.path.join(_package_dir, "locale")
_system_locale_dir = "/usr/share/locale"

# Инициализация locale
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass


def _read_language_from_config() -> str:
    """Прочитать настройку языка напрямую из config.json (без импорта Config)."""
    config_path = os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "adwyra", "config.json",
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("language", "auto")
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return "auto"


def get_available_languages() -> list[str]:
    """Вернуть список доступных языковых кодов из встроенных переводов."""
    langs = []
    if os.path.isdir(_locale_dir):
        for entry in sorted(os.listdir(_locale_dir)):
            mo = os.path.join(_locale_dir, entry, "LC_MESSAGES", f"{DOMAIN}.mo")
            if os.path.isfile(mo):
                langs.append(entry)
    return langs


def _load_translation(lang: str = "auto"):
    """Загрузить перевод для указанного языка."""
    languages = None if lang == "auto" else [lang]

    for search_dir in (_locale_dir, _system_locale_dir):
        try:
            return gettext.translation(DOMAIN, localedir=search_dir, languages=languages)
        except FileNotFoundError:
            continue
    return gettext.NullTranslations()


def _init():
    """Инициализировать перевод на основании config."""
    global _, ngettext  # noqa: PLW0603
    lang = _read_language_from_config()
    t = _load_translation(lang)
    _ = t.gettext
    ngettext = t.ngettext


# Привязка домена
for _path in (_locale_dir, _system_locale_dir):
    if os.path.isdir(_path):
        gettext.bindtextdomain(DOMAIN, _path)
        break
else:
    gettext.bindtextdomain(DOMAIN, _locale_dir)
gettext.textdomain(DOMAIN)

# Начальная инициализация
_: gettext.NullTranslations.gettext  # type hint placeholder
ngettext: gettext.NullTranslations.ngettext
_init()
