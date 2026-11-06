"""Human-facing output: coloured inline diff with word highlights, and side by side."""

import re
import shutil

from . import myers

RED = "\x1b[31m"
GREEN = "\x1b[32m"
CYAN = "\x1b[36m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
REV = "\x1b[7m"
RESET = "\x1b[0m"

_WORDS = re.compile(r"\w+|\s+|[^\w\s]")


def _c(text, code, colour):
    return f"{code}{text}{RESET}" if colour else text


def word_diff(old, new, colour=True):
    """Return (old_marked, new_marked) with changed words highlighted."""
    a = _WORDS.findall(old)
    b = _WORDS.findall(new)
    ops = myers.diff(a, b)
    old_out, new_out = [], []
    for op, i, j in ops:
        if op == "=":
            old_out.append(a[i])
            new_out.append(b[j])
        elif op == "-":
            old_out.append(_c(a[i], REV, colour))
        else:
            new_out.append(_c(b[j], REV, colour))
    return "".join(old_out), "".join(new_out)


def _pair_changes(lines):
    """Within a hunk, pair up runs of -/+ lines so words can be compared."""
    out = []
    i = 0
    while i < len(lines):
        if lines[i][0] == "-":
            minus = []
            while i < len(lines) and lines[i][0] == "-":
                minus.append(lines[i][1]); i += 1
            plus = []
            while i < len(lines) and lines[i][0] == "+":
                plus.append(lines[i][1]); i += 1
            out.append(("change", minus, plus))
        elif lines[i][0] == "+":
            plus = []
            while i < len(lines) and lines[i][0] == "+":
                plus.append(lines[i][1]); i += 1
            out.append(("change", [], plus))
        else:
            out.append(("same", [lines[i][1]], []))
            i += 1
    return out


def inline(hunks, a_name, b_name, colour=True, words=True):
    out = [_c(f"--- {a_name}", BOLD, colour), _c(f"+++ {b_name}", BOLD, colour)]
    for h in hunks:
        out.append(_c(h.header(), CYAN, colour))
        for kind, minus, plus in _pair_changes(h.lines):
            if kind == "same":
                out.append(" " + minus[0])
                continue
            if words and len(minus) == len(plus) and minus:
                for o, n in zip(minus, plus):
                    om, nm = word_diff(o, n, colour)
                    out.append(_c("-", RED, colour) + _c(om, RED, colour))
                    out.append(_c("+", GREEN, colour) + _c(nm, GREEN, colour))
            else:
                for o in minus:
                    out.append(_c("-" + o, RED, colour))
                for n in plus:
                    out.append(_c("+" + n, GREEN, colour))
    return "\n".join(out) + "\n"


def _visible_len(s):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))


def _pad(s, width):
    vis = _visible_len(s)
    if vis > width:
        # cut by visible characters, keeping escapes
        out, count = [], 0
        for tok in re.split(r"(\x1b\[[0-9;]*m)", s):
            if tok.startswith("\x1b"):
                out.append(tok)
            else:
                take = tok[: max(0, width - 1 - count)]
                out.append(take)
                count += len(take)
        return "".join(out) + "…" + (RESET if "\x1b" in s else "")
    return s + " " * (width - vis)


def side_by_side(a_lines, b_lines, colour=True, width=None):
    width = width or shutil.get_terminal_size((120, 20)).columns
    col = max(10, (width - 3) // 2)
    ops = myers.diff(a_lines, b_lines)
    rows = []
    ai = bi = 0
    pending_minus = []
    for op, i, j in ops:
        if op == "-":
            pending_minus.append(i)
            continue
        if op == "+":
            if pending_minus:
                k = pending_minus.pop(0)
                left = _c(a_lines[k], RED, colour)
                right = _c(b_lines[j], GREEN, colour)
                rows.append((f"{k + 1:>4} {left}", f"{j + 1:>4} {right}", "|"))
            else:
                rows.append(("", f"{j + 1:>4} " + _c(b_lines[j], GREEN, colour), ">"))
            continue
        for k in pending_minus:
            rows.append((f"{k + 1:>4} " + _c(a_lines[k], RED, colour), "", "<"))
        pending_minus = []
        rows.append((f"{i + 1:>4} {a_lines[i]}", f"{j + 1:>4} {b_lines[j]}", " "))
    for k in pending_minus:
        rows.append((f"{k + 1:>4} " + _c(a_lines[k], RED, colour), "", "<"))
    return "\n".join(f"{_pad(l, col)} {_c(m, BOLD, colour) if m != ' ' else m} {_pad(r, col).rstrip()}" for l, r, m in rows) + "\n"


def stats(a_lines, b_lines):
    ops = myers.diff(a_lines, b_lines)
    added = sum(1 for op, _, _ in ops if op == "+")
    removed = sum(1 for op, _, _ in ops if op == "-")
    return added, removed
