# tdiff

A diff tool for the terminal: coloured output with the changed *words*
highlighted, a side-by-side view, folder comparison, plain unified diffs
that `patch` and `git apply` accept, and its own `apply` command.

```
$ tdiff old.py new.py
--- old.py
+++ new.py
@@ -12,7 +12,7 @@
     if not path.exists():
-        raise ValueError("missing file")        ← "ValueError" highlighted
+        raise FileNotFoundError("missing file") ← "FileNotFoundError" highlighted
     return path.read_text()

$ tdiff -y old.py new.py          # side by side
$ tdiff -u old.py new.py > fix.diff
$ tdiff apply fix.diff
```

I wanted `git diff --word-diff` for files that aren't in git, and a diff I
could read on a phone over SSH. Writing the algorithm was the fun part.

## Who it's for

Me, comparing config files and exports that never see version control.
Anyone who wants a readable diff without installing a GUI, or who wants a
small, complete implementation of Myers' algorithm to read.

## Built with

- Python 3.9+, standard library only.
- `pytest` for the tests. One test shells out to GNU `patch` if it's
  installed, to prove the unified output is the real thing.

## Install

```sh
git clone https://github.com/ksliu0307us-ua/tdiff.git
cd tdiff
pip install -e .
```

Or run it without installing: `python -m tdiff.cli ...`.

## Usage

```sh
tdiff a.txt b.txt                 # inline, coloured, word highlights
tdiff -y a.txt b.txt              # side by side, numbered, | < > markers
tdiff -u a.txt b.txt              # plain unified diff for patch/git/email
tdiff --stat a.txt b.txt          # just "+3 -2"
tdiff dir1/ dir2/                 # every file, recursively; lists files only on one side
tdiff -w a.txt b.txt              # ignore whitespace differences
tdiff -B a.txt b.txt              # ignore blank lines
tdiff -c 5 a.txt b.txt            # more context
tdiff --no-words a.txt b.txt      # whole-line colouring only
tdiff --color never a.txt b.txt   # or set NO_COLOR; auto-detects a pipe
cat x | tdiff - b.txt             # stdin on either side

tdiff apply fix.diff              # patch the file named in the diff
tdiff apply fix.diff -t other.txt # ...or this file instead
tdiff apply fix.diff -p1          # strip a/ b/ prefixes like patch -p1
tdiff apply fix.diff -R           # un-apply
tdiff apply fix.diff -n           # dry run: say whether it would apply cleanly
```

Exit codes follow `diff`: 0 identical, 1 different, 2 error.

## How it works

- `tdiff/myers.py` is Myers' O(ND) shortest-edit-script algorithm with the
  usual common-prefix/suffix trim. It works on any sequence, so the same
  code diffs lines for the hunks and words for the highlights.
- `tdiff/unified.py` groups the edit script into hunks with context, writes
  the unified format, parses it back, and applies it (forwards or in
  reverse) with exact-context matching. No fuzz yet; see the roadmap.
- `tdiff/render.py` does the colouring and the side-by-side layout.

The tests generate hundreds of random edits and check that `a → diff →
apply` gives back `b` exactly at every context size, and that GNU `patch`
agrees.

## Running the tests

```sh
pip install pytest
pytest
```

## Roadmap

See [ROADMAP.md](ROADMAP.md). Issues and PRs welcome.

## License

MIT. See [LICENSE](LICENSE).
