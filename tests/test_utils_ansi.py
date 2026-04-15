"""
Tests for utils/ansi.py — verify the shared ANSI constants are exported
and actually produce ANSI escape sequences.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.ansi import (
    RESET, BOLD, DIM, RED, GREEN, YELLOW, BLUE, CYAN, WHITE, GRAY
)


def test_all_constants_are_strings():
    for name, val in [("RESET", RESET), ("BOLD", BOLD), ("DIM", DIM),
                      ("RED", RED), ("GREEN", GREEN), ("YELLOW", YELLOW),
                      ("BLUE", BLUE), ("CYAN", CYAN), ("WHITE", WHITE),
                      ("GRAY", GRAY)]:
        assert isinstance(val, str), f"{name} should be a string"


def test_all_constants_start_with_escape():
    for name, val in [("RESET", RESET), ("BOLD", BOLD), ("DIM", DIM),
                      ("RED", RED), ("GREEN", GREEN), ("YELLOW", YELLOW),
                      ("BLUE", BLUE), ("CYAN", CYAN), ("WHITE", WHITE),
                      ("GRAY", GRAY)]:
        assert val.startswith("\033["), f"{name} should start with ESC["


def test_reset_is_generic():
    assert RESET == "\033[0m"


def test_constants_are_distinct():
    vals = [RESET, BOLD, DIM, RED, GREEN, YELLOW, BLUE, CYAN, WHITE, GRAY]
    assert len(vals) == len(set(vals)), "All ANSI constants should be distinct"
