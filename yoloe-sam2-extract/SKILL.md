# Skill: yoloe-sam2-extract

# YOLOE + SAM2.1 卡通角色提取 Skill

## 概览

从教材/绘本/漫画页面中**自动识别并逐个抠出所有卡通人物**，输出透明背景 PNG。

**两阶段流水线**：
1. **YOLOE-11S-seg**（开放词汇检测+分割，2025 ICCV）：文字提示 "cartoon character" 自动定位所有角色框（无需手动打点/打框）
2. **SAM2.1 hiera tiny**（Meta）：用 YOLOE 的框做 box 提示，逐像素精确分割，得到干净的角色 mask

**纯本地运行，CPU 可跑**，模型已内置在本 skill 的 `model/` 目录，无需联网。

## 触发条件

- 用户说"提取/抠出图中所有卡通人物/角色"
- 教材、绘本、漫画、动画截图的角色批量提取
- 需要逐个角色的透明背景 PNG（做视频素材、三视图参考等）

## 模型下载（重要）

**模型权重不随 git 上传**（`model/` 已 git 忽略，体积 748MB）。克隆仓库后需先下载模型：

```bash
cd yoloe-sam2-extract
bash download_models.sh      # 一键下载全部 3 个模型 + 建立软链
```

三个模型及下载链接：

| 模型 | 大小 | 下载 | 用途 |
|:---|:---|:---|:---|
| yoloe-11s-seg.pt | 27MB | `https://huggingface.co/jameslahm/yoloe/resolve/main/yoloe-11s-seg.pt` | YOLOE 检测+分割 |
| sam2.1_hiera_tiny.pt | 149MB | `https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt` | SAM2.1 分割 |
| mobileclip_blt.pt | 572MB | `https://huggingface.co/apple/MobileCLIP-B-LT/resolve/main/mobileclip_blt.pt` | YOLOE 文本编码器 |

**部署后需建立两个软链**（`download_models.sh` 已自动完成）：
```bash
ln -sf model/mobileclip/mobileclip_blt.pt mobileclip_blt.pt            # YOLOE 用相对路径加载
ln -sf code/sam2_code/sam2/configs configs                             # SAM2 hydra 加载 configs
```

**注意**：`mobileclip_blt.pt` 软链指向 `model/`（不随 git 上传），克隆后必须下载模型并重建软链，否则 YOLOE 报找不到文件。

## 目录结构

```
yoloe-sam2-extract/
├── SKILL.md                    # 本文档
├── extract_characters.py       # 主脚本（唯一入口）
├── model/                      # 模型权重（git 忽略，不入库）
│   ├── yoloe/yoloe-11s-seg.pt      # YOLOE 检测+分割（27MB）
│   ├── sam2/sam2.1_hiera_tiny.pt   # SAM2.1 分割（149MB）
│   └── mobileclip/mobileclip_blt.pt # YOLOE 文本编码器（572MB）
├── code/                       # 运行代码（YOLOE/SAM2 的 vendored 源码）
│   ├── ultralytics/            # YOLOE 的 ultralytics fork
│   ├── CLIP/                   # YOLOE 文本编码依赖
│   ├── ml-mobileclip/          # MobileCLIP 实现
│   └── sam2_code/sam2/         # SAM2 源码 + configs
├── configs -> code/sam2_code/sam2/configs   # SAM2 hydra 配置软链
└── mobileclip_blt.pt -> model/mobileclip/mobileclip_blt.pt  # 软链（YOLOE 硬编码相对路径）
```

**注意**：
- `configs` 和 `mobileclip_blt.pt` 是**符号链接**，复制 skill 到新机器时必须保留软链或用 `cp -rL` 解引用，否则运行失败。
- 模型在 `model/`（git 忽略），复制整个 skill 目录时需一并拷贝。

## 环境要求

- Python 3.10+（推荐 3.12）
- **必须用系统 Python**（`/usr/bin/python3`），需 torch ≥2.5.1（P100/P102 等老 GPU 用 cu121 版）
- 依赖：`torch torchvision pillow numpy hydra-core omegaconf iopath ftfy regex timm open_clip_torch clip`

```bash
pip install torch torchvision pillow numpy hydra-core omegaconf iopath ftfy regex timm open_clip_torch clip
```

**说明**：
- `clip` 是 Ultralytics 的 CLIP（`git+https://github.com/ultralytics/CLIP.git`），YOLOE 文本编码必需；本 skill 的 `code/CLIP/` 已含其源码，`sys.path` 已指向它，多数情况下无需单独安装
- 若运行报 `No module named 'clip'`，将 `code/CLIP` 加入 `PYTHONPATH` 或 `pip install git+https://github.com/ultralytics/CLIP.git`
- venv/conda 的 torch 2.13+ 在 P102（算力 6.1）等老 GPU 上会报 CUDA kernel 错误，**务必用 `/usr/bin/python3`（torch 2.5.1+cu121）**

## 用法

```bash
# 基本用法
/usr/bin/python3 extract_characters.py <输入图片.png> <输出目录>

# 指定识别类别（默认卡通人物/动物）
/usr/bin/python3 extract_characters.py 输入.png 输出/ --names "cartoon character, cartoon animal, cartoon fox"

# 调低置信度捡更多角色（默认 0.10）
/usr/bin/python3 extract_characters.py 输入.png 输出/ --conf 0.08

# 框扩大比例（默认 0=原始框；角色被截断时可试 0.2~0.5）
/usr/bin/python3 extract_characters.py 输入.png 输出/ --expand 0.3
```

### 参数说明

| 参数 | 默认 | 说明 |
|:---|:---:|:---|
| `input` | 必填 | 输入图片路径 |
| `output` | 输入同目录 | 输出目录（自动创建） |
| `--conf` | 0.10 | YOLOE 置信度阈值，越低检出越多 |
| `--expand` | 0.0 | 检测框扩大比例，0=原始框 |
| `--names` | `cartoon character, cartoon animal` | 识别类别，逗号分隔 |
| `--iou` | 0.3 | 去重 IoU 阈值，>0.3 视为同一角色 |

## 输出

- 每个角色一个 `角色_NN_类别.png`（RGBA 透明背景）
- 按 YOLOE 置信度从高到低排序
- mask 分数（SAM2）0.80-0.96 表示分割置信度高

## 工作原理

```
文字提示 "cartoon character"
    ↓ MobileCLIP 文本编码器（572MB，把文字转向量）
    ↓ YOLOE 扫描全图 → 检测框 + 类别 + 置信度
    ↓ IoU 去重（>0.3 合并同一角色）
    ↓ SAM2.1 用每个框做 box 提示 → 逐像素 mask
    ↓ 裁剪 + alpha 通道 → 透明 PNG
```

## 常见问题

- **报 CUDA kernel 错误**：venv/conda 的 torch 太新（如 2.13）不支持老 GPU（P102 算力 6.1）。用 `/usr/bin/python3`（torch 2.5.1+cu121）运行。
- **找不到 mobileclip_blt.pt / configs**：软链被破坏。重新执行：
  ```bash
  ln -sf code/sam2_code/sam2/configs configs
  ln -sf model/mobileclip/mobileclip_blt.pt mobileclip_blt.pt
  ```
- **检出的框带背景**：这是语义分割的正常现象。可试 `--expand 0`（默认）或调低 `--conf` 观察；若要更干净可对结果再人工筛选。
- **CPU 慢**：全流程在 CPU 跑约 1-2 分钟/图（YOLOE + SAM2 均 CPU）。有 GPU 时 torch 用 cuda 版会快很多。

## 与其他方案对比

| 方案 | 体积 | 文字识别 | 卡通识别效果 |
|:---|:---|:---|:---|
| **YOLOE + SAM2.1（本 skill）** | 748MB | ✅ | ✅ 最强（22框→15角色） |
| YOLO-World | 25MB | ✅ | ⚠️ 弱（4框） |
| YOLO26-seg | 135MB | ❌ 固定 COCO 80 类 | ❌ 不识别卡通 |
| Grounding-DINO + SAM2 | 811MB | ✅ | ✅ 好（11角色） |

## MobileCLIP 文本编码器变体（重要结论）

YOLOE 的文本编码器（把 "cartoon character" 转向量）**只有 blt 变体可用**：

| 变体 | 大小 | 卡通识别 |
|:---|:---|:---|
| s0 | 206MB | ❌ 0框 |
| s1 | 325MB | ❌ 0框 |
| s2 | 380MB | ❌ 0框 |
| **blt（默认）** | **572MB** | ✅ 22框 |

**实测结论**：s0/s1/s2 是独立训练的模型，语义能力不足，无法识别 "cartoon character" 等抽象类别。**必须用 blt**（572MB），这是 YOLOE 识别卡通角色的最低要求。

可通过 `--text-model s0/s1/s2` 参数切换，但除 blt 外均无法识别卡通角色。文件 `mobileclip_blt.pt` 已在 `model/mobileclip/`，软链到 skill 根目录供 YOLOE 相对路径加载。
