# -*- coding: utf-8 -*-
"""Точка входа."""

import sys
from .application import Application


def main():
    app = Application()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
