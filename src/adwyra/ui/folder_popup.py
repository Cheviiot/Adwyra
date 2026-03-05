# -*- coding: utf-8 -*-
"""Попап папки."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, Gio, GLib, GObject

from ..core import config, folders


class FolderAppTile(Gtk.Button):
    """Тайл приложения внутри папки."""
    
    __gsignals__ = {
        "launched": (GObject.SignalFlags.RUN_LAST, None, ()),
        "remove": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self, app_info: Gio.AppInfo):
        super().__init__()
        self.app_info = app_info
        self.app_id = app_info.get_id() or ""
        
        self.add_css_class("flat")
        
        self._build()
        self._setup_menu()
        
        self.connect("clicked", self._launch)
    
    def _build(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        self.set_child(box)
        
        icon = Gtk.Image.new_from_gicon(
            self.app_info.get_icon() or Gio.ThemedIcon.new("application-x-executable")
        )
        icon.set_pixel_size(config.get("icon_size"))
        box.append(icon)
        
        label = Gtk.Label(label=self.app_info.get_display_name() or "")
        label.set_ellipsize(3)
        label.set_max_width_chars(12)
        box.append(label)
    
    def _setup_menu(self):
        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("released", self._show_menu)
        self.add_controller(click)
    
    def _show_menu(self, gesture, n, x, y):
        menu = Gio.Menu()
        menu.append("Убрать из папки", "tile.remove")
        
        group = Gio.SimpleActionGroup()
        action = Gio.SimpleAction.new("remove", None)
        action.connect("activate", lambda a, p: self.emit("remove", self.app_id))
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


class FolderPopup(Adw.Window):
    """Попап содержимого папки."""
    
    __gsignals__ = {
        "app-launched": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self, folder_id: str, **kwargs):
        super().__init__(**kwargs)
        self.folder_id = folder_id
        
        self._build()
        self._populate()
        self._setup_events()
        
        folders.connect("changed", self._on_changed)
    
    def _build(self):
        data = folders.get(self.folder_id) or {}
        
        self.set_title(data.get("name", "Папка"))
        self.set_modal(True)
        self.set_default_size(500, 400)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)
        
        # Header
        header = Adw.HeaderBar()
        box.append(header)
        
        # Название
        self._title_btn = Gtk.Button()
        self._title_btn.add_css_class("flat")
        self._title_label = Gtk.Label(label=data.get("name", "Папка"))
        self._title_label.add_css_class("title-3")
        self._title_btn.set_child(self._title_label)
        self._title_btn.connect("clicked", self._rename)
        header.set_title_widget(self._title_btn)
        
        # Удалить
        del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        del_btn.set_tooltip_text("Удалить")
        del_btn.connect("clicked", self._delete)
        header.pack_end(del_btn)
        
        # Сетка
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        box.append(scroll)
        
        self._grid = Gtk.FlowBox()
        self._grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self._grid.set_homogeneous(True)
        self._grid.set_max_children_per_line(5)
        self._grid.set_min_children_per_line(3)
        self._grid.set_column_spacing(16)
        self._grid.set_row_spacing(16)
        self._grid.set_margin_start(24)
        self._grid.set_margin_end(24)
        self._grid.set_margin_top(16)
        self._grid.set_margin_bottom(24)
        scroll.set_child(self._grid)
    
    def _populate(self):
        while child := self._grid.get_first_child():
            self._grid.remove(child)
        
        data = folders.get(self.folder_id) or {}
        
        for app_id in data.get("apps", []):
            info = Gio.DesktopAppInfo.new(app_id)
            if not info:
                continue
            
            tile = FolderAppTile(info)
            tile.connect("launched", self._on_launched)
            tile.connect("remove", self._on_remove)
            self._grid.append(tile)
        
        if not self._grid.get_first_child():
            lbl = Gtk.Label(label="Пусто")
            lbl.add_css_class("dim-label")
            self._grid.append(lbl)
    
    def _setup_events(self):
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)
    
    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False
    
    def _on_launched(self, tile):
        self.emit("app-launched")
        self.close()
    
    def _on_remove(self, tile, app_id):
        folders.remove_app(self.folder_id, app_id)
    
    def _on_changed(self, obj):
        data = folders.get(self.folder_id)
        if not data:
            self.close()
            return
        self._title_label.set_label(data.get("name", "Папка"))
        self._populate()
    
    def _rename(self, btn):
        data = folders.get(self.folder_id) or {}
        
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
            if r == "ok" and entry.get_text().strip():
                folders.rename(self.folder_id, entry.get_text().strip())
        
        dialog.connect("response", on_resp)
        dialog.present()
    
    def _delete(self, btn):
        dialog = Adw.MessageDialog.new(self, "Удалить папку?")
        dialog.set_body("Приложения вернутся в главную сетку.")
        dialog.add_response("cancel", "Отмена")
        dialog.add_response("delete", "Удалить")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def on_resp(d, r):
            if r == "delete":
                folders.delete(self.folder_id)
        
        dialog.connect("response", on_resp)
        dialog.present()
