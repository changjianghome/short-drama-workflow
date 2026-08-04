---
name: runninghub-api
description: Trigger this skill when calling ComfyUI workflows and AI WebApps hosted on RunningHub.ai or RunningHub.cn. Supports task submission, status query polling, and image/video download.
---

# RunningHub ComfyUI API Skill

本技能为 Agent 提供调用 RunningHub 平台托管的 ComfyUI 工作流和 AI 应用（WebApp）的能力。

当用户提出测试、集成或自动调用 RunningHub 上的 AI 工作流时，应触发并严格遵循本技能的规范。

---

## 1. 核心设计原则

1.  **零外部依赖**：优先使用 Python 原生库（`urllib`）编写脚本。
2.  **Unicode 安全编码**：下载图片/视频 URL 必须先经过 `urllib.parse.quote(url, safe='/:?=&')` 编码以防 unicode 报错。
3.  **密钥安全**：使用环境变量 `RUNNINGHUB_API_KEY` 传递密钥，禁止代码中硬编码。
4.  **链接有效期**：生成的云端链接仅 24 小时有效，任务成功后需立即自动下载本地落盘。
5.  **并发限制**：**一个 API Key 同一时间只能运行一个接口调用**。多并发任务必须使用不同的 API Key 组合。
6.  **RH 余额自动追踪**：调用脚本时加 `--project-dir wk/项目名`，成功后自动从 `.env` 扣除 RH（视频 5 RH/s、图片 7 RH/张），并更新 `API用量追踪.md`。无需手动操作。
7.  **⚠️ 每轮对话首次使用必须先查余额**：**每轮对话第一次调用 RunningHub API 前，必须先执行 `scripts/query_account_api.py` 查询当前 API Key 的实际余额**（`.env` 路径通过 `RH_ENV_PATH` 环境变量指定，默认当前目录 `.env`）。确认余额充足后再提交任务。
8.  **账号地域隔离**：WebApp 分国内版(`runninghub.cn`)/国际版(`runninghub.ai`)。`webapp not exists(901)` 优先怀疑 key 与应用地域不匹配。`query_account_api.py --all` 的多账号表不再内置（分享安全），本地维护在 `scripts/.accounts.json` 或环境变量 `RH_ACCOUNTS_JSON` 中。
9.  **`.env` 解析**：`.env` 行尾常带中文注释（如 `KEY=xxx  # 备注 | 600 RH`），提取键值时用 `sed 's/^KEY=//;s/#.*//' | tr -d ' \r\n'` 去注释去空白，并校验长度（RH key 32 位 hex）。
10. **rh_tracker 路径**：`rh_tracker.py` 默认读当前目录 `.env`，可用 `export RH_ENV_PATH=<你的.env路径>` 覆盖；或加 `--no-track-rh` 跳过追踪并手动补记 `API用量追踪.md`。

---

## 5. RH 积分消耗参考

| 任务类型 | 预估消耗 | 说明 |
|:---|:---|:---|
| **LTX 2.3 图生视频** | **~5 RH/秒** | 基于 2026-07-19 实测数据（866 RH / ~260s 成功视频） |
| **图片生成** (Z_image/单图编辑等) | **~7 RH/张** | 基于实测估算 |
| **卡通儿童教材插画批量出图** | **~0.3 RH/张** | 2026-08-02 实测：256 尺寸 42 张耗 13 RH、50 张耗 12 RH。批量预算按 0.3 RH/张 估算 |

> [!IMPORTANT]
> 加 `--project-dir` 后，脚本在**任务提交前**先检查余额：
> - 余额不足 → 🚨 告警 + 取消任务（`exit 1`）
> - 余额充足 → 显示预估消耗和剩余 → 继续执行
> - 任务成功后自动扣除并更新 `.env` + `API用量追踪.md`

## 2. 工作流及专属脚本列表

后续新增工作流时，请在此表中追加，并统一在 `scripts/` 目录下放置其“专属调用脚本”和“调用说明文档”：

| 工作流/应用名称 | WebApp ID | 专属调用脚本 | 调用说明文档 |
| :--- | :--- | :--- | :--- |
| **Z_image-快速版本-基础工作流** | `2076895906833715201` | [Z_image_快速版本_基础工作流.py](file:///Users/wuwu/Documents/project_backup/wk/runninghub-api/scripts/Z_image_%E5%BF%AB%E9%80%9F%E7%89%88%E6%9C%AC_%E5%9F%BA%E7%A1%80%E5%B7%A5%E4%BD%9C%E6%B5%81.py) | [Z_image_快速版本_基础工作流_说明.md](file:///Users/wuwu/Documents/project_backup/wk/runninghub-api/scripts/Z_image_%E5%BF%AB%E9%80%9F%E7%89%88%E6%9C%AC_%E5%9F%BA%E7%A1%80%E5%B7%A5%E4%BD%9C%E6%B5%81_%E8%AF%B4%E6%98%8E.md) |
| **2511单图参考编辑_bf16-基础工作流** | `2076911428203798530` | [单图参考编辑_bf16_基础工作流.py](file:///Users/wuwu/Documents/project_backup/wk/runninghub-api/scripts/%E5%8D%95%E5%9B%BE%E5%8F%82%E8%80%83%E7%BC%96%E8%BE%91_bf16_%E5%9F%BA%E7%A1%80%E5%B7%A5%E4%BD%9C%E6%B5%81.py) | [单图参考编辑_bf16_基础工作流_说明.md](file:///Users/wuwu/Documents/project_backup/wk/runninghub-api/scripts/%E5%8D%95%E5%9B%BE%E5%8F%82%E8%80%83%E7%BC%96%E8%BE%91_bf16_%E5%9F%BA%E7%A1%80%E5%B7%A5%E4%BD%9C%E6%B5%81_%E8%AF%B4%E6%98%8E.md) |
| **卡通儿童教材插画** | `2083566214957322242` | [卡通儿童教材插画.py](scripts/卡通儿童教材插画.py) | [卡通儿童教材插画_说明.md](scripts/卡通儿童教材插画_说明.md) |
| **RH 批量文生图**（通用） | 任意 | [rh_batch_image.py](scripts/rh_batch_image.py) | 30min 超时 + 断点下载；大批量(>40张)优先用此脚本，勿用内置 600s 超时脚本 |
| **ltx2.3_无导演台_纯参数** | `2077031364116959233` | [ltx2.3_无导演台_纯参数.py](file:///Users/wuwu/Downloads/wk/runninghub-api/scripts/ltx2.3_%E6%97%A0%E5%AF%BC%E6%BC%94%E5%8F%B0_%E7%BA%AF%E5%8F%82%E6%95%B0.py) | [ltx2.3_无导演台_纯参数_说明.md](file:///Users/wuwu/Downloads/wk/runninghub-api/scripts/ltx2.3_%E6%97%A0%E5%AF%BC%E6%BC%94%E5%8F%B0_%E7%BA%AF%E5%8F%82%E6%95%B0_%E8%AF%B4%E6%98%8E.md) |
| **卡通儿童教材插画** | `2083566214957322242` | [卡通儿童教材插画.py](scripts/卡通儿童教材插画.py) | [卡通儿童教材插画_说明.md](scripts/卡通儿童教材插画_说明.md) |

---

## ⚠️ LTX 2.3 重要特性：音视频同步生成

**LTX 2.3 是音视频模型，会同时生成视频 + 背景音乐 + 人物声音。**

使用 LTX 2.3 时，提示词中**必须**包含音频描述（`audio: ...`），否则生成的视频将没有声音。

### 音频描述要求

每个 Shot 末尾必须追加 `audio: ...`，包含以下至少2项：
1. 环境音（风声、雨声、城市噪音等）
2. 拟音/动作音效（脚步、碰撞、摩擦等）
3. 人物声音（呼吸、叹息、笑声、说话等）
4. 背景音乐（钢琴、弦乐、吉他等）

### 示例

```
Shot 1 medium shot, a girl sits at desk then picks up phone as it vibrates, 
audio: phone vibration buzzing, soft piano melody, quiet breathing, distant traffic
```

详见 [ltx2.3-JSON生成规则.md](scripts/ltx2.3-JSON生成规则.md) 的 H9.3-d 章节。

---

## 🔴 生成 LTX JSON 提示词前的强制流程（必须先做！）

**每次要生成 LTX 视频（图生视频）前，必须先读规则 + 用生成脚本，禁止凭感觉手写 JSON。**

### 强制顺序

```
第1步：完整阅读 scripts/ltx2.3-JSON生成规则.md（必须！重点：H9 转场连续性、台词嵌入、角色命名、W3 数据自洽）
第2步：用通用脚本 gen_ltx_json.py 生成（禁止手写 JSON 结构）
第3步：生成后核对——global_prompt 只含画面实际角色、local_prompts 含台词原文+audio
```

### 第2步：使用通用生成脚本 gen_ltx_json.py

脚本路径：`scripts/gen_ltx_json.py`（与 ai-film-industrialization-skill 同步）
模板：`scripts/project.example.yaml`

```bash
# 1. 复制模板，填写本项目角色清单 + Clip清单
cp scripts/project.example.yaml 提示词/project.yaml

# 2. 预览（不写文件，检查帧数/角色数）
python3 scripts/gen_ltx_json.py -c 提示词/project.yaml -o 提示词/ --dry-run

# 3. 正式生成全部 LTX JSON
python3 scripts/gen_ltx_json.py -c 提示词/project.yaml -o 提示词/
```

### 配置填写要点（防多出人物/防角色混淆）

| 字段 | 必填 | 说明 |
|:---|:---:|:---|
| `present_chars` | ✅ | 该画面**实际出现**的角色（四宫格切分后逐格核对） |
| `positions` | 多角色必填 | 每角色画面位置（left/right/beside/facing），脚本自动写入 global/local |
| `speaker` | 有台词必填 | 说话人（用 characters 标准名），脚本自动带完整外貌+位置 |
| `line` | 有台词必填 | 台词原文（英文课本用英文，中文剧本用中文） |
| `audio` | ✅ | 环境音/音效/人声/背景乐，≥2项 |

### 生成后核对清单

- [ ] 每 clip 的 `global_prompt` 只含 `present_chars` 对应角色，末尾有 `ONLY these character(s)...`
- [ ] 多角色画面有 `positions` 位置关系
- [ ] 有台词段 `local_prompts` 含台词原文（英文单引号包裹）
- [ ] 每段含 `audio: ...`
- [ ] `segment_lengths` / `frame_indices` 满足 W3 自洽（sum=总帧数）

---

---

## 4. 错误码参考

调用接口如遇异常响应，请查阅同目录下的 [错误码说明.md](错误码说明.md) 文件，根据错误码定位问题原因并参考处理建议。

---

## 3. 调用脚本使用说明

每个工作流的专属脚本均已内置其 `WEBAPP_ID` 且封装了友好的命名参数，**调用时不需要再传入复杂的 JSON 结构或 App ID**。

### 调用示例（以 Z_image-快速版本 为例）：

```bash
# 1. 导出 API Key 环境变量
export RUNNINGHUB_API_KEY="您的_32位_API_KEY"

# 2. 带 RH 追踪的完整调用（推荐）
python3 scripts/Z_image_快速版本_基础工作流.py \
  --prompt "A futuristic city at sunset" \
  --resolution "768x512 (3:2) (横屏)" \
  --project-dir "wk/项目名"

# 3. 不想自动扣减 RH 时加 --no-track-rh
python3 scripts/Z_image_快速版本_基础工作流.py \
  --prompt "test" \
  --no-track-rh
```

#### 脚本参数说明：
1.  **正面提示词 (`--prompt` / `-p`，必填)**：
    *   描述画面主体内容的自然语言，越详细生动效果越佳。
2.  **尺寸 (`--resolution` / `-r`，可选)**：
    *   默认值：`"768x512 (3:2) (横屏)"`。
    *   > [!IMPORTANT]
    *   > **尺寸参数具有极其严格的固定格式要求，填错任何一个字符或空格都会导致生成尺寸错误甚至接口报错。**
    *   支持的固定合法尺寸格式列表包括：
        *   `"768x512 (3:2) (横屏)"` (默认)
        *   `"1536x1024 (3:2) (横屏)"`
        *   `"1280x720 (16:9) (横屏)"`
        *   `"1920x1080 (16:9) (横屏)"`
        *   `"1024x1024 (1:1) (方形)"`
        *   `"768x768 (1:1) (方形)"`
        *   `"720x1280 (9:16) (竖屏)"`
        *   `"1080x1920 (9:16) (竖屏)"`
        *   `"1024x1536 (2:3) (竖屏)"`
3.  **负面提示词 (`--negative` / `-n`，选填)**：
    *   用于排除画面中不希望出现的元素（如：畸形肢体、模糊画质等）。
    *   脚本内已预置了通用的负面过滤词，通常不需要手动指定，除非有特定排除需求。
4.  **API Key (`--apikey`，选填)**：
    *   RunningHub 的 API Key。
    *   推荐通过设置系统环境变量 `RUNNINGHUB_API_KEY` 来传递，避免在命令行或脚本中直接写明。
5.  **项目目录 (`--project-dir`，选填)**：
    *   用于自动更新 `wk/项目名/API用量追踪.md` 和 `.env` 中的 RH 余额。
    *   指定后在任务成功后自动扣除对应 RH（图片 7 RH/张，视频 5 RH/秒）。
6.  **禁用追踪 (`--no-track-rh`，选填)**：
    *   跳过 RH 余额自动扣减和记录。

### LTX 2.3 专属参数

7.  **视频时长 (`--duration` / `-d`，选填)**：
    *   手动指定视频时长（秒），用于 RH 扣减计算。
    *   若不指定，自动从 `all_segment_lengths / 25 FPS` 推算。
