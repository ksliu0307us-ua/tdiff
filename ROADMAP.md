# Roadmap

Roughly in order. Open an issue if you want one sooner.

## Soon

- [ ] Fuzzy apply: match hunks with an offset, and with reduced context (`--fuzz 2`), like `patch` does
- [ ] "\ No newline at end of file" handling in both output and apply
- [ ] Multi-file patches from folder diffs (`tdiff -u dir1 dir2 > all.diff`, `tdiff apply all.diff -p1`)
- [ ] Character-level highlights inside changed words when the words are long (`--chars`)
- [ ] Binary file detection: say "binary files differ" instead of printing garbage
- [ ] `--ignore-case` and `--ignore-matching-lines REGEX`

## Next

- [ ] Smarter line matching: pair a deleted and an added line by similarity before word-diffing, so a changed line next to an unrelated insert doesn't get mis-paired
- [ ] Move detection: mark a block that was deleted in one place and added in another
- [ ] Syntax-aware word splitting for code (treat `foo.bar(` sensibly)
- [ ] Three-way merge: `tdiff merge base ours theirs` with conflict markers
- [ ] HTML output for sharing a diff
- [ ] Patience / histogram diff as alternative algorithms for nicer output on reordered code

## Later / maybe

- [ ] Interactive hunk selection for `apply` (`-i`), like `git add -p`
- [ ] A pager mode that folds unchanged regions
- [ ] Publish to PyPI

## Housekeeping

- [ ] Benchmarks on large files; the trace array in Myers is O(D²) memory and could use the linear-space refinement
- [ ] GitHub Actions running `pytest` on Linux, macOS and Windows (CRLF handling)
- [ ] Type hints and a `mypy` pass
- [ ] CHANGELOG.md starting at 0.2.0
