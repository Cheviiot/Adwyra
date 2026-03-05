# -*- coding: utf-8 -*-
"""Поле поиска."""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject


class SearchBar(Gtk.SearchEntry):
    """Стилизованное поле поиска."""
    
    __gtype_name__ = "SearchBar"
    
    __gsignals__ = {
        "query-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self):
        super().__init__()
        self.set_placeholder_text("Поиск")
        self.set_hexpand(True)
        
        self.connect("search-changed", self._on_changed)
    
    def _on_changed(self, entry):
        self.emit("query-changed", entry.get_text())
    
    def clear(self):
        self.set_text("")
