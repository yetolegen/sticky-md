from stickies import ink, link_at, links_of, marks, next_prefix, offset, spans, title_of


def test_title_of():
    assert title_of("\n# Buy milk\nfoo") == "Buy milk"
    assert title_of("- [ ] call: bob?") == "call bob"
    assert title_of("# ") == ""


def test_spans():
    t = "# hi\n**b** and *i* and `c`\n- [x] done\n[[link]]\n~~s~~"
    assert {s[0] for s in spans(t)} == {"h1", "bold", "it", "code", "done", "link", "strike"}
    assert ("bold", 5, 10) in spans(t)
    assert ("tag", 4, 9) in spans("see #todo")
    assert not [s for s in spans("# title") if s[0] == "tag"]


def test_next_prefix():
    assert next_prefix("- [x] a") == "- [ ] "
    assert next_prefix("  - a") == "  - "
    assert next_prefix("plain") is None


def test_ink():
    assert ink("#ffffff") == "#111111"
    assert ink("#000000") == "#ffffff"


def test_links():
    t = "see [[Foo]] and [[Bar|b]] and [[Baz#h]]"
    assert links_of(t) == {"foo", "bar", "baz"}
    assert link_at(t, t.index("Foo")) == "Foo"
    assert link_at(t, 0) is None


def test_marks_and_offset():
    t = "# hi\n**b**"
    assert {(0, 2), (5, 7), (8, 10)} <= set(marks(t))
    assert offset("ab\ncd", "2.1") == 4
