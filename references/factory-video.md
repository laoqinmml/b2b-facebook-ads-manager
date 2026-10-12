# 工厂获客视频模式

把一批工厂照片 + 产品视频做成一条可以直接投 FB / IG / TikTok 的获客短视频。默认结构是上下分屏：**上屏工厂/产线，中缝常驻大标题和卖点，下屏成品/款式**。

## 什么时候用

用户给一个素材文件夹（工厂照片、产线视频、产品视频、色卡），要的是"能获客的广告片"，并且通常要求凸显中国供应商 / 工厂身份。

不适用：

- 口播视频去气口、加动态字幕 → `$kbcut`
- 用 HTML + 无头浏览器做动效合成 → `$hyperframes` / `$general-video`
- 只要一张图或一套海报 → 本技能的主页物料模式，见 [text-poster.md](text-poster.md)、[page-banner.md](page-banner.md)

## 工作流

### 1. 先盘点，再动手

素材超过 20 个文件时，**先给素材盘点 + 方向建议，再开始渲染**，不要闷头剪。跑：

```bash
python scripts/inspect_materials.py "D:\素材文件夹" --out "素材清单.md" --contact-sheet
```

它会按文件夹统计图片/视频数量、逐条列出视频的时长与分辨率，并给每条视频出一张抽帧九宫格，方便直接判断画面能不能用。盘点要回答三件事：工厂素材够不够、有没有真实产线动态素材、竖屏素材够不够（横屏素材不能直接铺满 9:16）。

方向建议一般给这五种，按优先级：上下分屏（主推）> 工厂巡览 > 性能实验 > 款式浏览 > 装柜出货。

### 2. 写 project.json

所有可变项都在一个 JSON 里（品牌、标题、每屏素材、字幕、时长、音轨）。完整字段和示例见 [factory-video-layout.md](factory-video-layout.md)。要点：

- `brand.color` 从客户 logo 里**取样**，不要凭感觉定
- `brand.title_lines` 是常驻大标题，写 `["CHINA WPC WALL PANEL", "SUPPLIER"]` 这种 1–2 行的形式
- 每个画面用 `{"src": "...", "ss": 1.2, "frac": [0.5, 0.42]}`，`frac` 是裁切取景的横向/纵向比例（0–1），用来选画面里想保留的区域
- 文案只写能从客户资料里核实的数字，**没有依据的认证、MOQ、交期、产能一律不写**

### 3. 生成包装层

```bash
python scripts/make_overlays.py project.json
```

产出顶部资质细条、中缝标题带（含每段字幕）、上/下屏标签、品牌水印、结尾卡。**品牌名、公司名、卖点数字一律用 Pillow 确定性排版，绝不用图像模型生成文字**——拼写错了整条片子就白拍，规则同本技能「主页物料快速规则」。

### 4. 渲染与合成

```bash
python scripts/make_video.py project.json            # 全部
python scripts/make_video.py project.json beat3      # 只重渲某一段
python scripts/make_video.py project.json --assemble # 只拼接和混音
```

逐段渲染再拼接，不要写一个巨大的 filtergraph：单段出错能单独重渲，改一段不用重跑全片。

### 5. 验收

```bash
python scripts/make_video.py project.json --check
```

脚本会核对：分辨率/帧率、每段的流结构、成片是否有音轨、第 1 秒的画面是否存在（大标题必须在第一秒就已经完整可读），并导出一张抽帧总览图和封面帧。**必须人眼看一遍总览图**再交付。

交付物固定四件：成片 mp4、封面帧、素材盘点与方向建议 md、交付说明 md（写清结构表、音轨状态、用了哪些素材、还缺什么）。

## 硬约束

1. **大标题从第一秒起就在画面正中，并贯穿全片。** 用户常说的是"前三秒出现中国 XXX 供应商"；做成常驻比做成 3 秒闪现更容易过需求，也更像投放大户的片子。
2. **静帧素材一律不动。** 照片不用推拉、不用缓慢缩放，固定机位裁切即可；只有视频素材播放。对产品静图做 Ken Burns 会发虚、显假，用户会明确要求去掉。
3. **中缝是信息带，不是分隔线。** 大标题 + 每段切换的卖点字幕都在这里，不要塞回顶部条里。
4. **上屏讲"我们是工厂"，下屏讲"东西卖得掉"。** 上屏用门头、车间、产线、仓库、装柜；下屏用成品、纹理、色卡、安装效果。
5. **每段 3 秒左右，全片 20–25 秒。** 再长完播率掉，再短讲不清工厂。
6. 文案必须和客户已有的投放物料口径一致（例如已有的分销商招募图），不要自创第二套说法。
7. 输出 9:16 为默认；需要 1:1 / 4:5 时同一套 `project.json` 改 `size` 重跑，版面按比例自动缩放。

## 脚本

技能目录 `scripts/` 下：

- `scripts/inspect_materials.py`：素材盘点 + 视频抽帧九宫格 + 生成盘点 md
- `scripts/make_overlays.py`：所有文字层 PNG（含结尾卡）
- `scripts/make_video.py`：分段渲染、拼接、音轨、封面、验收

依赖：Pillow + **外部 ffmpeg / ffprobe**（必须在 PATH 上，或让用户提供所在目录）。详见 [environment.md](environment.md)。

## 参考

- [factory-video-layout.md](factory-video-layout.md)：版面尺寸与字号契约、ffmpeg 表达式与踩坑、完整 project.json 示例
