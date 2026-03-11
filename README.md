# Adwyra

<p align="center">
  <img src="data/icons/hicolor/128x128/apps/com.github.adwyra.png" alt="Adwyra" width="128">
</p>

<p align="center">
  <strong>Минималистичный лаунчер приложений для GNOME</strong>
</p>

<p align="center">
  <img src="screenshots/screenshot.png" alt="Adwyra Screenshot" width="600">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/GTK-4.0-green?style=flat-square" alt="GTK 4">
  <img src="https://img.shields.io/badge/Libadwaita-1.0-blue?style=flat-square" alt="Libadwaita">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/License-GPL--3.0-red?style=flat-square" alt="License">
</p>

---

## Возможности

- 📱 **Сетка приложений** — настраиваемый размер иконок и сетки
- 📁 **Папки** — группировка перетаскиванием
- 🔍 **Поиск** — мгновенный поиск по названию
- ✏️ **Переименование** — локальные псевдонимы приложений
- ⭐ **Закрепление** — избранные приложения всегда первые
- 🎨 **Темы** — автоматическая, светлая, тёмная
- ⚡ **Автозакрытие** — при запуске или потере фокуса

## Установка

### Stapler

```bash
stplr repo add adwyra https://github.com/cheviiot/adwyra.git
stplr refresh && stplr install adwyra
```

### Вручную

```bash
git clone https://github.com/cheviiot/adwyra.git
cd adwyra && ./adwyra
```

<details>
<summary><strong>Зависимости</strong></summary>

| Дистрибутив | Команда |
|-------------|---------|
| Debian/Ubuntu | `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1` |
| Fedora | `sudo dnf install python3-gobject gtk4 libadwaita` |
| Arch | `sudo pacman -S python-gobject gtk4 libadwaita` |
| ALT Linux | `sudo apt-get install python3-module-pygobject3 libgtk4 libadwaita` |

</details>

## Использование

```bash
adwyra          # Открыть
adwyra --toggle # Показать/скрыть
```

**Совет:** назначьте `adwyra --toggle` на горячую клавишу в настройках GNOME или прямо в приложении.

## Управление

| Действие | Способ |
|----------|--------|
| Запустить | Клик |
| Создать папку | Перетащить на приложение |
| Переименовать | ПКМ → Переименовать |
| Закрепить | ПКМ → Закрепить |
| Настройки | Кнопка ⚙ |
| Закрыть | `Esc` |

## Лицензия

[GPL-3.0-or-later](LICENSE)
