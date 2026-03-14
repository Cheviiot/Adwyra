# -*- coding: utf-8 -*-
"""Поле поиска.

Активируется по клику, чтобы не захватывать фокус
при открытии окна.
"""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject, GLib

from ...i18n import _


class SearchBar(Gtk.Box):
    """Контейнер с полем поиска, активируемым по клику."""
    
    __gtype_name__ = "SearchBar"
    
    __gsignals__ = {
        "query-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    # Таймауты в миллисекундах
    IDLE_TIMEOUT = 3000   # 3 секунды без ввода — сбросить фокус (если поле пустое)
    ACTIVE_TIMEOUT = 15000  # 15 секунд с текстом — сбросить фокус
    
    def __init__(self):
        super().__init__()
        self._focus_timer_id = None
        self._has_input = False  # Был ли ввод после получения фокуса
        self._is_focused = False  # Флаг для отслеживания фокуса
        
        # Контейнер не должен получать фокус при Tab-навигации
        Gtk.Box.set_focusable(self, False)
        
        self._entry = Gtk.SearchEntry()
        self._entry.set_placeholder_text(_("Поиск"))
        self._entry.set_hexpand(True)
        self._entry.set_focusable(False)
        self._entry.connect("search-changed", self._on_changed)
        self.append(self._entry)
        
        # Включить фокус по клику на весь контейнер
        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        self.add_controller(click)
        
        # Отслеживать потерю фокуса
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("enter", self._on_focus_enter)
        focus_ctrl.connect("leave", self._on_focus_leave)
        self._entry.add_controller(focus_ctrl)
    
    def _on_click(self, gesture, n_press, x, y):
        self._entry.set_focusable(True)
        self._entry.grab_focus()
        self._has_input = bool(self._entry.get_text())
        self._start_focus_timer()
    
    def _on_focus_enter(self, ctrl):
        self._is_focused = True
        self._has_input = bool(self._entry.get_text())
        self._start_focus_timer()
    
    def _on_focus_leave(self, ctrl):
        self._is_focused = False
        self._cancel_focus_timer()
        self._has_input = False
        # При потере фокуса — убрать focusable
        self._entry.set_focusable(False)
    
    def _start_focus_timer(self):
        self._cancel_focus_timer()
        # Если есть текст или был ввод — дольше ждём
        timeout = self.ACTIVE_TIMEOUT if self._entry.get_text() else self.IDLE_TIMEOUT
        self._focus_timer_id = GLib.timeout_add(timeout, self._on_focus_timeout)
    
    def _cancel_focus_timer(self):
        if self._focus_timer_id:
            GLib.source_remove(self._focus_timer_id)
            self._focus_timer_id = None
    
    def _on_focus_timeout(self):
        self._focus_timer_id = None
        # Если в поле есть текст — не сбрасывать фокус, перезапустить таймер
        if self._entry.get_text():
            self._focus_timer_id = GLib.timeout_add(self.ACTIVE_TIMEOUT, self._on_focus_timeout)
            return False
        self._has_input = False
        # Сбросить фокус и focusable
        self._entry.set_focusable(False)
        # Убрать фокус с entry 
        window = self.get_root()
        if window:
            window.set_focus(None)
        return False
    
    def _on_changed(self, entry):
        text = entry.get_text()
        self._has_input = bool(text)
        # При вводе сбрасываем таймер с новым значением
        if self._entry.has_focus():
            self._start_focus_timer()
        self.emit("query-changed", text)
    
    def release_focus(self):
        """Принудительно сбросить фокус (вызывается извне при клике вне поиска)."""
        self._cancel_focus_timer()
        self._has_input = False
        self._is_focused = False
        # Сначала сбросить фокус, потом убрать focusable
        window = self.get_root()
        if window:
            window.set_focus(None)
        self._entry.set_focusable(False)
        return False  # Для GLib.idle_add
    
    def get_text(self):
        return self._entry.get_text()
    
    def set_text(self, text):
        self._entry.set_text(text)
    
    def clear(self):
        self._entry.set_text("")
        self._entry.set_focusable(False)
        self._cancel_focus_timer()
        self._has_input = False
    
    def set_focusable(self, focusable):
        self._entry.set_focusable(focusable)
        if not focusable:
            self._cancel_focus_timer()
            self._has_input = False
    
    def grab_focus(self):
        self._entry.set_focusable(True)
        self._entry.grab_focus()
        self._has_input = bool(self._entry.get_text())
        self._start_focus_timer()
    
    def has_focus(self) -> bool:
        """Проверить, активно ли поле поиска."""
        return self._is_focused or self._entry.has_focus()
