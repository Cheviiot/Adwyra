# -*- coding: utf-8 -*-
"""Диалог настроек."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from ..core import config


class PreferencesDialog(Adw.PreferencesWindow):
    """Окно настроек."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Настройки")
        self.set_default_size(400, 500)
        
        self._build()
    
    def _build(self):
        page = Adw.PreferencesPage()
        self.add(page)
        
        # Внешний вид
        appearance = Adw.PreferencesGroup()
        appearance.set_title("Внешний вид")
        page.add(appearance)
        
        # Тема
        theme_row = Adw.ComboRow()
        theme_row.set_title("Тема")
        theme_row.set_model(Gtk.StringList.new(["Системная", "Светлая", "Тёмная"]))
        theme_map = {"system": 0, "light": 1, "dark": 2}
        theme_row.set_selected(theme_map.get(config.get("theme"), 0))
        theme_row.connect("notify::selected", self._on_theme)
        appearance.add(theme_row)
        
        # Размер иконок
        icon_row = Adw.ComboRow()
        icon_row.set_title("Размер иконок")
        icon_row.set_model(Gtk.StringList.new(["Маленький (56)", "Средний (72)", "Большой (96)"]))
        icon_map = {56: 0, 72: 1, 96: 2}
        icon_row.set_selected(icon_map.get(config.get("icon_size"), 1))
        icon_row.connect("notify::selected", self._on_icon_size)
        appearance.add(icon_row)
        
        # Сетка
        grid_group = Adw.PreferencesGroup()
        grid_group.set_title("Сетка")
        page.add(grid_group)
        
        # Колонки
        cols_row = Adw.SpinRow.new_with_range(4, 10, 1)
        cols_row.set_title("Колонки")
        cols_row.set_value(config.get("columns"))
        cols_row.connect("notify::value", lambda r, p: config.set("columns", int(r.get_value())))
        grid_group.add(cols_row)
        
        # Строки
        rows_row = Adw.SpinRow.new_with_range(3, 8, 1)
        rows_row.set_title("Строки")
        rows_row.set_value(config.get("rows"))
        rows_row.connect("notify::value", lambda r, p: config.set("rows", int(r.get_value())))
        grid_group.add(rows_row)
        
        # Поведение
        behavior = Adw.PreferencesGroup()
        behavior.set_title("Поведение")
        page.add(behavior)
        
        # Закрывать при запуске
        close_launch = Adw.SwitchRow()
        close_launch.set_title("Закрывать при запуске")
        close_launch.set_active(config.get("close_on_launch"))
        close_launch.connect("notify::active", lambda r, p: config.set("close_on_launch", r.get_active()))
        behavior.add(close_launch)
        
        # Закрывать при потере фокуса
        close_focus = Adw.SwitchRow()
        close_focus.set_title("Закрывать при потере фокуса")
        close_focus.set_active(config.get("close_on_focus_lost"))
        close_focus.connect("notify::active", lambda r, p: config.set("close_on_focus_lost", r.get_active()))
        behavior.add(close_focus)
        
        # Скрывать закреплённые в Dock
        hide_dock = Adw.SwitchRow()
        hide_dock.set_title("Скрывать закреплённые в Dock")
        hide_dock.set_active(config.get("hide_dock_apps"))
        hide_dock.connect("notify::active", lambda r, p: config.set("hide_dock_apps", r.get_active()))
        behavior.add(hide_dock)
    
    def _on_theme(self, row, param):
        themes = ["system", "light", "dark"]
        config.set("theme", themes[row.get_selected()])
        self._apply_theme()
    
    def _on_icon_size(self, row, param):
        sizes = [56, 72, 96]
        config.set("icon_size", sizes[row.get_selected()])
    
    def _apply_theme(self):
        theme = config.get("theme")
        style_manager = Adw.StyleManager.get_default()
        
        if theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
