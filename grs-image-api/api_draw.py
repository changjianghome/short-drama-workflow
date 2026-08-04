#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通用作图工具 - 完全独立，不依赖任何业务逻辑或特定的 JSON 目录结构。
你可以将此脚本拷贝到任何地方使用。

GrsAI 绘图 API 封装
API 地址: POST https://grsaiapi.com/v1/draw/completions
备用域名: https://grsai.dakka.com.cn/v1/draw/completions

注意：生成的四宫格图片需使用 四宫格切分.py 切分，本模型参数为 -p 5 --min-gap 10
"""

import os
import json
import urllib.request
import urllib.error
import time
import ssl
import argparse
import io
from pathlib import Path
from PIL import Image

# 忽略 SSL 证书验证
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 优先从当前工作目录（项目文件夹）读取 .env，其次从本脚本同目录读取
_env_path = Path.cwd() / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).parent / ".env"

if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

API_KEY = os.environ.get("GRSAI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "❌ 未找到 API Key！请在项目根目录下或脚本同目录下创建 .env 文件，写入:\n"
        "   GRSAI_API_KEY=sk-your-key-here\n"
        "   或通过环境变量 GRSAI_API_KEY 设置。"
    )
URL = "https://grsai.dakka.com.cn/v1/api/generate"
RESULT_URL = "https://grsai.dakka.com.cn/v1/api/result"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def encode_and_compress_image(image_path: str, max_size: int = 512, quality: int = 85) -> str:
    """压缩图片并转为 Base64

    规范:
      - 最大边缩放至 512 像素以内 (Lanczos 滤波)
      - RGBA 转 RGB
      - JPEG 质量 85%
      - 目标体积 ~50KB
    """
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            width, height = img.size
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(max_size * height / width)
                else:
                    new_height = max_size
                    new_width = int(max_size * width / height)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            import base64
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"⚠️ 图片处理失败 {image_path}: {e}")
        return None

def submit_draw_task(prompt: str, resolution: str, base64_images: list, model: str = "gpt-image-2", timeout: int = 600) -> str:
    """提交 gpt-image-2 绘图任务，返回 task_id"""
    payload = {
        "model": model,
        "prompt": prompt,
        "aspectRatio": resolution,
        "images": base64_images,
        "replyType": "async"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                URL, data=json.dumps(payload).encode('utf-8'),
                headers=headers, method='POST'
            )
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                # 校验 code == 0 或 含有 id 字段
                task_id = res_data.get("id") or res_data.get("data", {}).get("id")
                if not task_id:
                    raise Exception(f"接口拒绝或未返回 task_id: {res_data}")
            return task_id
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 网络异常重试 ({attempt+1}/{max_retries})...")
                time.sleep(2)
            else:
                raise e
    return None

def poll_draw_result(task_id: str, output_path: str, poll_interval: int = 3, timeout_sec: int = 1200):
    """轮询绘图结果（GET 请求），下载图片到 output_path"""
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout_sec:
            raise Exception("轮询超时 (超过 20 分钟)。")

        time.sleep(poll_interval)

        try:
            poll_url = f"{RESULT_URL}?id={task_id}"
            poll_req = urllib.request.Request(
                poll_url, headers=headers, method='GET'
            )
            with urllib.request.urlopen(poll_req, context=ctx, timeout=30) as poll_resp:
                poll_res = json.loads(poll_resp.read().decode('utf-8'))
        except Exception as e:
            print(f"⚠️ 轮询网络波动: {e}")
            continue

        # 支撑顶级属性或 data 包装层
        data = poll_res if "status" in poll_res else poll_res.get("data", {})
        status = data.get("status")
        progress = data.get("progress", 0)

        print(f"⏳ 任务状态: {status} (进度: {progress}%)")

        if status == "succeeded":
            results = data.get("results", [])
            img_url = results[0].get("url") if results else data.get("url")

            if not img_url:
                raise Exception(f"任务成功但未找到图片链接: {data}")

            print(f"⬇️ 开始下载图片: {img_url}")
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            img_req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(img_req, context=ctx, timeout=30) as resp:
                with open(output_path, 'wb') as out_f:
                    out_f.write(resp.read())
            print(f"✅ 图片成功保存至: {output_path}")
            return output_path

        elif status in ["failed", "error", "violation"]:
            error_msg = data.get("error") or data.get("failure_reason") or "未知错误"
            raise Exception(f"绘图失败 [{status}]: {error_msg}")

def draw(prompt: str, output_path: str, resolution: str = "1536x1024", reference_images: list = None, model: str = "gpt-image-2"):
    """一站式 gpt-image-2 作图函数：提交 -> 轮询 -> 下载

    参数:
      prompt:         作图提示词
      output_path:    图片保存的绝对路径
      resolution:     分辨率 (默认 1536x1024)
      reference_images: 参考图路径列表 (可选)
      model:          模型名称 (默认 gpt-image-2, 可选 gpt-image-2-vip)
    """
    base64_images = []
    if reference_images:
        for path in reference_images:
            if os.path.exists(path):
                b64 = encode_and_compress_image(path)
                if b64:
                    base64_images.append(b64)
            else:
                print(f"❌ 警告: 参考图片不存在 -> {path}")

    print(f"\n🎨 正在发送图像生成请求 [{model}] -> 目标文件: {os.path.basename(output_path)}")
    task_id = submit_draw_task(prompt, resolution, base64_images, model=model)
    if not task_id:
        raise Exception("提交失败，未获取到 task_id")

    print(f"🚀 任务已异步提交，任务 ID: {task_id}，开始轮询状态...")
    return poll_draw_result(task_id, output_path)

def main():
    parser = argparse.ArgumentParser(description="gpt-image-2 专有 API 作图脚本")
    parser.add_argument("--prompt", type=str, required=True, help="作图提示词 (字符串)")
    parser.add_argument("--output", type=str, required=True, help="最终保存图片的绝对路径 (例如: /a/b/c.png)")
    parser.add_argument("--model", type=str, default="gpt-image-2", choices=["gpt-image-2", "gpt-image-2-vip"],
                        help="支持的模型名称 (默认 gpt-image-2)")
    parser.add_argument("--resolution", "--ratio", type=str, default="1536x1024",
                        help="图片分辨率 宽x高 格式。如: 1536x1024, 1024x1024 等")

    parser.add_argument("--image1", type=str, help="参考图 1 绝对路径")
    parser.add_argument("--image2", type=str, help="参考图 2 绝对路径")
    parser.add_argument("--image3", type=str, help="参考图 3 绝对路径")
    parser.add_argument("--image4", type=str, help="参考图 4 绝对路径")

    args = parser.parse_args()

    image_paths = []
    if args.image1: image_paths.append(args.image1)
    if args.image2: image_paths.append(args.image2)
    if args.image3: image_paths.append(args.image3)
    if args.image4: image_paths.append(args.image4)

    draw(args.prompt, args.output, args.resolution, image_paths if image_paths else None, model=args.model)

if __name__ == "__main__":
    main()
