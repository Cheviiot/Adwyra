# -*- coding: utf-8 -*-
"""Утилиты для работы с иконками."""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf

# Кеш результатов: (icon_string, size) -> bool
# Иконки не меняются в рантайме — кеш живёт до перезапуска
_rounding_cache: dict[tuple[str, int], bool] = {}


def icon_needs_rounding(gicon: Gio.Icon, size: int) -> bool:
    """Определяет, нужно ли скруглять иконку.
    
    Проверяет угловые пиксели на прозрачность.
    Если углы непрозрачны — иконка квадратная, нужно скруглить.
    Результат кешируется по icon+size.
    """
    if not gicon:
        return False
    
    # Проверяем кеш
    key = (gicon.to_string(), size)
    cached = _rounding_cache.get(key)
    if cached is not None:
        return cached
    
    result = _check_rounding(gicon, size)
    _rounding_cache[key] = result
    return result


def _check_rounding(gicon: Gio.Icon, size: int) -> bool:
    """Фактическая проверка угловых пикселей (тяжёлая операция)."""
    try:
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        icon_paintable = theme.lookup_by_gicon(
            gicon, size, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.FORCE_REGULAR
        )
        if not icon_paintable:
            return False
        
        icon_file = icon_paintable.get_file()
        if not icon_file:
            return False
        
        path = icon_file.get_path()
        if not path:
            return False
        
        if path.endswith('.svg'):
            return False
        
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        if not pixbuf or not pixbuf.get_has_alpha():
            return True
        
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        rowstride = pixbuf.get_rowstride()
        pixels = pixbuf.get_pixels()
        n_channels = pixbuf.get_n_channels()
        
        if n_channels < 4:
            return True
        
        corner_size = min(5, width // 4, height // 4)
        opaque_corners = 0
        total_checked = 0
        
        corners = [
            (0, 0),
            (width - corner_size, 0),
            (0, height - corner_size),
            (width - corner_size, height - corner_size),
        ]
        
        for cx, cy in corners:
            for dy in range(corner_size):
                for dx in range(corner_size):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < width and 0 <= y < height:
                        idx = y * rowstride + x * n_channels + 3
                        if idx < len(pixels):
                            total_checked += 1
                            if pixels[idx] > 200:
                                opaque_corners += 1
        
        if total_checked > 0:
            return opaque_corners / total_checked > 0.7
        
        return False
        
    except Exception:
        return False
