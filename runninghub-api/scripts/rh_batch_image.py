#!/usr/bin/env python3
"""RunningHub 批量文生图：提交 → 轮询(最长30min) → 下载。
超时不丢结果（内置脚本 卡通儿童教材插画.py 的轮询 600s 写死，批量任务会超时丢失）。

用法:
    python3 rh_batch_image.py \
      --webapp <WebApp_ID> \
      --prompt-file <提示词文件每行一张图> \
      --account <账号名或32位key> \
      --width 256 --height 256 \
      --outdir <输出目录>

依赖:
    - 同目录 query_account_api.py (账号表)
    - 节点结构需匹配 WebApp: 提示词node26 / 宽node6 / 高node7 (卡通儿童教材插画应用)
"""
import json, os, sys, time, argparse, urllib.request, urllib.error, urllib.parse

DEFAULT_WEBAPP = "2083566214957322242"  # 卡通儿童教材插画


def get_key(name_or_key):
    if len(name_or_key) == 32:
        return name_or_key
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import query_account_api as q
    return q.ACCOUNTS[name_or_key]


def api(url, payload, key):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"errorCode": str(e.code), "errorMessage": e.read().decode()[:300]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webapp", default=DEFAULT_WEBAPP)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--account", required=True, help="账号名(账号N) 或 32位key")
    ap.add_argument("--width", type=int, default=256)
    ap.add_argument("--height", type=int, default=256)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--max-wait", type=int, default=1800)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    key = get_key(args.account)
    lines = [l.strip() for l in open(args.prompt_file) if l.strip()]
    print(f"[rh] {len(lines)} 行提示词 | 账号{args.account} | webapp {args.webapp}", flush=True)

    payload = {"nodeInfoList": [
        {"nodeId": "26", "fieldName": "text", "fieldValue": "\n".join(lines), "description": "text"},
        {"nodeId": "6", "fieldName": "value", "fieldValue": str(args.width), "description": "宽"},
        {"nodeId": "7", "fieldName": "value", "fieldValue": str(args.height), "description": "高"},
    ], "instanceType": "default", "usePersonalQueue": "false"}

    resp = api(f"https://www.runninghub.cn/openapi/v2/run/ai-app/{args.webapp}", payload, key)
    tid = resp.get("taskId")
    if not tid:
        print(f"[rh] 提交失败: {resp.get('errorMessage')} ({resp.get('errorCode')})", flush=True)
        sys.exit(1)
    print(f"[rh] 已提交 taskId={tid}，开始轮询（最长 {args.max_wait//60}min）...", flush=True)

    start = time.time()
    while time.time() - start < args.max_wait:
        time.sleep(10)
        r = api("https://www.runninghub.cn/openapi/v2/query", {"taskId": tid}, key)
        st = r.get("status")
        if st == "SUCCESS":
            results = r.get("results", [])
            print(f"[rh] SUCCESS，{len(results)} 张，开始下载...", flush=True)
            n = 0
            for i, item in enumerate(results, 1):
                url = item.get("url")
                if not url:
                    continue
                ext = url.split("?")[0].split(".")[-1] or "png"
                if len(ext) > 5:
                    ext = "png"
                fpath = os.path.join(args.outdir, f"z_image_{i:05d}.{ext}")
                try:
                    enc = urllib.parse.quote(url, safe='/:?=&')
                    req = urllib.request.Request(enc, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=60) as fr:
                        with open(fpath, "wb") as f:
                            f.write(fr.read())
                    n += 1
                    if n % 10 == 0:
                        print(f"  ...{n}/{len(results)}", flush=True)
                except Exception as e:
                    print(f"  [下载失败{i}] {e}", flush=True)
            print(f"[rh] 完成，下载 {n}/{len(results)} 张", flush=True)
            sys.exit(0)
        elif st == "FAILED":
            print(f"[rh] FAILED: {r.get('errorMessage')}", flush=True)
            sys.exit(1)
        else:
            if int(time.time() - start) % 60 < 10:
                print(f"[rh] {st} {(time.time()-start)//60:.0f}min", flush=True)
    print(f"[rh] 超时({args.max_wait//60}min)，任务可能仍在云端", flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
