"""Myers' O(ND) diff: the shortest edit script between two sequences.

`diff(a, b)` returns a list of (op, a_index, b_index) with op one of
"=" (same element at a[i] and b[j]), "-" (a[i] deleted), "+" (b[j] inserted).
Works on any sequences with hashable elements: lines, words, characters.

The common prefix and suffix are stripped first because that's cheap and it
makes the quadratic-worst-case part run on the smallest possible middle.
"""


def _middle(a, b):
    n, m = len(a), len(b)
    if n == 0:
        return [("+", 0, j) for j in range(m)]
    if m == 0:
        return [("-", i, 0) for i in range(n)]

    max_d = n + m
    offset = max_d
    v = [0] * (2 * max_d + 2)
    trace = []

    for d in range(max_d + 1):
        trace.append(list(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v[offset + k - 1] < v[offset + k + 1]):
                x = v[offset + k + 1]  # move down (insert)
            else:
                x = v[offset + k - 1] + 1  # move right (delete)
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[offset + k] = x
            if x >= n and y >= m:
                return _backtrack(trace, a, b, offset)
    raise RuntimeError("unreachable")


def _backtrack(trace, a, b, offset):
    x, y = len(a), len(b)
    ops = []
    for d in range(len(trace) - 1, -1, -1):
        v = trace[d]
        k = x - y
        if k == -d or (k != d and v[offset + k - 1] < v[offset + k + 1]):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v[offset + prev_k]
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            ops.append(("=", x, y))
        if d > 0:
            if x == prev_x:
                y -= 1
                ops.append(("+", x, y))
            else:
                x -= 1
                ops.append(("-", x, y))
    ops.reverse()
    return ops


def diff(a, b):
    a = list(a)
    b = list(b)
    # strip common prefix / suffix
    start = 0
    while start < len(a) and start < len(b) and a[start] == b[start]:
        start += 1
    end_a, end_b = len(a), len(b)
    while end_a > start and end_b > start and a[end_a - 1] == b[end_b - 1]:
        end_a -= 1
        end_b -= 1

    ops = [("=", i, i) for i in range(start)]
    middle = _middle(a[start:end_a], b[start:end_b])
    ops += [(op, i + start, j + start) for op, i, j in middle]
    tail = len(a) - end_a
    ops += [("=", end_a + t, end_b + t) for t in range(tail)]
    return ops


def apply_ops(a, b, ops):
    """Rebuild b from a and the ops (used in tests to prove the script is valid)."""
    out = []
    for op, i, j in ops:
        if op == "=":
            assert a[i] == b[j]
            out.append(a[i])
        elif op == "+":
            out.append(b[j])
    return out
