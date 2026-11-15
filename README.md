# sticky-md

Sticky notes that are an Obsidian vault. Always on top. Built for fast capture.

Notes = plain `.md` in `~/StickyMD`. Open that folder in Obsidian, same notes. Edit in either, they sync live.

Run: `pythonw stickies.py`. Python stdlib only, Windows.

## fast
- `Ctrl+Alt+N` anywhere: new note at your mouse, cursor ready. Type.
- `Ctrl+Alt+S` anywhere: hide / show all notes
- select text = auto copied (settings can turn off)
- untitled notes name themselves from first line on close
- `Ctrl+L`: list + search, `Enter` opens top hit

## novel bit
Notes that link to each other get arrows drawn between them on your desktop. Links become a map.

## obsidian stuff
- live preview: `**`, `#`, `[[` hide unless cursor is on that line
- `[[wikilinks]]`: Ctrl+click opens note, makes it if missing
- backlinks (`↩ n` button), `#tags`, daily note (📅)
- rename (double-click title) updates `[[links]]` everywhere
- checklists you can click, bullet continue on Enter

## other
- pin = always on top, put down = normal window
- colors, dark/light, font size, opacity in settings
- in note: Ctrl+B, Ctrl+I, Ctrl+N, Ctrl+W

Test: `pytest`
