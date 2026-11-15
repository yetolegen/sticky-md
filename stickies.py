import ctypes
import json
import os
import re
import sys
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import messagebox, simpledialog

DIR = Path.home() / "StickyMD"
STATE = DIR / "state.json"
STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/StickyMD.vbs"
FONT = "Segoe UI"
KEY = "#ff00fe"
MOD, WM_HOTKEY, PM_REMOVE = 3, 0x312, 1
BAD = r'[\\/:*?"<>|]'
COLORS = {
    "yellow": ("#e6b800", "#fff6bf"),
    "green": ("#5fb84a", "#d3efca"),
    "pink": ("#e0679d", "#fad5e5"),
    "purple": ("#9577d6", "#e4dbf6"),
    "blue": ("#3f9fe0", "#d1e9fa"),
    "gray": ("#8c8c8c", "#e6e6e6"),
    "charcoal": ("#555555", "#c9c9c9"),
}
THEMES = {
    "dark": dict(bg="#202020", body="#2d2d2d", card="#383838", fg="#f2f2f2", muted="#9a9a9a", code="#4a4a4a",
                 link="#6cb6ff", tag="#d9a0ff", edge="#0f0f0f"),
    "light": dict(bg="#f3f3f3", body=None, card="#ffffff", fg="#1f1f1f", muted="#666666", code="#d6d6d6",
                  link="#0645ad", tag="#7a3fb0", edge="#b5b5b5"),
}
DEFAULTS = {"theme": "dark", "color": "yellow", "size": 11, "alpha": 100, "pinned": True, "lines": True, "autocopy": True, "autostart": False}
PATTERNS = [
    ("h1", r"^# .*$"),
    ("h2", r"^## .*$"),
    ("h3", r"^#{3,6} .*$"),
    ("bold", r"\*\*.+?\*\*"),
    ("it", r"(?<!\*)\*(?!\*)[^*\n]+?\*(?!\*)"),
    ("strike", r"~~.+?~~"),
    ("code", r"`[^`\n]+`"),
    ("done", r"^- \[x\] .*$"),
    ("link", r"\[\[.+?\]\]"),
    ("tag", r"(?<![\w#&])#[A-Za-z][\w/-]*"),
]
LINK = re.compile(r"\[\[([^\]|#\n]+)(?:#[^\]|\n]*)?(?:\|[^\]\n]*)?\]\]")


def spans(text):
    return [(tag, m.start(), m.end()) for tag, p in PATTERNS for m in re.finditer(p, text, re.M)]


def marks(text):
    out = []
    for tag, a, b in spans(text):
        if tag in ("h1", "h2", "h3"):
            out.append((a, a + re.match(r"#+ ", text[a:b]).end()))
        elif tag in ("bold", "strike", "link"):
            out += [(a, a + 2), (b - 2, b)]
        elif tag in ("it", "code"):
            out += [(a, a + 1), (b - 1, b)]
    return out


def links_of(text):
    return {m.group(1).strip().lower() for m in LINK.finditer(text)}


def link_at(text, off):
    for m in LINK.finditer(text):
        if m.start() <= off < m.end():
            return m.group(1).strip()


def offset(text, idx):
    line, col = map(int, idx.split("."))
    return sum(len(x) + 1 for x in text.split("\n")[:line - 1]) + col


def next_prefix(line):
    m = re.match(r"^\s*(- \[[ x]\] |- )", line)
    return m.group(0).replace("[x]", "[ ]") if m else None


def title_of(text):
    for line in text.splitlines():
        t = re.sub(r"^[#>\- ]+(\[[ x]\] )?", "", line).strip()
        if t:
            return re.sub(BAD, "", t)[:40].strip(" .")
    return ""


def ink(color):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#111111" if r + g + b > 380 else "#ffffff"


def tint(color, k=0.14):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    t = 0 if r + g + b > 380 else 255
    return "#%02x%02x%02x" % tuple(round(c + (t - c) * k) for c in (r, g, b))


def hover(w, bg=None, fg=None):
    def on(e):
        w._c = (w.cget("bg"), w.cget("fg"))
        w.config(bg=bg or tint(w._c[0]), fg=fg or w._c[1])

    def off(e):
        w.config(bg=w._c[0], fg=w._c[1])

    w.bind("<Enter>", on)
    w.bind("<Leave>", off)


def tip(w, text):
    box = {}

    def show():
        t = box["t"] = tk.Toplevel(w)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        tk.Label(t, text=text, bg="#2b2b2b", fg="#f2f2f2", font=(FONT, 9), padx=6, pady=3).pack()
        t.geometry(f"+{w.winfo_rootx()}+{w.winfo_rooty() + w.winfo_height() + 4}")

    def hide(e=None):
        if "j" in box:
            w.after_cancel(box.pop("j"))
        if "t" in box:
            box.pop("t").destroy()

    w.bind("<Enter>", lambda e: box.update(j=w.after(500, show)), add="+")
    w.bind("<Leave>", hide, add="+")
    w.bind("<Button-1>", hide, add="+")


class Note:
    def __init__(self, app, path, info):
        self.app, self.path = app, path
        self.pinned = info.get("pinned", app.cfg["pinned"])
        self.color = info.get("color", app.cfg["color"])
        self.mtime = path.stat().st_mtime_ns if path.exists() else 0
        self.win = w = tk.Toplevel(app.root)
        w.overrideredirect(True)
        w.geometry(info.get("geo", "300x340+120+120"))
        w.attributes("-topmost", self.pinned)
        w.config(highlightthickness=1)
        self.bar = bar = tk.Frame(w, cursor="fleur")
        bar.pack(fill="x")
        bar.bind("<ButtonPress-1>", self.grab)
        bar.bind("<B1-Motion>", self.drag)
        self.btns = [
            self.button(bar, "+", "left", lambda e: app.new(), "New note (Ctrl+N)"),
            self.button(bar, "", "left", self.toggle_pin, "Keep on top / put down"),
            self.button(bar, "✕", "right", self.close, "Close (Ctrl+W)", True),
            self.button(bar, "⋯", "right", self.menu, "Menu"),
        ]
        self.pin = self.btns[1]
        self.title = tk.Label(bar, font=(FONT, 9), anchor="w", padx=6)
        self.title.pack(side="left", fill="x", expand=True)
        self.title.bind("<ButtonPress-1>", self.grab)
        self.title.bind("<B1-Motion>", self.drag)
        self.title.bind("<Double-Button-1>", self.rename)
        tip(self.title, "Drag to move, double-click to rename")
        self.tools = tk.Frame(w)
        self.tools.pack(side="bottom", fill="x")
        self.tl = []
        for label, style, cmd, hint in (
            ("B", "bold", lambda: self.wrap("**"), "Bold (Ctrl+B)"),
            ("I", "italic", lambda: self.wrap("*"), "Italic (Ctrl+I)"),
            ("S", "overstrike", lambda: self.wrap("~~"), "Strikethrough"),
            ("•", "", lambda: self.prefix("- "), "Bullet list"),
            ("☐", "", lambda: self.prefix("- [ ] "), "Checklist"),
        ):
            b = tk.Label(self.tools, text=label, font=(FONT, 11) + ((style,) if style else ()), padx=12, pady=6, cursor="hand2")
            b.pack(side="left")
            hover(b)
            tip(b, hint)
            b.bind("<Button-1>", lambda e, c=cmd: c(), add="+")
            self.tl.append(b)
        self.bl = tk.Label(self.tools, text="↩ 0", font=(FONT, 10), padx=10, pady=6, cursor="hand2")
        self.bl.pack(side="right", padx=(0, 22))
        hover(self.bl)
        tip(self.bl, "Backlinks")
        self.bl.bind("<Button-1>", self.back, add="+")
        self.tl.append(self.bl)
        self.msg = tk.Label(self.tools, font=(FONT, 9), padx=6)
        self.msg.pack(side="left")
        self.text = t = tk.Text(w, bd=0, wrap="word", undo=True, padx=14, pady=10, spacing1=2, spacing3=2, highlightthickness=0)
        t.pack(fill="both", expand=True)
        t.insert("1.0", path.read_text(encoding="utf-8-sig") if path.exists() else "# ")
        t.edit_reset()
        t.edit_modified(False)
        t.bind("<<Modified>>", self.changed)
        t.bind("<Button-1>", self.click)
        t.bind("<Control-Button-1>", self.follow)
        t.bind("<Return>", self.enter)
        t.bind("<KeyRelease>", lambda e: self.style())
        t.bind("<ButtonRelease-1>", self.released)
        for key, fn in (("b", lambda: self.wrap("**")), ("i", lambda: self.wrap("*")), ("n", app.new),
                        ("w", self.close), ("l", app.hub.show)):
            t.bind(f"<Control-{key}>", lambda e, f=fn: (f(), "break")[1])
        self.grip = tk.Label(w, text="◢", font=(FONT, 12), padx=4, cursor="size_nw_se")
        self.grip.place(relx=1, rely=1, anchor="se")
        tip(self.grip, "Resize")
        self.grip.bind("<B1-Motion>", self.resize)
        self.apply()
        self.paint_title()

    def button(self, bar, label, side, cmd, hint, close=False):
        b = tk.Label(bar, text=label, font=(FONT, 12), padx=11, pady=4, cursor="hand2")
        b.pack(side=side)
        if close:
            hover(b, "#c42b1c", "#ffffff")
        else:
            hover(b)
        tip(b, hint)
        b.bind("<Button-1>", cmd, add="+")
        return b

    def apply(self):
        cfg = self.app.cfg
        th = THEMES[cfg["theme"]]
        head, light = COLORS[self.color]
        body, s = th["body"] or light, cfg["size"]
        fg = th["fg"]
        self.win.attributes("-alpha", cfg["alpha"] / 100)
        self.win.config(bg=body, highlightbackground=th["edge"])
        self.bar.config(bg=head)
        self.title.config(bg=head, fg=ink(head))
        for b in self.btns:
            b.config(bg=head, fg=ink(head))
        self.tools.config(bg=body)
        for b in self.tl:
            b.config(bg=body, fg=fg)
        self.grip.config(bg=body, fg=th["muted"])
        self.msg.config(bg=body, fg=th["muted"])
        t = self.text
        t.config(bg=body, fg=fg, insertbackground=fg, font=(FONT, s))
        t.tag_configure("h1", font=(FONT, s + 6, "bold"))
        t.tag_configure("h2", font=(FONT, s + 3, "bold"))
        t.tag_configure("h3", font=(FONT, s + 1, "bold"))
        t.tag_configure("bold", font=(FONT, s, "bold"))
        t.tag_configure("it", font=(FONT, s, "italic"))
        t.tag_configure("strike", overstrike=True)
        t.tag_configure("code", font=("Consolas", s - 1), background=th["code"])
        t.tag_configure("done", overstrike=True, foreground=th["muted"])
        t.tag_configure("link", foreground=th["link"], underline=True)
        t.tag_configure("tag", foreground=th["tag"])
        t.tag_configure("hide", elide=True)
        self.paint_pin()
        self.style()

    def paint_title(self):
        s = self.path.stem
        self.title.config(text=s if len(s) < 24 else s[:23] + "…")

    def paint_back(self):
        self.bl.config(text=f"↩ {len(self.app.backlinks(self.path.stem))}")

    def grab(self, e):
        self.dx, self.dy = e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y()

    def drag(self, e):
        self.win.geometry(f"+{e.x_root - self.dx}+{e.y_root - self.dy}")

    def resize(self, e):
        w = max(200, e.x_root - self.win.winfo_rootx())
        h = max(140, e.y_root - self.win.winfo_rooty())
        self.win.geometry(f"{w}x{h}")

    def paint_pin(self):
        self.pin.config(text="📌" if self.pinned else "⇩")

    def toggle_pin(self, e=None):
        self.pinned = not self.pinned
        self.win.attributes("-topmost", self.pinned)
        self.paint_pin()

    def set_color(self, name):
        self.color = name
        self.apply()

    def menu(self, e):
        m = tk.Menu(self.win, tearoff=0)
        cm = tk.Menu(m, tearoff=0)
        for name in COLORS:
            cm.add_command(label=name, command=lambda n=name: self.set_color(n))
        m.add_cascade(label="Color", menu=cm)
        m.add_command(label="Rename", command=self.rename)
        m.add_command(label="Today's note", command=self.app.today)
        m.add_command(label="Notes list", command=self.app.hub.show)
        m.add_command(label="Settings", command=self.app.show_settings)
        m.add_separator()
        m.add_command(label="Delete note", command=self.delete)
        m.tk_popup(e.x_root, e.y_root)

    def back(self, e):
        m = tk.Menu(self.win, tearoff=0)
        found = self.app.backlinks(self.path.stem)
        for p in found:
            m.add_command(label=p.stem, command=lambda p=p: self.app.open_note(p, self))
        if not found:
            m.add_command(label="No backlinks", state="disabled")
        m.tk_popup(e.x_root, e.y_root)

    def rename(self, e=None):
        name = simpledialog.askstring("Rename", "Name:", initialvalue=self.path.stem, parent=self.win)
        if name:
            self.app.rename(self, name)

    def wrap(self, mark):
        t = self.text
        if t.tag_ranges("sel"):
            a, b = t.index("sel.first"), t.index("sel.last")
            t.insert(b, mark)
            t.insert(a, mark)
        else:
            t.insert("insert", mark * 2)
            t.mark_set("insert", f"insert-{len(mark)}c")
        t.focus_force()

    def prefix(self, p):
        self.text.insert("insert linestart", p)
        self.text.focus_force()

    def click(self, e):
        t = self.text
        t.focus_force()
        line, col = map(int, t.index(f"@{e.x},{e.y}").split("."))
        m = re.match(r"- \[([ x])\] ", t.get(f"{line}.0", f"{line}.end"))
        if m and 2 <= col <= 4:
            t.replace(f"{line}.3", f"{line}.4", " " if m.group(1) == "x" else "x")
            return "break"

    def follow(self, e):
        t = self.text
        body = t.get("1.0", "end-1c")
        name = link_at(body, offset(body, t.index(f"@{e.x},{e.y}")))
        if name:
            self.app.open_link(name, self)
        return "break"

    def enter(self, e):
        t = self.text
        line = t.get("insert linestart", "insert")
        p = next_prefix(line)
        if p is None:
            return None
        if line.strip() in ("-", "- [ ]", "- [x]"):
            t.delete("insert linestart", "insert")
        else:
            t.insert("insert", "\n" + p)
        return "break"

    def released(self, e):
        self.style()
        t = self.text
        if self.app.cfg["autocopy"] and t.tag_ranges("sel"):
            t.clipboard_clear()
            t.clipboard_append(t.get("sel.first", "sel.last"))
            self.flash("copied")

    def flash(self, text):
        self.msg.config(text=text)
        self.win.after(1200, lambda: self.msg.winfo_exists() and self.msg.config(text=""))

    def autoname(self):
        title = title_of(self.text.get("1.0", "end-1c"))
        if self.path.stem.startswith("Untitled") and self.path.exists() and title and not (DIR / f"{title}.md").exists():
            self.app.rename(self, title)

    def style(self):
        t = self.text
        body = t.get("1.0", "end-1c")
        for tag, _ in PATTERNS:
            t.tag_remove(tag, "1.0", "end")
        t.tag_remove("hide", "1.0", "end")
        for tag, a, b in spans(body):
            t.tag_add(tag, f"1.0+{a}c", f"1.0+{b}c")
        cur = int(t.index("insert").split(".")[0])
        for a, b in marks(body):
            if body.count("\n", 0, a) + 1 != cur:
                t.tag_add("hide", f"1.0+{a}c", f"1.0+{b}c")

    def changed(self, _):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.style()
        self.path.write_text(self.text.get("1.0", "end-1c"), encoding="utf-8")
        self.mtime = self.path.stat().st_mtime_ns
        self.app.hub.refresh()

    def reload(self):
        new = self.path.read_text(encoding="utf-8-sig")
        t = self.text
        if new != t.get("1.0", "end-1c"):
            at = t.index("insert")
            t.delete("1.0", "end")
            t.insert("1.0", new)
            t.mark_set("insert", at)
            t.edit_modified(False)
            self.style()
        self.mtime = self.path.stat().st_mtime_ns

    def poll(self):
        if self.path.exists() and self.path.stat().st_mtime_ns != self.mtime:
            self.reload()
        self.paint_back()

    def info(self):
        return {"geo": self.win.geometry(), "pinned": self.pinned, "color": self.color}

    def close(self, e=None):
        self.autoname()
        self.app.state[self.path.name] = {**self.info(), "closed": True}
        self.win.destroy()
        self.app.notes.remove(self)
        self.app.save()
        self.app.maybe_quit()

    def delete(self):
        if messagebox.askyesno("Delete", f"Delete {self.path.name}?", parent=self.win):
            self.path.unlink(missing_ok=True)
            self.app.state.pop(self.path.name, None)
            self.win.destroy()
            self.app.notes.remove(self)
            self.app.save()
            self.app.hub.refresh()
            self.app.maybe_quit()


class Hub:
    def __init__(self, app):
        self.app, self.job, self.found = app, None, []
        self.win = w = tk.Toplevel(app.root)
        w.title("Sticky Notes")
        w.geometry("360x560+60+60")
        w.protocol("WM_DELETE_WINDOW", self.hide)
        self.top = tk.Frame(w)
        self.top.pack(fill="x", padx=8, pady=(8, 0))
        self.plus = tk.Label(self.top, text="+", font=(FONT, 18), padx=10, cursor="hand2")
        self.plus.pack(side="left")
        hover(self.plus)
        tip(self.plus, "New note")
        self.plus.bind("<Button-1>", lambda e: app.new(), add="+")
        self.day = tk.Label(self.top, text="📅", font=(FONT, 14), padx=8, pady=4, cursor="hand2")
        self.day.pack(side="left")
        hover(self.day)
        tip(self.day, "Today's note")
        self.day.bind("<Button-1>", lambda e: app.today(), add="+")
        self.gear = tk.Label(self.top, text="⚙", font=(FONT, 16), padx=10, pady=4, cursor="hand2")
        self.gear.pack(side="right")
        hover(self.gear)
        tip(self.gear, "Settings")
        self.gear.bind("<Button-1>", lambda e: app.show_settings(), add="+")
        self.title = tk.Label(w, text="Sticky Notes", font=(FONT, 16, "bold"), anchor="w")
        self.title.pack(fill="x", padx=16, pady=(4, 8))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: (self.build(), self.sync()))
        self.search = tk.Entry(w, textvariable=self.q, relief="flat", font=(FONT, 11))
        self.search.pack(fill="x", padx=16, ipady=8)
        self.hint = tk.Label(self.search, text="Search notes or #tags", font=(FONT, 11))
        self.hint.bind("<Button-1>", lambda e: self.search.focus_set())
        self.search.bind("<FocusIn>", self.sync)
        self.search.bind("<FocusOut>", self.sync)
        self.search.bind("<Return>", lambda e: self.found and self.app.open_note(self.found[0]))
        self.sync()
        self.canvas = tk.Canvas(w, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=8)
        self.list = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.list, anchor="nw", tags="f")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig("f", width=e.width))
        self.list.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        w.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"))
        w.bind("<Escape>", lambda e: self.hide())
        self.apply()
        w.withdraw()

    def apply(self):
        th = THEMES[self.app.cfg["theme"]]
        self.win.config(bg=th["bg"])
        for f in (self.top, self.canvas, self.list):
            f.config(bg=th["bg"])
        for b in (self.plus, self.day, self.gear):
            b.config(bg=th["bg"], fg=th["muted"])
        self.title.config(bg=th["bg"], fg=th["fg"])
        self.search.config(bg=th["card"], fg=th["fg"], insertbackground=th["fg"])
        self.hint.config(bg=th["card"], fg=th["muted"])
        if self.win.state() != "withdrawn":
            self.build()

    def sync(self, e=None):
        if self.q.get() or self.win.focus_get() is self.search:
            self.hint.place_forget()
        else:
            self.hint.place(x=8, rely=0.5, anchor="w")

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.build()
        self.win.focus_force()
        self.search.focus_set()

    def hide(self):
        self.win.withdraw()
        self.app.maybe_quit()

    def refresh(self):
        if self.win.state() == "withdrawn":
            return
        if self.job:
            self.win.after_cancel(self.job)
        self.job = self.win.after(300, self.build)

    def build(self):
        self.job, self.found = None, []
        for c in self.list.winfo_children():
            c.destroy()
        q = self.q.get().lower()
        for p in sorted(DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            txt = p.read_text(encoding="utf-8-sig")
            if q in txt.lower():
                self.found.append(p)
                self.card(p, txt)
        if not self.list.winfo_children():
            th = THEMES[self.app.cfg["theme"]]
            tk.Label(self.list, text="No matches" if q else "No notes yet", bg=th["bg"], fg=th["muted"],
                     font=(FONT, 11)).pack(pady=40)

    def card(self, p, txt):
        th = THEMES[self.app.cfg["theme"]]
        head = COLORS[self.app.state.get(p.name, {}).get("color", self.app.cfg["color"])][0]
        f = tk.Frame(self.list, bg=th["card"], cursor="hand2")
        f.pack(fill="x", padx=16, pady=6)
        tk.Frame(f, bg=head, height=3).pack(fill="x")
        lt = time.localtime(p.stat().st_mtime)
        same = time.strftime("%Y%m%d", lt) == time.strftime("%Y%m%d")
        tk.Label(f, text=time.strftime("%I:%M %p" if same else "%b %d", lt), bg=th["card"], fg=th["muted"],
                 font=(FONT, 9), anchor="e").pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(f, text=p.stem, bg=th["card"], fg=th["fg"], font=(FONT, 12, "bold"),
                 anchor="w").pack(fill="x", padx=12)
        body = " ".join(txt.split()).lstrip("# ")
        if body.lower().startswith(p.stem.lower()):
            body = body[len(p.stem):].strip()
        tk.Label(f, text=body[:140] or "empty note", bg=th["card"], fg=th["muted"], font=(FONT, 10), wraplength=290,
                 justify="left", anchor="w").pack(fill="x", padx=12, pady=(2, 12))
        kids = f.winfo_children()[1:]

        def lit(e, on):
            at = str(f.winfo_containing(e.x_root, e.y_root))
            if not on and (at == str(f) or at.startswith(str(f) + ".")):
                return
            for w in [f, *kids]:
                w.config(bg=tint(th["card"]) if on else th["card"])

        for w in [f, *f.winfo_children()]:
            w.bind("<Button-1>", lambda e, p=p: self.app.open_note(p))
            w.bind("<Enter>", lambda e: lit(e, True))
            w.bind("<Leave>", lambda e: lit(e, False))


class Lines:
    def __init__(self, app):
        self.app = app
        u = ctypes.windll.user32
        self.ox, self.oy = u.GetSystemMetrics(76), u.GetSystemMetrics(77)
        self.win = w = tk.Toplevel(app.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-transparentcolor", KEY)
        w.geometry(f"{u.GetSystemMetrics(78)}x{u.GetSystemMetrics(79)}+{self.ox}+{self.oy}")
        self.c = tk.Canvas(w, bg=KEY, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        w.withdraw()
        self.tick()

    def reach(self, a, b):
        x, y, w, h = a.win.winfo_rootx(), a.win.winfo_rooty(), a.win.winfo_width(), a.win.winfo_height()
        dx = b.win.winfo_rootx() + b.win.winfo_width() / 2 - (x + w / 2)
        dy = b.win.winfo_rooty() + b.win.winfo_height() / 2 - (y + h / 2)
        s = min(w / 2 / abs(dx) if dx else 1e9, h / 2 / abs(dy) if dy else 1e9)
        return x + w / 2 + dx * s - self.ox, y + h / 2 + dy * s - self.oy, s

    def tick(self):
        app, segs = self.app, []
        if app.cfg["lines"]:
            by = {n.path.stem.lower(): n for n in app.notes if n.pinned and n.win.state() != "withdrawn"}
            for a in by.values():
                for t in app.graph.get(a.path.stem.lower(), ()):
                    b = by.get(t)
                    if b and b is not a:
                        segs.append((a, b))
        self.c.delete("all")
        for a, b in segs:
            x1, y1, s1 = self.reach(a, b)
            x2, y2, s2 = self.reach(b, a)
            if s1 + s2 < 1:
                self.c.create_line(x1, y1, x2, y2, fill=COLORS[a.color][0], width=2, arrow="last", arrowshape=(10, 12, 4))
        hidden = self.win.state() == "withdrawn"
        if segs and hidden:
            self.win.deiconify()
            self.win.attributes("-topmost", True)
        elif not segs and not hidden:
            self.win.withdraw()
        self.win.after(100, self.tick)


class Keys:
    def __init__(self, app):
        self.app, self.u, self.msg = app, ctypes.windll.user32, wintypes.MSG()
        for i, key in enumerate("NS", 1):
            self.u.RegisterHotKey(None, i, MOD, ord(key))
        self.poll()

    def poll(self):
        while self.u.PeekMessageW(ctypes.byref(self.msg), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
            if self.msg.wParam == 1:
                x, y = self.app.root.winfo_pointerxy()
                self.app.new((x - 30, y - 60))
            else:
                self.app.toggle()
        self.app.root.after(60, self.poll)


class App:
    def __init__(self):
        DIR.mkdir(exist_ok=True)
        self.root = tk.Tk()
        self.root.withdraw()
        data = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
        self.cfg = {**DEFAULTS, **data.get("settings", {})}
        self.state = {k: v for k, v in data.get("notes", {}).items() if (DIR / k).exists()}
        self.notes, self.sw, self.graph, self.seen, self.hidden = [], None, {}, {}, False
        self.index()
        self.hub = Hub(self)
        files = sorted(DIR.glob("*.md"))
        for p in files:
            if not self.state.get(p.name, {}).get("closed"):
                self.open_note(p)
        if not self.notes:
            self.hub.show() if files else self.new()
        self.lines = Lines(self)
        Keys(self)
        self.tick()
        self.root.mainloop()

    def index(self):
        files = {p: p.stat().st_mtime_ns for p in DIR.glob("*.md")}
        for p, m in files.items():
            if self.seen.get(p) != m:
                self.graph[p.stem.lower()] = links_of(p.read_text(encoding="utf-8-sig"))
        self.seen = files
        stems = {p.stem.lower() for p in files}
        self.graph = {k: v for k, v in self.graph.items() if k in stems}

    def backlinks(self, stem):
        me = stem.lower()
        return [p for p in sorted(DIR.glob("*.md")) if p.stem.lower() != me and me in self.graph.get(p.stem.lower(), ())]

    def open(self, path, info):
        self.notes.append(Note(self, path, info))

    def open_note(self, path, near=None):
        for n in self.notes:
            if n.path == path:
                n.win.lift()
                n.text.focus_force()
                return
        info = {**self.state.get(path.name, {}), "closed": False}
        if "geo" not in info:
            if near:
                x, y = near.win.winfo_x() + near.win.winfo_width() + 24, near.win.winfo_y()
            else:
                x = y = 120 + 30 * len(self.notes)
            info["geo"] = f"300x340+{x}+{y}"
        self.open(path, info)

    def open_link(self, name, near):
        name = re.sub(BAD, "", name).strip()
        p = next((p for p in DIR.glob("*.md") if p.stem.lower() == name.lower()), None)
        if p is None:
            p = DIR / f"{name}.md"
            p.write_text(f"# {name}\n", encoding="utf-8")
        self.open_note(p, near)

    def today(self):
        p = DIR / f"{time.strftime('%Y-%m-%d')}.md"
        if not p.exists():
            p.write_text(f"# {p.stem}\n\n", encoding="utf-8")
        self.open_note(p)

    def new(self, at=None):
        if self.hidden:
            self.toggle()
        taken = {p.stem.lower() for p in DIR.glob("*.md")} | {n.path.stem.lower() for n in self.notes}
        name, i = "Untitled", 0
        while name.lower() in taken:
            i += 1
            name = f"Untitled {i}"
        x, y = at or (120 + 30 * len(self.notes),) * 2
        info = {"geo": f"300x340+{max(x, 0)}+{max(y, 0)}", "pinned": self.cfg["pinned"], "color": self.cfg["color"]}
        self.open(DIR / f"{name}.md", info)
        t = self.notes[-1].text
        t.after(80, t.focus_force)

    def toggle(self):
        self.hidden = not self.hidden
        for n in self.notes:
            if self.hidden:
                n.win.withdraw()
            else:
                n.win.deiconify()

    def rename(self, note, name):
        name = re.sub(BAD, "", name).strip()
        old, new = note.path, DIR / f"{name}.md"
        if not name or (new.exists() and new.name.lower() != old.name.lower()):
            messagebox.showerror("Rename", "Name is empty or taken.", parent=note.win)
            return
        if old.exists():
            old.rename(new)
        pat = re.compile(r"\[\[" + re.escape(old.stem) + r"(?=[\]|#])", re.I)
        for p in DIR.glob("*.md"):
            txt = p.read_text(encoding="utf-8-sig")
            out = pat.sub(lambda m: "[[" + name, txt)
            if out != txt:
                p.write_text(out, encoding="utf-8")
        note.path = new
        if old.name in self.state:
            self.state[new.name] = self.state.pop(old.name)
        for n in self.notes:
            if n.path.exists():
                n.reload()
        note.paint_title()
        self.index()
        self.hub.refresh()

    def maybe_quit(self):
        if not self.notes and self.hub.win.state() == "withdrawn":
            self.root.destroy()

    def save(self):
        self.state.update({n.path.name: n.info() for n in self.notes})
        STATE.write_text(json.dumps({"settings": self.cfg, "notes": self.state}), encoding="utf-8")

    def set(self, key, value):
        self.cfg[key] = value
        if key in ("theme", "size", "alpha"):
            for n in self.notes:
                n.apply()
            self.hub.apply()
        self.save()

    def autostart(self, on):
        if on:
            py = Path(sys.executable).with_name("pythonw.exe")
            STARTUP.write_text(f'CreateObject("WScript.Shell").Run """{py}"" ""{Path(__file__).resolve()}""", 0\n')
        else:
            STARTUP.unlink(missing_ok=True)

    def show_settings(self):
        if self.sw and self.sw.winfo_exists():
            self.sw.lift()
            return
        w = self.sw = tk.Toplevel(self.root)
        w.title("Settings")
        w.geometry("320x470")
        w.resizable(False, False)
        w.bind("<Escape>", lambda e: w.destroy())
        pad = dict(anchor="w", padx=16, pady=(12, 2))
        tk.Label(w, text="Theme").pack(**pad)
        theme = tk.StringVar(value=self.cfg["theme"])
        row = tk.Frame(w)
        row.pack(anchor="w", padx=16)
        for v in THEMES:
            tk.Radiobutton(row, text=v, value=v, variable=theme, command=lambda: self.set("theme", theme.get())).pack(side="left")
        tk.Label(w, text="Default color for new notes").pack(**pad)
        color = tk.StringVar(value=self.cfg["color"])
        row = tk.Frame(w)
        row.pack(anchor="w", padx=16)
        for name, (head, _) in COLORS.items():
            tk.Radiobutton(row, value=name, variable=color, indicatoron=0, width=3, bg=head, selectcolor=head,
                           command=lambda: self.set("color", color.get())).pack(side="left", padx=2)
        tk.Label(w, text="Font size").pack(**pad)
        size = tk.StringVar(value=str(self.cfg["size"]))
        tk.Spinbox(w, from_=9, to=24, width=5, textvariable=size, command=lambda: self.set("size", int(size.get()))).pack(anchor="w", padx=16)
        tk.Label(w, text="Opacity").pack(**pad)
        scale = tk.Scale(w, from_=50, to=100, orient="horizontal", length=240, command=lambda v: self.set("alpha", int(float(v))))
        scale.set(self.cfg["alpha"])
        scale.pack(anchor="w", padx=16)
        pinned = tk.BooleanVar(value=self.cfg["pinned"])
        tk.Checkbutton(w, text="New notes always on top", variable=pinned, command=lambda: self.set("pinned", pinned.get())).pack(**pad)
        lines = tk.BooleanVar(value=self.cfg["lines"])
        tk.Checkbutton(w, text="Draw arrows between linked notes", variable=lines, command=lambda: self.set("lines", lines.get())).pack(anchor="w", padx=16)
        copy = tk.BooleanVar(value=self.cfg["autocopy"])
        tk.Checkbutton(w, text="Copy selected text automatically", variable=copy, command=lambda: self.set("autocopy", copy.get())).pack(anchor="w", padx=16)
        auto = tk.BooleanVar(value=self.cfg["autostart"])
        tk.Checkbutton(w, text="Start with Windows", variable=auto,
                       command=lambda: (self.set("autostart", auto.get()), self.autostart(auto.get()))).pack(anchor="w", padx=16)
        tk.Button(w, text="Open notes folder", command=lambda: os.startfile(DIR)).pack(anchor="w", padx=16, pady=12)

    def tick(self):
        self.index()
        for n in self.notes:
            n.poll()
            if n.pinned and not n.win.attributes("-topmost"):
                n.win.attributes("-topmost", True)
        self.save()
        self.root.after(2000, self.tick)


if __name__ == "__main__":
    App()
