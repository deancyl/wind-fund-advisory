from PIL import Image

img_path = r"C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794406255999_c8abd7ad.png"
im = Image.open(img_path)
print("Image size:", im.size)

# Crop top 1200px
crop1 = im.crop((0, 0, im.width, min(1400, im.height)))
crop1.save(r"d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\top_crop.png")

# Crop next 1400px (1200 to 2600)
crop2 = im.crop((0, 1200, im.width, min(2600, im.height)))
crop2.save(r"d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\mid_crop.png")

# Crop next 1400px (2400 to end)
crop3 = im.crop((0, 2400, im.width, im.height))
crop3.save(r"d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\bottom_crop.png")

print("Saved all crops successfully!")
