"""Unified diff format: build it, parse it, apply it.

The format `patch` and `git apply` read:

    --- a/file
    +++ b/file
    @@ -start,count +start,count @@
     context line
    -removed line
    +added line
"""

from dataclasses import dataclass, field

from . import myers


class PatchError(Exception):
    pass


@dataclass
class Hunk:
    a_start: int  # 1-based
    a_count: int
    b_start: int
    b_count: int
    lines: list = field(default_factory=list)  # ("=", text) / ("-", text) / ("+", text)

    def header(self):
        def rng(start, count):
            # count 0: `start` is the line after which the change goes (0 = top)
            return str(start) if count == 1 else f"{start},{count}"

        return f"@@ -{rng(self.a_start, self.a_count)} +{rng(self.b_start, self.b_count)} @@"


def hunks(a_lines, b_lines, context=3):
    """Group a Myers edit script into hunks with `context` lines around changes."""
    ops = myers.diff(a_lines, b_lines)
    if all(op == "=" for op, _, _ in ops):
        return []

    change_idx = [k for k, (op, _, _) in enumerate(ops) if op != "="]
    groups = []
    start = change_idx[0]
    prev = start
    for k in change_idx[1:]:
        if k - prev > 2 * context:
            groups.append((start, prev))
            start = k
        prev = k
    groups.append((start, prev))

    out = []
    for first, last in groups:
        lo = max(0, first - context)
        hi = min(len(ops), last + context + 1)
        chunk = ops[lo:hi]
        a_idx = [i for op, i, _ in chunk if op != "+"]
        b_idx = [j for op, _, j in chunk if op != "-"]
        a_count = len(a_idx)
        b_count = len(b_idx)
        # non-empty range: first line, 1-based. empty range: the line it goes after.
        a_start = a_idx[0] + 1 if a_idx else chunk[0][1]
        b_start = b_idx[0] + 1 if b_idx else chunk[0][2]
        lines = []
        for op, i, j in chunk:
            lines.append((op, a_lines[i] if op != "+" else b_lines[j]))
        out.append(Hunk(a_start, a_count, b_start, b_count, lines))
    return out


def format_unified(a_lines, b_lines, a_name="a", b_name="b", context=3):
    hs = hunks(a_lines, b_lines, context)
    if not hs:
        return ""
    out = [f"--- {a_name}", f"+++ {b_name}"]
    for h in hs:
        out.append(h.header())
        for op, text in h.lines:
            prefix = {"=": " ", "-": "-", "+": "+"}[op]
            out.append(prefix + text)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- parsing

@dataclass
class FilePatch:
    a_name: str
    b_name: str
    hunks: list


def parse(text):
    """Parse one or more file patches out of unified diff text."""
    lines = text.splitlines()
    patches = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("--- "):
            i += 1
            continue
        a_name = lines[i][4:].split("\t")[0]
        i += 1
        if i >= len(lines) or not lines[i].startswith("+++ "):
            raise PatchError(f"expected +++ after --- near line {i}")
        b_name = lines[i][4:].split("\t")[0]
        i += 1
        hs = []
        while i < len(lines) and lines[i].startswith("@@"):
            hdr = lines[i]
            try:
                parts = hdr.split("@@")[1].strip().split()
                a_part, b_part = parts[0][1:], parts[1][1:]
                a_start, a_count = _range(a_part)
                b_start, b_count = _range(b_part)
            except (IndexError, ValueError):
                raise PatchError(f"bad hunk header: {hdr}")
            i += 1
            h = Hunk(a_start, a_count, b_start, b_count)
            seen_a = seen_b = 0
            while i < len(lines) and (seen_a < a_count or seen_b < b_count):
                ln = lines[i]
                if ln.startswith("\\"):  # "\ No newline at end of file"
                    i += 1
                    continue
                tag, body = (ln[0], ln[1:]) if ln else (" ", "")
                if tag == " ":
                    h.lines.append(("=", body)); seen_a += 1; seen_b += 1
                elif tag == "-":
                    h.lines.append(("-", body)); seen_a += 1
                elif tag == "+":
                    h.lines.append(("+", body)); seen_b += 1
                else:
                    raise PatchError(f"unexpected line in hunk: {ln!r}")
                i += 1
            hs.append(h)
        patches.append(FilePatch(a_name, b_name, hs))
    if not patches:
        raise PatchError("no patches found")
    return patches


def _range(s):
    if "," in s:
        start, count = s.split(",")
        return int(start), int(count)
    return int(s), 1


# ---------------------------------------------------------------- applying

def apply_patch(a_lines, hs, reverse=False):
    """Apply hunks to a list of lines. Raises PatchError if context doesn't match."""
    out = []
    pos = 0  # index into a_lines
    for n, h in enumerate(hs, 1):
        if reverse:
            h = Hunk(h.b_start, h.b_count, h.a_start, h.a_count,
                     [({"-": "+", "+": "-", "=": "="}[op], t) for op, t in h.lines])
        start = h.a_start - 1 if h.a_count else h.a_start
        if start < pos or start > len(a_lines):
            raise PatchError(f"hunk {n} out of range")
        out.extend(a_lines[pos:start])
        pos = start
        for op, text in h.lines:
            if op == "+":
                out.append(text)
            else:
                if pos >= len(a_lines) or a_lines[pos] != text:
                    got = a_lines[pos] if pos < len(a_lines) else "<end of file>"
                    raise PatchError(f"hunk {n} does not match at line {pos + 1}: expected {text!r}, found {got!r}")
                if op == "=":
                    out.append(text)
                pos += 1
    out.extend(a_lines[pos:])
    return out
