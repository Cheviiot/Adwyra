# -*- coding: utf-8 -*-
"""Система плагинов Adwyra.

Загружает, активирует и управляет плагинами из двух директорий:
  - /usr/lib/adwyra/plugins/  — системные плагины (установленные через Stapler)
  - ~/.config/adwyra/plugins/ — пользовательские плагины (для разработки)

Каждый плагин — папка с plugin.py, содержащим класс, наследующий AdwyraPlugin.

Структура плагина:
    <plugins_dir>/my_plugin/
        plugin.py          # Точка входа (обязателен)
        # ... другие файлы

plugin.py должен содержать:
    from adwyra.core.plugins import AdwyraPlugin

    class Plugin(AdwyraPlugin):
        meta = {
            "id": "my_plugin",
            "name": "My Plugin",
            "description": "Описание плагина",
            "version": "1.0",
            "author": "Автор",
        }

        def activate(self):
            # Вызывается при включении
            pass

        def deactivate(self):
            # Вызывается при выключении
            pass
"""

import os
import sys
import json
import importlib
import importlib.util
from gi.repository import GLib, GObject


class AdwyraPlugin:
    """Базовый класс плагина.
    
    Плагины наследуют этот класс и переопределяют activate/deactivate.
    Поле meta содержит метаданные плагина.
    """
    
    meta = {
        "id": "",
        "name": "Unnamed Plugin",
        "description": "",
        "version": "0.1",
        "author": "",
        "min_app_version": "",
    }
    
    def __init__(self, app_context):
        """Инициализация плагина.
        
        Args:
            app_context: PluginContext с API для взаимодействия с приложением.
        """
        self.ctx = app_context
    
    def activate(self):
        """Вызывается при включении плагина. Переопределите в своём плагине."""
        pass
    
    def deactivate(self):
        """Вызывается при выключении плагина. Переопределите в своём плагине."""
        pass

    def on_app_launched(self, app_id):
        """Вызывается при запуске приложения. app_id — ID приложения."""
        pass

    def on_search(self, query):
        """Вызывается при поиске. Вернуть список результатов или None."""
        return None

    def on_window_shown(self):
        """Вызывается при показе окна лаунчера."""
        pass

    def on_window_hidden(self):
        """Вызывается при скрытии окна лаунчера."""
        pass


class PluginContext:
    """API контекст, передаваемый плагинам.
    
    Каждый плагин получает свой экземпляр с доступом к:
    - UI хукам (настройки, страницы, контекстное меню)
    - Конфигурации приложения (чтение)
    - Собственному хранилищу настроек (чтение/запись)
    - Списку приложений
    """
    
    def __init__(self, plugin_manager, plugin_id):
        self._pm = plugin_manager
        self._plugin_id = plugin_id
        self._data_dir = os.path.join(
            GLib.get_user_config_dir(), "adwyra", "plugin_data", plugin_id
        )
        self._config_path = os.path.join(self._data_dir, "config.json")
        self._config_cache = None
    
    # --- Собственное хранилище плагина ---
    
    def _ensure_config(self):
        if self._config_cache is not None:
            return self._config_cache
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config_cache = {}
        else:
            self._config_cache = {}
        return self._config_cache
    
    def get_plugin_config(self, key, default=None):
        """Прочитать значение из конфигурации плагина.
        
        Хранится в ~/.config/adwyra/plugin_data/<id>/config.json
        """
        return self._ensure_config().get(key, default)
    
    def set_plugin_config(self, key, value):
        """Записать значение в конфигурацию плагина."""
        data = self._ensure_config()
        data[key] = value
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_data_dir(self):
        """Получить директорию для хранения данных плагина.
        
        Returns:
            Путь: ~/.config/adwyra/plugin_data/<id>/
        """
        os.makedirs(self._data_dir, exist_ok=True)
        return self._data_dir
    
    # --- UI хуки ---
    
    def add_prefs_group(self, group):
        """Добавить группу настроек (Adw.PreferencesGroup) в настройки плагина.
        
        Группа будет доступна на отдельной странице настроек плагина.
        
        Args:
            group: Adw.PreferencesGroup для отображения.
        """
        if self._plugin_id not in self._pm._prefs_groups:
            self._pm._prefs_groups[self._plugin_id] = []
        self._pm._prefs_groups[self._plugin_id].append(group)
    
    def remove_prefs_group(self, group):
        """Убрать группу настроек плагина."""
        groups = self._pm._prefs_groups.get(self._plugin_id, [])
        if group in groups:
            groups.remove(group)
            if not groups:
                self._pm._prefs_groups.pop(self._plugin_id, None)
    
    def add_page(self, page_id, widget, title):
        """Добавить страницу в стек навигации.
        
        Args:
            page_id: Уникальный идентификатор страницы.
            widget: Gtk.Widget — содержимое страницы.
            title: Заголовок (для навигации).
        """
        self._pm.emit("page-added", page_id, widget, title)
    
    def remove_page(self, page_id):
        """Убрать страницу из стека навигации."""
        self._pm.emit("page-removed", page_id)
    
    def add_context_menu_item(self, label, callback):
        """Добавить пункт в контекстное меню приложений.
        
        Args:
            label: Текст пункта меню.
            callback: Callable(app_id: str) — вызывается при выборе пункта.
        Returns:
            Идентификатор пункта для последующего удаления.
        """
        item_id = id(callback)
        self._pm._menu_items[item_id] = {"label": label, "callback": callback}
        return item_id
    
    def remove_context_menu_item(self, item_id):
        """Убрать пункт из контекстного меню."""
        self._pm._menu_items.pop(item_id, None)
    
    def get_config(self, key, default=None):
        """Прочитать значение из конфигурации приложения."""
        from . import config
        return config.get(key) if config.get(key) is not None else default
    
    def get_apps(self):
        """Получить список всех установленных приложений (Gio.AppInfo)."""
        from .apps import app_service
        return app_service.get_all()


class PluginManager(GObject.Object):
    """Менеджер плагинов — обнаружение, загрузка, активация.
    
    Signals:
        changed(): Список плагинов изменился (загрузка/выгрузка/вкл/выкл).
        prefs-group-added(group): Плагин добавил группу настроек.
        prefs-group-removed(group): Плагин удалил группу настроек.
        page-added(page_id, widget, title): Плагин добавил страницу.
        page-removed(page_id): Плагин удалил страницу.
    """
    
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "prefs-group-added": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "prefs-group-removed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "page-added": (GObject.SignalFlags.RUN_LAST, None, (str, object, str)),
        "page-removed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    # Системный путь (Stapler-пакеты устанавливают сюда)
    SYSTEM_PLUGINS_DIR = "/usr/lib/adwyra/plugins"
    
    def __init__(self):
        super().__init__()
        self._user_plugins_dir = os.path.join(GLib.get_user_config_dir(), "adwyra", "plugins")
        self._state_path = os.path.join(GLib.get_user_config_dir(), "adwyra", "plugins.json")
        self._plugins = {}       # plugin_id -> {"instance": AdwyraPlugin, "module": module, "active": bool}
        self._enabled = set()    # IDs включённых плагинов
        self._menu_items = {}    # item_id -> {"label": str, "callback": callable}
        self._prefs_groups = {}  # plugin_id -> [Adw.PreferencesGroup]
        self._load_state()
    
    def _load_state(self):
        """Загрузить список включённых плагинов."""
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._enabled = set(data.get("enabled", []))
            except (json.JSONDecodeError, IOError):
                self._enabled = set()
    
    def _save_state(self):
        """Сохранить список включённых плагинов."""
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        with open(self._state_path, "w", encoding="utf-8") as f:
            json.dump({"enabled": list(self._enabled)}, f, indent=2, ensure_ascii=False)
    
    def discover(self):
        """Обнаружить плагины.
        
        Сканирует системный (/usr/lib/adwyra/plugins/) и пользовательский
        (~/.config/adwyra/plugins/) каталоги. При совпадении ID
        пользовательский плагин имеет приоритет.
        Автоматически активирует ранее включённые плагины.
        """
        # Сначала системные, потом пользовательские (приоритет)
        for plugins_dir in (self.SYSTEM_PLUGINS_DIR, self._user_plugins_dir):
            if not os.path.isdir(plugins_dir):
                continue
            
            for name in sorted(os.listdir(plugins_dir)):
                plugin_dir = os.path.join(plugins_dir, name)
                plugin_file = os.path.join(plugin_dir, "plugin.py")
                
                if not os.path.isdir(plugin_dir) or not os.path.isfile(plugin_file):
                    continue
                
                if name in self._plugins:
                    continue  # Уже загружен
                
                self._load_plugin(name, plugin_file)
        
        # Активировать ранее включённые
        for pid in list(self._enabled):
            if pid in self._plugins and not self._plugins[pid]["active"]:
                self._activate(pid)
        
        self.emit("changed")
    
    @staticmethod
    def _compare_versions(a, b):
        """Сравнить два версионных номера (x.y.z). Возвращает -1, 0 или 1."""
        def parse(v):
            parts = []
            for x in v.split("."):
                try:
                    parts.append(int(x))
                except ValueError:
                    parts.append(0)
            return parts
        from itertools import zip_longest
        for x, y in zip_longest(parse(a), parse(b), fillvalue=0):
            if x < y:
                return -1
            if x > y:
                return 1
        return 0
    
    def _validate_meta(self, meta, plugin_id):
        """Проверить обязательные поля метаданных.
        
        Returns:
            (ok, reason) — кортеж с результатом и причиной ошибки.
        """
        if not meta.get("id"):
            return False, "отсутствует meta['id']"
        if not meta.get("name") or meta["name"] == "Unnamed Plugin":
            return False, "отсутствует meta['name']"
        return True, ""
    
    def _check_compatibility(self, meta):
        """Проверить совместимость с текущей версией Adwyra.
        
        Returns:
            (ok, reason) — кортеж с результатом и причиной.
        """
        min_ver = meta.get("min_app_version", "")
        if not min_ver:
            return True, ""
        from .. import __version__
        if self._compare_versions(__version__, min_ver) < 0:
            return False, f"требуется Adwyra ≥{min_ver} (установлена {__version__})"
        return True, ""
    
    def _load_plugin(self, plugin_id, plugin_file):
        """Загрузить модуль плагина (без активации)."""
        module_name = f"adwyra_plugin_{plugin_id}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            plugin_cls = getattr(module, "Plugin", None)
            if not plugin_cls or not issubclass(plugin_cls, AdwyraPlugin):
                print(f"[plugins] {plugin_id}: класс Plugin не найден или не наследует AdwyraPlugin")
                return
            
            # Определить ID из мета-класса до создания экземпляра
            meta_id = getattr(plugin_cls, "meta", {}).get("id") or plugin_id
            
            # Создать уникальный контекст для плагина
            context = PluginContext(self, meta_id)
            instance = plugin_cls(context)
            
            # Валидация метаданных
            ok, reason = self._validate_meta(instance.meta, plugin_id)
            if not ok:
                print(f"[plugins] {plugin_id}: невалидные метаданные — {reason}")
                return
            
            # Проверка совместимости
            ok, reason = self._check_compatibility(instance.meta)
            if not ok:
                print(f"[plugins] {plugin_id}: несовместим — {reason}")
                self._plugins[meta_id] = {
                    "instance": instance,
                    "module": module,
                    "active": False,
                    "dir_name": plugin_id,
                    "error": reason,
                }
                return
            
            self._plugins[meta_id] = {
                "instance": instance,
                "module": module,
                "active": False,
                "dir_name": plugin_id,
                "error": None,
            }
        except Exception as e:
            print(f"[plugins] Ошибка загрузки {plugin_id}: {e}")
    
    def _activate(self, plugin_id):
        """Активировать плагин."""
        entry = self._plugins.get(plugin_id)
        if not entry or entry["active"]:
            return
        if entry.get("error"):
            return
        try:
            entry["instance"].activate()
            entry["active"] = True
        except Exception as e:
            print(f"[plugins] Ошибка активации {plugin_id}: {e}")
            entry["error"] = f"ошибка активации: {e}"
            self._enabled.discard(plugin_id)
            self._save_state()
    
    def _deactivate(self, plugin_id):
        """Деактивировать плагин."""
        entry = self._plugins.get(plugin_id)
        if not entry or not entry["active"]:
            return
        try:
            entry["instance"].deactivate()
        except Exception as e:
            print(f"[plugins] Ошибка деактивации {plugin_id}: {e}")
        entry["active"] = False
        self._prefs_groups.pop(plugin_id, None)
    
    def enable(self, plugin_id):
        """Включить плагин (активировать + запомнить)."""
        if plugin_id not in self._plugins:
            return
        self._enabled.add(plugin_id)
        self._activate(plugin_id)
        self._save_state()
        self.emit("changed")
    
    def disable(self, plugin_id):
        """Выключить плагин (деактивировать + запомнить)."""
        self._enabled.discard(plugin_id)
        self._deactivate(plugin_id)
        self._save_state()
        self.emit("changed")
    
    def is_enabled(self, plugin_id) -> bool:
        """Включён ли плагин."""
        return plugin_id in self._enabled
    
    def get_all(self) -> list[dict]:
        """Получить список всех обнаруженных плагинов.
        
        Returns:
            Список словарей: id, name, description, version, author, active, error.
        """
        result = []
        for pid, entry in self._plugins.items():
            meta = entry["instance"].meta
            result.append({
                "id": pid,
                "name": meta.get("name", pid),
                "description": meta.get("description", ""),
                "version": meta.get("version", ""),
                "author": meta.get("author", ""),
                "active": entry["active"],
                "error": entry.get("error"),
            })
        return result
    
    def get_menu_items(self) -> list[dict]:
        """Получить дополнительные пункты контекстного меню от плагинов.
        
        Returns:
            Список словарей с полями: id, label, callback.
        """
        return [
            {"id": item_id, "label": data["label"], "callback": data["callback"]}
            for item_id, data in self._menu_items.items()
        ]
    
    def has_prefs(self, plugin_id) -> bool:
        """Есть ли у плагина группы настроек."""
        return bool(self._prefs_groups.get(plugin_id))
    
    def get_prefs_groups(self, plugin_id) -> list:
        """Получить группы настроек плагина."""
        return list(self._prefs_groups.get(plugin_id, []))
    
    def shutdown(self):
        """Деактивировать все плагины при выходе."""
        for pid in list(self._plugins):
            if self._plugins[pid]["active"]:
                self._deactivate(pid)
    
    # --- Lifecycle уведомления ---
    
    def _notify_active(self, method, *args):
        """Вызвать метод у всех активных плагинов."""
        for pid, entry in self._plugins.items():
            if entry["active"]:
                try:
                    getattr(entry["instance"], method)(*args)
                except Exception as e:
                    print(f"[plugins] {pid}.{method}: {e}")
    
    def notify_app_launched(self, app_id):
        """Уведомить плагины о запуске приложения."""
        self._notify_active("on_app_launched", app_id)
    
    def notify_search(self, query):
        """Запросить у плагинов дополнительные результаты поиска."""
        results = []
        for pid, entry in self._plugins.items():
            if entry["active"]:
                try:
                    plugin_results = entry["instance"].on_search(query)
                    if plugin_results:
                        results.extend(plugin_results)
                except Exception as e:
                    print(f"[plugins] {pid}.on_search: {e}")
        return results
    
    def notify_window_shown(self):
        """Уведомить плагины о показе окна."""
        self._notify_active("on_window_shown")
    
    def notify_window_hidden(self):
        """Уведомить плагины о скрытии окна."""
        self._notify_active("on_window_hidden")
    
    def reload(self, plugin_id):
        """Перезагрузить плагин (hot-reload).
        
        Деактивирует плагин, перезагружает модуль с диска
        и активирует снова если был включён.
        """
        entry = self._plugins.get(plugin_id)
        if not entry:
            return
        
        was_enabled = plugin_id in self._enabled
        dir_name = entry["dir_name"]
        
        if entry["active"]:
            self._deactivate(plugin_id)
        
        # Удалить модуль из кэша Python
        module_name = f"adwyra_plugin_{dir_name}"
        sys.modules.pop(module_name, None)
        self._prefs_groups.pop(plugin_id, None)
        del self._plugins[plugin_id]
        self._enabled.discard(plugin_id)
        
        # Найти файл плагина (пользовательский приоритетнее)
        plugin_file = None
        for plugins_dir in (self._user_plugins_dir, self.SYSTEM_PLUGINS_DIR):
            pf = os.path.join(plugins_dir, dir_name, "plugin.py")
            if os.path.isfile(pf):
                plugin_file = pf
                break
        
        if not plugin_file:
            self.emit("changed")
            return
        
        # Перезагрузить
        self._load_plugin(dir_name, plugin_file)
        
        # Найти новый ID (мог измениться)
        new_id = None
        for pid, e in self._plugins.items():
            if e["dir_name"] == dir_name:
                new_id = pid
                break
        
        if new_id and was_enabled:
            self._enabled.add(new_id)
            self._activate(new_id)
            self._save_state()
        
        self.emit("changed")


# Глобальный экземпляр
plugin_manager = PluginManager()
