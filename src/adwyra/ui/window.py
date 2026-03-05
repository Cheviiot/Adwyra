# -*- coding: utf-8 -*-
"""Главное окно лаунчера."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, Gio, GLib

from ..core import config, folders, SearchService
from ..core.apps import app_service
from ..core.favorites import get_gnome_dock_apps
from .widgets import AppGrid, SearchBar


class MainWindow(Adw.ApplicationWindow):
    """Главное окно."""
    
    def __init__(self, app, **kwargs):
        super().__init__(application=app, **kwargs)
        self._child_window = None
        self._is_dragging = False
        self._has_dialog = False
        self._search_svc = SearchService()
        self._current_folder = None
        
        self._build()
        self._setup_events()
        self._connect_signals()
        self._load_apps()
    
    def _build(self):
        self.set_title("Adwyra")
        self.set_decorated(False)
        self._update_size()
        
        # Overlay для кнопки настроек
        overlay = Gtk.Overlay()
        self.set_content(overlay)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.set_child(main_box)
        
        # Панель заголовка папки (скрыта по умолчанию)
        self._folder_header = Gtk.Box()
        self._folder_header.set_margin_top(8)
        self._folder_header.set_margin_start(12)
        self._folder_header.set_margin_end(12)
        self._folder_header.set_visible(False)
        main_box.append(self._folder_header)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("circular")
        back_btn.connect("clicked", self._on_back)
        self._folder_header.append(back_btn)
        
        self._folder_title = Gtk.Label()
        self._folder_title.set_hexpand(True)
        self._folder_title.add_css_class("title-4")
        self._folder_header.append(self._folder_title)
        
        self._folder_del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self._folder_del_btn.add_css_class("circular")
        self._folder_del_btn.connect("clicked", self._on_folder_delete_btn)
        self._folder_header.append(self._folder_del_btn)
        
        # Поиск сверху (компактный, по центру)
        self._search_box = Gtk.Box()
        self._search_box.set_halign(Gtk.Align.CENTER)
        self._search_box.set_margin_top(12)
        self._search_box.set_margin_bottom(8)
        main_box.append(self._search_box)
        
        self._search = SearchBar()
        self._search.set_hexpand(False)
        self._search_box.append(self._search)
        
        # Stack для переключения видов
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_vexpand(True)
        main_box.append(self._stack)
        
        # Главная сетка
        self._grid = AppGrid()
        self._stack.add_named(self._grid, "main")
        
        # Сетка папки (фиксированный Grid)
        self._folder_grid = Gtk.Grid()
        self._folder_grid.set_row_homogeneous(True)
        self._folder_grid.set_column_homogeneous(True)
        self._folder_grid.set_column_spacing(8)
        self._folder_grid.set_row_spacing(8)
        self._folder_grid.set_margin_start(16)
        self._folder_grid.set_margin_end(16)
        self._folder_grid.set_margin_top(12)
        self._folder_grid.set_margin_bottom(12)
        self._folder_grid.set_halign(Gtk.Align.CENTER)
        self._folder_grid.set_valign(Gtk.Align.START)
        
        folder_scroll = Gtk.ScrolledWindow()
        folder_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        folder_scroll.set_child(self._folder_grid)
        self._stack.add_named(folder_scroll, "folder")
        
        # Страница настроек
        self._prefs_page = self._build_prefs_page()
        prefs_scroll = Gtk.ScrolledWindow()
        prefs_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        prefs_scroll.set_child(self._prefs_page)
        self._stack.add_named(prefs_scroll, "prefs")
        
        # Кнопка настроек справа снизу
        self._prefs_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
        self._prefs_btn.set_tooltip_text("Настройки")
        self._prefs_btn.add_css_class("circular")
        self._prefs_btn.set_halign(Gtk.Align.END)
        self._prefs_btn.set_valign(Gtk.Align.END)
        self._prefs_btn.set_margin_end(12)
        self._prefs_btn.set_margin_bottom(12)
        self._prefs_btn.connect("clicked", self._open_prefs)
        overlay.add_overlay(self._prefs_btn)
    
    def _update_size(self):
        cols = config.get("columns")
        rows = config.get("rows")
        icon = config.get("icon_size")
        size = max(cols, rows) * (icon + 32) + 48
        self.set_default_size(size, size)
        self.set_resizable(False)
    
    def _setup_events(self):
        # Клавиши
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)
        
        # Потеря фокуса
        if config.get("close_on_focus_lost"):
            focus = Gtk.EventControllerFocus()
            focus.connect("leave", lambda c: GLib.timeout_add(100, self._check_close))
            self.add_controller(focus)
    
    def _connect_signals(self):
        self._search.connect("query-changed", self._on_search)
        self._search_svc.connect("results", self._on_results)
        
        self._grid.connect("app-launched", self._on_launched)
        self._grid.connect("folder-open", self._on_folder_open)
        self._grid.connect("folder-rename", self._on_folder_rename)
        self._grid.connect("folder-delete", self._on_folder_delete)
        self._grid.connect("drag-begin", self._on_drag_begin)
        self._grid.connect("drag-end", self._on_drag_end)
        
        app_service.connect("changed", lambda s: self._load_apps())
        folders.connect("changed", lambda f: self._grid.refresh())
        config.connect("changed", self._on_config_changed)
    
    def _on_drag_begin(self, grid):
        self._is_dragging = True
    
    def _on_drag_end(self, grid):
        self._is_dragging = False
    
    def _load_apps(self):
        apps = app_service.get_all()
        exclude = set(folders.get_all_app_ids())
        
        # Скрывать закреплённые в Dock
        if config.get("hide_dock_apps"):
            exclude.update(get_gnome_dock_apps())
        
        self._search_svc.set_apps(apps)
        self._search_svc.set_exclude(exclude)
        
        filtered = [a for a in apps if a.get_id() not in exclude]
        self._grid.set_apps(filtered)
    
    def _on_search(self, search_bar, query):
        self._search_svc.search(query)
    
    def _on_results(self, svc, apps):
        self._grid.set_apps(apps)
    
    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            if self._current_folder:
                self._on_back(None)
                return True
            if self._search.get_text():
                self._search.clear()
                return True
            self.close()
            return True
        if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_f:
            self._search.grab_focus()
            return True
        return False
    
    def _check_close(self):
        if self.is_active() or self._child_window or self._is_dragging or self._has_dialog:
            return False
        self.close()
        return False
    
    def _on_launched(self, grid):
        if config.get("close_on_launch"):
            self.close()
    
    def _on_folder_open(self, grid, folder_id):
        self._current_folder = folder_id
        self._populate_folder(folder_id)
        self._folder_title.set_label(folders.get_folder_name(folder_id))
        self._folder_del_btn.set_visible(True)
        self._folder_header.set_visible(True)
        self._search_box.set_visible(False)
        self._prefs_btn.set_visible(False)
        self._stack.set_visible_child_name("folder")
    
    def _populate_folder(self, folder_id):
        from .folder_popup import FolderAppTile
        
        # Очистить Grid
        while True:
            child = self._folder_grid.get_first_child()
            if not child:
                break
            self._folder_grid.remove(child)
        
        data = folders.get(folder_id)
        if not data:
            return
        
        all_apps = app_service.get_all()
        app_map = {a.get_id(): a for a in all_apps}
        
        cols = config.get("columns")
        rows = config.get("rows")
        icon_size = config.get("icon_size")
        
        # Заполняем все ячейки placeholder'ами
        for r in range(rows):
            for c in range(cols):
                placeholder = Gtk.Box()
                placeholder.set_size_request(icon_size + 20, icon_size + 40)
                self._folder_grid.attach(placeholder, c, r, 1, 1)
        
        # Добавляем реальные элементы
        idx = 0
        for app_id in data.get("apps", []):
            app_info = app_map.get(app_id)
            if app_info:
                tile = FolderAppTile(app_info)
                tile.connect("launched", self._on_folder_app_launched)
                tile.connect("remove", self._on_app_remove_from_folder)
                row = idx // cols
                col = idx % cols
                old = self._folder_grid.get_child_at(col, row)
                if old:
                    self._folder_grid.remove(old)
                self._folder_grid.attach(tile, col, row, 1, 1)
                idx += 1
    
    def _on_folder_app_launched(self, tile):
        if config.get("close_on_launch"):
            self.close()
    
    def _on_app_remove_from_folder(self, tile, app_id):
        if self._current_folder:
            folders.remove_app(self._current_folder, app_id)
            self._populate_folder(self._current_folder)
    
    def _on_back(self, btn):
        self._current_folder = None
        self._folder_header.set_visible(False)
        self._folder_del_btn.set_visible(True)
        self._search_box.set_visible(True)
        self._prefs_btn.set_visible(True)
        self._stack.set_visible_child_name("main")
        self._load_apps()
    
    def _on_folder_delete_btn(self, btn):
        if self._current_folder:
            self._show_delete_dialog(self._current_folder)
    
    def _on_folder_rename(self, grid, folder_id):
        self._show_rename_dialog(folder_id)
    
    def _on_folder_delete(self, grid, folder_id):
        self._show_delete_dialog(folder_id)
    
    def _show_rename_dialog(self, folder_id):
        data = folders.get(folder_id)
        if not data:
            return
        
        self._has_dialog = True
        dialog = Adw.MessageDialog.new(self, "Переименовать")
        dialog.add_response("cancel", "Отмена")
        dialog.add_response("ok", "OK")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        
        entry = Gtk.Entry()
        entry.set_text(data.get("name", ""))
        entry.set_margin_start(24)
        entry.set_margin_end(24)
        dialog.set_extra_child(entry)
        
        def on_resp(d, r):
            self._has_dialog = False
            if r == "ok" and entry.get_text().strip():
                folders.rename(folder_id, entry.get_text().strip())
        
        dialog.connect("response", on_resp)
        dialog.present()
    
    def _show_delete_dialog(self, folder_id):
        self._has_dialog = True
        dialog = Adw.MessageDialog.new(self, "Удалить папку?")
        dialog.set_body("Приложения вернутся в главную сетку.")
        dialog.add_response("cancel", "Отмена")
        dialog.add_response("delete", "Удалить")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def on_resp(d, r):
            self._has_dialog = False
            if r == "delete":
                folders.delete(folder_id)
                if self._current_folder == folder_id:
                    self._on_back(None)
        
        dialog.connect("response", on_resp)
        dialog.present()
    
    def _on_child_close(self, window):
        self._child_window = None
        return False
    
    def _open_prefs(self, btn):
        self._folder_title.set_label("Настройки")
        self._folder_del_btn.set_visible(False)
        self._folder_header.set_visible(True)
        self._search_box.set_visible(False)
        self._prefs_btn.set_visible(False)
        self._stack.set_visible_child_name("prefs")
    
    def _build_prefs_page(self):
        from gi.repository import Adw
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Внешний вид
        appearance = Adw.PreferencesGroup()
        appearance.set_title("Внешний вид")
        box.append(appearance)
        
        # Тема
        theme_row = Adw.ComboRow()
        theme_row.set_title("Тема")
        theme_row.set_model(Gtk.StringList.new(["Системная", "Светлая", "Тёмная"]))
        theme_map = {"system": 0, "light": 1, "dark": 2}
        theme_row.set_selected(theme_map.get(config.get("theme"), 0))
        theme_row.connect("notify::selected", self._on_theme_change)
        appearance.add(theme_row)
        
        # Размер иконок
        icon_row = Adw.ComboRow()
        icon_row.set_title("Размер иконок")
        icon_row.set_model(Gtk.StringList.new(["Маленький (56)", "Средний (72)", "Большой (96)"]))
        icon_map = {56: 0, 72: 1, 96: 2}
        icon_row.set_selected(icon_map.get(config.get("icon_size"), 1))
        icon_row.connect("notify::selected", self._on_icon_size_change)
        appearance.add(icon_row)
        
        # Сетка
        grid_group = Adw.PreferencesGroup()
        grid_group.set_title("Сетка")
        box.append(grid_group)
        
        cols_row = Adw.SpinRow.new_with_range(4, 10, 1)
        cols_row.set_title("Колонки")
        cols_row.set_value(config.get("columns"))
        cols_row.connect("notify::value", lambda r, p: config.set("columns", int(r.get_value())))
        grid_group.add(cols_row)
        
        rows_row = Adw.SpinRow.new_with_range(3, 8, 1)
        rows_row.set_title("Строки")
        rows_row.set_value(config.get("rows"))
        rows_row.connect("notify::value", lambda r, p: config.set("rows", int(r.get_value())))
        grid_group.add(rows_row)
        
        # Поведение
        behavior = Adw.PreferencesGroup()
        behavior.set_title("Поведение")
        box.append(behavior)
        
        close_launch = Adw.SwitchRow()
        close_launch.set_title("Закрывать при запуске")
        close_launch.set_active(config.get("close_on_launch"))
        close_launch.connect("notify::active", lambda r, p: config.set("close_on_launch", r.get_active()))
        behavior.add(close_launch)
        
        close_focus = Adw.SwitchRow()
        close_focus.set_title("Закрывать при потере фокуса")
        close_focus.set_active(config.get("close_on_focus_lost"))
        close_focus.connect("notify::active", lambda r, p: config.set("close_on_focus_lost", r.get_active()))
        behavior.add(close_focus)
        
        hide_dock = Adw.SwitchRow()
        hide_dock.set_title("Скрывать закреплённые в Dock")
        hide_dock.set_active(config.get("hide_dock_apps"))
        hide_dock.connect("notify::active", lambda r, p: config.set("hide_dock_apps", r.get_active()))
        behavior.add(hide_dock)
        
        # Горячая клавиша
        hotkey_group = Adw.PreferencesGroup()
        hotkey_group.set_title("Горячая клавиша")
        hotkey_group.set_description("Назначьте клавишу для быстрого вызова")
        box.append(hotkey_group)
        
        # Получить текущую горячую клавишу
        current_hotkey = self._get_current_hotkey()
        
        self._hotkey_row = Adw.ActionRow()
        self._hotkey_row.set_title("Горячая клавиша")
        self._hotkey_row.set_subtitle(current_hotkey or "Не назначена")
        self._hotkey_row.set_activatable(True)
        self._hotkey_row.connect("activated", self._on_capture_hotkey)
        
        if current_hotkey:
            clear_btn = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
            clear_btn.set_valign(Gtk.Align.CENTER)
            clear_btn.add_css_class("flat")
            clear_btn.set_tooltip_text("Удалить")
            clear_btn.connect("clicked", self._on_clear_hotkey)
            self._hotkey_row.add_suffix(clear_btn)
        
        hotkey_group.add(self._hotkey_row)
        
        return box
    
    def _on_theme_change(self, row, param):
        from gi.repository import Adw
        themes = ["system", "light", "dark"]
        theme = themes[row.get_selected()]
        config.set("theme", theme)
        style = Adw.StyleManager.get_default()
        if theme == "dark":
            style.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif theme == "light":
            style.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style.set_color_scheme(Adw.ColorScheme.DEFAULT)
    
    def _on_icon_size_change(self, row, param):
        sizes = [56, 72, 96]
        config.set("icon_size", sizes[row.get_selected()])
    
    def _get_current_hotkey(self):
        """Получить текущую горячую клавишу из GNOME settings."""
        try:
            settings = Gio.Settings.new("org.gnome.settings-daemon.plugins.media-keys")
            customs = settings.get_strv("custom-keybindings")
            for path in customs:
                if "adwyra" in path:
                    custom = Gio.Settings.new_with_path(
                        "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding",
                        path
                    )
                    binding = custom.get_string("binding")
                    if binding:
                        # Преобразуем в читаемый вид
                        keyval, mods = Gtk.accelerator_parse(binding)
                        if keyval:
                            return Gtk.accelerator_get_label(keyval, mods)
                        return binding
        except Exception:
            pass
        return None
    
    def _on_capture_hotkey(self, row):
        """Показать диалог захвата горячей клавиши."""
        dialog = Adw.MessageDialog.new(self, "Нажмите сочетание клавиш")
        dialog.set_body("Нажмите нужное сочетание клавиш для вызова Adwyra.\nНапример: Super+A, Ctrl+Space")
        dialog.add_response("cancel", "Отмена")
        dialog.set_close_response("cancel")
        
        # Метка для отображения нажатых клавиш
        key_label = Gtk.Label(label="Ожидание...")
        key_label.add_css_class("title-1")
        key_label.set_margin_top(20)
        key_label.set_margin_bottom(20)
        dialog.set_extra_child(key_label)
        
        self._captured_hotkey = None
        
        def on_key(controller, keyval, keycode, state):
            # Игнорируем одиночные модификаторы
            if keyval in (Gdk.KEY_Control_L, Gdk.KEY_Control_R,
                          Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
                          Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
                          Gdk.KEY_Super_L, Gdk.KEY_Super_R,
                          Gdk.KEY_Meta_L, Gdk.KEY_Meta_R):
                return False
            
            mods = state & Gtk.accelerator_get_default_mod_mask()
            accel = Gtk.accelerator_name(keyval, mods)
            if accel:
                # Преобразуем в читаемый вид
                label = Gtk.accelerator_get_label(keyval, mods)
                key_label.set_label(label)
                self._captured_hotkey = accel
                # Добавляем кнопку подтверждения
                if "apply" not in [r for r in ["cancel"]]:
                    dialog.add_response("apply", "Применить")
                    dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
            return True
        
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", on_key)
        dialog.add_controller(key_controller)
        
        def on_response(dlg, response):
            if response == "apply" and self._captured_hotkey:
                self._save_hotkey(self._captured_hotkey)
                # Обновить UI
                label = Gtk.accelerator_get_label(
                    *Gtk.accelerator_parse(self._captured_hotkey)
                )
                self._hotkey_row.set_subtitle(label or self._captured_hotkey)
            self._has_dialog = False
        
        self._has_dialog = True
        dialog.connect("response", on_response)
        dialog.present()
    
    def _save_hotkey(self, accel):
        """Сохранить горячую клавишу в GNOME settings."""
        import subprocess
        try:
            settings = Gio.Settings.new("org.gnome.settings-daemon.plugins.media-keys")
            customs = list(settings.get_strv("custom-keybindings"))
            
            # Путь для нашего шортката
            path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/adwyra/"
            
            # Добавляем путь если его нет
            if path not in customs:
                customs.append(path)
                settings.set_strv("custom-keybindings", customs)
            
            # Настраиваем шорткат
            custom = Gio.Settings.new_with_path(
                "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding",
                path
            )
            custom.set_string("name", "Adwyra")
            custom.set_string("command", "adwyra --toggle")
            custom.set_string("binding", accel)
            
            Gio.Settings.sync()
        except Exception as e:
            print(f"Ошибка сохранения горячей клавиши: {e}")
    
    def _on_clear_hotkey(self, btn):
        """Удалить горячую клавишу."""
        try:
            settings = Gio.Settings.new("org.gnome.settings-daemon.plugins.media-keys")
            customs = list(settings.get_strv("custom-keybindings"))
            
            path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/adwyra/"
            
            if path in customs:
                customs.remove(path)
                settings.set_strv("custom-keybindings", customs)
            
            # Очищаем binding
            custom = Gio.Settings.new_with_path(
                "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding",
                path
            )
            custom.reset("name")
            custom.reset("command")
            custom.reset("binding")
            
            Gio.Settings.sync()
            self._hotkey_row.set_subtitle("Не назначена")
        except Exception as e:
            print(f"Ошибка удаления горячей клавиши: {e}")
    
    def _on_config_changed(self, cfg, key, val):
        if key in ("columns", "rows", "icon_size", "hide_dock_apps"):
            self._update_size()
            self._load_apps()
