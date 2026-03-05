# -*- coding: utf-8 -*-
"""Сервис загрузки приложений."""

from gi.repository import Gio, GObject


class AppService(GObject.Object):
    """Кэширует и отслеживает изменения приложений."""
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__()
        self._apps: list[Gio.AppInfo] = []
        self._monitor = Gio.AppInfoMonitor.get()
        self._monitor.connect("changed", self._on_changed)
        self._load()
    
    def _load(self):
        self._apps = [
            app for app in Gio.AppInfo.get_all()
            if app.should_show()
        ]
        self._apps.sort(key=lambda a: (a.get_display_name() or "").lower())
    
    def _on_changed(self, monitor):
        self._load()
        self.emit("changed")
    
    def get_all(self) -> list[Gio.AppInfo]:
        return self._apps
    
    def get_by_id(self, app_id: str) -> Gio.AppInfo | None:
        return Gio.DesktopAppInfo.new(app_id)
    
    def launch(self, app_info: Gio.AppInfo) -> bool:
        try:
            return app_info.launch(None, None)
        except Exception:
            return False


app_service = AppService()
