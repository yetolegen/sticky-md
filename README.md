# sticky-md

![type [[Ideas]] in one note, an arrow draws to the Ideas note](docs/demo.png)

Sticky notes that are an Obsidian vault. Always on top. Paste anything, it looks like it did where you copied it.

Notes = plain `.md` in `~/StickyMD`. Open that folder in Obsidian, same notes. Edit in either, they sync live.

Run: `pythonw stickies.py`. Windows. Needs Python 3 + `matplotlib` for LaTeX (optional, Pillow for jpg).

## paste = looks like the source
- copy from web, Word, Excel, paste: headings, bold, lists, links, tables come over
- no `##`, `**`, `|---|` on screen: real headings, real table grid, real rule line
- `[text](url)` shows just the link. bare `https://...` is a link. click opens it
- raw syntax only when you want it: `Ctrl+E` (or Settings: reveal on edit line)
- the file stays clean markdown

## fast
- `Ctrl+Alt+N` anywhere: new note at your mouse, cursor ready. Type.
- `Ctrl+Alt+S` anywhere: hide / show all notes. `Ctrl+Alt+L`: notes list
- select text = auto copied (settings can turn off)
- untitled notes name themselves from first line on close
- search: words, `#tag`, `tag:x`, `title:x`, `-word`

## novel bit
Notes that link to each other get arrows drawn between them on your desktop. Links become a map. Graph view (◎) too.

## obsidian stuff
- `[[wikilinks]]` (click opens, makes it if missing), `[[note#heading]]`, `[[` autocomplete
- backlinks (`↩ n`), `#tags`, daily note (📅)
- rename like Windows: double-click the title (or F2), type, Enter. no dialog. links update everywhere
- select text: floating pill with bold, italic, strike, highlight, `[[link]]`, copy
- callouts `> [!tip]`, code blocks, quotes, numbered + checklists, `==highlight==`, frontmatter
- `$LaTeX$` and `$$...$$`: formula shows rendered while cursor is in it
- `![[pic.png]]` / `![alt](pic.png)`: click opens image
- fonts, 4 themes, colors, opacity in settings

## other
- pin = always on top, put down = normal window
- `—` collapses note to its title bar (Ctrl+M)
- in note: Ctrl+B, Ctrl+I, Ctrl+N, Ctrl+W, Ctrl+E

Not here: plugins, canvas, inline images, real LaTeX inside the text flow.

Test: `pytest`
