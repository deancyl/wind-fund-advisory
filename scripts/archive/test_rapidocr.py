from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image

ocr = RapidOCR()
# Test on a blank image with text
img = Image.new('RGB', (300, 100), color=(255, 255, 255))
from PIL import ImageDraw
d = ImageDraw.Draw(img)
d.text((10, 10), "招商中证白酒指数(LOF)A 524.24", fill=(0, 0, 0))
res, elapse = ocr(np.array(img))
print("Test synthetic image OCR result:", res)
