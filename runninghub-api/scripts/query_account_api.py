#!/usr/bin/env python3
"""Query RunningHub account info via REST API (no browser needed).

Usage:
  export RUNNINGHUB_API_KEY="your_32_hex_key"
  python3 query_account_api.py

  # Or pass directly:
  python3 query_account_api.py --apikey "your_32_hex_key"

  # Query all accounts from SKILL.md account list:
  python3 query_account_api.py --all

  # Output as JSON:
  python3 query_account_api.py --json
"""

import json
import os
import sys
import urllib.request
import urllib.error

API_URL = "https://www.runninghub.cn/uc/openapi/accountStatus"

# ⚠️ 明文 API Key 已移除（分享安全）。
# 本地使用 --all 查询多账号时，把账号表放到本文件同级 .accounts.json（勿分享，已在 .gitignore 建议）：
#   {"账号1": "<32位hex>", "账号2": "<32位hex>", ...}
# 或用环境变量：export RH_ACCOUNTS_JSON='{"账号1":"<32位hex>"}'


def load_accounts():
    raw = os.environ.get("RH_ACCOUNTS_JSON", "")
    if not raw:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".accounts.json"), encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            raw = ""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception as e:
        print(f"警告: RH_ACCOUNTS_JSON/.accounts.json 解析失败: {e}")
        return {}


ACCOUNTS = load_accounts()


def query(apikey):
    data = json.dumps({"apikey": apikey}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Host": "www.runninghub.cn",
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"code": e.code, "msg": f"HTTP {e.code}: {e.reason}", "data": None}
    except Exception as e:
        return {"code": -1, "msg": str(e), "data": None}


def main():
    args = sys.argv[1:]

    if "--all" in args:
        if not ACCOUNTS:
            print("未找到账号表：请在 .accounts.json 或环境变量 RH_ACCOUNTS_JSON 中提供（勿分享密钥）。")
            sys.exit(1)
        print(f"{'名称':<8} {'RH币':<8} {'任务数':<8} {'钱包':<12} {'API类型':<10}")
        print("-" * 50)
        total_coins = 0
        for name, key in ACCOUNTS.items():
            result = query(key)
            d = result.get("data") or {}
            coins = d.get("remainCoins", "N/A")
            tasks = d.get("currentTaskCounts", "N/A")
            money = d.get("remainMoney") or "-"
            currency = d.get("currency") or ""
            api_type = d.get("apiType", "N/A")
            if coins != "N/A":
                total_coins += int(coins)
            print(f"{name:<8} {coins:<8} {tasks:<8} {money}{currency:<8} {api_type:<10}")
        print("-" * 50)
        print(f"{'合计':<8} {total_coins:<8}")
        return

    apikey = None
    output_json = "--json" in args

    for i, a in enumerate(args):
        if a == "--apikey" and i + 1 < len(args):
            apikey = args[i + 1]
            break

    if not apikey:
        apikey = os.environ.get("RUNNINGHUB_API_KEY")

    if not apikey:
        print("Usage: export RUNNINGHUB_API_KEY=xxx; python3 query_account_api.py")
        print("   or: python3 query_account_api.py --apikey <key>")
        print("   or: python3 query_account_api.py --all  (query all known accounts)")
        sys.exit(1)

    result = query(apikey)

    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result.get("code") != 0:
        print(f"查询失败: {result.get('msg', 'unknown error')}")
        sys.exit(1)

    d = result["data"]
    print(f"{'项目':<12} {'值':<12}")
    print("-" * 28)
    print(f"{'RH币':<12} {d.get('remainCoins', 'N/A'):<12}")
    print(f"{'运行任务数':<12} {d.get('currentTaskCounts', 'N/A'):<12}")
    print(f"{'钱包余额':<12} {d.get('remainMoney') or '-'}")
    print(f"{'货币':<12} {d.get('currency') or '-'}")
    print(f"{'API类型':<12} {d.get('apiType', 'N/A')}")


if __name__ == "__main__":
    main()
