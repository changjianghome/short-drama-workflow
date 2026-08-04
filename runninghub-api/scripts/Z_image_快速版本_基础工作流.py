#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
import urllib.parse

# 默认配置
DEFAULT_WEBAPP_ID = "2076895906833715201"
DEFAULT_NEGATIVE_PROMPT = (
    "extra hands, extra feet, redundant limbs, incorrect number of limbs, "
    "abnormal number of fingers, distorted fingers, missing limbs, misplaced limbs, "
    "blurry, low resolution, distorted, pixelated, deformed, ugly, messy background, "
    "text watermark, stitching marks, overexposed, color cast"
)

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
    print(f"正在下载: {url} -> {filepath}")
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

    parser = argparse.ArgumentParser(description="RunningHub Z_image-快速版本-基础工作流 专属调用脚本")
    parser.add_argument("--apikey", help="RunningHub API Key (默认从环境变量 RUNNINGHUB_API_KEY 读取)")
    parser.add_argument("--prompt", "-p", required=True, help="正向提示词 (文生图内容)")
    parser.add_argument("--negative", "-n", default=DEFAULT_NEGATIVE_PROMPT, help="负向提示词")
    parser.add_argument("--resolution", "-r", default="768x512 (3:2) (横屏)", help="分辨率尺寸 (默认: 768x512 (3:2) (横屏))")
    parser.add_argument("--outdir", default=default_outdir, help=f"结果保存目录 (默认: {default_outdir})")
    parser.add_argument("--poll-interval", type=int, default=5, help="状态轮询间隔秒数 (默认: 5)")
    parser.add_argument("--project-dir", default=None, help="项目目录 (用于更新 wk/项目名/API用量追踪.md)")
    parser.add_argument("--no-track-rh", action="store_true", help="禁用 RH 余额自动追踪")
    
    args = parser.parse_args()
    
    api_key = args.apikey or os.getenv("RUNNINGHUB_API_KEY")
    if not api_key:
        print("错误: 必须提供 --apikey 参数或设置 RUNNINGHUB_API_KEY 环境变量")
        sys.exit(1)
        
    # 动态组装该工作流特定的 nodeInfoList
    node_info_list = [
        {
            "nodeId": "11",
            "fieldName": "text",
            "fieldValue": args.prompt,
            "description": "正面提示"
        },
        {
            "nodeId": "23",
            "fieldName": "resolution",
            "fieldValue": args.resolution,
            "description": "resolution"
        },
        {
            "nodeId": "12",
            "fieldName": "text",
            "fieldValue": args.negative,
            "description": "负面提示"
        }
    ]
        
    # RH 余额预检查
    if not args.no_track_rh and args.project_dir:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from rh_tracker import check_balance
            balance, enough = check_balance(api_key, 7)
            if not enough:
                print("[RH追踪] 任务取消：余额不足，请切换 Key 或充值")
                sys.exit(1)
        except ImportError:
            pass

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
            downloaded_files = []
            for r in results:
                url = r.get("url")
                if url:
                    fpath = download_image(url, args.outdir)
                    if fpath:
                        downloaded_files.append(fpath)
            # RH 余额自动追踪
            if downloaded_files and not args.no_track_rh:
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    from rh_tracker import track_image_generation
                    for fpath in downloaded_files:
                        track_image_generation(api_key, os.path.basename(fpath), args.project_dir)
                except ImportError as e:
                    print(f"[RH追踪] 模块加载失败: {e}")
            break
        elif status == "FAILED":
            print(f"任务运行失败。错误码: {res.get('errorCode')}, 原因: {res.get('errorMessage')}")
            break
            
        time.sleep(args.poll_interval)

if __name__ == "__main__":
    main()
