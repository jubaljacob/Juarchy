#!/usr/bin/env python3
"""Keep Thunar's foreground colors readable after Caelestia regenerates GTK CSS."""

import os
from pathlib import Path


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
MARKER = "/* Thunar readable foregrounds */"
COLORS = """
/* Thunar readable foregrounds */
.thunar.background,
.thunar .titlebar,
.thunar .sidebar,
.thunar .view,
.thunar .view cell,
.thunar .sidebar .view,
.thunar .frame.standard-view .view,
.thunar label,
.thunar button,
.thunar entry,
.thunar menubar,
.thunar menu,
.thunar popover {
    color: @window_fg_color;
}

.thunar button,
.thunar entry {
    background-color: @card_bg_color;
    background-image: none;
}

.thunar menu,
.thunar popover {
    background-color: @popover_bg_color;
}

.thunar entry {
    caret-color: @window_fg_color;
}

.thunar .view:selected,
.thunar .view:selected:backdrop,
.thunar .view cell:selected,
.thunar .sidebar .view:selected,
.thunar .frame.standard-view .view:selected,
.thunar .frame.standard-view .view *:selected,
.thunar button:checked,
.thunar button:checked label,
.thunar button.toggle:checked,
.thunar button.toggle:checked label,
.thunar header.top tabs .reorderable-page:checked label,
.thunar menuitem:hover,
.thunar menuitem:hover label {
    color: @accent_color;
}

.thunar entry selection {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
}

.thunar :disabled,
.thunar :disabled label,
.thunar :disabled image {
    color: alpha(@window_fg_color, 0.55);
}
"""


def update(path: Path, transform) -> None:
    if path.is_file():
        original = path.read_text()
        changed = transform(original)
        if changed != original:
            path.write_text(changed)


def main() -> None:
    for version in ("3.0", "4.0"):
        directory = CONFIG / f"gtk-{version}"
        update(
            directory / "gtk.css",
            lambda css: css.replace(
                "@define-color theme_selected_fg_color @primary;",
                "@define-color theme_selected_fg_color @accent_color;",
            ),
        )
        update(
            directory / "thunar.css",
            lambda css: css.split(MARKER, 1)[0].rstrip() + "\n" + COLORS,
        )


if __name__ == "__main__":
    main()
