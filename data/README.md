# Data

The complete dataset is in this repository:

```text
data/
├── images/     7,209 × image_<id>.jpg       256 × 256 RGB, ~88 MB
└── masks/      7,209 × image_<id>_lab.png   256 × 256, 8-bit, ten-value encoding
```

Total: 14,418 data files, ~97 MB including the documentation.

The masks in `data/masks/` are **already corrected**: the three tiles described in
[`../corrections/`](../corrections/) carry their v2 labels, not the v1 ones. The
original v1 files are kept in `corrections/masks_v1/` if you want to see what changed.

The masks are in the **ten-value source encoding** (`0`–`9`), not in the nine paper
class ids. Convert before training:

```bash
python tools/convert_masks_10to9.py --src data/masks --dst masks_9class/
python tools/verify_encoding.py --masks data/masks --expect source
```

See [`../metadata/encoding.md`](../metadata/encoding.md) for the lookup table and the
list of ways to get it wrong.

---

## Which split to use

There is deliberately **no** `train/` `valid/` `test/` folder structure. The split is a
list of tile stems in [`../metadata/splits/`](../metadata/splits/):

| Split | Tiles | File |
|---|---:|---|
| train | 5,046 | `metadata/splits/train.txt` |
| valid | 1,442 | `metadata/splits/valid.txt` |
| test | 721 | `metadata/splits/test.txt` |

> **Do not re-split.** These are spatially contiguous blocks, not a random draw. A
> random split puts near-duplicate neighbouring tiles into both training and test and
> inflates every metric.

If you prefer folders on disk, generate them:

```bash
python tools/materialize_splits.py --data data --out splits
# symlinks by default; add --copy to duplicate the files instead
```

That creates `splits/{train,valid,test}/{images,masks}/` following the official
assignment.

### A note on the split shipped with the manuscript files

Copies of the dataset that circulated alongside the manuscript were arranged as
`train/ 5,767`, `valid/ 721`, `test/ 721`. That is **not** the split reported in the
paper, which is `5,046 / 1,442 / 721`: 1,225 tiles fall into a different subset between
the two. The lists in `metadata/splits/` are the ones that reproduce Table 2 of the
paper exactly, pixel for pixel, and they are the ones to use. If you hold an old copy
with a `train/valid/test` folder layout, check it against `metadata/splits/` before
comparing numbers with the paper.

---

## File naming

Tiles are joined to splits by stem; the mask carries a `_lab` suffix:

```text
metadata/splits/test.txt        ->  image_10353
data/images/image_10353.jpg
data/masks/image_10353_lab.png
```

The suffix is kept from the original archive so that file names match the original
release and the paper's supplementary material. `tools/check_dataset.py` and
`tools/materialize_splits.py` accept either `image_<id>.png` or `image_<id>_lab.png`.

---

## Why the files are tracked directly, not through Git LFS

No single file is larger than 20 kB and the whole set is under 100 MB, so plain Git
copes: one `git clone` and nothing extra to install. Git LFS would only pay off if the
masks were re-released repeatedly, because binary blobs do not delta-compress.

Two consequences worth knowing before you fork:

- The **web uploader cannot add 14k files** in one go. Clone, commit and push with the
  Git CLI.
- If you change masks and commit, the repository grows by the full size of the changed
  files. Publish derived sets (for example the converted nine-class masks) as a release
  asset rather than as a commit.

This repository is the authoritative version. If a copy you obtained elsewhere
disagrees, please open an issue so it can be fixed here.
