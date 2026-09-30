# -*- coding: utf-8 -*-
"""
Solid-colour + white-text Facebook poster builder.

Deterministic typography on a flat brand-colour field: no photo, no AI, so the
copy can never be misspelled or garbled. Renders the three placement ratios:

    9x16   1080x1920   Stories / Reels / Reels Overlay
    1x1    1080x1080   Feed / Profile Feed / Search / Notification
    1.91x1 1200x628    In-stream / landscape

Anatomy, mirroring the reference style:

    optional letter-spaced brand line
    serif display headline (white)
    optional sans body paragraph
    bullet list

The landscape version centres the headline and the bullet block; the portrait
and square versions are left aligned.
"""

import argparse
import os
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

SERIF_BOLD = ("Bodoni Bd BT Bold.ttf", "georgiab.ttf", "timesbd.ttf", "cambriab.ttf")
SANS_LIGHT = ("segoeuil.ttf", "segoeui.ttf", "arial.ttf")
SANS_SEMI = ("segoeuisl.ttf", "segoeui.ttf", "arial.ttf")

# ratio -> (width, height, headline size as a fraction of the width, text scale)
RATIOS = {
    "9x16": (1080, 1920, 0.072, 1.18),
    "1x1": (1080, 1080, 0.080, 1.0),
    "1.91x1": (1200, 628, 0.072, 1.0),
}
TOP_BIAS = 0.28

WHITE = (255, 255, 255)
BULLET = "\u2022  "


def hex_rgb(value):
    v = value.strip().lstrip("#")
    if len(v) != 6:
        raise SystemExit("--bg needs a 6 digit hex colour, got %r" % value)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def load_font(candidates, size):
    for name in candidates:
        path = name if os.path.isabs(name) else os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise RuntimeError("no usable font found among %s" % (candidates,))


def text_w(draw, text, font, tracking=0):
    if not text:
        return 0
    if not tracking:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]
    total = 0
    for ch in text:
        box = draw.textbbox((0, 0), ch, font=font)
        total += (box[2] - box[0]) + tracking
    return total - tracking


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if text_w(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_tracked(draw, xy, text, font, fill, tracking, align, max_w):
    width = text_w(draw, text, font, tracking)
    x, y = xy
    if align == "center":
        x += (max_w - width) / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        box = draw.textbbox((0, 0), ch, font=font)
        x += (box[2] - box[0]) + tracking


def measure(draw, sizes, content_w, brand, title, body, bullets):
    t_size, s_size, bl_size, k_size = sizes
    serif = load_font(SERIF_BOLD, int(round(t_size)))
    sans = load_font(SANS_LIGHT, int(round(s_size)))
    sans_b = load_font(SANS_LIGHT, int(round(bl_size)))
    kicker = load_font(SANS_SEMI, int(round(k_size)))

    t_lines = wrap(draw, title, serif, content_w)
    t_gap = t_size * 1.28

    b_lines = wrap(draw, body, sans, content_w) if body else []
    b_gap = s_size * 1.42

    marker_w = text_w(draw, BULLET, sans_b)
    bl_lines = []
    for item in bullets:
        chunks = wrap(draw, item, sans_b, content_w - marker_w)
        for i, chunk in enumerate(chunks):
            bl_lines.append((BULLET if i == 0 else " " * len(BULLET), chunk))
    bl_gap = bl_size * 1.38

    gaps = {
        "kicker": k_size * 1.05 if brand else 0.0,
        "kicker_to_title": k_size * 1.9 if brand else 0.0,
        "title_to_body": s_size * 1.9 if b_lines else 0.0,
        "body_to_bullets": bl_size * 1.8 if bl_lines else 0.0,
    }
    total = (gaps["kicker"] + gaps["kicker_to_title"] + t_gap * len(t_lines)
             + gaps["title_to_body"] + b_gap * len(b_lines)
             + gaps["body_to_bullets"] + bl_gap * len(bl_lines))
    return {
        "serif": serif, "sans": sans, "sans_b": sans_b, "kicker": kicker,
        "t_lines": t_lines, "t_gap": t_gap,
        "b_lines": b_lines, "b_gap": b_gap,
        "bl_lines": bl_lines, "bl_gap": bl_gap,
        "marker_w": marker_w, "gaps": gaps, "total": total,
    }


def build(w, h, bg, brand, title, body, bullets, footer, out,
          title_scale=0.080, text_scale=1.0):
    canvas = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(canvas)

    mx = int(round(w * 0.105))
    my = int(round(h * 0.075))
    content_w = w - 2 * mx
    avail_h = h - 2 * my
    align = "center" if (w / float(h)) > 1.2 else "left"

    sizes = [w * title_scale, w * 0.0362 * text_scale, w * 0.0362 * text_scale,
             w * 0.0185 * text_scale]
    floor = w * 0.030
    m = measure(d, sizes, content_w, brand, title, body, bullets)
    while m["total"] > avail_h and sizes[0] > floor:
        sizes = [s * 0.985 for s in sizes]
        m = measure(d, sizes, content_w, brand, title, body, bullets)
    sizes = [int(round(s)) for s in sizes]
    m = measure(d, sizes, content_w, brand, title, body, bullets)

    slack = max(0.0, avail_h - m["total"])
    y = my + slack * TOP_BIAS
    x0 = mx

    if brand:
        draw_tracked(d, (x0, y), brand, m["kicker"], WHITE, sizes[3] * 0.5,
                     align, content_w)
        y += m["gaps"]["kicker"] + m["gaps"]["kicker_to_title"]

    for line in m["t_lines"]:
        lw = text_w(d, line, m["serif"])
        lx = x0 + ((content_w - lw) / 2.0 if align == "center" else 0)
        d.text((lx, y), line, font=m["serif"], fill=WHITE)
        y += m["t_gap"]
    y += m["gaps"]["title_to_body"]

    for line in m["b_lines"]:
        lw = text_w(d, line, m["sans"])
        lx = x0 + ((content_w - lw) / 2.0 if align == "center" else 0)
        d.text((lx, y), line, font=m["sans"], fill=WHITE)
        y += m["b_gap"]
    y += m["gaps"]["body_to_bullets"]

    if m["bl_lines"]:
        block_w = max(text_w(d, mk + tx, m["sans_b"]) for mk, tx in m["bl_lines"])
        bx = x0 + ((content_w - block_w) / 2.0 if align == "center" else 0)
        for mk, tx in m["bl_lines"]:
            d.text((bx, y), mk, font=m["sans_b"], fill=WHITE)
            d.text((bx + m["marker_w"], y), tx, font=m["sans_b"], fill=WHITE)
            y += m["bl_gap"]

    if footer:
        fs = int(round(sizes[2] * 0.7))
        f = load_font(SANS_SEMI, fs)
        draw_tracked(d, (mx, h - my - fs * 1.5), footer, f, WHITE, fs * 0.3,
                     align, content_w)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    canvas.save(out)
    return out, (w, h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", default="9x16,1x1,1.91x1",
                    help="comma separated, any of: %s" % ", ".join(sorted(RATIOS)))
    ap.add_argument("--size", default=None, help="override one size, e.g. 1080x1080")
    ap.add_argument("--bg", default="1B5942", help="solid background hex colour")
    ap.add_argument("--brand", default="", help="small letter-spaced line at the top")
    ap.add_argument("--title", required=True, help="serif display headline")
    ap.add_argument("--body", default="", help="sans paragraph under the headline")
    ap.add_argument("--bullets", default="", help="semicolon separated bullet lines")
    ap.add_argument("--footer", default="", help="small line pinned to the bottom")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()

    bullets = [b.strip() for b in args.bullets.split(";") if b.strip()]
    bg = hex_rgb(args.bg)

    if args.size:
        parts = args.size.lower().split("x")
        targets = [("custom", (int(parts[0]), int(parts[1]), 0.080, 1.0))]
    else:
        targets = []
        for key in [r.strip() for r in args.ratio.split(",") if r.strip()]:
            if key not in RATIOS:
                raise SystemExit("unknown ratio %r, expected one of %s"
                                 % (key, ", ".join(sorted(RATIOS))))
            targets.append((key, RATIOS[key]))

    for key, (w, h, title_scale, text_scale) in targets:
        out = os.path.join(args.out_dir, "%s-%s.png" % (args.prefix, key))
        path, size = build(w, h, bg, args.brand, args.title, args.body,
                           bullets, args.footer, out, title_scale=title_scale,
                           text_scale=text_scale)
        print("%-8s %dx%d  %s" % (key, size[0], size[1], path))


if __name__ == "__main__":
    main()
