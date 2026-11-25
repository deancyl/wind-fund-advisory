from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

ocr = RapidOCR()
img_path = r"C:\Users\deanc\.gemini\antigravity\brain\1395b6f9-733c-4446-9cdb-f33a19e5f711\.user_uploaded\media_1794236135877_65af68f3.jpg"
img = Image.open(img_path)
print(f"Loaded image {img.size}")

# Because the image is only 127x1024, let's upscale it using PIL BICUBIC or LANCZOS
# e.g., 8x width: 1016 x 8192
img_upscaled = img.resize((img.width * 8, img.height * 8), Image.Resampling.LANCZOS)
print(f"Upscaled to {img_upscaled.size}")

# Slice into segments of height 1000 with 150 overlap
segments = []
h_step = 1000 - 150
cur_y = 0
total_h = img_upscaled.height
idx = 0

all_ocr_results = []
while cur_y < total_h:
    end_y = min(cur_y + 1000, total_h)
    box = (0, cur_y, img_upscaled.width, end_y)
    seg = img_upscaled.crop(box)
    seg_np = np.array(seg)
    res, _ = ocr(seg_np)
    if res:
        for item in res:
            box_coords, text, conf = item
            # adjust y coordinate
            all_ocr_results.append((cur_y, text, conf))
    print(f"Segment {idx} (y={cur_y}..{end_y}): {len(res) if res else 0} boxes detected")
    cur_y += h_step
    idx += 1

print("\n--- Detected Texts ---")
for y, text, conf in all_ocr_results:
    print(f"[y={y:4d}, conf={conf:.2f}] {text}")
