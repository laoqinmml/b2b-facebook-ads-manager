"""Extract a logo from a photo (backlit sign, door sign, printed logo) into a clean asset.

Method: estimate the local bright background with a large MaxFilter, keep pixels
that are both much darker than that background and near-black overall, then drop
everything that is not a sizeable component inside the logo area. This removes
marble veining, tile grout lines, wall texture and backlight glow without
touching the letterforms.

Outputs {prefix}-whitebg.png (for inspection) and {prefix}-transparent.png, then
run scripts/logo_variants.py to produce the full deliverable set.

Example:

    python scripts/logo_from_photo.py --src "door-sign.jpg" \
        --prefix ronghui-logo --out-dir output/logo \
        --keep-box 48,62,588,492 \
        --keep-bands "200,80,452,302;75,305,575,395;75,396,585,492"

Tuning order: read the keep/drop log first, then adjust --delta-floor (strokes
disappear), --min-area (texture survives), or the keep regions.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


def parse_box(text: str) -> tuple[int, int, int, int]:
    parts = [int(v.strip()) for v in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"需要 4 个数字 x0,y0,x1,y1：{text}")
    return parts  # type: ignore[return-value]


def parse_bands(text: str) -> tuple[tuple[int, int, int, int], ...]:
    if not text.strip():
        return ()
    return tuple(parse_box(chunk) for chunk in text.split(";") if chunk.strip())


def build_mask(gray: Image.Image, bg_window: int, delta_floor: int, delta_range: int, l_floor: int) -> Image.Image:
    background = gray.filter(ImageFilter.MaxFilter(bg_window))
    delta = ImageChops.subtract(background, gray)
    coverage = delta.point(
        lambda v: 0 if v <= delta_floor else min(255, int((v - delta_floor) * 255 / delta_range))
    )
    dark = gray.point(lambda v: 255 if v < l_floor else 0)
    return ImageChops.multiply(coverage, dark).convert("L")


def clean_components(
    mask: Image.Image,
    keep_box: tuple[int, int, int, int] | None,
    keep_bands: tuple[tuple[int, int, int, int], ...],
    min_area: int,
    log_area: int,
) -> tuple[Image.Image, list[str]]:
    """Keep only sizeable components that sit inside the logo area."""
    w, h = mask.size
    px = mask.load()
    seen = bytearray(w * h)
    keep = Image.new("L", (w, h), 0)
    kpx = keep.load()
    log: list[str] = []

    for sy in range(h):
        for sx in range(w):
            idx = sy * w + sx
            if seen[idx] or px[sx, sy] < 128:
                continue
            stack = [(sx, sy)]
            seen[idx] = 1
            comp: list[tuple[int, int]] = []
            touches = False
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                if cx in (0, w - 1) or cy in (0, h - 1):
                    touches = True
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        nidx = ny * w + nx
                        if not seen[nidx] and px[nx, ny] >= 128:
                            seen[nidx] = 1
                            stack.append((nx, ny))

            xs = [p[0] for p in comp]
            ys = [p[1] for p in comp]
            box = (min(xs), min(ys), max(xs), max(ys))
            area = len(comp)
            inside = True if keep_box is None else (
                box[0] >= keep_box[0] and box[1] >= keep_box[1] and box[2] <= keep_box[2] and box[3] <= keep_box[3]
            )
            if inside and keep_bands:
                inside = any(
                    box[0] >= bx0 and box[1] >= by0 and box[2] <= bx1 and box[3] <= by1
                    for bx0, by0, bx1, by1 in keep_bands
                )

            if area >= min_area and inside and not touches:
                for cx2, cy2 in comp:
                    kpx[cx2, cy2] = 255
                log.append(f"keep  area={area:6d} box={box}")
            elif area >= log_area:
                log.append(f"drop  area={area:6d} box={box} inside={inside} touches={touches}")
    return keep, log


def main() -> None:
    parser = argparse.ArgumentParser(description="从照片中提取 logo（去背景纹理与光晕）")
    parser.add_argument("--src", required=True, help="源照片")
    parser.add_argument("--prefix", required=True, help="输出文件名前缀")
    parser.add_argument("--out-dir", default="output/logo")
    parser.add_argument("--bg-window", type=int, default=35, help="局部背景估计的 MaxFilter 窗口，需为奇数")
    parser.add_argument("--delta-floor", type=int, default=90, help="低于此局部对比度视为背景纹理")
    parser.add_argument("--delta-range", type=int, default=50, help="抗锯齿过渡带宽度")
    parser.add_argument("--l-floor", type=int, default=120, help="笔画亮度上限（越接近黑越安全）")
    parser.add_argument("--binary-threshold", type=int, default=110, help="连通域分析前的二值化阈值")
    parser.add_argument("--min-area", type=int, default=60, help="小于此面积的连通域直接丢弃")
    parser.add_argument("--log-area", type=int, default=200, help="大于此面积的丢弃组件写入日志")
    parser.add_argument("--keep-box", type=parse_box, default=None, help="logo 区域 x0,y0,x1,y1")
    parser.add_argument("--keep-bands", type=parse_bands, default=(), help="按行白名单，多段用分号分隔")
    parser.add_argument("--pad", type=int, default=24, help="输出留白")
    parser.add_argument("--blur", type=float, default=0.7, help="边缘平滑（手机拍摄的像素台阶）")
    args = parser.parse_args()

    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"文件不存在：{src}")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    gray = Image.open(src).convert("RGB").convert("L")
    coverage = build_mask(gray, args.bg_window, args.delta_floor, args.delta_range, args.l_floor)
    binary = coverage.point(lambda v: 255 if v >= args.binary_threshold else 0)
    keep, log = clean_components(binary, args.keep_box, args.keep_bands, args.min_area, args.log_area)
    for line in log:
        print(line)
    if not any(line.startswith("keep") for line in log):
        raise SystemExit("没有保留任何组件：先放松 --delta-floor / --l-floor，或检查 --keep-box 是否写反")

    alpha = ImageChops.multiply(coverage, keep)
    if args.blur > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(args.blur))

    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        raise SystemExit("alpha 为空：确认源图是深色 logo 在浅色背景上")
    box = (
        max(0, bbox[0] - args.pad),
        max(0, bbox[1] - args.pad),
        min(alpha.width, bbox[2] + args.pad),
        min(alpha.height, bbox[3] + args.pad),
    )
    alpha = alpha.crop(box)
    print(f"alpha bbox: {bbox} | cropped: {alpha.size}")

    white_bg = Image.new("RGB", alpha.size, (255, 255, 255))
    white_bg.paste(Image.new("RGB", alpha.size, (0, 0, 0)), (0, 0), alpha)
    white_bg.save(out / f"{args.prefix}-whitebg.png")

    transparent = Image.merge(
        "RGBA",
        (Image.new("L", alpha.size, 0), Image.new("L", alpha.size, 0), Image.new("L", alpha.size, 0), alpha),
    )
    transparent.save(out / f"{args.prefix}-transparent.png")

    print(f"wrote {args.prefix}-whitebg.png and {args.prefix}-transparent.png to {out}")
    print("下一步：确认底稿后用 scripts/logo_variants.py 生成白底/透明/反白/方形全套。")


if __name__ == "__main__":
    main()
