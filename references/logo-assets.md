# Logo 资产化（Logo Assets）

工厂客户手上常常只有一个带背景的照片：车间门口的招牌、背光的门头、印在彩盒或水印里的 logo，没有矢量原文件。本文件规定如何把这些素材变成可用的品牌资产。

## 目标产物清单

一次交付就出全套，避免后面反复找素材：

| 文件 | 用途 |
|---|---|
| `{prefix}-whitebg.png` | 白底黑字，用于合同、报价单、Word、白底广告图 |
| `{prefix}-whitebg@2x.png` | 2 倍图，用于高清网页和高分屏印刷 |
| `{prefix}-transparent.png` | 透明底黑字，用于浅色背景海报、Banner 叠加 |
| `{prefix}-white-reversed.png` | 透明底白字（反白），用于深色背景 Banner、视频片尾 |
| `{prefix}-square-1080.png` | 1080×1080 白底方形，直接当主页头像 |
| `{prefix}-square-1080-transparent.png` | 1080×1080 透明方形，留给其他版位 |

## 两条路线

| 路线 | 用法 | 说明 |
|---|---|---|
| AI 清理（`$imagegen`） | 招牌照片 → 纯白底纯黑字的干净底稿 | 适合光晕、纹理、反光重的源图 |
| 确定性抠图（脚本） | 照片 → alpha 通道 → 全套变体 | 尺寸、边缘、透明度可控，不改字形 |

推荐串联：**先用 AI 出干净底稿，再用脚本出 alpha 和变体**。源图本身干净（比如已经拍得很平的印刷品）时可以直接走脚本。

## AI 清理提示词模板

用 `logo-brand` 用例，并在提示里把"只清理、不重画"讲清楚：

```text
Use case: logo-brand
Asset type: clean logo asset, black on white, for web and print use
Primary request: Turn this photo of a backlit sign into a crisp, flat, professional logo asset. Keep the logo design exactly as it is; only clean it up.
Input image: the attached photo is the reference and the only source of the logo artwork.
Scene/backdrop: pure solid white background, completely uniform, no texture, no marble, no tile, no grout lines, no wall, no shadows, no gradient, no vignette.
Subject: exactly the same logo lockup: {逐个描述图形元素、英文拼写、中文字、横线位置}
Style/medium: flat vector-style logo reproduction, solid pure black letterforms, perfectly smooth edges, even stroke weight, high resolution, sharp anti-aliased curves.
Composition/framing: centered lockup, same stacked layout and the same relative sizes, spacing and proportions as the reference, even white margins on all four sides.
Constraints: reproduce the letterforms exactly as in the reference; keep {英文} spelled exactly {逐字母}; keep {中文} exactly {汉字}; remove the warm glow, the backlight halo and the panel edges completely; no color, pure black and pure white only.
Avoid: glow, halo, backlight, marble texture, tile grout lines, wall texture, drop shadow, gradient background, color tints, extra text, misspelled or garbled letters, altered letterforms, thinned or melted strokes, watermark, logos, signature.
```

描述 `Subject` 时不要只说 "the logo"，要把版式拆开写：图形在上、英文在中间、中文在下、左右各一条横线、某个字母里有细白线之类。写得越具体，AI 越不会重新设计。

## 硬规则

- 只清理，不重画。字形、字距、粗细、比例必须和原始素材一致。
- 不发明 logo。没有 logo 文件时，问用户是否接受纯文字公司名，不要自己画一个。
- 拼写逐字母核对；中文字逐字核对（"荣 惠"不等于"荣惠"，字距和横线也是设计的一部分）。
- 只用纯黑和纯白，不要带品牌色版本，除非用户提供品牌色规范。
- 深色背景用反白版（`-white-reversed.png`），不要把黑字版放在深色底上。

## 脚本：从照片直接抠

`scripts/logo_from_photo.py`：用"局部背景估计 + 局部对比度 + 连通域过滤"把笔画和背景分开。

```bash
python scripts/logo_from_photo.py \
  --src "door-sign.jpg" \
  --prefix ronghui-logo \
  --out-dir output/logo \
  --keep-box 48,62,588,492 \
  --keep-bands "200,80,452,302;75,305,575,395;75,396,585,492"
```

参数怎么调（按这个顺序看，不要一上来就乱改）：

1. 先跑一次，看输出的 `keep / drop` 日志。被误删的组件会在日志里显示 `drop area=... box=...`。
2. 笔画被删 → 降 `--delta-floor`（默认 90）或降 `--l-floor`（默认 120，笔画不够黑时调高也行，但会带进阴影）。
3. 背景纹理被留下 → 升 `--min-area`（默认 60），或收紧 `--keep-box` / `--keep-bands`。
4. 边缘发虚、锯齿明显 → 调 `--blur`（默认 0.7）。
5. `--keep-bands` 是"logo 由几行组成"的区域白名单，能一次性干掉图上的大理石纹、瓷砖缝、反光。

输出 `{prefix}-whitebg.png`（做底稿检查）和 `{prefix}-transparent.png`；确认无误后再跑 `logo_variants.py` 出全套。

## 脚本：出全套变体

`scripts/logo_variants.py`：从干净底稿（黑字白底）生成白底、透明、反白、1080 方形和 @2x。

```bash
python scripts/logo_variants.py \
  --src "clean-logo.png" \
  --prefix ronghui-logo \
  --out-dir output/logo
```

参数：`--margin`（裁切后留白，默认 40）、`--black-percentile`（黑场估计，默认 0.002）、`--square`（默认 1080）、`--square-fill`（方形画布里 logo 占比，默认 0.86，主页头像会圆裁，不要贴边）。

## 质检清单

- 放大到 200% 看边缘：字形有没有被磨圆、断笔、粘连。
- 英文拼写逐字母比对；中文逐字比对；字距和装饰线是否保留。
- 透明 PNG 的边缘没有白边（白边说明 alpha 没抠干净，深色底上会露馅）。
- 1080 方形头像版：logo 完整、居中、四周有余量，圆裁后不缺角。
- 反白版在深色背景上预览一次。
- 交付时说明每个文件用在哪里，避免客户把反白版放白底。

## 常见坑

- 背景纹理（大理石纹、瓷砖缝、墙砖）被当成笔画：靠 `--keep-bands` 和 `--min-area` 过滤，不要靠调阈值硬抠。
- 背光招牌的暖色光晕没去干净：先在 `$imagegen` 里清理，再进脚本。
- 手机拍摄的像素锯齿直接放大：先轻微高斯模糊（约 0.7）再上采样，放大后才不会出现台阶。
- 让 AI"重新设计一个更现代的 logo"：这是对外物料事故，直接禁止。
- 只用 AI 出的图当最终文件：AI 可能改字形，必须叠加脚本产出的确定性 alpha 版本，或者人工逐字核对后再用。
