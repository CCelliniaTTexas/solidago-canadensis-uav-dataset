# 加拿大一枝黄花九类无人机分割数据集（中文速览）

本仓库是数据集 **`Solidago canadensis`（加拿大一枝黄花）九类无人机影像分割数据集**
的发布主页。**完整数据就在仓库里**，克隆后即可使用：

```text
data/images/   7,209 张 image_<id>.jpg
data/masks/    7,209 张 image_<id>_lab.png   （十源值编码，已含 v2 修正）
```

同一份数据也以 DOI 归档在 Mendeley Data，引用时请用 DOI：

> **DOI: [10.17632/5pxk3ym2yv](https://doi.org/10.17632/5pxk3ym2yv)**
> v2 直接链接：<https://data.mendeley.com/datasets/5pxk3ym2yv/2>

训练与评测代码在 [`solidago-canadensis-segmentation`](https://github.com/CCelliniaTTexas/solidago-canadensis-segmentation)。

英文完整说明见 [`README.md`](README.md)，本页只列中文使用者最容易出错的要点。

---

## ⚠️ 最重要的一条：掩码不是 0–8 顺序

发布的 PNG 掩码里存的是**标注阶段的十源值编码（0–9）**，**不等于**论文的九个类别编号。
其中源值 `1` 与 `4` 都表示混凝土路面（合并为一类），源值 `6` 是旋转裁剪产生的填充区域，
对应论文的背景类 `0`。

```text
PNG 中的源值 : 0   1   2   3   4   5   6   7   8   9
论文类别编号 : 5   4   1   3   4   6   0   2   7   8
```

反查（每个类别由哪些源值产生）：

| 类别 | 名称 | PNG 源值 |
|---:|---|---|
| 0 | 背景 | `6` |
| 1 | 加拿大一枝黄花 | `2` |
| 2 | 建筑废弃材料 | `7` |
| 3 | 其他植被 | `3` |
| 4 | 混凝土路面 | `1`、`4` |
| 5 | 裸地 | `0` |
| 6 | 建筑物 | `5` |
| 7 | 车顶 | `8` |
| 8 | 沥青路面 | `9` |

**常见错误**：把字节值直接当类别读。结果是「背景」被当成「裸地」、「裸地」被当成「建筑物」。
论文 Table 1 里那列 "Pixel value" 写的是 `0–8`，指的是类别编号，**不是**文件里存的字节，
照它读会错。详见 [`metadata/encoding.md`](metadata/encoding.md)。

---

## 数据概况

| 项目 | 数值 |
|---|---|
| 影像块数 | 7,209 |
| 尺寸 | 256 × 256 像素（约 8.7 m × 8.7 m） |
| 地面采样距离 | 3.4 cm |
| 航高 | 120 m |
| 采集时间 | 2025 年 10 月 25 日（盛花期） |
| 地点 | 浙江省舟山市岱山岛 |
| 类别数 | 9（背景 + 8 个地物类） |
| 训练 / 验证 / 测试 | 5,046 / 1,442 / 721 |
| 划分方式 | 按 10×10 空间分块整块分配（70/20/10），非随机划分 |

空间分块是刻意的：滑窗切块会让相邻块高度相似，随机划分会把同一片地面同时放进训练和测试，
指标会虚高。因此本数据集的绝对值比随机划分偏低，但更可信。

各类别像素占比：背景 0.19 %、一枝黄花 11.09 %、建筑废弃材料 10.02 %、其他植被 29.15 %、
混凝土路面 14.50 %、裸地 8.07 %、建筑物 19.54 %、车顶 0.91 %、沥青路面 6.52 %。

逐类逐划分的像素数见 [`metadata/dataset_statistics.csv`](metadata/dataset_statistics.csv)，
与论文 Table 2 的最大偏差 **0.005 个百分点**。

---

## 快速开始

```bash
git clone https://github.com/CCelliniaTTexas/solidago-canadensis-uav-dataset.git
cd solidago-canadensis-uav-dataset
python -m pip install numpy pillow

# 1. 确认仓库内掩码的编码（应输出 source）
python tools/verify_encoding.py --masks data/masks --expect source

# 2. 转换成论文的九类编号
python tools/convert_masks_10to9.py --src data/masks --dst masks_9class/

# 3. 验收：类别占比应与发布值一致
python tools/verify_encoding.py --masks masks_9class --expect 9class

# 4. 检查划分里每一块影像与掩码是否齐全、是否一致
python tools/check_dataset.py --images data/images --masks data/masks --expect source

# 5. 可选：生成 train/valid/test 目录结构
python tools/materialize_splits.py --data data --out splits
```

**不要转换两次**。已经转过一次的掩码再套一次查找表，每一类都会被写坏，而且不会有任何报错。
转换脚本会先检测、发现像已转换就直接拒绝执行。

**不要把划分改成随机划分**。发布的是空间分块划分；随机划分会让相邻近重复块同时进入
训练与测试，指标会虚高，也无法与论文对比。

> **注意划分口径**：随稿件流传的一些数据副本是 `train/ 5767`、`valid/ 721`、`test/ 721`，
> 这与论文的 `5046 / 1442 / 721` **不同**，有 1225 张归属不一样。以 `metadata/splits/`
> 为准——那是能逐像素复现 Table 2 的口径。

---

## v2 修正了什么

三张影像块的类别整体标错，已按原图重新标注（几何不变，只改类别）：

| 影像块 | v1 | v2 |
|---|---|---|
| `image_19967` | 99.1 % 混凝土路面 | 整块改为一枝黄花（该块是纯群落） |
| `image_12233` | 47.9 % 建筑物 | 改为裸地（露天场地被标成建筑） |
| `image_23781` | 53.0 % 建筑物 | 改为裸地（同上） |

对比图：[`corrections/figures/corrections.png`](corrections/figures/corrections.png)；
逐像素改动明细：[`corrections/corrections_report.csv`](corrections/corrections_report.csv)。

**`data/masks/` 里已经是修正后的结果，从本仓库开始用不需要再打补丁。**

`corrections/` 下的三个目录是给"已经从 Mendeley 下载过 v1"的人用的，编码不同，
**不要拿错**：

- `corrections/masks_v1/` — 修正前的原始错误掩码（十源值编码），用于对照
- `corrections/masks_v2/` — 修正后的掩码（十源值编码），覆盖到 v1 目录后一起转换
- `corrections/masks_9class/` — 修正后并已转换为九类编号，如果你已用九类版就用这个

三张图都在**训练集**里，所以修正不改变验证/测试集，v1 与 v2 的测试指标仍可比。

---

## 质量筛查表

[`qc/suspicious.csv`](qc/suspicious.csv) 列出 7,209 块中的 509 块（7.1 %），
这些块的掩码类别构成与影像统计特征互相矛盾（例如掩码说是混凝土/建筑，影像却是连片植被）。

**这是待复核清单，不是错误清单。** 每块都要看图确认后才能决定是否剔除。
如果要剔除，训练集和测试集的处理方式必须写清楚——只在训练时剔除是合理的；
训练和测试都剔除会让指标失去可比性。`image_19967` 就是因为上了这张表才被发现标错。

表中 `exg_built` / `exg_veg` 为空是**正常**的：当该块没有对应类别的像素时，
平均超绿指数无定义，填 0 会造成误导。

---

## 许可与引用

数据、掩码与元数据均以 **CC BY 4.0** 发布，可自由使用与改编（含商业用途），
需注明出处并链接许可协议。见 [`LICENSE`](LICENSE)。

引用请同时给出数据集 DOI 与论文。格式见 [`CITATION.cff`](CITATION.cff)。

---

## 联系

于志锋 yu@hznu.edu.cn

发现新的错误影像块欢迎提 issue 或邮件。**请不要直接提 PR 改掩码**——正式归档在
Mendeley Data 上，分叉出去会与 DOI 版本不一致。能对照原图核实的修正会并入下一版。
