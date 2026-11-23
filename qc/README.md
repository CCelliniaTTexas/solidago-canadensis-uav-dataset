# Quality-control screening list

`suspicious.csv` lists **509 of the 7,209 tiles (7.1 %)** whose mask composition and
image statistics are mutually inconsistent. It is a review queue, not a list of
confirmed errors.

| Split | Flagged | Total | Share |
|---|---:|---:|---:|
| train | 350 | 5,046 | 6.9 % |
| valid | 101 | 1,442 | 7.0 % |
| test | 58 | 721 | 8.0 % |

The rate is close to uniform across the three subsets, which is what you want: the
flagging is not concentrated in one split, so excluding flagged tiles does not change
the train/test relationship.

---

## How a tile gets flagged

Two independent signals are compared: what the mask says is on the ground, and what
the image looks like.

| Signal | Definition |
|---|---|
| `frac_built` | mask fraction of concrete pavement, buildings and asphalt pavement |
| `frac_veg` | mask fraction of *S. canadensis* and other vegetation |
| `exg_built` | mean excess-green index over the built-up pixels |
| `exg_veg` | mean excess-green index over the vegetation pixels |

The excess-green index is `2G − R − B` over tile means; high means green, low or
negative means bare soil, concrete or shadow.

Two rules produce the two `reason` values:

| reason | Meaning |
|---|---|
| `built_area_green(exg=N)` | the mask says the tile is largely built-up (up to 99.8 %) but the pixels are green (N typically 25–72). 477 tiles. |
| `veg_area_not_green(exg=N)` | the mask says the tile is largely vegetation but the pixels are not green (N typically 0–4, occasionally negative). 32 tiles. |

The first rule dominates because the failure it catches is the common one: a green
canopy annotated as concrete or buildings. `image_19967`, corrected in v2, was found
exactly this way.

---

## How to use it

**Do not delete these tiles blindly.** Some are genuinely fine — a green roof, a
vegetated yard behind a concrete wall, a shadowed patch of vegetation. The list tells
you where to look, not what to conclude.

If you need a conservative training set:

```python
import csv

flagged = {r["tile"] for r in csv.DictReader(open("qc/suspicious.csv"))}
train = [t for t in open("metadata/splits/train.txt").read().split()
         if t not in flagged]
```

and then **state in your protocol** that flagged tiles were excluded, because metrics
computed with and without them are not comparable. Excluding them from training only
is a defensible choice; excluding them from the test set as well inflates every
number and makes the result impossible to compare with the published baselines.

The cleanest option, if you have the source imagery, is to correct a tile rather than
drop it — which is what v2 did for three of them.

---

## Notes on the file

- `exg_built` is empty when `frac_built == 0`, and `exg_veg` when `frac_veg == 0`:
  the mean excess-green index over a region that contains no pixels is undefined.
  Roughly 15 rows have the first empty, 220 the second. Reading those as `0` would
  put them at the bottom of the index range and invert their meaning.
- `reason` repeats the index rounded to an integer (`exg=69` for 69.3). Use the
  `exg_built` / `exg_veg` columns when you need the precise value.
- Column-by-column description: [`../metadata/data_dictionary.md`](../metadata/data_dictionary.md).
