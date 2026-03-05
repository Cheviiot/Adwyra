# -*- coding: utf-8 -*-
"""Тайл приложения."""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, Gio, GLib, GObject

from ...core import config, favorites


class AppTile(Gtk.Button):
    """Тайл приложения с иконкой, подписью и drag-drop."""
    
    __gtype_name__ = "AppTile"
    
    __gsignals__ = {
        "launched": (GObject.SignalFlags.RUN_LAST, None, ()),
        "folder-create": (GObject.SignalFlags.RUN_LAST, None, (str, str)),
        "fav-moved": (GObject.SignalFlags.RUN_LAST, None, (str, str)),  # (moved_app, before_app)
        "drag-begin": (GObject.SignalFlags.RUN_LAST, None, ()),
        "drag-end": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self, app_info: Gio.AppInfo):
        super().__init__()
        self.app_info = app_info
        self.app_id = app_info.get_id() or ""
        self._hover_timeout = None
        self._drop_app_id = None
        
        self.add_css_class("flat")
        
        self._build()
        self._setup_dnd()
        self._setup_menu()
        
        self.connect("clicked", self._launch)
    
    def _build(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER)
        self.set_child(box)
        
        # Контейнер для иконки с индикатором
        icon_overlay = Gtk.Overlay()
        
        # Иконка
        self._icon = Gtk.Image.new_from_gicon(
            self.app_info.get_icon() or Gio.ThemedIcon.new("application-x-executable")
        )
        self._icon.set_pixel_size(config.get("icon_size"))
        self._icon.add_css_class("app-icon")
        self._icon.set_overflow(Gtk.Overflow.HIDDEN)
        icon_overlay.set_child(self._icon)
        
        # Индикатор закрепления
        self._pin_badge = Gtk.Image.new_from_icon_name("starred-symbolic")
        self._pin_badge.set_pixel_size(14)
        self._pin_badge.set_halign(Gtk.Align.END)
        self._pin_badge.set_valign(Gtk.Align.START)
        self._pin_badge.add_css_class("pin-badge")
        self._pin_badge.set_visible(favorites.contains(self.app_id))
        icon_overlay.add_overlay(self._pin_badge)
        
        box.append(icon_overlay)
        
        # Название
        label = Gtk.Label(label=self.app_info.get_display_name() or "")
        label.set_ellipsize(3)
        label.set_max_width_chars(12)
        label.set_lines(2)
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.add_css_class("app-label")
        box.append(label)
    
    def _setup_dnd(self):
        # Drag source
        drag = Gtk.DragSource()
        drag.set_actions(Gdk.DragAction.MOVE)
        drag.connect("prepare", self._on_drag_prepare)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)
        
        # Drop target
        drop = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
        drop.connect("enter", self._on_drop_enter)
        drop.connect("leave", self._on_drop_leave)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)
    
    def _on_drag_prepare(self, source, x, y):
        return Gdk.ContentProvider.new_for_value(self.app_id)
    
    def _on_drag_begin(self, source, drag):
        self.emit("drag-begin")
        icon = Gtk.DragIcon.get_for_drag(drag)
        img = Gtk.Image.new_from_gicon(
            self.app_info.get_icon() or Gio.ThemedIcon.new("application-x-executable")
        )
        img.set_pixel_size(config.get("icon_size"))
        icon.set_child(img)
    
    def _on_drag_end(self, source, drag, delete_data):
        self.emit("drag-end")
    
    def _on_drop_enter(self, target, x, y):
        self.add_css_class("drop-hover")
        self._drop_app_id = None
        # Запускать таймер создания папки только если оба приложения не закреплены
        if not favorites.contains(self.app_id):
            self._hover_timeout = GLib.timeout_add(600, self._create_folder_timeout)
        else:
            self._hover_timeout = None
        return Gdk.DragAction.MOVE
    
    def _on_drop_leave(self, target):
        self.remove_css_class("drop-hover")
        if self._hover_timeout:
            GLib.source_remove(self._hover_timeout)
            self._hover_timeout = None
        self._drop_app_id = None
    
    def _create_folder_timeout(self):
        self._hover_timeout = None
        if self._drop_app_id and self._drop_app_id != self.app_id:
            # Не создавать папку если перетаскиваемое приложение закреплено
            if not favorites.contains(self._drop_app_id):
                self.emit("folder-create", self._drop_app_id, self.app_id)
        return False
    
    def _on_drop(self, target, value, x, y):
        self._drop_app_id = value
        self._on_drop_leave(target)
        
        if not value or value == self.app_id:
            return True
        
        # Если перетаскиваемое приложение закреплено - перемещаем позицию
        if favorites.contains(value):
            self.emit("fav-moved", value, self.app_id)
        else:
            # Обычное приложение - создаём папку
            if not favorites.contains(self.app_id):
                self.emit("folder-create", value, self.app_id)
        return True
    
    def _setup_menu(self):
        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("released", self._show_menu)
        self.add_controller(click)
    
    def _show_menu(self, gesture, n, x, y):
        is_fav = favorites.contains(self.app_id)
        
        menu = Gio.Menu()
        menu.append("Открепить" if is_fav else "Закрепить", "tile.toggle")
        
        group = Gio.SimpleActionGroup()
        action = Gio.SimpleAction.new("toggle", None)
        action.connect("activate", lambda a, p: favorites.toggle(self.app_id))
        group.add_action(action)
        self.insert_action_group("tile", group)
        
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self)
        popover.popup()
    
    def _launch(self, btn):
        try:
            self.app_info.launch(None, None)
        except GLib.Error:
            pass
        self.emit("launched")
    
    def update_icon_size(self):
        self._icon.set_pixel_size(config.get("icon_size"))
