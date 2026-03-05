# Adwyra

**Минималистичный лаунчер приложений для Gnome**

<p>
  <img src="https://img.shields.io/badge/GTK-4.0-green?style=flat-square" alt="GTK 4">
  <img src="https://img.shields.io/badge/Libadwaita-1.0-blue?style=flat-square" alt="Libadwaita">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/License-GPL--3.0-red?style=flat-square" alt="License">
</p>

## Возможности

- **Сетка приложений** — настраиваемый размер иконок и количество колонок/строк
- **Папки** — перетащите приложение на другое для группировки
- **Поиск** — мгновенный поиск по названию
- **Скрытие Dock-приложений** — не показывать закреплённые в GNOME Dock
- **Автозакрытие** — при запуске приложения или потере фокуса

## Установка

```bash
# Stapler
stplr repo add adwyra https://github.com/cheviiot/adwyra.git
stplr refresh && stplr install adwyra

# Вручную
git clone https://github.com/cheviiot/adwyra.git
cd adwyra && ./adwyra
```

### Зависимости

| Дистрибутив | Команда |
|-------------|---------|
| Debian/Ubuntu | `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1` |
| Fedora | `sudo dnf install python3-gobject gtk4 libadwaita` |
| Arch | `sudo pacman -S python-gobject gtk4 libadwaita` |
| ALT Linux | `sudo apt-get install python3-module-pygobject3 libgtk4 libadwaita` |

## Использование

```bash
adwyra          # Запуск
adwyra --toggle # Показать/скрыть
adwyra --show   # Показать
adwyra --hide   # Скрыть
```

### Горячая клавиша

Назначьте `adwyra --toggle` на системный шорткат через Настройки → Горячая клавиша.

### Управление

| Действие | Способ |
|----------|--------|
| Запуск | Клик по приложению |
| Создать папку | Перетащить приложение на другое |
| Удалить из папки | ПКМ → Удалить |
| Удалить папку | Кнопка корзины в заголовке |
| Настройки | Кнопка ⚙ справа снизу |
| Закрыть | `Esc` или клик вне окна |

## Лицензия

[GPL-3.0-or-later](LICENSE)
