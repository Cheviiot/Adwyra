# -*- coding: utf-8 -*-
"""Основное приложение."""

import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio, GLib, Gdk

from . import __app_id__
from .ui import MainWindow
from .core import config


class Application(Adw.Application):
    """Главное приложение Adwyra."""
    
    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        
        self.add_main_option("toggle", ord("t"), GLib.OptionFlags.NONE, 
                             GLib.OptionArg.NONE, "Переключить окно", None)
        self.add_main_option("show", ord("s"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Показать окно", None)
        self.add_main_option("hide", ord("h"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Скрыть окно", None)
        
        self._window = None
    
    def do_startup(self):
        Adw.Application.do_startup(self)
        self._load_css()
        self._apply_theme()
    
    def _load_css(self):
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if not os.path.exists(css_path):
            return
        
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
    
    def _apply_theme(self):
        theme = config.get("theme")
        style_manager = Adw.StyleManager.get_default()
        
        if theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
    
    def do_activate(self):
        if not self._window:
            self._window = MainWindow(self)
            self._window.connect("close-request", self._on_close)
        self._window.present()
    
    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        
        if options.contains("toggle"):
            if self._window and self._window.is_visible():
                self._window.close()
            else:
                self.activate()
        elif options.contains("show"):
            self.activate()
        elif options.contains("hide"):
            if self._window:
                self._window.close()
        else:
            self.activate()
        
        return 0
    
    def _on_close(self, window):
        self._window = None
        return False
