"""The dashboard's colours (config/theme.yaml): write the Streamlit theme and check colour contrast.

WHAT THIS SCRIPT DOES
---------------------
1. Reads config/theme.yaml (the only place colours are kept).
2. Writes the [theme] and [theme.sidebar] sections of .streamlit/config.toml from it (other sections are kept).
3. Checks every colour pair listed under contrast_checks against WCAG AA (4.5:1 for text, 3:1 for large text and
   chart marks) and prints the result. The dashboard itself reads theme.yaml for its CSS and chart colours.

HOW TO RUN
    python src/theme.py          (after changing config/theme.yaml; then restart the dashboard)
"""

from __future__ import annotations

import re
from pathlib import Path

from common import PROJECT_ROOT, load_yaml

CONFIG_TOML = PROJECT_ROOT / ".streamlit" / "config.toml"


def load_theme() -> dict:
    return load_yaml("theme.yaml")


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    def channel(c):
        c = int(h[c:c + 2], 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(0) + 0.7152 * channel(2) + 0.0722 * channel(4)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours (1 to 21)."""
    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def colour(theme: dict, ref: str) -> str:
    """'primary', 'status.on_track', 'chart.0' or 'logo.green' -> its hex code."""
    if ref.startswith("status."):
        return theme["status"][ref.split(".", 1)[1]]
    if ref.startswith("chart."):
        return theme["chart_categorical"][int(ref.split(".", 1)[1])]
    if ref.startswith("logo."):
        return theme["logo_colours"][ref.split(".", 1)[1]]
    return theme["colours"][ref]


def contrast_report(theme: dict | None = None) -> list[dict]:
    theme = theme or load_theme()
    rows = []
    for fg, bg, minimum, what in theme["contrast_checks"]:
        a, b = colour(theme, fg), colour(theme, bg)
        ratio = contrast(a, b)
        rows.append(dict(pair=f"{fg} {a} on {bg} {b}", what=what, ratio=round(ratio, 2), minimum=minimum,
                         passes=ratio >= minimum))
    return rows


def theme_toml(theme: dict) -> str:
    c = theme["colours"]
    chart = ", ".join(f'"{x}"' for x in theme["chart_categorical"])
    return f'''[theme]
# Written by src/theme.py from config/theme.yaml: change the colours there, not here.
base = "light"
primaryColor = "{c['primary']}"
backgroundColor = "{c['page_background']}"
secondaryBackgroundColor = "{c['card_background']}"
textColor = "{c['text']}"
linkColor = "{c['link']}"
borderColor = "{c['border']}"
font = "sans serif"
chartCategoricalColors = [{chart}]

[theme.sidebar]
backgroundColor = "{c['primary']}"
secondaryBackgroundColor = "{c['sidebar_input_background']}"
textColor = "{c['sidebar_text']}"
primaryColor = "{c['white']}"
linkColor = "{c['sidebar_text']}"
borderColor = "{c['primary_dark']}"
'''


def write_config(theme: dict | None = None, path: Path = CONFIG_TOML) -> None:
    """Replace the theme sections of config.toml, keeping every other section."""
    theme = theme or load_theme()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    kept = re.sub(r"\[theme(\.[a-z]+)?\][^\[]*", "", text).strip()
    path.write_text(theme_toml(theme) + "\n" + kept + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    write_config()
    print(f"Wrote the theme to {CONFIG_TOML}")
    failed = 0
    for r in contrast_report():
        mark = "pass" if r["passes"] else "FAIL"
        failed += not r["passes"]
        print(f"  {mark}  {r['ratio']:5.2f} (needs {r['minimum']})  {r['what']}: {r['pair']}")
    print(f"{failed} pair(s) below the minimum.")
    return 0


if __name__ == "__main__":
    main()
