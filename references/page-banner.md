# 主页封面与横版 Banner（Page Banner）

Facebook 主页封面、横版素材底座、公司介绍图的制作规范。产出物是可直接上传的位图，不涉及任何 API 写操作。

## 尺寸与安全区

| 用途 | 尺寸 | 说明 |
|---|---|---|
| 主页封面（上传文件） | 1640 × 624 px | Meta 建议值，约 2.63:1 |
| 桌面实际显示 | 820 × 312 px | 用这个尺寸导出一次，反查文字是否过小、发糊 |
| 横版广告素材 | 1.91:1（如 1200 × 628） | 需要投横版版位时单独排一版，不要拉伸封面 |
| Stories / Reels | 9:16 | 见 [b2b-ad-builder.md](b2b-ad-builder.md) 的版位素材章节 |

排版约束：

- 关键文字全部放在画面中部；左右各留约 8%、上下各留约 10% 的边距。
- 回避左下角：桌面端主页头像和主页名压在封面左下角，约占左侧 20%、下方 30% 的区域（以当前版式为准）。
- 移动端会额外上下裁切，发布前用手机和桌面各预览一次，以真实预览为准。
- 800 × 312 的桌面缩小版上，正文小于 20 px 就会糊，别把品类词写得比公司名还靠边。

## 两种做法，先选对路

| 做法 | 适用 | 代价 |
|---|---|---|
| 确定性合成（推荐做主封面） | 公司介绍型封面、需要中英文字精确无误、要放真实工厂照片 | 需要脚本和照片素材，版式自由度靠参数调 |
| AI 生成（`$jojocode-imagegen`） | 概念场景图、排产品列阵的氛围图、没有合适实拍时 | 文字容易拼错，产品结构可能被改动，必须逐字校验 |

公司名、品类、市场这类必须准确的信息，优先走确定性合成；AI 生成的结果只做背景或氛围，文字另行叠加。

## 确定性合成

脚本：`scripts/make_page_banner.py`（真实照片 + 精确排版，一次导出 1640×624 和 820×312）。

```bash
python scripts/make_page_banner.py \
  --photo "factory-row.png" \
  --style band \
  --kicker "KITCHEN SMALL APPLIANCE FACTORY · OEM / ODM · CKD / SKD" \
  --title-en "ZHONGSHAN RONGHUI ELECTRIC APPLIANCE CO., LTD." \
  --title-cn "中山市荣惠电器有限公司" \
  --sub1 "Blenders · Mixers · Coffee Makers · Induction Cookers" \
  --prefix fb-cover-ronghui-band \
  --out-dir output/banner
```

两种版式：

- `band`：上方深色品牌带放公司名，下方接一条真实产品/产线照片横带。信息层级最清楚，适合主页主封面。
- `fullbleed`：整幅照片铺满，加深色渐变蒙版压住对比度，文字居中叠加。气势足，但对照片质量要求高。

参数要点：

- `--accent` / `--navy-top` / `--navy-bottom` 改品牌色；不改客户品牌色。
- `--photo-anchor 0.4` 控制裁切重心（0 偏上、1 偏下），用来避开照片里的杂物和高光。
- `--font-en-bold` / `--font-cn-bold` 等可覆盖字体；默认自动在系统字体里找 Segoe UI / 微软雅黑（Windows）、Arial / PingFang（macOS）、DejaVu（Linux）。
- 中文标题缺失时留空即可，脚本会跳过该行。

## AI 生成

调用 `$jojocode-imagegen`，用 `ads-marketing` 用例、`Facebook Page cover banner, ultra-wide horizontal` 资产类型。尺寸、密钥和参考图换比例规则见 [image-channel.md](image-channel.md)。模板：

```text
Use case: ads-marketing
Asset type: Facebook Page cover banner, ultra-wide horizontal
Primary request: {一句话描述这张封面的用途，例如：中国厨房小家电工厂主页封面，基于真实展厅产品列阵}
Scene/backdrop: {真实场景，例如：明亮的现代工厂展厅、玻璃隔断、抛光地面、柔和顶灯}
Subject: {产品列阵：颜色、数量、角度、材质，写具体}
Text (verbatim), must be spelled exactly: {逐字给出每一行文字，标注位置和大小层级}
Composition/framing: ultra-wide 2.6 to 1；标题放在中部安全区；产品贴底排开，两侧留白；外边缘不放重要内容
Lighting/mood: 明亮高调棚拍日光，柔和反射，干净的商业氛围
Style/medium: 高端商业产品摄影，锐利、现代、企业感
Color palette: {主色与强调色}
Constraints: 每行文字拼写必须逐字正确；全部文字在中央安全区内；不要水印、不要品牌 logo、不要人物、不要多余文字、不要乱码字母
Avoid: watermark, misspelled or garbled text, extra text blocks, logos, distorted or melted appliance shapes, cluttered background, dark muddy lighting, cropped-off headline
```

AI 生成后的必查项：公司名逐字母比对、中文是否被画成假字、产品结构有没有被改（按钮数、杯体形状、料斗位置）、有没有多出无意义字母。任一项不对就重出，不要将就。

## 文字层级模板

从上到下四层，一层一个意思：

1. `kicker`：身份行，全大写小字加字距，如 `KITCHEN SMALL APPLIANCE FACTORY · OEM / ODM`。
2. 公司名（英文全大写）：最大字号，封面第一视觉。
3. 公司名（中文）：次一级，与英文配套出现。
4. 品类行 / 市场行：小字一行，品类之间用 `·` 分隔。

配套做法：深色蒙版保证文字对比度；公司名加一点模糊投影防止压在浅色照片上糊掉；用一条品牌强调色细线做分隔，比整块色块更耐看。

## 质检清单

- 文字无裁切、无错字、无乱码；公司名和品牌拼写与用户提供的完全一致。
- 820×312 缩小版上仍能读清公司名和一行品类。
- 左下角没有重要文字被头像压住。
- 产品结构未被改动；照片里的杂物、反光、无关遮挡已清理或裁掉。
- 用了用户原始 Logo 文件，没有重画、没有改比例、没有覆盖机身原有标识。
- 没有把 Meta 自带 CTA 按钮画进图里；没有水印。

## 常见坑

- 直接把 9:16 或 1:1 素材拉伸成封面：产品变形，文字压扁。各版位单独排版。
- 只导出 1640×624 就交付：桌面端看到的其实是 820×312，小字全糊。
- 用 AI 生成图当公司介绍封面：公司名拼错或中文字形不对，属于对外物料事故。
- 把主页头像和主页名会压住的位置当安全区用。
