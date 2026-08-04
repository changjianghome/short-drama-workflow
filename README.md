# short-drama-workflow

英语教材短剧制作完整工作流：教材对话 → 人物识别 → 环境母图 → 四宫格分镜 → LTX JSON → 一句话一个视频。

AI short-drama production workflow for English teaching content (textbook dialogues → finished video), split into **6 decoupled stages** with phase-gate control.

## 包含的 Skill（平级并列，互不包含）

本仓库是**平级 skill 集合**，`ai-film-6-stage` 只是通过相对路径（`../<skill名>/...`）**依赖**其他 skill，不包含它们。

| Skill | 用途 |
|-------|------|
| `ai-film-6-stage` | 六阶段制作主流程（总入口，阶段门禁强制） |
| `runninghub-api` | RunningHub 余额查询 + LTX 2.3 图生视频 + JSON 生成规则 |
| `grs-image-api` | GRS 四宫格分镜生成 + 四宫格切分 |
| `image-person-extraction` | SAM3 从教材插图中抠取人物 |
| `yoloe-sam2-extract` | **YOLOE + SAM2.1 自动识别并抠取卡通角色**（文字提示，无需打点） |
| `mac-say` | 本机 Mac 语音播报通知（≤30字） |
| `feishu-bot` | 成品发送到飞书（可选） |

## 六阶段总览

| # | 阶段 | 工具 |
|---|------|------|
| 1 | 准备（建目录、人物清单、剧本、场景设计、Clip分镜） | 人工 |
| 2 | 人物资产（用户提供/提取/生成，名字验真）+ 环境母图 | **仅 RunningHub** |
| 3 | 四宫格提示词（每 4 个 Clip 一组，手写） | 人工 |
| 4 | 生成四宫格 + 切分单图 | **GRS** |
| 5 | 每张切分图一个 LTX JSON（先看真实图片再写） | 规则 |
| 6 | 视频生成（一句话一个视频）+ 拼接 + 压缩 | RH LTX 2.3 |

## 阶段门禁

- **没有完成本阶段任务，不允许查看下一阶段文件的内容。**
- 门禁状态记录在 `ai-film-6-stage/流程进度.md`（`⬜` → `✅`）。
- 进入阶段 N 前运行：`bash 流程门禁检查.sh N <项目目录>`
  - 输出「✅ 前置阶段全部完成」→ 继续；
  - 输出「⛔ 禁止继续」→ 立即停止，先完成前置阶段，禁止查看当前及后续阶段内容。

## 快速开始

```bash
# 1. 克隆仓库，保持所有 skill 平级（同一父目录）
git clone <仓库地址> short-drama-workflow

# 2. 配置密钥
cp .env.example .env       # 填写 RUNNINGHUB_API_KEY / GRSAI_API_KEY 等
set -a; source ./.env; set +a

# 3. 从阶段1开始
cd ai-film-6-stage
bash 流程门禁检查.sh 1 .
```

## 安全说明

- **不包含任何真实密钥**。`query_account_api.py` 不再内置账号 Key——通过环境变量 `RH_ACCOUNTS_JSON` 或 `runninghub-api/scripts/.accounts.json`（已被 git 忽略）提供。
- `.env`、`.accounts.json`、`model/` 已被 `.gitignore` 排除，**严禁提交**。
- 本机内网 IP 已替换为占位符 `<MAC_SAY_PRIMARY_IP>` / `<MAC_SAY_BACKUP_IP>`，可用 `MAC_SAY_URL` 环境变量覆盖。
- `image-person-extraction` 的模型权重（约 3.2 GB，`facebook/sam3`）**未包含**在仓库中，下载方式见其 SKILL.md。

## 环境要求

- Python 3、Pillow（`pip install pillow`）、ffmpeg
- RunningHub API Key（必需）；GRS API Key（必需）；飞书机器人 / Mac 语音服务（可选）
