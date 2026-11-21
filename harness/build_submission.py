"""Pack `solvers/` into the archive a Main-track submission uses.

    python harness/build_submission.py [--out submission.zip]

Layout follows the submission format: one folder per problem slug, one entry
point `solve.py` directly inside it, every folder self-contained (the shared
`common/orlib.py` is copied in). Zip is written deterministically (sorted names,
fixed timestamps) so the same sources always give the same bytes.
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOLVERS = os.path.join(ROOT, "solvers")
COMMON = os.path.join(ROOT, "common", "orlib.py")
DEFAULT_OUT = os.path.join(ROOT, "submission.zip")


def stage(target: str) -> list[str]:
    """Copy every solver folder plus the shared helpers into `target`."""
    slugs = sorted(d for d in os.listdir(SOLVERS) if os.path.isdir(os.path.join(SOLVERS, d)))
    for slug in slugs:
        src = os.path.join(SOLVERS, slug)
        dst = os.path.join(target, slug)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "runs"))
        shutil.copy2(COMMON, os.path.join(dst, "orlib.py"))
    return slugs


def archive_size() -> int:
    """Size in bytes of the archive a submission would upload."""
    tmp = tempfile.mkdtemp(prefix="fo-pack-")
    try:
        stage(tmp)
        out = os.path.join(tmp, "..", os.path.basename(tmp) + ".zip")
        write_zip(tmp, out)
        size = os.path.getsize(out)
        os.unlink(out)
        return size
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write_zip(source: str, out: str) -> None:
    names: list[tuple[str, str]] = []
    for base, _dirs, files in os.walk(source):
        for name in files:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, source).replace(os.sep, "/")
            names.append((rel, full))
    names.sort()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel, full in names:
            info = zipfile.ZipInfo(rel, date_time=(2027, 1, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, "rb") as fh:
                zf.writestr(info, fh.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="fo-pack-")
    try:
        slugs = stage(tmp)
        write_zip(tmp, args.out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    size = os.path.getsize(args.out)
    print(f"{args.out}: {size/1024:.1f} KiB, {len(slugs)} problem folders ({', '.join(slugs)})")
    return 0 if size <= 4 * 1024 * 1024 else 1


if __name__ == "__main__":
    raise SystemExit(main())
