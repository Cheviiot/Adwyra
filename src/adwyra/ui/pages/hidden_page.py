# -*- coding: utf-8 -*-
"""Страница управления скрытыми приложениями.

Позволяет пользователю возвращать скрытые приложения обратно в сетку.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, GObject

from ...core import hidden_apps
from ...core.apps import app_service
from ...i18n import _


class HiddenPage(Gtk.Box):
    """Список скрытых приложений с возможностью восстановления.
    
    Signals:
        back(): Пользователь нажал "Назад".
    """
    
    __gtype_name__ = "HiddenPage"
    
    __gsignals__ = {
        "back": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(4)
        self.set_margin_bottom(8)
        
        self._build()
    
    def _build(self):
        # Заголовок с кнопкой назад
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_bottom(1)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("overlay-btn")
        back_btn.connect("clicked", lambda b: self.emit("back"))
        header_box.append(back_btn)
        
        title = Gtk.Label(label=_("Скрытые приложения"))
        title.add_css_class("title-2")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.CENTER)
        header_box.append(title)
        
        # Spacer для центрирования (ширина = кнопка назад)
        spacer = Gtk.Box()
        spacer.set_size_request(22, -1)
        header_box.append(spacer)
        
        self.append(header_box)
        
        # Контейнер для списка приложений
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self.append(self._list)
        
        # Пустое состояние
        self._empty_label = Gtk.Label(label=_("Нет скрытых приложений"))
        self._empty_label.add_css_class("empty-state")
        self._empty_label.set_margin_top(24)
        self.append(self._empty_label)
    
    def populate(self):
        """Заполнить список скрытых приложений."""
        # Очистить список
        while row := self._list.get_row_at_index(0):
            self._list.remove(row)
        
        hidden_ids = hidden_apps.get_all()
        all_apps = app_service.get_all()
        app_map = {a.get_id(): a for a in all_apps}
        
        has_items = False
        for app_id in hidden_ids:
            app_info = app_map.get(app_id)
            if app_info:
                has_items = True
                row = Adw.ActionRow()
                row.set_title(app_info.get_display_name() or app_id)
                
                # Иконка приложения
                icon = Gtk.Image.new_from_gicon(
                    app_info.get_icon() or Gio.ThemedIcon.new("application-x-executable")
                )
                icon.set_pixel_size(32)
                row.add_prefix(icon)
                
                # Кнопка восстановления
                restore_btn = Gtk.Button.new_from_icon_name("view-reveal-symbolic")
                restore_btn.set_valign(Gtk.Align.CENTER)
                restore_btn.add_css_class("flat")
                restore_btn.set_tooltip_text(_("Показать"))
                restore_btn.connect("clicked", self._on_restore, app_id)
                row.add_suffix(restore_btn)
                
                self._list.append(row)
        
        self._list.set_visible(has_items)
        self._empty_label.set_visible(not has_items)
    
    def _on_restore(self, btn, app_id):
        """Восстановить скрытое приложение."""
        hidden_apps.remove(app_id)
        self.populate()
