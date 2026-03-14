# -*- coding: utf-8 -*-
"""Система локальных псевдонимов приложений.

Хранит пользовательские имена для приложений,
которые отображаются только в Adwyra.
"""

import json
import os

from gi.repository import GLib, GObject


class Aliases(GObject.Object):
    """Управление локальными псевдонимами приложений."""
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self):
        super().__init__()
        self._dir = os.path.join(GLib.get_user_config_dir(), "adwyra")
        self._path = os.path.join(self._dir, "aliases.json")
        self._data = self._load()
    
    def _load(self) -> dict:
        """Загружает псевдонимы из файла."""
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _save(self):
        """Сохраняет псевдонимы в файл."""
        os.makedirs(self._dir, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
    
    def get(self, app_id: str) -> str | None:
        """Возвращает псевдоним для приложения или None."""
        return self._data.get(app_id)
    
    def set(self, app_id: str, name: str):
        """Устанавливает псевдоним для приложения."""
        if name.strip():
            self._data[app_id] = name.strip()
        else:
            # Пустое имя - удаляем псевдоним
            self._data.pop(app_id, None)
        self._save()
        self.emit("changed", app_id)
    
    def remove(self, app_id: str):
        """Удаляет псевдоним приложения."""
        if app_id in self._data:
            del self._data[app_id]
            self._save()
            self.emit("changed", app_id)
    
    def get_display_name(self, app_id: str, default: str) -> str:
        """Возвращает псевдоним или оригинальное имя."""
        return self._data.get(app_id) or default


aliases = Aliases()
