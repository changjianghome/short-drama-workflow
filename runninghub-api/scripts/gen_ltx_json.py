#!/usr/bin/env python3
"""
LTX 2.3 提示词 JSON 通用生成器（项目配置驱动）

用法：
  python3 gen_ltx_json.py --config project.yaml --outdir 提示词/
  python3 gen_ltx_json.py --config project.yaml --outdir 提示词/ --dry-run

说明：
- 脚本只包含"不变的规则"（JSON结构、段落模板、帧数算法、strengths、negative_prompt）
- 每个项目新建一份 project.yaml，填写角色清单 + Clip清单
- 变化的内容（角色、画面、台词、每格实际人物）全部在 project.yaml 中
- 生成前务必逐格核对四宫格图片，将 clip.present_chars 填为该画面实际角色

配置格式示例见同目录 project.example.yaml
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("缺少 PyYAML，请先安装: pip install pyyaml")
    sys.exit(1)

# ================= 不变的规则 =================

NEGATIVE_PROMPT = (
    "worst quality, inconsistent motion, blurry, jittery, distorted face, deformed face, ugly, "
    "aged skin, wrinkles, asymmetric eyes, extra fingers, mutated hands, bad anatomy, static image, "
    "frozen, oversaturated, cartoon, anime, plastic skin, motion smear, transition cuts, scene change, "
    "text overlay, watermark, multiple characters, character duplication, ghost double, split screen, "
    "picture-in-picture, frame within frame, embedded image, image inside image, double exposure overlay, "
    "hard cut, jump cut, smash cut, montage style, scene transition wipe, fade to black, crossfade, "
    "multiple panels, comic panel layout, photo collage"
)

# 台词字数 → 帧数（30fps），基于: 秒 ≈ 字数/2.5 + 动作节点×2.0，再 ×30
def calc_frames(quote_len, action_nodes=0, min_frames=176, max_frames=240):
    """按台词字数+动作节点计算帧数"""
    seconds = quote_len / 2.5 + action_nodes * 2.0
    frames = int(seconds * 30) + 1
    # 情感重音/收尾镜头额外加余量
    frames = max(frames, min_frames)
    frames = min(frames, max_frames)
    return frames

def calc_frames_no_dialogue(action_nodes=1, min_frames=176, max_frames=200):
    """无台词镜头：动作节点数×2.0秒"""
    seconds = max(action_nodes * 2.0, 5.0)
    frames = int(seconds * 30) + 1
    frames = max(frames, min_frames)
    frames = min(frames, max_frames)
    return frames

def build_global_prompt(style_base, present_chars, scene, positions=None):
    """global_prompt: 风格基底 + 实际角色 + 位置关系 + 场景 + 约束词"""
    style = " ".join(style_base.split())  # 压平换行
    gp = f"{style} {scene}. "
    if present_chars:
        # 每个角色完整外貌 + 画面中的位置
        parts = []
        for c in present_chars:
            pos = (positions or {}).get(c["name"])
            desc = c["desc"]
            if pos:
                parts.append(f"{c['name']} ({desc}) {pos}")
            else:
                parts.append(f"{c['name']} ({desc})")
        gp += "In this frame: " + "; ".join(parts) + ". "
    if len(present_chars) < 4:
        gp += "ONLY these character(s) appear in this scene, no other characters."
    return gp

def build_local_prompt(clip, present_chars, n_shot=1):
    """
    段落模板：Shot N + 景别 + camera + 角色物理动作 + 位置关系 + 说话人完整描述 + 台词 + audio
    clip: {scene, camera, shot, action, line, audio, present_chars, positions, action_nodes}
    """
    shot_name = f"Shot {n_shot}"
    camera = clip.get("camera", "medium shot, static frame")
    action = clip.get("action", "")
    line = clip.get("line", "")
    audio = clip.get("audio", "gentle ambient music, soft room sound")
    positions = clip.get("positions") or {}
    speaker = clip.get("speaker", present_chars[0]["name"] if present_chars else "")
    speaker_verb = clip.get("speaker_verb", "says")

    # 多角色位置关系句（谁在谁旁边/对面/左边/右边），用于模型区分身份
    if len(present_chars) >= 2:
        pos_sentences = []
        for c in present_chars:
            pos = positions.get(c["name"])
            if pos:
                pos_sentences.append(f"{c['name']} {pos}")
        if pos_sentences:
            action = f"{action}; frame positions: " + ", ".join(pos_sentences)

    seg = f"{shot_name} {camera}, {action}"

    # 台词提示：说话人必须带完整外貌+位置，让模型知道"哪个角色"在说话
    if line:
        speaker_full = ""
        for c in present_chars:
            if c["name"] == speaker:
                pos = positions.get(speaker, "")
                speaker_full = f"{c['name']} ({c['desc']}" + (f", {pos}" if pos else "") + ")"
                break
        if not speaker_full and speaker:
            speaker_full = speaker
        if speaker_full:
            seg = f"{shot_name} {camera}, {action}, {speaker_full} {speaker_verb}: '{line}'"
        else:
            seg = f"{shot_name} {camera}, {action}, {speaker_verb}: '{line}'"

    seg += f", audio: {audio}"

    if not line:
        seg += ", no dialogue, silent moment"

    # 非末段加镜头转换（单段默认无）
    if clip.get("transition"):
        seg += f", then the camera {clip.get('transition')}"
    return seg

def build_ltxv_add_guide_multi(seg_lengths, strengths=None):
    """frame_indices 由 segment_lengths 累加"""
    frame_indices = []
    acc = 0
    for s in seg_lengths:
        frame_indices.append(acc)
        acc += s
    if not strengths:
        strengths = [1.0] + [0.9] * (len(seg_lengths) - 1)
    return {
        "frame_indices": frame_indices,
        "strengths": strengths,
    }

def write_json(clip, config, outdir, dry_run=False):
    """为单个 clip 生成 JSON 文件"""
    present_chars = [c for c in config["characters"] if c["name"] in clip.get("present_chars", [])]
    scene = clip.get("scene", "")

    # 时长
    line_len = len(clip.get("line", ""))
    action_nodes = clip.get("action_nodes", 0)
    if line_len > 0:
        frames = calc_frames(line_len, action_nodes)
    else:
        frames = calc_frames_no_dialogue(action_nodes)

    # global_prompt
    global_prompt = build_global_prompt(config.get("style_base", ""), present_chars, scene, clip.get("positions"))

    # local_prompts
    local_prompt = build_local_prompt(clip, present_chars)

    # ltxv_add_guide_multi
    ltxv = build_ltxv_add_guide_multi([frames])

    data = {
        "global_prompt": global_prompt,
        "local_prompts": local_prompt,
        "segment_lengths": ",".join(str(f) for f in [frames]),
        "ltxv_add_guide_multi": ltxv,
        "negative_prompt": NEGATIVE_PROMPT,
    }

    outpath = outdir / f"LTX_{clip['id']}.json"
    if dry_run:
        print(f"[dry-run] 将写入 {outpath.name}: frames={frames}, chars={len(present_chars)}")
        return

    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"OK {outpath.name}: frames={frames}, chars={len(present_chars)}")

def main():
    parser = argparse.ArgumentParser(description="LTX 2.3 JSON 通用生成器")
    parser.add_argument("--config", "-c", required=True, help="项目配置文件 project.yaml")
    parser.add_argument("--outdir", "-o", default="提示词", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览不写文件")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"项目: {config.get('project', 'unnamed')} | clips: {len(config['clips'])}")
    for clip in config["clips"]:
        write_json(clip, config, outdir, dry_run=args.dry_run)
    print("完成")

if __name__ == "__main__":
    main()
