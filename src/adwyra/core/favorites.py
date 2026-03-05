# -*- coding: utf-8 -*-
"""Управление избранными приложениями."""

import json
import os
from gi.repository import GLib, GObject, Gio


def get_gnome_dock_apps() -> set[str]:
    """Получить закреплённые в GNOME Shell Dock."""
    try:
        settings = Gio.Settings.new("org.gnome.shell")
        favorites = settings.get_strv("favorite-apps")
        return set(favorites)
    except Exception:
        return set()


class Favorites(GObject.Object):
    """Хранилище избранных приложений."""
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__()
        self._dir = os.path.join(GLib.get_user_data_dir(), "adwyra")
        self._path = os.path.join(self._dir, "favorites.json")
        self._apps: list[str] = self._load()
    
    def _load(self) -> list[str]:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                    return data.get("apps", [])
            except (json.JSONDecodeError, IOError):
                pass
        return []
    
    def _save(self):
        os.makedirs(self._dir, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({"apps": self._apps}, f)
        self.emit("changed")
    
    def get_all(self) -> list[str]:
        return list(self._apps)
    
    def contains(self, app_id: str) -> bool:
        return app_id in self._apps
    
    def add(self, app_id: str):
        if app_id and app_id not in self._apps:
            self._apps.append(app_id)
            self._save()
    
    def remove(self, app_id: str):
        if app_id in self._apps:
            self._apps.remove(app_id)
            self._save()
    
    def move(self, app_id: str, target_id: str | None):
        """Переместить приложение на позицию указанного."""
        if app_id not in self._apps or app_id == target_id:
            return
        
        if target_id and target_id in self._apps:
            old_idx = self._apps.index(app_id)
            target_idx = self._apps.index(target_id)
            
            self._apps.remove(app_id)
            target_idx = self._apps.index(target_id)
            
            # Если двигали слева направо - вставляем после target
            if old_idx < target_idx + 1:
                self._apps.insert(target_idx + 1, app_id)
            else:
                # Справа налево - вставляем перед target
                self._apps.insert(target_idx, app_id)
        else:
            self._apps.remove(app_id)
            self._apps.append(app_id)
        self._save()
    
    def toggle(self, app_id: str) -> bool:
        if self.contains(app_id):
            self.remove(app_id)
            return False
        self.add(app_id)
        return True


favorites = Favorites()
