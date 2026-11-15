import base64
import ctypes
import json
import os
import random
import re
import sys
import time
import tkinter as tk
import webbrowser
from bisect import bisect_right
from ctypes import wintypes
from html.parser import HTMLParser
from io import BytesIO
from itertools import accumulate
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox

DIR = Path.home() / "StickyMD"
STATE = DIR / "state.json"
STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/StickyMD.vbs"
FONT = "Segoe UI"
F = 1.0
KEY = "#ff00fe"
BAD = r'[\\/:*?"<>|]'
IMG = (".png", ".gif", ".jpg", ".jpeg", ".bmp", ".webp")
FAMILIES = ("Inter", "Segoe UI Variable Text", "Segoe UI", "Roboto", "Bahnschrift", "Calibri", "Cambria", "Candara",
            "Consolas", "Cascadia Code", "Georgia", "Arial", "Verdana", "Tahoma", "Times New Roman", "Trebuchet MS")
MOD, WM_HOTKEY, PM_REMOVE = 3, 0x312, 1
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
    "midnight": dict(bg="#0d1117", body="#161b22", card="#1c2230", fg="#e6edf3", muted="#8b949e", code="#2a3140",
                     link="#58a6ff", tag="#d2a8ff", edge="#010409"),
    "paper": dict(bg="#f6f1e7", body="#fbf6ea", card="#fffdf7", fg="#2b2b2b", muted="#7a7466", code="#e8e0cc",
                  link="#1a5fb4", tag="#8e44ad", edge="#cbbf9f"),
}
CALLOUTS = {
    True: {"note": "#1e3a5f", "tip": "#1f4d2f", "warning": "#5c4a14", "danger": "#5c1f1f"},
    False: {"note": "#cfe3f7", "tip": "#d3efca", "warning": "#f7e6b0", "danger": "#f5cccc"},
}
DEFAULTS = {"theme": "dark", "color": "yellow", "size": 11, "alpha": 100, "font": "", "pinned": True, "lines": True,
            "autocopy": True, "reveal": False, "autostart": False}
MATH = r"\$\$.+?\$\$|(?<![\\$\w])\$[^$\n]+?\$(?![\w$])"
PATTERNS = [
    ("meta", r"\A---\n.*?\n---[ \t]*(?=\n|\Z)", re.S),
    ("fence", r"^```.*?^```[ \t]*$", re.S),
    ("h1", r"^# .*$", 0),
    ("h2", r"^## .*$", 0),
    ("h3", r"^#{3,6} .*$", 0),
    ("hr", r"^(?:---|\*\*\*|___)[ \t]*$", 0),
    ("quote", r"^> (?!\[!).*$", 0),
    ("co-note", r"^> \[!\w+\].*$", 0),
    ("co-tip", r"^> \[!(?:tip|success|check|done)\].*$", 0),
    ("co-warning", r"^> \[!(?:warning|caution|attention)\].*$", 0),
    ("co-danger", r"^> \[!(?:danger|error|bug|failure)\].*$", 0),
    ("table", r"^\|.*\|[ \t]*$", 0),
    ("bold", r"\*\*.+?\*\*", 0),
    ("it", r"(?<!\*)\*(?!\*)[^*\n]+?\*(?!\*)", 0),
    ("strike", r"~~.+?~~", 0),
    ("mark", r"==.+?==", 0),
    ("code", r"`[^`\n]+`", 0),
    ("math", MATH, re.S),
    ("done", r"^- \[x\] .*$", 0),
    ("img", r"!\[[^\]\n]*\]\([^)\n]+\)", 0),
    ("mdlink", r"(?<!!)\[[^\]\n]+\]\([^)\s]+\)", 0),
    ("url", r"https?://[^\s<>)\]]+[^\s<>)\].,;:!?]", 0),
    ("link", r"\[\[.+?\]\]", 0),
    ("tag", r"(?<![\w#&])#[A-Za-z][\w/-]*", 0),
    ("bullet", r"^[ \t]*[-*+](?= )", 0),
]
LINK = re.compile(r"\[\[([^\]|#\n]+)(?:#([^\]|\n]*))?(?:\|[^\]\n]*)?\]\]")
MDIMG = re.compile(r"!\[[^\]\n]*\]\(([^)\n]+)\)")
GEO = re.compile(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)")
SYM = {r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ", r"\theta": "θ", r"\lambda": "λ", r"\mu": "μ",
       r"\pi": "π", r"\sigma": "σ", r"\omega": "ω", r"\sum": "∑", r"\int": "∫", r"\infty": "∞", r"\leq": "≤",
       r"\geq": "≥", r"\neq": "≠", r"\approx": "≈", r"\cdot": "·", r"\times": "×", r"\pm": "±", r"\to": "→",
       r"\sqrt": "√"}
SUP = str.maketrans("0123456789+-n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ")
SUB = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")
TEX = {}


def z(n):
    return round(n * F)


def geo(w, h, x, y):
    return f"{z(w)}x{z(h)}+{x}+{y}"


def scale_geo(g, f):
    m = GEO.match(g)
    return "x".join(str(round(int(v) * f)) for v in m.groups()[:2]) + "".join(f"+{round(int(v) * f)}" for v in m.groups()[2:]) if m else g


def spans(text):
    out = [(tag, m.start(), m.end()) for tag, p, fl in PATTERNS for m in re.finditer(p, text, re.M | fl)]
    raw = [(a, b) for tag, a, b in out if tag in ("fence", "meta")]
    return [s for s in out if s[0] in ("fence", "meta") or not any(a <= s[1] < b for a, b in raw)]


def marks(text):
    out = []
    for tag, a, b in spans(text):
        if tag in ("h1", "h2", "h3"):
            out.append((a, a + re.match(r"#+ ", text[a:b]).end()))
        elif tag in ("bold", "strike", "link", "mark"):
            out += [(a, a + 2), (b - 2, b)]
            if tag == "link" and a > 0 and text[a - 1] == "!":
                out.append((a - 1, a))
        elif tag in ("it", "code"):
            out += [(a, a + 1), (b - 1, b)]
        elif tag == "quote":
            out.append((a, a + 2))
        elif tag == "mdlink":
            n = len(re.match(r"\[([^\]]+)\]\(", text[a:b]).group(1))
            out += [(a, a + 1), (a + 1 + n, b)]
        elif tag == "img":
            n = len(re.match(r"!\[([^\]]*)\]\(", text[a:b]).group(1))
            out += [(a, a + 2), (a + 2 + n, b)]
        elif tag == "co-note":
            n = len(re.match(r"> \[!(\w+)\]", text[a:b]).group(1))
            out += [(a, a + 4), (a + 4 + n, a + 5 + n)]
        elif tag == "fence":
            nl = text.find("\n", a)
            if 0 <= nl < b:
                out += [(a, nl + 1), (text.rindex("\n", a, b), b)]
    return out


def links_of(text):
    return {m.group(1).strip().lower() for m in LINK.finditer(text)}


def link_at(text, off):
    for m in LINK.finditer(text):
        if m.start() <= off < m.end():
            return m.group(1).strip(), (m.group(2) or "").strip()


def image_at(text, off):
    for m in MDIMG.finditer(text):
        if m.start() <= off < m.end():
            return m.group(1).strip()


MDLINK = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\s]+)\)")
URL = re.compile(r"https?://[^\s<>)\]]+[^\s<>)\].,;:!?]")
HEADS = ("h1", "h2", "h3", "h4", "h5", "h6")
ROW = r"\s*\|.*\|\s*"


def url_at(text, off):
    for rx, g in ((MDLINK, 2), (URL, 0)):
        for m in rx.finditer(text):
            if m.start() <= off < m.end():
                return m.group(g)


def strip_inline(s):
    s = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\*\*|~~|==|`|\*", "", s)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def blocks(text):
    lines = text.split("\n")
    out, fence, i = [], False, 0
    if lines[0].strip() == "---":
        i = next((j + 1 for j in range(1, len(lines)) if lines[j].strip() == "---"), 0)
    while i < len(lines):
        s = lines[i]
        if s.lstrip().startswith("```"):
            fence = not fence
        elif not fence and re.fullmatch(r"(?:---|\*\*\*|___)[ \t]*", s):
            out.append({"kind": "hr", "a": i + 1, "b": i + 1})
        elif not fence and re.fullmatch(ROW, s):
            j = i
            while j < len(lines) and re.fullmatch(ROW, lines[j]):
                j += 1
            grp = lines[i:j]
            if len(grp) >= 2 and re.fullmatch(r"\s*\|?[\s:|-]*-[\s:|-]*\|?\s*", grp[1]):
                al = ["center" if c.startswith(":") and c.endswith(":") else "right" if c.endswith(":") else "left" for c in cells(grp[1])]
                out.append({"kind": "table", "a": i + 1, "b": j, "align": al,
                            "rows": [cells(g) for k, g in enumerate(grp) if k != 1]})
                i = j
                continue
        i += 1
    return out


class MD(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.o, self.lists, self.href, self.skip, self.pre = [], [], [], 0, False
        self.rows = self.row = self.cell = None

    def w(self, s):
        (self.cell if self.cell is not None else self.o).append(s)

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("script", "style", "head"):
            self.skip += 1
        elif tag in HEADS:
            self.w("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("p", "div", "section", "article") and self.cell is None:
            self.w("\n\n")
        elif tag == "br":
            self.w(" " if self.cell is not None else "\n")
        elif tag in ("strong", "b"):
            self.w("**")
        elif tag in ("em", "i"):
            self.w("*")
        elif tag in ("del", "s", "strike"):
            self.w("~~")
        elif tag == "code" and not self.pre:
            self.w("`")
        elif tag == "pre":
            self.pre = True
            self.w("\n\n```\n")
        elif tag == "a":
            self.href.append(a.get("href", ""))
            self.w("[")
        elif tag in ("ul", "ol"):
            self.lists.append([tag, 0])
            self.w("\n")
        elif tag == "li":
            cur = self.lists[-1] if self.lists else ["ul", 0]
            cur[1] += 1
            self.w("\n" + "  " * max(len(self.lists) - 1, 0) + ("- " if cur[0] == "ul" else f"{cur[1]}. "))
        elif tag == "blockquote":
            self.w("\n\n> ")
        elif tag == "hr":
            self.w("\n\n---\n\n")
        elif tag == "table":
            self.rows = []
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag == "img":
            self.w(f"![{a.get('alt', '')}]({a.get('src', '')})")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip -= 1
        elif tag in HEADS or tag in ("p", "div", "section", "article", "blockquote"):
            self.w("\n\n" if self.cell is None else "")
        elif tag in ("strong", "b"):
            self.w("**")
        elif tag in ("em", "i"):
            self.w("*")
        elif tag in ("del", "s", "strike"):
            self.w("~~")
        elif tag == "code" and not self.pre:
            self.w("`")
        elif tag == "pre":
            self.pre = False
            self.w("\n```\n\n")
        elif tag == "a" and self.href:
            self.w(f"]({self.href.pop()})")
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self.w("\n")
        elif tag in ("td", "th") and self.cell is not None:
            cell = " ".join("".join(self.cell).split()).replace("|", "\\|")
            self.cell = None
            if self.row is not None:
                self.row.append(cell)
        elif tag == "tr" and self.row is not None and self.rows is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.rows is not None:
            rows, self.rows = self.rows, None
            if rows:
                n = max(map(len, rows))
                rows = [r + [""] * (n - len(r)) for r in rows]
                lines = ["| " + " | ".join(r) + " |" for r in rows]
                lines.insert(1, "| " + " | ".join("---" for _ in range(n)) + " |")
                self.w("\n\n" + "\n".join(lines) + "\n\n")

    def handle_data(self, data):
        if not self.skip:
            self.w(data if self.pre else re.sub(r"\s+", " ", data))


def html_to_md(html):
    p = MD()
    p.feed(html)
    out = "".join(p.o)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\*\*\s*\*\*", "", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip("\n")


def tsv_to_md(text):
    rows = [ln.split("\t") for ln in text.splitlines() if ln.strip()]
    if len(rows) < 2 or not all(len(r) > 1 for r in rows):
        return ""
    n = max(map(len, rows))
    rows = [[c.strip().replace("|", "\\|") for c in r] + [""] * (n - len(r)) for r in rows]
    lines = ["| " + " | ".join(r) + " |" for r in rows]
    lines.insert(1, "| " + " | ".join("---" for _ in range(n)) + " |")
    return "\n".join(lines)


def clip_html():
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    u.GetClipboardData.restype = ctypes.c_void_p
    u.GetClipboardData.argtypes = [ctypes.c_uint]
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = [ctypes.c_void_p]
    k.GlobalUnlock.argtypes = [ctypes.c_void_p]
    fmt = u.RegisterClipboardFormatW("HTML Format")
    if not u.OpenClipboard(None):
        return ""
    try:
        h = u.GetClipboardData(fmt)
        if not h:
            return ""
        p = k.GlobalLock(h)
        raw = ctypes.string_at(p)
        k.GlobalUnlock(h)
    finally:
        u.CloseClipboard()
    a, b = re.search(rb"StartFragment:(\d+)", raw), re.search(rb"EndFragment:(\d+)", raw)
    return (raw[int(a.group(1)):int(b.group(1))] if a and b else raw).decode("utf-8", "replace")


def clean(text):
    t = re.sub(r"```|-{3,}|\*\*|~~|==|`|\|", " ", text)
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\[\[|\]\]", "", t)
    return " ".join(" ".join(re.sub(r"^[#>\s-]+", "", ln) for ln in t.splitlines()).split())


def math_at(text, off):
    for m in re.finditer(MATH, text, re.S):
        if m.start() <= off < m.end():
            return m.group(0).strip("$ \n")


def unicode_tex(s):
    for k, v in SYM.items():
        s = s.replace(k, v)
    s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\^\{([^{}]*)\}|\^(\w)", lambda m: (m.group(1) or m.group(2)).translate(SUP), s)
    s = re.sub(r"_\{([^{}]*)\}|_(\w)", lambda m: (m.group(1) or m.group(2)).translate(SUB), s)
    return s.replace("{", "").replace("}", "")


def render_tex(tex, color):
    from matplotlib.mathtext import math_to_image
    buf = BytesIO()
    math_to_image(f"${tex}$", buf, dpi=round(130 * F), format="png", color=color)
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))


def matches(stem, text, query):
    low = text.lower()
    for tok in query.lower().split():
        neg = tok.startswith("-")
        tok = tok.lstrip("-")
        if tok.startswith("tag:"):
            ok = f"#{tok[4:].lstrip('#')}" in low
        elif tok.startswith("title:"):
            ok = tok[6:] in stem.lower()
        else:
            ok = tok in low or tok in stem.lower()
        if ok == neg:
            return False
    return True


def offset(text, idx):
    line, col = map(int, idx.split("."))
    return sum(len(x) + 1 for x in text.split("\n")[:line - 1]) + col


def next_prefix(line):
    m = re.match(r"^(\s*)(\d+)\. ", line)
    if m:
        return f"{m.group(1)}{int(m.group(2)) + 1}. "
    m = re.match(r"^\s*(- \[[ x]\] |- |> )", line)
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


def aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()


def rounded(win):
    win.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)


def mix(a, b, k):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(ca, cb))


def glide(w, bg, fg, steps=5):
    if getattr(w, "_j", None):
        w.after_cancel(w._j)
    b0, f0 = w.cget("bg"), w.cget("fg")

    def step(i):
        if not w.winfo_exists():
            return
        w.config(bg=mix(b0, bg, i / steps), fg=mix(f0, fg, i / steps))
        w._j = w.after(16, step, i + 1) if i < steps else None

    step(1)


def hover(w, bg=None, fg=None):
    w._j = None

    def on(e):
        if w._j is None:
            w._c = (w.cget("bg"), w.cget("fg"))
        glide(w, bg or tint(w._c[0]), fg or w._c[1])

    def off(e):
        glide(w, *w._c)

    def press(e):
        if w._j:
            w.after_cancel(w._j)
            w._j = None
        w.config(bg=mix(bg or tint(w._c[0]), "#000000", 0.25))

    def release(e):
        if w.winfo_exists():
            glide(w, bg or tint(w._c[0]), fg or w._c[1])

    w.bind("<Enter>", on)
    w.bind("<Leave>", off)
    w.bind("<ButtonPress-1>", press, add="+")
    w.bind("<ButtonRelease-1>", release, add="+")


def tip(w, text):
    box = {}

    def show():
        t = box["t"] = tk.Toplevel(w)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        tk.Label(t, text=text, bg="#2b2b2b", fg="#f2f2f2", font=(FONT, 9), padx=z(6), pady=z(3)).pack()
        t.geometry(f"+{w.winfo_rootx()}+{w.winfo_rooty() + w.winfo_height() + z(4)}")

    def hide(e=None):
        if "j" in box:
            w.after_cancel(box.pop("j"))
        if "t" in box:
            box.pop("t").destroy()

    w.bind("<Enter>", lambda e: box.update(j=w.after(500, show)), add="+")
    w.bind("<Leave>", hide, add="+")
    w.bind("<Button-1>", hide, add="+")


def movable(win, *widgets):
    d = {}

    def grab(e):
        d["o"] = (e.x_root - win.winfo_x(), e.y_root - win.winfo_y())

    def drag(e):
        win.geometry(f"+{e.x_root - d['o'][0]}+{e.y_root - d['o'][1]}")

    for w in widgets:
        w.bind("<ButtonPress-1>", grab, add="+")
        w.bind("<B1-Motion>", drag)


def sizer(win, w, h):
    g = tk.Label(win, text="◢", font=(FONT, 12), padx=z(4), cursor="size_nw_se")
    g.place(relx=1, rely=1, anchor="se")
    g.bind("<B1-Motion>", lambda e: win.geometry(f"{max(w, e.x_root - win.winfo_rootx())}x{max(h, e.y_root - win.winfo_rooty())}"))
    tip(g, "Resize")
    return g


def hbtn(parent, text, cmd, hint, size=12, red=False, pad=11):
    b = tk.Label(parent, text=text, font=(FONT, size), padx=z(pad), pady=z(4), cursor="hand2")
    if red:
        hover(b, "#c42b1c", "#ffffff")
    else:
        hover(b)
    tip(b, hint)
    b.bind("<Button-1>", cmd, add="+")
    return b


def shade(win, hide, show, keep, grip):
    if win._shaded:
        w = win.winfo_width()
        for fn in show:
            fn()
        win.geometry(f"{w}x{win._full}")
        grip.place(relx=1, rely=1, anchor="se")
    else:
        win._full = win.winfo_height()
        for wid in hide:
            wid.pack_forget()
        grip.place_forget()
        win.update_idletasks()
        win.geometry(f"{win.winfo_width()}x{keep.winfo_reqheight() + z(2)}")
    win._shaded = not win._shaded


class Note:
    def __init__(self, app, path, info):
        self.app, self.path = app, path
        self.pinned = info.get("pinned", app.cfg["pinned"])
        self.color = info.get("color", app.cfg["color"])
        self.mtime = path.stat().st_mtime_ns if path.exists() else 0
        self.sug, self.raw, self.emb, self.sig, self.down = None, False, [], None, None
        self.pl, self.ed = None, None
        self.win = w = tk.Toplevel(app.root)
        w._shaded, w._full = False, 0
        w.overrideredirect(True)
        w.geometry(info.get("geo", geo(300, 340, z(120), z(120))))
        w.attributes("-topmost", self.pinned)
        w.config(highlightthickness=1)
        self.bar = bar = tk.Frame(w, cursor="fleur")
        bar.pack(fill="x")
        self.btns = [
            hbtn(bar, "+", lambda e: app.new(), "New note (Ctrl+N)", pad=8),
            hbtn(bar, "", self.toggle_pin, "Keep on top / put down", pad=8),
            hbtn(bar, "✕", self.close, "Close (Ctrl+W)", red=True, pad=8),
            hbtn(bar, "⋯", self.menu, "Menu", pad=8),
            hbtn(bar, "—", self.collapse, "Collapse (Ctrl+M)", pad=8),
        ]
        self.pin = self.btns[1]
        for b, side in zip(self.btns, ("left", "left", "right", "right", "right")):
            b.pack(side=side)
        self.title = tk.Label(bar, font=(FONT, 9), anchor="w", padx=z(6))
        self.title.pack(side="left", fill="x", expand=True)
        movable(w, bar, self.title)
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
            b = tk.Label(self.tools, text=label, font=(FONT, 11) + ((style,) if style else ()), padx=z(12), pady=z(6), cursor="hand2")
            b.pack(side="left")
            hover(b)
            tip(b, hint)
            b.bind("<Button-1>", lambda e, c=cmd: c(), add="+")
            self.tl.append(b)
        self.bl = tk.Label(self.tools, text="↩ 0", font=(FONT, 10), padx=z(10), pady=z(6), cursor="hand2")
        self.bl.pack(side="right", padx=(0, z(22)))
        hover(self.bl)
        tip(self.bl, "Backlinks")
        self.bl.bind("<Button-1>", self.back, add="+")
        self.tl.append(self.bl)
        self.msg = tk.Label(self.tools, font=(FONT, 9), padx=z(6))
        self.msg.pack(side="left")
        self.text = t = tk.Text(w, bd=0, wrap="word", undo=True, padx=z(14), pady=z(10), spacing1=z(2), spacing3=z(2), highlightthickness=0)
        t.pack(fill="both", expand=True)
        self.pv = tk.Label(w, bd=0, padx=z(12), pady=z(8))
        t.insert("1.0", path.read_text(encoding="utf-8-sig") if path.exists() else "# ")
        t.edit_reset()
        t.edit_modified(False)
        t.bind("<<Modified>>", self.changed)
        t.bind("<Button-1>", self.click)
        t.bind("<<Paste>>", self.paste)
        t.bind("<Return>", self.enter)
        t.bind("<Tab>", self.accept)
        t.bind("<Escape>", self.unsuggest)
        t.bind("<F2>", lambda e: self.rename())
        t.bind("<Down>", lambda e: self.pick(1))
        t.bind("<Up>", lambda e: self.pick(-1))
        t.bind("<KeyRelease>", self.keyed)
        t.bind("<ButtonRelease-1>", self.released)
        for key, fn in (("b", lambda: self.wrap("**")), ("i", lambda: self.wrap("*")), ("n", app.new),
                        ("w", self.close), ("l", app.hub.show), ("m", self.collapse), ("e", self.toggle_raw)):
            t.bind(f"<Control-{key}>", lambda e, f=fn: (f(), "break")[1])
        self.grip = sizer(w, z(200), z(140))
        self.apply()
        self.paint_title()
        rounded(w)
        if info.get("collapsed"):
            w._full = info.get("full", z(340))
            w._shaded = False
            w.update_idletasks()
            self.collapse()
            w._full = info.get("full", z(340))

    def collapse(self, e=None):
        shade(self.win, (self.text, self.tools, self.pv), (lambda: self.tools.pack(side="bottom", fill="x"),
                                                           lambda: self.text.pack(fill="both", expand=True)), self.bar, self.grip)
        self.pv.place_forget()

    def apply(self):
        cfg = self.app.cfg
        th = THEMES[cfg["theme"]]
        head, light = COLORS[self.color]
        body, s = th["body"] or light, cfg["size"]
        fg, nf = th["fg"], cfg["font"] or FONT
        dark = ink(body) == "#ffffff"
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
        self.pv.config(bg=th["card"], fg=fg)
        t = self.text
        t.config(bg=body, fg=fg, insertbackground=fg, font=(nf, s))
        t.tag_configure("h1", font=(nf, s + 6, "bold"))
        t.tag_configure("h2", font=(nf, s + 3, "bold"))
        t.tag_configure("h3", font=(nf, s + 1, "bold"))
        t.tag_configure("bold", font=(nf, s, "bold"))
        t.tag_configure("it", font=(nf, s, "italic"))
        t.tag_configure("strike", overstrike=True)
        t.tag_configure("mark", background="#7a6a10" if dark else "#fff0a0")
        t.tag_configure("code", font=("Consolas", s - 1), background=th["code"])
        t.tag_configure("fence", font=("Consolas", s - 1), background=th["code"], lmargin1=z(6), lmargin2=z(6))
        t.tag_configure("table", font=("Consolas", s - 1))
        t.tag_configure("meta", font=(nf, s - 2), foreground=th["muted"])
        t.tag_configure("hr", foreground=th["muted"], overstrike=True)
        t.tag_configure("quote", foreground=th["muted"], font=(nf, s, "italic"), lmargin1=z(12), lmargin2=z(12))
        for tag, key in (("co-note", "note"), ("co-tip", "tip"), ("co-warning", "warning"), ("co-danger", "danger")):
            t.tag_configure(tag, background=CALLOUTS[dark][key], font=(nf, s, "bold"))
        t.tag_configure("math", foreground=th["tag"], font=("Cambria Math", s))
        t.tag_configure("done", overstrike=True, foreground=th["muted"])
        t.tag_configure("img", foreground=th["link"])
        t.tag_configure("link", foreground=th["link"], underline=True)
        t.tag_configure("mdlink", foreground=th["link"], underline=True)
        t.tag_configure("url", foreground=th["link"], underline=True)
        t.tag_configure("tag", foreground=th["tag"])
        t.tag_configure("bullet", foreground=COLORS[self.color][0], font=(nf, s, "bold"))
        t.tag_configure("hide", elide=True)
        self.paint_pin()
        self.style()

    def paint_title(self):
        s = self.path.stem
        self.title.config(text=s if len(s) < 24 else s[:23] + "…")

    def paint_back(self):
        self.bl.config(text=f"↩ {len(self.app.backlinks(self.path.stem))}")

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
        m.add_command(label="Rendered view" if self.raw else "Show markdown syntax (Ctrl+E)", command=self.toggle_raw)
        m.add_command(label="Today's note", command=self.app.today)
        m.add_command(label="Notes list", command=self.app.hub.show)
        m.add_command(label="Graph", command=self.app.show_graph)
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
        if self.ed:
            return
        head = COLORS[self.color][0]
        en = self.ed = tk.Entry(self.bar, font=(FONT, 9), relief="flat", bd=0, bg=tint(head, 0.3), fg=ink(head),
                                insertbackground=ink(head), highlightthickness=z(1), highlightbackground=ink(head),
                                highlightcolor=ink(head), selectbackground=ink(head), selectforeground=head)
        en.insert(0, self.path.stem)
        en.select_range(0, "end")
        self.title.pack_forget()
        en.pack(side="left", fill="x", expand=True, padx=z(4), pady=z(6), ipady=z(2))
        en.focus_force()

        def done(commit):
            if self.ed is not en:
                return
            self.ed = None
            name = en.get().strip()
            en.destroy()
            self.title.pack(side="left", fill="x", expand=True)
            if commit and name and name != self.path.stem and not self.app.rename(self, name):
                self.flash("name taken")

        en.bind("<Return>", lambda e: done(True))
        en.bind("<Escape>", lambda e: done(False))
        en.bind("<FocusOut>", lambda e: done(True))

    def wrap(self, mark, end=None):
        t = self.text
        end = end or mark
        if t.tag_ranges("sel"):
            a, b = t.index("sel.first"), t.index("sel.last")
            t.insert(b, end)
            t.insert(a, mark)
        else:
            t.insert("insert", mark + end)
            t.mark_set("insert", f"insert-{len(end)}c")
        t.focus_force()

    def copy(self):
        t = self.text
        t.clipboard_clear()
        t.clipboard_append(t.get("sel.first", "sel.last"))
        self.flash("copied")

    def pill(self):
        t = self.text
        box = t.tag_ranges("sel") and t.bbox("sel.first")
        if not box or self.win._shaded:
            return self.unpill()
        th = THEMES[self.app.cfg["theme"]]
        if not self.pl:
            p = tk.Toplevel(self.win)
            p.overrideredirect(True)
            p.attributes("-topmost", True)
            p.config(bg=th["card"], highlightthickness=1, highlightbackground=th["edge"])
            for label, style, cmd in (
                ("B", "bold", lambda: self.wrap("**")),
                ("I", "italic", lambda: self.wrap("*")),
                ("S", "overstrike", lambda: self.wrap("~~")),
                ("H", "", lambda: self.wrap("==")),
                ("[[ ]]", "", lambda: self.wrap("[[", "]]")),
                ("Copy", "", self.copy),
            ):
                b = tk.Label(p, text=label, font=(FONT, 10) + ((style,) if style else ()), bg=th["card"], fg=th["fg"],
                             padx=z(8), pady=z(4), cursor="hand2")
                b.pack(side="left")
                hover(b)
                b.bind("<ButtonRelease-1>", lambda e, c=cmd: (c(), self.unpill(), self.text.focus_force()), add="+")
            rounded(p)
            self.pl = p
        self.pl.update_idletasks()
        self.pl.geometry(f"+{t.winfo_rootx() + box[0]}+{max(t.winfo_rooty() + box[1] - self.pl.winfo_reqheight() - z(6), 0)}")

    def unpill(self):
        if self.pl:
            self.pl.destroy()
            self.pl = None

    def prefix(self, p):
        self.text.insert("insert linestart", p)
        self.text.focus_force()

    def click(self, e):
        t = self.text
        t.focus_force()
        self.unsuggest()
        self.unpill()
        self.down = (e.x, e.y)
        line, col = map(int, t.index(f"@{e.x},{e.y}").split("."))
        m = re.match(r"- \[([ x])\] ", t.get(f"{line}.0", f"{line}.end"))
        if m and 2 <= col <= 4:
            t.replace(f"{line}.3", f"{line}.4", " " if m.group(1) == "x" else "x")
            return "break"

    def follow(self, e):
        t = self.text
        body = t.get("1.0", "end-1c")
        off = offset(body, t.index(f"@{e.x},{e.y}"))
        hit = link_at(body, off)
        if hit:
            self.app.open_link(hit[0], self, hit[1])
        elif image_at(body, off):
            self.app.open_image(image_at(body, off), self)
        elif url_at(body, off):
            webbrowser.open(url_at(body, off))

    def goto(self, heading):
        t = self.text
        body = t.get("1.0", "end-1c")
        m = re.search(r"^#+ +" + re.escape(heading) + r"\s*$", body, re.M | re.I)
        if m:
            t.mark_set("insert", f"{body.count(chr(10), 0, m.start()) + 1}.0")
            t.see("insert")
            self.style()

    def enter(self, e):
        if self.sug:
            return self.accept()
        t = self.text
        line = t.get("insert linestart", "insert")
        p = next_prefix(line)
        if p is None:
            return None
        if re.fullmatch(r"\s*(-( \[[ x]\])?|\d+\.|>)\s*", line):
            t.delete("insert linestart", "insert")
        else:
            t.insert("insert", "\n" + p)
        return "break"

    def keyed(self, e):
        self.style()
        t = self.text
        if not t.tag_ranges("sel"):
            self.unpill()
        m = re.search(r"\[\[([^\]\n]*)$", t.get("insert linestart", "insert"))
        names = [p.stem for p in sorted(DIR.glob("*.md")) if m and m.group(1).lower() in p.stem.lower()][:8]
        if m and names and e.keysym not in ("Up", "Down", "Return", "Tab", "Escape"):
            self.suggest(names, m.group(1))
        elif not m or not names:
            self.unsuggest()
        self.preview()

    def suggest(self, names, typed):
        th = THEMES[self.app.cfg["theme"]]
        if not self.sug:
            p = tk.Toplevel(self.win)
            p.overrideredirect(True)
            p.attributes("-topmost", True)
            lb = tk.Listbox(p, bg=th["card"], fg=th["fg"], selectbackground=COLORS[self.color][0], selectforeground=ink(COLORS[self.color][0]),
                            highlightthickness=1, highlightbackground=th["edge"], relief="flat", activestyle="none", font=(FONT, 10))
            lb.pack()
            self.sug = {"win": p, "lb": lb}
        lb = self.sug["lb"]
        lb.delete(0, "end")
        lb.insert("end", *names)
        lb.config(height=len(names), width=max(len(n) for n in names) + 2)
        lb.selection_set(0)
        self.sug["typed"] = typed
        x, y, _, h = self.text.bbox("insert")
        self.sug["win"].geometry(f"+{self.text.winfo_rootx() + x}+{self.text.winfo_rooty() + y + h + z(4)}")

    def unsuggest(self, e=None):
        if self.sug:
            self.sug["win"].destroy()
            self.sug = None
            return "break"

    def pick(self, d):
        if not self.sug:
            return None
        lb = self.sug["lb"]
        i = (lb.curselection() or (0,))[0]
        lb.selection_clear(0, "end")
        lb.selection_set(min(max(i + d, 0), lb.size() - 1))
        return "break"

    def accept(self, e=None):
        if not self.sug:
            return None
        lb, typed = self.sug["lb"], self.sug["typed"]
        name = lb.get(lb.curselection()[0])
        self.unsuggest()
        self.text.delete(f"insert-{len(typed)}c", "insert")
        self.text.insert("insert", name + "]]")
        return "break"

    def preview(self):
        t = self.text
        body = t.get("1.0", "end-1c")
        tex = math_at(body, offset(body, t.index("insert")))
        if not tex or self.win._shaded:
            self.pv.place_forget()
            return
        fg = THEMES[self.app.cfg["theme"]]["fg"]
        if (tex, fg) not in TEX:
            try:
                TEX[(tex, fg)] = render_tex(tex, fg)
            except (ImportError, ValueError, RuntimeError):
                TEX[(tex, fg)] = None
        img = TEX[(tex, fg)]
        if img:
            self.pv.config(image=img, text="")
        else:
            self.pv.config(image="", text=unicode_tex(tex), font=("Cambria Math", self.app.cfg["size"] + 2))
        self.pv.place(x=0, rely=1, y=-self.tools.winfo_height(), relwidth=1, anchor="sw")
        self.pv.lift()

    def released(self, e):
        t = self.text
        moved = self.down and (abs(e.x - self.down[0]) > 3 or abs(e.y - self.down[1]) > 3)
        if self.down and not moved and not t.tag_ranges("sel"):
            self.follow(e)
        self.style()
        self.preview()
        if self.app.cfg["autocopy"] and t.tag_ranges("sel"):
            t.clipboard_clear()
            t.clipboard_append(t.get("sel.first", "sel.last"))
            self.flash("copied")
        self.pill()

    def flash(self, text):
        self.msg.config(text=text)
        self.win.after(1200, lambda: self.msg.winfo_exists() and self.msg.config(text=""))

    def autoname(self):
        title = title_of(self.text.get("1.0", "end-1c"))
        if self.path.stem.startswith("Untitled") and self.path.exists() and title and not (DIR / f"{title}.md").exists():
            self.app.rename(self, title)

    def style(self):
        t = self.text
        was = t.edit_modified()
        body = t.get("1.0", "end-1c")
        starts = list(accumulate([0] + [len(ln) + 1 for ln in body.split("\n")]))

        def at(off):
            i = bisect_right(starts, off) - 1
            return f"{i + 1}.{off - starts[i]}"

        for tag, _, _ in PATTERNS:
            t.tag_remove(tag, "1.0", "end")
        t.tag_remove("hide", "1.0", "end")
        for tag, a, b in spans(body):
            t.tag_add(tag, at(a), at(b))
        cur = int(t.index("insert").split(".")[0])
        if not self.raw:
            for a, b in marks(body):
                if not (self.app.cfg["reveal"] and bisect_right(starts, a) == cur):
                    t.tag_add("hide", at(a), at(b))
        self.embed(body, cur)
        if not was:
            t.edit_modified(False)

    def toggle_raw(self, e=None):
        self.raw = not self.raw
        self.style()
        self.flash("raw" if self.raw else "rendered")

    def paste(self, e):
        t = self.text
        try:
            plain = t.clipboard_get()
        except tk.TclError:
            plain = ""
        html = clip_html()
        new = (html_to_md(html) if html else "") or tsv_to_md(plain) or plain
        if not new:
            return "break"
        if t.tag_ranges("sel"):
            t.delete("sel.first", "sel.last")
        if "\n" in new.strip("\n") and not new.endswith("\n"):
            new += "\n"
        t.insert("insert", new)
        t.see("insert")
        return "break"

    def embed(self, body, cur):
        t = self.text
        lines = body.split("\n")
        show = [] if self.raw else [b for b in blocks(body) if not (b["a"] <= cur <= b["b"])]
        for b in show:
            t.tag_add("hide", f"{b['a']}.0", f"{b['b']}.{len(lines[b['b'] - 1])}")
        cfg = self.app.cfg
        sig = (cfg["theme"], cfg["size"], cfg["font"], self.color, tuple((b["kind"], b["a"], b["b"], str(b.get("rows"))) for b in show))
        if sig == self.sig:
            return
        self.sig = sig
        for _, _, idx in reversed(t.dump("1.0", "end", window=True)):
            t.delete(idx)
        for f in self.emb:
            f.destroy()
        self.emb = []
        th = THEMES[cfg["theme"]]
        for b in show:
            f = self.make_table(b) if b["kind"] == "table" else tk.Frame(t, height=z(1), width=max(z(120), t.winfo_width() - z(60)), bg=th["muted"])
            t.window_create(f"{b['b']}.{len(lines[b['b'] - 1])}", window=f, padx=z(2), pady=z(6))
            self.emb.append(f)

    def make_table(self, blk):
        cfg = self.app.cfg
        th = THEMES[cfg["theme"]]
        body = th["body"] or COLORS[self.color][1]
        f = tk.Frame(self.text, bg=th["code"], cursor="hand2")
        for r, row in enumerate(blk["rows"]):
            for c, cell in enumerate(row):
                side = blk["align"][c] if c < len(blk["align"]) else "left"
                lab = tk.Label(f, text=strip_inline(cell), bg=tint(body, 0.1) if r == 0 else body, fg=th["fg"],
                               font=(cfg["font"] or FONT, cfg["size"] - 1, "bold" if r == 0 else "normal"),
                               anchor={"left": "w", "right": "e", "center": "center"}[side], justify="left",
                               wraplength=z(200), padx=z(8), pady=z(4))
                lab.grid(row=r, column=c, sticky="nsew", padx=z(1), pady=z(1))
                lab.bind("<Button-1>", lambda e, b=blk: self.edit_block(b))
        return f

    def edit_block(self, blk):
        self.text.mark_set("insert", f"{blk['a']}.0")
        self.text.focus_force()
        self.style()

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
            self.sig = None
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
        out = {"geo": self.win.geometry(), "pinned": self.pinned, "color": self.color}
        if self.win._shaded:
            out.update(collapsed=True, full=self.win._full)
        return out

    def close(self, e=None):
        self.unsuggest()
        self.unpill()
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


class Pane:
    def __init__(self, app, title, w, h, x, y):
        th = THEMES[app.cfg["theme"]]
        self.app, self.th = app, th
        self.win = win = tk.Toplevel(app.root)
        win._shaded, win._full = False, 0
        win.overrideredirect(True)
        win.geometry(geo(w, h, z(x), z(y)))
        win.config(bg=th["bg"], highlightthickness=1, highlightbackground=th["edge"])
        win.bind("<Escape>", lambda e: self.hide())
        self.top = tk.Frame(win, bg=th["bg"], cursor="fleur")
        self.top.pack(fill="x", padx=z(6), pady=(z(6), 0))
        self.title = tk.Label(win, text=title, bg=th["bg"], fg=th["fg"], font=(FONT, 18, "bold"), anchor="w", padx=z(8))
        movable(win, self.top, self.title)

    def hide(self):
        self.win.destroy()


class Hub(Pane):
    def __init__(self, app):
        super().__init__(app, "Sticky Notes", 360, 560, 60, 60)
        self.job, self.found = None, []
        w = self.win
        self.btns = [
            hbtn(self.top, "+", lambda e: app.new(), "New note", 18),
            hbtn(self.top, "📅", lambda e: app.today(), "Today's note", 13),
            hbtn(self.top, "◎", lambda e: app.show_graph(), "Graph view", 15),
            hbtn(self.top, "✕", lambda e: self.hide(), "Close", 12, True),
            hbtn(self.top, "—", lambda e: self.collapse(), "Collapse", 12),
            hbtn(self.top, "⚙", lambda e: app.show_settings(), "Settings", 15),
        ]
        for b, side in zip(self.btns, ("left", "left", "left", "right", "right", "right")):
            b.pack(side=side)
        self.title.pack(fill="x", padx=z(8), pady=(z(4), z(10)))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: (self.build(), self.sync()))
        self.search = tk.Entry(w, textvariable=self.q, relief="flat", font=(FONT, 11))
        self.search.pack(fill="x", padx=z(16), ipady=z(8))
        self.hint = tk.Label(self.search, text="Search notes, #tags, tag:x, -word", font=(FONT, 11))
        self.hint.bind("<Button-1>", lambda e: self.search.focus_set())
        self.search.bind("<FocusIn>", self.sync)
        self.search.bind("<FocusOut>", self.sync)
        self.search.bind("<Return>", lambda e: self.found and self.app.open_note(self.found[0]))
        self.sync()
        self.canvas = tk.Canvas(w, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=z(8))
        self.list = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.list, anchor="nw", tags="f")
        self.canvas.bind("<Configure>", self.resized)
        self.list.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        w.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"))
        self.grip = sizer(w, z(280), z(360))
        self.apply()
        rounded(w)
        w.protocol("WM_DELETE_WINDOW", self.hide)
        w.withdraw()

    def collapse(self):
        shade(self.win, (self.search, self.canvas), (lambda: self.search.pack(fill="x", padx=z(16), ipady=z(8)),
                                                     lambda: self.canvas.pack(fill="both", expand=True, pady=z(8))), self.title, self.grip)

    def hide(self):
        self.win.withdraw()
        self.app.maybe_quit()

    def resized(self, e):
        self.canvas.itemconfig("f", width=e.width)
        self.refresh()

    def apply(self):
        th = THEMES[self.app.cfg["theme"]]
        self.th = th
        self.win.config(bg=th["bg"], highlightbackground=th["edge"])
        for f in (self.top, self.canvas, self.list):
            f.config(bg=th["bg"])
        for b in self.btns:
            b.config(bg=th["bg"], fg=th["muted"])
        self.title.config(bg=th["bg"], fg=th["fg"])
        self.search.config(bg=th["card"], fg=th["fg"], insertbackground=th["fg"])
        self.hint.config(bg=th["card"], fg=th["muted"])
        self.grip.config(bg=th["bg"], fg=th["muted"])
        if self.win.state() != "withdrawn":
            self.build()

    def sync(self, e=None):
        if self.q.get() or self.win.focus_get() is self.search:
            self.hint.place_forget()
        else:
            self.hint.place(x=z(8), rely=0.5, anchor="w")

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.build()
        self.win.focus_force()
        self.search.focus_set()

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
        q = self.q.get()
        for p in sorted(DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            txt = p.read_text(encoding="utf-8-sig")
            if matches(p.stem, txt, q):
                self.found.append(p)
                self.card(p, txt)
        if not self.list.winfo_children():
            tk.Label(self.list, text="No matches" if q else "No notes yet", bg=self.th["bg"], fg=self.th["muted"],
                     font=(FONT, 11)).pack(pady=z(40))

    def card(self, p, txt):
        th = self.th
        head = COLORS[self.app.state.get(p.name, {}).get("color", self.app.cfg["color"])][0]
        f = tk.Frame(self.list, bg=th["card"], cursor="hand2")
        f.pack(fill="x", padx=z(16), pady=z(6))
        tk.Frame(f, bg=head, height=z(3)).pack(fill="x")
        lt = time.localtime(p.stat().st_mtime)
        same = time.strftime("%Y%m%d", lt) == time.strftime("%Y%m%d")
        tk.Label(f, text=time.strftime("%I:%M %p" if same else "%b %d", lt), bg=th["card"], fg=th["muted"],
                 font=(FONT, 9), anchor="e").pack(fill="x", padx=z(12), pady=(z(8), 0))
        tk.Label(f, text=p.stem, bg=th["card"], fg=th["fg"], font=(FONT, 12, "bold"),
                 anchor="w").pack(fill="x", padx=z(12))
        body = clean(txt)
        if body.lower().startswith(p.stem.lower()):
            body = body[len(p.stem):].strip()
        wl = max(z(200), self.canvas.winfo_width() - z(56))
        tags = list(dict.fromkeys(re.findall(r"(?<![\w#&])#[A-Za-z][\w/-]*", txt)))[:3]
        n = len(self.app.backlinks(p.stem))
        chips = [(c, th["tag"]) for c in tags] + ([(f"↩ {n}", th["muted"])] if n else [])
        tk.Label(f, text=body[:140] or "empty note", bg=th["card"], fg=th["muted"], font=(FONT, 10), wraplength=wl,
                 justify="left", anchor="w").pack(fill="x", padx=z(12), pady=(z(2), z(8) if chips else z(12)))
        if chips:
            row = tk.Frame(f, bg=th["card"])
            row.pack(fill="x", padx=z(12), pady=(0, z(12)))
            for text, col in chips:
                tk.Label(row, text=text, bg=tint(th["card"], 0.12), fg=col, font=(FONT, 9), padx=z(7), pady=z(1)).pack(side="left", padx=(0, z(5)))
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


class Graph(Pane):
    def __init__(self, app):
        super().__init__(app, "Graph", 560, 460, 200, 120)
        w, th = self.win, self.th
        x = hbtn(self.top, "✕", lambda e: self.hide(), "Close", 12, True)
        x.config(bg=th["bg"], fg=th["muted"])
        x.pack(side="right")
        self.title.pack(fill="x", padx=z(8), pady=(z(4), 0))
        self.c = tk.Canvas(w, bg=th["bg"], highlightthickness=0)
        self.c.pack(fill="both", expand=True, pady=z(8))
        self.grip = sizer(w, z(300), z(240))
        self.grip.config(bg=th["bg"], fg=th["muted"])
        self.layout()
        self.c.bind("<Configure>", lambda e: self.draw())
        rounded(w)

    def layout(self):
        names = [p.stem for p in sorted(DIR.glob("*.md"))]
        low = {n.lower(): n for n in names}
        self.edges = {(a, low[t]) for a in names for t in self.app.graph.get(a.lower(), ()) if t in low and low[t] != a}
        rnd = random.Random(1)
        pos = {n: [rnd.random(), rnd.random()] for n in names}
        for _ in range(250):
            push = {n: [0.0, 0.0] for n in names}
            for a in names:
                for b in names:
                    if a < b:
                        dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                        d = max((dx * dx + dy * dy) ** 0.5, 0.02)
                        f = 0.0015 / (d * d)
                        push[a][0] += dx / d * f
                        push[a][1] += dy / d * f
                        push[b][0] -= dx / d * f
                        push[b][1] -= dy / d * f
            for a, b in self.edges:
                dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
                for n, s in ((a, 1), (b, -1)):
                    push[n][0] += dx * 0.04 * s
                    push[n][1] += dy * 0.04 * s
            for n in names:
                pos[n] = [min(max(pos[n][0] + push[n][0], 0.06), 0.94), min(max(pos[n][1] + push[n][1], 0.08), 0.9)]
        self.pos = pos

    def draw(self):
        c, th, app = self.c, self.th, self.app
        c.delete("all")
        W, H = max(c.winfo_width(), 1), max(c.winfo_height(), 1)
        at = {n: (p[0] * W, p[1] * H) for n, p in self.pos.items()}
        for a, b in self.edges:
            c.create_line(*at[a], *at[b], fill=th["muted"], width=z(1))
        for n, (x, y) in at.items():
            deg = sum(1 for e in self.edges if n in e)
            r = z(7 + 2 * deg)
            col = COLORS[app.state.get(f"{n}.md", {}).get("color", app.cfg["color"])][0]
            tag = f"n{abs(hash(n))}"
            c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="", tags=tag)
            c.create_text(x, y + r + z(10), text=n, fill=th["fg"], font=(FONT, 9), tags=tag)
            c.tag_bind(tag, "<Button-1>", lambda e, n=n: app.open_note(DIR / f"{n}.md"))
            c.tag_bind(tag, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.config(cursor=""))


class View(Pane):
    def __init__(self, app, path, near=None):
        x, y = (near.win.winfo_x() + near.win.winfo_width() + z(24), near.win.winfo_y()) if near else (z(200), z(120))
        super().__init__(app, path.name, 100, 100, 0, 0)
        w, th = self.win, self.th
        try:
            img = tk.PhotoImage(file=str(path))
        except tk.TclError:
            from PIL import Image, ImageTk
            img = ImageTk.PhotoImage(Image.open(path))
        k = max(1, -(-img.width() // z(640)), -(-img.height() // z(480)))
        self.img = img.subsample(k) if k > 1 else img
        x_ = hbtn(self.top, "✕", lambda e: self.hide(), "Close", 12, True)
        x_.config(bg=th["bg"], fg=th["muted"])
        x_.pack(side="right")
        self.title.config(font=(FONT, 11, "bold"))
        self.title.pack(side="left")
        tk.Label(w, image=self.img, bg=th["bg"], bd=0).pack(padx=z(8), pady=z(8))
        w.attributes("-topmost", True)
        w.geometry(f"+{x}+{y}")
        w.update_idletasks()
        w.geometry(f"{w.winfo_reqwidth()}x{w.winfo_reqheight()}+{x}+{y}")
        rounded(w)


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
                self.c.create_line(x1, y1, x2, y2, fill=COLORS[a.color][0], width=z(2), arrow="last",
                                   arrowshape=(z(10), z(12), z(4)))
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
        for i, key in enumerate("NSL", 1):
            self.u.RegisterHotKey(None, i, MOD, ord(key))
        self.poll()

    def poll(self):
        while self.u.PeekMessageW(ctypes.byref(self.msg), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
            if self.msg.wParam == 1:
                x, y = self.app.root.winfo_pointerxy()
                self.app.new((x - z(30), y - z(60)))
            elif self.msg.wParam == 2:
                self.app.toggle()
            else:
                self.app.hub.show()
        self.app.root.after(60, self.poll)


class App:
    def __init__(self):
        global F, FONT
        DIR.mkdir(exist_ok=True)
        aware()
        for ttf in (Path(__file__).parent / "fonts").glob("*.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(str(ttf), 0x10, 0)
        self.root = tk.Tk()
        self.root.withdraw()
        F = self.root.winfo_fpixels("1i") / 96
        have = set(tkfont.families(self.root))
        FONT = next((f for f in ("Inter", "Segoe UI Variable Text") if f in have), FONT)
        data = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
        self.cfg = {**DEFAULTS, **data.get("settings", {})}
        self.state = {k: v for k, v in data.get("notes", {}).items() if (DIR / k).exists()}
        if "dpi" not in self.cfg:
            for v in self.state.values():
                if "geo" in v:
                    v["geo"] = scale_geo(v["geo"], F)
            self.cfg["dpi"] = F
        self.notes, self.sw, self.gw, self.graph, self.seen, self.hidden = [], None, None, {}, {}, False
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

    def open_note(self, path, near=None, heading=""):
        n = next((n for n in self.notes if n.path == path), None)
        if n:
            n.win.lift()
            n.text.focus_force()
        else:
            info = {**self.state.get(path.name, {}), "closed": False}
            if not info.get("geo"):
                if near:
                    x, y = near.win.winfo_x() + near.win.winfo_width() + z(24), near.win.winfo_y()
                else:
                    x = y = z(120 + 30 * len(self.notes))
                info["geo"] = geo(300, 340, x, y)
            self.open(path, info)
            n = self.notes[-1]
        if heading:
            n.goto(heading)

    def open_link(self, name, near, heading=""):
        name = re.sub(r'[:*?"<>|]', "", name).strip()
        if Path(name).suffix.lower() in IMG:
            return self.open_image(name, near)
        name = re.sub(BAD, "", name)
        p = next((p for p in DIR.glob("*.md") if p.stem.lower() == name.lower()), None)
        if p is None:
            p = DIR / f"{name}.md"
            p.write_text(f"# {name}\n", encoding="utf-8")
        self.open_note(p, near, heading)

    def open_image(self, name, near=None):
        p = next((p for p in [DIR / name, *DIR.rglob(Path(name).name)] if p.is_file()), None)
        if p is None:
            return messagebox.showinfo("Image", f"Not found: {name}")
        try:
            View(self, p, near)
        except (tk.TclError, ImportError, OSError) as err:
            messagebox.showerror("Image", f"Cannot open {p.name}: {err}")

    def show_graph(self):
        if self.gw and self.gw.win.winfo_exists():
            self.gw.win.lift()
            return
        self.gw = Graph(self)

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
        x, y = at or (z(120 + 30 * len(self.notes)),) * 2
        info = {"geo": geo(300, 340, max(x, 0), max(y, 0)), "pinned": self.cfg["pinned"], "color": self.cfg["color"]}
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
            return False
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
        return True

    def maybe_quit(self):
        if not self.notes and self.hub.win.state() == "withdrawn":
            self.root.destroy()

    def save(self):
        self.state.update({n.path.name: n.info() for n in self.notes})
        STATE.write_text(json.dumps({"settings": self.cfg, "notes": self.state}), encoding="utf-8")

    def set(self, key, value):
        self.cfg[key] = value
        if key in ("theme", "size", "alpha", "font"):
            for n in self.notes:
                n.apply()
            self.hub.apply()
        if key == "theme" and self.sw and self.sw.winfo_exists():
            g = self.sw.geometry()
            self.root.after(0, lambda: (self.sw.destroy(), self.show_settings(g)))
        self.save()

    def autostart(self, on):
        if on:
            py = Path(sys.executable).with_name("pythonw.exe")
            STARTUP.write_text(f'CreateObject("WScript.Shell").Run """{py}"" ""{Path(__file__).resolve()}""", 0\n')
        else:
            STARTUP.unlink(missing_ok=True)

    def show_settings(self, at=None):
        if self.sw and self.sw.winfo_exists():
            self.sw.lift()
            return
        th = THEMES[self.cfg["theme"]]
        w = self.sw = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.config(bg=th["bg"], highlightthickness=1, highlightbackground=th["edge"])
        w.geometry(at or geo(330, 680, z(150), z(60)))
        w.bind("<Escape>", lambda e: w.destroy())
        head = tk.Frame(w, bg=th["bg"], cursor="fleur")
        head.pack(fill="x", padx=z(6), pady=(z(6), 0))
        ttl = tk.Label(head, text="Settings", bg=th["bg"], fg=th["fg"], font=(FONT, 16, "bold"), anchor="w", padx=z(8))
        ttl.pack(side="left")
        close = hbtn(head, "✕", lambda e: w.destroy(), "Close", 12, True)
        close.config(bg=th["bg"], fg=th["muted"])
        close.pack(side="right")
        movable(w, head, ttl)

        def sec(text):
            tk.Label(w, text=text, bg=th["bg"], fg=th["muted"], font=(FONT, 9), anchor="w").pack(fill="x", padx=z(16), pady=(z(14), z(4)))

        def row():
            r = tk.Frame(w, bg=th["bg"])
            r.pack(anchor="w", padx=z(16))
            return r

        def check(text, key, then=None):
            v = tk.BooleanVar(value=self.cfg[key])
            tk.Checkbutton(w, text=text, variable=v, bg=th["bg"], fg=th["fg"], selectcolor=th["card"], activebackground=th["bg"],
                           activeforeground=th["fg"], highlightthickness=0, bd=0, font=(FONT, 10), anchor="w",
                           command=lambda: (self.set(key, v.get()), then and then(v.get()))).pack(fill="x", padx=z(12), pady=z(2))

        sec("Theme")
        theme = tk.StringVar(value=self.cfg["theme"])
        r = row()
        for v in THEMES:
            tk.Radiobutton(r, text=v.title(), value=v, variable=theme, indicatoron=0, bg=th["card"], fg=th["fg"],
                           selectcolor=tint(th["card"], 0.3), activebackground=tint(th["card"]), activeforeground=th["fg"],
                           relief="flat", bd=0, padx=z(10), pady=z(6), highlightthickness=0, font=(FONT, 10),
                           command=lambda: self.set("theme", theme.get())).pack(side="left", padx=(0, z(5)))
        sec("Default color for new notes")
        rings = {}

        def ring():
            for n, lab in rings.items():
                lab.config(highlightbackground=th["fg"] if n == self.cfg["color"] else th["bg"])

        r = row()
        for name, (hd, _) in COLORS.items():
            lab = tk.Label(r, bg=hd, width=3, height=1, highlightthickness=z(2), highlightbackground=th["bg"], cursor="hand2")
            lab.pack(side="left", padx=z(3))
            lab.bind("<Button-1>", lambda e, n=name: (self.set("color", n), ring()))
            tip(lab, name)
            rings[name] = lab
        ring()
        sec("Note font")
        fams = [f for f in FAMILIES if f in set(tkfont.families(self.root))]
        fv = tk.StringVar(value=self.cfg["font"] or FONT)
        om = tk.OptionMenu(w, fv, *fams, command=lambda v: self.set("font", v))
        om.config(bg=th["card"], fg=th["fg"], activebackground=tint(th["card"]), activeforeground=th["fg"], highlightthickness=0,
                  relief="flat", bd=0, font=(FONT, 10), anchor="w", width=24)
        om["menu"].config(bg=th["card"], fg=th["fg"], activebackground=tint(th["card"]), activeforeground=th["fg"], font=(FONT, 10))
        om.pack(anchor="w", padx=z(16))
        sec("Font size")
        size = tk.StringVar(value=str(self.cfg["size"]))
        tk.Spinbox(w, from_=9, to=24, width=5, textvariable=size, command=lambda: self.set("size", int(size.get())),
                   bg=th["card"], fg=th["fg"], buttonbackground=th["card"], insertbackground=th["fg"], relief="flat",
                   highlightthickness=0, font=(FONT, 10)).pack(anchor="w", padx=z(16))
        sec("Opacity")
        W, pad = z(280), z(10)
        bar = tk.Canvas(w, width=W, height=z(26), bg=th["bg"], highlightthickness=0, cursor="hand2")
        bar.pack(anchor="w", padx=z(16))

        def draw(v):
            x = pad + (W - 2 * pad) * (v - 50) / 50
            bar.delete("all")
            bar.create_line(pad, z(13), W - pad, z(13), width=z(4), fill=th["card"], capstyle="round")
            bar.create_line(pad, z(13), x, z(13), width=z(4), fill=COLORS[self.cfg["color"]][0], capstyle="round")
            bar.create_oval(x - z(8), z(5), x + z(8), z(21), fill=th["fg"], outline="")

        def slide(e):
            v = round(50 + 50 * min(max((e.x - pad) / (W - 2 * pad), 0), 1))
            draw(v)
            self.set("alpha", v)

        bar.bind("<Button-1>", slide)
        bar.bind("<B1-Motion>", slide)
        draw(self.cfg["alpha"])
        tk.Frame(w, bg=th["bg"], height=z(8)).pack()
        check("New notes always on top", "pinned")
        check("Draw arrows between linked notes", "lines")
        check("Copy selected text automatically", "autocopy")
        check("Reveal syntax on the line you edit", "reveal")
        check("Start with Windows", "autostart", self.autostart)
        folder = tk.Label(w, text="Open notes folder", bg=th["card"], fg=th["fg"], font=(FONT, 10), padx=z(14), pady=z(8), cursor="hand2")
        folder.pack(anchor="w", padx=z(16), pady=z(16))
        hover(folder)
        folder.bind("<Button-1>", lambda e: os.startfile(DIR))
        rounded(w)

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
