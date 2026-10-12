# 工厂获客视频：版面契约与实现细节

配合 [factory-video.md](factory-video.md) 使用：那份写流程和硬约束，这份写尺寸/字号契约、project.json 字段、ffmpeg 表达式与验收清单。

## 一、四层结构

除顶部资质细条外，其余三块的高度都按画布高度的比例算，所以同一套配置能出 9:16 / 1:1 / 4:5。基准是 1080×1920。

| 区块 | 占高比例 | 1080×1920 | 1080×1080 | 内容 |
| --- | --- | --- | --- | --- |
| 资质细条 | 0.0292 | 56px | 32px | `100+ PRODUCTION LINES · 60,000 m² WORKSHOP · ISO 9001 / ISO 14001 / SGS`，居中，浅绿字 |
| 上屏 | 0.3958 | 760px | 428px | 工厂 / 产线 |
| 中缝 | 0.1771 | 340px | 191px | 品牌名行 + 大标题（1–2 行）+ 每段字幕行 |
| 下屏 | 余量 | 764px | 429px | 成品 / 款式 |

字号统一按 `scale = 画布高 / 1920` 缩放，宽度按 1080 固定。中缝三行垂直居中排布，行距 `字号 × 1.10`，行间 26px / 22px。

其他固定元素：

- 上屏左上 `OUR FACTORY`、下屏左上 `OUR PRODUCTS` 圆角标签（高 54px，圆角 11px，内边距 23px）
- 右下角品牌水印（宽 300px，75% 不透明）
- 每屏左右留白 56px

## 二、字号与排版规则

**大标题优先用窄体工业无衬线。** Windows 上 `bahnschrift.ttf` 的 `Bold Condensed` 实例是很接近 DIN 的窄体，比 Arial Black 更像外贸工厂片；用 Pillow 的 `set_variation_by_name("Bold Condensed")` 取实例。字体缺失时按 `Bahnschrift → Arial Black → DejaVu Sans Bold` 回退，并告知用户实际用了哪个。

所有文字都必须**自动缩放到框内**：从上限字号逐像素递减，直到 `textlength` 合适。不要写死字号——客户换一句更长的卖点就会溢出。

排版实现要点：

- 用 `textbbox((0,0), ...)` 取视觉 bbox，把**可见顶部**对齐到目标 y，不要直接按基线猜位置（不同字体的 ascent 差异会让两行标题叠在一起）
- 字间距用逐字符绘制实现（Pillow 没有 letter-spacing），并把字间距计入宽度
- 中缝字幕单行优先；一行放不下再按"两行长度差最小"切分，不要贪心填满第一行
- 大标题两行时，第二行可以比第一行短很多（`CHINA WPC WALL PANEL` / `SUPPLIER`），层级反而更清楚

## 三、色彩

```python
# 从客户 logo 取样，不要凭感觉定
from PIL import Image
bg = Image.open("logo.jpg").convert("RGB").getpixel((30, 30))   # -> (27, 89, 66)
```

配色只有四个：品牌主色、主色亮一档（用于中缝上下 4px 分隔线和结尾卡上下边）、米白（CTA 底色）、浅绿（次要文字）。深色底上不要用纯白大面积正文，次要信息用主色的浅色版。

水印与结尾卡 logo：若客户只给了"色底 + 白字"的方图，用亮度阈值反相抠出白色字标当 alpha 通道即可，**不要重画 logo**：

```python
grey = src.crop(bbox).convert("L")
alpha = grey.point(lambda v: 0 if v < 90 else min(255, int((v - 90) * 4.2)))
```

## 四、project.json

```jsonc
{
  "size": [1080, 1920],            // 9:16；1:1 用 [1080, 1080]
  "fps": 30,
  "work_dir": "…/工作文件",
  "out_dir": "…/交付文件",
  "name": "Client_Product_China_Supplier_9x16",

  "brand": {
    "name": "FANCY DEKOR",
    "color": "#1B5942",
    "logo": "D:/…/Fancy Dekor icon.jpg",
    "logo_mode": "white-wordmark",   // 或 "as-is"（已经是透明 PNG）
    "title_lines": ["CHINA WPC WALL PANEL", "SUPPLIER"],
    "right_label": "FACTORY DIRECT  ·  OEM & ODM",
    "font_headline": null            // 可选：指定 .ttf / .otf
  },

  "strip": "100+ PRODUCTION LINES  ·  60,000 m² WORKSHOP  ·  ISO 9001 / ISO 14001 / SGS",

  "hook": {
    "duration": 3.2,
    "caption": "FACTORY DIRECT  ·  OEM & ODM  ·  SINCE 2007",
    "upper": {"src": "D:/…/车间1.jpg", "frac": [0.5, 0.34]},
    "lower": {"src": "D:/…/工厂大门.png", "frac": [0.5, 0.5]}
  },

  "beats": [
    {
      "duration": 3.0,
      "caption": "IN-HOUSE LAMINATION LINE · 100+ PRODUCTION LINES",
      "upper": {"src": "D:/…/产线.mp4", "ss": 0.2, "frac": [0.5, 0.30]},
      "lower": {"src": "D:/…/成品堆.jpg", "frac": [0.5, 0.42]}
    }
  ],

  "endcard": {
    "duration": 3.6,
    "headline": "VISIT OUR FACTORY",
    "company": "LEHEJU (HUBEI) NEW DECORATION MATERIAL CO., LTD",
    "pillars": ["OWN FACTORY  ·  60,000 m² PLANT  ·  100+ EXTRUSION LINES",
                "OEM & ODM  ·  YOUR BRAND, COLORS & PACKING",
                "FACTORY PRICING  ·  DIRECT SUPPLY, NO MIDDLEMEN"],
    "cta": "SEND US A MESSAGE   →   GET A QUOTE",
    "footer": "FANCY DEKOR  ·  LX",
    "products": "WPC WALL PANEL · FLUTED WALL PANEL · PVC SKIRTING BOARD · PROFILES"
  },

  "audio": null
  // 需要现场环境音或 BGM 时：
  // "audio": {"src": "D:/…/车间.mp4", "volume": 0.30, "lowpass": 4200, "fade_out": 1.6}
}
```

`frac` 是取景锚点：`[0.5, 0.5]` 居中裁切；`[0.5, 0.30]` 表示纵向取靠上的区域（看到机器和人），`[0.5, 0.45]` 用于竖屏素材塞进横向画面时避开地面。

## 五、ffmpeg 实现与踩坑

每段的画面链只有三步，**没有缩放动画**：

```
scale=1080:H:force_original_aspect_ratio=increase,crop=1080:H:(iw-1080)*XF:(ih-H)*YF,fps=30,setsar=1
```

再用 `color` 生成画布，按上屏 → 下屏 → 标签 → 细条 → 中缝 → 水印的顺序 `overlay`。照片输入统一加 `-loop 1 -framerate 30 -t <秒>`，视频输入用 `-ss <秒> -t <秒>`。

实际踩过的坑：

1. **filtergraph 输入序号写错**：叠加层多的时候最容易错。数一遍 `-i` 的顺序再写 `[N:v]`，标签层没加就整段报 `Invalid file index`。
2. **表达式的逗号必须转义**：`clip((t-0.10)/0.34\,0\,1)`。不过既然静帧不动，正常用不到 `t` 表达式——需要的时候优先用 `fade` / `overlay enable` 这类现成参数。
3. **Windows 中文路径 + PowerShell 脚本**：`.ps1` 默认按 ANSI 读取无 BOM 的 UTF-8 文件，中文路径会变乱码，而且 `${VAR}:` 这类写法会被当成驱动器限定符。**直接用 Python 调 ffmpeg**，不要再包一层 PowerShell。
4. **拼接前每段的编码参数必须完全一致**（分辨率、帧率、像素格式、preset、CRF），否则 concat demuxer 会出问题。
5. **逐段渲染完再拼接**，不要把所有素材塞进一个 filter_complex；出错时定位成本差一个数量级。
6. 需要静音就输出加 `-an`；需要环境音就 `-stream_loop -1` 拉长素材音频再 `lowpass + volume + afade`，音量压到均值 −25dB 上下，别盖过人声。

## 六、验收清单

- [ ] 分辨率、帧率、时长符合预期（`ffprobe`）
- [ ] 有/无音轨符合本次要求
- [ ] 第 0.2s 与第 1.0s 的画面里，大标题已经完整可读
- [ ] 抽帧总览图逐格看过：没有黑帧、没有裁到头、没有字幕压住主体
- [ ] 静帧素材确实没有位移（对比同一段的首帧与末帧）
- [ ] 所有公司名、品牌名、数字与客户资料一致
- [ ] 结尾卡 CTA 与客户实际承接方式一致（私信 / 表单 / WhatsApp）
