#!/usr/bin/env python3
import os, sys, argparse, cv2, torch
import numpy as np
from PIL import Image
from transformers import Sam3Model, Sam3Processor

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SAM3_DIR = os.path.join(SKILL_DIR, "model", "sam3")

def extract_objects(input_path, output_dir, prompt, threshold=0.75, mask_threshold=0.25, device_override=None, categories=None):
    if device_override == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    os.makedirs(output_dir, exist_ok=True)
    if device_override in ("cuda", "cpu"):
        device = device_override
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"加载 SAM 3 模型 ({device})...")
    model = Sam3Model.from_pretrained(SAM3_DIR).to(device)
    processor = Sam3Processor.from_pretrained(SAM3_DIR)
    model.eval()
    print(f"SAM 3 加载完成 (840M)")

    img = Image.open(input_path).convert("RGB")
    img_np = np.array(img)
    print(f"图片: {input_path}  ({img.size[0]}x{img.size[1]})")

    if categories:
        category_map = {}
        for cat in categories.split(","):
            if ":" in cat:
                name, text = cat.split(":", 1)
                category_map[name.strip()] = text.strip()
            else:
                category_map[cat.strip()] = cat.strip()

        prompts = list(set(category_map.values()))
        prompt_to_names = {}
        for name, text in category_map.items():
            prompt_to_names[text] = name
    else:
        prompts = [p.strip() for p in prompt.split(",") if p.strip()]
        prompt_to_names = {}

    all_masks = []
    CLOSE_KERNEL, CLOSE_ITER = 15, 3
    kernel = np.ones((CLOSE_KERNEL, CLOSE_KERNEL), np.uint8)

    for p in prompts:
        print(f"  提示词: \"{p}\"")
        inputs = processor(images=img, text=p, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        results = processor.post_process_instance_segmentation(
            outputs, threshold=threshold, mask_threshold=mask_threshold,
            target_sizes=inputs.get("original_sizes").tolist()
        )[0]

        if device == "cuda":
            torch.cuda.empty_cache()

        for mask, box, score in zip(results["masks"], results["boxes"], results["scores"]):
            mask_np = mask.cpu().numpy().astype(np.uint8)
            x1, y1, x2, y2 = [int(v) for v in box.tolist()]

            mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_CLOSE, kernel, iterations=CLOSE_ITER)
            mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_OPEN, kernel, iterations=1)
            mask_np = cv2.GaussianBlur(mask_np, (5, 5), 0)
            mask_np = (mask_np > 0.5).astype(np.uint8)

            if mask_np[y1:y2, x1:x2].sum() < 50:
                continue

            roi = np.zeros((y2 - y1, x2 - x1, 4), dtype=np.uint8)
            roi[:, :, :3] = img_np[y1:y2, x1:x2]
            roi[:, :, 3] = mask_np[y1:y2, x1:x2] * 255

            all_masks.append((roi, score.item(), mask_np > 0, p))

    if not all_masks:
        print("未检测到目标")
        return

    all_masks.sort(key=lambda x: x[1], reverse=True)
    if categories:
        prompt_best = {}
        for roi, score, a, prompt in all_masks:
            if prompt not in prompt_best or score > prompt_best[prompt][1]:
                prompt_best[prompt] = (roi, score, a)
        kept = []
        for prompt, (roi, score, a) in prompt_best.items():
            dup = False
            for k_roi, k_score, b, _ in kept:
                inter = (a & b).sum()
                union = (a | b).sum()
                if union > 0 and inter / union > 0.5:
                    dup = True
                    break
            if not dup:
                kept.append((roi, score, a, prompt))
    else:
        kept = []
        for roi, score, a, prompt in all_masks:
            dup = False
            for k_roi, k_score, b, _ in kept:
                inter = (a & b).sum()
                union = (a | b).sum()
                if union > 0 and inter / union > 0.5:
                    dup = True
                    break
            if not dup:
                kept.append((roi, score, a, prompt))

    print(f"去重后保留 {len(kept)} / {len(all_masks)} 个目标")
    for i, (roi, score, _, prompt) in enumerate(kept):
        if categories and prompt in prompt_to_names:
            out_name = f"{prompt_to_names[prompt]}.png"
        else:
            out_name = f"人物-{i+1}.png"
        Image.fromarray(roi).save(os.path.join(output_dir, out_name))
        print(f"  [{i+1}] score={score:.3f}  {roi.shape[1]}x{roi.shape[0]}  -> {out_name}")

    print(f"完成! {len(all_masks)} 个物体已提取到 {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAM 3 文本提示词目标提取")
    parser.add_argument("--input", "-i", required=True, help="输入图片路径")
    parser.add_argument("--output", "-o", default="./人物提取结果", help="输出目录")
    parser.add_argument("--prompt", "-p", default="", help="文本提示词，多个用逗号分隔")
    parser.add_argument("--categories", "-c", default="", help="按类别提取，格式: 类别名:提示词,类别名:提示词")
    parser.add_argument("--threshold", type=float, default=0.75, help="检测置信度阈值 (默认: 0.75)")
    parser.add_argument("--mask-threshold", type=float, default=0.25, help="掩码二值化阈值 (默认: 0.25)")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto",
                        help="运行设备: auto 自动检测(有GPU用GPU), cuda 强制GPU, cpu 强制CPU (默认: auto)")
    args = parser.parse_args()

    extract_objects(args.input, args.output, args.prompt, args.threshold, args.mask_threshold, args.device, args.categories)
