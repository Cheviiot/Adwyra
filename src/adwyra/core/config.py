# -*- coding: utf-8 -*-
"""Система конфигурации приложения.

Хранит пользовательские настройки в JSON-файле (~/.config/adwyra/config.json).
При изменении любого параметра автоматически сохраняет файл и оповещает
подписчиков через GObject-сигнал "changed".

Пример использования:
    from adwyra.core import config
    
    # Чтение настройки
    columns = config.get("columns")
    
    # Изменение настройки (автосохранение + сигнал)
    config.set("columns", 8)
    
    # Подписка на изменения
    config.connect("changed", lambda cfg, key, val: print(f"{key} = {val}"))
"""

import json
import os
from gi.repository import GLib, GObject


class Config(GObject.Object):
    """Менеджер настроек приложения.
    
    Attributes:
        DEFAULTS: Значения по умолчанию для всех настроек.
    
    Signals:
        changed(key: str, value: Any): Настройка изменилась.
    """
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, (str, object)),
    }
    
    DEFAULTS = {
        "columns": 7,           # Столбцов в сетке
        "rows": 5,              # Строк в сетке
        "icon_size": 56,        # Размер иконок (px)
        "theme": "system",      # Тема: system, light, dark
        "language": "auto",     # Язык: auto, ru, en
        "transparent": False,   # Прозрачность окна
        "close_on_launch": True,          # Закрывать при запуске приложения
        "close_on_focus_lost": True,      # Закрывать при потере фокуса
        "hide_dock_apps": True,           # Скрывать закреплённые в Dock
    }
    
    def __init__(self):
        super().__init__()
        self._config_dir = os.path.join(GLib.get_user_config_dir(), "adwyra")
        self._config_path = os.path.join(self._config_dir, "config.json")
        self._data = self._load()
    
    def _load(self) -> dict:
        """Загрузить настройки из файла или вернуть значения по умолчанию."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    # Объединяем с дефолтами (новые ключи добавятся автоматически)
                    return {**self.DEFAULTS, **user_data}
            except (json.JSONDecodeError, IOError):
                pass
        return dict(self.DEFAULTS)
    
    def _save(self):
        """Сохранить текущие настройки в файл."""
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str):
        """Получить значение настройки.
        
        Args:
            key: Имя параметра (см. DEFAULTS).
            
        Returns:
            Значение настройки или значение по умолчанию.
        """
        return self._data.get(key, self.DEFAULTS.get(key))
    
    def set(self, key: str, value):
        """Установить значение настройки.
        
        Сохраняет файл и эмитит сигнал "changed" только если значение изменилось.
        
        Args:
            key: Имя параметра.
            value: Новое значение.
        """
        if self._data.get(key) != value:
            self._data[key] = value
            self._save()
            self.emit("changed", key, value)
    
    # === Вычисляемые свойства ===
    
    @property
    def per_page(self) -> int:
        """Количество элементов на одной странице сетки."""
        return self.get("columns") * self.get("rows")


# Глобальный экземпляр конфигурации
config = Config()
