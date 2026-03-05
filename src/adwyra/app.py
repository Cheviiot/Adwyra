# -*- coding: utf-8 -*-
"""
Adwyra — главный модуль приложения
"""

import sys
import json
import locale
from pathlib import Path
from typing import Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")

from gi.repository import Gtk, Adw, Gio, GLib, Gdk, Pango

from . import __version__, __app_id__


class FavoritesManager:
    """Управление закреплёнными приложениями."""

    def __init__(self):
        self.config_dir = Path(GLib.get_user_config_dir()) / "adwyra"
        self.config_file = self.config_dir / "favorites.json"
        self.favorites: set[str] = set()
        self._load()

    def _load(self):
        """Загружает избранное из файла."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = set(data.get("favorites", []))
            except (json.JSONDecodeError, OSError):
                self.favorites = set()

    def _save(self):
        """Сохраняет избранное в файл."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"favorites": list(self.favorites)}, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def is_favorite(self, app_id: str) -> bool:
        return app_id in self.favorites

    def add(self, app_id: str):
        self.favorites.add(app_id)
        self._save()

    def remove(self, app_id: str):
        self.favorites.discard(app_id)
        self._save()

    def toggle(self, app_id: str) -> bool:
        """Переключает статус. Возвращает новый статус."""
        if app_id in self.favorites:
            self.favorites.discard(app_id)
            self._save()
            return False
        else:
            self.favorites.add(app_id)
            self._save()
            return True


# Глобальный менеджер избранного
favorites_manager = FavoritesManager()


class AppTile(Gtk.Button):
    """Плитка приложения: иконка + название."""

    def __init__(self, app_info: Gio.DesktopAppInfo):
        super().__init__()
        self.app_info = app_info
        self.app_id = app_info.get_id() or ""

        # Настройка кнопки
        self.set_css_classes(["flat", "app-tile"])
        self.set_size_request(100, 110)

        # Overlay для звезды
        overlay = Gtk.Overlay()

        # Контейнер
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        # Иконка
        icon = app_info.get_icon()
        if icon:
            image = Gtk.Image.new_from_gicon(icon)
        else:
            image = Gtk.Image.new_from_icon_name("application-x-executable")
        image.set_pixel_size(64)
        image.set_css_classes(["app-icon"])
        box.append(image)

        # Название
        name = app_info.get_display_name() or app_info.get_name() or "Unknown"
        label = Gtk.Label(label=name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(12)
        label.set_lines(2)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.set_css_classes(["app-label"])
        box.append(label)

        overlay.set_child(box)

        # Звезда для избранного
        self.star_icon = Gtk.Image.new_from_icon_name("starred-symbolic")
        self.star_icon.set_pixel_size(16)
        self.star_icon.set_halign(Gtk.Align.END)
        self.star_icon.set_valign(Gtk.Align.START)
        self.star_icon.set_margin_top(4)
        self.star_icon.set_margin_end(4)
        self.star_icon.set_css_classes(["favorite-star"])
        self.star_icon.set_visible(favorites_manager.is_favorite(self.app_id))
        overlay.add_overlay(self.star_icon)

        self.set_child(overlay)

        # Для поиска
        self.search_name = name.lower()

        # Контекстное меню
        self._setup_context_menu()

    def _setup_context_menu(self):
        """Настраивает контекстное меню."""
        # Создаём меню
        menu = Gio.Menu()
        
        if favorites_manager.is_favorite(self.app_id):
            menu.append("Открепить", f"tile.unpin")
        else:
            menu.append("Закрепить", f"tile.pin")

        self.popover = Gtk.PopoverMenu.new_from_model(menu)
        self.popover.set_parent(self)
        self.popover.set_has_arrow(True)

        # Actions
        action_group = Gio.SimpleActionGroup()
        
        pin_action = Gio.SimpleAction.new("pin", None)
        pin_action.connect("activate", self._on_pin)
        action_group.add_action(pin_action)
        
        unpin_action = Gio.SimpleAction.new("unpin", None)
        unpin_action.connect("activate", self._on_unpin)
        action_group.add_action(unpin_action)

        self.insert_action_group("tile", action_group)

        # Правый клик
        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)  # Правая кнопка
        gesture.connect("pressed", self._on_right_click)
        self.add_controller(gesture)

    def _on_right_click(self, gesture, n_press, x, y):
        """Обработчик правого клика."""
        # Обновляем меню
        menu = Gio.Menu()
        if favorites_manager.is_favorite(self.app_id):
            menu.append("Открепить", "tile.unpin")
        else:
            menu.append("Закрепить", "tile.pin")
        
        self.popover.set_menu_model(menu)
        
        # Позиционируем и показываем
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        self.popover.set_pointing_to(rect)
        self.popover.popup()

    def _on_pin(self, action, param):
        """Закрепить приложение."""
        favorites_manager.add(self.app_id)
        self.star_icon.set_visible(True)
        self._request_resort()

    def _on_unpin(self, action, param):
        """Открепить приложение."""
        favorites_manager.remove(self.app_id)
        self.star_icon.set_visible(False)
        self._request_resort()

    def _request_resort(self):
        """Запрашивает пересортировку."""
        parent = self.get_parent()
        if parent:
            flow_box = parent.get_parent()
            if isinstance(flow_box, Gtk.FlowBox):
                flow_box.invalidate_sort()
                # Найти окно и игнорировать потерю фокуса
                root = self.get_root()
                if root and hasattr(root, 'ignore_next_focus_loss'):
                    root.ignore_next_focus_loss()

    def is_favorite(self) -> bool:
        return favorites_manager.is_favorite(self.app_id)

    def launch(self) -> tuple[bool, Optional[str]]:
        """Запускает приложение."""
        try:
            self.app_info.launch([], None)
            return True, None
        except GLib.Error as e:
            return False, f"Не удалось запустить: {e.message}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class MainWindow(Adw.ApplicationWindow):
    """Главное окно лаунчера."""

    def __init__(self, app: Adw.Application):
        super().__init__(application=app)

        self.set_title("Adwyra")
        self.set_deletable(False)
        self.app_count = 0
        self.tiles: list[AppTile] = []  # Список плиток
        self._ignore_focus_loss = False  # Флаг для игнорирования потери фокуса

        self._build_ui()
        self._load_applications()
        self._setup_shortcuts()
        self._apply_css()
        
        # Закрываем при потере фокуса
        self.connect("notify::is-active", self._on_focus_changed)

    def _build_ui(self):
        """Создаёт UI."""
        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Главный контейнер
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # Header bar
        header = Adw.HeaderBar()
        header.set_css_classes(["flat"])
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        # Поиск в центре
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Поиск приложений…")
        self.search_entry.set_hexpand(True)
        self.search_entry.set_max_width_chars(40)
        self.search_entry.connect("search-changed", self._on_search_changed)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_box.set_hexpand(True)
        search_box.set_halign(Gtk.Align.CENTER)
        search_box.append(self.search_entry)

        header.set_title_widget(search_box)
        main_box.append(header)

        # Scrolled window для сетки
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Контейнер с отступами
        clamp = Adw.Clamp()
        clamp.set_maximum_size(1200)
        clamp.set_tightening_threshold(600)

        inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner_box.set_margin_top(24)
        inner_box.set_margin_bottom(24)
        inner_box.set_margin_start(24)
        inner_box.set_margin_end(24)

        # FlowBox для плиток
        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_halign(Gtk.Align.FILL)
        self.flow_box.set_homogeneous(True)
        self.flow_box.set_row_spacing(12)
        self.flow_box.set_column_spacing(12)
        self.flow_box.set_min_children_per_line(3)
        self.flow_box.set_max_children_per_line(12)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_filter_func(self._filter_func)
        self.flow_box.set_sort_func(self._sort_func)

        inner_box.append(self.flow_box)
        clamp.set_child(inner_box)
        scrolled.set_child(clamp)
        main_box.append(scrolled)

    def _apply_css(self):
        """Применяет стили."""
        css = b"""
        .app-tile {
            padding: 12px;
            border-radius: 12px;
            transition: all 200ms ease;
        }

        .app-tile:hover {
            background-color: alpha(@accent_color, 0.1);
        }

        .app-tile:active {
            background-color: alpha(@accent_color, 0.2);
        }

        .app-icon {
            margin-bottom: 4px;
        }

        .app-label {
            font-size: 11px;
            opacity: 0.9;
        }

        .favorite-star {
            color: @warning_color;
            background-color: alpha(@window_bg_color, 0.8);
            border-radius: 50%;
            padding: 2px;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _setup_shortcuts(self):
        """Настраивает горячие клавиши."""
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_f and state & Gdk.ModifierType.CONTROL_MASK:
            self.search_entry.grab_focus()
            return True
        if keyval == Gdk.KEY_Escape:
            if self.search_entry.get_text():
                self.search_entry.set_text("")
                return True
            else:
                self.close()
                return True
        return False

    def _load_applications(self):
        """Загружает приложения."""
        for app_info in Gio.AppInfo.get_all():
            if not isinstance(app_info, Gio.DesktopAppInfo):
                continue
            if not app_info.should_show():
                continue
            # Исключаем себя из списка
            app_id = app_info.get_id() or ""
            if app_id.replace(".desktop", "") == __app_id__:
                continue
            name = app_info.get_display_name() or app_info.get_name()
            if not name or not app_info.get_executable():
                continue

            tile = AppTile(app_info)
            tile.connect("clicked", self._on_tile_clicked)
            self.flow_box.append(tile)
            self.tiles.append(tile)
            self.app_count += 1

        self._adjust_window_size()
        self.flow_box.invalidate_sort()

    def _adjust_window_size(self):
        """Адаптирует размер окна."""
        tile_width = 100 + 12
        tile_height = 110 + 12
        margins = 48
        header_height = 47

        display = Gdk.Display.get_default()
        monitor = display.get_monitors().get_item(0)
        if monitor:
            geometry = monitor.get_geometry()
            screen_width = int(geometry.width * 0.85)
            screen_height = int(geometry.height * 0.85)
        else:
            screen_width = 1200
            screen_height = 800

        cols = min(8, max(5, self.app_count // 5))
        rows = (self.app_count + cols - 1) // cols

        width = min(cols * tile_width + margins, screen_width)
        height = min(rows * tile_height + margins + header_height, screen_height)

        width = max(500, width)
        height = max(400, height)

        self.set_default_size(width, height)

    def _filter_func(self, child: Gtk.FlowBoxChild) -> bool:
        """Фильтрует плитки по поиску."""
        tile = child.get_child()
        if not isinstance(tile, AppTile):
            return True

        search_text = self.search_entry.get_text().lower().strip()
        if not search_text:
            return True

        return search_text in tile.search_name

    def _sort_func(self, child1: Gtk.FlowBoxChild, child2: Gtk.FlowBoxChild) -> int:
        """Сортирует плитки: сначала избранные, потом по имени."""
        tile1 = child1.get_child()
        tile2 = child2.get_child()

        if not isinstance(tile1, AppTile) or not isinstance(tile2, AppTile):
            return 0

        # Избранные первыми
        fav1 = tile1.is_favorite()
        fav2 = tile2.is_favorite()
        
        if fav1 and not fav2:
            return -1
        if fav2 and not fav1:
            return 1

        # Затем по имени
        name1 = tile1.app_info.get_display_name() or ""
        name2 = tile2.app_info.get_display_name() or ""
        return locale.strcoll(name1.lower(), name2.lower())

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        self.flow_box.invalidate_filter()

    def _on_focus_changed(self, window, pspec):
        if not self.is_active():
            # Игнорируем потерю фокуса после действия в меню
            if self._ignore_focus_loss:
                self._ignore_focus_loss = False
                return
            # Не закрываем, если открыто контекстное меню
            for tile in self.tiles:
                if hasattr(tile, 'popover') and tile.popover.is_visible():
                    return
            self.close()

    def ignore_next_focus_loss(self):
        """Игнорировать следующую потерю фокуса."""
        self._ignore_focus_loss = True
        # Сброс через 500мс
        GLib.timeout_add(500, self._reset_ignore_flag)

    def _reset_ignore_flag(self):
        """Сбрасывает флаг игнорирования."""
        self._ignore_focus_loss = False
        return False  # Не повторять таймер

    def _on_tile_clicked(self, tile: AppTile):
        success, error_msg = tile.launch()
        if not success and error_msg:
            toast = Adw.Toast.new(error_msg)
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)
        else:
            GLib.timeout_add(200, self.close)


class LauncherApp(Adw.Application):
    """Главный класс приложения."""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        locale.setlocale(locale.LC_ALL, "")
        self._setup_icon()

    def _setup_icon(self):
        """Настраивает иконку приложения."""
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        data_dirs = [
            Path(__file__).parent.parent.parent / "data" / "icons",
            Path("/usr/share/icons"),
            Path("/usr/local/share/icons"),
        ]
        for path in data_dirs:
            if path.exists():
                icon_theme.add_search_path(str(path))
        
        Gtk.Window.set_default_icon_name("adwyra")

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        win.present()


def main():
    """Точка входа."""
    app = LauncherApp()
    return app.run(sys.argv)
