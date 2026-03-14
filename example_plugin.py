# Пример плагина для Adwyra
#
# Плагины распространяются через Stapler как отдельные пакеты.
# Системный путь: /usr/lib/adwyra/plugins/<имя>/plugin.py
# Для разработки: ~/.config/adwyra/plugins/<имя>/plugin.py
#
# Структура пакета плагина:
#   /usr/lib/adwyra/plugins/my_plugin/
#       plugin.py          # Точка входа (обязателен)
#       # ... другие файлы
#
# Файл plugin.py должен содержать класс Plugin, наследующий AdwyraPlugin.

from adwyra.core.plugins import AdwyraPlugin


class Plugin(AdwyraPlugin):
    meta = {
        "id": "my_plugin",
        "name": "Мой плагин",
        "description": "Описание плагина",
        "version": "1.0",
        "author": "Автор",
        "min_app_version": "",  # Минимальная версия Adwyra (например "0.5.0"), пусто = любая
    }

    def activate(self):
        """Вызывается при включении плагина."""

        # Добавить пункт в контекстное меню приложений
        self._menu_id = self.ctx.add_context_menu_item(
            "Мой пункт меню",
            self._on_menu_click
        )

        # Добавить группу настроек плагина (отображается на отдельной странице,
        # доступной по кнопке ⚙ рядом с переключателем плагина)
        # import gi
        # gi.require_version("Adw", "1")
        # from gi.repository import Adw
        # self._group = Adw.PreferencesGroup()
        # self._group.set_title("Настройки моего плагина")
        # row = Adw.SwitchRow()
        # row.set_title("Опция")
        # self._group.add(row)
        # self.ctx.add_prefs_group(self._group)

        # Добавить свою страницу в навигацию
        # from gi.repository import Gtk
        # page = Gtk.Label(label="Моя страница")
        # self.ctx.add_page("my_page", page, "Мой плагин")

        # Использовать собственное хранилище настроек плагина
        # count = self.ctx.get_plugin_config("launch_count", 0)
        # self.ctx.set_plugin_config("launch_count", count + 1)

    def deactivate(self):
        """Вызывается при выключении плагина."""
        if self._menu_id:
            self.ctx.remove_context_menu_item(self._menu_id)
            self._menu_id = None

        # self.ctx.remove_prefs_group(self._group)
        # self.ctx.remove_page("my_page")

    # --- Lifecycle хуки (необязательные) ---

    def on_app_launched(self, app_id):
        """Вызывается при запуске любого приложения."""
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

    def _on_menu_click(self, app_id):
        """Вызывается при выборе пункта меню. app_id — ID приложения."""
        print(f"Клик по приложению: {app_id}")


# === Доступные методы ctx (PluginContext) ===
#
# --- Собственное хранилище плагина ---
#
# ctx.get_plugin_config(key, default=None)
#     Прочитать значение из ~/.config/adwyra/plugin_data/<id>/config.json
#
# ctx.set_plugin_config(key, value)
#     Записать значение в конфигурацию плагина.
#
# ctx.get_data_dir()
#     Директория для файлов плагина: ~/.config/adwyra/plugin_data/<id>/
#
# --- UI хуки ---
#
# ctx.add_context_menu_item(label, callback) -> item_id
#     Добавить пункт в ПКМ-меню на тайлах приложений.
#     callback(app_id: str) вызывается при выборе пункта.
#
# ctx.remove_context_menu_item(item_id)
#     Убрать пункт из контекстного меню.
#
# ctx.add_prefs_group(group)
#     Добавить Adw.PreferencesGroup в настройки плагина.
#     Отображается на отдельной странице (кнопка ⚙ во вкладке «Плагины»).
#
# ctx.remove_prefs_group(group)
#     Убрать группу настроек плагина.
#
# ctx.add_page(page_id, widget, title)
#     Добавить страницу (Gtk.Widget) в стек навигации.
#
# ctx.remove_page(page_id)
#     Убрать страницу из стека.
#
# --- Чтение данных приложения ---
#
# ctx.get_config(key, default=None)
#     Прочитать значение из конфигурации Adwyra.
#
# ctx.get_apps()
#     Получить список всех приложений (Gio.AppInfo).
