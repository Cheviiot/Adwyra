# -*- coding: utf-8 -*-
"""Сервис поиска с debounce."""

from gi.repository import GLib, GObject, Gio


class SearchService(GObject.Object):
    """Поиск приложений с debounce."""
    
    __gsignals__ = {
        "results": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }
    
    DEBOUNCE_MS = 150
    
    def __init__(self):
        super().__init__()
        self._timeout_id = None
        self._apps: list[Gio.AppInfo] = []
        self._exclude: set[str] = set()
    
    def set_apps(self, apps: list[Gio.AppInfo]):
        self._apps = apps
    
    def set_exclude(self, app_ids: set[str]):
        self._exclude = app_ids
    
    def search(self, query: str):
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
        self._timeout_id = GLib.timeout_add(
            self.DEBOUNCE_MS,
            self._do_search,
            query
        )
    
    def search_immediate(self, query: str) -> list[Gio.AppInfo]:
        return self._filter(query)
    
    def _do_search(self, query: str) -> bool:
        self._timeout_id = None
        results = self._filter(query)
        self.emit("results", results)
        return False
    
    def _filter(self, query: str) -> list[Gio.AppInfo]:
        q = query.lower().strip()
        results = []
        
        for app in self._apps:
            if app.get_id() in self._exclude:
                continue
            
            if not q:
                results.append(app)
                continue
            
            name = (app.get_display_name() or "").lower()
            desc = (app.get_description() or "").lower()
            keywords = " ".join(app.get_keywords() or []).lower()
            
            if q in name or q in desc or q in keywords:
                results.append(app)
        
        return results
