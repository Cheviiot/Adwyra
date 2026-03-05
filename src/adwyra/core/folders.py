# -*- coding: utf-8 -*-
"""Управление папками приложений."""

import json
import os
from gi.repository import GLib, GObject


class Folders(GObject.Object):
    """Хранилище папок с приложениями."""
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__()
        self._dir = os.path.join(GLib.get_user_data_dir(), "adwyra")
        self._path = os.path.join(self._dir, "folders.json")
        self._data = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"folders": {}, "counter": 0}
    
    def _save(self):
        os.makedirs(self._dir, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        self.emit("changed")
    
    def get_ids(self) -> list[str]:
        return list(self._data.get("folders", {}).keys())
    
    def get(self, folder_id: str) -> dict | None:
        return self._data.get("folders", {}).get(folder_id)
    
    def create(self, name: str, apps: list[str] = None) -> str:
        self._data["counter"] = self._data.get("counter", 0) + 1
        folder_id = f"folder_{self._data['counter']}"
        self._data["folders"][folder_id] = {"name": name, "apps": apps or []}
        self._save()
        return folder_id
    
    def rename(self, folder_id: str, name: str):
        folder = self._data["folders"].get(folder_id)
        if folder:
            folder["name"] = name
            self._save()
    
    def delete(self, folder_id: str):
        if folder_id in self._data["folders"]:
            del self._data["folders"][folder_id]
            self._save()
    
    def add_app(self, folder_id: str, app_id: str):
        folder = self._data["folders"].get(folder_id)
        if folder and app_id not in folder["apps"]:
            folder["apps"].append(app_id)
            self._save()
    
    def remove_app(self, folder_id: str, app_id: str):
        folder = self._data["folders"].get(folder_id)
        if folder and app_id in folder["apps"]:
            folder["apps"].remove(app_id)
            self._save()
    
    def get_all_app_ids(self) -> set[str]:
        result = set()
        for folder in self._data.get("folders", {}).values():
            result.update(folder.get("apps", []))
        return result


folders = Folders()
