# -*- coding: utf-8 -*-
"""Страница настроек приложения.

Содержит вкладки «Настройки» и «Плагины» (если есть хотя бы один плагин).
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject

from ...core import config, keybindings
from ...core.plugins import plugin_manager
from ...i18n import _, get_available_languages


class PrefsPage(Gtk.Box):
    """Страница настроек с вкладками.
    
    Signals:
        back(): Пользователь нажал "Назад".
        show-about(): Открыть страницу "О программе".
        show-hidden(): Открыть список скрытых приложений.
    """
    
    __gtype_name__ = "PrefsPage"
    
    __gsignals__ = {
        "back": (GObject.SignalFlags.RUN_LAST, None, ()),
        "show-about": (GObject.SignalFlags.RUN_LAST, None, ()),
        "show-hidden": (GObject.SignalFlags.RUN_LAST, None, ()),
        "show-plugin-prefs": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._pending = {}  # Буфер отложенных изменений (columns, rows, icon_size)
        self._build()
        plugin_manager.connect("changed", lambda pm: self._update_plugins_tab())
    
    def _build(self):
        # Один общий ScrolledWindow для всей страницы
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        scroll.set_vexpand(True)
        
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.set_child(outer)
        self.append(scroll)
        
        # === Заголовок ===
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_start(6)
        header_box.set_margin_end(6)
        header_box.set_margin_top(4)
        header_box.set_margin_bottom(1)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("overlay-btn")
        back_btn.connect("clicked", lambda b: self.emit("back"))
        header_box.append(back_btn)
        
        # Заголовок (показывается когда нет плагинов)
        self._title = Gtk.Label(label=_("Настройки"))
        self._title.add_css_class("title-2")
        self._title.set_hexpand(True)
        self._title.set_halign(Gtk.Align.CENTER)
        header_box.append(self._title)
        
        # Переключатель вкладок (заменяет заголовок когда есть плагины)
        self._tab_stack = Gtk.Stack()
        self._tab_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._tab_stack.set_vexpand(True)
        
        self._switcher = Gtk.StackSwitcher()
        self._switcher.set_stack(self._tab_stack)
        self._switcher.set_halign(Gtk.Align.CENTER)
        self._switcher.set_hexpand(True)
        self._switcher.set_visible(False)
        header_box.append(self._switcher)
        
        about_btn = Gtk.Button.new_from_icon_name("help-about-symbolic")
        about_btn.add_css_class("flat")
        about_btn.add_css_class("overlay-btn")
        about_btn.set_tooltip_text(_("О программе"))
        about_btn.connect("clicked", lambda b: self.emit("show-about"))
        header_box.append(about_btn)
        
        outer.append(header_box)
        
        # === Вкладка «Настройки» ===
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        settings_box.set_margin_start(10)
        settings_box.set_margin_end(10)
        settings_box.set_margin_top(2)
        settings_box.set_margin_bottom(4)
        self._build_settings(settings_box)
        
        self._tab_stack.add_titled(settings_box, "settings", _("Настройки"))
        
        # === Вкладка «Плагины» ===
        self._plugins_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._plugins_box.set_margin_start(10)
        self._plugins_box.set_margin_end(10)
        self._plugins_box.set_margin_top(2)
        self._plugins_box.set_margin_bottom(4)
        
        self._plugins_tab = self._plugins_box
        self._tab_stack.add_titled(self._plugins_box, "plugins", _("Плагины"))
        
        outer.append(self._tab_stack)
        
        # Скрыть переключатель и вкладку если нет плагинов
        self._update_plugins_tab()
    
    def _build_settings(self, box):
        """Содержимое вкладки настроек."""
        # Внешний вид
        appearance = Adw.PreferencesGroup()
        appearance.set_title(_("Внешний вид"))
        box.append(appearance)
        
        # Язык
        _LANG_NAMES = {"ru": "Русский", "en": "English"}
        available = get_available_languages()
        lang_labels = [_("Авто")] + [_LANG_NAMES.get(c, c) for c in available]
        lang_codes = ["auto"] + available
        
        current_lang = config.get("language")
        current_lang_idx = lang_codes.index(current_lang) if current_lang in lang_codes else 0
        
        self._lang_row = Adw.ExpanderRow()
        self._lang_row.set_title(_("Язык"))
        self._lang_row.set_subtitle(lang_labels[current_lang_idx])
        self._lang_codes = lang_codes
        
        lang_group = None
        for i, label in enumerate(lang_labels):
            check = Gtk.CheckButton()
            if lang_group is None:
                lang_group = check
            else:
                check.set_group(lang_group)
            check.set_active(i == current_lang_idx)
            
            row = Adw.ActionRow()
            row.set_title(label)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            code = lang_codes[i]
            check.connect("toggled", self._make_lang_handler(code, label))
            self._lang_row.add_row(row)
        
        appearance.add(self._lang_row)
        
        # Тема
        theme_labels = [_("Системная"), _("Светлая"), _("Тёмная")]
        theme_codes = ["system", "light", "dark"]
        current_theme = config.get("theme")
        current_theme_idx = theme_codes.index(current_theme) if current_theme in theme_codes else 0
        
        self._theme_row = Adw.ExpanderRow()
        self._theme_row.set_title(_("Тема"))
        self._theme_row.set_subtitle(theme_labels[current_theme_idx])
        
        theme_group = None
        for i, label in enumerate(theme_labels):
            check = Gtk.CheckButton()
            if theme_group is None:
                theme_group = check
            else:
                check.set_group(theme_group)
            check.set_active(i == current_theme_idx)
            
            row = Adw.ActionRow()
            row.set_title(label)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            code = theme_codes[i]
            check.connect("toggled", self._make_theme_handler(code, label))
            self._theme_row.add_row(row)
        
        appearance.add(self._theme_row)
        
        transparent_row = Adw.SwitchRow()
        transparent_row.set_title(_("Прозрачность окна"))
        transparent_row.set_active(config.get("transparent"))
        transparent_row.connect("notify::active", lambda r, p: config.set("transparent", r.get_active()))
        appearance.add(transparent_row)
        
        # Сетка
        grid_group = Adw.PreferencesGroup()
        grid_group.set_title(_("Сетка"))
        box.append(grid_group)
        
        self._cols_row = Adw.SpinRow.new_with_range(4, 7, 1)
        self._cols_row.set_title(_("Колонки"))
        self._cols_row.set_value(config.get("columns"))
        self._cols_row.connect("notify::value", lambda r, p: self._stage("columns", int(r.get_value())))
        grid_group.add(self._cols_row)
        
        self._rows_row = Adw.SpinRow.new_with_range(3, 6, 1)
        self._rows_row.set_title(_("Строки"))
        self._rows_row.set_value(config.get("rows"))
        self._rows_row.connect("notify::value", lambda r, p: self._stage("rows", int(r.get_value())))
        grid_group.add(self._rows_row)
        
        # Размер иконок
        icon_labels = [_("Маленький (56)"), _("Средний (72)"), _("Большой (96)")]
        icon_sizes = [56, 72, 96]
        current_icon = config.get("icon_size")
        current_icon_idx = icon_sizes.index(current_icon) if current_icon in icon_sizes else 0
        
        self._icon_row = Adw.ExpanderRow()
        self._icon_row.set_title(_("Размер иконок"))
        self._icon_row.set_subtitle(icon_labels[current_icon_idx])
        
        icon_group = None
        for i, label in enumerate(icon_labels):
            check = Gtk.CheckButton()
            if icon_group is None:
                icon_group = check
            else:
                check.set_group(icon_group)
            check.set_active(i == current_icon_idx)
            
            row = Adw.ActionRow()
            row.set_title(label)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            size = icon_sizes[i]
            check.connect("toggled", self._make_icon_handler(size, label))
            self._icon_row.add_row(row)
        
        grid_group.add(self._icon_row)
        
        # Кнопка «Применить» для отложенных настроек сетки
        self._apply_btn = Gtk.Button(label=_("Применить"))
        self._apply_btn.add_css_class("suggested-action")
        self._apply_btn.set_halign(Gtk.Align.CENTER)
        self._apply_btn.set_margin_top(2)
        self._apply_btn.set_visible(False)
        self._apply_btn.connect("clicked", self._on_apply)
        box.append(self._apply_btn)
        
        # Поведение
        behavior = Adw.PreferencesGroup()
        behavior.set_title(_("Поведение"))
        box.append(behavior)
        
        close_launch = Adw.SwitchRow()
        close_launch.set_title(_("Закрывать при запуске"))
        close_launch.set_active(config.get("close_on_launch"))
        close_launch.connect("notify::active", lambda r, p: config.set("close_on_launch", r.get_active()))
        behavior.add(close_launch)
        
        close_focus = Adw.SwitchRow()
        close_focus.set_title(_("Закрывать при потере фокуса"))
        close_focus.set_active(config.get("close_on_focus_lost"))
        close_focus.connect("notify::active", lambda r, p: config.set("close_on_focus_lost", r.get_active()))
        behavior.add(close_focus)
        
        hide_dock = Adw.SwitchRow()
        hide_dock.set_title(_("Скрывать закреплённые в Dock"))
        hide_dock.set_active(config.get("hide_dock_apps"))
        hide_dock.connect("notify::active", lambda r, p: config.set("hide_dock_apps", r.get_active()))
        behavior.add(hide_dock)
        
        hidden_row = Adw.ActionRow()
        hidden_row.set_title(_("Скрытые приложения"))
        hidden_row.set_subtitle(_("Приложения, удалённые из сетки"))
        hidden_row.set_activatable(True)
        hidden_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        hidden_row.connect("activated", lambda r: self.emit("show-hidden"))
        behavior.add(hidden_row)
        
        # Горячая клавиша
        hotkey_group = Adw.PreferencesGroup()
        hotkey_group.set_title(_("Горячая клавиша"))
        hotkey_group.set_description(_("Введите сочетание, например: Super+A, Ctrl+Space"))
        box.append(hotkey_group)
        
        current_hotkey = keybindings.get_current()
        
        self._hotkey_entry = Adw.EntryRow()
        self._hotkey_entry.set_title(_("Сочетание клавиш"))
        self._hotkey_entry.set_text(current_hotkey or "")
        self._hotkey_entry.connect("apply", self._on_hotkey_apply)
        self._hotkey_entry.set_show_apply_button(True)
        
        clear_btn = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.add_css_class("flat")
        clear_btn.add_css_class("dimmed")
        clear_btn.set_tooltip_text(_("Удалить"))
        clear_btn.connect("clicked", self._on_clear_hotkey)
        self._hotkey_entry.add_suffix(clear_btn)
        
        hotkey_group.add(self._hotkey_entry)
    
    def _update_plugins_tab(self):
        """Показать/скрыть вкладку плагинов и переключатель."""
        has_plugins = len(plugin_manager.get_all()) > 0
        self._plugins_tab.set_visible(has_plugins)
        self._switcher.set_visible(has_plugins)
        self._title.set_visible(not has_plugins)
        
        if has_plugins:
            self._populate_plugins()
    
    def _populate_plugins(self):
        """Обновить содержимое вкладки плагинов."""
        # Очистить
        while child := self._plugins_box.get_first_child():
            self._plugins_box.remove(child)
        
        group = Adw.PreferencesGroup()
        group.set_title(_("Установленные плагины"))
        group.set_description(_("Плагины из /usr/lib/adwyra/plugins/ и ~/.config/adwyra/plugins/"))
        
        for p in plugin_manager.get_all():
            row = Adw.SwitchRow()
            row.set_title(p["name"])
            subtitle = p.get("description", "")
            if p.get("version"):
                subtitle += f" (v{p['version']})" if subtitle else f"v{p['version']}"
            if p.get("author"):
                subtitle += f" — {p['author']}" if subtitle else p["author"]
            
            error = p.get("error")
            if error:
                subtitle = f"⚠ {error}" + (f"\n{subtitle}" if subtitle else "")
                row.set_sensitive(False)
            
            row.set_subtitle(subtitle)
            row.set_active(p["active"])
            
            pid = p["id"]
            row.connect("notify::active", lambda r, param, _pid=pid: (
                plugin_manager.enable(_pid) if r.get_active() else plugin_manager.disable(_pid)
            ))
            
            if plugin_manager.has_prefs(pid):
                settings_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
                settings_btn.set_valign(Gtk.Align.CENTER)
                settings_btn.add_css_class("flat")
                settings_btn.set_tooltip_text(_("Настройки"))
                settings_btn.connect("clicked", lambda b, _pid=pid: self.emit("show-plugin-prefs", _pid))
                row.add_suffix(settings_btn)
            
            group.add(row)
        
        self._plugins_box.append(group)
    
    def _on_language_change(self, row, param):
        lang = self._lang_codes[row.get_selected()]
        if config.get("language") != lang:
            config.set("language", lang)
            self._lang_row.set_subtitle(_("Требуется перезапуск"))
    
    def _make_lang_handler(self, code, label):
        def on_toggled(check):
            if not check.get_active():
                return
            self._lang_row.set_expanded(False)
            self._lang_row.set_subtitle(label)
            if config.get("language") != code:
                config.set("language", code)
                self._lang_row.set_subtitle(label + "  ·  " + _("Требуется перезапуск"))
        return on_toggled
    
    def _make_theme_handler(self, code, label):
        def on_toggled(check):
            if not check.get_active():
                return
            self._theme_row.set_expanded(False)
            self._theme_row.set_subtitle(label)
            config.set("theme", code)
            style = Adw.StyleManager.get_default()
            if code == "dark":
                style.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            elif code == "light":
                style.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            else:
                style.set_color_scheme(Adw.ColorScheme.DEFAULT)
        return on_toggled
    
    def _make_icon_handler(self, size, label):
        def on_toggled(check):
            if not check.get_active():
                return
            self._icon_row.set_expanded(False)
            self._icon_row.set_subtitle(label)
            self._stage("icon_size", size)
        return on_toggled
    
    def _stage(self, key, value):
        """Буферизовать изменение. Показать кнопку если значение отличается от текущего."""
        if value == config.get(key):
            self._pending.pop(key, None)
        else:
            self._pending[key] = value
        self._apply_btn.set_visible(bool(self._pending))
    
    def _on_apply(self, btn):
        """Применить все буферизованные изменения разом."""
        for key, value in self._pending.items():
            config.set(key, value)
        self._pending.clear()
        self._apply_btn.set_visible(False)
    
    def _on_hotkey_apply(self, entry):
        """Применить введённую горячую клавишу."""
        text = entry.get_text()
        accel = keybindings.normalize(text)
        
        if not accel or not keybindings.validate(accel):
            self._show_entry_error(entry, text)
            return
        
        # Проверить конфликт
        conflict = keybindings.check_conflict(accel)
        if conflict:
            entry.add_css_class("error")
            entry.set_text(_("Занято: {}").format(conflict))
            GLib.timeout_add(2500, lambda: (entry.remove_css_class("error"), entry.set_text(text)) or False)
            return
        
        # Сохраняем
        if keybindings.save(accel):
            label = keybindings.get_label(accel)
            entry.set_text(label or text)
            entry.add_css_class("success")
            GLib.timeout_add(1500, lambda: entry.remove_css_class("success") or False)
        else:
            self._show_entry_error(entry, text)
    
    def _show_entry_error(self, entry, original_text):
        entry.add_css_class("error")
        GLib.timeout_add(2000, lambda: entry.remove_css_class("error") or False)
    
    def _on_clear_hotkey(self, btn):
        """Удалить горячую клавишу."""
        if keybindings.clear():
            self._hotkey_entry.set_text("")
