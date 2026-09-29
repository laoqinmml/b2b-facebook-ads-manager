"""Turn a cleaned black-on-white logo into the full deliverable set.

Input is the cleaned logo: pure black letterforms on a uniform white
background (produced by $imagegen or by scripts/logo_from_photo.py). Output:

    {prefix}-whitebg.png                  white background, black logo
    {prefix}-whitebg@2x.png               2x for high-DPI and print
    {prefix}-transparent.png              transparent, black logo
    {prefix}-white-reversed.png           transparent, white logo (dark backgrounds)
    {prefix}-square-1080.png              1080x1080, Facebook Page profile picture
    {prefix}-square-1080-transparent.png  1080x1080 transparent

Example:

    python scripts/logo_variants.py --src clean-logo.png \
        --prefix ronghui-logo --out-dir output/logo
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops


def estimate_black_level(gray: Image.Image, percentile: float) -> int:
    """Darkest tone that is still ink rather than paper noise."""
    hist = gray.histogram()
    total = sum(hist)
    seen = 0
    for value, count in enumerate(hist):
        seen += count
        if seen > total * percentile:
            return value
    return 0


def build_alpha(gray: Image.Image, black: int) -> Image.Image:
    """Coverage of black over white: 0 on paper, 255 on strokes."""
    scale = 255.0 / max(1, 255 - black)
    alpha = gray.point(lambda v: max(0, min(255, int((255 - v) * scale))))
    return ImageChops.multiply(alpha, gray.point(lambda v: 255 if v < 250 else 0))


def square_canvas(layer: Image.Image, side: int, fill: float, transparent: bool) -> Image.Image:
    scale = min(side * fill / layer.width, side * fill / layer.height)
    inner = layer.resize((round(layer.width * scale), round(layer.height * scale)), Image.LANCZOS)
    mode = "RGBA" if transparent else "RGB"
    background = (0, 0, 0, 0) if transparent else (255, 255, 255)
    canvas = Image.new(mode, (side, side), background)
    offset = ((side - inner.width) // 2, (side - inner.height) // 2)
    if transparent:
        canvas.alpha_composite(inner)
    else:
        canvas.paste(inner, offset)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="从干净的黑白 logo 底稿生成全套品牌资产")
    parser.add_argument("--src", required=True, help="干净底稿：纯黑 logo + 纯白背景")
    parser.add_argument("--prefix", required=True, help="输出文件名前缀，例如 ronghui-logo")
    parser.add_argument("--out-dir", default="output/logo")
    parser.add_argument("--margin", type=int, default=40, help="裁切后四周留白像素")
    parser.add_argument("--black-percentile", type=float, default=0.002, help="黑场估计分位（默认 0.002）")
    parser.add_argument("--square", type=int, default=1080, help="方形头像边长")
    parser.add_argument("--square-fill", type=float, default=0.86, help="logo 在方形画布中的占比，留出圆裁余量")
    parser.add_argument("--no-2x", action="store_true", help="不输出 @2x 版本")
    args = parser.parse_args()

    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"文件不存在：{src}")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    img = Image.open(src).convert("RGB")
    gray = img.convert("L")
    black = estimate_black_level(gray, args.black_percentile)
    alpha = build_alpha(gray, black)

    bbox = alpha.getbbox()
    if not bbox:
        raise SystemExit("没找到任何笔画：底稿可能不是黑字白底，或黑场估计失真")
    box = (
        max(0, bbox[0] - args.margin),
        max(0, bbox[1] - args.margin),
        min(alpha.width, bbox[2] + args.margin),
        min(alpha.height, bbox[3] + args.margin),
    )
    alpha = alpha.crop(box)
    print(f"black level: {black} | trimmed: {alpha.size}")

    white_bg = Image.new("RGB", alpha.size, (255, 255, 255))
    white_bg.paste(Image.new("RGB", alpha.size, (0, 0, 0)), (0, 0), alpha)
    white_bg.save(out / f"{args.prefix}-whitebg.png")
    if not args.no_2x:
        white_bg.resize((white_bg.width * 2, white_bg.height * 2), Image.LANCZOS).save(
            out / f"{args.prefix}-whitebg@2x.png"
        )

    black_layer = Image.merge(
        "RGBA",
        (Image.new("L", alpha.size, 0), Image.new("L", alpha.size, 0), Image.new("L", alpha.size, 0), alpha),
    )
    black_layer.save(out / f"{args.prefix}-transparent.png")

    white_layer = Image.merge(
        "RGBA",
        (Image.new("L", alpha.size, 255), Image.new("L", alpha.size, 255), Image.new("L", alpha.size, 255), alpha),
    )
    white_layer.save(out / f"{args.prefix}-white-reversed.png")

    square_canvas(white_bg, args.square, args.square_fill, transparent=False).save(
        out / f"{args.prefix}-square-{args.square}.png"
    )
    square_canvas(black_layer, args.square, args.square_fill, transparent=True).save(
        out / f"{args.prefix}-square-{args.square}-transparent.png"
    )

    print(f"wrote 6 variants (prefix {args.prefix}) to {out}")
    print("检查：200% 放大看边缘；透明版放到深色底上看有没有白边；方形版圆裁后是否仍有留白。")


if __name__ == "__main__":
    main()
