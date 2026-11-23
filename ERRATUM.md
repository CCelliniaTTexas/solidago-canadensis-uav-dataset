# Erratum and patch — nine-class UAV dataset of *Solidago canadensis*

Patch to version 1 of this dataset
Version: v2 · Date: 2026-10-29 · Contact: Zhifeng Yu, yu@hznu.edu.cn

This document is the authoritative record of what version 2 changes. It supersedes
the erratum distributed with the v2 data release, which is unchanged in
substance but less precise about the tile-level numbers.

---

## 1. Class encoding

The released PNG masks store **ten source values** (`0`–`9`) that are the label ids
of the annotation campaign. They do **not** equal the nine class ids of the paper.
The conversion is a fixed lookup, implemented in
[`tools/convert_masks_10to9.py`](tools/convert_masks_10to9.py):

```text
source value : 0  1  2  3  4  5  6  7  8  9
paper class  : 5  4  1  3  4  6  0  2  7  8
```

Read the other way round, so that you know which byte values produce a given class:

| class | name | source values |
|---:|---|---|
| 0 | Background | `6` |
| 1 | *Solidago canadensis* | `2` |
| 2 | Discarded construction materials | `7` |
| 3 | Other vegetation | `3` |
| 4 | Concrete pavement | `1`, `4` |
| 5 | Bare ground | `0` |
| 6 | Buildings | `5` |
| 7 | Vehicle roofs | `8` |
| 8 | Asphalt pavement | `9` |

Three facts make this table necessary, and each of them has caused a real error:

1. **Source values `1` and `4` both denote concrete pavement.** The annotation
   campaign used the two labels interchangeably for grey-white concrete roads. They
   are merged into class 4.
2. **Source value `6` is not buildings and not bare ground — it is the padding**
   produced by image rotation and rectangular cropping, and it becomes class 0
   (Background). 99.9 % of it lies on the outer border of a tile.
3. **Source value `0` is bare ground and becomes class 5.** Source values `0` and
   `6` must never be confused. A mask dominated by `6` is background; a mask
   dominated by `0` is bare ground.

> **Correction to the article.** Table 1 of the paper carries a column headed
> "Pixel value" listing `0–8` in step with the class id. That column describes the
> class ids, *not* the bytes stored in the released PNGs. Anyone reading Table 1 as
> a specification of the released files will label background as bare ground and
> bare ground as buildings. Use the table above instead.

### Validation

Applying the lookup to the full 7,209-tile mask set reproduces the class proportions
of Table 2 of the paper. Measured on this release:

| class | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| this release, % | 0.19 | 11.09 | 10.02 | 29.15 | 14.50 | 8.07 | 19.54 | 0.91 | 6.52 |
| Table 2, % | 0.19 | 11.09 | 10.02 | 29.15 | 14.51 | 8.07 | 19.54 | 0.91 | 6.52 |

Largest deviation: **0.005 percentage points**. Per-split pixel totals also match
Table 2 exactly (330,694,656 / 94,502,912 / 47,251,456). This is the check that
should be run on any pipeline before training; `tools/verify_encoding.py` automates
it. Machine-readable form: [`metadata/dataset_statistics.csv`](metadata/dataset_statistics.csv).

---

## 2. Tiles corrected in this version

Three tiles were reported by a user of the dataset and re-checked against the source
imagery. In each case the class of whole regions was wrong; the geometry is
preserved and only those regions were relabelled.

| Tile | Released v1 mask | Problem | v2 |
|---|---|---|---|
| `image_19967` | 99.1 % concrete pavement (source `1`), 0.9 % bare ground (source `0`) | the tile is a pure *S. canadensis* stand | both → *S. canadensis* (source `2`) |
| `image_12233` | 47.9 % buildings (source `5`) | open bare ground annotated as buildings | → bare ground (source `0`) |
| `image_23781` | 53.0 % buildings (source `5`) | open bare ground annotated as buildings | → bare ground (source `0`) |

Shares are of the tile area. The full pixel-level transitions, including the small
remainder of each tile, are in
[`corrections/corrections_report.csv`](corrections/corrections_report.csv):

```text
image_12233   Buildings            -> Bare ground           47.85 % of tile
image_19967   Concrete pavement    -> S. canadensis         99.13 %
image_19967   Bare ground          -> S. canadensis          0.87 %
image_23781   Buildings            -> Bare ground           52.98 %
```

`image_19967` was already on the screening list (§4) as a green tile annotated as
built-up, which is how the error came to light.

Side-by-side imagery: [`corrections/figures/corrections.png`](corrections/figures/corrections.png).

---

## 3. How to apply

**Starting from this repository: nothing to do.** `data/masks/` holds the corrected
masks for all 7,209 tiles, in the same ten-value encoding as v1. Convert as usual:

```bash
python tools/convert_masks_10to9.py --src data/masks --dst masks_9class/
```

**Starting from an earlier v1 copy:** overwrite the three tiles and convert:

```bash
cp corrections/masks_v2/*_lab.png path/to/masks_v1/
python tools/convert_masks_10to9.py --src path/to/masks_v1/ --dst masks_9class/
```

`corrections/masks_v1/` keeps the original wrong masks so the change can be audited.

If you already keep converted nine-class masks, use `corrections/masks_9class/`
instead — those three files are in class ids `0–8`. **Do not convert them a second
time**: the converter would silently re-map every class. `tools/verify_encoding.py`
tells you which encoding a folder is in if you are unsure.

`suspicious.csv` is unchanged by v2. No other image or mask was touched; tile count,
splits and file names are identical to v1.

---

## 4. Screening list

[`qc/suspicious.csv`](qc/suspicious.csv) lists 509 of the 7,209 tiles (7.1 %) whose
mask composition and image statistics are mutually inconsistent, for example a tile
whose mask is dominated by concrete and asphalt while the image is a closed
vegetation canopy.

The list is published **for review, not as a list of errors**: each tile must be
inspected before it is excluded. If a conservative training set is needed, the tiles
in this list can be held out, but the protocol should say so, because metrics
computed with and without them are not comparable.

Two columns (`exg_built`, `exg_veg`) are empty when the corresponding class covers
no pixel in the tile — the mean excess-green index over an empty region is
undefined, and writing `0` there would be a lie. See [`qc/README.md`](qc/README.md).

---

## 5. What is not included

- **Labelme JSON files.** Not part of this dataset. The published masks were
  exported from a later, filtered version of the annotations and do not correspond
  one to one to the raw JSON geometry.
- **Hyperspectral bands.** The orthorectified hyperspectral mosaic and the per-tile
  spectral stack used in the fusion experiment are available from the corresponding
  author on reasonable request.
- **Model checkpoints.** Kept with the article's supplementary material rather than
  here, so that this repository stays a dataset repository.

---

## 6. Files added in v2

| File | Purpose |
|---|---|
| `ERRATUM.md` | this document |
| `tools/convert_masks_10to9.py` | the ten-value → nine-class converter |
| `tools/verify_encoding.py` | encoding and proportion checker |
| `tools/check_dataset.py` | completeness and consistency checker |
| `tools/materialize_splits.py` | builds train/valid/test folders from the stem lists |
| `qc/suspicious.csv` | screening list |
| `data/masks/` | all 7,209 masks, corrected |
| `corrections/masks_v1/`, `masks_v2/` | the three tiles before and after |
| `corrections/masks_9class/` | the three corrected tiles, converted |
| `corrections/corrections_report.csv` | pixel-level transitions |
| `metadata/` | class definitions, statistics, splits, encoding notes |
