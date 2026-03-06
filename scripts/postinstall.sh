#!/bin/bash
# Скрипт после установки/обновления
# Запускается как root

# Удаляем старые __pycache__ и удалённые файлы (*.pyc для несуществующих .py)
find /usr/lib/adwyra -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Компилируем Python байткод для ускорения запуска
if command -v python3 &>/dev/null; then
    python3 -m compileall -q /usr/lib/adwyra 2>/dev/null || true
fi

# Обновляем кэш иконок
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -q /usr/share/icons/hicolor 2>/dev/null || true
fi

# Обновляем desktop базу данных
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi

exit 0
