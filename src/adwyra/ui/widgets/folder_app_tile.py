# -*- coding: utf-8 -*-
"""Тайл приложения внутри папки."""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gio, GObject

from .base_tile import BaseTile
from ...i18n import _


class FolderAppTile(BaseTile):
    """Тайл приложения внутри папки.
    
    Упрощённая версия AppTile без drag-drop и закрепления.
    Используется только внутри папок.
    """
    
    __gtype_name__ = "FolderAppTile"
    
    __gsignals__ = {
        "remove": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self, app_info: Gio.AppInfo):
        super().__init__(app_info)
        self._build()
        self._setup_context_menu(self._show_menu)
    
    def _build(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        self.set_child(box)
        
        box.append(self._build_icon())
        box.append(self._build_label())
    
    def _show_menu(self, gesture, n, x, y):
        menu = Gio.Menu()
        menu.append(_("Убрать из папки"), "tile.remove")
        
        group = Gio.SimpleActionGroup()
        action = Gio.SimpleAction.new("remove", None)
        action.connect("activate", lambda a, p: self.emit("remove", self.app_id))
        group.add_action(action)
        
        self._show_popover_menu(menu, group, "tile")
