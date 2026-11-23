# Data dictionary

Every machine-readable table in this repository, with column meanings.

---

## `metadata/class_definitions.csv`

One row per predicted class.

| column | type | meaning |
|---|---|---|
| `class_id` | int 0–8 | the class index used in the paper and by models |
| `class_name` | str | class name as used in the paper |
| `description` | str | annotation rule, condensed from Table 1 of the paper |
| `png_source_values` | str | space-separated byte values in the released PNG that map to this class; more than one means the source values are merged |
| `n_source_values` | int | how many source values map here; `2` only for concrete pavement |
| `proportion_pct` | float | share of all annotated pixels, computed over all 7,209 tiles |

`png_source_values` is the column to build a lookup table from. `class_id` is the
column to train against.

---

## `metadata/dataset_statistics.csv`

One row per class plus a `total` row. Pixel counts, not tile counts.

| column | type | meaning |
|---|---|---|
| `class_id` | int 0–8, or `total` | class index |
| `class_name` | str | class name; empty on the `total` row |
| `train_pixels` | int | pixels of this class in the 5,046 training tiles |
| `valid_pixels` | int | pixels in the 1,442 validation tiles |
| `test_pixels` | int | pixels in the 721 test tiles |
| `total_pixels` | int | sum over the three subsets |
| `proportion_pct` | float | `total_pixels` over all annotated pixels |

These numbers reproduce Table 2 of the paper to within 0.01 percentage points. They
were computed from the masks, not copied from the manuscript.

They are computed from the **v1** masks so that they match Table 2 exactly. The three
v2 corrections move four of them by 0.01–0.015 percentage points: class 1 +0.01,
class 4 −0.01, class 5 +0.01, class 6 −0.01. Use these numbers as the acceptance test
and allow that tolerance — `tools/check_dataset.py` defaults to 0.05 pp for exactly
this reason.

---

## `metadata/splits_summary.csv`

One row per subset plus `total`.

| column | type | meaning |
|---|---|---|
| `split` | str | `train`, `valid`, `test` or `total` |
| `tiles` | int | number of tiles |
| `pixels` | int | `tiles × 65536` |
| `share_of_tiles_pct` | float | share of tiles |
| `share_of_pixels_pct` | float | share of pixels |

Tile shares are exactly 70.0 / 20.0 / 10.0 by design. Pixel shares are identical to
tile shares, because every tile is 256 × 256: 5,046 / 1,442 / 721 tiles is exactly
330,694,656 / 94,502,912 / 47,251,456 pixels. What differs between the subsets is
**class composition**, not size — the blocks are spatially distinct, so a class that
happens to concentrate in a few blocks is unevenly represented. That is why the
per-class columns of `dataset_statistics.csv` are not in a 7 : 2 : 1 ratio even
though the totals are.

---

## `metadata/splits/{train,valid,test}.txt`

Plain text, one tile stem per line, no extension, no header, Unix line endings.

```text
image_10324
image_10325
...
```

Resolve a stem to files as

```text
images/<stem>.jpg
masks/<stem>.png           # or <stem>_lab.png in the v2 correction patch
```

The three files together cover 7,209 stems, all unique, with no overlap. They are
the split used for every number reported in the paper. **Do not re-split at random** —
see the note in the main README on spatial blocking.

---

## `corrections/corrections_report.csv`

Pixel-level difference between the v1 mask and the corrected v2 mask, for the three
tiles changed in v2. Both masks are compared in the nine-class encoding, so the
rows are class-to-class transitions, not byte changes.

| column | type | meaning |
|---|---|---|
| `tile` | str | tile stem |
| `from_class` | str | class in the v1 mask |
| `to_class` | str | class in the v2 mask |
| `pixels` | int | number of pixels with this transition |
| `pct_of_tile` | float | `pixels / 65536 × 100` |

Total corrected area: 132,613 px over 3 tiles, i.e. 0.03 % of the whole dataset
(472,449,024 px).

---

## `qc/suspicious.csv`

The screening list. One row per flagged tile, 509 rows.

| column | type | meaning |
|---|---|---|
| `split` | str | `train`, `valid` or `test` |
| `tile` | str | tile stem |
| `frac_built` | float 0–1 | fraction of the tile whose mask is concrete pavement, buildings or asphalt pavement |
| `frac_veg` | float 0–1 | fraction of the tile whose mask is *S. canadensis* or other vegetation |
| `exg_built` | float or empty | mean excess-green index over the built-up pixels; **empty when `frac_built` is 0**, because the mean over an empty region is undefined |
| `exg_veg` | float or empty | the same over the vegetation pixels; empty when `frac_veg` is 0 |
| `reason` | str | `built_area_green(exg=N)` — built-up mask but green image; `veg_area_not_green(exg=N)` — vegetation mask but not-green image; `N` is the index rounded to an integer |

The excess-green index is `2G − R − B` with `R`, `G`, `B` the tile mean of each
channel. High values mean green. Empty cells are intentional; do not read them as
zero. A reader that requires all columns numeric should drop the rows where the
relevant `frac_*` is 0, or fill with `NaN`.

The list is a **review queue**, not a set of confirmed errors — see `qc/README.md`.
