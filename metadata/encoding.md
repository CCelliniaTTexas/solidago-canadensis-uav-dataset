# Label encoding

Everything you need in order to be certain that a mask means what you think it
means. If you read only one section, read [Pitfalls](#pitfalls).

---

## 1. What is stored

The released PNG masks are 8-bit single-channel images with the annotation
campaign's own **ten** source values, `0`–`9`. They are not the nine paper class
ids, and the mapping is not the identity:

```text
source value in PNG :  0   1   2   3   4   5   6   7   8   9
paper class id      :  5   4   1   3   4   6   0   2   7   8
```

Ten source values collapse to nine classes because source `1` and source `4` both
denote concrete pavement.

The inverse mapping — which bytes produce a given class — is what you need when you
build a lookup for your own pipeline:

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

The same information, with descriptions and per-class proportions, is in
[`class_definitions.csv`](class_definitions.csv).

---

## 2. Why the mapping looks like this

The source values are the order in which classes were created in Labelme during the
annotation campaign, not a designed taxonomy. Concrete pavement was annotated under
two separate labels for a while before the rule set was fixed, and both survived
into the exported files. Background was likewise handled as its own label, because
rotating an image and cropping back to a rectangle leaves regions that have no
land-cover attribution at all.

The paper renumbered the classes into the order used in all its tables
(`0` background … `8` asphalt) and reported the merged concrete class, so the
published files and the published tables use different numbers for the same thing.
That is the whole source of confusion around this dataset.

---

## 3. Worked example

`image_10324`, a tile of mostly other vegetation and bare ground:

```python
import numpy as np
from PIL import Image

LUT = np.array([5, 4, 1, 3, 4, 6, 0, 2, 7, 8], dtype=np.uint8)

raw = np.asarray(Image.open("masks/image_10324.png"))
np.unique(raw)            # -> [3, 5]
np.unique(LUT[raw])       # -> [3, 6]

# source 3 = other vegetation  -> class 3
# source 5 = buildings         -> class 6
```

Note the last line: the tile's second-most-common byte is `5`, which is **buildings**,
not bare ground. Reading it as a class id directly would report bare ground.

---

## 4. Pitfalls

### 4.1 Reading the bytes as class ids

The most common failure. A mask that is 47 % byte `6` is **background**, not
buildings (buildings are `5`); a mask that is 8 % byte `0` is **bare ground**, not
background (background is `6`).

### 4.2 Converting twice

If a folder already holds class ids `0–8`, applying the lookup again destroys it:

```text
class 0 -> 5    class 1 -> 4    class 2 -> 1    class 3 -> 3
class 4 -> 4    class 5 -> 6    class 6 -> 0    class 7 -> 2
class 8 -> 7
```

A converted set contains no byte `9` (asphalt is class 8), so the presence of `9`
proves a folder is still in source encoding — but the absence of `9` proves nothing.
`tools/convert_masks_10to9.py` refuses to run on a folder it can tell is already
converted, and `tools/verify_encoding.py` reports which encoding a folder is in by
testing both hypotheses against the published class proportions. Run it first.

### 4.3 Mixing encodings

`data/masks/` ships the corrected set in **source encoding**, so converting it is the
normal path. `corrections/masks_v2/` holds the same three corrected tiles in source
encoding for patching an earlier v1 copy, and `corrections/masks_9class/` holds
those three already converted. Copying the wrong one into the wrong folder is silent —
the arrays still look like plausible label images. Keep one encoding per directory and
name the directory after it.

### 4.4 Treating background as a land-cover class

Class 0 is padding from rotation and cropping, 99.9 % of it on the tile border, and
it is 0.19 % of all pixels. It is still useful as a class during training — it stops
the model from inventing land cover in padding — but it should be excluded from any
land-cover accuracy that you report, and you should say explicitly whether you did.

### 4.5 Expecting a `labelme` JSON round trip

The masks were exported from a filtered annotation version; they do not correspond
one to one to raw JSON geometry. Do not try to regenerate masks from JSON.

---

## 5. Reference proportions

Computed from the full 7,209-tile release, nine classes, after conversion:

| class | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| % of all pixels | 0.19 | 11.09 | 10.02 | 29.15 | 14.50 | 8.07 | 19.54 | 0.91 | 6.52 |

Any correct conversion of the complete release lands on these numbers to within
0.01 percentage points per class. Use them as the acceptance test for your data
pipeline; `tools/verify_encoding.py --expect 9class` does it for you.

Per-split counts: [`dataset_statistics.csv`](dataset_statistics.csv).
