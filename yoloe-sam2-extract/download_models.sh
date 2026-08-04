#!/bin/bash
# 下载 YOLOE + SAM2.1 + MobileCLIP 模型权重到本 skill 的 model/ 目录
# 用法: bash download_models.sh
# 需要 wget 和 python3（huggingface_hub，用于 HF 下载）

set -e
cd "$(dirname "$0")"

mkdir -p model/yoloe model/sam2 model/mobileclip

echo "[1/3] 下载 YOLOE-11S-seg (27MB)..."
wget -q --show-progress -O model/yoloe/yoloe-11s-seg.pt \
  "https://huggingface.co/jameslahm/yoloe/resolve/main/yoloe-11s-seg.pt"

echo "[2/3] 下载 SAM2.1 hiera tiny (149MB)..."
wget -q --show-progress -O model/sam2/sam2.1_hiera_tiny.pt \
  "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"

echo "[3/3] 下载 MobileCLIP-BLT 文本编码器 (572MB)..."
wget -q --show-progress -O model/mobileclip/mobileclip_blt.pt \
  "https://huggingface.co/apple/MobileCLIP-B-LT/resolve/main/mobileclip_blt.pt"

echo "建立软链（YOLOE 用相对路径加载 mobileclip，SAM2 用 hydra 相对路径加载 configs）..."
ln -sf model/mobileclip/mobileclip_blt.pt mobileclip_blt.pt
ln -sf model/mobileclip/mobileclip_blt.pt code/sam2_code/sam2/mobileclip_blt.pt 2>/dev/null || true
ln -sf code/sam2_code/sam2/configs configs

echo "完成！模型已下载到 model/"
ls -lh model/yoloe/ model/sam2/ model/mobileclip/
