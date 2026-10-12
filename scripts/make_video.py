# -*- coding: utf-8 -*-
"""Render, concatenate and verify a b2b-factory-video project.

Usage:
  python make_video.py project.json              render every segment + assemble
  python make_video.py project.json beat3        re-render one segment only
  python make_video.py project.json --assemble   concatenate + mix audio only
  python make_video.py project.json --check      verify the finished file
"""
import json
import os
import subprocess
import sys

from make_overlays import hex_rgb, layout

VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm")
MID = "@MID@"          # placeholder for the per-segment middle band


def run(cmd, label, quiet=True):
    print("==>", label, flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if res.returncode != 0:
        print(res.stdout[-3000:])
        print(res.stderr[-8000:])
        raise SystemExit("ffmpeg failed: " + label)
    return res


def probe(path, entries="format=duration", stream=None):
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream, "-show_entries",
                "stream=codec_type,codec_name,width,height,r_frame_rate"]
    cmd += ["-show_entries", entries, "-of", "json", path]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return json.loads(out or "{}")


def is_video(p):
    return p.lower().endswith(VIDEO_EXT)


def src_input(shot, dur, fps):
    if is_video(shot["src"]):
        return ["-ss", str(shot.get("ss", 0)), "-t", str(dur), "-i", shot["src"]]
    return ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", shot["src"]]


def still(path, dur, fps):
    return ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", path]


def band(shot, idx, band_h, fps, out):
    xf, yf = shot.get("frac", [0.5, 0.5])
    return ("[%d:v]scale=1080:%d:force_original_aspect_ratio=increase,"
            "crop=1080:%d:(iw-1080)*%s:(ih-%d)*%s,fps=%d,setsar=1[%s]"
            % (idx, band_h, band_h, xf, band_h, yf, fps, out))


class Renderer:
    def __init__(self, proj):
        self.p = proj
        self.W, self.H = proj.get("size", [1080, 1920])
        self.fps = proj.get("fps", 30)
        # make_overlays writes the exact layout it rendered against; always
        # prefer it so the two scripts cannot drift apart
        lay = os.path.join(proj["work_dir"], "overlays", "layout.json")
        if os.path.exists(lay):
            with open(lay, encoding="utf-8") as fh:
                self.L = json.load(fh)
        else:
            self.L = layout((self.W, self.H))
        self.s = self.L["s"]
        self.brand_hex = "0x" + proj["brand"]["color"].lstrip("#").upper()
        self.ov = os.path.join(proj["work_dir"], "overlays")
        self.clips = os.path.join(proj["work_dir"], "clips")
        self.out_dir = proj["out_dir"]
        self.layers = self._layer_plan()
        self.enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-r", str(self.fps), "-an"]

    def _layer_plan(self):
        L, s = self.L, self.s
        plan = [(os.path.join(self.ov, "strip.png"), 0, 0)]
        plan.append((MID, 0, L["mid_y"]))
        plan.append((os.path.join(self.ov, "pill_upper.png"),
                     L["pad"], L["top_y"] + round(26 * s)))
        plan.append((os.path.join(self.ov, "pill_lower.png"),
                     L["pad"], L["bot_y"] + round(26 * s)))
        wm = os.path.join(self.ov, "watermark.png")
        if os.path.exists(wm):
            plan.append((wm, "main_w-overlay_w-%d" % L["pad"],
                         "main_h-overlay_h-%d" % round(46 * s)))
        return plan

    def _mid_for(self, tag):
        return os.path.join(self.ov, "mid_%s.png" % tag)

    def render(self, tag, dur, upper, lower, fade_in=0.0, fade_out=0.0, mid_key=None):
        """Inputs are 0 upper, 1 lower, then every layer in plan order with the
        middle band swapped for the one belonging to this segment."""
        args = []
        args += src_input(upper, dur, self.fps)
        args += src_input(lower, dur, self.fps)
        order = []
        for lp, x, y in self.layers:
            if lp == MID:
                lp = self._mid_for(mid_key or tag)
            order.append((lp, x, y))
            args += still(lp, dur, self.fps)

        f = [band(upper, 0, self.L["top_h"], self.fps, "vup"),
             band(lower, 1, self.L["bot_h"], self.fps, "vlo"),
             "color=c=%s:s=%dx%d:r=%d:d=%s[bg]"
             % (self.brand_hex, self.W, self.H, self.fps, dur)]
        f.append("[bg][vup]overlay=0:%d[s0]" % self.L["top_y"])
        f.append("[s0][vlo]overlay=0:%d[s1]" % self.L["bot_y"])
        last = "s1"
        for i, (_, x, y) in enumerate(order):
            nxt = "s%d" % (i + 2)
            f.append("[%s][%d:v]overlay=x=%s:y=%s:format=auto[%s]"
                     % (last, i + 2, x, y, nxt))
            last = nxt
        tail = ""
        if fade_in:
            tail += "fade=t=in:st=0:d=%s:color=%s," % (fade_in, self.brand_hex)
        if fade_out:
            tail += ("fade=t=out:st=%s:d=%s:color=%s,"
                     % (round(dur - fade_out, 3), fade_out, self.brand_hex))
        f.append("[%s]%sformat=yuv420p[out]" % (last, tail))

        out = os.path.join(self.clips, tag + ".mp4")
        cmd = (["ffmpeg", "-y", "-v", "error", "-hide_banner"] + args +
               ["-filter_complex", ";".join(f), "-map", "[out]", "-t", str(dur)] +
               self.enc + [out])
        run(cmd, tag)

    def segment_plan(self):
        hook = self.p["hook"]
        plan = [("hook", hook["duration"], hook["upper"], hook["lower"], 0.26, 0.30, "hook")]
        for i, b in enumerate(self.p["beats"], 1):
            plan.append(("beat%d" % i, b["duration"], b["upper"], b["lower"],
                         0.20 if i == 1 else 0.0, 0.0, str(i)))
        end = self.p["endcard"]
        plan.append(("end", end["duration"], None, None, 0.45, 0.0, None))
        return plan

    def render_all(self, only=None):
        os.makedirs(self.clips, exist_ok=True)
        for tag, dur, up, lo, fi, fo, mid in self.segment_plan():
            if only and only != tag:
                continue
            if tag == "end":
                self.render_end(dur, fi)
            else:
                self.render(tag, dur, up, lo, fi, fo, mid)

    def render_end(self, dur, fade_in):
        card = os.path.join(self.ov, "endcard.png")
        args = still(card, dur, self.fps)
        f = ("[0:v]fps=%d,setsar=1,fade=t=in:st=0:d=%s:color=%s,"
             "format=yuv420p[out]" % (self.fps, fade_in, self.brand_hex))
        out = os.path.join(self.clips, "end.mp4")
        cmd = (["ffmpeg", "-y", "-v", "error", "-hide_banner"] + args +
               ["-filter_complex", f, "-map", "[out]", "-t", str(dur)] +
               self.enc + [out])
        run(cmd, "end")

    def assemble(self):
        tags = [t for t, *_ in self.segment_plan()]
        total, lines = 0.0, []
        for t in tags:
            path = os.path.join(self.clips, t + ".mp4")
            if not os.path.exists(path):
                raise SystemExit("missing segment: " + path)
            total += float(probe(path).get("format", {}).get("duration", 0))
            lines.append("file '%s'" % path.replace("\\", "/"))
        lst = os.path.join(self.p["work_dir"], "concat_list.txt")
        with open(lst, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        out = os.path.join(self.out_dir, self.p["name"] + ".mp4")
        os.makedirs(self.out_dir, exist_ok=True)
        cmd = (["ffmpeg", "-y", "-v", "error", "-hide_banner",
                "-f", "concat", "-safe", "0", "-i", lst, "-map", "0:v"])
        audio = self.p.get("audio")
        if audio:
            cmd += ["-stream_loop", "-1", "-i", audio["src"]]
            st = round(total - audio.get("fade_out", 1.6), 2)
            af = ("[1:a]lowpass=f=%d,volume=%s,afade=t=in:st=0:d=1.2,"
                  "afade=t=out:st=%s:d=%s[a]"
                  % (audio.get("lowpass", 4200), audio.get("volume", 0.3), st,
                     audio.get("fade_out", 1.6)))
            cmd += ["-filter_complex", af, "-map", "[a]",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest"]
        else:
            cmd += ["-an"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "19",
                "-pix_fmt", "yuv420p", "-r", str(self.fps),
                "-movflags", "+faststart", out]
        run(cmd, "assemble")
        print("duration: %.2fs -> %s" % (total, out))
        return out, total

    def check(self):
        out = os.path.join(self.out_dir, self.p["name"] + ".mp4")
        if not os.path.exists(out):
            raise SystemExit("no finished file: " + out)
        info = probe(out, "format=duration,size")
        streams = probe(out, stream="v")["streams"] + probe(out, stream="a").get("streams", [])
        kinds = [s["codec_type"] for s in streams]
        dur = float(info["format"]["duration"])
        print("file      : %s" % out)
        print("duration  : %.2fs" % dur)
        print("streams   : %s" % ", ".join("%s(%s)" % (s["codec_type"], s.get("codec_name", "")) for s in streams))
        problems = []
        if "video" not in kinds:
            problems.append("no video stream")
        want_audio = bool(self.p.get("audio"))
        if want_audio and "audio" not in kinds:
            problems.append("audio expected but missing")
        if not want_audio and "audio" in kinds:
            problems.append("audio present but project audio is null")

        brand = hex_rgb(self.p["brand"]["color"])
        sheet_dir = self.p["work_dir"]
        for t in (0.2, 1.0, dur * 0.5, max(0.0, dur - 1.5)):
            png = os.path.join(sheet_dir, "check_%.2f.png" % t)
            run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", out,
                 "-frames:v", "1", "-update", "1", png], "frame@%.2fs" % t)
            frac = self._brand_fraction(png, brand)
            print("brand band @%.2fs: %.1f%% of frame" % (t, frac * 100))
            if t <= 1.0 and frac < 0.05:
                problems.append("the middle title band is not visible at %.2fs" % t)
        sheet = os.path.join(sheet_dir, "contact_sheet.jpg")
        run(["ffmpeg", "-y", "-v", "error", "-i", out, "-filter_complex",
             "fps=1,scale=210:-1,tile=6x4", "-frames:v", "1", "-update", "1", sheet],
            "contact sheet")
        cover = os.path.join(self.out_dir, self.p["name"] + "_封面.jpg")
        run(["ffmpeg", "-y", "-v", "error", "-ss", "1.0", "-i", out,
             "-frames:v", "1", "-q:v", "2", cover], "cover")
        print("contact sheet: %s" % sheet)
        print("cover        : %s" % cover)
        if problems:
            print("PROBLEMS: " + "; ".join(problems))
            raise SystemExit(1)
        print("check passed. Look at the contact sheet before delivering.")

    @staticmethod
    def _brand_fraction(png, brand):
        from PIL import Image
        im = Image.open(png).convert("RGB").resize((108, 192))
        px = list(im.getdata())
        hit = sum(1 for r, g, b in px
                  if abs(r - brand[0]) < 36 and abs(g - brand[1]) < 36
                  and abs(b - brand[2]) < 36)
        return hit / float(len(px))


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: make_video.py project.json [segment|--assemble|--check]")
    with open(sys.argv[1], encoding="utf-8") as fh:
        proj = json.load(fh)
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    r = Renderer(proj)
    if arg == "--check":
        r.check()
    elif arg == "--assemble":
        r.assemble()
        r.check()
    elif arg:
        r.render_all(only=arg)
        if arg not in ("hook", "end"):
            print("re-run with --assemble to rebuild the finished file")
    else:
        r.render_all()
        r.assemble()
        r.check()


if __name__ == "__main__":
    main()
