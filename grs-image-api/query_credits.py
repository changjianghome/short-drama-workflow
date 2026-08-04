#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GrsAI 积分余额查询工具

接口: POST https://grsaiapi.com/client/openapi/getAPIKeyCredits
      POST https://grsai.dakka.com.cn/client/openapi/getAPIKeyCredits

用法:
    python3 query_credits.py                 # 读取 .env 中的 GRSAI_API_KEY
    python3 query_credits.py --api-key sk-xxx   # 手动指定 key
    python3 query_credits.py --cn             # 使用国内节点
"""

import os
import json
import argparse
import urllib.request
import urllib.error
import time
import ssl
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

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

URL_GLOBAL = "https://grsaiapi.com/client/openapi/getAPIKeyCredits"
URL_CN = "https://grsai.dakka.com.cn/client/openapi/getAPIKeyCredits"


def query_credits(api_key: str, cn: bool = False) -> dict:
    url = URL_CN if cn else URL_GLOBAL
    payload = json.dumps({"apiKey": api_key}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if res.get("code") != 0:
        raise RuntimeError(f"接口返回错误: {res}")
    return res["data"]


def main():
    parser = argparse.ArgumentParser(description="GrsAI 积分余额查询工具")
    parser.add_argument("--api-key", type=str, default=None, help="GRSAI API Key（默认读取 .env 的 GRSAI_API_KEY）")
    parser.add_argument("--cn", action="store_true", help="使用国内节点 grsai.dakka.com.cn")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GRSAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ 未找到 API Key！请通过 --api-key 传入，或在 .env 中配置 GRSAI_API_KEY")

    data = query_credits(api_key, cn=args.cn)
    node = "国内节点" if args.cn else "全球节点"

    if args.json:
        print(json.dumps({"node": node, "credits": data.get("credits"), "raw": data}, ensure_ascii=False))
        return

    credits = data.get("credits")
    create_time = data.get("createTime")
    expire_time = data.get("expireTime")
    print(f"🏦 GrsAI 积分余额查询 [{node}]")
    print(f"   当前积分: {credits}")
    if create_time:
        print(f"   创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(create_time))}")
    if expire_time:
        print(f"   到期时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_time)) if expire_time else '永久'}")
    if credits is not None and credits < 440:
        print("   ⚠️ 余额不足（nano-banana-fast 单次需 440 积分）")


if __name__ == "__main__":
    main()
