"""Prepare web copies while retaining the complete artwork and supplied originals."""
from pathlib import Path
import shutil
from PIL import Image, ImageOps

root = Path(__file__).resolve().parents[2]
source = root / 'assets/branding/originals/club-primary-original.png'
with Image.open(source) as original:
    image = ImageOps.exif_transpose(original).convert('RGBA')
    # The supplied PNG has some semi-opaque edge pixels. Keep its black background,
    # rather than letting the page color bleed through those pixels.
    background = Image.new('RGBA', image.size, (2, 2, 2, 255))
    image = Image.alpha_composite(background, image).convert('RGB')
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    image.save(root / 'public/club-logo.png', format='PNG', optimize=True)
shutil.copy2(root / 'assets/branding/originals/club-alternative-original.jpg', root / 'public/club-logo-light.jpg')
for name in ('club-logo.png', 'club-logo-light.jpg'):
    with Image.open(root / 'public' / name) as image:
        assert image.convert('RGBA').getchannel('A').getextrema() == (255, 255)
print('ASSETS_READY primary=opaque-black alternative=opaque-white originals=unchanged')
