"""
AIOS shared ANSI terminal colour constants.

All modules that print coloured output import from here so the
definitions exist in exactly one place.
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
