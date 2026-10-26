"""Normalize a supplied club raster logo without changing the source file."""
import argparse
from pathlib import Path
from PIL import Image, ImageOps


def install(source: Path, output: Path):
    if source.resolve() == output.resolve():
        raise ValueError('Chọn tệp nguồn khác đường dẫn đầu ra để giữ nguyên bản gốc.')
    with Image.open(source, formats=['PNG', 'JPEG', 'WEBP']) as image:
        image.load()
        if min(image.size) < 32:
            raise ValueError('Logo cần ít nhất 32 × 32 pixel.')
        normalized = ImageOps.exif_transpose(image).convert('RGBA')
        normalized.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        output.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(output, format='PNG', optimize=True)
    with Image.open(output) as check:
        check.verify()
    print(f'LOGO_READY {output.resolve()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cài logo chính thức CMC Infrasec (PNG/JPEG/WebP).')
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent / 'public/club-logo.png')
    args = parser.parse_args()
    install(args.source, args.output)
