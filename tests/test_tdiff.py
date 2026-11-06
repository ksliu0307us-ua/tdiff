import random
import shutil
import subprocess

import pytest

from tdiff import myers, render, unified
from tdiff.cli import main


# --- myers -------------------------------------------------------------------------

def test_basic_scripts():
    assert myers.diff("abc", "abc") == [("=", 0, 0), ("=", 1, 1), ("=", 2, 2)]
    assert myers.diff("", "ab") == [("+", 0, 0), ("+", 0, 1)]
    assert myers.diff("ab", "") == [("-", 0, 0), ("-", 1, 0)]
    ops = myers.diff("abcabba", "cbabac")  # the example from Myers' paper: distance 5
    assert sum(1 for op, _, _ in ops if op != "=") == 5


def test_random_scripts_are_valid():
    rng = random.Random(1)
    for _ in range(300):
        a = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
        b = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
        assert myers.apply_ops(a, b, myers.diff(a, b)) == b


def test_prefix_suffix_fast_path():
    a = ["same"] * 1000 + ["x"] + ["same"] * 1000
    b = ["same"] * 1000 + ["y"] + ["same"] * 1000
    ops = [o for o in myers.diff(a, b) if o[0] != "="]
    assert ops == [("-", 1000, 1000), ("+", 1001, 1000)]


# --- unified -----------------------------------------------------------------------

A = ["one", "two", "three", "four", "five", "six", "seven"]
B = ["one", "2", "three", "four", "five five", "six", "seven", "eight"]


def test_format_unified():
    text = unified.format_unified(A, B, "a.txt", "b.txt")
    assert text.splitlines()[:3] == ["--- a.txt", "+++ b.txt", "@@ -1,7 +1,8 @@"]
    assert "-two" in text and "+2" in text and "+eight" in text


def test_identical_is_empty():
    assert unified.format_unified(A, A) == ""
    assert unified.hunks(A, A) == []


def test_hunks_split_when_far_apart():
    a = [str(i) for i in range(40)]
    b = list(a)
    b[2] = "x"
    b[30] = "y"
    hs = unified.hunks(a, b, context=3)
    assert len(hs) == 2
    assert hs[0].header() == "@@ -1,6 +1,6 @@"
    assert hs[1].header() == "@@ -28,7 +28,7 @@"


def test_zero_context_insertion_header():
    hs = unified.hunks(["a", "b"], ["a", "x", "b"], context=0)
    assert [h.header() for h in hs] == ["@@ -1,0 +2 @@"]
    hs = unified.hunks(["a", "b"], ["x", "a", "b"], context=0)
    assert [h.header() for h in hs] == ["@@ -0,0 +1 @@"]


def test_parse_and_apply_roundtrip():
    text = unified.format_unified(A, B, "a", "b")
    patches = unified.parse(text)
    assert patches[0].a_name == "a" and patches[0].b_name == "b"
    assert unified.apply_patch(A, patches[0].hunks) == B
    assert unified.apply_patch(B, patches[0].hunks, reverse=True) == A


def test_apply_rejects_bad_context():
    text = unified.format_unified(A, B)
    hs = unified.parse(text)[0].hunks
    with pytest.raises(unified.PatchError, match="does not match"):
        unified.apply_patch(["totally", "different"], hs)


def test_parse_errors():
    with pytest.raises(unified.PatchError):
        unified.parse("not a patch")
    with pytest.raises(unified.PatchError):
        unified.parse("--- a\n+++ b\n@@ nonsense @@\n")


def test_random_roundtrips_all_contexts():
    rng = random.Random(2)
    for _ in range(150):
        a = [rng.choice("pqrs") + str(rng.randint(0, 2)) for _ in range(rng.randint(0, 15))]
        b = list(a)
        for _ in range(rng.randint(1, 5)):
            r = rng.random()
            if r < 0.4 and b:
                b.pop(rng.randrange(len(b)))
            elif r < 0.8:
                b.insert(rng.randint(0, len(b)), "new")
            elif b:
                b[rng.randrange(len(b))] = "chg"
        for ctx in (0, 1, 3):
            text = unified.format_unified(a, b, context=ctx)
            if not text:
                assert a == b
                continue
            hs = unified.parse(text)[0].hunks
            assert unified.apply_patch(a, hs) == b
            assert unified.apply_patch(b, hs, reverse=True) == a


@pytest.mark.skipif(shutil.which("patch") is None, reason="GNU patch not installed")
def test_gnu_patch_accepts_our_output(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("\n".join(A) + "\n")
    text = unified.format_unified(A, B, "a.txt", "a.txt")
    r = subprocess.run(["patch", "-s", str(f)], input=text, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert f.read_text().splitlines() == B


# --- render ------------------------------------------------------------------------

def test_word_diff_marks_only_changed_words():
    old, new = render.word_diff("the quick brown fox", "the slow brown fox", colour=True)
    assert "\x1b[7mquick\x1b[0m" in old and "\x1b[7mslow\x1b[0m" in new
    assert "\x1b[7mbrown" not in new


def test_inline_and_side_by_side_plain():
    hs = unified.hunks(A, B)
    text = render.inline(hs, "a", "b", colour=False)
    assert "-two" in text and "+2" in text
    sbs = render.side_by_side(A, B, colour=False, width=60)
    rows = sbs.splitlines()
    assert any("|" in r and "two" in r and "2" in r for r in rows)
    assert any(r.strip().startswith(">") for r in rows)  # the added "eight"


def test_stats():
    assert render.stats(A, B) == (3, 2)


# --- cli -----------------------------------------------------------------------------

def test_cli_diff_exit_codes_and_unified(tmp_path, capsys):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("\n".join(A) + "\n")
    b.write_text("\n".join(B) + "\n")
    assert main([str(a), str(a)]) == 0
    assert main(["-u", str(a), str(b), "--color", "never"]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"--- {a}\n+++ {b}\n@@")
    assert main([str(a), str(tmp_path / "missing")]) == 2


def test_cli_apply_and_reverse(tmp_path, capsys):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("\n".join(A) + "\n")
    b.write_text("\n".join(B) + "\n")
    main(["-u", str(a), str(b), "--color", "never"])
    patch = tmp_path / "p.diff"
    patch.write_text(capsys.readouterr().out)
    assert main(["apply", str(patch), "-n"]) == 0
    assert a.read_text().splitlines() == A  # dry run changed nothing
    assert main(["apply", str(patch)]) == 0
    assert a.read_text().splitlines() == B
    assert main(["apply", str(patch), "-R"]) == 0
    assert a.read_text().splitlines() == A


def test_cli_dirs(tmp_path, capsys):
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    (tmp_path / "x" / "same.txt").write_text("s\n")
    (tmp_path / "y" / "same.txt").write_text("s\n")
    (tmp_path / "x" / "only.txt").write_text("o\n")
    (tmp_path / "x" / "ch.txt").write_text("1\n2\n")
    (tmp_path / "y" / "ch.txt").write_text("1\n3\n")
    assert main([str(tmp_path / "x"), str(tmp_path / "y"), "--stat"]) == 1
    out = capsys.readouterr().out
    assert "only in" in out and "only.txt" in out
    assert "b/ch.txt: +1 -1" in out
    assert "same.txt" not in out.replace("only.txt", "")
