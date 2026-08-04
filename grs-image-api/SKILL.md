---
name: "grs-image-api"
description: "GrsAI 绘图 API 的独立封装。提供图片生成、参考图压缩、任务提交与轮询下载的完整能力。当用户要求作图或生成图片时触发。"
---

# GrsAI 通用作图 API

---

## ⚠️ 错误记录（必读）

每次使用本 Skill 时，必须注意以下常见错误：

1. **WebP/GIF/PNG 格式未转换**：必须先转为 JPEG，否则 API 无法识别参考图
2. **多角色参考图未标注**：合并参考图必须加彩色标签条标注角色名
3. **模型选择错误**：复杂多角色场景用 gpt-image-2，简单场景用 nano-banana-fast

---

# GrsAI 通用作图 API

## 功能概述

提供 GrsAI `gpt-image-2` 模型的完整作图能力封装：
- 文生图（纯 prompt 生成）
- 图生图（参考图 + prompt）
- 支持多参考图（背景图、角色图等）
- 自动图片压缩（Base64）、异步提交、轮询下载

## 前置准备

### API Key 配置

在 `.env` 文件中写入你的 API Key：
一般已经在当前项目 env 中提供 key，自行获取
```bash
GRSAI_API_KEY=sk-your-key-here
```

> API 官网：https://grsai.com/zh
> `.env` 已写入 `.gitignore` 规则（如有），分享时删除 `.env` 即可，脚本内不包含任何硬编码 Key。

## 核心脚本

技能内提供三个职责单一、互不干涉的独立脚本：

1. **`nano_banana_draw.py`** — 专用于 **`nano-banana-fast`** 及 `nano-banana` 系列模型 ⭐ **首选推荐**
2. **`api_draw.py`** — 专用于 **`gpt-image-2` / `gpt-image-2-vip`** 模型（高质量但较慢、较贵）
3. **`query_credits.py`** — 查询 GrsAI 积分余额（API Key 直查，无需浏览器）

### 模型选择策略（重要）

| 优先级 | 模型 | 脚本 | 速度 | 成本 | 适用场景 |
|:---:|:---|:---|:---:|:---:|:---|
| ⭐ 首选 | `nano-banana-fast` | `nano_banana_draw.py` | 快 | 低 | 日常作图、分镜图、环境图、参考图迭代、批量生成 |
| 备选 | `gpt-image-2` | `api_draw.py` | 慢 | 高 | 角色三视图、需要极高细节的精品图、需要特殊风格的场景 |

> **默认规则**：所有图片生成任务，优先使用 `nano_banana_draw.py`（nano-banana-fast 模型）。
> 仅当用户明确要求"高质量"或"精品图"，或 nano-banana-fast 效果不满足需求时，才使用 `api_draw.py`（gpt-image-2 模型）。

---

### 命令行用法

#### ① 调用 `nano-banana-fast`（首选，快速低成本）⭐
```bash
python3 .agents/skills/grs-image-api/nano_banana_draw.py \
  --prompt "A cute golden retriever in a field of sunflowers, 8k, photorealistic" \
  --aspect_ratio "3:2" \
  --image_size "1K" \
  --output /path/to/output.png
```

#### ② 调用 `nano-banana-fast`（带参考图，最多 4 张）
```bash
python3 .agents/skills/grs-image-api/nano_banana_draw.py \
  --prompt "A 2x2 grid storyboard based on reference images..." \
  --aspect_ratio "3:2" \
  --image_size "1K" \
  --image1 /path/to/char_ref.png \
  --image2 /path/to/bg_ref.png \
  --image3 /path/to/char2_ref.png \
  --image4 /path/to/prop_ref.png \
  --output /path/to/output.png
```

> **多参考图说明**：两个脚本 CLI 均支持 **最多 4 张**参考图（`--image1` ~ `--image4`），按需传任意 1~4 张即可；底层 `draw()` 函数的 `reference_images` 列表则支持任意数量。

#### ③ 调用 `gpt-image-2`（高质量精品图，较慢）
```bash
python3 .agents/skills/grs-image-api/api_draw.py \
  --prompt "A luxury study room with warm lighting, cinematic, photorealistic, 8k" \
  --resolution "1536x1024" \
  --output /path/to/output.png
```

#### ④ 调用 `gpt-image-2`（带参考图，最多 4 张）
```bash
python3 .agents/skills/grs-image-api/api_draw.py \
  --prompt "A character sheet showing 3 views..." \
  --resolution "1536x1024" \
  --image1 /path/to/ref1.png \
  --image2 /path/to/ref2.png \
  --image3 /path/to/ref3.png \
  --image4 /path/to/ref4.png \
  --output /path/to/output.png
```

### Python API 调用

```python
# ⭐ 首选：nano-banana-fast
from nano_banana_draw import draw as nano_draw

# 文生图
nano_draw(
    prompt="A luxury study room, cinematic lighting, photorealistic, 8k",
    output_path="/path/to/output.png",
    aspect_ratio="3:2",
    image_size="1K"
)

# 图生图（带参考图）
nano_draw(
    prompt="A 2x2 grid storyboard based on reference images...",
    output_path="/path/to/output.png",
    aspect_ratio="3:2",
    reference_images=["/path/to/bg.png", "/path/to/char1.png"]
)

# 备选：gpt-image-2（高质量）
from api_draw import draw

draw(
    prompt="A character sheet showing 3 views...",
    output_path="/path/to/output.png",
    resolution="1536x1024",
    reference_images=["/path/to/ref.png"]
)
```

### nano_banana_draw.py 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---:|:---:|:---|
| `--prompt` | str | 必填 | 作图提示词 |
| `--output` | str | 必填 | 图片保存路径 |
| `--aspect_ratio` | str | `3:2` | 图片比例（支持 `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `5:4`, `4:5`, `21:9`） |
| `--image_size` | str | `1K` | 分辨率尺寸（`1K` / `2K` / `4K`） |
| `--image1` | str | 无 | 参考图 1 路径 |
| `--image2` | str | 无 | 参考图 2 路径 |
| `--image3` | str | 无 | 参考图 3 路径 |
| `--image4` | str | 无 | 参考图 4 路径 |

---

### 积分余额查询

#### 命令行用法
```bash
# 默认读取 .env 的 GRSAI_API_KEY，全球节点
python3 .agents/skills/grs-image-api/query_credits.py

# 指定 key / 国内节点 / JSON 输出
python3 .agents/skills/grs-image-api/query_credits.py --api-key sk-xxxx --cn --json
```

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---:|:---:|:---|
| `--api-key` | str | `.env` 中的 `GRSAI_API_KEY` | GrsAI API Key |
| `--cn` | flag | 关 | 使用国内节点 `grsai.dakka.com.cn` |
| `--json` | flag | 关 | 以 JSON 格式输出原始数据 |

- **接口**: `POST https://grsaiapi.com/client/openapi/getAPIKeyCredits`（请求体 `{"apiKey": "sk-xxx"}`）
- **返回**: `data.credits` 为当前积分余额；积分不足 440（nano-banana-fast 单次价）时脚本会给出警告
- **用量参考**（单次生成消耗积分）: `nano-banana-fast`/`nano-banana-2-lite` 440 · `gpt-image-2` 600 · `nano-banana-2` 1200 · `nano-banana-pro*` 1800+

---

## 1. 接口配置

### 支持的图片分辨率（aspectRatio）

参数格式为 `宽x高`（如 `1536x1024`）。支持以下分辨率：

| 分辨率 | 比例 |
|--------|------|
| 1024×1024 | 1:1（方形） |
| 1672×941 | 16:9（横屏） |
| 941×1672 | 9:16（竖屏） |
| 1443×1090 | 约 4:3 |
| 1090×1443 | 约 3:4 |
| 1536×1024 | 约 3:2（横屏） |
| 1024×1536 | 约 2:3（竖屏） |
| 1408×1120 | 约 5:4 |
| 1120×1408 | 约 4:5 |
| 1920×832 | 约 21:9（超宽横屏） |
| 832×1920 | 约 9:21（超宽竖屏） |
| 1792×896 | 约 2:1（宽屏） |
| 896×1792 | 约 1:2（竖宽屏） |

| 项目 | 值 |
|------|-----|
| API 地址 | `POST https://grsaiapi.com/v1/api/generate` |
| 备用地址 | `POST https://grsai.dakka.com.cn/v1/api/generate` |
| 结果轮询 | `GET https://grsaiapi.com/v1/api/result?id=<task_id>` |
| 请求超时 | 600 秒（10 分钟） |
| 模型 | `gpt-image-2` / `gpt-image-2-vip` |
| 认证 | `Authorization: Bearer <API_KEY>` |

### 请求体结构

```json
{
  "model": "gpt-image-2",
  "prompt": "作图提示词",
  "aspectRatio": "1536x1024",
  "images": ["base64编码或URL的参考图1", "base64编码或URL的参考图2"],
  "replyType": "async"
}
```

---

## 2. 参考图预处理规范

将本地图片传入 `urls` 前必须执行压缩：

1. **格式转换（关键！）**：统一转 **JPEG**，RGBA 先转 RGB
   - ⚠️ **WebP、GIF、PNG 透明图等格式必须先转为 JPEG**，否则 API 可能无法识别参考图，导致生成结果与参考图完全不一致
   - 转换示例：
     ```python
     from PIL import Image
     img = Image.open('ref.webp').convert('RGB')
     img.save('ref.jpg', 'JPEG', quality=95)
     ```
2. **尺寸缩放**：最大边缩放至 **512 像素**以内，Lanczos 滤波，保持宽高比
3. **压缩质量**：**85%**
4. **Base64 编码**：将 JPEG 字节流编码后放入 `urls` 数组
5. **目标体积**：每张参考图 Base64 体积 ~**50KB**

### 多角色参考图合并与标注规范（重要！）

当一张参考图中包含**多个角色**时，必须在图片上添加文字标注，标明每个角色的名称和位置，否则模型会混淆角色身份。

#### 规则

1. **单角色参考图**：无需额外标注，prompt 中说明即可
2. **多角色合并参考图（2个及以上）**：
   - 必须将多张角色三视图**上下拼接**为一张图
   - 每个角色上方必须添加**彩色标签条**，写明：
     - 角色序号（1. / 2. / 3.）
     - 角色英文名 + 中文名
     - 核心特征（如"round hamster + knife + shield"）
   - 标签条颜色区分不同角色（如红、蓝、黄）
3. **Prompt 中必须对应说明**：
   - `Use reference image 2 for: 1. Daodun Dog (刀盾狗), 2. Gugu Penguin (小企鹅), 3. Banana Cat (香蕉猫)`

#### 合并参考图代码模板

```python
from PIL import Image, ImageDraw, ImageFont

def create_labeled_reference(char_images: list, output_path: str, label_h: int = 40):
    """
    将多个角色三视图合并为一张带标注的参考图
    char_images: [(path, label, color), ...]
    """
    images = [(Image.open(p).convert('RGB'), label) for p, label, _ in char_images]
    colors = [c for _, _, c in char_images]
    w = max(img.width for img, _ in images)
    total_h = sum(label_h + img.height for img, _ in images)
    
    combined = Image.new('RGB', (w, total_h), (255, 255, 255))
    draw = ImageDraw.Draw(combined)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28)
    
    y = 0
    for i, ((img, label), color) in enumerate(zip(images, colors)):
        # 标签条
        draw.rectangle([(0, y), (w, y + label_h)], fill=color)
        draw.text((10, y + 5), f'{i+1}. {label}', fill=(0, 0, 0), font=font)
        # 角色图
        combined.paste(img, ((w - img.width) // 2, y + label_h))
        y += label_h + img.height
    
    combined.save(output_path, quality=95)
    return output_path

# 使用示例
create_labeled_reference([
    ('刀盾狗_三视图.png', 'Daodun Dog (刀盾狗) - knife + shield', (255, 200, 200)),
    ('小企鹅_三视图.png', 'Gugu Penguin (小企鹅) - blue penguin', (200, 200, 255)),
    ('香蕉猫_三视图.png', 'Banana Cat (香蕉猫) - cat in banana peel', (255, 255, 200)),
], 'three_chars_labeled.jpg')
```

#### 错误示例 vs 正确示例

| 方式 | 结果 |
|:---|:---|
| ❌ 直接拼接无标注 | 模型分不清谁是谁，角色错乱 |
| ✅ 拼接 + 彩色标签条 | 模型准确识别每个角色 |

---

## 3. Prompt 书写规范（四宫格分镜图）

### 3.1 结构模板

```
A single 2x2 grid storyboard (4-panel comic strip) based on the reference images.

Use reference image 1 for background design of [场景描述].
Use reference image 2 for [角色名]'s face and clothing.
...

Panel 1: [左上] [景别] [物理动作和视觉构图描述]
Panel 2: [右上] [景别] [物理动作和视觉构图描述]
Panel 3: [左下] [景别] [物理动作和视觉构图描述]
Panel 4: [右下] [景别] [物理动作和视觉构图描述]

Maintain the visual style and character consistency from the reference images across all panels. Cinematic lighting, photorealistic, 8k.
```

### 3.2 规则要点

- **头部声明**：以 `A single 2x2 grid storyboard (4-panel comic strip)...` 开头
- **绑定参考图**：明确写出 `Use reference image 1 for ... Use reference image 2 for ...`
- **Panel 描述**：依次定义 Panel 1-4，描述物理动作、视觉构图、特写元素
- **时间戳**：如果包含手机屏幕内容，显式写明 `The screen has a red timestamp in the bottom right: "2025.05.20 23:14:07"`
- **结尾约束**：追加 `Maintain the visual style and character consistency...`
- **水印禁止**：prompt 末尾追加 `生成图片不要出现水印,字幕,标识等内容。`

---

## 4. 背景图生成规范

| 参数 | 值 |
|------|-----|
| prompt 来源 | 场景提示词 JSON 中的 `"提示词英文"` |
| aspectRatio | `"1536x1024"`（硬编码） |
| urls | `[]`（纯文生图，无参考图） |
| 输出命名 | `场X/背景Y.png` |

---

## 5. 异常处理与容错

### 重试策略
- 网络异常自动重试 3 次（间隔 2 秒）
- 轮询超时上限：20 分钟

### AI 监控要点
- **apikey credits not enough**：立即中止所有任务，通知用户
- **output_moderation**（内容违规）：AI 修改 prompt 去敏后重试
- **502 / timed out / generate image failed**（服务器崩溃）：跳过当前任务
  - 若**连续 4 个任务**遭遇此类错误 → 休眠 **30 分钟**后自动重试

---

## 6. 作图执行顺序

```
第一步：生成背景图（纯文生图）
  → python3 grs-image-api/api_draw.py --prompt "..." --output "场X/背景1.png"

第二步：生成四宫格图（带背景 + 角色参考图）
  → python3 grs-image-api/api_draw.py --prompt "..." --output "场X/X-1.png" \
    --image1 "场X/背景1.png" --image2 "人物/林逸风.png"

⚠ 必须先有背景图，再生成四宫格
```

---

## 7. 数据文件引用关系

```
人物/              ← 角色肖像 PNG（文件名即角色名）
├── 林逸风.png
└── 沈佳宜.png

场X/               ← 场次目录
├── 背景1.png      ← 背景图（由作图 API 生成）
├── X-1.png        ← 四宫格图（由作图 API 生成）
├── 场X场景提示词.json   ← 背景提示词来源
├── 场X详细事件描述.json  ← 分镜剧本来源
└── 场X绘图任务.json     ← 自动化批量参数配置
```

---

## 8. 四宫格图片切分工具

将 GRS 生成的四宫格图片自动切分为 4 张单独图片，去除白边/黑边分割线。

- **脚本**：`四宫格切分.py`
- **详细用法**：见 `四宫格切分_说明.md`
- **参数差异**：GPT 模型用 `-p 5`，Nano Banana 模型用 `-p 25`
