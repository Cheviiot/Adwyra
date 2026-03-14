# -*- coding: utf-8 -*-
"""Core модуль — бизнес-логика приложения."""

from .config import config
from .apps import AppService
from .favorites import favorites
from .folders import folders
from .search import SearchService
from .aliases import aliases
from .hidden_apps import hidden_apps
from .keybindings import keybindings
from .update_checker import UpdateChecker
from .plugins import plugin_manager, AdwyraPlugin
