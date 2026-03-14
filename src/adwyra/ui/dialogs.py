# -*- coding: utf-8 -*-
"""Диалоговые окна приложения.

Компактные кастомные диалоги в стиле GNOME:
- BaseDialog: базовый класс без декораций
- RenameDialog: ввод нового имени (для папок, псевдонимов)
- DeleteConfirmDialog: подтверждение удаления
- DialogManager: фабрика для создания диалогов
"""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject

from ..i18n import _


class BaseDialog(Gtk.Window):
    """Базовый класс для компактных модальных диалогов без декораций."""
    
    def __init__(self, parent: Gtk.Window, title: str = ""):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("compact-dialog")
        
        self._parent = parent
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._box.set_margin_top(12)
        self._box.set_margin_bottom(12)
        self._box.set_margin_start(12)
        self._box.set_margin_end(12)
        
        if title:
            label = Gtk.Label(label=title)
            label.add_css_class("heading")
            self._box.append(label)
        
        self.set_child(self._box)
        
        # Создаём кнопки
        self._btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_box.set_halign(Gtk.Align.END)
        self._btn_box.set_margin_top(4)
    
    def _add_buttons(self):
        """Добавить кнопки в конец диалога."""
        self._box.append(self._btn_box)
    
    def _add_cancel_button(self, label: str = None):
        """Добавить кнопку отмены."""
        btn = Gtk.Button(label=label or _("Отмена"))
        btn.connect("clicked", lambda b: self.close())
        self._btn_box.append(btn)
        return btn


class RenameDialog(BaseDialog):
    """Диалог переименования."""
    
    __gtype_name__ = "RenameDialog"
    
    __gsignals__ = {
        "renamed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self, parent: Gtk.Window, title: str, current_name: str = ""):
        super().__init__(parent, title)
        
        self._entry = Gtk.Entry()
        self._entry.set_text(current_name)
        self._entry.set_width_chars(18)
        self._box.append(self._entry)
        
        self._add_cancel_button()
        
        ok_btn = Gtk.Button(label=_("OK"))
        ok_btn.add_css_class("suggested-action")
        ok_btn.connect("clicked", self._on_ok)
        self._entry.connect("activate", self._on_ok)
        self._btn_box.append(ok_btn)
        
        self._add_buttons()
    
    def _on_ok(self, *args):
        text = self._entry.get_text().strip()
        if text:
            self.emit("renamed", text)
        self.close()
    
    def present(self):
        super().present()
        self._entry.grab_focus()


class DeleteConfirmDialog(BaseDialog):
    """Диалог подтверждения удаления."""
    
    __gtype_name__ = "DeleteConfirmDialog"
    
    __gsignals__ = {
        "confirmed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self, parent: Gtk.Window, title: str, description: str = ""):
        super().__init__(parent, title)
        
        if description:
            desc = Gtk.Label(label=description)
            desc.add_css_class("dim-label")
            self._box.append(desc)
        
        self._btn_box.set_margin_top(8)
        self._add_cancel_button()
        
        del_btn = Gtk.Button(label=_("Удалить"))
        del_btn.add_css_class("destructive-action")
        del_btn.connect("clicked", self._on_delete)
        self._btn_box.append(del_btn)
        
        self._add_buttons()
    
    def _on_delete(self, btn):
        self.emit("confirmed")
        self.close()


class DialogManager:
    """Менеджер диалогов для управления флагом _has_dialog."""
    
    def __init__(self, window: Gtk.Window):
        self._window = window
        self._has_dialog = False
    
    @property
    def has_dialog(self) -> bool:
        """Есть ли открытый диалог."""
        return self._has_dialog
    
    def _on_close(self, dialog):
        """Callback при закрытии диалога."""
        self._has_dialog = False
        return False
    
    def show_rename(self, title: str, current_name: str, on_renamed):
        """Показать диалог переименования."""
        self._has_dialog = True
        dialog = RenameDialog(self._window, title, current_name)
        dialog.connect("renamed", lambda d, name: on_renamed(name))
        dialog.connect("close-request", self._on_close)
        dialog.present()
        return dialog
    
    def show_delete(self, title: str, description: str, on_confirmed):
        """Показать диалог подтверждения удаления."""
        self._has_dialog = True
        dialog = DeleteConfirmDialog(self._window, title, description)
        dialog.connect("confirmed", lambda d: on_confirmed())
        dialog.connect("close-request", self._on_close)
        dialog.present()
        return dialog
