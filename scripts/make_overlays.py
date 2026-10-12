# -*- coding: utf-8 -*-
"""Render every text layer for a b2b-factory-video project.

Usage:  python make_overlays.py project.json

Produces, inside <work_dir>/overlays:
  strip.png        top credential strip
  mid_hook.png     middle band for the hook (brand row + big title + hook line)
  mid_N.png        middle band for beat N (brand row + big title + caption)
  pill_upper.png   OUR FACTORY style label
  pill_lower.png   OUR PRODUCTS style label
  watermark.png    corner wordmark
  endcard.png      full-frame closing card

All copy is drawn with Pillow so brand and claim spelling is exact.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu",
             "/System/Library/Fonts/Supplemental"]
HEAD_CANDIDATES = [("bahnschrift.ttf", "Bold Condensed"), ("ariblk.ttf", None),
                   ("DejaVuSans-Bold.ttf", None), ("Arial Bold.ttf", None)]
BOLD_CANDIDATES = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]
SEMI_CANDIDATES = ["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]

BASE_H = 1920.0
STRIP_F = 0.029167
BASE_MID = 340          # fallback middle-band height at a 1920-tall frame
MID_PAD_V = 26          # vertical padding inside the middle band


def find_font(names):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


class Fonts:
    def __init__(self, override=None, warn=print):
        self.head_path = override or find_font([c[0] for c in HEAD_CANDIDATES])
        self.head_var = None
        if not override:
            for name, var in HEAD_CANDIDATES:
                p = find_font([name])
                if p:
                    self.head_path, self.head_var = p, var
                    break
        self.bold_path = find_font(BOLD_CANDIDATES)
        self.semi_path = find_font(SEMI_CANDIDATES) or self.bold_path
        self.head_var = self._check(self.head_path, self.head_var, warn)
        if not self.head_path or not self.bold_path:
            raise SystemExit("no usable font found; pass brand.font_headline")
        warn("fonts: headline=%s(%s) bold=%s semi=%s"
             % (self.head_path, self.head_var, self.bold_path, self.semi_path))

    @staticmethod
    def _check(path, var, warn):
        if not path or not var:
            return None
        try:
            ImageFont.truetype(path, 40).set_variation_by_name(var)
            return var
        except Exception:
            warn("variable instance %r unavailable, using default" % var)
            return None

    def head(self, size):
        return _load(self.head_path, size, self.head_var)

    def bold(self, size):
        return _load(self.bold_path, size)

    def semi(self, size):
        return _load(self.semi_path, size)


def _load(path, size, variation=None):
    f = ImageFont.truetype(path, max(8, int(size)))
    if variation:
        try:
            f.set_variation_by_name(variation)
        except Exception:
            pass
    return f


def hex_rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def tw(d, text, font, ls=0):
    if not text:
        return 0.0
    return d.textlength(text, font=font) + ls * (len(text) - 1)


def vbox(d, text, font):
    b = d.textbbox((0, 0), text, font=font)
    return b[1], b[3] - b[1]


def draw_ls(d, xy, text, font, fill, ls=0, anchor_x="left"):
    x, y = xy
    if anchor_x != "left":
        w = tw(d, text, font, ls)
        x = x - w if anchor_x == "right" else x - w / 2.0
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + ls


def fit(d, text, maker, max_w, max_size, min_size=12):
    size = int(max_size)
    while size > min_size:
        f = maker(size)
        if d.textlength(text, font=f) <= max_w:
            return f, size
        size -= 1
    return maker(min_size), min_size


def wordmark(path, target_w, mode="white-wordmark"):
    src = Image.open(path).convert("RGBA")
    if mode == "as-is":
        mark = src.crop(src.getbbox())
    else:
        rgb = Image.new("RGB", src.size, (255, 255, 255))
        rgb.paste(src, (0, 0), src)
        px = rgb.load()
        w, h = rgb.size
        minx, miny, maxx, maxy = w, h, 0, 0
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                r, g, b = px[x, y]
                if r > 200 and g > 200 and b > 200:
                    minx, miny = min(minx, x), min(miny, y)
                    maxx, maxy = max(maxx, x), max(maxy, y)
        if maxx <= minx or maxy <= miny:
            raise SystemExit("could not locate a white wordmark in " + path)
        pad = 16
        grey = rgb.crop((max(0, minx - pad), max(0, miny - pad),
                         min(w, maxx + pad), min(h, maxy + pad))).convert("L")
        alpha = grey.point(lambda v: 0 if v < 90 else min(255, int((v - 90) * 4.2)))
        mark = Image.new("RGBA", grey.size, (255, 255, 255, 0))
        mark.putalpha(alpha)
        mark = mark.crop(mark.getbbox())
    if target_w:
        ratio = target_w / mark.width
        mark = mark.resize((int(target_w), max(1, round(mark.height * ratio))),
                           Image.LANCZOS)
    return mark


def layout(size, mid_px=None):
    """Zones: credential strip, factory band, middle band, product band.

    The middle band is content-height driven (1-line and 2-line titles need
    very different heights), and whatever is left is split evenly between the
    two screens.
    """
    W, H = size
    s = H / BASE_H
    strip_h = round(56 * s)
    mid_h = int(round(mid_px)) if mid_px else round(BASE_MID * s)
    rest = max(0, H - strip_h - mid_h)
    top_h = rest // 2
    bot_h = rest - top_h
    top_y = strip_h
    mid_y = top_y + top_h
    bot_y = mid_y + mid_h
    return dict(W=W, H=H, s=s, strip_h=strip_h, top_y=top_y, top_h=top_h,
                mid_y=mid_y, mid_h=mid_h, bot_y=bot_y, bot_h=bot_h,
                pad=round(56 * s), pill_h=round(54 * s), pill_r=round(11 * s))


def mid_metrics(L, F, brand, caption):
    """Everything the middle band needs, computed once so the band height and
    its rendering always agree."""
    W, s, pad = L["W"], L["s"], L["pad"]
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines = brand["title_lines"]
    f_brand = F.bold(round(25 * s))
    f_title, s_title = fit(d, max(lines, key=len), F.head, W - 2 * pad,
                           round(88 * s), round(30 * s))
    f_cap, _ = fit(d, caption, F.semi, W - 2 * pad, round(30 * s), round(13 * s))
    lh = int(s_title * 1.10)
    heights = [vbox(d, t, f_title)[1] for t in lines]
    b_off, b_h = vbox(d, brand["name"], f_brand)
    c_off, c_h = vbox(d, caption, f_cap)
    gap_a, gap_b = round(26 * s), round(22 * s)
    content = (b_h + gap_a + sum(heights) + lh * (len(lines) - 1)
               + gap_b + c_h)
    return dict(d=d, f_brand=f_brand, f_title=f_title, f_cap=f_cap,
                s_title=s_title, lh=lh, heights=heights, b_off=b_off, b_h=b_h,
                c_off=c_off, c_h=c_h, gap_a=gap_a, gap_b=gap_b,
                content=content, pad_v=round(MID_PAD_V * s), lines=lines)


def mid_band_px(L, F, brand, caption):
    m = mid_metrics(L, F, brand, caption)
    return m["content"] + 2 * m["pad_v"]


def build_mid(L, F, brand, caption, colors, caption_color):
    W, mid_h, s = L["W"], L["mid_h"], L["s"]
    BRAND, BRIGHT = colors[0], colors[1]
    WHITE = (255, 255, 255)
    m = mid_metrics(L, F, brand, caption)
    d = m["d"]
    band = Image.new("RGBA", (W, mid_h), BRAND + (255,))
    d = ImageDraw.Draw(band)
    d.rectangle([0, 0, W, max(2, round(4 * s))], fill=BRIGHT)
    d.rectangle([0, mid_h - max(2, round(4 * s)), W, mid_h], fill=BRIGHT)

    pad = L["pad"]
    f_brand, f_title, f_cap = m["f_brand"], m["f_title"], m["f_cap"]
    lines, lh, heights = m["lines"], m["lh"], m["heights"]
    y = (mid_h - m["content"]) // 2
    draw_ls(d, (pad, y - m["b_off"]), brand["name"], f_brand, WHITE,
            ls=max(1, round(5 * s)))
    label = brand.get("right_label")
    if label:
        draw_ls(d, (W - pad, y - m["b_off"] + 2), label, F.semi(round(22 * s)), colors[3],
                ls=max(1, round(2 * s)), anchor_x="right")
    y += m["b_h"] + m["gap_a"]
    for i, t in enumerate(lines):
        off, h = vbox(d, t, f_title)
        draw_ls(d, (W / 2, y - off), t, f_title, WHITE, ls=max(1, round(2 * s)),
                anchor_x="center")
        y += lh if i < len(lines) - 1 else h
    y += m["gap_b"]
    draw_ls(d, (W / 2, y - m["c_off"]), caption, f_cap, caption_color,
            ls=max(1, round(2 * s)), anchor_x="center")
    return band


def build_endcard(L, F, brand, end, colors, cream):
    W, H, s, pad = L["W"], L["H"], L["s"], L["pad"]
    BRAND, BRIGHT = colors[0], colors[1]
    WHITE = (255, 255, 255)
    card = Image.new("RGBA", (W, H), BRAND + (255,))
    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, W, max(4, round(14 * s))], fill=BRIGHT)
    d.rectangle([0, H - max(4, round(14 * s)), W, H], fill=BRIGHT)

    y = round(300 * s)
    if brand.get("logo"):
        mark = wordmark(brand["logo"], round(620 * s), brand.get("logo_mode", "white-wordmark"))
        card.paste(mark, ((W - mark.width) // 2, y), mark)
        y += mark.height + round(46 * s)
    company = end.get("company") or brand["name"]
    f_co, _ = fit(d, company, F.semi, W - 2 * pad, round(25 * s), round(12 * s))
    o, _ = vbox(d, company, f_co)
    draw_ls(d, (W / 2, y - o), company, f_co, colors[3], ls=2, anchor_x="center")

    y = round(706 * s)
    d.line([(W * 0.16, y), (W * 0.84, y)], fill=BRIGHT, width=max(2, round(3 * s)))
    y = round(756 * s)
    f_a = F.bold(round(50 * s))
    o, hA = vbox(d, "WELCOME TO", f_a)
    draw_ls(d, (W / 2, y - o), "WELCOME TO", f_a, colors[3], ls=round(8 * s),
            anchor_x="center")
    y += hA + round(18 * s)
    f_b, _ = fit(d, end["headline"], F.head, W - 2 * pad, round(96 * s), round(40 * s))
    o, hB = vbox(d, end["headline"], f_b)
    draw_ls(d, (W / 2, y - o), end["headline"], f_b, WHITE, ls=2, anchor_x="center")
    y += hB + round(64 * s)

    pillars = end.get("pillars") or []
    if pillars:
        f_p, _ = fit(d, max(pillars, key=len), F.semi, W - 2 * pad,
                     round(30 * s), round(13 * s))
        for ln in pillars:
            o, hF = vbox(d, ln, f_p)
            draw_ls(d, (W / 2, y - o), ln, f_p, colors[3], ls=round(3 * s),
                    anchor_x="center")
            y += hF + round(30 * s)
        y += round(46 * s)

    if end.get("cta"):
        f_c, _ = fit(d, end["cta"], F.bold, W - round(220 * s), round(38 * s),
                     round(18 * s))
        cw = tw(d, end["cta"], f_c, 2)
        o, hC = vbox(d, end["cta"], f_c)
        d.rounded_rectangle([(W - cw) / 2 - round(48 * s), y - round(30 * s),
                             (W + cw) / 2 + round(48 * s), y + hC + round(30 * s)],
                            radius=round(54 * s), fill=cream + (255,))
        draw_ls(d, (W / 2, y - o), end["cta"], f_c, (16, 56, 41), ls=2,
                anchor_x="center")
        y += hC + round(92 * s)

    if end.get("products"):
        f_pr, _ = fit(d, end["products"], F.semi, W - 2 * pad, round(27 * s),
                      round(13 * s))
        o, _ = vbox(d, end["products"], f_pr)
        draw_ls(d, (W / 2, y - o), end["products"], f_pr, colors[3], ls=1,
                anchor_x="center")

    if end.get("footer"):
        f_ft = F.semi(round(22 * s))
        o, _ = vbox(d, end["footer"], f_ft)
        draw_ls(d, (W / 2, H - round(130 * s) - o), end["footer"], f_ft,
                colors[4], ls=round(4 * s), anchor_x="center")
    return card


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: make_overlays.py project.json")
    with open(sys.argv[1], encoding="utf-8") as fh:
        proj = json.load(fh)

    W, H = proj.get("size", [1080, 1920])
    if W != 1080:
        raise SystemExit("only 1080-wide frames are supported; scale afterwards")
    ov = os.path.join(proj["work_dir"], "overlays")
    os.makedirs(ov, exist_ok=True)

    brand = proj["brand"]
    probe = layout((W, H))
    F = Fonts(brand.get("font_headline"))
    states = [proj["hook"]["caption"]] + [b["caption"] for b in proj["beats"]]
    if proj.get("mid_height"):
        mid_px = int(proj["mid_height"])
    else:
        mid_px = max(mid_band_px(probe, F, brand, c) for c in states)
    L = layout((W, H), mid_px)
    s = L["s"]

    BRAND = hex_rgb(brand["color"])
    BRIGHT = tuple(min(255, int(c * 1.35 + 22)) for c in BRAND)
    WHITE = (255, 255, 255)
    MINT = tuple(int(c + (255 - c) * 0.72) for c in BRAND)
    FOOT = tuple(int(c + (255 - c) * 0.52) for c in BRAND)
    CREAM = (246, 243, 236)
    colors = (BRAND, BRIGHT, WHITE, MINT, FOOT)
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    with open(os.path.join(ov, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(L, fh, ensure_ascii=False, indent=2)
    print("layout: mid=%dpx top=%dpx bottom=%dpx (title lines: %d)"
          % (L["mid_h"], L["top_h"], L["bot_h"], len(brand["title_lines"])))

    strip = Image.new("RGBA", (W, L["strip_h"]), BRAND + (255,))
    sd = ImageDraw.Draw(strip)
    txt = proj.get("strip", "")
    if txt:
        f, _ = fit(sd, txt, F.semi, W - 2 * L["pad"], round(21 * s), round(11 * s))
        o, h = vbox(sd, txt, f)
        draw_ls(sd, (W / 2, (L["strip_h"] - h) // 2 - o), txt, f, MINT, ls=1,
                anchor_x="center")
    strip.save(os.path.join(ov, "strip.png"))

    hook = proj["hook"]
    build_mid(L, F, brand, hook["caption"], colors, MINT).save(
        os.path.join(ov, "mid_hook.png"))
    for i, beat in enumerate(proj["beats"], 1):
        build_mid(L, F, brand, beat["caption"], colors, CREAM).save(
            os.path.join(ov, "mid_%d.png" % i))

    for name, label in (("pill_upper", proj.get("pill_upper", "OUR FACTORY")),
                        ("pill_lower", proj.get("pill_lower", "OUR PRODUCTS"))):
        f = F.bold(round(26 * s))
        lw = tw(d, label, f, round(3 * s))
        img = Image.new("RGBA", (int(lw + 46 * s), L["pill_h"]), (0, 0, 0, 0))
        dd = ImageDraw.Draw(img)
        dd.rounded_rectangle([0, 0, img.width - 1, img.height - 1],
                             radius=L["pill_r"], fill=BRAND + (236,))
        o, _ = vbox(dd, label, f)
        draw_ls(dd, (round(23 * s), (L["pill_h"] - round(20 * s)) / 2 - o),
                label, f, WHITE, ls=round(3 * s))
        img.save(os.path.join(ov, name + ".png"))

    if brand.get("logo"):
        mark = wordmark(brand["logo"], round(300 * s),
                        brand.get("logo_mode", "white-wordmark"))
        mark.save(os.path.join(ov, "logo_white.png"))
        wm = Image.new("RGBA", (mark.width + 8, mark.height + 8), (0, 0, 0, 0))
        wm.paste(mark, (4, 4), mark)
        wm.putalpha(wm.getchannel("A").point(lambda v: int(v * 0.75)))
        wm.save(os.path.join(ov, "watermark.png"))

    end = proj["endcard"]
    build_endcard(L, F, brand, end, colors, CREAM).convert("RGB").save(
        os.path.join(ov, "endcard.png"))
    print("overlays written to " + ov)


if __name__ == "__main__":
    main()
