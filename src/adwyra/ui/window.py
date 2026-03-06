# -*- coding: utf-8 -*-
"""Главное окно лаунчера Adwyra.

Содержит основной интерфейс с сеткой приложений, поиском,
и встроенными страницами настроек и информации о программе.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, Gio, GLib

from .. import __version__, __app_name__
from ..core import config, folders, SearchService
from ..core.apps import app_service
from ..core.favorites import get_gnome_dock_apps
from .widgets import AppGrid, SearchBar

# GSettings схемы
GSETTINGS_MEDIA_KEYS = "org.gnome.settings-daemon.plugins.media-keys"
GSETTINGS_CUSTOM_KEYBINDING = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
GSETTINGS_WM = "org.gnome.desktop.wm.keybindings"
GSETTINGS_SHELL = "org.gnome.shell.keybindings"
ADWYRA_KEYBINDING_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/adwyra/"


class MainWindow(Adw.ApplicationWindow):
    """Главное окно приложения.
    
    Управляет навигацией между страницами (сетка, папка, настройки, о программе),
    обработкой горячих клавиш и взаимодействием с пользователем.
    """
    
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
        
        # Сбросить фокус при показе
        self.connect("show", self._on_show)
    
    def _on_show(self, widget):
        # Убрать фокус с поля поиска через idle чтобы сработало после GTK
        GLib.idle_add(self._clear_focus)
    
    def _clear_focus(self):
        self.set_focus(None)
        return False
    
    def _build(self):
        self.set_title("Adwyra")
        self.set_decorated(False)
        self._update_size()
        
        # Overlay для кнопки настроек
        overlay = Gtk.Overlay()
        self.set_content(overlay)
        
        # Stack для переключения видов
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_vexpand(True)
        self._stack.set_hhomogeneous(True)
        self._stack.set_vhomogeneous(True)
        overlay.set_child(self._stack)
        
        # === Главная страница ===
        main_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Поиск сверху (компактный, по центру)
        self._search_box = Gtk.Box()
        self._search_box.set_halign(Gtk.Align.CENTER)
        self._search_box.set_margin_top(12)
        self._search_box.set_margin_bottom(8)
        main_page.append(self._search_box)
        
        self._search = SearchBar()
        self._search.set_hexpand(False)
        self._search_box.append(self._search)
        
        # Сетка приложений
        self._grid = AppGrid()
        self._grid.set_valign(Gtk.Align.START)
        self._grid.set_vexpand(True)
        main_page.append(self._grid)
        
        self._stack.add_named(main_page, "main")
        
        # Контейнер папки с inline заголовком
        folder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        folder_box.set_margin_start(16)
        folder_box.set_margin_end(16)
        folder_box.set_margin_top(12)
        folder_box.set_margin_bottom(12)
        
        # Заголовок папки (inline)
        folder_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("dimmed")
        back_btn.connect("clicked", self._on_back)
        folder_header.append(back_btn)
        
        self._folder_title = Gtk.Label()
        self._folder_title.add_css_class("title-2")
        self._folder_title.set_hexpand(True)
        self._folder_title.set_halign(Gtk.Align.CENTER)
        folder_header.append(self._folder_title)
        
        self._folder_del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self._folder_del_btn.add_css_class("flat")
        self._folder_del_btn.add_css_class("dimmed")
        self._folder_del_btn.connect("clicked", self._on_folder_delete_btn)
        folder_header.append(self._folder_del_btn)
        
        folder_box.append(folder_header)
        
        # Сетка папки
        self._folder_grid = Gtk.Grid()
        self._folder_grid.set_row_homogeneous(True)
        self._folder_grid.set_column_homogeneous(True)
        self._folder_grid.set_column_spacing(8)
        self._folder_grid.set_row_spacing(8)
        self._folder_grid.set_halign(Gtk.Align.CENTER)
        self._folder_grid.set_valign(Gtk.Align.START)
        folder_box.append(self._folder_grid)
        
        folder_scroll = Gtk.ScrolledWindow()
        folder_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        folder_scroll.set_child(folder_box)
        self._stack.add_named(folder_scroll, "folder")
        
        # === Страница настроек ===
        self._prefs_page = self._build_prefs_page()
        prefs_scroll = Gtk.ScrolledWindow()
        prefs_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        prefs_scroll.set_child(self._prefs_page)
        self._stack.add_named(prefs_scroll, "prefs")
        
        # === Страница О программе ===
        self._about_page = self._build_about_page()
        about_scroll = Gtk.ScrolledWindow()
        about_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        about_scroll.set_child(self._about_page)
        self._stack.add_named(about_scroll, "about")
        
        # Кнопка настроек слева сверху (только на главной)
        self._prefs_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
        self._prefs_btn.set_tooltip_text("Настройки")
        self._prefs_btn.add_css_class("flat")
        self._prefs_btn.add_css_class("dim-label")
        self._prefs_btn.add_css_class("overlay-btn")
        self._prefs_btn.set_halign(Gtk.Align.START)
        self._prefs_btn.set_valign(Gtk.Align.START)
        self._prefs_btn.set_margin_start(12)
        self._prefs_btn.set_margin_top(12)
        self._prefs_btn.connect("clicked", self._open_prefs)
        overlay.add_overlay(self._prefs_btn)
        
        # Кнопка закрытия справа сверху
        self._close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")
        self._close_btn.set_tooltip_text("Закрыть")
        self._close_btn.add_css_class("flat")
        self._close_btn.add_css_class("dim-label")
        self._close_btn.add_css_class("overlay-btn")
        self._close_btn.set_halign(Gtk.Align.END)
        self._close_btn.set_valign(Gtk.Align.START)
        self._close_btn.set_margin_end(12)
        self._close_btn.set_margin_top(12)
        self._close_btn.connect("clicked", lambda b: self.close())
        overlay.add_overlay(self._close_btn)
    
    def _update_size(self):
        cols = config.get("columns")
        rows = config.get("rows")
        icon = config.get("icon_size")
        width = cols * (icon + 32) + 48
        height = rows * (icon + 48) + 80  # Учёт поиска и точек
        self.set_default_size(width, height)
        self.set_resizable(False)
    
    def _setup_events(self):
        # Клавиши
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)
        
        # Потеря фокуса окна
        self.connect("notify::is-active", self._on_active_changed)
    
    def _on_active_changed(self, window, pspec):
        if not self.is_active() and config.get("close_on_focus_lost"):
            GLib.timeout_add(100, self._check_close)
    
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
        folders.connect("changed", lambda f: self._load_apps())
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
        # Игнорируем клавиши когда открыт диалог
        if self._has_dialog:
            return False
        
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
            self._search.set_focusable(True)
            self._search.grab_focus()
            return True
        return False
    
    def _check_close(self):
        # Не закрывать если активны, есть дочернее окно, перетаскивание или диалог
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
        folder_data = folders.get(folder_id)
        self._folder_title.set_label(folder_data["name"] if folder_data else "Папка")
        self._folder_del_btn.set_visible(True)
        self._prefs_btn.set_visible(False)
        self._close_btn.set_visible(False)
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
        self._prefs_btn.set_visible(True)
        self._close_btn.set_visible(True)
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
        
        dialog = Gtk.Window()
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.set_decorated(False)
        dialog.set_resizable(False)
        dialog.add_css_class("compact-dialog")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        title = Gtk.Label(label="Переименовать")
        title.add_css_class("heading")
        box.append(title)
        
        entry = Gtk.Entry()
        entry.set_text(data.get("name", ""))
        entry.set_width_chars(18)
        box.append(entry)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(4)
        
        cancel_btn = Gtk.Button(label="Отмена")
        cancel_btn.connect("clicked", lambda b: dialog.close())
        btn_box.append(cancel_btn)
        
        ok_btn = Gtk.Button(label="OK")
        ok_btn.add_css_class("suggested-action")
        
        def on_ok(b):
            if entry.get_text().strip():
                folders.rename(folder_id, entry.get_text().strip())
            dialog.close()
        
        ok_btn.connect("clicked", on_ok)
        entry.connect("activate", on_ok)
        btn_box.append(ok_btn)
        
        box.append(btn_box)
        dialog.set_child(box)
        
        def on_close(w):
            self._has_dialog = False
            return False
        
        dialog.connect("close-request", on_close)
        dialog.present()
        entry.grab_focus()
    
    def _show_delete_dialog(self, folder_id):
        self._has_dialog = True
        
        dialog = Gtk.Window()
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.set_decorated(False)
        dialog.set_resizable(False)
        dialog.add_css_class("compact-dialog")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        title = Gtk.Label(label="Удалить папку?")
        title.add_css_class("heading")
        box.append(title)
        
        desc = Gtk.Label(label="Приложения вернутся в сетку")
        desc.add_css_class("dim-label")
        box.append(desc)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)
        
        cancel_btn = Gtk.Button(label="Отмена")
        cancel_btn.connect("clicked", lambda b: dialog.close())
        btn_box.append(cancel_btn)
        
        del_btn = Gtk.Button(label="Удалить")
        del_btn.add_css_class("destructive-action")
        
        def on_delete(b):
            folders.delete(folder_id)
            dialog.close()
            if self._current_folder == folder_id:
                self._on_back(None)
        
        del_btn.connect("clicked", on_delete)
        btn_box.append(del_btn)
        
        box.append(btn_box)
        dialog.set_child(box)
        
        def on_close(w):
            self._has_dialog = False
            return False
        
        dialog.connect("close-request", on_close)
        dialog.present()
    
    def _on_child_close(self, window):
        self._child_window = None
        return False
    
    def _open_prefs(self, btn):
        self._prefs_btn.set_visible(False)
        self._close_btn.set_visible(False)
        self._stack.set_visible_child_name("prefs")
    
    def _build_prefs_page(self):
        from gi.repository import Adw
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Заголовок с кнопкой назад
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_bottom(8)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("dimmed")
        back_btn.connect("clicked", self._on_back)
        header_box.append(back_btn)
        
        title = Gtk.Label(label="Настройки")
        title.add_css_class("title-2")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.CENTER)
        header_box.append(title)
        
        # Кнопка About
        about_btn = Gtk.Button.new_from_icon_name("help-about-symbolic")
        about_btn.add_css_class("flat")
        about_btn.add_css_class("dimmed")
        about_btn.set_tooltip_text("О программе")
        about_btn.connect("clicked", self._show_about)
        header_box.append(about_btn)
        
        box.append(header_box)
        
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
        hotkey_group.set_description("Введите сочетание, например: Super+A, Ctrl+Space")
        box.append(hotkey_group)
        
        # Получить текущую горячую клавишу
        current_hotkey = self._get_current_hotkey()
        
        self._hotkey_entry = Adw.EntryRow()
        self._hotkey_entry.set_title("Сочетание клавиш")
        self._hotkey_entry.set_text(current_hotkey or "")
        self._hotkey_entry.connect("apply", self._on_hotkey_apply)
        self._hotkey_entry.set_show_apply_button(True)
        
        clear_btn = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.add_css_class("flat")
        clear_btn.add_css_class("dimmed")
        clear_btn.set_tooltip_text("Удалить")
        clear_btn.connect("clicked", self._on_clear_hotkey)
        self._hotkey_entry.add_suffix(clear_btn)
        
        hotkey_group.add(self._hotkey_entry)
        
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
            settings = Gio.Settings.new(GSETTINGS_MEDIA_KEYS)
            customs = settings.get_strv("custom-keybindings")
            for path in customs:
                if "adwyra" in path:
                    custom = Gio.Settings.new_with_path(
                        GSETTINGS_CUSTOM_KEYBINDING,
                        path
                    )
                    binding = custom.get_string("binding")
                    if binding:
                        # Преобразуем в читаемый вид (GTK4)
                        success, keyval, mods = Gtk.accelerator_parse(binding)
                        if success and keyval:
                            return Gtk.accelerator_get_label(keyval, mods)
                        return binding
        except Exception:
            pass
        return None
    
    def _reset_dialog_flag(self):
        self._has_dialog = False
        return False
    
    def _normalize_hotkey(self, text):
        """Преобразовать текст в GTK accelerator формат."""
        if not text:
            return None
        text = text.strip()
        # Уже в формате GTK <Mod>key
        if text.startswith("<"):
            return text
        # Формат Super+A -> <Super>a
        parts = text.split("+")
        if len(parts) < 2:
            return None
        mods = []
        key = parts[-1].lower()
        for p in parts[:-1]:
            p = p.strip().lower()
            if p in ("super", "mod4"):
                mods.append("<Super>")
            elif p in ("ctrl", "control"):
                mods.append("<Control>")
            elif p in ("alt", "mod1"):
                mods.append("<Alt>")
            elif p == "shift":
                mods.append("<Shift>")
        if not mods:
            return None
        return "".join(mods) + key
    
    def _on_hotkey_apply(self, entry):
        """Применить введённую горячую клавишу."""
        text = entry.get_text()
        accel = self._normalize_hotkey(text)
        
        if not accel:
            # Показать ошибку
            entry.add_css_class("error")
            GLib.timeout_add(2000, lambda: entry.remove_css_class("error") or False)
            return
        
        # Проверка валидности (GTK4 возвращает 3 значения)
        success, keyval, mods = Gtk.accelerator_parse(accel)
        if not success or keyval == 0:
            entry.add_css_class("error")
            GLib.timeout_add(2000, lambda: entry.remove_css_class("error") or False)
            return
        
        # Проверить конфликт
        conflict = self._check_hotkey_conflict(accel)
        if conflict:
            entry.add_css_class("error")
            entry.set_text(f"Занято: {conflict}")
            GLib.timeout_add(2500, lambda: (entry.remove_css_class("error"), entry.set_text(text)) or False)
            return
        
        # Сохраняем
        self._save_hotkey(accel)
        label = Gtk.accelerator_get_label(keyval, mods)
        entry.set_text(label or text)
        entry.add_css_class("success")
        GLib.timeout_add(1500, lambda: entry.remove_css_class("success") or False)
    
    def _check_hotkey_conflict(self, accel):
        """Проверить, занято ли сочетание клавиш системой."""
        try:
            # Проверяем media-keys
            settings = Gio.Settings.new(GSETTINGS_MEDIA_KEYS)
            
            # Проверяем стандартные шорткаты
            for key in settings.list_keys():
                try:
                    val = settings.get_value(key)
                    if val.get_type_string() == 's':
                        if val.get_string() == accel:
                            return key.replace("-", " ").title()
                    elif val.get_type_string() == 'as':
                        if accel in val.get_strv():
                            return key.replace("-", " ").title()
                except Exception:
                    pass
            
            # Проверяем custom keybindings (кроме нашего)
            customs = settings.get_strv("custom-keybindings")
            for path in customs:
                if "adwyra" in path:
                    continue
                try:
                    custom = Gio.Settings.new_with_path(
                        GSETTINGS_CUSTOM_KEYBINDING,
                        path
                    )
                    if custom.get_string("binding") == accel:
                        return custom.get_string("name") or "Другой шорткат"
                except Exception:
                    pass
            
            # Проверяем WM keybindings
            try:
                wm = Gio.Settings.new(GSETTINGS_WM)
                for key in wm.list_keys():
                    bindings = wm.get_strv(key)
                    if accel in bindings:
                        return key.replace("-", " ").title()
            except Exception:
                pass
            
            # Проверяем shell keybindings
            try:
                shell = Gio.Settings.new(GSETTINGS_SHELL)
                for key in shell.list_keys():
                    bindings = shell.get_strv(key)
                    if accel in bindings:
                        return key.replace("-", " ").title()
            except Exception:
                pass
                
        except Exception:
            pass
        return None
    
    def _save_hotkey(self, accel):
        """Сохранить горячую клавишу в GNOME settings."""
        try:
            settings = Gio.Settings.new(GSETTINGS_MEDIA_KEYS)
            customs = list(settings.get_strv("custom-keybindings"))
            
            # Добавляем путь если его нет
            if ADWYRA_KEYBINDING_PATH not in customs:
                customs.append(ADWYRA_KEYBINDING_PATH)
                settings.set_strv("custom-keybindings", customs)
            
            # Настраиваем шорткат
            custom = Gio.Settings.new_with_path(
                GSETTINGS_CUSTOM_KEYBINDING,
                ADWYRA_KEYBINDING_PATH
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
            settings = Gio.Settings.new(GSETTINGS_MEDIA_KEYS)
            customs = list(settings.get_strv("custom-keybindings"))
            
            if ADWYRA_KEYBINDING_PATH in customs:
                customs.remove(ADWYRA_KEYBINDING_PATH)
                settings.set_strv("custom-keybindings", customs)
            
            # Очищаем binding
            custom = Gio.Settings.new_with_path(
                GSETTINGS_CUSTOM_KEYBINDING,
                ADWYRA_KEYBINDING_PATH
            )
            custom.reset("name")
            custom.reset("command")
            custom.reset("binding")
            
            Gio.Settings.sync()
            self._hotkey_entry.set_text("")
        except Exception as e:
            print(f"Ошибка удаления горячей клавиши: {e}")
    
    def _on_config_changed(self, cfg, key, val):
        if key in ("columns", "rows", "icon_size", "hide_dock_apps"):
            self._update_size()
            self._load_apps()
    
    def _show_about(self, btn):
        """Показать страницу О программе."""
        self._stack.set_visible_child_name("about")
    
    def _build_about_page(self):
        """Создать страницу О программе."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Заголовок с кнопкой назад
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_bottom(4)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("dimmed")
        back_btn.connect("clicked", lambda b: self._stack.set_visible_child_name("prefs"))
        header_box.append(back_btn)
        
        title = Gtk.Label(label="О программе")
        title.add_css_class("title-2")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.CENTER)
        header_box.append(title)
        
        # Spacer для центрирования
        spacer = Gtk.Box()
        spacer.set_size_request(34, -1)
        header_box.append(spacer)
        
        box.append(header_box)
        
        # Иконка и название
        icon = Gtk.Image.new_from_icon_name("com.github.adwyra")
        icon.set_pixel_size(96)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_margin_top(8)
        box.append(icon)
        
        name_label = Gtk.Label(label=__app_name__)
        name_label.add_css_class("title-2")
        name_label.set_halign(Gtk.Align.CENTER)
        name_label.set_margin_top(4)
        box.append(name_label)
        
        version_label = Gtk.Label(label=f"Версия {__version__}")
        version_label.add_css_class("dim-label")
        version_label.set_halign(Gtk.Align.CENTER)
        box.append(version_label)
        
        desc_label = Gtk.Label(label="Минималистичный лаунчер приложений для GNOME")
        desc_label.set_halign(Gtk.Align.CENTER)
        desc_label.set_margin_top(4)
        desc_label.set_wrap(True)
        box.append(desc_label)
        
        # Ссылка
        link_btn = Gtk.LinkButton.new_with_label(
            "https://github.com/cheviiot/adwyra",
            "GitHub"
        )
        link_btn.set_halign(Gtk.Align.CENTER)
        link_btn.set_margin_top(8)
        box.append(link_btn)
        
        # Лицензия
        license_label = Gtk.Label(label="Лицензия: GPL-3.0")
        license_label.add_css_class("dim-label")
        license_label.set_halign(Gtk.Align.CENTER)
        license_label.set_margin_top(8)
        box.append(license_label)
        
        return box
