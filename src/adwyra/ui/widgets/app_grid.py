# -*- coding: utf-8 -*-
"""Сетка приложений с пагинацией."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio, GObject

from ...core import config, folders, favorites
from .app_tile import AppTile
from .folder_tile import FolderTile


class AppGrid(Gtk.Box):
    """Сетка с Carousel пагинацией."""
    
    __gtype_name__ = "AppGrid"
    
    __gsignals__ = {
        "app-launched": (GObject.SignalFlags.RUN_LAST, None, ()),
        "folder-open": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "folder-rename": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "folder-delete": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "drag-begin": (GObject.SignalFlags.RUN_LAST, None, ()),
        "drag-end": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._apps: list[Gio.AppInfo] = []
        
        self._build()
        favorites.connect("changed", lambda f: self._populate())
    
    def _build(self):
        # Carousel
        self._carousel = Adw.Carousel()
        self._carousel.set_allow_scroll_wheel(True)
        self._carousel.set_allow_mouse_drag(True)
        self._carousel.set_vexpand(True)
        self.append(self._carousel)
        
        # Индикатор (точки)
        self._dots = Adw.CarouselIndicatorDots()
        self._dots.set_carousel(self._carousel)
        self._dots.set_margin_bottom(16)
        self.append(self._dots)
    
    def set_apps(self, apps: list[Gio.AppInfo]):
        self._apps = apps
        self._populate()
    
    def _populate(self):
        self._dots.set_carousel(None)
        
        while self._carousel.get_n_pages() > 0:
            self._carousel.remove(self._carousel.get_nth_page(0))
        
        # Сортировка: закреплённые приложения в начале (в порядке favorites)
        fav_ids = favorites.get_all()
        fav_apps = []
        other_apps = []
        
        app_map = {a.get_id(): a for a in self._apps}
        
        # Сначала закреплённые в их порядке
        for app_id in fav_ids:
            if app_id in app_map:
                fav_apps.append(app_map[app_id])
        
        # Затем остальные
        for app in self._apps:
            if app.get_id() not in fav_ids:
                other_apps.append(app)
        
        # Элементы: папки + закреплённые + остальные
        items = []
        for fid in folders.get_ids():
            items.append(("folder", fid))
        for app in fav_apps:
            items.append(("app", app))
        for app in other_apps:
            items.append(("app", app))
        
        # Пагинация
        per_page = config.per_page
        
        for start in range(0, max(len(items), 1), per_page):
            page_items = items[start:start + per_page]
            page = self._create_page(page_items)
            self._carousel.append(page)
        
        self._dots.set_carousel(self._carousel)
    
    def _create_page(self, items) -> Gtk.Widget:
        if not items:
            lbl = Gtk.Label(label="Ничего не найдено")
            lbl.add_css_class("dim-label")
            return lbl
        
        cols = config.get("columns")
        rows = config.get("rows")
        
        # Используем Grid для фиксированной сетки
        grid = Gtk.Grid()
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        grid.set_margin_top(12)
        grid.set_margin_bottom(12)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.START)
        
        # Заполняем все ячейки (пустые - невидимые placeholder'ы)
        icon_size = config.get("icon_size")
        for r in range(rows):
            for c in range(cols):
                placeholder = Gtk.Box()
                placeholder.set_size_request(icon_size + 20, icon_size + 40)
                grid.attach(placeholder, c, r, 1, 1)
        
        # Добавляем реальные элементы
        idx = 0
        for typ, data in items:
            if typ == "folder":
                tile = FolderTile(data)
                tile.connect("open", lambda t, fid: self.emit("folder-open", fid))
                tile.connect("renamed", lambda t, fid: self.emit("folder-rename", fid))
                tile.connect("deleted", lambda t, fid: self.emit("folder-delete", fid))
            else:
                tile = AppTile(data)
                tile.connect("launched", lambda t: self.emit("app-launched"))
                tile.connect("folder-create", self._on_folder_create)
                tile.connect("fav-moved", self._on_fav_moved)
                tile.connect("drag-begin", lambda t: self.emit("drag-begin"))
                tile.connect("drag-end", lambda t: self.emit("drag-end"))
            
            row = idx // cols
            col = idx % cols
            # Удаляем placeholder и ставим тайл
            old = grid.get_child_at(col, row)
            if old:
                grid.remove(old)
            grid.attach(tile, col, row, 1, 1)
            idx += 1
        
        return grid
    
    def _on_folder_create(self, tile, app1: str, app2: str):
        folders.create("Новая папка", [app1, app2])
        self._populate()
    
    def _on_fav_moved(self, tile, moved_app: str, target_app: str):
        """Переместить закреплённое приложение."""
        if favorites.contains(target_app):
            favorites.move(moved_app, target_app)
    
    def refresh(self):
        self._populate()
