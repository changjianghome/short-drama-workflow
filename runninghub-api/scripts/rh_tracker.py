#!/usr/bin/env python3
"""RH 余额追踪模块 - 每次 API 调用成功后自动扣除 RH 并更新 .env 和 API用量追踪.md"""
import os
import re
import sys
import fcntl
import time
from datetime import datetime


# .env 路径通过环境变量 RH_ENV_PATH 配置；默认读取当前目录 .env（分享安全，勿写死机器路径）
DEFAULT_ENV_PATH = os.getenv("RH_ENV_PATH", ".env")


def _find_env_line(api_key, env_path=DEFAULT_ENV_PATH):
    """在 .env 中查找匹配 api_key 的行和行号"""
    with open(env_path, 'r') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if api_key.strip() in line:
            return lines, i, line
    return None


def _parse_rh(line):
    """从 .env 行注释中提取 RH 余额: # ... | 17 RH"""
    m = re.search(r'\|\s*(\d+)\s*RH', line)
    return int(m.group(1)) if m else None


def _read_current_balance(api_key, env_path=DEFAULT_ENV_PATH):
    """读取当前 API Key 的 RH 余额"""
    result = _find_env_line(api_key, env_path)
    if not result:
        return None, None, None
    lines, idx, line = result
    rh = _parse_rh(line)
    return rh, lines, idx


def _atomically_replace_line(filepath, line_idx, new_line):
    """原子替换文件的某一行（带文件锁）"""
    lock_path = filepath + ".lock"
    with open(lock_path, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            lines[line_idx] = new_line
            tmp = filepath + ".tmp"
            with open(tmp, 'w') as f:
                f.writelines(lines)
            os.replace(tmp, filepath)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def deduct_rh(api_key, amount, env_path=DEFAULT_ENV_PATH):
    """
    从 .env 中扣除指定 API Key 的 RH 余额
    返回: (扣除后余额, 是否成功)
    """
    rh, lines, idx = _read_current_balance(api_key, env_path)
    if rh is None:
        print(f"[RH追踪] ⚠️ 未找到 Key 在 .env 中的行: {api_key[:8]}...")
        return None, False

    new_rh = max(rh - amount, 0)
    old_line = lines[idx]
    new_line = re.sub(r'\|\s*\d+\s*RH', f'| {new_rh} RH', old_line)

    if new_line == old_line:
        print(f"[RH追踪] ⚠️ .env 行格式不匹配，跳过更新")
        return new_rh, False

    _atomically_replace_line(env_path, idx, new_line)
    print(f"[RH追踪] ✅ {api_key[:8]}... 扣除 {amount} RH: {rh} → {new_rh}")

    if new_rh <= 10 and new_rh > 0:
        print(f"[RH追踪] ⚠️ 余额不足预警: 仅剩 {new_rh} RH!")
    elif new_rh <= 0:
        print(f"[RH追踪] 🚨 余额已耗尽! 请充值或切换 Key")

    return new_rh, True


def get_key_info(api_key, env_path=DEFAULT_ENV_PATH):
    """获取 Key 的详细信息（账号名、手机号）"""
    rh, lines, idx = _read_current_balance(api_key, env_path)
    if rh is None:
        return None
    line = lines[idx]
    m_phone = re.search(r'(\d{11})', line)
    m_name = re.search(r'#\s*(\S+)', line)
    return {
        'phone': m_phone.group(1) if m_phone else '?',
        'name': m_name.group(1) if m_name else '?',
        'rh': rh
    }


def append_usage_record(project_dir, record_line):
    """
    在项目 API用量追踪.md 的 RunningHub 表格中追加一行

    record_line 格式:
    "| 2026-07-19 20:30 | 视频 | 片03_左上 | ...37be | 5s | ✅ 成功 | LTX 图生视频 |"
    """
    md_path = os.path.join(project_dir, "API用量追踪.md")
    if not os.path.exists(md_path):
        print(f"[RH追踪] ⚠️ 未找到 API用量追踪.md: {md_path}")
        return False

    # 找到 RunningHub 表格中最后一行记录的位置
    with open(md_path, 'r') as f:
        lines = f.readlines()

    in_rh_section = False
    insert_at = None

    for i, line in enumerate(lines):
        if 'RunningHub API' in line and '|---' in lines[i+1] if i+1 < len(lines) else False:
            in_rh_section = True
            continue
        if in_rh_section and line.startswith('|') and ('视频' in line or '图片' in line or '—' in line):
            insert_at = i  # 不断更新到最后一个表格行
        if in_rh_section and not line.startswith('|') and insert_at and i > insert_at + 1:
            break

    if insert_at is None:
        print(f"[RH追踪] ⚠️ 未找到 RunningHub 表格，无法追加记录")
        return False

    # 在最后一个表格行之后插入新行
    new_record = record_line + "\n"
    lines.insert(insert_at + 1, new_record)

    tmp = md_path + ".tmp"
    with open(tmp, 'w') as f:
        f.writelines(lines)
    os.replace(tmp, md_path)

    print(f"[RH追踪] ✅ 已更新 {os.path.basename(md_path)}")
    return True


def track_image_generation(api_key, filename, project_dir=None):
    """
    追踪一次图片生成，扣除 7 RH
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    key_suffix = api_key[-4:] if len(api_key) >= 4 else '?'
    info = get_key_info(api_key)

    new_rh, ok = deduct_rh(api_key, 7)
    if not ok:
        return

    if project_dir and os.path.isdir(project_dir):
        record = f"| {now} | 图片 | {filename} | ...{key_suffix} | ✅ 成功 | Z_image 图片生成 (7 RH) |"
        append_usage_record(project_dir, record)


def track_video_generation(api_key, filename, duration_seconds, project_dir=None):
    """
    追踪一次视频生成，扣除 duration_seconds × 5 RH
    """
    amount = duration_seconds * 5
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    key_suffix = api_key[-4:] if len(api_key) >= 4 else '?'
    info = get_key_info(api_key)

    new_rh, ok = deduct_rh(api_key, amount)
    if not ok:
        return

    if project_dir and os.path.isdir(project_dir):
        record = f"| {now} | 视频 | {filename} | ...{key_suffix} | {duration_seconds}s | ✅ 成功 | LTX 图生视频 ({amount} RH) |"
        append_usage_record(project_dir, record)


def preview_balance(api_key):
    """预览扣除前余额"""
    info = get_key_info(api_key)
    if info:
        print(f"[RH追踪] 当前 Key: {info['name']} ({info['phone']}) | 余额: {info['rh']} RH")
    else:
        print(f"[RH追踪] ⚠️ 未找到 Key 信息")


def check_balance(api_key, required_rh):
    """
    任务前余额检查，返回 (余额, 是否足够)
    不足时直接打印告警
    """
    info = get_key_info(api_key)
    if not info:
        print(f"[RH追踪] ⚠️ 无法检查余额，请手动确认")
        return None, True  # 未找到时放行
    rh = info['rh']
    if rh < required_rh:
        print(f"[RH追踪] 🚨 {info['name']} 余额不足! 需要 {required_rh} RH，剩余 {rh} RH")
        return rh, False
    print(f"[RH追踪] {info['name']} 余额 {rh} RH，本次预估消耗 {required_rh} RH，剩余 {rh - required_rh} RH")
    return rh, True


# ---- CLI 独立测试 ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 rh_tracker.py <api_key> [preview|deduct <amount>]")
        sys.exit(1)

    key = sys.argv[1]
    cmd = sys.argv[2] if len(sys.argv) > 2 else "preview"

    if cmd == "preview":
        preview_balance(key)
    elif cmd == "deduct":
        amount = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        deduct_rh(key, amount)
    else:
        print(f"未知命令: {cmd}")
