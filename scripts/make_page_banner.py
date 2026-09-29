"""Build a Facebook Page cover banner from real photos (no AI generation).

Deterministic compositing: real factory/product photos plus exact typography,
so company names and Chinese characters are never misspelled. Exports both the
upload size (1640x624) and Facebook's desktop display size (820x312) so small
text legibility can be checked before publishing.

Two layouts:

    band       dark brand band on top, real photo strip along the bottom
    fullbleed  full-bleed photo, dark scrim, centred bilingual lock-up

Examples:

    python scripts/make_page_banner.py --photo row.png --style band \
        --kicker "KITCHEN SMALL APPLIANCE FACTORY  ·  OEM / ODM" \
        --title-en "ZHONGSHAN RONGHUI ELECTRIC APPLIANCE CO., LTD." \
        --title-cn "中山市荣惠电器有限公司" \
        --sub1 "Blenders · Mixers · Coffee Makers · Induction Cookers" \
        --out-dir output/banner --prefix fb-cover-ronghui-band

    python scripts/make_page_banner.py --photo showroom.png --style fullbleed \
        --title-cn "中山市荣惠电器有限公司" \
        --title-en "ZHONGSHAN RONGHUI ELECTRIC APPLIANCE CO., LTD." \
        --sub1 "Blenders · Mixers · Coffee Makers" \
        --sub2 "Export to Southeast Asia · Middle East · Africa · South America" \
        --out-dir output/banner --prefix fb-cover-ronghui-fullbleed
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1640, 624
DESKTOP_SIZE = (820, 312)

LATIN_BOLD_CANDIDATES = (
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)
LATIN_SEMI_CANDIDATES = (
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
LATIN_REGULAR_CANDIDATES = (
    r"C:\Windows\Fonts\segoeui.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)
CJK_BOLD_CANDIDATES = (
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
)
CJK_REGULAR_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def hex_color(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise argparse.ArgumentTypeError(f"颜色需要 6 位十六进制，例如 F5B33C：{value}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def resolve_font(candidates: tuple[str, ...], override: str | None, label: str) -> str:
    if override:
        if not Path(override).exists():
            raise SystemExit(f"--{label} 指定的字体不存在：{override}")
        return override
    for path in candidates:
        if Path(path).exists():
            return path
    raise SystemExit(
        f"找不到可用字体（{label}），请用 --{label} 指定字体文件。已尝试：\n  " + "\n  ".join(candidates)
    )


def load(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def text_w(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, tracking: int = 0) -> float:
    if not tracking:
        return draw.textlength(text, font=font)
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * max(0, len(text) - 1)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill,
    tracking: int = 0,
    center: bool = False,
) -> None:
    x, y = xy
    if center:
        x -= text_w(draw, text, font, tracking) / 2
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def cover(img: Image.Image, w: int, h: int, y_anchor: float = 0.5) -> Image.Image:
    """Scale to cover w x h, cropping vertically around y_anchor (0=top, 1=bottom)."""
    scale = max(w / img.width, h / img.height)
    nw, nh = round(img.width * scale), round(img.height * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = round((nh - h) * y_anchor)
    return resized.crop((left, top, left + w, top + h))


def vertical_scrim(size: tuple[int, int], stops: list[tuple[float, int]], tint=(5, 12, 24)) -> Image.Image:
    """Alpha veil that ramps top -> bottom. stops = [(position 0..1, alpha 0..255)]."""
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = layer.load()
    ordered = sorted(stops)
    for y in range(h):
        t = y / max(1, h - 1)
        alpha = ordered[-1][1] if t > ordered[-1][0] else ordered[0][1]
        for i in range(len(ordered) - 1):
            p0, a0 = ordered[i]
            p1, a1 = ordered[i + 1]
            if p0 <= t <= p1:
                k = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                alpha = round(a0 + (a1 - a0) * k)
                break
        row = tint + (alpha,)
        for x in range(w):
            px[x, y] = row
    return layer


def shadowed_text(
    base: Image.Image,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill,
    tracking: int = 0,
    center: bool = False,
    blur: int = 6,
    alpha: int = 170,
) -> None:
    """Draw text with a soft drop shadow so it survives a busy photo."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_tracked(ImageDraw.Draw(layer), (xy[0] + 2, xy[1] + 3), text, font, (0, 0, 0, alpha), tracking, center)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    draw_tracked(ImageDraw.Draw(base), xy, text, font, fill, tracking, center)


def band_variant(args, fonts: dict[str, str]) -> Image.Image:
    """Dark brand band on top, real photo strip along the bottom."""
    canvas = Image.new("RGBA", (W, H), args.navy_top + (255,))
    band_h = args.band_height

    grad = Image.new("RGBA", (W, band_h))
    px = grad.load()
    for y in range(band_h):
        k = y / max(1, band_h - 1)
        row = tuple(round(args.navy_top[i] + (args.navy_bottom[i] - args.navy_top[i]) * k) for i in range(3))
        for x in range(W):
            px[x, y] = row + (255,)
    canvas.alpha_composite(grad, (0, 0))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, W, 7], fill=args.accent + (255,))

    photo = Image.open(args.photo).convert("RGB")
    strip = cover(photo, W, H - band_h, y_anchor=args.photo_anchor).convert("RGBA")
    strip.alpha_composite(vertical_scrim(strip.size, [(0.0, 120), (0.25, 40), (1.0, 0)]))
    canvas.alpha_composite(strip, (0, band_h))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, band_h - 1, W, band_h + 1], fill=(255, 255, 255, 26))
    draw.rectangle([0, band_h + 2, W, band_h + 4], fill=args.accent + (120,))

    cx = W // 2
    if args.kicker:
        draw_tracked(draw, (cx, 46), args.kicker, load(fonts["semi"], args.kicker_size), args.accent + (255,), 3, True)
    if args.title_en:
        shadowed_text(canvas, (cx, 84), args.title_en, load(fonts["latin_bold"], args.title_en_size), (255, 255, 255, 255), 1, True, 7, 165)
    draw = ImageDraw.Draw(canvas)
    if args.title_cn:
        draw_tracked(draw, (cx, 156), args.title_cn, load(fonts["cjk_bold"], args.title_cn_size), (222, 231, 242, 255), 4, True)
    if args.sub1:
        draw_tracked(draw, (cx, 213), args.sub1, load(fonts["latin"], args.sub_size), (170, 187, 208, 255), 1, True)
    if args.sub2:
        draw_tracked(draw, (cx, 244), args.sub2, load(fonts["latin"], args.sub_size - 2), (150, 168, 190, 255), 1, True)
    return canvas


def fullbleed_variant(args, fonts: dict[str, str]) -> Image.Image:
    """Full-bleed photo with a scrim and a centred bilingual lock-up."""
    photo = Image.open(args.photo).convert("RGB")
    canvas = cover(photo, W, H, y_anchor=args.photo_anchor).convert("RGBA")
    canvas.alpha_composite(vertical_scrim(canvas.size, [(0.0, 218), (0.5, 132), (1.0, 58)]))

    cx = W // 2
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([cx - 70, 92, cx + 70, 97], fill=args.accent + (255,))

    if args.kicker:
        draw_tracked(draw, (cx, 120), args.kicker, load(fonts["semi"], args.kicker_size), args.accent + (255,), 3, True)
    if args.title_cn:
        shadowed_text(canvas, (cx, 162), args.title_cn, load(fonts["cjk_bold"], args.title_cn_size), (255, 255, 255, 255), 6, True, 8, 190)
    if args.title_en:
        shadowed_text(canvas, (cx, 252), args.title_en, load(fonts["latin_bold"], args.title_en_size), (222, 231, 242, 255), 1, True, 7, 175)
    if args.sub1:
        shadowed_text(canvas, (cx, 318), args.sub1, load(fonts["semi"], args.sub_size), (240, 246, 253, 255), 1, True, 7, 195)
    if args.sub2:
        shadowed_text(canvas, (cx, 360), args.sub2, load(fonts["latin"], args.sub_size), (186, 202, 222, 255), 1, True, 6, 170)
    return canvas


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="生成 Facebook 主页封面 Banner（1640x624 + 820x312）")
    p.add_argument("--photo", required=True, help="照片：band 用产品/产线横带图，fullbleed 用整幅展厅图")
    p.add_argument("--style", choices=("band", "fullbleed"), default="band")
    p.add_argument("--out-dir", default="output/banner")
    p.add_argument("--prefix", default="fb-cover", help="输出文件名前缀")
    p.add_argument("--kicker", default="", help="第一行身份行，全大写小字")
    p.add_argument("--title-en", default="", help="英文公司名（全大写）")
    p.add_argument("--title-cn", default="", help="中文公司名")
    p.add_argument("--sub1", default="", help="品类行")
    p.add_argument("--sub2", default="", help="第二行说明（市场/认证等）")
    p.add_argument("--accent", type=hex_color, default=hex_color("F5B33C"))
    p.add_argument("--navy-top", type=hex_color, default=hex_color("09172C"))
    p.add_argument("--navy-bottom", type=hex_color, default=hex_color("0E2646"))
    p.add_argument("--band-height", type=int, default=268)
    p.add_argument("--photo-anchor", type=float, default=None, help="裁切重心 0=偏上 1=偏下；默认 band 0.44 / fullbleed 0.30")
    p.add_argument("--kicker-size", type=int, default=23)
    p.add_argument("--title-en-size", type=int, default=None, help="默认 band 45 / fullbleed 33")
    p.add_argument("--title-cn-size", type=int, default=None, help="默认 band 34 / fullbleed 60")
    p.add_argument("--sub-size", type=int, default=None, help="默认 band 22 / fullbleed 23")
    p.add_argument("--font-latin-bold", dest="font_latin_bold", default=None)
    p.add_argument("--font-latin-semi", dest="font_latin_semi", default=None)
    p.add_argument("--font-latin", dest="font_latin", default=None)
    p.add_argument("--font-cjk-bold", dest="font_cjk_bold", default=None)
    p.add_argument("--font-cjk", dest="font_cjk", default=None)
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not Path(args.photo).exists():
        raise SystemExit(f"照片不存在：{args.photo}")
    if not (args.title_en or args.title_cn):
        raise SystemExit("至少要给一个 --title-en 或 --title-cn")

    if args.photo_anchor is None:
        args.photo_anchor = 0.44 if args.style == "band" else 0.30
    if args.title_en_size is None:
        args.title_en_size = 45 if args.style == "band" else 33
    if args.title_cn_size is None:
        args.title_cn_size = 34 if args.style == "band" else 60
    if args.sub_size is None:
        args.sub_size = 22 if args.style == "band" else 23

    fonts = {
        "latin_bold": resolve_font(LATIN_BOLD_CANDIDATES, args.font_latin_bold, "font-latin-bold"),
        "semi": resolve_font(LATIN_SEMI_CANDIDATES, args.font_latin_semi, "font-latin-semi"),
        "latin": resolve_font(LATIN_REGULAR_CANDIDATES, args.font_latin, "font-latin"),
        "cjk_bold": resolve_font(CJK_BOLD_CANDIDATES, args.font_cjk_bold, "font-cjk-bold"),
        "cjk": resolve_font(CJK_REGULAR_CANDIDATES, args.font_cjk, "font-cjk"),
    }

    image = band_variant(args, fonts) if args.style == "band" else fullbleed_variant(args, fonts)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    big = image.convert("RGB")
    big_path = out_dir / f"{args.prefix}-{W}x{H}.png"
    small_path = out_dir / f"{args.prefix}-{DESKTOP_SIZE[0]}x{DESKTOP_SIZE[1]}.png"
    big.save(big_path)
    big.resize(DESKTOP_SIZE, Image.LANCZOS).save(small_path)

    print(f"wrote {big_path}")
    print(f"wrote {small_path}")
    print("发布前检查：820x312 上公司名和品类行是否仍清晰；左下角是否被主页头像压住。")


if __name__ == "__main__":
    main()
