#!/usr/bin/python3
# Copyright (C) 2026 Sebastiano Franchini
# SPDX-License-Identifier: GPL-3.0-or-later
import sys
import json
import os
import hashlib
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, Pango, Adw

DATA_DIR = os.path.expanduser('~/.local/share/clipstory')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
CURRENT_FILE = os.path.join(DATA_DIR, 'current')
GRAIN_FILE = os.path.join(DATA_DIR, 'grain.png')
GRAIN_LIGHT_FILE = os.path.join(DATA_DIR, 'grain-light.png')
GRAIN_SIZE = 96
IMAGES_DIR = os.path.join(DATA_DIR, 'images')
THUMBS_DIR = os.path.join(DATA_DIR, 'thumbs')
THUMB_WIDTH = 144
THUMB_HEIGHT = 96
THUMB_DISPLAY_WIDTH = 72
THUMB_DISPLAY_HEIGHT = 48
MAX_TEXT_CHARS = 200
PRIVATE_DIR_MODE = 0o700

SHOW_SETTINGS = False
if '--settings' in sys.argv:
    SHOW_SETTINGS = True
    sys.argv.remove('--settings')


GLASS_CSS = """
window.glass,
window.glass.background {
    background: none;
    background-color: transparent;
}

window.glass .glass-panel {
    color: #000000;
}

window.glass.glass-dark .glass-panel {
    color: #ffffff;
}

window.glass row .subtitle,
window.glass .dimmed,
window.glass .dim-label {
    opacity: 1;
    color: rgba(0, 0, 0, 0.72);
}

window.glass.glass-dark row .subtitle,
window.glass.glass-dark .dimmed,
window.glass.glass-dark .dim-label {
    color: rgba(255, 255, 255, 0.78);
}

window.glass row .title {
    opacity: 1;
    color: #000000;
}

window.glass.glass-dark row .title {
    color: #ffffff;
}

window.glass entry.search text placeholder {
    opacity: 1;
    color: rgba(0, 0, 0, 0.58);
}

window.glass.glass-dark entry.search text placeholder {
    color: rgba(255, 255, 255, 0.62);
}

window.glass.csd,
window.glass.background.csd {
    border-radius: 14px;
}

window.glass .glass-panel {
    border-radius: 14px;
    border: 1px solid rgba(0, 0, 0, 0.12);
    background-image:
        url("__GRAIN_LIGHT__"),
        radial-gradient(circle at 12% 0%, rgba(255, 255, 255, 0.70) 0%, rgba(255, 255, 255, 0) 55%),
        radial-gradient(circle at 100% 100%, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0) 45%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0) 40%),
        linear-gradient(rgba(90, 120, 175, 0.04), rgba(90, 120, 175, 0.04)),
        linear-gradient(180deg,
            rgba(250, 250, 252, 0.93) 0%,
            rgba(238, 240, 243, 0.91) 45%,
            rgba(208, 212, 219, 0.90) 100%);
    box-shadow:
        inset 0 1.5px 0 rgba(255, 255, 255, 0.95),
        inset 0 0 0 1px rgba(255, 255, 255, 0.40),
        inset 0 -14px 26px -16px rgba(0, 0, 0, 0.14);
}

window.glass.glass-dark .glass-panel {
    border: 1px solid rgba(255, 255, 255, 0.14);
    background-image:
        url("__GRAIN__"),
        radial-gradient(circle at 12% 0%, rgba(255, 255, 255, 0.17) 0%, rgba(255, 255, 255, 0) 55%),
        radial-gradient(circle at 100% 100%, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0) 45%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.07) 0%, rgba(255, 255, 255, 0) 40%),
        linear-gradient(rgba(70, 105, 175, 0.07), rgba(70, 105, 175, 0.07)),
        linear-gradient(180deg,
            rgba(52, 56, 66, 0.91) 0%,
            rgba(36, 39, 47, 0.91) 50%,
            rgba(27, 29, 35, 0.93) 100%);
    box-shadow:
        inset 0 1.5px 0 rgba(255, 255, 255, 0.32),
        inset 0 0 0 1px rgba(255, 255, 255, 0.10),
        inset 0 -1px 0 rgba(255, 255, 255, 0.06),
        inset 0 -16px 28px -18px rgba(0, 0, 0, 0.55);
}

window.glass headerbar {
    background: none;
    box-shadow: none;
    border: none;
    color: @window_fg_color;
}

window.glass list.boxed-list {
    border: 1px solid alpha(@window_fg_color, 0.08);
    border-radius: 12px;
    background-color: alpha(@window_fg_color, 0.06);
    box-shadow: none;
}

window.glass list.boxed-list > row {
    background: none;
}

window.glass entry.search {
    min-height: 28px;
    padding: 0 8px;
    border: none;
    border-radius: 8px;
    background-color: alpha(@window_fg_color, 0.08);
    box-shadow: inset 0 1px 0 alpha(white, 0.55);
}

window.glass entry.search:focus-within {
    outline: none;
    background-color: alpha(@window_fg_color, 0.11);
    box-shadow: inset 0 1px 0 alpha(white, 0.55);
}

window.glass list.clip-list {
    background: none;
}

window.glass row.clip-row {
    margin: 1px 6px;
    border: none;
    border-radius: 8px;
    background: none;
    transition: background-color 100ms ease;
}

window.glass row.clip-row:hover {
    background-color: alpha(@window_fg_color, 0.07);
}

window.glass row.clip-row:selected {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
}

window.glass .clip-text,
window.glass .clip-title {
    font-size: 13px;
}

window.glass .clip-title {
    font-weight: 600;
}

window.glass .clip-subtitle {
    font-size: 11px;
    color: rgba(0, 0, 0, 0.72);
}

window.glass.glass-dark .clip-subtitle {
    color: rgba(255, 255, 255, 0.78);
}

window.glass row.clip-row:selected .clip-subtitle {
    color: alpha(@accent_fg_color, 0.8);
}

window.glass .pin-dot {
    min-width: 8px;
    min-height: 8px;
    background-color: alpha(@window_fg_color, 0.35);
    border-radius: 50%;
}

window.glass row.clip-row:selected .pin-dot {
    background-color: alpha(@accent_fg_color, 0.85);
}

window.glass .current-dot {
    min-width: 8px;
    min-height: 8px;
    background-color: @accent_bg_color;
    border-radius: 50%;
}

window.glass row.clip-row:selected .current-dot {
    background-color: transparent;
    border: 2px solid alpha(@accent_fg_color, 0.95);
}

window.glass .clip-thumb {
    border-radius: 5px;
    border: 1px solid alpha(@window_fg_color, 0.18);
}

window.glass .section-header {
    margin: 8px 16px 2px 16px;
    font-size: 11px;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.68);
}

window.glass.glass-dark .section-header {
    color: rgba(255, 255, 255, 0.72);
}

window.glass .clip-footer {
    padding: 7px 12px;
    border-top: 1px solid alpha(@window_fg_color, 0.08);
    font-size: 11px;
    color: rgba(0, 0, 0, 0.72);
}

window.glass.glass-dark .clip-footer {
    color: rgba(255, 255, 255, 0.80);
}
"""


def apply_scheme_class(window, style_manager, param=None):
    """Mark the window with 'glass-dark' while a dark colour scheme is active."""
    if style_manager.get_dark():
        window.add_css_class("glass-dark")
    else:
        window.remove_css_class("glass-dark")


def build_css():
    """Return the stylesheet with the path of the grain texture filled in."""
    return (GLASS_CSS
            .replace("__GRAIN_LIGHT__", Gio.File.new_for_path(GRAIN_LIGHT_FILE).get_uri())
            .replace("__GRAIN__", Gio.File.new_for_path(GRAIN_FILE).get_uri()))


def write_grain_tile(path, darkness, alpha):
    """Write a GRAIN_SIZE square tile of random grey noise; darkness (0-1) scales the grey level."""
    noise = bytes(int(value * darkness) for value in os.urandom(GRAIN_SIZE * GRAIN_SIZE))
    pixels = bytearray(GRAIN_SIZE * GRAIN_SIZE * 4)
    pixels[0::4] = noise
    pixels[1::4] = noise
    pixels[2::4] = noise
    pixels[3::4] = bytes([alpha]) * (GRAIN_SIZE * GRAIN_SIZE)
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        GLib.Bytes.new(bytes(pixels)), GdkPixbuf.Colorspace.RGB, True, 8,
        GRAIN_SIZE, GRAIN_SIZE, GRAIN_SIZE * 4)
    pixbuf.savev(path, 'png', [], [])


def ensure_grain_texture():
    """Create the noise tiles that give the glass a frosted grain, if they are missing.

    The dark glass uses a mid-grey grain; the light glass needs a darker and slightly
    stronger one, otherwise it disappears against the bright background.
    """
    try:
        os.makedirs(DATA_DIR, mode=PRIVATE_DIR_MODE, exist_ok=True)
        if not os.path.exists(GRAIN_FILE):
            write_grain_tile(GRAIN_FILE, 1.0, 14)
        if not os.path.exists(GRAIN_LIGHT_FILE):
            write_grain_tile(GRAIN_LIGHT_FILE, 0.55, 26)
    except (GLib.Error, OSError) as e:
        print(f"Error creating grain texture: {e}")


def item_digest(item):
    return hashlib.sha256(item_key(item).encode('utf-8')).hexdigest()


def load_current_digest():
    """Digest of the entry that is currently in the clipboard, as recorded by the extension."""
    try:
        with open(CURRENT_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return None


def item_key(item):
    """Identity of a history entry: stored image name or text content."""
    if item.get("image") is not None:
        return "image:" + item["image"]
    return "text:" + item.get("text", "")


def describe_image(name):
    """Return a short description such as '480 x 300 - 136 KB' for a stored image."""
    path = os.path.join(IMAGES_DIR, name)
    try:
        file_info = GdkPixbuf.Pixbuf.get_file_info(path)
        size = os.path.getsize(path)
    except OSError:
        return ""
    size_text = f"{size / (1024 * 1024):.1f} MB" if size >= 1024 * 1024 else f"{max(1, round(size / 1024))} KB"
    if file_info[0] is None:
        return size_text
    return f"{file_info[1]} \u00d7 {file_info[2]} \u00b7 {size_text}"


def make_thumbnail(source_path, thumb_path):
    """Write a THUMB_WIDTH x THUMB_HEIGHT tile: the image scaled to cover it and centre-cropped."""
    file_info = GdkPixbuf.Pixbuf.get_file_info(source_path)
    if file_info[0] is None:
        raise OSError("unreadable image")
    source_width, source_height = file_info[1], file_info[2]
    scale = max(THUMB_WIDTH / source_width, THUMB_HEIGHT / source_height)
    width = max(THUMB_WIDTH, round(source_width * scale))
    height = max(THUMB_HEIGHT, round(source_height * scale))
    scaled = GdkPixbuf.Pixbuf.new_from_file_at_scale(source_path, width, height, False)
    tile = scaled.new_subpixbuf((width - THUMB_WIDTH) // 2, (height - THUMB_HEIGHT) // 2,
                                THUMB_WIDTH, THUMB_HEIGHT)
    tile.savev(thumb_path, 'png', [], [])


def load_thumbnail(name):
    """Return the cached tile texture of a stored image, creating or refreshing it when needed."""
    thumb_path = os.path.join(THUMBS_DIR, name)
    try:
        if os.path.exists(thumb_path):
            texture = Gdk.Texture.new_from_filename(thumb_path)
            if (texture.get_width(), texture.get_height()) == (THUMB_WIDTH, THUMB_HEIGHT):
                return texture
        os.makedirs(THUMBS_DIR, mode=PRIVATE_DIR_MODE, exist_ok=True)
        make_thumbnail(os.path.join(IMAGES_DIR, name), thumb_path)
        return Gdk.Texture.new_from_filename(thumb_path)
    except (GLib.Error, OSError) as e:
        print(f"Error loading thumbnail: {e}")
        return None


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"theme": "system"}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {"theme": "system"}


def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), mode=PRIVATE_DIR_MODE, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f)
    except Exception as e:
        print(f"Error saving settings: {e}")


class ClipstorySettingsWindow(Adw.ApplicationWindow):
    """Settings, a keyboard reference with the meaning of the markers, and an about page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Clipstory")
        self.set_default_size(540, 580)
        self.add_css_class("glass")
        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", lambda manager, param: apply_scheme_class(self, manager))
        apply_scheme_class(self, style_manager)

        self.settings = load_settings()

        stack = Adw.ViewStack()
        stack.set_vexpand(True)
        stack.add_titled_with_icon(self.build_general_page(), "general", "General", "emblem-system-symbolic")
        stack.add_titled_with_icon(self.build_shortcuts_page(), "shortcuts", "Shortcuts", "input-keyboard-symbolic")
        stack.add_titled_with_icon(self.build_about_page(), "about", "About", "help-about-symbolic")

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE))

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.add_css_class("glass-panel")
        panel.set_overflow(Gtk.Overflow.HIDDEN)
        panel.append(header)
        panel.append(stack)
        self.set_content(panel)

    @staticmethod
    def add_rows(group, rows):
        for title, subtitle in rows:
            row = Adw.ActionRow(title=title, subtitle=subtitle)
            row.set_subtitle_lines(0)
            group.add(row)

    def build_general_page(self):
        page = Adw.PreferencesPage()

        group_theme = Adw.PreferencesGroup()
        group_theme.set_title("Appearance")
        group_theme.set_description("Clipstory can follow the GNOME colour scheme or stay light or dark.")
        page.add(group_theme)

        model = Gtk.StringList.new(["System", "Light", "Dark"])
        self.combo_theme = Adw.ComboRow(title="Theme")
        self.combo_theme.set_model(model)
        theme_val = self.settings.get("theme", "system")
        self.combo_theme.set_selected({"light": 1, "dark": 2}.get(theme_val, 0))
        self.combo_theme.connect("notify::selected", self.on_theme_changed)
        group_theme.add(self.combo_theme)

        group_data = Adw.PreferencesGroup()
        group_data.set_title("Your data")
        group_data.set_description("Everything stays on this computer. Nothing is sent over the network.")
        page.add(group_data)
        self.add_rows(group_data, [
            ("History", "~/.local/share/clipstory/history.json (the last 50 entries; pinned entries are always kept)"),
            ("Images", "~/.local/share/clipstory/images, with small previews in thumbs"),
            ("Privacy", "Only you can read these files. Copied passwords are stored too, so clear the history if needed."),
        ])
        return page

    def build_shortcuts_page(self):
        page = Adw.PreferencesPage()

        group_open = Adw.PreferencesGroup()
        group_open.set_title("Open and choose")
        page.add(group_open)
        self.add_rows(group_open, [
            ("Open the history", "Super + V, or click the icon in the top bar"),
            ("Search", "Just start typing"),
            ("Choose an entry", "Up / Down"),
            ("Copy the entry", "Enter, or click it. Then paste with Ctrl + V where you want it"),
            ("Close", "Escape"),
        ])

        group_manage = Adw.PreferencesGroup()
        group_manage.set_title("Manage entries")
        page.add(group_manage)
        self.add_rows(group_manage, [
            ("Pin or unpin", "Ctrl + Enter. Pinned entries stay at the top and are never discarded"),
            ("Move a pinned entry", "Ctrl + Up / Ctrl + Down"),
            ("Delete", "Delete key, while the search field is empty"),
        ])

        group_markers = Adw.PreferencesGroup()
        group_markers.set_title("What the dots mean")
        page.add(group_markers)
        self.add_rows(group_markers, [
            ("Grey dot", "The entry is pinned"),
            ("Coloured dot", "This entry is what is in your clipboard right now (on the selected row it is a ring)"),
        ])
        return page

    def build_about_page(self):
        page = Adw.PreferencesPage()

        group = Adw.PreferencesGroup()
        group.set_title("Clipstory")
        group.set_description("Clipboard history for GNOME on Wayland. Text and images, search, pinning.")
        page.add(group)
        self.add_rows(group, [
            ("How it works", "A small GNOME Shell extension watches the clipboard and saves what you copy. "
                             "This window, opened with Super + V, lets you search it and copy an entry back."),
            ("Limits", "Choosing an entry puts it in the clipboard; paste it yourself with Ctrl + V. "
                       "Wayland does not allow an app to type into another one."),
            ("Source and licence", "github.com/Sestiano/clipstory, GPL-3.0-or-later"),
        ])
        return page

    def on_theme_changed(self, combo, param):
        selected = combo.get_selected()
        theme = "system"
        style_manager = Adw.StyleManager.get_default()
        if selected == 1:
            theme = "light"
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif selected == 2:
            theme = "dark"
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

        self.settings["theme"] = theme
        save_settings(self.settings)


class ClipstoryWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Clipboard History")
        self.set_default_size(400, -1)
        self.add_css_class("glass")
        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", lambda manager, param: apply_scheme_class(self, manager))
        apply_scheme_class(self, style_manager)

        self.history = self.load_history()
        self.has_pinned = False
        self.current_digest = load_current_digest()
        self.handing_over = False

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.add_css_class("glass-panel")
        vbox.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_content(vbox)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search")
        self.search.set_margin_top(10)
        self.search.set_margin_bottom(4)
        self.search.set_margin_start(10)
        self.search.set_margin_end(10)
        self.search.connect("search-changed", self.on_search_changed)
        vbox.append(self.search)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_propagate_natural_height(True)
        self.scrolled.set_max_content_height(500)
        self.scrolled.set_min_content_height(150)

        vbox.append(self.scrolled)

        footer = Gtk.Label(label="\u2191 \u2193 select    \u21b5 copy    Ctrl \u21b5 pin    Del delete", xalign=0.5)
        footer.add_css_class("clip-footer")
        vbox.append(footer)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_focusable(False)
        self.listbox.set_filter_func(self.filter_row)
        self.listbox.set_header_func(self.update_header)
        self.listbox.connect("row-activated", self.on_row_activated)
        self.listbox.add_css_class("clip-list")
        self.listbox.set_margin_top(4)
        self.listbox.set_margin_bottom(6)

        self.scrolled.set_child(self.listbox)

        self.populate_listbox()

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_ctrl)

        self.connect("notify::is-active", self.on_is_active_changed)
        GLib.idle_add(self.search.grab_focus)

    def iter_rows(self):
        """Yield the history rows (skips the placeholder shown for an empty history)."""
        child = self.listbox.get_first_child()
        while child is not None:
            if hasattr(child, 'key'):
                yield child
            child = child.get_next_sibling()

    def filter_row(self, row):
        query = self.search.get_text().strip().lower()
        search_text = getattr(row, 'search_text', None)
        if not query or search_text is None:
            return True
        return query in search_text

    def update_header(self, row, before):
        """Show a 'Pinned' / 'Recent' heading above the first row of each group."""
        if not hasattr(row, 'key') or not self.has_pinned:
            row.set_header(None)
            return
        if before is None or getattr(before, 'pinned', None) != row.pinned:
            header = row.get_header()
            if header is None:
                header = Gtk.Label(xalign=0.0)
                header.add_css_class("section-header")
                row.set_header(header)
            header.set_label("Pinned" if row.pinned else "Recent")
        else:
            row.set_header(None)

    def visible_rows(self):
        return [row for row in self.iter_rows() if self.filter_row(row)]

    def on_search_changed(self, entry):
        self.listbox.invalidate_filter()
        self.select_first_visible()

    def select_first_visible(self):
        rows = self.visible_rows()
        if rows:
            self.listbox.select_row(rows[0])
            self.scroll_to_row(rows[0])
        else:
            self.listbox.unselect_all()

    def move_selection(self, step):
        rows = self.visible_rows()
        if not rows:
            return
        current = self.listbox.get_selected_row()
        if current in rows:
            index = max(0, min(len(rows) - 1, rows.index(current) + step))
        else:
            index = 0
        self.listbox.select_row(rows[index])
        self.scroll_to_row(rows[index])

    def scroll_to_row(self, row):
        found, bounds = row.compute_bounds(self.listbox)
        if not found:
            return
        adjustment = self.scrolled.get_vadjustment()
        top = bounds.get_y()
        bottom = top + bounds.get_height()
        if top < adjustment.get_value():
            adjustment.set_value(top)
        elif bottom > adjustment.get_value() + adjustment.get_page_size():
            adjustment.set_value(bottom - adjustment.get_page_size())

    def on_key_pressed(self, controller, keyval, keycode, state):
        is_ctrl = (state & Gdk.ModifierType.CONTROL_MASK) != 0

        if keyval == Gdk.KEY_Escape:
            self.get_application().quit()
            return True
        elif keyval == Gdk.KEY_Delete:
            if self.search.get_text():
                return False
            row = self.listbox.get_selected_row()
            if row and hasattr(row, 'key'):
                self.delete_item(row)
                return True
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self.listbox.get_selected_row()
            if row and hasattr(row, 'key'):
                if is_ctrl:
                    self.toggle_pin(row)
                else:
                    self.on_row_activated(self.listbox, row)
            return True
        elif keyval == Gdk.KEY_Up:
            row = self.listbox.get_selected_row()
            if is_ctrl:
                if row and hasattr(row, 'key'):
                    self.move_pinned_item(row, -1)
            else:
                self.move_selection(-1)
            return True
        elif keyval == Gdk.KEY_Down:
            row = self.listbox.get_selected_row()
            if is_ctrl:
                if row and hasattr(row, 'key'):
                    self.move_pinned_item(row, 1)
            else:
                self.move_selection(1)
            return True
        return False

    def find_item(self, key):
        for item in self.history:
            if item_key(item) == key:
                return item
        return None

    def toggle_pin(self, row):
        key = row.key
        item = self.find_item(key)
        if item is None:
            return
        item["pinned"] = not item.get("pinned", False)
        if item["pinned"]:
            pinned = [i for i in self.history if i.get("pinned")]
            max_order = max([i.get("pin_order", 0) for i in pinned] + [-1])
            item["pin_order"] = max_order + 1
        else:
            item.pop("pin_order", None)
        self.save_history()
        self.populate_listbox()
        self.select_row_by_key(key)

    def move_pinned_item(self, row, direction):
        key = row.key

        pinned_items = [item for item in self.history if item.get("pinned")]
        pinned_items.sort(key=lambda x: x.get("pin_order", 0))

        idx = -1
        for i, item in enumerate(pinned_items):
            if item_key(item) == key:
                idx = i
                break

        if idx == -1:
            return

        new_idx = idx + direction
        if 0 <= new_idx < len(pinned_items):
            tmp = pinned_items[idx].get("pin_order", 0)
            pinned_items[idx]["pin_order"] = pinned_items[new_idx].get("pin_order", 0)
            pinned_items[new_idx]["pin_order"] = tmp
            self.save_history()
            self.populate_listbox()
            self.select_row_by_key(key)

    def select_row_by_key(self, key):
        for row in self.iter_rows():
            if row.key == key:
                self.listbox.select_row(row)
                self.scroll_to_row(row)
                return

    def delete_item(self, row):
        item = self.find_item(row.key)
        if item is not None and item.get("image") is not None:
            for directory in (IMAGES_DIR, THUMBS_DIR):
                try:
                    os.remove(os.path.join(directory, item["image"]))
                except FileNotFoundError:
                    pass
                except OSError as e:
                    print(f"Error deleting image file: {e}")
        self.history = [i for i in self.history if item_key(i) != row.key]
        self.save_history()

        self.listbox.remove(row)
        if not self.history:
            self.populate_listbox()
        else:
            self.select_first_visible()

    def save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), mode=PRIVATE_DIR_MODE, exist_ok=True)
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Error saving history: {e}")

    def on_is_active_changed(self, window, param):
        if self.handing_over:
            return
        if not self.get_property("is-active"):
            GLib.timeout_add(100, self.get_application().quit)

    def load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def populate_listbox(self):
        # Clear existing rows first
        while child := self.listbox.get_first_child():
            self.listbox.remove(child)

        if not self.history:
            label = Gtk.Label(label="Clipboard is empty", xalign=0.5, yalign=0.5)
            label.set_margin_top(24)
            label.set_margin_bottom(24)
            label.add_css_class("dim-label")
            self.listbox.append(label)
            return

        pinned_items = [item for item in self.history if item.get("pinned")]
        unpinned_items = [item for item in reversed(self.history) if not item.get("pinned")]
        self.has_pinned = bool(pinned_items)

        pinned_items.sort(key=lambda x: x.get("pin_order", 0))

        for item in pinned_items:
            self.add_row(item)

        for item in unpinned_items:
            self.add_row(item)

        self.select_first_visible()

    def build_thumbnail(self, name):
        """Return a small rounded preview, or None when the image cannot be read."""
        texture = load_thumbnail(name)
        if texture is None:
            return None
        picture = Gtk.Picture.new_for_paintable(texture)
        picture.set_can_shrink(True)
        picture.set_content_fit(Gtk.ContentFit.COVER)

        # The spacer fixes the displayed size; the picture is an overlay so its larger
        # (2x) pixel size does not enlarge the row.
        spacer = Gtk.Box()
        spacer.set_size_request(THUMB_DISPLAY_WIDTH, THUMB_DISPLAY_HEIGHT)
        frame = Gtk.Overlay()
        frame.set_child(spacer)
        frame.add_overlay(picture)
        frame.set_overflow(Gtk.Overflow.HIDDEN)
        frame.set_valign(Gtk.Align.CENTER)
        frame.add_css_class("clip-thumb")
        return frame

    def build_content(self, item):
        """Return the widget shown inside a row and the lowercase text used for searching."""
        if item.get("image") is not None:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_start(10)
            box.set_margin_end(10)
            box.set_margin_top(6)
            box.set_margin_bottom(6)

            frame = self.build_thumbnail(item["image"])
            if frame is not None:
                box.append(frame)

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            details.set_valign(Gtk.Align.CENTER)
            title = Gtk.Label(label="Image", xalign=0.0)
            title.add_css_class("clip-title")
            subtitle = Gtk.Label(label=describe_image(item["image"]), xalign=0.0)
            subtitle.add_css_class("clip-subtitle")
            details.append(title)
            details.append(subtitle)
            box.append(details)
            return box, "image"

        text = item.get("text", "")
        display_text = text.strip()
        if len(display_text) > MAX_TEXT_CHARS:
            display_text = display_text[:MAX_TEXT_CHARS - 3] + "..."

        label = Gtk.Label(label=display_text, xalign=0.0)
        label.add_css_class("clip-text")
        label.set_margin_start(10)
        label.set_margin_end(10)
        label.set_margin_top(7)
        label.set_margin_bottom(7)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_lines(2)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        return label, text.lower()

    def add_row(self, item):
        content, search_text = self.build_content(item)
        content.set_hexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(content)

        markers = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        markers.set_valign(Gtk.Align.CENTER)
        markers.set_margin_end(12)
        if self.current_digest is not None and item_digest(item) == self.current_digest:
            current_dot = Gtk.Box()
            current_dot.set_valign(Gtk.Align.CENTER)
            current_dot.add_css_class("current-dot")
            markers.append(current_dot)
        if item.get("pinned"):
            pin_dot = Gtk.Box()
            pin_dot.set_valign(Gtk.Align.CENTER)
            pin_dot.add_css_class("pin-dot")
            markers.append(pin_dot)
        if markers.get_first_child() is not None:
            box.append(markers)

        row = Gtk.ListBoxRow()
        row.set_focusable(False)
        row.add_css_class("clip-row")
        row.set_child(box)
        row.key = item_key(item)
        row.search_text = search_text
        row.pinned = bool(item.get("pinned"))
        row.image = item.get("image")
        row.full_text = item.get("text")
        self.listbox.append(row)

    def on_row_activated(self, listbox, row):
        if not hasattr(row, 'key'):
            return

        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        if row.image is not None:
            try:
                with open(os.path.join(IMAGES_DIR, row.image), 'rb') as f:
                    png_bytes = GLib.Bytes.new(f.read())
                clipboard.set_content(Gdk.ContentProvider.new_for_bytes('image/png', png_bytes))
            except OSError as e:
                print(f"Error reading image: {e}")
                return
        elif row.full_text:
            clipboard.set(row.full_text)
        print("Clipboard updated.")

        # Hide at once so the window does not seem frozen, but keep the process alive long
        # enough for the clipboard to be stored/noticed by the compositor.
        self.handing_over = True
        self.set_visible(False)
        GLib.timeout_add(500, self.get_application().quit)


class ClipstoryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="local.seb.clipstory",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_startup(self):
        Adw.Application.do_startup(self)
        settings = load_settings()
        theme = settings.get("theme", "system")
        style_manager = Adw.StyleManager.get_default()
        if theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

        css_provider = Gtk.CssProvider()
        ensure_grain_texture()
        css_provider.load_from_data(build_css().encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            if SHOW_SETTINGS:
                win = ClipstorySettingsWindow(application=self)
            else:
                win = ClipstoryWindow(application=self)
        win.present()


if __name__ == '__main__':
    app = ClipstoryApp()
    sys.exit(app.run(sys.argv))
