import os 
import random
from PIL import Image 
from transforms import RGBTransform 

file_path = input("Token file:")
os.chdir(os.path.dirname(file_path))

img = Image.open(file_path)
img_rgb = img.convert('RGBA')

for i in range(100):
    img_r = RGBTransform().mix_with((random.randint(0,15)*16+15,random.randint(0,15)*16+15,random.randint(0,15)*16+15), factor=0.30).applied_to(img_rgb)
    img_r.save('token' + str(i) + '.png')