#!/usr/bin/env python3
"""Convert the released mask encoding (ten source values, 0-9) to the nine paper
classes (0-8).

The released PNGs store the label ids of the annotation campaign. Two of them
(1 and 4) both denote concrete pavement and are merged, and one (6) is the padding
left by image rotation and rectangular cropping, which becomes class 0. Every other
value shifts.

    source -> paper
    0 -> 5  Bare ground
    1 -> 4  Concrete pavement   \\
    4 -> 4  Concrete pavement   / merged
    2 -> 1  Solidago canadensis
    3 -> 3  Other vegetation
    5 -> 6  Buildings
    6 -> 0  Background (padding from image rotation and rectangular cropping)
    7 -> 2  Discarded construction materials
    8 -> 7  Vehicle roofs
    9 -> 8  Asphalt pavement

Usage
    python convert_masks_10to9.py --src masks/ --dst masks_9class/
    python convert_masks_10to9.py --src masks/ --dst masks_9class/ --report
    python convert_masks_10to9.py --src masks/ --dst masks_9class/ --force

The function convert(array) is importable and works on a numpy uint8 array.

Applying the converter to masks that have already been converted silently corrupts
them (class 0 would become 5, class 6 would become 0, and so on). The script
therefore inspects the source folder first and refuses to run when it looks already
converted; --force overrides that check.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

# source value -> paper class
LUT = np.array([5, 4, 1, 3, 4, 6, 0, 2, 7, 8], dtype=np.uint8)
#                      ^0 ^1 ^2 ^3 ^4 ^5 ^6 ^7 ^8 ^9

CLASS_NAMES = [
    "Background", "Solidago canadensis", "Discarded construction materials",
    "Other vegetation", "Concrete pavement", "Bare ground", "Buildings",
    "Vehicle roofs", "Asphalt pavement",
]

# Class proportions of the complete release, in percent. Same numbers as
# metadata/dataset_statistics.csv and Table 2 of the paper.
REFERENCE_PCT = np.array([0.19, 11.09, 10.02, 29.15, 14.50, 8.07, 19.54, 0.91, 6.52])


def convert(arr):
    """Map a uint8 mask with values 0-9 to the nine paper classes 0-8."""
    arr = np.asarray(arr)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    if not np.issubdtype(arr.dtype, np.integer):
        raise TypeError("mask must be an integer array, got %s" % arr.dtype)
    mx = int(arr.max()) if arr.size else 0
    if mx > 9:
        raise ValueError("unexpected mask value %d (expected 0-9)" % mx)
    return LUT[arr]


def _pct_9class(hist):
    """Class proportions implied by treating values 0-8 as class ids."""
    tot = hist[:9].sum()
    return hist[:9] / tot * 100.0 if tot else np.zeros(9)


def _pct_source(hist):
    """Class proportions implied by treating the values as source codes."""
    cls = np.zeros(9)
    for s in range(10):
        cls[LUT[s]] += hist[s]
    tot = cls.sum()
    return cls / tot * 100.0 if tot else np.zeros(9)


def detect_encoding(hist, tol_pp=2.0):
    """Guess the encoding of a value histogram.

    Returns (label, detail) where label is 'source', '9class' or 'inconclusive'.

    The decision is relative: whichever reading lands closer to the published
    proportions wins, as long as it is at least twice as close as the other. A subset
    of masks deviates from the full-release proportions in absolute terms, so an
    absolute tolerance alone would call a subset inconclusive — and an inconclusive
    folder that is in fact already converted would be converted a second time.
    """
    hist = np.asarray(hist, dtype=np.float64)
    if hist.shape[0] < 10:
        hist = np.concatenate([hist, np.zeros(10 - hist.shape[0])])
    if hist[9] > 0:
        return "source", "value 9 present (asphalt); a converted set cannot contain 9"
    a = _pct_9class(hist)
    b = _pct_source(hist)
    da = float(np.abs(a - REFERENCE_PCT).max())
    db = float(np.abs(b - REFERENCE_PCT).max())
    detail = ("max deviation from reference proportions: "
              "as-9-class %.2f pp, as-source %.2f pp" % (da, db))
    if db < da * 0.5:
        return "source", detail
    if da < db * 0.5 and da <= tol_pp:
        return "9class", detail
    return "inconclusive", detail


def scan(folder, limit=None):
    """Value histogram over every PNG in a folder."""
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    if limit:
        files = files[:limit]
    hist = np.zeros(10, dtype=np.int64)
    for i, f in enumerate(files):
        a = np.asarray(Image.open(os.path.join(folder, f)).convert("L"))
        hist += np.bincount(a.ravel(), minlength=10)[:10]
        if (i + 1) % 1000 == 0:
            print("  scanned %d/%d" % (i + 1, len(files)), flush=True)
    return files, hist


def main():
    ap = argparse.ArgumentParser(
        description="Convert ten-value source masks to the nine paper classes.")
    ap.add_argument("--src", required=True, help="folder of released *_lab.png masks")
    ap.add_argument("--dst", required=True, help="output folder")
    ap.add_argument("--report", action="store_true",
                    help="print the source value histogram before converting")
    ap.add_argument("--force", action="store_true",
                    help="convert even if the source looks already converted")
    ap.add_argument("--limit", type=int, default=None,
                    help="only use the first N files for the encoding check")
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        sys.exit("not a directory: %s" % args.src)

    files, hist = scan(args.src, args.limit)
    if not files:
        sys.exit("no PNG files in %s" % args.src)

    tot = hist.sum()
    print("source folder: %s  (%d PNG, %s px)"
          % (args.src, len(files), format(tot, ",")))
    if args.report:
        print("\n  value   share%   class it maps to")
        for v in range(10):
            if hist[v] == 0 and v < 9:
                continue
            print("  %5d  %7.2f   %s" % (v, 100.0 * hist[v] / tot,
                                         CLASS_NAMES[LUT[v]]))

    label, detail = detect_encoding(hist)
    print("\nencoding check: %s" % label)
    print("  " + detail)

    if label == "9class" and not args.force:
        sys.exit("\nThese masks already look like nine-class ids. Converting them "
                 "would corrupt every label.\nUse --force only if you are certain "
                 "this folder really holds ten-value source masks.")

    if label == "inconclusive" and not args.force:
        sys.exit("\nCannot tell which encoding this folder is in — the proportions "
                 "match neither reading, which happens for small folders and for\n"
                 "patch folders such as corrections/masks_v2/ (3 tiles).\n\n"
                 "Converting a folder that is already in nine-class ids would "
                 "silently corrupt it,\nso conversion is refused. Pass --force once "
                 "you have confirmed the encoding by hand,\nor check a known tile "
                 "with tools/verify_encoding.py first.")

    os.makedirs(args.dst, exist_ok=True)
    n = 0
    for f in files:
        a = np.asarray(Image.open(os.path.join(args.src, f)).convert("L"))
        Image.fromarray(convert(a)).save(os.path.join(args.dst, f))
        n += 1

    print("\nconverted %d masks -> %s" % (n, args.dst))

    _, out_hist = scan(args.dst, None)
    out_pct = _pct_9class(out_hist)
    dev = float(np.abs(out_pct - REFERENCE_PCT).max())
    print("\nresulting class proportions (% of pixels):")
    for c in range(9):
        print("  class %d  %-32s %6.2f   (reference %6.2f)"
              % (c, CLASS_NAMES[c], out_pct[c], REFERENCE_PCT[c]))
    print("\nmax deviation from the reference: %.2f pp" % dev)
    if dev > 1.0:
        print("  note: a full-dataset conversion lands within 0.01 pp. A larger\n"
              "  deviation usually means the folder is a subset, or that a correction\n"
              "  patch was applied to only part of it.")
    else:
        print("  OK")


if __name__ == "__main__":
    main()
