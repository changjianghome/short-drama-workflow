# zimage-批量出图 AI 应用 API 调用说明文档

本文档用于指导开发者如何通过 API 调用在 RunningHub 平台托管的 **`zimage-批量出图`** AI 应用，用于批量生成卡通儿童教材风格的插画图片。

---

## 1. 基础信息

*   **应用名称**：zimage-批量出图
*   **WebApp ID**：`2083566214957322242`
*   **API 域名**：`https://www.runninghub.cn`
*   **出图方式**：文生图（支持多行提示词批量出图）

---

## 2. 前置准备

1.  **获取 API Key**：登录 RunningHub 官网 → 控制台 → "API设置" → 复制 32 位唯一 API KEY。
2.  **检查账户额度**：确保账户拥有足够的 RH 币（本应用预估约 7 RH/张）。
3.  **确认接口权限**：消费级 API Key 需基础版及以上会员；企业级 Key 不受限。

---

## 3. API 接口规范

### 3.1 步骤一：提交任务

*   **请求地址**：`POST` -> `https://www.runninghub.cn/openapi/v2/run/ai-app/2083566214957322242`
*   **请求头**：
    ```http
    Content-Type: application/json
    Authorization: Bearer <您的_32位_API_KEY>
    ```
*   **`nodeInfoList` 节点参数**：
    1.  **提示词 (Node ID: `26`)**
        *   `fieldName`: `"text"`
        *   `fieldValue`: 绘图提示词。支持**多行**，每行一个场景，将按行数批量生成对应数量的图片。
    2.  **宽度 (Node ID: `6`)**
        *   `fieldName`: `"value"`
        *   `fieldValue`: 数字（如 `512`）。
    3.  **高度 (Node ID: `7`)**
        *   `fieldName`: `"value"`
        *   `fieldValue`: 数字（如 `512`）。

*   **请求体 JSON 示例**：
    ```json
    {
      "nodeInfoList": [
        {
          "nodeId": "26",
          "fieldName": "text",
          "fieldValue": "卡通儿童教材插画，一个笑眯眯的小学生睡前把课本和文具整齐收进书包，墙上有贴满星星的习惯打卡表，柔和的卧室背景，明亮糖果色，扁平插画风，主体居中，无文字\n卡通儿童教材插画，小朋友侧耳认真听讲，眼睛发亮，老师在讲台指着黑板，明亮教室背景，圆润可爱画风，暖色调，主体居中，无文字",
          "description": "text"
        },
        {
          "nodeId": "6",
          "fieldName": "value",
          "fieldValue": "512",
          "description": "宽"
        },
        {
          "nodeId": "7",
          "fieldName": "value",
          "fieldValue": "512",
          "description": "高"
        }
      ],
      "instanceType": "default",
      "usePersonalQueue": "false"
    }
    ```

### 3.2 步骤二：轮询任务状态

*   **请求地址**：`POST` -> `https://www.runninghub.cn/openapi/v2/query`
*   **请求体**：`{"taskId": "<taskId>"}`
*   **状态**：`QUEUED` / `RUNNING` / `SUCCESS` / `FAILED`
*   成功后 `results` 数组返回图片链接（**有效期仅 24 小时**，需及时下载）。

---

## 4. 专属脚本调用方式

脚本位于 `scripts/zimage-批量出图.py`，已内置 WebApp ID 并封装 RH 追踪，无需传复杂 JSON。

```bash
# 1. 导出 API Key 环境变量
export RUNNINGHUB_API_KEY="您的_32位_API_KEY"

# 2. 带 RH 追踪的完整调用（推荐）
python3 scripts/zimage-批量出图.py \
  --prompt "卡通儿童教材插画，一个笑眯眯的小学生睡前把课本和文具整齐收进书包，墙上有贴满星星的习惯打卡表，柔和的卧室背景，明亮糖果色，扁平插画风，主体居中，无文字
卡通儿童教材插画，小朋友侧耳认真听讲，眼睛发亮，老师在讲台指着黑板，明亮教室背景，圆润可爱画风，暖色调，主体居中，无文字" \
  --width 512 --height 512 \
  --project-dir "wk/项目名"

# 3. 不想自动扣减 RH 时加 --no-track-rh
python3 scripts/zimage-批量出图.py --prompt "test" --no-track-rh
```

### 参数说明
| 参数 | 说明 |
| :--- | :--- |
| `--prompt` / `-p`（必填） | 提示词，支持多行，每行一个场景/一张图 |
| `--width` / `-W` | 图片宽度（默认 512） |
| `--height` / `-H` | 图片高度（默认 512） |
| `--apikey` | API Key（推荐用环境变量 `RUNNINGHUB_API_KEY`） |
| `--outdir` | 结果保存目录（默认脚本目录下 `outputs/`） |
| `--project-dir` | 项目目录，用于自动更新 `API用量追踪.md` 和 `.env` RH 余额 |
| `--no-track-rh` | 跳过 RH 余额自动扣减和记录 |

---

## 5. 常见问题与错误排查

1.  **错误码 `1` (Unknown error)**：多为 API Key 无效或账号额度（RH 币）不足，先查询余额。
2.  **401 Unauthorized**：`Authorization` 头格式错误，必须为 `Bearer <KEY>` 且含空格。
3.  **图片链接失效**：RunningHub 输出链接仅 24 小时有效，任务成功后须立即下载。
