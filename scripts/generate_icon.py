from PIL import Image, ImageDraw, ImageFont
import os

out = os.path.join(os.path.dirname(__file__), '..', 'layoutpress.ico')
# create base image
size = 256
img = Image.new('RGBA', (size, size), (0,0,0,0))
d = ImageDraw.Draw(img)
# simple logo: rounded square with initials "IM"
bg = (60,120,200)
rect_radius = 40
# draw rounded rectangle
try:
    from PIL import ImageFilter
    # rounded rectangle fallback if available
    d.rounded_rectangle((20,20,size-20,size-20), radius=rect_radius, fill=bg)
except Exception:
    d.rectangle((20,20,size-20,size-20), fill=bg)
# draw initials
try:
    fnt = ImageFont.truetype('arial.ttf', 120)
except Exception:
    fnt = ImageFont.load_default()
text = "LP"
try:
    bbox = d.textbbox((0,0), text, font=fnt)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
except Exception:
    try:
        w, h = fnt.getsize(text)
    except Exception:
        w, h = (60, 30)
d.text(((size-w)/2,(size-h)/2-10), text, font=fnt, fill=(255,255,255))
# save multiple sizes into .ico
sizes = [(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)]
icons = [img.resize(s, Image.LANCZOS) for s in sizes]
icons[0].save(out, format='ICO', sizes=sizes)
print('Wrote', out)
