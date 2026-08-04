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
import mimetypes
import ssl

DEFAULT_WEBAPP_ID = "2077031364116959233"

def upload_image(api_key, filepath):
    if not os.path.exists(filepath):
        print(f"警告: 本地文件不存在: {filepath}，将传递原字符串。")
        return filepath
    
    print(f"正在上传本地参考图片: {filepath} ...")
    url = "https://www.runninghub.cn/openapi/v2/media/upload/binary"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(filepath)
    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type:
        mime_type = "image/png"
    
    try:
        with open(filepath, "rb") as f:
            file_content = f.read()
    except Exception as e:
        print(f"警告: 读取本地文件失败: {e}，将传递原字符串。")
        return filepath
        
    body = []
    body.append(f"--{boundary}".encode('utf-8'))
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode('utf-8'))
    body.append(f'Content-Type: {mime_type}'.encode('utf-8'))
    body.append(b'')
    body.append(file_content)
    body.append(f"--{boundary}--".encode('utf-8'))
    body.append(b'')
    
    data = b'\r\n'.join(body)
    
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    headers["Content-Length"] = str(len(data))
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=context) as r:
            res = json.loads(r.read().decode('utf-8'))
            if res.get("code") == 0 and "data" in res:
                download_url = res["data"].get("download_url")
                if download_url:
                    print(f"图片上传成功，云端路径: {download_url}")
                    return download_url
            print(f"警告: 上传失败，响应: {res}，将传递原字符串。")
            return filepath
    except Exception as e:
        print(f"警告: 上传文件异常: {e}，将传递原字符串。")
        return filepath

def process_image_param(api_key, image_param):
    if not image_param or str(image_param).lower() == 'none':
        return "None"
    if str(image_param).startswith("http://") or str(image_param).startswith("https://") or str(image_param).startswith("data:"):
        return image_param
    return upload_image(api_key, image_param)

def submit_task(api_key, webapp_id, node_info_list, max_retries=10, retry_delay=15):
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
    
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=30, context=context) as r:
                res = json.loads(r.read().decode('utf-8'))
                if res.get("errorCode") and str(res.get("errorCode")) != "0":
                    err_code = str(res.get("errorCode"))
                    err_msg = res.get("errorMessage")
                    print(f"提交尝试 {attempt}/{max_retries} 失败: {err_msg} (错误码: {err_code})")
                    if err_code == "421" or "queue limit" in str(err_msg).lower():
                        print(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    return None
                return res.get("taskId")
        except Exception as e:
            print(f"提交网络异常 {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
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
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=30, context=context) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print("查询异常:", e)
        return None

def download_file(url, output_dir, output_file=None):
    if output_file:
        filepath = os.path.abspath(output_file)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    else:
        filename = url.split("/")[-1].split("?")[0]
        abs_outdir = os.path.abspath(output_dir)
        os.makedirs(abs_outdir, exist_ok=True)
        filepath = os.path.join(abs_outdir, filename)
        
    print(f"正在下载: {url} -> {filepath}")
    try:
        encoded_url = urllib.parse.quote(url, safe='/:?=&')
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(encoded_url, timeout=30, context=context) as r, open(filepath, 'wb') as f:
            f.write(r.read())
        print(f"下载成功！保存位置: {os.path.abspath(filepath)}")
        return filepath
    except Exception as e:
        print("下载失败:", e)
        return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_outdir = os.path.join(script_dir, "outputs")

    parser = argparse.ArgumentParser(description="RunningHub ltx2.3_无导演台_纯参数 专属调用脚本")
    parser.add_argument("--apikey", help="RunningHub API Key (默认从环境变量 RUNNINGHUB_API_KEY 读取)")
    
    # 新增对 JSON 配置文件的支持
    parser.add_argument("--json_file", "-j", help="从 JSON 文件读取参数配置 (global_prompt, local_prompts, segment_lengths 等)")
    
    # 核心提示词与配置
    parser.add_argument("--global_prompt", default="", help="全局提示词")
    parser.add_argument("--local_prompts", default="", help="分段提示词 (用 | 分隔)")
    
    parser.add_argument("--resolution", "-r", default="768x512 (3:2) (横屏)", help="分辨率 (默认: 768x512 (3:2) (横屏))")
    parser.add_argument("--image1", default="None", help="参考图1 (本地路径或URL，传 None 表示不使用)")
    parser.add_argument("--image2", default="None", help="参考图2")
    parser.add_argument("--image3", default="None", help="参考图3")
    parser.add_argument("--image4", default="None", help="参考图4")
    parser.add_argument("--segment_lengths", default="", help="segment_lengths 参数")
    parser.add_argument("--all_segment_lengths", default="0", help="all_segment_lengths 参数")
    parser.add_argument("--frame_indice1", default="0", help="frame_indice1 参数")
    parser.add_argument("--frame_indice2", default="0", help="frame_indice2 参数")
    parser.add_argument("--frame_indice3", default="0", help="frame_indice3 参数")
    parser.add_argument("--frame_indice4", default="0", help="frame_indice4 参数")
    parser.add_argument("--strengths1", default="0", help="strengths1 参数")
    parser.add_argument("--strengths2", default="0", help="strengths2 参数")
    parser.add_argument("--strengths3", default="0", help="strengths3 参数")
    parser.add_argument("--strengths4", default="0", help="strengths4 参数")
    parser.add_argument("--outdir", default=default_outdir, help=f"结果保存目录 (默认: {default_outdir})")
    parser.add_argument("--output_file", "-o", default=None, help="自定义完整输出文件路径和名字(如: /tmp/my_video.mp4)。若指定，则覆盖 outdir")
    parser.add_argument("--poll-interval", type=int, default=5, help="状态轮询间隔秒数 (默认: 5)")
    parser.add_argument("--duration", "-d", type=int, default=None, help="视频时长(秒)，用于 RH 扣减计算。若不指定，自动从 all_segment_lengths/25 推算")
    parser.add_argument("--project-dir", default=None, help="项目目录 (用于更新 wk/项目名/API用量追踪.md)")
    parser.add_argument("--no-track-rh", action="store_true", help="禁用 RH 余额自动追踪")
    
    args = parser.parse_args()
    
    api_key = args.apikey or os.getenv("RUNNINGHUB_API_KEY")
    if not api_key:
        print("错误: 必须提供 --apikey 参数或设置 RUNNINGHUB_API_KEY 环境变量")
        sys.exit(1)
        
    # 如果指定了 JSON 文件，则从 JSON 文件中覆盖相应参数
    if args.json_file:
        if os.path.exists(args.json_file):
            with open(args.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                args.global_prompt = data.get("global_prompt", args.global_prompt)
                args.local_prompts = data.get("local_prompts", args.local_prompts)
                args.segment_lengths = data.get("segment_lengths", args.segment_lengths)
                
                # 提取 ltxv_add_guide_multi 内部的 frame_indices 和 strengths
                guide = data.get("ltxv_add_guide_multi")
                if guide and isinstance(guide, dict):
                    fi = guide.get("frame_indices", [])
                    st = guide.get("strengths", [])
                    if len(fi) > 0: args.frame_indice1 = int(fi[0])
                    if len(fi) > 1: args.frame_indice2 = int(fi[1])
                    if len(fi) > 2: args.frame_indice3 = int(fi[2])
                    if len(fi) > 3: args.frame_indice4 = int(fi[3])
                    
                    if len(st) > 0: args.strengths1 = float(st[0])
                    if len(st) > 1: args.strengths2 = float(st[1])
                    if len(st) > 2: args.strengths3 = float(st[2])
                    if len(st) > 3: args.strengths4 = float(st[3])
        else:
            print(f"警告: 找不到 JSON 文件 {args.json_file}")
            
    # 自动计算总帧数 (all_segment_lengths)
    if args.segment_lengths:
        try:
            lengths = [int(x.strip()) for x in str(args.segment_lengths).split(',') if x.strip()]
            args.all_segment_lengths = sum(lengths)
        except Exception as e:
            print(f"警告: 无法自动计算 segment_lengths 的总和: {e}")
            
    # 动态组装节点信息
    node_info_list = [
        {"nodeId": "1521", "fieldName": "text", "fieldValue": args.global_prompt, "description": "全局提示词"},
        {"nodeId": "1522", "fieldName": "text", "fieldValue": args.local_prompts, "description": "分段提示词"},
        {"nodeId": "1270", "fieldName": "resolution", "fieldValue": args.resolution, "description": "resolution"},
        {"nodeId": "1460", "fieldName": "image", "fieldValue": process_image_param(api_key, args.image1), "description": "参考图1"},
        {"nodeId": "1501", "fieldName": "image", "fieldValue": process_image_param(api_key, args.image2), "description": "参考图2"},
        {"nodeId": "1502", "fieldName": "image", "fieldValue": process_image_param(api_key, args.image3), "description": "参考图3"},
        {"nodeId": "1503", "fieldName": "image", "fieldValue": process_image_param(api_key, args.image4), "description": "参考图4"},
        {"nodeId": "1507", "fieldName": "text", "fieldValue": str(args.segment_lengths), "description": "segment_lengths"},
        {"nodeId": "1508", "fieldName": "value", "fieldValue": int(args.all_segment_lengths), "description": "all_segment_lengths"},
        {"nodeId": "1509", "fieldName": "value", "fieldValue": int(args.frame_indice1), "description": "frame_indice1"},
        {"nodeId": "1510", "fieldName": "value", "fieldValue": int(args.frame_indice2), "description": "frame_indice2"},
        {"nodeId": "1511", "fieldName": "value", "fieldValue": int(args.frame_indice3), "description": "frame_indice3"},
        {"nodeId": "1512", "fieldName": "value", "fieldValue": int(args.frame_indice4), "description": "frame_indice4"},
        {"nodeId": "1517", "fieldName": "value", "fieldValue": float(args.strengths1), "description": "strengths1"},
        {"nodeId": "1518", "fieldName": "value", "fieldValue": float(args.strengths2), "description": "strengths2"},
        {"nodeId": "1519", "fieldName": "value", "fieldValue": float(args.strengths3), "description": "strengths3"},
        {"nodeId": "1520", "fieldName": "value", "fieldValue": float(args.strengths4), "description": "strengths4"}
    ]
        
    # 计算视频时长（用于 RH 扣减）
    video_duration = args.duration
    if video_duration is None and args.all_segment_lengths:
        try:
            total_frames = int(args.all_segment_lengths)
            video_duration = max(total_frames // 25, 1)  # 25 FPS
        except:
            video_duration = 5  # 默认 5s
    if video_duration is None:
        video_duration = 5

    # RH 余额预检查
    rv_required = video_duration * 5
    if not args.no_track_rh and args.project_dir:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from rh_tracker import check_balance
            balance, enough = check_balance(api_key, rv_required)
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
    max_wait_seconds = 900  # 最长轮询15分钟
    
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
                    fpath = download_file(url, args.outdir, args.output_file)
                    if fpath:
                        downloaded_files.append(fpath)
            # RH 余额自动追踪
            if downloaded_files and not args.no_track_rh:
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    from rh_tracker import track_video_generation
                    for fpath in downloaded_files:
                        track_video_generation(api_key, os.path.basename(fpath), video_duration, args.project_dir)
                except ImportError as e:
                    print(f"[RH追踪] 模块加载失败: {e}")
            break
        elif status == "FAILED":
            print(f"任务运行失败。错误码: {res.get('errorCode')}, 原因: {res.get('errorMessage')}")
            break
            
        time.sleep(args.poll_interval)

if __name__ == "__main__":
    main()
