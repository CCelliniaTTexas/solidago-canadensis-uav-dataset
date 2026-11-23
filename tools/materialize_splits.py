#!/usr/bin/env python3
"""Materialise the published split as train / valid / test folders.

The repository ships one flat `data/images` and `data/masks` and the split as stem
lists in `metadata/splits/`. Some training pipelines expect folders instead. This
script builds them without duplicating 97 MB when the filesystem allows it.

Usage
    python materialize_splits.py --data data --out splits
    python materialize_splits.py --data data --out splits --mode copy
    python materialize_splits.py --data data --out splits --mode hardlink

Modes
    auto      symlink, then hardlink, then copy (default)
    symlink   fail if links are not permitted
    hardlink  fail if the output is on another volume
    copy      duplicate the files; largest but always works

Never re-splits anything: the assignment comes from metadata/splits/ unchanged.
"""
import argparse
import filecmp
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def load(stem):
    p = os.path.join(REPO, "metadata", "splits", stem + ".txt")
    if not os.path.exists(p):
        sys.exit("missing split file: %s" % p)
    return [x.strip() for x in open(p, encoding="utf-8") if x.strip()]


def find(d, stem, exts):
    for e in exts:
        p = os.path.join(d, stem + e)
        if os.path.exists(p):
            return p
    return None


def link_or_copy(src, dst, mode):
    if mode in ("auto", "symlink"):
        try:
            os.symlink(os.path.abspath(src), dst)
            return "symlink"
        except (OSError, NotImplementedError):
            if mode == "symlink":
                raise
    if mode in ("auto", "hardlink"):
        try:
            os.link(src, dst)
            return "hardlink"
        except OSError:
            if mode == "hardlink":
                raise
    shutil.copy2(src, dst)
    return "copy"


def main():
    ap = argparse.ArgumentParser(
        description="Build train/valid/test folders from the published split.")
    ap.add_argument("--data", default="data", help="folder holding images/ and masks/")
    ap.add_argument("--out", default="splits", help="output folder")
    ap.add_argument("--mode", choices=["auto", "symlink", "hardlink", "copy"],
                    default="auto")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    images = os.path.join(args.data, "images")
    masks = os.path.join(args.data, "masks")
    for d in (images, masks):
        if not os.path.isdir(d):
            sys.exit("not a directory: %s" % d)

    used = {}
    for split in ("train", "valid", "test"):
        stems = load(split)
        di = os.path.join(args.out, split, "images")
        dm = os.path.join(args.out, split, "masks")
        os.makedirs(di, exist_ok=True)
        os.makedirs(dm, exist_ok=True)
        miss_i = miss_m = 0
        for stem in stems:
            ip = find(images, stem, (".jpg", ".jpeg", ".png"))
            mp = find(masks, stem, ("_lab.png", ".png"))
            if ip is None:
                miss_i += 1
                continue
            if mp is None:
                miss_m += 1
                continue
            how = link_or_copy(ip, os.path.join(di, os.path.basename(ip)), args.mode)
            used[how] = used.get(how, 0) + 1
            how = link_or_copy(mp, os.path.join(dm, os.path.basename(mp)), args.mode)
            used[how] = used.get(how, 0) + 1
        print("%-6s %5d tiles   missing images %d, missing masks %d"
              % (split, len(stems), miss_i, miss_m))

    print("\nlink type used: %s" % ", ".join("%s=%d" % kv for kv in sorted(used.items())))
    print("output: %s" % os.path.abspath(args.out))
    if "copy" in used:
        print("  note: copies were made; the output folder now holds a second "
              "full copy of the data")


if __name__ == "__main__":
    main()
