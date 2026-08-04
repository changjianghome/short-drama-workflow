---
name: ai-film-6-stage
description: 将任意英语教材/剧本制作为 AI 短片的六阶段工业化流程（英文教学短视频、对话提问场景）。当用户说"按六阶段流程制作""拆分流程""AI短片"且需分阶段执行时触发。六个阶段完全解耦：①准备→②人物与环境母图(RH)→③四宫格提示词→④四宫格制作(GRS)→⑤LTX JSON→⑥视频生成(RH，一句话一个视频)。每个阶段独立文件 + 阶段门禁，完成本阶段前禁止查看下一阶段。内置依赖 skill（runninghub-api / grs-image-api / image-person-extraction / mac-say / feishu-bot）自包含复制在本包 skills/ 下。Six-stage AI short-film production pipeline for English textbook content, stages decoupled with phase-gate control.
compatibility: opencode
metadata:
  audience: 英语教材教学视频制作者
  workflow: 教材→分镜→母图→四宫格→LTX→视频
---

# AI 短片六阶段制作流程 (ai-film-6-stage)

## 触发条件

- 用户提供英语教材/剧本，要求制作教学短视频（提问对话场景）
- 用户要求"按六阶段流程""分阶段制作""一个阶段一个文件"
- 需要从课本插图识别人物并建立人物资产

## 六阶段总览

| 阶段 | 文件 | 做什么 | 用什么 |
|------|------|--------|--------|
| 1 | `阶段1_准备阶段.md` | 建目录、识别图中人物建人物清单、剧本、场景设计、Clip分镜 | manual |
| 2 | `阶段2_人物与环境母图.md` | 人物资产建立（用户提供/提取/生成+验真）+ 环境母图 | **只用 RH** |
| 3 | `阶段3_四宫格提示词.md` | 每 4 个 Clip 一组手写四宫格提示词 | manual |
| 4 | `阶段4_四宫格制作.md` | GRS 生成四宫格 + 切分单图 | **用 GRS** |
| 5 | `阶段5_LTX提示词JSON.md` | 一张切分图 → 一个 LTX JSON | 遵守生成规则 |
| 6 | `阶段6_视频生成.md` | JSON+切分图→RH LTX，一句话一个视频，拼接压缩 | RH LTX 2.3 |

## 阶段门禁（硬性）

- **没有完成本阶段任务，不允许查看下一阶段文件的内容。**
- 状态记录在 `流程进度.md`（`⬜`→`✅`）。
- 进入阶段 N 前运行：`bash 流程门禁检查.sh N <项目目录>`
  - 「✅ 前置阶段全部完成」→ 继续；「⛔ 禁止继续」→ 立即停止，禁止查看当前及后续阶段内容。
- 每阶段完成时把 `流程进度.md` 对应行改为 `✅`。

## 人物资产规则（最重要）

- 人物资产库不再依赖固定目录：从**教材插图/用户图片**识别人物（含有名字/没名字、主要人物优先），先建 `01_剧本/人物清单.md`。
- 来源按序：①用户提供 ②SAM3 提取（image-person-extraction）③确需时 RH 生成。
- **名字必须验真**：与原始插图比对发型/服装/年龄/性别，禁止张冠李戴、禁止编造名字。

## 目录结构

本 skill 与依赖 skill **平级并列**（不互相包含），约定放在同一父目录（如 `short-drama-workflow/`）：

```
short-drama-workflow/
├── ai-film-6-stage/          # 本 skill
│   ├── SKILL.md
│   ├── 阶段1_准备阶段.md … 阶段6_视频生成.md
│   ├── 流程进度.md / 流程门禁检查.sh / 资产文件.md / README.md / .env.example
│   └── 01_剧本/ … 09_最终视频/        # 各阶段产物
├── runninghub-api/           # 依赖 skill（平级）
├── grs-image-api/
├── image-person-extraction/
├── mac-say/
└── feishu-bot/
```

## 依赖 skill（平级并列，仅依赖不包含）

本 skill **不包含**任何依赖，只是按名称/相对路径引用同级目录下的 skill。安装时保持各 skill 平级（同一父目录）即可：

- `../runninghub-api`：RH 余额查询、LTX2.3 图生视频、JSON 生成规则
- `../grs-image-api`：GRS 四宫格生成、四宫格切分
- `../image-person-extraction`：教材人物 SAM3 提取抠图
- `../mac-say`：任务结束/受阻语音播报（≤30字）
- `../feishu-bot`：成品发送（可选）

> 阶段文件中的脚本路径统一写 `../<skill名>/…` 相对引用。需要时先读取对应 skill 的 `SKILL.md`。

## 全局硬性规则

1. 1 图 1 视频，1 句话 1 视频；一个人物只说一句话。
2. 分辨率默认 `768x512 (3:2) (横屏)`；台词格式 `角色名 says: '…'`。
3. RH 优先余额少账号；`--no-track-rh`；新项目清理 `.rh_tracker*`。
4. 生成文件禁止删除，新版本 `_v2/_v3` 后缀；每阶段结束更新 `资产文件.md`。
5. GRS 未经用户确认禁用；mac-say 文本 ≤30 字且带项目名。

## 使用方法

```bash
bash 流程门禁检查.sh 1 wk/项目名   # 从阶段1开始
# 读取 阶段1_准备阶段.md 执行，完成后把 流程进度.md 阶段1 改为 ✅
```
