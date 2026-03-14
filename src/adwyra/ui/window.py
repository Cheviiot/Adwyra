# -*- coding: utf-8 -*-
"""Главное окно лаунчера Adwyra.

Содержит основной интерфейс с сеткой приложений, поиском,
и встроенными страницами настроек и информации о программе.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, GLib

from ..core import config, folders, SearchService, hidden_apps
from ..core.apps import app_service
from ..core.favorites import get_gnome_dock_apps
from ..core.plugins import plugin_manager
from .widgets import AppGrid, SearchBar
from .dialogs import DialogManager
from .pages import PrefsPage, AboutPage, HiddenPage
from .focus_utils import is_text_input_active
from ..i18n import _


class MainWindow(Adw.ApplicationWindow):
    """Главное окно приложения.
    
    Управляет навигацией между страницами (сетка, папка, настройки, о программе),
    обработкой горячих клавиш и взаимодействием с пользователем.
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(application=app, **kwargs)
        self._is_dragging = False
        self._dialogs = DialogManager(self)
        self._search_svc = SearchService()
        self._current_folder = None
        self._current_query = ""
        self._all_apps = []
        self._resize_debounce_id = None
        
        self._build()
        self._setup_events()
        self._connect_signals()
        self._load_apps()
        
        # Сбросить фокус при показе
        self.connect("show", self._on_show)
    
    def _on_show(self, widget):
        # Убрать фокус с поля поиска через idle чтобы сработало после GTK
        GLib.idle_add(self._clear_focus)
        self._schedule_square_check()
        plugin_manager.notify_window_shown()
    
    def _clear_focus(self):
        self.set_focus(None)
        return False
    
    def _build(self):
        self.set_title("Adwyra")
        self.set_decorated(False)
        self._update_size()
        self._apply_transparency()
        
        # Overlay для кнопки настроек
        self._overlay = Gtk.Overlay()
        self.set_content(self._overlay)
        
        # Stack для переключения видов
        self._stack = Gtk.Stack()
        self._stack.set_transition_duration(250)
        self._stack.set_vexpand(True)
        self._stack.set_hhomogeneous(False)
        self._stack.set_vhomogeneous(False)
        self._overlay.set_child(self._stack)
        
        # === Главная страница ===
        self._main_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._main_page.set_hexpand(True)
        self._main_page.set_vexpand(True)
        
        # Поиск сверху (компактный, по центру)
        self._search_box = Gtk.Box()
        self._search_box.set_halign(Gtk.Align.CENTER)
        self._search_box.set_margin_top(4)
        self._search_box.set_margin_bottom(1)
        self._main_page.append(self._search_box)
        
        self._search = SearchBar()
        self._search.set_hexpand(False)
        self._search_box.append(self._search)
        
        # Сетка приложений в overlay (для сообщения "Ничего не найдено")
        self._grid_overlay = Gtk.Overlay()
        self._grid_overlay.set_hexpand(True)
        self._grid_overlay.set_vexpand(True)
        
        self._grid = AppGrid()
        self._grid.set_halign(Gtk.Align.FILL)
        self._grid.set_valign(Gtk.Align.FILL)
        self._grid.set_hexpand(True)
        self._grid.set_vexpand(True)
        self._grid_overlay.set_child(self._grid)
        
        # Label "Ничего не найдено" (поверх grid, изначально скрыт)
        self._empty_label = Gtk.Label(label=_("Ничего не найдено"))
        self._empty_label.add_css_class("empty-state")
        self._empty_label.set_halign(Gtk.Align.CENTER)
        self._empty_label.set_valign(Gtk.Align.CENTER)
        self._empty_label.set_visible(False)
        self._grid_overlay.add_overlay(self._empty_label)
        
        self._main_page.append(self._grid_overlay)
        
        self._stack.add_named(self._main_page, "main")
        
        # Контейнер папки с inline заголовком
        folder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        folder_box.set_margin_start(6)
        folder_box.set_margin_end(6)
        folder_box.set_margin_top(4)
        folder_box.set_margin_bottom(8)
        
        # Заголовок папки (inline)
        folder_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.add_css_class("overlay-btn")
        back_btn.connect("clicked", self._on_back)
        folder_header.append(back_btn)
        
        self._folder_title = Gtk.Label()
        self._folder_title.add_css_class("title-2")
        self._folder_title.set_hexpand(True)
        self._folder_title.set_halign(Gtk.Align.CENTER)
        folder_header.append(self._folder_title)
        
        self._folder_del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self._folder_del_btn.add_css_class("flat")
        self._folder_del_btn.add_css_class("overlay-btn")
        self._folder_del_btn.connect("clicked", self._on_folder_delete_btn)
        folder_header.append(self._folder_del_btn)
        
        folder_box.append(folder_header)
        
        # Сетка папки
        self._folder_grid = Gtk.Grid()
        self._folder_grid.set_row_homogeneous(True)
        self._folder_grid.set_column_homogeneous(True)
        self._folder_grid.set_column_spacing(6)
        self._folder_grid.set_row_spacing(6)
        self._folder_grid.set_halign(Gtk.Align.CENTER)
        self._folder_grid.set_valign(Gtk.Align.START)
        folder_box.append(self._folder_grid)
        
        folder_scroll = Gtk.ScrolledWindow()
        folder_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        folder_scroll.set_child(folder_box)
        self._stack.add_named(folder_scroll, "folder")
        
        # === Страница настроек ===
        self._prefs_page = PrefsPage()
        self._prefs_page.connect("back", lambda p: self._on_back(None))
        self._prefs_page.connect("show-about", lambda p: self._show_about(None))
        self._prefs_page.connect("show-hidden", lambda p: self._show_hidden_page(None))
        self._prefs_page.connect("show-plugin-prefs", self._show_plugin_prefs)
        self._stack.add_named(self._prefs_page, "prefs")
        
        # === Страница О программе ===
        self._about_page = AboutPage()
        self._about_page.connect("back", lambda p: self._navigate("prefs", back=True))
        about_scroll = Gtk.ScrolledWindow()
        about_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        about_scroll.set_child(self._about_page)
        self._stack.add_named(about_scroll, "about")
        
        # === Страница скрытых приложений ===
        self._hidden_page = HiddenPage()
        self._hidden_page.connect("back", lambda p: self._navigate("prefs", back=True))
        hidden_scroll = Gtk.ScrolledWindow()
        hidden_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        hidden_scroll.set_child(self._hidden_page)
        self._stack.add_named(hidden_scroll, "hidden")
        
        # === Страница настроек плагина ===
        self._current_pp_id = None
        pp_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        pp_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pp_header.set_margin_start(6)
        pp_header.set_margin_end(6)
        pp_header.set_margin_top(4)
        pp_header.set_margin_bottom(1)
        
        pp_back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        pp_back.add_css_class("flat")
        pp_back.add_css_class("overlay-btn")
        pp_back.connect("clicked", lambda b: self._on_plugin_prefs_back())
        pp_header.append(pp_back)
        
        self._pp_title = Gtk.Label()
        self._pp_title.add_css_class("title-2")
        self._pp_title.set_hexpand(True)
        self._pp_title.set_halign(Gtk.Align.CENTER)
        pp_header.append(self._pp_title)
        
        pp_spacer = Gtk.Box()
        pp_spacer.set_size_request(22, -1)
        pp_header.append(pp_spacer)
        
        pp_outer.append(pp_header)
        
        self._pp_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._pp_content.set_margin_start(10)
        self._pp_content.set_margin_end(10)
        self._pp_content.set_margin_bottom(4)
        pp_outer.append(self._pp_content)
        
        pp_scroll = Gtk.ScrolledWindow()
        pp_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        pp_scroll.set_child(pp_outer)
        self._stack.add_named(pp_scroll, "plugin_prefs")
        
        # Кнопка настроек слева сверху (только на главной)
        self._prefs_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
        self._prefs_btn.set_tooltip_text(_("Настройки"))
        self._prefs_btn.add_css_class("flat")
        self._prefs_btn.add_css_class("dim-label")
        self._prefs_btn.add_css_class("overlay-btn")
        self._prefs_btn.set_halign(Gtk.Align.START)
        self._prefs_btn.set_valign(Gtk.Align.START)
        self._prefs_btn.set_margin_start(6)
        self._prefs_btn.set_margin_top(4)
        self._prefs_btn.set_focusable(True)  # Чтобы фокус уходил с поиска при клике
        self._prefs_btn.connect("clicked", self._open_prefs)
        self._overlay.add_overlay(self._prefs_btn)
        
        # Кнопка закрытия справа сверху
        self._close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")
        self._close_btn.set_tooltip_text(_("Закрыть"))
        self._close_btn.add_css_class("flat")
        self._close_btn.add_css_class("dim-label")
        self._close_btn.add_css_class("overlay-btn")
        self._close_btn.set_halign(Gtk.Align.END)
        self._close_btn.set_valign(Gtk.Align.START)
        self._close_btn.set_margin_end(6)
        self._close_btn.set_margin_top(4)
        self._close_btn.set_focusable(True)  # Чтобы фокус уходил с поиска при клике
        self._close_btn.connect("clicked", lambda b: self.close())
        self._overlay.add_overlay(self._close_btn)
    
    def _apply_transparency(self):
        if config.get("transparent"):
            self.add_css_class("transparent-window")
        else:
            self.remove_css_class("transparent-window")

    # === Навигация между страницами ===

    def _navigate(self, page_name: str, *, back: bool = False):
        """Переключить Stack на страницу с направленной анимацией.

        Args:
            page_name: Имя страницы в Stack.
            back: True = возврат назад (slide right), False = вглубь (slide left).
        """
        transition = (
            Gtk.StackTransitionType.SLIDE_RIGHT if back
            else Gtk.StackTransitionType.SLIDE_LEFT
        )
        self._stack.set_visible_child_full(page_name, transition)

    # === Система размеров окна ===
    #
    # Принцип: GTK делает layout сам, мы измеряем результат и делаем квадрат.
    # 1. _estimate_side() — начальный размер (с запасом)
    # 2. set_default_size(S, S) — первый кадр квадратный
    # 3. tick callback — проверяет реальный размер и корректирует
    #
    # Никаких магических констант. Работает при любом шрифте/теме/DPI.

    _sq_tick_id = None
    _sq_attempts = 0

    def _estimate_side(self) -> int:
        """Начальная оценка стороны квадратного окна.

        Специально завышаем на ~10%, чтобы контент гарантированно
        поместился и окно было квадратным с первого кадра.
        """
        cols = config.get("columns")
        rows = config.get("rows")
        icon = config.get("icon_size")
        # Размеры ячейки (icon + кнопка + label)
        cell_w = icon + 24
        cell_h = icon + 42
        grid_w = cols * cell_w + (cols - 1) * 6 + 24
        grid_h = rows * cell_h + (rows - 1) * 6 + 16
        chrome_h = 36  # search bar only (compact)
        return max(grid_w, grid_h + chrome_h)

    def _update_size(self):
        """(Re)apply window sizing: generous square estimate + post-layout correction."""
        # Сброс предыдущих ограничений
        self.set_size_request(-1, -1)
        side = self._estimate_side()
        self.set_default_size(side, side)
        self.set_size_request(side, side)
        self.set_resizable(False)
        self._schedule_square_check()

    def _schedule_square_check(self):
        """Запланировать проверку квадратности через tick callback."""
        self._sq_attempts = 0
        if self._sq_tick_id is None:
            self._sq_tick_id = self.add_tick_callback(self._tick_enforce_square)

    def _tick_enforce_square(self, widget, clock):
        """Frame callback: измеряем реальный размер и корректируем до квадрата."""
        self._sq_attempts += 1
        w, h = self.get_width(), self.get_height()
        if w <= 0 or h <= 0:
            # Окно ещё не отрисовано
            if self._sq_attempts > 10:
                self._sq_tick_id = None
                return False
            return True
        if w == h:
            # Уже квадрат
            self._sq_tick_id = None
            return False
        # Не квадрат — GTK расширил одну сторону.
        # Выравниваем по большей.
        side = max(w, h)
        self.set_size_request(side, side)
        self.set_default_size(side, side)
        if self._sq_attempts > 5:
            self._sq_tick_id = None
            return False
        return True  # проверить в следующем кадре
    
    def _setup_events(self):
        # Перехват стрелок — блокируем везде кроме текстовых полей
        arrow_ctrl = Gtk.EventControllerKey()
        arrow_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        arrow_ctrl.connect("key-pressed", self._on_arrow_capture)
        self.add_controller(arrow_ctrl)
        
        # Клавиши
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)
        
        # Потеря фокуса окна
        self.connect("notify::is-active", self._on_active_changed)
        
        # Отслеживаем изменение фокуса для сброса focusable у поиска
        self.connect("notify::focus-widget", self._on_focus_widget_changed)
        
        # Клик на главной странице в фазе CAPTURE — сбросить фокус с поиска
        main_click = Gtk.GestureClick()
        main_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        main_click.connect("pressed", self._on_main_page_click)
        self._main_page.add_controller(main_click)
    
    def _on_active_changed(self, window, pspec):
        if not self.is_active() and config.get("close_on_focus_lost"):
            GLib.timeout_add(100, self._check_close)
    
    def _on_arrow_capture(self, ctrl, keyval, keycode, state):
        """Блокировать стрелки везде кроме текстовых полей."""
        arrow_keys = (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Left, Gdk.KEY_Right)
        if keyval not in arrow_keys:
            return False  # Не стрелка — пропускаем
        
        # Разрешаем стрелки только в текстовых полях
        if is_text_input_active(self):
            return False
        
        # Блокируем стрелки
        return True
    
    def _on_main_page_click(self, gesture, n_press, x, y):
        """Клик на главной странице — сбросить фокус с поиска если кликнули вне него."""
        if not self._search.has_focus():
            return
        
        # Находим виджет под курсором
        widget = self._main_page.pick(x, y, Gtk.PickFlags.DEFAULT)
        
        # Проверяем, является ли виджет частью поиска
        current = widget
        while current:
            if current == self._search:
                return  # Кликнули в поле поиска — не трогаем
            current = current.get_parent()
        
        # Клик вне поиска — сбросить фокус
        self._search.release_focus()

    def _on_focus_widget_changed(self, window, pspec):
        """При смене фокуса — сбросить focusable у поиска если фокус ушёл."""
        focused = self.get_focus()
        
        # Проверяем, является ли новый фокус частью поиска
        if focused is not None:
            current = focused
            while current:
                if current == self._search:
                    return  # Фокус внутри поиска
                current = current.get_parent()
        
        # Фокус ушёл из поиска (или None) — сбрасываем focusable
        self._search.set_focusable(False)
    
    def _connect_signals(self):
        self._search.connect("query-changed", self._on_search)
        self._search_svc.connect("results", self._on_results)
        
        self._grid.connect("app-launched", self._on_launched)
        self._grid.connect("folder-open", self._on_folder_open)
        self._grid.connect("folder-rename", self._on_folder_rename)
        self._grid.connect("folder-delete", self._on_folder_delete)
        self._grid.connect("drag-begin", self._on_drag_begin)
        self._grid.connect("drag-end", self._on_drag_end)
        
        app_service.connect("changed", lambda s: self._load_apps())
        folders.connect("changed", lambda f: self._load_apps())
        hidden_apps.connect("changed", lambda h: self._load_apps())
        config.connect("changed", self._on_config_changed)
        
        # Хуки плагинов для UI
        plugin_manager.connect("page-added", self._on_plugin_page_added)
        plugin_manager.connect("page-removed", self._on_plugin_page_removed)
        plugin_manager.connect("changed", self._on_plugins_changed)
        
        # Загрузить плагины
        plugin_manager.discover()
    
    def _on_drag_begin(self, grid):
        self._is_dragging = True
    
    def _on_drag_end(self, grid):
        self._is_dragging = False
    
    def _load_apps(self):
        apps = app_service.get_all()
        exclude = set(folders.get_all_app_ids())
        
        # Скрывать закреплённые в Dock
        if config.get("hide_dock_apps"):
            exclude.update(get_gnome_dock_apps())
        
        # Скрывать вручную скрытые приложения
        exclude.update(hidden_apps.get_all())
        
        self._search_svc.set_apps(apps)
        self._search_svc.set_exclude(exclude)
        
        filtered = [a for a in apps if a.get_id() not in exclude]
        self._all_apps = filtered
        self._grid.set_apps(filtered)
        self._empty_label.set_visible(False)
    
    def _on_search(self, search_bar, query):
        self._current_query = query.strip()
        if not self._current_query:
            # Пустой запрос — показать все приложения
            self._empty_label.set_visible(False)
            self._grid.set_opacity(1)
            self._grid.set_can_target(True)
            self._grid.set_apps(self._all_apps)
        else:
            self._search_svc.search(query)
    
    def _on_results(self, svc, apps):
        if not apps and self._current_query:
            # Пустой результат при активном поиске — скрыть grid через opacity (сохраняет размер)
            self._empty_label.set_visible(True)
            self._grid.set_opacity(0)
            self._grid.set_can_target(False)
        else:
            self._empty_label.set_visible(False)
            self._grid.set_opacity(1)
            self._grid.set_can_target(True)
            self._grid.set_apps(apps)
    
    def _on_key(self, ctrl, keyval, keycode, state):
        # Игнорируем клавиши когда открыт диалог
        if self._has_dialog:
            return False
        
        # Escape работает глобально
        if keyval == Gdk.KEY_Escape:
            # При активном поиске — сначала очищаем текст
            if self._search.get_text():
                self._search.clear()
                self.set_focus(None)  # Убираем фокус с поиска
                return True
            if self._current_folder:
                self._on_back(None)
                return True
            self.close()
            return True
        
        # Пропускаем остальные клавиши к editable виджетам
        if is_text_input_active(self):
            # Enter в поиске — активировать первый элемент
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                if self._search.get_text() and self._grid.has_items:
                    self._grid.activate_first()
                    return True
            return False
        
        # Ctrl+F — фокус на поиске
        if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_f:
            self._search.set_focusable(True)
            self._search.grab_focus()
            return True
        
        return False
    
    @property
    def _has_dialog(self) -> bool:
        return self._dialogs.has_dialog
    
    def _check_close(self):
        # Не закрывать если активны, есть дочернее окно, перетаскивание или диалог
        if self.is_active() or self._is_dragging or self._has_dialog:
            return False
        self.close()
        return False
    
    def _on_launched(self, grid):
        if config.get("close_on_launch"):
            self.close()
    
    def _on_folder_open(self, grid, folder_id):
        self._current_folder = folder_id
        self._populate_folder(folder_id)
        folder_data = folders.get(folder_id)
        self._folder_title.set_label(folder_data["name"] if folder_data else _("Папка"))
        self._folder_del_btn.set_visible(True)
        self._prefs_btn.set_visible(False)
        self._close_btn.set_visible(False)
        self._navigate("folder")
    
    def _populate_folder(self, folder_id):
        from .widgets import FolderAppTile
        
        # Очистить Grid
        while True:
            child = self._folder_grid.get_first_child()
            if not child:
                break
            self._folder_grid.remove(child)
        
        data = folders.get(folder_id)
        if not data:
            return
        
        all_apps = app_service.get_all()
        app_map = {a.get_id(): a for a in all_apps}
        
        cols = config.get("columns")
        rows = config.get("rows")
        
        # Placeholderы для стабильной структуры сетки
        for r in range(rows):
            for c in range(cols):
                placeholder = Gtk.Box()
                self._folder_grid.attach(placeholder, c, r, 1, 1)
        
        # Добавляем реальные элементы
        idx = 0
        for app_id in data.get("apps", []):
            app_info = app_map.get(app_id)
            if app_info:
                tile = FolderAppTile(app_info)
                tile.connect("launched", self._on_folder_app_launched)
                tile.connect("remove", self._on_app_remove_from_folder)
                row = idx // cols
                col = idx % cols
                old = self._folder_grid.get_child_at(col, row)
                if old:
                    self._folder_grid.remove(old)
                self._folder_grid.attach(tile, col, row, 1, 1)
                idx += 1
    
    def _on_folder_app_launched(self, tile):
        if config.get("close_on_launch"):
            self.close()
    
    def _on_app_remove_from_folder(self, tile, app_id):
        if self._current_folder:
            folders.remove_app(self._current_folder, app_id)
            self._populate_folder(self._current_folder)
    
    def _on_back(self, btn):
        self._current_folder = None
        self._prefs_btn.set_visible(True)
        self._close_btn.set_visible(True)
        self._navigate("main", back=True)
        GLib.idle_add(self._clear_focus)  # Сбросить фокус после переключения
        self._load_apps()
    
    def _on_folder_delete_btn(self, btn):
        if self._current_folder:
            self._show_delete_dialog(self._current_folder)
    
    def _on_folder_rename(self, grid, folder_id):
        self._show_rename_dialog(folder_id)
    
    def _on_folder_delete(self, grid, folder_id):
        self._show_delete_dialog(folder_id)
    
    def _show_rename_dialog(self, folder_id):
        data = folders.get(folder_id)
        if not data:
            return
        self._dialogs.show_rename(
            _("Переименовать"),
            data.get("name", ""),
            lambda name: folders.rename(folder_id, name)
        )
    
    def _show_delete_dialog(self, folder_id):
        def on_confirmed():
            folders.delete(folder_id)
            if self._current_folder == folder_id:
                self._on_back(None)
        
        self._dialogs.show_delete(
            _("Удалить папку?"),
            _("Приложения вернутся в сетку"),
            on_confirmed
        )
    
    def _open_prefs(self, btn):
        self._prefs_btn.set_visible(False)
        self._close_btn.set_visible(False)
        self._navigate("prefs")
    
    def _on_config_changed(self, cfg, key, val):
        if key in ("columns", "rows", "icon_size"):
            self._schedule_resize()
        elif key == "hide_dock_apps":
            self._update_size()
            self._load_apps()
        elif key == "transparent":
            self._apply_transparency()

    def _schedule_resize(self):
        """Debounce: отложить перестройку на 300мс, сбросить при повторном вызове."""
        if self._resize_debounce_id is not None:
            GLib.source_remove(self._resize_debounce_id)
        self._resize_debounce_id = GLib.timeout_add(300, self._apply_resize)

    def _apply_resize(self):
        """Применить отложенную перестройку размера."""
        self._resize_debounce_id = None
        self._update_size()
        self._load_apps()
        self._recenter()
        return False

    def _recenter(self):
        """Перецентрировать окно после изменения размера (hide+present)."""
        self.set_visible(False)
        GLib.idle_add(self._recenter_show)

    def _recenter_show(self):
        self.present()
        return False
    
    def _show_about(self, btn):
        """Показать страницу О программе."""
        self._navigate("about")
        # Автоматически проверяем обновления при открытии
        self._about_page.check_updates()
    
    def _show_hidden_page(self, row):
        """Показать страницу скрытых приложений."""
        self._hidden_page.populate()
        self._navigate("hidden")
    
    # --- Хуки плагинов ---
    
    def _show_plugin_prefs(self, page, plugin_id):
        """Показать страницу настроек плагина."""
        # Очистить предыдущее содержимое
        while child := self._pp_content.get_first_child():
            self._pp_content.remove(child)
        
        self._current_pp_id = plugin_id
        
        # Заголовок
        for p in plugin_manager.get_all():
            if p["id"] == plugin_id:
                self._pp_title.set_label(p["name"])
                break
        
        # Добавить группы настроек
        for group in plugin_manager.get_prefs_groups(plugin_id):
            self._pp_content.append(group)
        
        self._navigate("plugin_prefs")
    
    def _on_plugin_prefs_back(self):
        """Вернуться из настроек плагина."""
        while child := self._pp_content.get_first_child():
            self._pp_content.remove(child)
        self._current_pp_id = None
        self._navigate("prefs", back=True)
    
    def _on_plugins_changed(self, pm):
        """При изменении плагинов — вернуться если настройки плагина больше недоступны."""
        if self._stack.get_visible_child_name() == "plugin_prefs":
            if self._current_pp_id and not plugin_manager.has_prefs(self._current_pp_id):
                self._on_plugin_prefs_back()
    
    def _on_plugin_page_added(self, pm, page_id, widget, title):
        """Плагин добавил страницу в стек."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        scroll.set_child(widget)
        self._stack.add_named(scroll, f"plugin_{page_id}")
    
    def _on_plugin_page_removed(self, pm, page_id):
        """Плагин удалил страницу из стека."""
        child = self._stack.get_child_by_name(f"plugin_{page_id}")
        if child:
            self._stack.remove(child)
    

