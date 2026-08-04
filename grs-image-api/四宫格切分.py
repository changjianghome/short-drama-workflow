#!/usr/bin/env python3
"""
四宫格自动切分工具 v3
自动识别白边/黑边分割线，精确切分并去除边缘杂色

用法:
    python 四宫格切分.py <输入图片> [选项]

示例:
    python 四宫格切分.py 分镜.png
    python 四宫格切分.py 分镜.png -p 10 -o 输出目录
    python 四宫格切分.py 分镜.png --split-mode rows  # 按行切分（2张）
"""

import argparse
import os
import sys
import numpy as np
from PIL import Image


def detect_division_lines(arr, threshold=235, min_gap=10):
    """
    检测分割线位置（支持白边和黑边）
    """
    h, w = arr.shape[:2]

    # 排除边缘（上下左右各2%）
    margin_h = int(h * 0.02)
    margin_w = int(w * 0.02)

    # 检测白色区域
    white_mask = np.all(arr > threshold, axis=2)
    # 检测黑色区域
    black_mask = np.all(arr < 15, axis=2)
    # 合并
    division_mask = white_mask | black_mask

    # 计算比例，排除边缘
    row_ratio = np.sum(division_mask, axis=1) / w
    col_ratio = np.sum(division_mask, axis=0) / h

    # 排除边缘区域
    row_ratio[:margin_h] = 0
    row_ratio[h-margin_h:] = 0
    col_ratio[:margin_w] = 0
    col_ratio[w-margin_w:] = 0

    # 找到比例 > 0.95 的行/列
    row_is_division = row_ratio > 0.95
    col_is_division = col_ratio > 0.95

    def extract_division_points(is_division, min_gap):
        """从布尔数组提取分割点"""
        points = np.where(is_division)[0]
        if len(points) == 0:
            return []

        divisions = []
        start = points[0]
        prev = points[0]

        for p in points[1:]:
            if p - prev > 1:
                end = prev
                if end - start >= min_gap - 1:
                    mid = (start + end) // 2
                    divisions.append(mid)
                start = p
            prev = p

        end = points[-1]
        if end - start >= min_gap - 1:
            mid = (start + end) // 2
            divisions.append(mid)

        return divisions

    row_divisions = extract_division_points(row_is_division, min_gap)
    col_divisions = extract_division_points(col_is_division, min_gap)

    return row_divisions, col_divisions


def split_grid(img, row_divisions, col_divisions, padding=0):
    """根据分割点切分图片"""
    w, h = img.size
    results = []

    # 生成切分区间
    row_ranges = []
    prev = 0
    for r in sorted(row_divisions):
        row_ranges.append((prev, r))
        prev = r
    row_ranges.append((prev, h))

    col_ranges = []
    prev = 0
    for c in sorted(col_divisions):
        col_ranges.append((prev, c))
        prev = c
    col_ranges.append((prev, w))

    # 切分
    idx = 1
    for row_start, row_end in row_ranges:
        for col_start, col_end in col_ranges:
            x1 = max(0, col_start + padding)
            y1 = max(0, row_start + padding)
            x2 = min(w, col_end - padding)
            y2 = min(h, row_end - padding)

            if x2 > x1 and y2 > y1:
                cropped = img.crop((x1, y1, x2, y2))
                name = f"part_{idx:02d}"
                results.append((name, cropped))
                idx += 1

    return results


def main():
    parser = argparse.ArgumentParser(
        description='四宫格自动切分工具 - 自动识别分割线并去除白边/黑边',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 分镜.png                    # 自动切分，输出到当前目录
  %(prog)s 分镜.png -p 10              # 内缩10像素
  %(prog)s 分镜.png -o 输出目录        # 指定输出目录
  %(prog)s 分镜.png --split-mode rows  # 只按行切分（输出2张）
  %(prog)s 分镜.png --split-mode cols  # 只按列切分（输出2张）
        """
    )

    parser.add_argument('input', help='输入图片路径')
    parser.add_argument('-p', '--padding', type=int, default=8,
                        help='内缩像素数 (默认: 8)')
    parser.add_argument('-o', '--output', default=None,
                        help='输出目录 (默认: 输入图片所在目录)')
    parser.add_argument('--ext', default='png', choices=['png', 'jpg', 'jpeg', 'webp'],
                        help='输出格式 (默认: png)')
    parser.add_argument('--split-mode', default='grid',
                        choices=['grid', 'rows', 'cols'],
                        help='切分模式 (默认: grid)')
    parser.add_argument('--min-gap', type=int, default=10,
                        help='最小分割线宽度 (默认: 10)')
    parser.add_argument('--threshold', type=int, default=235,
                        help='白色检测阈值 (默认: 235)')
    parser.add_argument('--debug', action='store_true',
                        help='显示调试信息')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 找不到文件 '{args.input}'")
        sys.exit(1)

    img = Image.open(args.input)
    arr = np.array(img)

    print(f"输入: {args.input}")
    print(f"尺寸: {img.size[0]}x{img.size[1]}")

    row_divs, col_divs = detect_division_lines(arr, args.threshold, args.min_gap)

    if args.debug:
        print(f"行分割点: {row_divs}")
        print(f"列分割点: {col_divs}")

    if args.split_mode == 'rows':
        col_divs = []
    elif args.split_mode == 'cols':
        row_divs = []

    if len(row_divs) == 0 and len(col_divs) == 0:
        print("未检测到分割线，自动估算为2x2网格...")
        w, h = img.size
        col_divs = [w // 2]
        row_divs = [h // 2]

    print(f"分割点: 行={row_divs}, 列={col_divs}")

    parts = split_grid(img, row_divs, col_divs, args.padding)

    output_dir = args.output or os.path.dirname(args.input) or '.'
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(args.input))[0]

    print(f"\n切分结果 ({len(parts)} 张):")
    for name, part in parts:
        output_path = os.path.join(output_dir, f"{base_name}_{name}.{args.ext}")
        part.save(output_path)
        print(f"  {output_path} ({part.size[0]}x{part.size[1]})")


if __name__ == '__main__':
    main()
