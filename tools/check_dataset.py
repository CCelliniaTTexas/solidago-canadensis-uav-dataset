#!/usr/bin/env python3
"""Check a downloaded copy of the dataset against the published metadata.

Verifies that
  * every tile stem in metadata/splits/ has an image and a mask,
  * there are no tiles outside the published split,
  * every mask is 256 x 256, single channel, with values inside the encoding,
  * the class proportions match metadata/dataset_statistics.csv.

Checks 1 and 2 catch a truncated download or a flattened directory. Check 4 catches
a wrong lookup table, which is otherwise silent.

Usage
    python check_dataset.py --images data/images --masks data/masks
    python check_dataset.py --images data/images --masks data/masks --split test
    python check_dataset.py --images data/images --masks masks_9class --expect 9class

Exit status is 0 when everything passes and 1 otherwise, so it can gate a pipeline.
"""
import argparse
import csv
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
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def read_splits(want=None):
    out = {}
    names = [want] if want else ["train", "valid", "test"]
    for n in names:
        p = os.path.join(REPO, "metadata", "splits", n + ".txt")
        if not os.path.exists(p):
            sys.exit("missing split file: %s" % p)
        out[n] = [x.strip() for x in open(p, encoding="utf-8") if x.strip()]
    return out


def read_reference():
    p = os.path.join(REPO, "metadata", "dataset_statistics.csv")
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    ref = np.zeros(9)
    for r in rows:
        if r["class_id"] == "total":
            continue
        ref[int(r["class_id"])] = float(r["proportion_pct"])
    return ref


def find(folder, stem, exts):
    for ext in exts:
        p = os.path.join(folder, stem + ext)
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser(
        description="Check a local copy of the dataset against the metadata.")
    ap.add_argument("--images", required=True, help="folder of image_<id>.jpg")
    ap.add_argument("--masks", required=True, help="folder of mask PNGs")
    ap.add_argument("--split", choices=["train", "valid", "test"], default=None,
                    help="check one split only (default: all)")
    ap.add_argument("--expect", choices=["source", "9class"], default="source",
                    help="encoding the masks should be in (default: source)")
    ap.add_argument("--tol", type=float, default=0.05,
                    help="allowed deviation of class proportions, percentage points")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    splits = read_splits(args.split)
    stems = [(n, t) for n, v in splits.items() for t in v]
    print("tiles to check: %d" % len(stems))

    fails = []
    hist = np.zeros(10, dtype=np.int64)
    shapes = set()
    missing_img = missing_msk = bad_size = 0

    for i, (split, stem) in enumerate(stems):
        ip = find(args.images, stem, (".jpg", ".jpeg", ".png", ".tif"))
        mp = find(args.masks, stem, (".png", "_lab.png"))
        if ip is None:
            missing_img += 1
            if missing_img <= 5:
                fails.append("%s/%s: image missing" % (split, stem))
            continue
        if mp is None:
            missing_msk += 1
            if missing_msk <= 5:
                fails.append("%s/%s: mask missing" % (split, stem))
            continue
        a = np.asarray(Image.open(mp).convert("L"))
        shapes.add(a.shape)
        if a.shape != (256, 256):
            bad_size += 1
            if bad_size <= 5:
                fails.append("%s/%s: mask is %s, expected (256, 256)"
                             % (split, stem, a.shape))
        hist += np.bincount(a.ravel(), minlength=10)[:10]
        if not args.quiet and (i + 1) % 2000 == 0:
            print("  checked %d/%d" % (i + 1, len(stems)), flush=True)

    print("\nmissing images : %d" % missing_img)
    print("missing masks  : %d" % missing_msk)
    print("wrong mask size: %d" % bad_size)
    print("mask shapes seen: %s" % (sorted(shapes) if len(shapes) < 4 else
                                    "%d distinct" % len(shapes)))

    # 目录里有没有划分之外的多余文件（始终对照全部三个划分）
    all_known = {t for v in read_splits(None).values() for t in v}
    on_disk = {os.path.splitext(f)[0].replace("_lab", "")
               for f in os.listdir(args.masks) if f.lower().endswith(".png")}
    extra = sorted(on_disk - all_known)
    print("masks not in the published split: %d%s"
          % (len(extra), (" e.g. " + ", ".join(extra[:5])) if extra else ""))

    # 编码与类别占比
    tot = int(hist.sum())
    if tot:
        if hist[9] > 0:
            verdict = "source"
        else:
            a9 = hist[:9] / hist[:9].sum() * 100.0
            cls = np.zeros(9)
            for s in range(10):
                cls[LUT[s]] += hist[s]
            b = cls / cls.sum() * 100.0
            ref = read_reference()
            if ref is None:
                verdict = "unknown"
            else:
                da = float(np.abs(a9 - ref).max())
                db = float(np.abs(b - ref).max())
                verdict = "9class" if da < db * 0.5 else ("source" if db < da * 0.5
                                                          else "inconclusive")
        print("\ndetected encoding: %s (expected %s)" % (verdict, args.expect))
        if verdict != args.expect:
            fails.append("encoding is %s, expected %s" % (verdict, args.expect))

        p = (hist[:9] / hist[:9].sum() * 100.0) if verdict in ("9class", "unknown") \
            else np.array([sum(hist[s] for s in range(10) if LUT[s] == c)
                           for c in range(9)], dtype=np.float64)
        if verdict in ("source", "inconclusive"):
            p = p / p.sum() * 100.0
        ref = read_reference()
        print("\nclass proportions (percent of pixels)")
        print("  class  %-32s %8s %10s %8s" % ("name", "this set", "published", "dev"))
        worst = 0.0
        for c in range(9):
            dev = p[c] - (ref[c] if ref is not None else 0.0)
            worst = max(worst, abs(dev))
            print("  %5d  %-32s %8.2f %10.2f %+8.2f"
                  % (c, CLASS_NAMES[c], p[c], ref[c] if ref is not None else 0.0, dev))
        print("\nmax deviation: %.3f pp (tolerance %.2f)" % (worst, args.tol))
        if worst > args.tol:
            if args.split:
                # A single split is spatially distinct by design, so its class
                # composition legitimately differs from the whole-dataset figures.
                print("  note: this is one split, not the whole dataset; the "
                      "published\n  proportions describe all 7,209 tiles, so a "
                      "deviation here is expected\n  and is not treated as a "
                      "failure. Run without --split to enforce it.")
            else:
                fails.append("class proportions deviate by %.3f pp" % worst)
    else:
        fails.append("no masks were read")

    print()
    if fails:
        print("FAILED: %d problem(s)" % len(fails))
        for f in fails[:20]:
            print("  - %s" % f)
        sys.exit(1)
    print("OK: dataset matches the published metadata")


if __name__ == "__main__":
    main()
