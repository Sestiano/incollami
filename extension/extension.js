// Copyright (C) 2026 Sebastiano Franchini
// SPDX-License-Identifier: GPL-3.0-or-later

import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

const DATA_DIR = GLib.get_home_dir() + '/.local/share/incollami';
const HISTORY_PATH = DATA_DIR + '/history.json';
const CURRENT_PATH = DATA_DIR + '/current';
const IMAGES_DIR = DATA_DIR + '/images';
const THUMBS_DIR = DATA_DIR + '/thumbs';
const APP_ID = 'io.github.sestiano.Incollami';
const MAX_HISTORY = 50;
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const PRIVATE_DIR_MODE = 0o700;

function itemKey(item) {
    return item.image !== undefined ? `image:${item.image}` : `text:${item.text}`;
}

export default class IncollamiExtension {
    constructor(metadata) {
        this._metadata = metadata;
        this._selection = null;
        this._ownerChangedId = null;
        this._actionId = Meta.KeyBindingAction.NONE;
        this._handlerId = 0;
        this._indicator = null;
        this._mapId = 0;
        this._mapTimeoutId = 0;
    }

    enable() {
        // Clipboard monitoring
        this._selection = global.display.get_selection();
        this._ownerChangedId = this._selection.connect('owner-changed', (selectionObj, selectionType) => {
            if (selectionType === Meta.SelectionType.SELECTION_CLIPBOARD) {
                this._onClipboardChanged();
            }
        });

        // Shortcut Super+V
        this._actionId = global.display.grab_accelerator('<Super>v', Meta.KeyBindingFlags.NONE);
        if (this._actionId !== Meta.KeyBindingAction.NONE) {
            const name = Meta.external_binding_name_for_action(this._actionId);
            Main.wm.allowKeybinding(name, Shell.ActionMode.ALL);

            this._handlerId = global.display.connect('accelerator-activated', (display, action) => {
                if (action === this._actionId) {
                    this._openUI();
                }
            });
        }

        // Top Panel Indicator
        this._indicator = new PanelMenu.Button(0.0, 'Incollami', true);
        const iconFile = Gio.File.new_for_path(
            GLib.build_filenamev([this._metadata.path, 'icons', 'incollami-symbolic.svg']));
        const icon = new St.Icon({
            gicon: iconFile.query_exists(null)
                ? new Gio.FileIcon({ file: iconFile })
                : new Gio.ThemedIcon({ name: 'edit-paste-symbolic' }),
            style_class: 'system-status-icon',
        });
        this._indicator.add_child(icon);

        // Open UI when indicator is clicked
        this._indicator.connect('button-press-event', (actor, event) => {
            const button = event.get_button();
            if (button === Clutter.BUTTON_PRIMARY) {
                this._openUI();
                return Clutter.EVENT_STOP;
            } else if (button === Clutter.BUTTON_SECONDARY) {
                this._openSettings();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        Main.panel.addToStatusArea('incollami', this._indicator);
    }

    disable() {
        this._stopWaitingForWindow();

        if (this._ownerChangedId && this._selection) {
            this._selection.disconnect(this._ownerChangedId);
            this._ownerChangedId = null;
        }

        if (this._handlerId) {
            global.display.disconnect(this._handlerId);
            this._handlerId = 0;
        }

        if (this._actionId !== Meta.KeyBindingAction.NONE) {
            global.display.ungrab_accelerator(this._actionId);
            this._actionId = Meta.KeyBindingAction.NONE;
        }

        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }

    _onClipboardChanged() {
        const mimeTypes = this._selection.get_mimetypes(Meta.SelectionType.SELECTION_CLIPBOARD);
        const clipboard = St.Clipboard.get_default();

        // Treat the content as an image only when no plain text is offered.
        const hasText = mimeTypes.some(type => type.startsWith('text/plain'));
        if (mimeTypes.includes('image/png') && !hasText) {
            clipboard.get_content(St.ClipboardType.CLIPBOARD, 'image/png', (clip, bytes) => {
                if (bytes && bytes.get_size() > 0 && bytes.get_size() <= MAX_IMAGE_BYTES) {
                    this._saveImageToHistory(bytes);
                }
            });
            return;
        }

        clipboard.get_text(St.ClipboardType.CLIPBOARD, (clip, text) => {
            if (text && text.trim().length > 0) {
                this._saveToHistory({ text });
            }
        });
    }

    _saveImageToHistory(bytes) {
        const name = `${GLib.compute_checksum_for_bytes(GLib.ChecksumType.SHA256, bytes)}.png`;
        try {
            GLib.mkdir_with_parents(IMAGES_DIR, PRIVATE_DIR_MODE);
            const file = Gio.File.new_for_path(`${IMAGES_DIR}/${name}`);
            if (!file.query_exists(null)) {
                file.replace_contents(bytes.get_data(), null, false, Gio.FileCreateFlags.PRIVATE, null);
            }
        } catch (e) {
            console.error(`Incollami: Error writing image: ${e}`);
            return;
        }
        this._saveToHistory({ image: name });
    }

    _loadHistory() {
        try {
            const file = Gio.File.new_for_path(HISTORY_PATH);
            if (file.query_exists(null)) {
                const [, contents] = file.load_contents(null);
                const decoder = new TextDecoder('utf-8');
                return JSON.parse(decoder.decode(contents));
            }
        } catch (e) {
            console.error(`Incollami: Error reading history: ${e}`);
        }
        return [];
    }

    // Record which entry is now in the clipboard so that the window can mark it.
    _writeCurrent(key) {
        try {
            const digest = GLib.compute_checksum_for_string(GLib.ChecksumType.SHA256, key, -1);
            const bytes = new GLib.Bytes(digest);
            Gio.File.new_for_path(CURRENT_PATH).replace_contents(
                bytes.get_data(), null, false,
                Gio.FileCreateFlags.REPLACE_DESTINATION | Gio.FileCreateFlags.PRIVATE, null);
        } catch (e) {
            console.error(`Incollami: Error writing current entry: ${e}`);
        }
    }

    _saveToHistory(newItem) {
        GLib.mkdir_with_parents(DATA_DIR, PRIVATE_DIR_MODE);
        this._writeCurrent(itemKey(newItem));
        let history = this._loadHistory();

        const newKey = itemKey(newItem);
        const existingIndex = history.findIndex(h => itemKey(h) === newKey);
        if (existingIndex !== -1) {
            if (existingIndex === history.length - 1) {
                return;
            }
            if (history[existingIndex].pinned) {
                return;
            }
            const item = history.splice(existingIndex, 1)[0];
            history.push(item);
        } else {
            history.push(newItem);
        }

        if (history.length > MAX_HISTORY) {
            const pinnedCount = history.filter(h => h.pinned).length;
            let unpinnedToKeep = Math.max(0, MAX_HISTORY - pinnedCount);
            const itemsToKeep = [];
            for (let i = history.length - 1; i >= 0; i--) {
                const item = history[i];
                if (item.pinned) {
                    itemsToKeep.unshift(item);
                } else if (unpinnedToKeep > 0) {
                    itemsToKeep.unshift(item);
                    unpinnedToKeep--;
                }
            }
            history = itemsToKeep;
        }

        try {
            const file = Gio.File.new_for_path(HISTORY_PATH);
            const contentBytes = new GLib.Bytes(JSON.stringify(history));
            file.replace_contents(
                contentBytes.get_data(), null, false,
                Gio.FileCreateFlags.REPLACE_DESTINATION | Gio.FileCreateFlags.PRIVATE, null);
        } catch (e) {
            console.error(`Incollami: Error writing history: ${e}`);
            return;
        }

        this._removeUnreferencedImages(history);
    }

    // Delete stored images and thumbnails that no history entry refers to.
    _removeUnreferencedImages(history) {
        const referenced = new Set(history.filter(h => h.image !== undefined).map(h => h.image));
        for (const dir of [IMAGES_DIR, THUMBS_DIR]) {
            const folder = Gio.File.new_for_path(dir);
            if (!folder.query_exists(null)) {
                continue;
            }
            try {
                const enumerator = folder.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
                let info;
                while ((info = enumerator.next_file(null)) !== null) {
                    if (!referenced.has(info.get_name())) {
                        folder.get_child(info.get_name()).delete(null);
                    }
                }
                enumerator.close(null);
            } catch (e) {
                console.error(`Incollami: Error cleaning ${dir}: ${e}`);
            }
        }
    }

    // With focus-follows-mouse a new window only receives keyboard focus when the pointer is
    // over it, so activate the window of the application that this extension has just launched.
    _focusLaunchedWindow() {
        this._stopWaitingForWindow();
        this._mapId = global.window_manager.connect('map', (wm, actor) => {
            const window = actor.meta_window;
            if (window.get_gtk_application_id() !== APP_ID) {
                return;
            }
            this._stopWaitingForWindow();
            Main.activateWindow(window);
        });
        this._mapTimeoutId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            this._mapTimeoutId = 0;
            this._stopWaitingForWindow();
            return GLib.SOURCE_REMOVE;
        });
    }

    _stopWaitingForWindow() {
        if (this._mapId) {
            global.window_manager.disconnect(this._mapId);
            this._mapId = 0;
        }
        if (this._mapTimeoutId) {
            GLib.source_remove(this._mapTimeoutId);
            this._mapTimeoutId = 0;
        }
    }

    _openUI() {
        try {
            this._focusLaunchedWindow();
            const path = GLib.build_filenamev([this._metadata.path, 'main.py']);
            Gio.Subprocess.new(
                ['/usr/bin/python3', path],
                Gio.SubprocessFlags.NONE
            );
        } catch (e) {
            console.error(`Incollami: Failed to launch UI: ${e}`);
        }
    }

    _openSettings() {
        try {
            this._focusLaunchedWindow();
            const path = GLib.build_filenamev([this._metadata.path, 'main.py']);
            Gio.Subprocess.new(
                ['/usr/bin/python3', path, '--settings'],
                Gio.SubprocessFlags.NONE
            );
        } catch (e) {
            console.error(`Incollami: Failed to launch Settings: ${e}`);
        }
    }
}
