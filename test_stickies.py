from stickies import (blocks, clean, html_to_md, ink, image_at, link_at, links_of, marks, math_at, matches, next_prefix,
                      offset, spans, title_of, tsv_to_md, unicode_tex, url_at)


def test_tables_and_rules():
    t = "intro\n| a | b |\n| --- | :-: |\n| 1 | 2 |\n\n---\n```\n| x | y |\n| - | - |\n```"
    b = blocks(t)
    assert [(x["kind"], x["a"], x["b"]) for x in b] == [("table", 2, 4), ("hr", 6, 6)]
    assert b[0]["rows"] == [["a", "b"], ["1", "2"]] and b[0]["align"] == ["left", "center"]


def test_links_render():
    t = "see [site](https://a.com/x) and https://b.org/y."
    assert url_at(t, t.index("site")) == "https://a.com/x"
    assert url_at(t, t.index("b.org")) == "https://b.org/y"
    assert url_at(t, 0) is None
    assert (4, 5) in marks(t)
    assert clean("## Hi **there** [a](http://x.y) | b |") == "Hi there a b"


def test_paste_conversion():
    html = "<h2>Title</h2><p>Hello <b>big</b> <a href='http://x.y'>link</a></p><ul><li>one</li><li>two</li></ul>" \
           "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
    md = html_to_md(html)
    assert "## Title" in md and "**big**" in md and "[link](http://x.y)" in md
    assert "- one" in md and "- two" in md
    assert "| A | B |" in md and "| --- | --- |" in md and "| 1 | 2 |" in md
    assert tsv_to_md("a\tb\n1\t2") == "| a | b |\n| --- | --- |\n| 1 | 2 |"
    assert tsv_to_md("plain text") == ""


def test_title_of():
    assert title_of("\n# Buy milk\nfoo") == "Buy milk"
    assert title_of("- [ ] call: bob?") == "call bob"
    assert title_of("# ") == ""


def test_spans():
    t = "# hi\n**b** and *i* and `c`\n- [x] done\n[[link]]\n~~s~~"
    assert {s[0] for s in spans(t)} == {"h1", "bold", "it", "code", "done", "link", "strike", "bullet"}
    assert ("bold", 5, 10) in spans(t)
    assert ("tag", 4, 9) in spans("see #todo")
    assert not [s for s in spans("# title") if s[0] == "tag"]


def test_new_markdown():
    t = "---\ntitle: x\n---\n> quote\n> [!warning] careful\n| a | b |\n==hi==\n$x^2$\n```\n# not a heading\n```\n![pic](a.png)"
    tags = {s[0] for s in spans(t)}
    assert {"meta", "quote", "co-note", "co-warning", "table", "mark", "math", "fence", "img"} <= tags
    assert "h1" not in tags
    assert (len("---\ntitle: x\n---\n"), len("---\ntitle: x\n---\n") + 2) in marks(t)


def test_next_prefix():
    assert next_prefix("- [x] a") == "- [ ] "
    assert next_prefix("  - a") == "  - "
    assert next_prefix("3. a") == "4. "
    assert next_prefix("> q") == "> "
    assert next_prefix("plain") is None


def test_ink():
    assert ink("#ffffff") == "#111111"
    assert ink("#000000") == "#ffffff"


def test_links():
    t = "see [[Foo]] and [[Bar|b]] and [[Baz#Head]]"
    assert links_of(t) == {"foo", "bar", "baz"}
    assert link_at(t, t.index("Foo")) == ("Foo", "")
    assert link_at(t, t.index("Baz")) == ("Baz", "Head")
    assert link_at(t, 0) is None
    assert image_at("x ![p](a/b.png) y", 5) == "a/b.png"


def test_marks_and_offset():
    t = "# hi\n**b**"
    assert {(0, 2), (5, 7), (8, 10)} <= set(marks(t))
    assert offset("ab\ncd", "2.1") == 4


def test_math_and_search():
    t = "cost $5 and $x^2$ ok"
    assert math_at(t, t.index("x^2")) == "x^2"
    assert math_at(t, 0) is None
    assert unicode_tex(r"\alpha^2 + \frac{a}{b}") == "α² + (a)/(b)"
    assert matches("Shop", "milk #todo", "tag:todo milk")
    assert not matches("Shop", "milk #todo", "milk -todo")
    assert matches("Shop", "milk", "title:sho")
