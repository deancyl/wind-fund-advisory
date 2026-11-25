import io
from PIL import Image
import numpy as np

def slice_long_screenshot_for_ocr(image_bytes: bytes, target_height: int = 1000, overlap: int = 150):
    """
    自适应无损长截图纵向切片算法：
    1. 保持 100% 原始宽度不压缩；
    2. 按每段 target_height (默认 1000px)、上下 overlap (默认 150px) 纵向切块；
    3. 返回切片列表 (PIL.Image or numpy array) 与每个切片的 y 坐标偏移量。
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    w, h = img.size
    slices = []
    
    if h <= target_height:
        return [(img, 0)]
    
    step = target_height - overlap
    cur_y = 0
    while cur_y < h:
        end_y = min(cur_y + target_height, h)
        crop_box = (0, cur_y, w, end_y)
        cropped = img.crop(crop_box)
        slices.append((cropped, cur_y))
        if end_y >= h:
            break
        cur_y += step
        
    return slices

# Test on synthetic 1080x8500 image
test_img = Image.new('RGB', (1080, 8500), color=(255, 255, 255))
buf = io.BytesIO()
test_img.save(buf, format='PNG')
raw_bytes = buf.getvalue()

res = slice_long_screenshot_for_ocr(raw_bytes)
print(f"Total slices created: {len(res)}")
for i, (seg, y_off) in enumerate(res):
    print(f"Slice {i}: size={seg.size}, y_offset={y_off}")
