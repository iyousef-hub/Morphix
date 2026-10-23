"""Bundled artwork paths for local development and PyInstaller builds."""
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"

def logo_png():
    return str(ASSETS / "morphix_logo.png")

def logo_svg():
    return str(ASSETS / "morphix_logo.svg")
