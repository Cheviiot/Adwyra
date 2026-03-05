# -*- coding: utf-8 -*-
"""Конфигурация приложения."""

import json
import os
from gi.repository import GLib, GObject


class Config(GObject.Object):
    """Настройки приложения с сохранением."""
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, (str, object)),
    }
    
    DEFAULTS = {
        "columns": 7,
        "rows": 5,
        "icon_size": 56,
        "theme": "system",  # system, light, dark
        "close_on_launch": True,
        "close_on_focus_lost": True,
        "hide_dock_apps": True,  # Скрывать закреплённые в Dock
    }
    
    def __init__(self):
        super().__init__()
        self._dir = os.path.join(GLib.get_user_config_dir(), "adwyra")
        self._path = os.path.join(self._dir, "config.json")
        self._data = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                    return {**self.DEFAULTS, **data}
            except (json.JSONDecodeError, IOError):
                pass
        return dict(self.DEFAULTS)
    
    def _save(self):
        os.makedirs(self._dir, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)
    
    def get(self, key: str):
        return self._data.get(key, self.DEFAULTS.get(key))
    
    def set(self, key: str, value):
        if self._data.get(key) != value:
            self._data[key] = value
            self._save()
            self.emit("changed", key, value)
    
    @property
    def per_page(self) -> int:
        return self.get("columns") * self.get("rows")


config = Config()
