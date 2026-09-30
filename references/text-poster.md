# 纯色文字海报（Solid-Colour Text Poster）

整张图只有一个纯色底和纯白文字，没有照片。常见的身份声明、卖点清单、"China XXX Manufacturer" 这类文字海报都属于这一型。

## 为什么走脚本而不是生图

这类图一个字都不能错，又不需要任何生成能力，所以固定用 `scripts/make_text_poster.py` 排版，不进 AI 生图通道：脚本改文案只改参数，重出成本几乎为零；AI 每次重画都要重新逐字校验。

什么时候仍然用 AI 生图：需要照片、场景、产品合成时。什么时候两者都不要用：需要真实 Logo 或公司中文字形时，走 [logo-assets.md](logo-assets.md) 的确定性抠图流程。

## 版面解剖

参考样式（帝王蓝底白字）拆出来的固定比例，脚本已按此设定：

| 元素 | 做法 |
|---|---|
| 底色 | 整幅纯色，无渐变、无纹理。品牌色优先，参考样式的蓝是 `#011DA4`，示例品牌绿是 `#1B5942` |
| 品牌行 | 可选，小号字加宽字距，放最上方 |
| 标题 | 高对比衬线（Bodoni Bold），纯白，占宽约 7–8%，可折 3 行 |
| 正文 | 无衬线细体（Segoe UI Light），纯白，占宽约 3.6% |
| 卖点列表 | 与正文同字体，`•` 起头，悬挂缩进 |
| 边距 | 左右约 10.5% 宽，上下约 7.5% 高 |
| 对齐 | 方形和竖版左对齐；横版标题和列表块居中 |
| 竖向分布 | 内容偏上，底部留白。Stories / Reels 底部有界面遮挡，不要往下堆 |

## 尺寸

| 比例 | 尺寸 | 版位 |
|---|---|---|
| `9x16` | 1080 × 1920 | Stories / Reels / Reels Overlay |
| `1x1` | 1080 × 1080 | Feed / Profile Feed / Search / Notification |
| `1.91x1` | 1200 × 628 | In-stream / 横版 |

同一个内容一次出三套，不要拉伸。横版按参考做法只放标题和卖点列表，把正文段落省掉，否则会挤成一团。

## 用法

```bash
python scripts/make_text_poster.py \
  --ratio "9x16,1x1" \
  --bg 1B5942 \
  --brand "FANCY DEKOR" \
  --title "China PVC Wall Panels & Skirting Boards Manufacturer" \
  --body "Supplying importers and distributors with factory-direct PVC wall panels, skirting boards and fluted panels." \
  --bullets "Own factory, 60,000 sqm, since 2007;100+ PVC extrusion lines;Marble, wood grain and fluted finishes;Factory direct OEM & ODM, no middlemen" \
  --out-dir output/poster --prefix fancy-dekor-text-green

python scripts/make_text_poster.py \
  --ratio "1.91x1" --bg 1B5942 --brand "FANCY DEKOR" \
  --title "China PVC Wall Panels & Skirting Boards Manufacturer" \
  --bullets "..." \
  --out-dir output/poster --prefix fancy-dekor-text-green
```

参数：

- `--ratio` 逗号分隔，可多选；`--size 1080x1080` 可覆盖成任意尺寸。
- `--bg` 六位色值，不带 `#` 也行。
- `--bullets` 用分号分隔，每段一条。
- `--brand` / `--body` / `--footer` 都可留空，留空就不画那一块。
- 字号会按内容自动收缩到安全区内，不需要手调；想调大标题就改脚本 `RATIOS` 里的标题比例或 `--size`。

## 文案怎么写

- 标题用参考句式的身份句：`China {品类} Manufacturer`、`We are the factory`。品类按客户实际产品写，不要凑不存在的品类。
- 卖点每条一个事实，来自用户提供的资料，数字原样保留（客户写 `60000` 就不要擅自改成 `60,000`）。
- 认证、质保年限、仓库位置、客户数量这类没有资料依据的一律不写；参考图里的 `Up to 3 years warranty`、`U.S. Based Warehouse` 是人家的产品条件，不能照抄。
- 不写价格、不写 `No.1` / `Best` / `Guaranteed` 这类绝对表述。

## 质检清单

- 逐字核对标题、正文、每一条卖点；连标点和数字写法都要和确认稿一致。
- 三套比例都实际打开看：有没有截断、折行断在奇怪的词上（一个孤零零的短词单独占一行）、列表第二行缩进是否对齐。
- 底色是纯色，放大边缘没有渐变台阶或压缩色带。
- 图上没有二维码、网址、邮箱、电话、WhatsApp，除非用户明确要求。
- 竖版底部三分之一留白，重要文字不落在 Stories 的界面遮挡区。

## 常见坑

- 把 Logo 或照片塞进纯色版：这个样式的力量来自纯文字，加图形就散了；需要品牌露出时用那行小号字距品牌名。
- 用 AI 生成这类图：文字必错，且每次都要重新校验，纯属自找麻烦。
- 横版硬塞正文段落：参考样式的横版只有标题加列表，正文留给广告文案区。
- 三个比例分别手排一遍：同一套参数跑三次即可，改文案时三套同步更新。
- 直接照抄参考图的蓝色：那不是品牌色，客户品牌有颜色就用品牌色。
