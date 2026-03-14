# -*- coding: utf-8 -*-
"""Страница управления плагинами.

Отображает список обнаруженных плагинов с переключателями вкл/выкл.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GObject

from ...core.plugins import plugin_manager
from ...i18n import _


class PluginsPage(Gtk.Box):
    """Страница плагинов."""
    
    __gtype_name__ = "PluginsPage"
    
    __gsignals__ = {
        "back": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(2)
        self.set_margin_bottom(4)
        
        self._build()
        plugin_manager.connect("changed", lambda pm: self.populate())
    
    def _build(self):
        # Заголовок
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_bottom(1)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("overlay-btn")
        back_btn.connect("clicked", lambda b: self.emit("back"))
        header.append(back_btn)
        
        title = Gtk.Label(label=_("Плагины"))
        title.add_css_class("title-2")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.CENTER)
        header.append(title)
        
        # Кнопка-заполнитель для симметрии
        spacer = Gtk.Box()
        spacer.set_size_request(22, -1)
        header.append(spacer)
        
        self.append(header)
        
        # Группа плагинов
        self._group = Adw.PreferencesGroup()
        self._group.set_title(_("Установленные плагины"))
        self._group.set_description(_("Плагины из ~/.config/adwyra/plugins/"))
        self.append(self._group)
        
        # Пустое состояние
        self._empty = Gtk.Label(label=_("Нет установленных плагинов"))
        self._empty.add_css_class("dim-label")
        self._empty.set_margin_top(12)
        self.append(self._empty)
    
    def populate(self):
        """Обновить список плагинов."""
        # Очистить группу
        while True:
            child = self._group.get_first_child()
            if not child:
                break
            # Adw.PreferencesGroup содержит listbox внутри
            # Используем remove для Adw rows
            break
        
        # Пересоздаём группу
        parent = self._group.get_parent()
        if parent:
            idx = 0
            child = parent.get_first_child()
            while child:
                if child == self._group:
                    break
                idx += 1
                child = child.get_next_sibling()
            parent.remove(self._group)
        
        self._group = Adw.PreferencesGroup()
        self._group.set_title("Установленные плагины")
        self._group.set_description("Плагины из ~/.config/adwyra/plugins/")
        
        plugins = plugin_manager.get_all()
        
        if plugins:
            self._empty.set_visible(False)
            for p in plugins:
                row = Adw.SwitchRow()
                row.set_title(p["name"])
                subtitle = p.get("description", "")
                if p.get("version"):
                    subtitle += f" (v{p['version']})" if subtitle else f"v{p['version']}"
                if p.get("author"):
                    subtitle += f" — {p['author']}" if subtitle else p["author"]
                row.set_subtitle(subtitle)
                row.set_active(p["active"])
                
                pid = p["id"]
                row.connect("notify::active", lambda r, param, _pid=pid: (
                    plugin_manager.enable(_pid) if r.get_active() else plugin_manager.disable(_pid)
                ))
                self._group.add(row)
        else:
            self._empty.set_visible(True)
        
        # Вставляем группу обратно (после header)
        header = self.get_first_child()
        if header:
            # insert_child_after вставляет после указанного
            self.insert_child_after(self._group, header)
