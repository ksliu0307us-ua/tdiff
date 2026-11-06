import argparse
import os
import sys
from pathlib import Path

from . import render, unified


def read_lines(path, ignore_ws=False, ignore_blank=False):
    if str(path) == "-":
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if ignore_blank:
        lines = [l for l in lines if l.strip()]
    if ignore_ws:
        lines = [" ".join(l.split()) for l in lines]
    return lines


def use_colour(args):
    if args.color == "always":
        return True
    if args.color == "never":
        return False
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def diff_pair(a_path, b_path, args, a_name=None, b_name=None):
    """Print the diff for one pair. Returns True if they differ."""
    a = read_lines(a_path, args.ignore_whitespace, args.ignore_blank)
    b = read_lines(b_path, args.ignore_whitespace, args.ignore_blank)
    a_name = a_name or str(a_path)
    b_name = b_name or str(b_path)
    hs = unified.hunks(a, b, args.context)
    if not hs:
        return False
    if args.stat:
        added, removed = render.stats(a, b)
        print(f"{b_name}: +{added} -{removed}")
    elif args.side_by_side:
        print(render.side_by_side(a, b, use_colour(args), args.width), end="")
    elif args.unified:
        print(unified.format_unified(a, b, a_name, b_name, args.context), end="")
    else:
        print(render.inline(hs, a_name, b_name, use_colour(args), words=not args.no_words), end="")
    return True


def diff_dirs(a_dir, b_dir, args):
    a_files = {str(p.relative_to(a_dir)) for p in a_dir.rglob("*") if p.is_file()}
    b_files = {str(p.relative_to(b_dir)) for p in b_dir.rglob("*") if p.is_file()}
    changed = False
    for rel in sorted(a_files | b_files):
        if rel not in b_files:
            print(f"only in {a_dir}: {rel}")
            changed = True
        elif rel not in a_files:
            print(f"only in {b_dir}: {rel}")
            changed = True
        else:
            if diff_pair(a_dir / rel, b_dir / rel, args, f"a/{rel}", f"b/{rel}"):
                changed = True
    return changed


def cmd_diff(args):
    a, b = Path(args.a), Path(args.b)
    if a.is_dir() and b.is_dir():
        return 1 if diff_dirs(a, b, args) else 0
    if a.is_dir() or b.is_dir():
        print("error: can't compare a folder with a file", file=sys.stderr)
        return 2
    for p in (a, b):
        if str(p) != "-" and not p.exists():
            print(f"error: no such file: {p}", file=sys.stderr)
            return 2
    return 1 if diff_pair(a, b, args) else 0


def cmd_apply(args):
    patch_text = sys.stdin.read() if args.patch == "-" else Path(args.patch).read_text(encoding="utf-8")
    try:
        patches = unified.parse(patch_text)
    except unified.PatchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    status = 0
    for fp in patches:
        # like GNU patch, the file named in the header is the one changed in either direction
        name = fp.a_name if fp.a_name != "/dev/null" else fp.b_name
        target = Path(args.target) if args.target else Path(_strip(name, args.strip))
        if not target.exists():
            print(f"error: no such file: {target}", file=sys.stderr)
            status = 1
            continue
        original = target.read_text(encoding="utf-8").splitlines()
        try:
            new = unified.apply_patch(original, fp.hunks, reverse=args.reverse)
        except unified.PatchError as e:
            print(f"error: {target}: {e}", file=sys.stderr)
            status = 1
            continue
        if args.dry_run:
            print(f"ok: {target} ({len(fp.hunks)} hunk(s) apply cleanly)")
        else:
            target.write_text("\n".join(new) + ("\n" if new else ""), encoding="utf-8")
            print(f"patched {target}")
    return status


def _strip(name, n):
    parts = name.replace("\\", "/").split("/")
    return "/".join(parts[n:]) if n < len(parts) else parts[-1]


def build_parser():
    p = argparse.ArgumentParser(prog="tdiff", description="compare files and folders, make and apply patches")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("diff", help="compare two files or folders (default command)")
    _diff_args(d)
    d.set_defaults(fn=cmd_diff)

    a = sub.add_parser("apply", help="apply a unified diff")
    a.add_argument("patch", help="patch file, or - for stdin")
    a.add_argument("-t", "--target", help="apply to this file instead of the name in the patch")
    a.add_argument("-p", "--strip", type=int, default=0, help="strip N leading path parts (like patch -pN)")
    a.add_argument("-R", "--reverse", action="store_true", help="un-apply the patch")
    a.add_argument("-n", "--dry-run", action="store_true", help="check without writing")
    a.set_defaults(fn=cmd_apply)
    return p


def _diff_args(d):
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("-u", "--unified", action="store_true", help="plain unified diff (what `patch` reads)")
    d.add_argument("-y", "--side-by-side", action="store_true")
    d.add_argument("--stat", action="store_true", help="just counts of added/removed lines")
    d.add_argument("-c", "--context", type=int, default=3, help="context lines (default 3)")
    d.add_argument("-w", "--ignore-whitespace", action="store_true")
    d.add_argument("-B", "--ignore-blank", action="store_true", help="ignore blank lines")
    d.add_argument("--no-words", action="store_true", help="don't highlight changed words within lines")
    d.add_argument("--width", type=int, help="total width for side-by-side (default: terminal)")
    d.add_argument("--color", choices=["auto", "always", "never"], default="auto")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # `tdiff a b` means `tdiff diff a b`
    if argv and argv[0] not in ("diff", "apply", "-h", "--help"):
        argv.insert(0, "diff")
    args = build_parser().parse_args(argv)
    if not getattr(args, "fn", None):
        build_parser().print_help()
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
