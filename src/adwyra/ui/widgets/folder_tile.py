# -*- coding: utf-8 -*-
"""Тайл папки.

Отображает превью 3x3 из иконок приложений внутри папки
и принимает drop приложений для добавления в папку.
"""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, Gio, GObject, Pango

from ...core import config, folders, favorites
from ...i18n import _


class FolderTile(Gtk.Button):
    """Тайл папки с превью 3x3."""
    
    __gtype_name__ = "FolderTile"
    
    __gsignals__ = {
        "open": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "renamed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "deleted": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self, folder_id: str):
        super().__init__()
        self.folder_id = folder_id
        self._folders_handler = None
        
        self.add_css_class("flat")
        
        self._build()
        self._setup_drop()
        self._setup_menu()
        
        self.connect("clicked", lambda b: self.emit("open", folder_id))
        self._folders_handler = folders.connect("changed", self._refresh)
        self.connect("destroy", self._on_destroy)
    
    def _on_destroy(self, widget):
        if self._folders_handler:
            folders.disconnect(self._folders_handler)
            self._folders_handler = None
    
    def _build(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_halign(Gtk.Align.CENTER)
        self.set_child(box)
        
        # Превью 3x3
        self._grid = Gtk.Grid()
        self._grid.add_css_class("folder-preview")
        self._grid.set_row_homogeneous(True)
        self._grid.set_column_homogeneous(True)
        self._grid.set_row_spacing(2)
        self._grid.set_column_spacing(2)
        box.append(self._grid)
        
        self._update_preview()
        
        # Название
        self._label = Gtk.Label()
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        self._label.set_max_width_chars(12)
        self._label.add_css_class("app-label")
        box.append(self._label)
        
        self._refresh(None)
    
    def _update_preview(self):
        while child := self._grid.get_first_child():
            self._grid.remove(child)
        
        data = folders.get(self.folder_id)
        apps = data.get("apps", []) if data else []
        preview_size = config.get("icon_size") // 3
        
        for i in range(9):
            row, col = i // 3, i % 3
            
            # Контейнер для закругления
            frame = Gtk.Frame()
            frame.add_css_class("icon-frame-small")
            frame.set_overflow(Gtk.Overflow.HIDDEN)
            
            img = Gtk.Image()
            if i < len(apps):
                info = Gio.DesktopAppInfo.new(apps[i])
                if info and info.get_icon():
                    img = Gtk.Image.new_from_gicon(info.get_icon())
            img.set_pixel_size(preview_size)
            frame.set_child(img)
            self._grid.attach(frame, col, row, 1, 1)
    
    def _setup_drop(self):
        drop = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
        drop.connect("enter", self._on_enter)
        drop.connect("leave", self._on_leave)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)
    
    def _on_enter(self, target, x, y):
        # Получить app_id из drag
        drop = target.get_drop()
        if drop:
            def on_read(drop, result):
                try:
                    value = drop.read_value_finish(result)
                    if isinstance(value, str) and favorites.contains(value):
                        self.remove_css_class("drop-hover")
                    else:
                        self.add_css_class("drop-hover")
                except Exception:
                    pass
            
            drop.read_value_async(str, 0, None, on_read)
        return Gdk.DragAction.MOVE
    
    def _on_leave(self, target):
        self.remove_css_class("drop-hover")
    
    def _on_drop(self, target, value, x, y):
        if isinstance(value, str):
            # Не принимать закреплённые приложения
            if favorites.contains(value):
                return False
            folders.add_app(self.folder_id, value)
        return True
    
    def _setup_menu(self):
        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("released", self._show_menu)
        self.add_controller(click)
    
    def _show_menu(self, gesture, n, x, y):
        menu = Gio.Menu()
        menu.append(_("Переименовать"), "fld.rename")
        menu.append(_("Удалить"), "fld.delete")
        
        group = Gio.SimpleActionGroup()
        
        rename = Gio.SimpleAction.new("rename", None)
        rename.connect("activate", lambda a, p: self.emit("renamed", self.folder_id))
        group.add_action(rename)
        
        delete = Gio.SimpleAction.new("delete", None)
        delete.connect("activate", lambda a, p: self.emit("deleted", self.folder_id))
        group.add_action(delete)
        
        self.insert_action_group("fld", group)
        
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self)
        popover.popup()
    
    def _refresh(self, obj):
        data = folders.get(self.folder_id)
        if data:
            self._label.set_label(data.get("name", "Папка"))
            self._update_preview()
