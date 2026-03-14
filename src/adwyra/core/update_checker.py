# -*- coding: utf-8 -*-
"""Проверка обновлений через GitHub API.

Асинхронная проверка новых версий приложения.
"""

import json
import threading
import urllib.request

from gi.repository import GLib, GObject


GITHUB_API_URL = "https://api.github.com/repos/Cheviiot/Adwyra/tags"


class UpdateChecker(GObject.Object):
    """Сервис проверки обновлений."""
    
    __gtype_name__ = "UpdateChecker"
    
    __gsignals__ = {
        # (latest_version: str | None, error: str | None)
        "check-complete": (GObject.SignalFlags.RUN_LAST, None, (str, str)),
    }
    
    def __init__(self, current_version: str):
        super().__init__()
        self._current_version = current_version
    
    def check(self):
        """Запустить асинхронную проверку обновлений."""
        def fetch():
            try:
                req = urllib.request.Request(
                    GITHUB_API_URL,
                    headers={"User-Agent": "Adwyra"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    if data and len(data) > 0:
                        latest = data[0]["name"]
                        if latest.startswith("v"):
                            latest = latest[1:]
                        GLib.idle_add(self._emit_result, latest, "")
                    else:
                        GLib.idle_add(self._emit_result, "", "Нет тегов")
            except Exception as e:
                GLib.idle_add(self._emit_result, "", str(e))
        
        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()
    
    def _emit_result(self, version: str, error: str):
        """Отправить результат в главный поток."""
        self.emit("check-complete", version or "", error or "")
        return False
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Сравнить версии.
        
        Args:
            v1: Первая версия.
            v2: Вторая версия.
            
        Returns:
            >0 если v1 > v2, <0 если v1 < v2, 0 если равны.
        """
        def parse(v):
            return [int(x) for x in v.split(".")]
        
        try:
            p1, p2 = parse(v1), parse(v2)
            for a, b in zip(p1, p2):
                if a != b:
                    return a - b
            return len(p1) - len(p2)
        except Exception:
            return 0
    
    def is_update_available(self, latest: str) -> bool:
        """Проверить, доступно ли обновление.
        
        Args:
            latest: Последняя версия с GitHub.
            
        Returns:
            True если есть более новая версия.
        """
        return self.compare_versions(latest, self._current_version) > 0
