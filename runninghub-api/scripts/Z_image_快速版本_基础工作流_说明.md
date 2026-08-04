# Z_image-快速版本-基础工作流 API 调用说明文档

本文档用于指导开发者如何通过 API 调用在 RunningHub 平台托管的 **`Z_image-快速版本-基础工作流`**（基于 bf16 的快速基础模型），用于进行高效率的文生图或图文内容创作。

---

## 1. 基础信息

*   **应用名称**：Z_image-快速版本-基础工作流
*   **基础模型**：bf16 快速基础模型（写实/文生图/海报制作）
*   **WebApp ID**：`2076895906833715201`
*   **API 域名**：`https://www.runninghub.cn`
*   **运行成本**：低消耗（适用于快速出图）

---

## 2. 前置准备

在进行 API 调用之前，请确保完成以下准备工作：
1.  **获取 API Key**：
    *   登录 [RunningHub 官网](https://www.runninghub.cn/)。
    *   进入控制台的 **“API设置”** 页面，复制您的 32 位唯一 API KEY。
2.  **检查账户额度**：
    *   确保您的 RunningHub 账户内拥有足够的 **RH 币 (RH Coins)**。
3.  **确保接口权限**：
    *   对于消费级 API Key，需要您的账户拥有 **基础版会员及以上** 权限。若为企业共享/独占密钥则不受此限制。

---

## 3. API 接口规范

整个生成流程包含两个步骤：**提交任务** 和 **状态轮询**。

### 3.1 步骤一：提交绘图任务 (Submit Task)

*   **请求地址**：`POST` -> `https://www.runninghub.cn/openapi/v2/run/ai-app/2076895906833715201`
*   **请求头 (Headers)**：
    ```http
    Content-Type: application/json
    Authorization: Bearer <您的_32位_API_KEY>
    ```
*   **请求体参数说明 (JSON)**：
    | 参数名 | 类型 | 是否必填 | 说明 |
    | :--- | :--- | :--- | :--- |
    | `nodeInfoList` | List | 是 | 动态修改工作流的节点参数映射列表（详见下方节点说明） |
    | `instanceType` | String | 否 | 运行实例类型：`default` (24G显存, 默认值) 或 `plus` (48G显存) |
    | `usePersonalQueue`| Boolean| 否 | 是否使用个人独占队列（默认 `"false"`） |

*   **`nodeInfoList` 节点参数控制**：
    该工作流支持修改以下三个节点：
    1.  **正面提示词 (Node ID: `11`)**
        *   `fieldName`: `"text"`
        *   `fieldValue`: 绘图正向提示词。建议使用专业自然语言描述。
    2.  **分辨率 (Node ID: `23`)**
        *   `fieldName`: `"resolution"`
        *   `fieldValue`: 出图的尺寸。可选的分辨率值例如：
            *   横屏：`"1536x1024 (3:2) (横屏)"`（推荐）、`"1216x832 (19:13) (横屏)"`、`"768x512 (3:2) (横屏)"`
            *   竖屏：`"1024x1536 (2:3) (竖屏)"`、`"768x1344 (4:7) (竖屏)"`
            *   方形：`"1024x1024 (1:1) (方形)"`
    3.  **负面提示词 (Node ID: `12`)**
        *   `fieldName`: `"text"`
        *   `fieldValue`: 排除的画面特征（如变形的手指、低分辨率等）。

*   **请求体 JSON 示例**：
    ```json
    {
      "nodeInfoList": [
        {
          "nodeId": "11",
          "fieldName": "text",
          "fieldValue": "A close-up portrait of an elegant young woman, soft lighting, cozy atmosphere.",
          "description": "正面提示"
        },
        {
          "nodeId": "23",
          "fieldName": "resolution",
          "fieldValue": "768x512 (3:2) (横屏)",
          "description": "resolution"
        },
        {
          "nodeId": "12",
          "fieldName": "text",
          "fieldValue": "extra limbs, deformed fingers, blurry, low resolution, ugly",
          "description": "负面提示"
        }
      ],
      "instanceType": "default",
      "usePersonalQueue": "false"
    }
    ```

*   **提交响应体示例 (JSON)**：
    ```json
    {
      "taskId": "2076896536855543810",
      "status": "RUNNING",
      "errorCode": "",
      "errorMessage": "",
      "results": null,
      "clientId": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
    ```

---

### 3.2 步骤二：轮询任务状态 (Query Task)

任务提交后将异步执行，开发者需使用返回的 `taskId` 发起状态查询。

*   **请求地址**：`POST` -> `https://www.runninghub.cn/openapi/v2/query`
*   **请求头 (Headers)**：
    ```http
    Content-Type: application/json
    Authorization: Bearer <您的_32位_API_KEY>
    ```
*   **请求体参数 (JSON)**：
    ```json
    {
      "taskId": "2076896536855543810"
    }
    ```

*   **响应体状态说明 (JSON)**：
    *   **排队/运行中状态**：返回的 `status` 为 `QUEUED` 或 `RUNNING`。
    *   **成功状态**：返回的 `status` 为 `SUCCESS`，此时 `results` 数组中将包含输出的图片链接（有效期仅 24 小时，需及时下载）。
    *   **失败状态**：返回的 `status` 为 `FAILED`，且会附带错误码和错误信息。

*   **查询成功响应体示例**：
    ```json
    {
      "taskId": "2076896536855543810",
      "status": "SUCCESS",
      "errorCode": "",
      "errorMessage": "",
      "usage": {
        "consumeCoins": "15.00",
        "taskCostTime": "12"
      },
      "results": [
        {
          "url": "https://rh-images-1252422369.cos.ap-beijing.myqcloud.com/.../z_image_00003_egjlc_1784005701.png",
          "nodeId": "10",
          "outputType": "png",
          "text": null
        }
      ]
    }
    ```

---

## 4. Python 极速调用代码实现（免第三方依赖）

以下是使用 Python 原生库（`urllib`）实现的极简调用与自动下载脚本。此版本自动规避了中文路径 URL 转码导致的 Unicode 报错，可开箱即用：

```python
#!/usr/bin/env python3
import os
import time
import json
import urllib.request
import urllib.error
import urllib.parse

# 1. 填入您的 RunningHub API Key
API_KEY = "您的_32位_API_KEY"
WEBAPP_ID = "2076895906833715201"

SUBMIT_URL = f"https://www.runninghub.cn/openapi/v2/run/ai-app/{WEBAPP_ID}"
QUERY_URL = "https://www.runninghub.cn/openapi/v2/query"

# 2. 配置您的提示词与分辨率
PROMPT = "日系胶片感少女，清透裸妆，坐在洒满阳光的窗沿，慵懒治愈"
NEGATIVE_PROMPT = "deformed fingers, blurry, low resolution, ugly, watermark"
RESOLUTION = "768x512 (3:2) (横屏)"

def submit_task():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "nodeInfoList": [
            {"nodeId": "11", "fieldName": "text", "fieldValue": PROMPT, "description": "正面提示"},
            {"nodeId": "23", "fieldName": "resolution", "fieldValue": RESOLUTION, "description": "resolution"},
            {"nodeId": "12", "fieldName": "text", "fieldValue": NEGATIVE_PROMPT, "description": "负面提示"}
        ],
        "instanceType": "default",
        "usePersonalQueue": "false"
    }
    
    print("正在提交绘图任务...")
    req = urllib.request.Request(SUBMIT_URL, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read().decode('utf-8'))
            print("提交成功, Task ID:", res.get("taskId"))
            return res.get("taskId")
    except Exception as e:
        print("提交任务失败:", e)
        return None

def query_and_download(task_id):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {"taskId": task_id}
    req = urllib.request.Request(QUERY_URL, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    
    while True:
        try:
            with urllib.request.urlopen(req) as r:
                res = json.loads(r.read().decode('utf-8'))
                status = res.get("status")
                print(f"当前任务状态: [{status}]")
                if status == "SUCCESS":
                    for result in res.get("results", []):
                        img_url = result.get("url")
                        if img_url:
                            download_image(img_url)
                    break
                elif status == "FAILED":
                    print("任务失败:", res.get("errorMessage"))
                    break
                time.sleep(5)
        except Exception as e:
            print("查询状态出错:", e)
            time.sleep(5)

def download_image(url):
    filename = url.split("/")[-1].split("?")[0]
    os.makedirs("outputs", exist_ok=True)
    filepath = os.path.join("outputs", filename)
    print(f"开始下载: {url} -> {filepath}")
    try:
        # 对包含中文字符的 URL 进行转义，防报错
        encoded_url = urllib.parse.quote(url, safe='/:?=&')
        urllib.request.urlretrieve(encoded_url, filepath)
        print(f"下载成功！已保存到: {os.path.abspath(filepath)}")
    except Exception as e:
        print("下载失败:", e)

if __name__ == "__main__":
    task_id = submit_task()
    if task_id:
        query_and_download(task_id)
```

---

## 5. 常见问题与错误排查

1.  **返回错误码 `1` (Unknown error)**:
    *   常发生在使用不合法的 API Key，或者低级别账号尝试调用需要高级会员的高功耗工作流时。
    *   对于此 `快速版本` 工作流（bf16 模型），如提示此错误，请检查您的 API Key 是否过期或者您的账号额度（RH 币）是否用尽。
2.  **返回 401 Unauthorized**:
    *   请求头中 `Authorization` 未正确携带，或者格式错误（必须是 `Bearer <KEY>` 且存在空格）。
3.  **返回 415**:
    *   请求的 `Content-Type` 未设置为 `application/json`。
4.  **生成的图片链接失效**:
    *   RunningHub 输出的图片链接存在 **24 小时生存期**，必须在任务成功后及时进行本地下载或同步转存至您自己的服务器，逾期后将无法恢复。
