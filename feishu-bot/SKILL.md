---
name: feishu-bot
description: 向飞书群/用户发送消息（文本/文件/图片/视频/语音）。传入 app_id + app_secret + chat_id + 消息内容即可一键发送。
---

# Feishu Bot Skill

通过飞书开放平台 API 发送消息。支持文本、文件、图片、视频、语音。

## 前置条件

- 飞书自建应用已开启「机器人能力」并已发布
- 已申请权限：`im:message:send_as_bot`
- 机器人已在目标群中或被添加到可用范围

## 配置（三选一）

**方式 A：项目 .env 文件**（推荐，自动加载）

在项目根目录 `.env` 中添加：
```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_CHAT_ID=oc_xxx       # 默认群/用户 ID，命令行可省略
```

**方式 B：feishu config 命令**
```bash
feishu config --app-id cli_xxx --app-secret xxxx
```

**方式 C：环境变量**
```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxxx"
export FEISHU_CHAT_ID="oc_xxx"
```

## 发送消息

```bash
# chat_id 可从命令行传入，也可从 .env / 环境变量默认加载
feishu text   "文本内容"                  # 使用 FEISHU_CHAT_ID
feishu text   <chat_id> "文本内容"        # 指定群/用户

feishu file   /path/to/file
feishu image  /path/to/image
feishu media  /path/to/video.mp4 [封面]
feishu audio  /path/to/audio

# 固定格式发送（分隔线 + 标题 + 内容 + 可选文件），每次发送条目固定格式
feishu post   --title "视频已完成" --content "这是简介或内容" --file /path/to/video.mp4
feishu post   --title "今日汇总"
feishu post   --content "只有内容没有标题"
feishu post   --file /path/to/document.pdf
```

### feishu post 固定格式说明

每次发送条目统一为以下结构（各字段均为可选，但标题/内容/文件至少提供其一）：

```
-----------
标题：xxx            # --title（可选）
内容正文             # --content（可选）
[文件/视频]           # --file（可选，自动识别类型）
```

- `--file` 自动按扩展名区分：`mp4/mov/avi/mkv/webm/m4v` 按视频发送（自动抽首帧作封面，可用 `--thumb` 指定封面）；`png/jpg/jpeg/gif/webp/bmp` 按图片发送；其余按普通文件发送。
- `--thumb` 仅对视频生效，需与 `--file` 配合使用。

## 限制

- 文件最大 **30MB**
- 图片最大 **10MB**
- 视频推荐 ≤ 25MB（上传较稳定）

## 脚本位置

`feishu.sh` 位于本 skill 同级目录，已安装为 `feishu` 命令。
