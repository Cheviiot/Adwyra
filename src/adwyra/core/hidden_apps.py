# -*- coding: utf-8 -*-
"""Управление скрытыми приложениями.

Позволяет пользователю скрывать приложения из лаунчера Adwyra,
при этом они остаются доступными в системе (в GNOME Activities и т.д.).

Файл хранения: ~/.config/adwyra/hidden.json
"""

import json
import os
from gi.repository import GLib, GObject


class HiddenApps(GObject.Object):
    """Менеджер скрытых приложений.
    
    Signals:
        changed(): Список скрытых приложений изменился.
    """
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__()
        self._dir = os.path.join(GLib.get_user_config_dir(), "adwyra")
        self._path = os.path.join(self._dir, "hidden.json")
        self._apps: list[str] = self._load()
    
    def _load(self) -> list[str]:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("apps", [])
            except (json.JSONDecodeError, IOError):
                pass
        return []
    
    def _save(self):
        os.makedirs(self._dir, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"apps": self._apps}, f)
        self.emit("changed")
    
    def get_all(self) -> list[str]:
        """Получить список ID всех скрытых приложений."""
        return list(self._apps)
    
    def contains(self, app_id: str) -> bool:
        """Проверить, скрыто ли приложение."""
        return app_id in self._apps
    
    def add(self, app_id: str):
        """Скрыть приложение."""
        if app_id and app_id not in self._apps:
            self._apps.append(app_id)
            self._save()
    
    def remove(self, app_id: str):
        """Показать скрытое приложение."""
        if app_id in self._apps:
            self._apps.remove(app_id)
            self._save()


hidden_apps = HiddenApps()
