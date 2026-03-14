# -*- coding: utf-8 -*-
"""Страница О программе.

Отображает информацию о приложении и проверяет обновления.
"""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject

from ...core import UpdateChecker
from ... import __version__, __app_name__
from ...i18n import _


class AboutPage(Gtk.Box):
    """Страница с информацией о программе и проверкой обновлений.
    
    Signals:
        back(): Пользователь нажал "Назад".
    """
    
    __gtype_name__ = "AboutPage"
    
    __gsignals__ = {
        "back": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(4)
        self.set_margin_bottom(8)
        
        self._update_checker = UpdateChecker(__version__)
        self._update_checker.connect("check-complete", self._on_update_result)
        
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
        
        title = Gtk.Label(label=_("О программе"))
        title.add_css_class("title-2")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.CENTER)
        header_box.append(title)
        
        # Spacer для центрирования (ширина = кнопка назад)
        spacer = Gtk.Box()
        spacer.set_size_request(22, -1)
        header_box.append(spacer)
        
        self.append(header_box)
        
        # Иконка и название
        icon = Gtk.Image.new_from_icon_name("com.github.adwyra")
        icon.set_pixel_size(96)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_margin_top(8)
        self.append(icon)
        
        name_label = Gtk.Label(label=__app_name__)
        name_label.add_css_class("title-2")
        name_label.set_halign(Gtk.Align.CENTER)
        name_label.set_margin_top(4)
        self.append(name_label)
        
        version_label = Gtk.Label(label=_("Версия {}").format(__version__))
        version_label.add_css_class("dim-label")
        version_label.set_halign(Gtk.Align.CENTER)
        self.append(version_label)
        
        # Статус обновлений
        self._update_status = Gtk.Label(label="")
        self._update_status.set_halign(Gtk.Align.CENTER)
        self._update_status.set_margin_top(4)
        self.append(self._update_status)
        
        desc_label = Gtk.Label(label=_("Минималистичный лаунчер приложений для GNOME"))
        desc_label.set_halign(Gtk.Align.CENTER)
        desc_label.set_margin_top(8)
        desc_label.set_wrap(True)
        self.append(desc_label)
        
        # Ссылка
        link_btn = Gtk.LinkButton.new_with_label(
            "https://github.com/cheviiot/adwyra",
            "GitHub"
        )
        link_btn.set_halign(Gtk.Align.CENTER)
        link_btn.set_margin_top(8)
        self.append(link_btn)
        
        # Лицензия
        license_label = Gtk.Label(label=_("Лицензия: GPL-3.0"))
        license_label.add_css_class("dim-label")
        license_label.set_halign(Gtk.Align.CENTER)
        license_label.set_margin_top(8)
        self.append(license_label)
    
    def check_updates(self):
        """Запустить проверку обновлений."""
        self._update_status.set_label(_("Проверка обновлений..."))
        self._update_status.remove_css_class("success")
        self._update_status.remove_css_class("warning")
        self._update_status.add_css_class("dim-label")
        self._update_checker.check()
    
    def _on_update_result(self, checker, latest_version, error):
        """Обработка результата проверки обновлений."""
        self._update_status.remove_css_class("dim-label")
        
        if error:
            self._update_status.set_label(_("⚠ Ошибка: {}").format(error[:30]))
            self._update_status.add_css_class("warning")
            return
        
        if self._update_checker.is_update_available(latest_version):
            self._update_status.set_label(_("🔄 Доступно: v{}").format(latest_version))
            self._update_status.add_css_class("warning")
        else:
            self._update_status.set_label(_("✓ Актуальная версия"))
            self._update_status.add_css_class("success")
