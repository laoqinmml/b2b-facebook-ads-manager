# 自动建广告模式

当用户明确要求新建 Meta 广告，并提供了下列任一类 token 时进入本模式：

- **Developer app user token**：由 Meta Developer 应用 / Graph API Explorer 取得的用户访问令牌。它不是一种单独的“Developer token 类型”；是否可用取决于 token 所属用户、应用权限、令牌有效期及资产分配。
- **System User token**：由 Business Manager 系统用户生成，须将目标广告账户和主页分配给该系统用户。

仅有 token 字符串不代表可操作目标资产。先用只读请求识别 `/me` 身份、`/me/permissions` 权限和目标账户；再确认目标 Page 可读、可取得 Page Access Token、可读写 Lead Form，并且目标 Ad Account 能创建 campaign、ad set、creative 和 ad。不要要求用户把 token 写入文件或命令历史；仅在当前进程中临时使用。

## 自动模式的授权边界

- 用户明确要求“创建广告 / 直接帮我创建”即授权本次完整新建链路中的必要创建写入（表单、Campaign、Ad Set、Creative、Ad）。无需在每个对象前重复询问。
- 自动模式以创建新对象为默认。若用户明确要求扩展指定的现有暂停广告组，可创建新广告；只有用户明确要求替换/更新某条现有广告时，才编辑该广告。不得改动其他对象或覆盖用户手工配置。
- 绝不因“自动创建”推定用户授权启动投放。所有新 Campaign、Ad Set、Ad 均创建为 `PAUSED`；不得自动修改账户花费上限或其他预算。
- 地区、预算、产品、表单目的或付费主体等缺少且会实质影响投放的信息时，只问必要问题。不得猜测预算或付费方。地区受限时移除并说明，不擅自换入其他国家。
- API 在创建过程中失败时，先查询是否已部分创建，再从最近已完成步骤安全恢复；不要因重试创建重复表单、Campaign、Ad Set、Creative 或 Ad。

## 执行顺序

1. **确认身份与资产**：检查 token 身份、有效权限、账户 ID、币种、账户状态、账户花费上限/已花费、主页和 Page Access Token、Lead Ads Terms、现有 Campaign/Ad Set/Ad。System User 有账户权限但未分配 Page 时，停止 Page 写入并指导用户在 BM 分配；BM 的资产可见不等于 token 主体具备 Page 权限。
2. **整理广告简报**：从用户提供的站点、产品资料和素材提取可核实事实，确认产品、买家、国家、预算、目标和语言。不得编造认证、产能、MOQ、性能、保证、价格、库存或制造商身份。
3. **核验定位与版位**：使用 Meta 当前定向搜索结果构造兴趣、行为和职位 ID；区分各条件组内 OR 与组间 AND。尊重用户指定的年龄、排除项及版位。对 API 返回的受限地区按原错误移除并告知。
4. **构建表单**：按当前 [b2b-ad-builder.md](b2b-ad-builder.md) 中的用户默认表单设置创建；调用 API 前核对字段顺序、required/optional、邮箱验证、表单类型、灵活投放和 Open 设置。隐私政策仅在 Meta 界面与 API 允许时省略；若强制要求，使用与实际数据流程一致的有效政策 URL，并指出此限制。获取并核对表单 ID、问题、联系信息、隐私 URL 和完成页。
5. **生成并检查素材**：为每个产品保留相符图片、产品页面、CTA 和表单，不把不同产品素材交叉混配。需要多个正文/标题/描述变体时，每类各 5 条，区分角度、以事实为依据，提交前检查 Unicode、长度和文本完整性。必要时生成多个产品 Creative；先检查预览。
6. **新建投放对象**：优先使用官方 Meta Business SDK；严格按 Campaign → Ad Set → Form/Creative → Ad 的依赖顺序创建。使用用户明确提供的预算层级和金额。明确指定的广告披露受益方和付费方应按实际信息填写，不得互相臆测。每个新对象设为 `PAUSED`。
7. **写后复核**：重读全部对象并逐项验证 ID、名称、层级关系、预算、国家、年龄、详细定位、版位、排除版位、付费方/受益方、Page、Form、CTA、图片/视频、正文/标题/描述及 `configured_status` / `effective_status`。检查创意预览及乱码/截断。`PENDING_REVIEW` 是等待审核，`IN_PROCESS` 是 Meta 处理，不是正常投放。
8. **回报结果**：简洁报告对象 ID、广告数量和产品、预算、定向、表单设置及每个对象状态；提供 Ads Manager 链接。明确广告是否仍暂停及任何受限地区、账户花费上限或审核处理状态。

## Token 与错误处理

- `ads_management`、`ads_read`、Page/Lead Ads 权限和 Business 资产分配按实际端点最小化检查。Developer app user token 与 System User token 使用同一 Graph API 验证流程，不因 token 类别而假设有更高权限。
- 不要求、不记录 App Secret。不要手工拼接包含 access token 的 URL，也不要将 token 写入脚本、报告、日志、diff 或最终回复；使用 SDK 的进程内凭据配置，或在直接 HTTP 请求时使用安全的 Authorization header。
- `(#10)`、`(#200)` 等权限错误需定位缺少的是 token scope、App Review/feature 还是具体资产分配；不能将 BM 级可见性解释为 Page 级可写权限。
- 写操作失败后先读回对象并核查部分结果，再决定是否继续；不要盲目重放 POST。
