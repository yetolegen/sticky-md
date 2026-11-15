from stickies import ink, next_prefix, spans


def test_spans():
    t = "# hi\n**b** and *i* and `c`\n- [x] done\n[[link]]\n~~s~~"
    assert {s[0] for s in spans(t)} == {"h1", "bold", "it", "code", "done", "link", "strike"}
    assert ("bold", 5, 10) in spans(t)


def test_next_prefix():
    assert next_prefix("- [x] a") == "- [ ] "
    assert next_prefix("  - a") == "  - "
    assert next_prefix("plain") is None


def test_ink():
    assert ink("#ffffff") == "#111111"
    assert ink("#000000") == "#ffffff"
