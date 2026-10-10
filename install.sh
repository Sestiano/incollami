#!/usr/bin/env bash
# Copyright (C) 2026 Sebastiano Franchini
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Incollami installer. Installs for the current user only, no root needed.
#
#   curl -fsSL https://raw.githubusercontent.com/Sestiano/incollami/main/install.sh | bash
#
# From a clone of the repository:
#   ./install.sh [--keep-super-v] [--uninstall [--purge]] [--help]
#
# The script is safe to run again: it updates the installed files and does not
# change anything that is already in place.
set -euo pipefail

REPO="${INCOLLAMI_REPO:-Sestiano/incollami}"
REF="${INCOLLAMI_REF:-main}"
UUID="incollami@sestiano.github.io"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
EXT_DIR="$DATA_HOME/gnome-shell/extensions/$UUID"
DATA_DIR="$DATA_HOME/incollami"
APP_ID="io.github.sestiano.Incollami"
APPS_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
DESKTOP_FILE="$APPS_DIR/$APP_ID.desktop"
ICON_FILE="$ICON_DIR/$APP_ID.svg"
LEGACY_UUID="clipstory@seb.local"
LEGACY_EXT_DIR="$DATA_HOME/gnome-shell/extensions/$LEGACY_UUID"
LEGACY_DATA_DIR="$DATA_HOME/clipstory"
BACKUP_FILE="$DATA_DIR/.toggle-message-tray.orig"
TRAY_SCHEMA="org.gnome.shell.keybindings"
TRAY_KEY="toggle-message-tray"
SUPER_V="<Super>v"

MODE="install"
KEEP_SUPER_V=0
PURGE=0

if [[ -t 1 ]]; then
    BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
    BOLD=""; DIM=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

say()  { printf '%s\n' "${GREEN}==>${RESET} $*"; }
note() { printf '%s\n' "${DIM}    $*${RESET}"; }
warn() { printf '%s\n' "${YELLOW}warning:${RESET} $*" >&2; }
die()  { printf '%s\n' "${RED}error:${RESET} $*" >&2; exit 1; }

usage() {
    cat <<EOF
Usage: install.sh [options]

  (no options)      Install or update Incollami for the current user.
  --keep-super-v    Do not take Super+V away from the GNOME notification shortcut.
  --uninstall       Remove Incollami and restore the Super+V shortcut.
  --purge           With --uninstall, also delete the clipboard history and images.
  --help            Show this help.

Environment: INCOLLAMI_REPO (user/repo) and INCOLLAMI_REF (branch or tag) select
the source used when the script is run through curl.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --uninstall)   MODE="uninstall" ;;
        --keep-super-v) KEEP_SUPER_V=1 ;;
        --purge)       PURGE=1 ;;
        --help|-h)     usage; exit 0 ;;
        *)             usage >&2; die "unknown option: $arg" ;;
    esac
done

[[ $EUID -ne 0 ]] || die "run this as your normal user, not as root"
command -v gsettings >/dev/null 2>&1 || die "gsettings not found: this installer needs GNOME"

# Add or remove one value in a gsettings string-list key (for example enabled-extensions).
edit_list() {
    local schema="$1" key="$2" action="$3" value="$4"
    python3 - "$schema" "$key" "$action" "$value" <<'PY'
import ast
import subprocess
import sys

schema, key, action, value = sys.argv[1:5]
raw = subprocess.run(["gsettings", "get", schema, key], capture_output=True, text=True, check=True).stdout.strip()
if raw.startswith("@as"):
    raw = raw[3:].strip()
items = ast.literal_eval(raw)
if action == "add" and value not in items:
    items.append(value)
elif action == "remove":
    items = [item for item in items if item != value]
subprocess.run(["gsettings", "set", schema, key, repr(items)], check=True)
PY
}

list_contains() {
    gsettings get "$1" "$2" | grep -qF "'$3'"
}

refresh_launcher_caches() {
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
}

# An entry in the application grid, so the settings can be opened even when the top bar icon is hidden.
install_launcher() {
    local logo="$SOURCE_DIR/../docs/logo.svg"
    mkdir -p "$APPS_DIR" "$ICON_DIR"
    if [[ -f "$logo" ]]; then
        install -m 644 "$logo" "$ICON_FILE"
    fi
    cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Incollami
Comment=Clipboard history: settings
Exec=/usr/bin/python3 "$EXT_DIR/main.py" --settings
Icon=$APP_ID
Terminal=false
Categories=Utility;GTK;
StartupWMClass=$APP_ID
Actions=History;

[Desktop Action History]
Name=Open the history
Exec=/usr/bin/python3 "$EXT_DIR/main.py"
DESKTOP
    refresh_launcher_caches
    note "added the Incollami entry to the application grid"
}

do_uninstall() {
    say "Removing Incollami"
    if [[ -d "$EXT_DIR" ]]; then
        rm -rf "$EXT_DIR"
        note "removed $EXT_DIR"
    fi
    edit_list org.gnome.shell enabled-extensions remove "$UUID"
    rm -f "$DESKTOP_FILE" "$ICON_FILE"
    refresh_launcher_caches

    if [[ -f "$BACKUP_FILE" ]]; then
        gsettings set "$TRAY_SCHEMA" "$TRAY_KEY" "$(cat "$BACKUP_FILE")"
        rm -f "$BACKUP_FILE"
        note "restored the original $TRAY_KEY shortcut"
    fi

    if [[ $PURGE -eq 1 ]]; then
        rm -rf "$DATA_DIR"
        note "deleted $DATA_DIR (history, images and settings)"
    else
        note "your clipboard history is kept in $DATA_DIR (use --uninstall --purge to delete it)"
    fi
    say "Done. Log out and back in to unload the extension."
}

# Locate the extension files: next to this script when run from a clone, otherwise download them.
resolve_source() {
    local here=""
    if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
        here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    fi
    if [[ -n "$here" && -f "$here/extension/extension.js" ]]; then
        SOURCE_DIR="$here/extension"
        return
    fi

    command -v curl >/dev/null 2>&1 || die "curl is required to download Incollami"
    command -v tar  >/dev/null 2>&1 || die "tar is required to unpack Incollami"
    WORK_DIR="$(mktemp -d)"
    trap 'rm -rf "$WORK_DIR"' EXIT
    say "Downloading $REPO ($REF)"
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz --strip-components=1 -C "$WORK_DIR"
    [[ -f "$WORK_DIR/extension/extension.js" ]] || die "the download does not contain the extension files"
    SOURCE_DIR="$WORK_DIR/extension"
}

check_requirements() {
    command -v python3 >/dev/null 2>&1 || die "python3 is required"
    if command -v gnome-shell >/dev/null 2>&1; then
        local version major
        version="$(gnome-shell --version | grep -oE '[0-9]+(\.[0-9]+)*' | head -1)"
        major="${version%%.*}"
        if [[ "$major" -lt 45 ]]; then
            die "GNOME Shell $version is too old: Incollami needs 45 or newer"
        fi
        note "GNOME Shell $version"
    else
        warn "gnome-shell not found; continuing, but the extension needs GNOME Shell 45 or newer"
    fi

    if ! python3 - <<'PY' 2>/dev/null
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, GdkPixbuf
PY
    then
        printf '%s\n' "${RED}error:${RESET} the Python bindings for GTK 4 and libadwaita are missing." >&2
        printf '%s\n' "Install them first, for example:" >&2
        printf '%s\n' "  Debian/Ubuntu:  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gdkpixbuf-2.0" >&2
        printf '%s\n' "  Fedora:         sudo dnf install python3-gobject gtk4 libadwaita" >&2
        printf '%s\n' "  Arch:           sudo pacman -S python-gobject gtk4 libadwaita" >&2
        exit 1
    fi
}

free_super_v() {
    [[ $KEEP_SUPER_V -eq 0 ]] || { note "keeping the notification shortcut on Super+V (--keep-super-v)"; return; }
    gsettings describe "$TRAY_SCHEMA" "$TRAY_KEY" >/dev/null 2>&1 || { warn "$TRAY_KEY not found; Super+V may still open the notification list"; return; }

    if list_contains "$TRAY_SCHEMA" "$TRAY_KEY" "$SUPER_V"; then
        mkdir -p "$DATA_DIR"
        chmod 700 "$DATA_DIR"
        [[ -f "$BACKUP_FILE" ]] || gsettings get "$TRAY_SCHEMA" "$TRAY_KEY" > "$BACKUP_FILE"
        edit_list "$TRAY_SCHEMA" "$TRAY_KEY" remove "$SUPER_V"
        note "Super+V no longer opens the GNOME notification list (it is still on Super+M)"
    else
        note "Super+V is already free"
    fi
}

# The project was first called Clipstory: move an earlier installation over to the new names.
migrate_legacy() {
    if [[ -d "$LEGACY_EXT_DIR" ]]; then
        rm -rf "$LEGACY_EXT_DIR"
        note "removed the old Clipstory extension"
    fi
    if list_contains org.gnome.shell enabled-extensions "$LEGACY_UUID"; then
        edit_list org.gnome.shell enabled-extensions remove "$LEGACY_UUID"
    fi
    if [[ -d "$LEGACY_DATA_DIR" && ! -e "$DATA_DIR" ]]; then
        mv "$LEGACY_DATA_DIR" "$DATA_DIR"
        note "moved your history from $LEGACY_DATA_DIR to $DATA_DIR"
    fi
}

do_install() {
    say "Checking requirements"
    check_requirements
    resolve_source

    migrate_legacy

    say "Installing the extension to $EXT_DIR"
    mkdir -p "$EXT_DIR"
    install -m 644 "$SOURCE_DIR/extension.js" "$SOURCE_DIR/metadata.json" "$EXT_DIR/"
    install -m 755 "$SOURCE_DIR/main.py" "$EXT_DIR/"
    mkdir -p "$EXT_DIR/icons"
    install -m 644 "$SOURCE_DIR"/icons/*.svg "$EXT_DIR/icons/"
    install_launcher

    say "Enabling the extension"
    edit_list org.gnome.shell enabled-extensions add "$UUID"

    say "Setting up the shortcut"
    free_super_v

    say "Installed."
    cat <<EOF

${BOLD}Last step:${RESET} log out and back in. On Wayland GNOME loads new extensions only at login.
Then copy something and press ${BOLD}Super+V${RESET}.

  Update:     run this installer again.
  Uninstall:  ./install.sh --uninstall   (add --purge to delete the history too)
EOF
}

case "$MODE" in
    install)   do_install ;;
    uninstall) do_uninstall ;;
esac
