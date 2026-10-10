# How Incollami works

Incollami is two small programs that share a folder of files.

```
 GNOME Shell                                   your session
┌───────────────────────────────┐             ┌──────────────────────────────┐
│ extension.js  (always running)│  writes     │ ~/.local/share/incollami/    │
│  - watches the clipboard      │ ──────────▶ │   history.json  images/ ...  │
│  - owns the Super+V shortcut  │             └──────────────────────────────┘
│  - shows the top-bar icon     │                       ▲  reads / edits
│  - starts main.py             │ ── launches ──▶ ┌─────┴────────────────────┐
└───────────────────────────────┘                 │ main.py (GTK 4 / Adw)    │
                                                  │  - the window you see    │
                                                  │  - search, pin, delete   │
                                                  │  - puts the entry back   │
                                                  │    in the clipboard      │
                                                  └──────────────────────────┘
```

## Why two programs

Only code running inside GNOME Shell can observe the clipboard on Wayland while no window has the
focus, and it can own a global shortcut. That is the **extension**. But drawing a modern window with
libadwaita from inside the shell is awkward and ties the look to the shell's own toolkit. So the
window is a normal GTK 4 application, **`main.py`**, that the extension starts each time you press
`Super + V` and that quits when it loses focus. It opens quickly: importing GTK and libadwaita alone
takes about a tenth of a second.

## The extension (`extension.js`)

- **Watching the clipboard.** It listens for the clipboard owner changing.
  - If the new content offers `image/png` and no plain text, it is stored as an image (up to 20 MB).
    The file name is the SHA-256 of the bytes, so copying the same image twice makes one entry.
  - Otherwise the text is read and stored.
  - Entries are unique; copying an existing one moves it to the end. Pinned entries do not move.
  - The history is trimmed to 50 entries, always keeping pinned ones. Images that no longer belong to
    any entry are deleted together with their previews.
- **The current entry.** Every time the clipboard changes it writes a SHA-256 of the entry's identity
  to the `current` file. The window compares it with each row to draw the coloured dot.
- **The shortcut.** It grabs `Super + V`. The installer also removes `Super + V` from GNOME's own
  `toggle-message-tray` shortcut, otherwise the two would compete.
- **Focus.** GNOME can be set to "focus follows mouse", and in that mode a new window only receives
  the keyboard if the pointer is over it. After launching `main.py` the extension waits for its window
  and activates it explicitly (matching the application id `io.github.sestiano.Incollami`).
- **The icon.** `icons/incollami-symbolic.svg` is a symbolic icon (filled shapes only, so the shell can
  recolour it). Left click opens the history, right click opens the settings.
- **Writes are private and atomic.** Files are created with mode `600` in a folder with mode `700`,
  and replaced with a temporary file, so a crash cannot leave a half-written history.

## The window (`main.py`)

- A `Gtk.SearchEntry` keeps the keyboard focus the whole time, so typing always searches. The list
  rows are not focusable; arrow keys move the selection programmatically. One key handler on the
  window (capture phase) implements all the shortcuts.
- Rows are built from the history: text is shown on up to two lines, images as a rounded preview with
  the pixel size and file size. The previews are cover-cropped tiles stored at twice the displayed size
  in `thumbs/`, created the first time they are needed.
- Choosing an entry sets the clipboard (`Gdk.ContentProvider` with the text, or the PNG bytes) and
  hides the window at once. The process stays alive for 500 ms so the system has time to take the
  clipboard content over, then exits.
- Pin state and order live in `history.json` (`pinned`, `pin_order`). Moving a pinned entry swaps the
  order of two neighbours.
- The window and the settings follow the GNOME colour scheme (or a fixed light or dark choice) and the
  accent colour, through libadwaita's named colours.

## The glass look

A GTK application cannot ask GNOME to blur what is behind it, so the glass is simulated with CSS only:

1. A vertical gradient of cool greys with 90 to 93 % opacity, so the desktop shows through a little.
2. A soft circular highlight in the top-left corner and a fainter one at the bottom-right, plus a
   diagonal sheen, like light on a pane.
3. Inner shadows: a bright 1.5 px line on the top edge, a thin rim, and a darker band at the bottom,
   which give the pane thickness.
4. A very faint blue veil that cancels the warm cast of a typical wallpaper.
5. A fine noise tile (`grain.png`, `grain-light.png`) for a frosted texture. The tiles are generated on
   first run; delete them to regenerate.

The values are in the `GLASS_CSS` string at the top of `main.py`.

## Files

| File | Purpose |
|---|---|
| `extension/extension.js` | Shell part: clipboard watcher, shortcut, icon, launches the window |
| `extension/main.py` | The history window and the settings window |
| `extension/metadata.json` | Extension description, id and supported GNOME versions |
| `extension/icons/incollami-symbolic.svg` | Top-bar icon |
| `install.sh` | Per-user installer and uninstaller |

## Data format

`history.json` is a list, oldest first:

```json
[
  { "text": "some copied text" },
  { "image": "3f2a…c1.png" },
  { "text": "a pinned note", "pinned": true, "pin_order": 1 }
]
```

## Ideas that are not done

- Pasting automatically after choosing an entry.
- Ignoring entries that a password manager marks as sensitive.
- A real blurred background, which would have to be applied by the extension to the window's actor.
