---
name: b2b-facebook-ads-manager
description: 管理 Meta/Facebook 广告账户、主页内容与外贸 B2B 获客视频的全流程技能：生成中文 Markdown 表现报告（近 7/30 天、同环比、表单线索/消息对话成效分离、花费上限余额预警）；研究目标受众、兴趣、隐藏兴趣并估算国家/地区覆盖；诊断并安全执行广告操作（新建默认 PAUSED、任何写操作须明确确认）；为制造商、机械设备供应商、外贸 B2B 企业研究产品并生成英文线索广告文案、中文审查翻译、5 组测试版本、产品海报、9:16/1:1/1.91:1 版位素材和高意向即时表单；制作主页封面 Banner（1640x624）、把实拍招牌照片转成全套 Logo 资产、写带工厂身份的自然流帖子文案；把工厂/产品素材文件夹剪成上下分屏、中缝常驻 China XXX Supplier 大标题的 9:16 B2B 获客短视频（FB/IG/TikTok 广告、Reels）。用户提供 Meta 访问口令、广告账户、Ads Manager 链接或对象 ID，或要求 FB 广告报告、受众研究、诊断、优化、创建/复制广告、写 B2B 广告文案、做主页封面图、清理 logo、写 FB 帖子，或提供工厂/产线/产品素材要获客视频、工厂视频、上下分屏、凸显 B 端身份、前三秒出现中国供应商时使用。
---

# B2B Facebook Ads Manager（Meta 广告报告、受众研究、安全操作、B2B 广告构建、主页物料与获客视频）

Meta/Facebook 广告账户、主页内容与外贸获客视频的单一入口，覆盖六种工作模式：

- **报告模式**：生成中文 Markdown 账户表现报告（只读）。见 [references/reporting.md](references/reporting.md)。
- **管理模式**：诊断、优化建议，并在用户明确确认后执行写操作。见 [references/management.md](references/management.md)。
- **受众研究模式**：查找目标受众、兴趣、隐藏兴趣，估算国家/地区覆盖。见 [references/audience.md](references/audience.md)。
- **B2B 广告构建模式**：从产品资料到英文文案、中文审查翻译、素材、线索表单和 Ads Manager 落地。见 [references/b2b-ad-builder.md](references/b2b-ad-builder.md)。
- **主页物料模式**：主页封面 Banner、纯色文字海报、实拍照片转 Logo 资产、自然流帖子文案。见 [references/page-banner.md](references/page-banner.md)、[references/text-poster.md](references/text-poster.md)、[references/logo-assets.md](references/logo-assets.md)、[references/page-post-copy.md](references/page-post-copy.md)。
- **工厂获客视频模式**：素材文件夹 → 上下分屏 9:16 获客短片（中缝常驻 China XXX Supplier 大标题）。见 [references/factory-video.md](references/factory-video.md)、[references/factory-video-layout.md](references/factory-video-layout.md)。

## 引导式开场（首次使用 / 意图不明时）

用户第一次使用本技能，或请求模糊（如“帮我看看广告”“用这个技能”“你看着办”）时，先走引导，不直接开跑：

1. 用一两句话说明本技能能做什么，然后只问一个问题让用户选择方向：
   - 账户表现报告（只读）
   - 受众 / 兴趣 / 覆盖研究（只读）
   - 诊断与优化建议（改动需确认）
   - B2B 广告构建（文案 / 素材 / 表单 / 建广告）
   - 主页物料（封面 Banner / Logo 资产 / 帖子文案）
   - 工厂获客视频（素材文件夹 → 上下分屏短片）
2. 按选择进入对应模式；每个模式按 [references/onboarding.md](references/onboarding.md) 的提问顺序收集信息，一次只问一组必要问题，不抛长问卷。
3. 先检查前置条件（token 是否已设置、账户是否已知），并在用户要设置 token 前先做模型来源检查：当前用国内模型时，按「安全规则」提示 FB 个人账号受限与封号风险并建议换国外模型，等用户明确回复再继续。
4. token 只报告“已设置 / 未设置”，粘贴后仅当前进程临时使用。
5. 每完成一步用一句话同步“已确认：…；还需要：…”，结束时区分“已完成结果”和“需用户确认后执行的动作”。

用户请求已明确（如“出近 30 天报告”）时，直接进入对应模式，不重复走开场问题。

## 安全规则（六种模式通用）

- 绝不打印、重复、存储或在报告、日志、代码文件、回复中包含访问口令 `FB_ACCESS_TOKEN`。优先从环境变量读取；用户粘贴的口令只作临时环境变量，用后立即移除。
- **接入 token 前先做模型来源检查（强制）**：用户要提供 / 设置 `FB_ACCESS_TOKEN`、登录或对接 FB 后台、跑任何请求 Meta 接口的动作之前，先判断当前会话所用模型是不是国内模型，然后按下面的分支处理；不确定就先问，不要默认跳过。
  - 判定依据按顺序取：当前模型名称或 ID 自报（如通义千问 / Qwen、DeepSeek、豆包 / Doubao、Kimi / 月之暗面、GLM / 智谱、文心 / ERNIE、混元、MiniMax、百川、Yi 等属国内；OpenAI、Claude、Gemini、Grok 等属国外）→ 当前环境的模型标识（系统提示、模型选择器、启动参数）→ 都拿不到就直接问用户“当前这个 agent 用的是哪家模型”。
  - 若是国内模型：在用户粘贴 token 之前明确提示风险——国内模型的调用链路与数据出境受国内监管，Meta 容易把这类访问判定为自动化或异常环境，后果从限制该 FB 个人账号的广告 / 主页功能，到触发风控封号；另外国内模型对英文素材和 Meta 政策的合规判断也可能有偏差。提示后建议先换国外模型（OpenAI 的 GPT 系列、Anthropic 的 Claude 系列）完成 FB 后台接入、token 生成与广告操作。
  - 提示完必须等用户明确回复（继续用当前模型 / 换模型）再往下走。用户选择继续时，只读操作照常执行；每条写操作按本文既有规则单独确认，并建议不要在主力账号或已投放在跑的账号上试。
  - 若是国外模型：不提示，直接继续。
- 需要代理时用 `FB_PROXY`，常用 `http://127.0.0.1:10808` 或 `socks5h://127.0.0.1:10808`。
- 所有新建广告默认 `PAUSED`。任何写操作（开关 campaign/ad set/ad、改预算或出价、删除/归档、修改在用广告、创建 A/B 副本、发布/启用暂停副本）都必须先取得用户对具体动作的明确确认。
- 每次确认的写操作后，重新读取对象并报告：对象 ID、名称、`configured_status`、`effective_status`。
- `effective_status=PENDING_REVIEW` 表示审核中；`IN_PROCESS` 表示 Meta 正在处理素材或创意。不要把二者误报为正常投放。
- 主页物料模式与工厂获客视频模式只写本地文件（图片、文案、视频），不触碰广告账户；涉及上传主页素材、发布帖子或把成片用于投放时，按上一篇的写操作规则先取得明确确认。

## 主页物料快速规则

公司名、品牌拼写、中文字形这类不能错的信息，一律用确定性方式产出，不用 AI 生成：

- **封面 Banner**：`scripts/make_page_banner.py`，真实照片 + 精确排版，同时导出 1640×624 与桌面显示尺寸 820×312；文字避开左下角（主页头像会压住）。详见 [references/page-banner.md](references/page-banner.md)。
- **纯色文字海报**：`scripts/make_text_poster.py`，纯色底 + 纯白文字、零照片，一次出 9:16 / 1:1 / 1.91:1；纯文字图不交给 AI 生图。详见 [references/text-poster.md](references/text-poster.md)。
- **Logo 资产**：只有实拍招牌照片时，先 `$jojocode-imagegen` 清理成纯白底纯黑字，再 `scripts/logo_from_photo.py` 抠 alpha、`scripts/logo_variants.py` 出白底/透明/反白/1080 方形全套；只清理不重画。详见 [references/logo-assets.md](references/logo-assets.md)。
- **帖子文案**：英文正文 + 中文对照，一段一个意思、段间空行；B2B 主页用"工厂身份"做钩子（`Factory, not a trading company.`），不编造认证、MOQ、产能，不写客户彩盒上的第三方品牌。详见 [references/page-post-copy.md](references/page-post-copy.md)。
- **主页简介与主页信息**：写 FB 主页简介、About、把空主页补完整时，改用 `$fb-page-profile-builder` 技能（引导式逐字段完善，含 255 字符简介与字段检查脚本）。
- **生图通道**：所有 AI 生图统一走 `$jojocode-imagegen`（用户固定生图接口），不要默认改用通用 `$imagegen`；版位尺寸、参考图换比例和密钥规则见 [references/image-channel.md](references/image-channel.md)。

## 工厂获客视频快速规则

用户给一个工厂 / 产线 / 产品素材文件夹，要"能获客的广告片"（上下分屏、凸显 B 端身份、前三秒出现中国供应商）时走这个模式，完整流程见 [references/factory-video.md](references/factory-video.md)：

- **先盘点再渲染**：素材超过 20 个文件时，先跑 `scripts/inspect_materials.py` 出素材清单 + 抽帧九宫格 + 方向建议，让用户确认方向后再开工，不要闷头剪整条片子。
- **脚本顺序**：`scripts/make_overlays.py project.json`（文字层）→ `scripts/make_video.py project.json`（分段渲染并拼接）→ `... --check`（验收）。单段改动用 `make_video.py project.json <段名>` 只重渲那一段。
- **大标题从第一秒起常驻画面正中**（`brand.title_lines`），贯穿全片；中缝同时承载每段卖点字幕，不要把字幕塞回顶部条。
- **静帧素材一律不动**：照片不做推拉和缓慢缩放，只有视频素材播放。对产品静图做 Ken Burns 会发虚显假。
- **上屏讲"我们是工厂"，下屏讲"东西卖得掉"**；每段约 3 秒，全片 20–25 秒。
- **文字层和主页物料同一套规矩**：品牌名、公司名、卖点数字一律用 Pillow 确定性排版，不用图像模型生成文字。
- **必须人眼看过抽帧总览图再交付**；交付四件：成片 mp4、封面帧、素材盘点 md、交付说明 md。
- 该模式只写本地文件和调用本地 ffmpeg，不触碰广告账户；要把成片用于投放或上传时，按写操作规则先取得明确确认。

## 依赖安装

```bash
pip install -r requirements.txt
```

requirements.txt 位于技能目录下；从其他工作目录运行时，请使用技能文件夹的完整路径。

工厂获客视频模式另外需要**外部 `ffmpeg` / `ffprobe` 可执行文件**（PATH 上能找到，或用参数指定完整路径），Python 侧只需 Pillow。缺 ffmpeg 时先让用户装好再开跑，不要试图用纯 Python 替代。

## 报告快速运行

报告模式优先使用内置脚本：

`scripts/generate_fb_markdown_reports.py`

```powershell
$env:FB_ACCESS_TOKEN='<token from user or environment>'
$env:FB_PROXY='http://127.0.0.1:10808'
python scripts/generate_fb_markdown_reports.py --account-id <ACCOUNT_ID> --out-dir fb_output
Remove-Item Env:\FB_ACCESS_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:\FB_PROXY -ErrorAction SilentlyContinue
```

脚本位于技能目录 `scripts/` 下；若从其他工作目录运行，请把 `scripts/` 换成技能文件夹的完整路径。

默认 Python 缺依赖时，使用 `codex_app.load_workspace_dependencies` 提供的 Codex 内置 Python。

## 最终回复

最终回复简洁、默认中文。报告给 Markdown 文件链接；广告/主页物料给成品文件路径；工厂获客视频给成片 mp4 与封面帧路径，并说明时长、分辨率、有无音轨、还缺什么素材。写操作给出已确认动作和复核状态；建议区分“分析结论”与“需用户确认后执行”的部分。
