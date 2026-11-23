#!/usr/bin/env python3
"""Report the encoding of a mask folder and its class proportions.

The released masks use ten source values (0-9) that are not the nine paper class
ids. Getting this wrong is silent: a mask that is 48 % byte 6 is background, not
buildings, and nothing will complain. This script tells you which encoding a folder
is in, and how far its class proportions are from the published ones, so that a
broken pipeline fails here rather than after a training run.

Usage
    python verify_encoding.py --masks path/to/masks
    python verify_encoding.py --masks path/to/masks --expect 9class
    python verify_encoding.py --masks path/to/masks --expect source --quiet

Exit status is 0 when the expectation holds (or none was given) and 1 otherwise,
so it can be used as a pipeline gate.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

LUT = np.array([5, 4, 1, 3, 4, 6, 0, 2, 7, 8], dtype=np.uint8)
CLASS_NAMES = [
    "Background", "Solidago canadensis", "Discarded construction materials",
    "Other vegetation", "Concrete pavement", "Bare ground", "Buildings",
    "Vehicle roofs", "Asphalt pavement",
]
# Complete-release proportions, percent. metadata/dataset_statistics.csv
REFERENCE_PCT = np.array([0.19, 11.09, 10.02, 29.15, 14.50, 8.07, 19.54, 0.91, 6.52])


def pct_9class(hist):
    tot = hist[:9].sum()
    return hist[:9] / tot * 100.0 if tot else np.zeros(9)


def pct_source(hist):
    cls = np.zeros(9)
    for s in range(10):
        cls[LUT[s]] += hist[s]
    tot = cls.sum()
    return cls / tot * 100.0 if tot else np.zeros(9)


def main():
    ap = argparse.ArgumentParser(
        description="Report the encoding of a mask folder and its class proportions.")
    ap.add_argument("--masks", required=True, help="folder of PNG masks")
    ap.add_argument("--expect", choices=["source", "9class"], default=None,
                    help="fail if the detected encoding differs")
    ap.add_argument("--tol", type=float, default=2.0,
                    help="max deviation in percentage points still treated as a "
                         "match (default 2.0; use 0.05 for the complete release)")
    ap.add_argument("--limit", type=int, default=None,
                    help="scan only the first N masks (default: all)")
    ap.add_argument("--quiet", action="store_true", help="only print the verdict")
    args = ap.parse_args()

    if not os.path.isdir(args.masks):
        sys.exit("not a directory: %s" % args.masks)

    files = sorted(f for f in os.listdir(args.masks) if f.lower().endswith(".png"))
    if args.limit:
        files = files[:args.limit]
    if not files:
        sys.exit("no PNG files in %s" % args.masks)

    hist = np.zeros(10, dtype=np.int64)
    for i, f in enumerate(files):
        a = np.asarray(Image.open(os.path.join(args.masks, f)).convert("L"))
        hist += np.bincount(a.ravel(), minlength=10)[:10]
        if not args.quiet and (i + 1) % 2000 == 0:
            print("  scanned %d/%d" % (i + 1, len(files)), flush=True)

    tot = int(hist.sum())
    if not args.quiet:
        print("folder : %s" % args.masks)
        print("masks  : %d   pixels: %s   size: %s"
              % (len(files), format(tot, ","),
                 "x".join(str(v) for v in Image.open(
                     os.path.join(args.masks, files[0])).size)))
        print("\nvalue histogram")
        print("  value   pixels        share%")
        for v in range(10):
            if hist[v] == 0:
                continue
            print("  %5d   %-12s %6.3f" % (v, format(int(hist[v]), ","),
                                           100.0 * hist[v] / tot))

    a = pct_9class(hist)
    b = pct_source(hist)
    da = float(np.abs(a - REFERENCE_PCT).max())
    db = float(np.abs(b - REFERENCE_PCT).max())

    if args.quiet:
        print("")
    print("-> read as nine-class ids : max deviation from reference %.2f pp" % da)
    print("-> read as source values  : max deviation from reference %.2f pp" % db)

    if hist[9] > 0:
        verdict = "source"
        why = "value 9 (asphalt) is present, so the folder cannot be converted"
    elif db < da * 0.5:
        verdict = "source"
        why = "proportions match only after applying the lookup"
    elif da < db * 0.5 and da <= args.tol:
        verdict = "9class"
        why = "proportions match the published class proportions directly"
    elif da < db * 0.5:
        verdict = "9class"
        why = ("9-class reading is closer, but the folder deviates from the full-release "
               "proportions; expected for a subset or a patch folder")
    else:
        verdict = "inconclusive"
        why = ("neither reading matches the full-release proportions; this is normal "
               "for a small folder or a patch folder, and it cannot be resolved from "
               "proportions alone")

    print("\nverdict: %s  (%s)" % (verdict, why))
    if verdict == "inconclusive" and not args.quiet:
        print("  for a subset, pass --limit or check a known-good tile by eye")
    if verdict == "source" and not args.quiet:
        print("  convert with: python tools/convert_masks_10to9.py "
              "--src %s --dst masks_9class/" % args.masks)

    if not args.quiet:
        p = b if verdict == "source" else a
        print("\nclass proportions (percent of pixels)")
        print("  class  %-32s %8s %10s" % ("name", "this set", "reference"))
        for c in range(9):
            print("  %5d  %-32s %8.2f %10.2f"
                  % (c, CLASS_NAMES[c], p[c], REFERENCE_PCT[c]))
        if len(files) > 1000:
            print("\n  note: the reference is for the complete 7,209-tile release. A")
            print("  deviation above ~0.1 pp on this many masks means either a")
            print("  partial patch or a wrong lookup.")

    if args.expect and verdict != args.expect:
        sys.exit("\nFAIL: expected %s, detected %s" % (args.expect, verdict))
    if args.expect:
        print("\nOK: encoding is %s as expected" % verdict)


if __name__ == "__main__":
    main()
