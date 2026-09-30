# 生图通道（JojoCode / `$jojocode-imagegen`）

所有 AI 生图——广告海报、版位素材、封面氛围图、Logo 清理底稿——统一走 `$jojocode-imagegen`，用用户配置的固定接口。不要默认改用通用 `$imagegen`。

## 通道与凭据

- 技能根目录：以 `$jojocode-imagegen` 的实际加载位置为准，本机为 `$env:USERPROFILE\.agents\skills\jojocode-imagegen`。
- 默认 provider `jojocode`，默认模型 `gpt-image-2`；凭据在该技能根目录的 `config.json`。
- `OPENAI_API_KEY` 环境变量优先于 `config.json`；key 只在当前进程内使用。
- 绝不打印、回显、写进回复或落盘 key，只报告"已配置 / 未配置"。
- 通道报错时（例如 `model_not_found`、`no available channel for model ... under group ...`）把原始错误报给用户，不要静默换成别的生图通道。

## 尺寸

`gpt-image-2` 接受任意 `宽x高`，条件是两边都是 16 的倍数、长边:短边 ≤ 3:1、总像素在 655,360–8,294,400 之间。

Facebook 版位固定这三套，不要用别的尺寸：

| 版位 | 比例 | 尺寸 |
|---|---|---|
| Stories / Reels / Reels Overlay | 9:16 | `1152x2048` |
| Feed / Profile Feed / Search / Notification | 1:1 | `1536x1536` |
| In-stream / 横版 | 1.91:1 | `1920x1008` |

## 生成

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.agents\skills\jojocode-imagegen\scripts\generate.ps1" `
  -Prompt "<完整提示词>" -UseCase "b2b-facebook-ad-poster" `
  -Size 1152x2048 -Quality high `
  -Out "<项目绝对路径>\output\imagegen\<主题>-9x16-v1.png"
```

- 输出统一放项目 `output/imagegen/`，文件名带主题、比例和版本号，例如 `fb-poster-dealer-dark-showroom-1x1-v1.png`。
- 不覆盖已有文件；改一版就把版本号 +1。
- `-Prompt` 里逐条列出必须逐字出现的文案（品牌名、标题、副标题、每条卖点、CTA、底部品类条）。不要写"一小段小字"这类会放任模型自己编的指令。

## 换比例：用参考图重排，不要拉伸

同一张素材要补另外两个比例时，把原图当参考图传给 bundled CLI 的 `edit`，要求"同一套设计、同一套文字，只换版式"，不要裁切或等比拉伸。

```powershell
$cfg = Get-Content "$env:USERPROFILE\.agents\skills\jojocode-imagegen\config.json" -Raw | ConvertFrom-Json
$env:OPENAI_BASE_URL = $cfg.providers.jojocode.base_url
$env:OPENAI_API_KEY  = $cfg.providers.jojocode.api_key
$py  = "$env:USERPROFILE\.agents\skills\jojocode-imagegen\.venv\Scripts\python.exe"
$cli = "$env:USERPROFILE\.codex\skills\.system\imagegen\scripts\image_gen.py"
& $py $cli edit --model gpt-image-2 --image "<原图>" --prompt "<重排提示词>" `
  --size 1536x1536 --quality high --no-augment --out "<新文件>"
```

- 必须用该技能自带 `.venv` 里的 python；系统 python 没有 `openai` SDK，会直接报 `openai SDK not installed`。
- 横版按左右分栏重排（文字栏 + 主图整幅出血），方形按上下分区重排；信息层级要按比例重新安排，不要缩放原版。
- 参考图通道同样受上面的尺寸规则约束。

## 生成后必查

用图片查看工具真的打开看一遍再交付：

- 逐字核对每一行文案，包括数字写法（`60000` 和 `60,000`、`100 plus` 和 `100+` 是两种写法，不能互相替换）。
- 没要求就不能出现二维码、网址、邮箱、电话、WhatsApp、水印、无意义小字段落、人物。
- 品牌名、公司名、中文字形与用户给的完全一致；只要有一个字母不对就重出。
- 任一项不对时生成新版本，不覆盖旧文件。

## 边界

- Logo、公司名这类必须精确的内容仍走确定性脚本（`scripts/logo_from_photo.py`、`scripts/logo_variants.py`、`scripts/make_page_banner.py`）；AI 只用来出干净底稿、背景和氛围图。
- 不要把 Meta 自带 CTA 按钮画进海报，除非用户明确要求。
