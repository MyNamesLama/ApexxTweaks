from pathlib import Path

ACCENT = "#bdff45"
BG = "#101211"
SURFACE = "#191c1a"
TEXT = "#f2f4ef"
MUTED = "#969e97"


def stylesheet():
    return (Path(__file__).parent / "assets" / "theme.qss").read_text(encoding="utf-8")
