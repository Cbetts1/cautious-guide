"""
AIOS — Shared ANSI colour constants.

Import these instead of redefining them in every module::

    from utils.colors import RESET, BOLD, CYAN, GREEN, RED, YELLOW
"""

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[1;31m"
GREEN  = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE   = "\033[1;34m"
CYAN   = "\033[1;36m"
WHITE  = "\033[1;37m"
GRAY   = "\033[0;37m"
