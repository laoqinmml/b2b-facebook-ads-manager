# -*- coding: utf-8 -*-
"""Inventory a factory/product material folder before designing the video.

Usage:
  python inspect_materials.py "D:\\素材文件夹" --out "素材清单.md" --contact-sheet

Prints per-folder image/video counts, lists every clip with duration and
resolution, and optionally writes one contact sheet per clip so the framing can
be judged without opening every file.
"""
import argparse
import json
import os
import subprocess

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic")
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".wmv", ".flv")


def probe(path):
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,width,height,r_frame_rate",
           "-show_entries", "format=duration", "-of", "json", path]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        data = json.loads(out or "{}")
    except json.JSONDecodeError:
        return None
    v = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), None)
    if not v:
        return None
    return dict(w=int(v.get("width", 0)), h=int(v.get("height", 0)),
                fps=v.get("r_frame_rate", "?"),
                dur=float(data.get("format", {}).get("duration", 0) or 0),
                audio=any(s["codec_type"] == "audio" for s in data.get("streams", [])))


def shot_hint(info):
    if not info:
        return "unreadable"
    if info["w"] > info["h"]:
        shape = "横屏"
    elif info["w"] < info["h"]:
        shape = "竖屏"
    else:
        shape = "方版"
    return "%s %dx%d %gfp %.1fs%s" % (shape, info["w"], info["h"], fps_value(info["fps"]),
                                      info["dur"], " +音频" if info["audio"] else "")


def fps_value(raw):
    try:
        if "/" in raw:
            num, den = raw.split("/")
            return round(float(num) / float(den), 2)
        return round(float(raw), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


def contact_sheet(path, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-filter_complex",
                    "fps=1/2,scale=300:-1,tile=5x4", "-frames:v", "1",
                    "-update", "1", out], capture_output=True)
    return os.path.exists(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default=None, help="markdown inventory path")
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--sheet-dir", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.folder)
    sheet_dir = args.sheet_dir or os.path.join(root, "_contact_sheets")
    lines = ["# 素材盘点：%s" % root, ""]
    totals = {IMAGE_EXT: 0, VIDEO_EXT: 0}
    groups = {}
    for dirpath, _, files in os.walk(root):
        if os.path.basename(dirpath).startswith("_"):
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            bucket = "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else None
            if not bucket:
                continue
            rel = os.path.relpath(dirpath, root)
            groups.setdefault(rel, {"image": [], "video": []})[bucket].append(
                os.path.join(dirpath, f))
            totals.setdefault(bucket, 0)
            totals[bucket] = totals.get(bucket, 0) + 1

    lines.append("| 文件夹 | 图片 | 视频 |")
    lines.append("| --- | --- | --- |")
    for rel in sorted(groups):
        g = groups[rel]
        lines.append("| %s | %d | %d |" % (rel or ".", len(g["image"]), len(g["video"])))
    lines.append("| **合计** | **%d** | **%d** |"
                 % (sum(len(g["image"]) for g in groups.values()),
                    sum(len(g["video"]) for g in groups.values())))
    lines.append("")

    shape_count = {"横屏": 0, "竖屏": 0, "方版": 0}
    infos = {}
    lines.append("## 视频清单")
    lines.append("")
    lines.append("| 文件 | 规格 |")
    lines.append("| --- | --- |")
    for rel in sorted(groups):
        for v in sorted(groups[rel]["video"]):
            info = probe(v)
            hint = shot_hint(info)
            infos[v] = info
            if info:
                shape_count[hint.split()[0]] += 1
            lines.append("| %s | %s |" % (os.path.relpath(v, root), hint))
    lines.append("")

    if args.contact_sheet:
        os.makedirs(sheet_dir, exist_ok=True)
        made = 0
        for rel in sorted(groups):
            for i, v in enumerate(sorted(groups[rel]["video"]), 1):
                safe = "".join(c if c.isalnum() else "_" for c in os.path.relpath(v, root))
                out = os.path.join(sheet_dir, safe[:70] + ".jpg")
                if contact_sheet(v, out):
                    made += 1
        lines.append("抽帧九宫格：`%s`（%d 张）" % (sheet_dir, made))
        lines.append("")

    total_v = totals.get("video", 0)
    lines.append("## 判断要点")
    lines.append("")
    lines.append("- 横屏 %d 条 / 竖屏 %d 条 / 方版 %d 条。竖屏素材不足时，9:16 成片只能靠横屏裁切或静图撑；"
                 "竖屏素材塞进横向分屏会被极度放大，慎用。"
                 % (shape_count["横屏"], shape_count["竖屏"], shape_count["方版"]))
    lines.append("- 视频 %d 条里哪几条是真实生产过程，需要人眼看抽帧确认；清单只能给出时长和画幅。"
                 % total_v)
    lines.append("- 静图可以直接铺满分屏，不需要动态素材；这也是上下分屏结构对照片素材友好的原因。")

    text = "\n".join(lines)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("written: " + args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
