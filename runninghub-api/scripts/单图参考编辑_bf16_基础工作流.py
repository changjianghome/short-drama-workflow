#!/usr/bin/env python3
import os
import sys
import time
import json
import uuid
import argparse
import urllib.request
import urllib.error
import urllib.parse

# 默认配置
DEFAULT_WEBAPP_ID = "2076911428203798530"

def upload_file(api_key, filepath):
    """上传本地文件获取云端 URL (免外部依赖 multipart/form-data 模拟)"""
    if not os.path.exists(filepath):
        print(f"错误: 本地文件不存在: {filepath}")
        return None
    
    url = "https://www.runninghub.cn/openapi/v2/media/upload/binary"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    print(f"正在上传本地参考图片: {filepath} ...")
    
    # 模拟 multipart/form-data
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(filepath)
    
    try:
        with open(filepath, "rb") as f:
            file_content = f.read()
    except Exception as e:
        print(f"读取本地文件失败: {e}")
        return None
        
    body = []
    body.append(f"--{boundary}".encode('utf-8'))
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode('utf-8'))
    body.append(b'Content-Type: image/png')  # 简易假设为 png
    body.append(b'')
    body.append(file_content)
    body.append(f"--{boundary}--".encode('utf-8'))
    body.append(b'')
    
    data = b'\r\n'.join(body)
    
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    headers["Content-Length"] = str(len(data))
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode('utf-8'))
            if res.get("code") == 0 and "data" in res:
                download_url = res["data"].get("download_url")
                print(f"图片上传成功，云端路径: {download_url}")
                return download_url
            else:
                print(f"图片上传失败: {res.get('message')} (响应码: {res.get('code')})")
                return None
    except Exception as e:
        print("上传文件异常:", e)
        return None

def submit_task(api_key, webapp_id, node_info_list):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "nodeInfoList": node_info_list,
        "instanceType": "default",
        "usePersonalQueue": "false"
    }
    
    url = f"https://www.runninghub.cn/openapi/v2/run/ai-app/{webapp_id}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode('utf-8'))
            if res.get("errorCode") and res.get("errorCode") != "0":
                print(f"提交失败: {res.get('errorMessage')} (错误码: {res.get('errorCode')})")
                return None
            return res.get("taskId")
    except Exception as e:
        print("提交请求异常:", e)
        return None

def query_status(api_key, task_id):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {"taskId": task_id}
    url = "https://www.runninghub.cn/openapi/v2/query"
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print("查询异常:", e)
        return None

def download_image(url, output_dir):
    filename = url.split("/")[-1].split("?")[0]
    abs_outdir = os.path.abspath(output_dir)
    os.makedirs(abs_outdir, exist_ok=True)
    filepath = os.path.join(abs_outdir, filename)
    print(f"正在下载结果: {url} -> {filepath}")
    try:
        encoded_url = urllib.parse.quote(url, safe='/:?=&')
        urllib.request.urlretrieve(encoded_url, filepath)
        print(f"下载成功！保存位置: {os.path.abspath(filepath)}")
        return filepath
    except Exception as e:
        print("下载失败:", e)
        return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_outdir = os.path.join(script_dir, "outputs")

    parser = argparse.ArgumentParser(description="RunningHub 2511单图参考编辑_bf16-基础工作流 专属调用脚本")
    parser.add_argument("--apikey", help="RunningHub API Key (默认从环境变量 RUNNINGHUB_API_KEY 读取)")
    parser.add_argument("--prompt", "-p", required=True, help="编辑提示词 (描述修改内容，例如：将整体颜色调亮，增加云朵)")
    parser.add_argument("--image", "-i", required=True, help="参考图。支持本地图片路径(自动上传)或网络图片公开 URL")
    parser.add_argument("--resolution", "-r", default="1536x1024 (3:2) (横屏)", help="出图分辨率尺寸 (默认: 1536x1024 (3:2) (横屏))")
    parser.add_argument("--outdir", default=default_outdir, help=f"结果保存目录 (默认: {default_outdir})")
    parser.add_argument("--poll-interval", type=int, default=5, help="状态轮询间隔秒数 (默认: 5)")
    
    args = parser.parse_args()
    
    api_key = args.apikey or os.getenv("RUNNINGHUB_API_KEY")
    if not api_key:
        print("错误: 必须提供 --apikey 参数或设置 RUNNINGHUB_API_KEY 环境变量")
        sys.exit(1)
        
    image_input = args.image
    
    # 判断是否为本地文件
    if os.path.exists(image_input) and os.path.isfile(image_input):
        cloud_url = upload_file(api_key, image_input)
        if not cloud_url:
            print("上传本地参考图失败，测试终止。")
            sys.exit(1)
        image_input = cloud_url
        
    # 动态组装特定于 2511 单图参考编辑的 nodeInfoList
    node_info_list = [
        {
            "nodeId": "15",
            "fieldName": "prompt",
            "fieldValue": args.prompt,
            "description": "编辑提示"
        },
        {
            "nodeId": "14",
            "fieldName": "image",
            "fieldValue": image_input,
            "description": "image"
        },
        {
            "nodeId": "35",
            "fieldName": "resolution",
            "fieldValue": args.resolution,
            "description": "resolution"
        }
    ]
        
    task_id = submit_task(api_key, DEFAULT_WEBAPP_ID, node_info_list)
    if not task_id:
        print("无法提交任务，测试终止。")
        sys.exit(1)
        
    print(f"开始轮询任务状态 (Task ID: {task_id})...")
    start_time = time.time()
    max_wait_seconds = 600  # 最长轮询10分钟
    
    while True:
        if time.time() - start_time > max_wait_seconds:
            print(f"提示: 任务轮询已超时 (超 {max_wait_seconds // 60} 分钟)。请稍后在网页控制台手动查看任务进度。")
            break
            
        res = query_status(api_key, task_id)
        if not res:
            time.sleep(args.poll_interval)
            continue
            
        status = res.get("status")
        print(f"当前状态: [{status}]")
        
        if status == "SUCCESS":
            print("生成成功！")
            results = res.get("results", [])
            for r in results:
                url = r.get("url")
                if url:
                    download_image(url, args.outdir)
            break
        elif status == "FAILED":
            print(f"任务运行失败。错误码: {res.get('errorCode')}, 原因: {res.get('errorMessage')}")
            break
            
        time.sleep(args.poll_interval)

if __name__ == "__main__":
    main()
