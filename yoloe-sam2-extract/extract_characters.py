#!/usr/bin/env python3
"""YOLOE 检测 + SAM2.1 分割 提取卡通人物脚本。

用法:
    python3 extract_characters.py <输入图片> [输出目录] [--conf 0.10] [--expand 0.0]

示例:
    python3 extract_characters.py /path/to/page.png /path/to/output_dir
"""
import sys, io, os, argparse

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.join(SKILL_DIR, 'code')
MODEL_DIR = os.path.join(SKILL_DIR, 'model')

os.chdir(SKILL_DIR)
sys.path.insert(0, CODE_DIR)
sys.path.insert(0, os.path.join(CODE_DIR, 'sam2_code'))
sys.path.insert(0, os.path.join(CODE_DIR, 'CLIP'))
sys.path.insert(0, os.path.join(CODE_DIR, 'ml-mobileclip'))

from hydra.core.global_hydra import GlobalHydra
GlobalHydra.instance().clear()
from hydra import initialize, compose
from hydra.utils import instantiate
from omegaconf import OmegaConf
from ultralytics import YOLOE
from PIL import Image
import numpy as np

YOLOE_CKPT = os.path.join(MODEL_DIR, 'yoloe', 'yoloe-11s-seg.pt')
SAM2_CKPT = os.path.join(MODEL_DIR, 'sam2', 'sam2.1_hiera_tiny.pt')
SAM2_CFG = 'sam2.1/sam2.1_hiera_t.yaml'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='输入图片路径')
    parser.add_argument('output', nargs='?', help='输出目录（默认输入同目录）')
    parser.add_argument('--conf', type=float, default=0.10, help='YOLOE 置信度阈值')
    parser.add_argument('--expand', type=float, default=0.0, help='框扩大比例，0=原始框')
    parser.add_argument('--names', default='cartoon character, cartoon animal', help='识别类别（逗号分隔）')
    parser.add_argument('--iou', type=float, default=0.3, help='去重 IoU 阈值')
    parser.add_argument('--text-model', default='blt', choices=['s0', 's1', 's2', 'b', 'blt'],
                        help='MobileCLIP 文本编码器变体（s0 最小 206MB，blt 最大 572MB）')
    args = parser.parse_args()

    SRC = args.input
    OUT = args.output or os.path.join(os.path.dirname(os.path.abspath(SRC)), os.path.basename(SRC) + '_提取')
    OUT = OUT if OUT.endswith(os.sep) else OUT + os.sep
    os.makedirs(OUT, exist_ok=True)
    EXPAND = args.expand
    names = [n.strip() for n in args.names.split(',')]

    with io.StringIO() as buf:
        old = sys.stdout
        sys.stdout = buf
        model = YOLOE(YOLOE_CKPT)
        model.to('cpu')
        model.args['text_model'] = f'mobileclip:{args.text_model}'
        model.model.args['text_model'] = f'mobileclip:{args.text_model}'
        model.set_classes(names, model.get_text_pe(names))
        results = model.predict(SRC, conf=args.conf, verbose=False)
        sys.stdout = old

    r = results[0]
    boxes = r.boxes.xyxy.cpu().numpy()
    clss = r.boxes.cls.cpu().numpy().astype(int)
    confs = r.boxes.conf.cpu().numpy()
    W, H = Image.open(SRC).size

    def iou(a, b):
        x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
        x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
        inter = max(0, x2-x1) * max(0, y2-y1)
        ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
        return inter/ua if ua > 0 else 0

    keep = []
    for i in range(len(boxes)):
        if not any(iou(boxes[i], boxes[j]) > args.iou for j in keep):
            keep.append(i)

    print(f'检测框: {len(boxes)}，去重后: {len(keep)}')

    os.chdir(SKILL_DIR)
    GlobalHydra.instance().clear()
    with initialize(version_base=None, config_path='configs'):
        cfg = compose(config_name='sam2.1/sam2.1_hiera_t.yaml')
    OmegaConf.resolve(cfg)
    from sam2.build_sam import _load_checkpoint
    sam_model = instantiate(cfg.model, _recursive_=True)
    _load_checkpoint(sam_model, SAM2_CKPT)
    sam_model = sam_model.to('cpu')
    sam_model.eval()

    from sam2.sam2_image_predictor import SAM2ImagePredictor
    predictor = SAM2ImagePredictor(sam_model)
    src = Image.open(SRC).convert('RGB')
    arr = np.array(src)
    predictor.set_image(arr)

    for n, i in enumerate(keep):
        x1, y1, x2, y2 = [float(v) for v in boxes[i]]
        bw, bh = x2-x1, y2-y1
        ex1, ey1 = max(0, x1-EXPAND*bw), max(0, y1-EXPAND*bh)
        ex2, ey2 = min(W, x2+EXPAND*bw), min(H, y2+EXPAND*bh)
        box = np.array([ex1, ey1, ex2, ey2])

        masks, scores, _ = predictor.predict(box=box, multimask_output=True)
        best = int(np.argmax(scores))
        m = masks[best]

        src_rgba = src.convert('RGBA')
        crop = src_rgba.crop((round(ex1), round(ey1), round(ex2), round(ey2)))
        ma = (m[round(ey1):round(ey2), round(ex1):round(ex2)] * 255).astype(np.uint8)
        out_img = crop.copy()
        out_img.putalpha(Image.fromarray(ma))
        out_img = out_img.crop(out_img.getbbox())
        nm = names[clss[i]] if clss[i] < len(names) else str(clss[i])
        path = f'{OUT}角色_{n+1:02d}_{nm.replace(" ", "_")}.png'
        out_img.save(path)
        print(f'  角色_{n+1:02d}: {nm} conf={confs[i]:.3f} 尺寸={out_img.size} score={scores[best]:.3f}')

    print('完成，输出目录:', OUT)


if __name__ == '__main__':
    main()
