---
name: image-person-extraction
description: 基于 Meta SAM 3 的图片目标提取工具。当用户说"提取图片中的XX"、"抠图"、"分割"、"人物提取"、"提取角色"时触发。支持照片、卡通、插画、教材等任意风格，直接用自然语言描述目标，输出透明背景 PNG。Image target extraction using Meta SAM 3 — trigger on "extract character", "cutout", "segment", "抠图", "人物提取".
compatibility: opencode
metadata:
  audience: 视频制作者、教材处理
  workflow: 素材提取
---

# 图片目标提取 Skill (SAM 3)

## 概览

基于 **Meta SAM 3 (Segment Anything with Concepts, 840M)** 的文本提示词目标提取工具。

**无需 YOLO 检测**，直接用自然语言描述要提取的目标，SAM 3 会自动识别并逐像素分割，输出透明背景 PNG。

支持任意风格（照片、卡通、插画、教材），效果远好于 YOLO + SAM2 / rembg 方案。

## 触发条件

- 用户说"提取图片中的XX"、"抠图"、"分割"、"人物提取"
- 需要从图片中提取特定类别的物体（人物、动物、物品等），做视频素材
- 批量处理教材/漫画/照片中的人物或物体

## 目录结构与模型

Skill 根目录为 `image-person-extraction/`，完整结构：

```
image-person-extraction/
├── SKILL.md              # 本文档
├── extract_with_sam3.py  # 提取脚本（核心）
└── model/
    └── sam3/             # SAM 3 模型权重（HuggingFace 格式，约 3.2GB）
        ├── config.json
        ├── model.safetensors   # 3.3GB 主权重
        ├── processor_config.json
        ├── tokenizer_config.json
        └── tokenizer.json
```

### 模型来源（重要：新机器部署时）

SAM 3 模型权重来自 HuggingFace 官方仓库 **`facebook/sam3`**，对应 transformers 的 `Sam3Model` / `Sam3Processor`。

脚本固定从 `model/sam3/` 本地目录加载模型。**复制本 Skill 到其他机器时，必须把整个 `model/sam3/` 目录（约 3.2GB）一并拷走**，否则会报 `Sam3Model.from_pretrained() 找不到本地目录`。

如本地缺模型，可用以下命令从 HuggingFace 下载（需要网络，海外模型建议走代理）：

```bash
# 需先安装依赖（见下），然后：
python3 - <<'EOF'
from transformers import Sam3Model, Sam3Processor
import os
os.makedirs("model/sam3", exist_ok=True)
Sam3Model.from_pretrained("facebook/sam3").save_pretrained("model/sam3")
Sam3Processor.from_pretrained("facebook/sam3").save_pretrained("model/sam3")
print("模型已保存到 model/sam3/")
EOF
```

（若网速慢，也可直接 `git lfs clone https://huggingface.co/facebook/sam3` 后拷入 `model/sam3/`。）

## 依赖安装

首次使用需安装依赖（Python 3.9+，建议 3.10+）：

```bash
pip install torch transformers pillow opencv-python numpy
```

- GPU 版 PyTorch（推荐，速度快 10 倍以上）：按 https://pytorch.org/get-started/locally/ 选择 CUDA 对应命令，例如：
  `pip install torch --index-url https://download.pytorch.org/whl/cu121`
- 纯 CPU 环境可只装 CPU 版（`pip install torch` 默认即可），速度较慢但可用。

## 执行流程

```bash
# 提取人物（默认：自动检测 GPU，有 GPU 用 GPU）
python3 extract_with_sam3.py \
  --input 图片.png \
  --output ./输出目录 \
  --prompt "a person, a child, a cartoon character"

# 提取动物（狗、猫、老鼠、狐狸）
python3 extract_with_sam3.py \
  --input 图片.png \
  --output ./输出目录 \
  --prompt "a dog, a cat, a mouse, a fox"

# 强制使用 CPU（例如无 GPU 的机器）
python3 extract_with_sam3.py \
  --input 图片.png \
  --output ./输出目录 \
  --prompt "a person" \
  --device cpu
```

## 参数说明

| 参数 | 默认值 | 说明 |
|:---|:---:|:---|
| `--input` / `-i` | 必填 | 输入图片路径（支持 .jpg/.png/.webp 等） |
| `--output` / `-o` | `./人物提取结果` | 输出目录（不存在会自动创建） |
| `--prompt` / `-p` | 必填 | 文本提示词，**多个目标用英文逗号分隔**，逐个独立检测 |
| `--threshold` | **0.75** | 检测置信度阈值，越高越严格（只保留高置信目标） |
| `--mask-threshold` | `0.25` | 掩码二值化阈值，越低掩码越完整 |
| `--device` | `auto` | 运行设备：`auto`（自动，有 GPU 用 GPU）/ `cuda`（强制 GPU）/ `cpu`（强制 CPU） |

## 提示词技巧（重要）

- **多个目标必须用英文逗号 `,` 分隔**，脚本会按每个提示词分别检测再合并去重。不要把多个词塞进一句（如 `"a dog and a cat"` 效果差）。
- 组合效果最佳：`"a boy, a girl, a dog, a cat"`（每个词单独一行检测，结果更准）。
- 目标不确定时，可多用近义词扩大召回：`"a person, people, a child, a cartoon character"`。
- 提示词越具体越好：`"a red dog"` 优于 `"a dog"`。
- **单名词容易检测不到**（如 `fox`、`monkey`、`cat` 单独作提示词常返回 0 结果），遇到这种情况加修饰词：`"a cartoon fox woman wearing sunglasses"`、`"a cartoon monkey boy wearing cap"`。
- **卡通角色易混淆**：SAM3 可能把猴子识别成 dog、猫识别成其他动物。提示词检测结果要配合 Step 2 的逐张观察，以人眼判断为准。

## 置信度阈值选择

| 场景 | 推荐阈值 |
|:---|:---:|
| 严格提取（只取最明显、最干净的目标） | 0.8 |
| 标准提取（**默认**，平衡数量与准确度） | **0.75** |
| 全面提取（尽可能多检测，会带入少量误检） | 0.5 ~ 0.6 |

## 标准工作流程（角色提取 + 三视图，推荐）

当任务是"从图中提取角色 / 人物素材"（教材、漫画、动画截图）时，**必须**按以下四步走：

### Step 1：查看原图，确定角色列表

- 先 `Read` 原图（注意：若当前模型不支持图片输入，需用 `--device cuda` 跑脚本，或借助视觉 API/工具看图）。
- 列出图中出现的**所有**角色，命名规则：
  - **有名字的用名字**（教材/官方设定，如 Mrs Fox、Bobby、Sam、Miss Li）。
  - **没名字的用形象**（如 dog_student、rabbit、monkey）。
- 先产出角色列表给用户确认，再开始提取。
- **重要**：不要把形象认错。卡通角色（如"戴帽子的棕色角色"）可能是猴子而非狗，观察时要确认角色特征，必要时请用户确认或对比教材角色页。

### Step 2：逐一提取，逐张观察判断

- 按角色列表**逐个角色**单独提取（一次一个 `--prompt`，不要一次全提）。
- 提示词从简到具体逐步尝试：`"cartoon mouse"` → 检测不到再换 `"a cartoon fox woman wearing sunglasses"`。单名词太简单时（如 `fox`、`monkey`）经常检不出，加修饰词（颜色、服装、身份）可提高命中。
- 同一角色检出多张时，**不要直接用最高置信度那张**，而是**从置信度高到低依次 `Read` 图片自己判断**：
  - 第一张符合要求 → 直接保留，后面的不再看。
  - 第一张不对（残影、错角色、侧面角度的废图）→ 继续看下一张，直到找到完整正确的角色图。
- 判断标准：角色主体完整、正面/主要姿态、无截断、背景干净。

### Step 3：重命名

- 保留的正确图片用 **Step 1 的角色名**重命名：`Mrs_Fox.png`、`Bobby.png`、`Sam.png`、`Dog_student.png`、`Rabbit.png` 等。
- 删除该角色其余未保留的候选图，再进行下一个角色。

### Step 4：制作三视图（角色参考图）

- 三视图（正/侧/背三视角）通过**生图 API**（如 agy/Gemini、GRS、即梦等）制作，参考提取出的角色 PNG 保持外观一致。
- **必须先征得用户允许才能调生图 API**，未经允许不制作三视图。
- 得到允许后，用保留的角色 PNG 作为参考图，让生图 API 输出该角色的正面/侧面/背面三视图，命名 `角色名_三视图.png`。
- **提示词规范：角色 + 描述 + 参考图片**。三者缺一不可：
  - **角色**：角色名字或身份（如 `Mrs Fox, the teacher fox`、`Bobby, the cartoon mouse`）。
  - **描述**：外观细节（颜色、服装、配饰、姿态，如 `wearing pink dress and sunglasses, full body, front view, side view, back view`）。
  - **参考图片**：必须附上 Step 3 提取出的角色 PNG 作为参考图，保证外观一致性。
- 示例：`"Mrs Fox, a cartoon fox teacher wearing pink dress and sunglasses, full body three-view (front/side/back), same character design as reference image"` + 参考图 `Mrs_Fox.png`。
- 参考已有资产格式：若项目内已有其他角色的三视图（如 `人物资产/` 目录下的 `角色名_三视图.png`），保持同样的命名与版式。
- 三视图可放入项目的角色资产目录（如 `01_资产/角色立绘/` 或 `人物资产/`），并在 `资产文件.md` 中登记。

## 去重与输出说明

- **自动去重**：多个提示词重复检出同一目标时，按全图 mask 重叠率 IoU > 0.5 合并，只保留置信度最高的一份。
- 每张图片输出 `人物-N.png`（RGBA 透明背景，N 按置信度从高到低排序），文件带 alpha 通道，可直接叠加到任意背景。
- 后处理：形态学闭运算补洞（15x15, 3次）+ 形态学开运算去噪（15x15, 1次）+ 高斯模糊平滑边缘（5x5）。

## 后处理参数（脚本内固定）

| 处理 | 参数 | 作用 |
|:---|:---:|:---|
| MORPH_CLOSE | 15x15, 3次 | 填补孔洞 |
| MORPH_OPEN | 15x15, 1次 | 去除噪点 |
| GaussianBlur | 5x5 | 平滑边缘锯齿 |

## 常见问题

- **`from_pretrained` 报找不到模型**：`model/sam3/` 目录缺失或不全，按上面"模型来源"一节重新下载/拷贝。
- **提示词检测不到目标**：降低 `--threshold`（如 0.5），或改用更具体的提示词。
- **同一目标被提取多份**：已内置去重；若仍重复，多为目标本身非常相似，可自行按置信度筛选。
- **有 GPU 但显示 cpu**：确认 `torch.cuda.is_available()` 为 True（`python3 -c "import torch; print(torch.cuda.is_available())"`），装 CUDA 版 torch；或显式加 `--device cuda`。
