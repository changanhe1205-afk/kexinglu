# 客行录免费云端接入

当前 cloud.json 已接入项目 czyuhzytkmgolncvfrbm 的公开配置；2026-10-17 已确认初始化表和函数存在、匿名访问被拒绝，用户确认收到验证码邮件。登录后的双端同步与跨账号隔离仍待实测。

空配置时：不假装登录成功、不自动上传任何本地数据。代码包含邮箱密码、邮箱验证码、GitHub PKCE 登录及手动双向同步。QQ 仍未接通，不是可用登录方式。

## 1. 创建项目

在 https://supabase.com/dashboard 使用自己的账号创建 Free 项目，名称可填 kexinglu。数据库管理员密码使用页面自动生成并妥善保管，不要发给开发助手，也不要写入客户端。

## 2. 初始化数据库

项目 SQL Editor 中执行 cloud/migrations/001_sync.sql。它创建带账号隔离的记录表、原子版本更新函数、私有图片桶与按用户目录隔离的存储策略。发布前须用两个测试账号检查跨账号查询/下载均被拒绝；仅通过本地模拟传输测试不能证明线上 RLS 已生效。

## 3. 客户端公开配置

Project URL 和 Publishable key 属于客户端公开配置；不要使用 Secret key、service_role、数据库密码。将同一份配置写入 assets/cloud.json 和 mobile/assets/cloud.json：

```json
{"url":"https://YOUR_PROJECT.supabase.co","publishableKey":"sb_publishable_YOUR_PUBLIC_KEY","githubEnabled":false}
```

必须重新生成安装包。默认空配置会显示“云端尚未启用”。终端不可把密钥或密码直接输出到日志。

## 4. 邮箱与密码

Authentication → Providers 中启用 Email；保留邮箱验证。账号密码使用邮箱作为账号。密码至少 8 位，云端最低强度也设为至少 8 位。邮箱验证码验证后可在应用中设置/更新密码，因此忘记密码也可先验证邮箱。

邮箱模板需要包含 `{{ .Token }}` 以支持复制验证码；支持登录验证码与首次注册验证邮件。默认邮件服务仅限项目团队成员等测试用途，不能供所有用户正常收件。上线须配置自有 SMTP，免费额度、域名验证与限流由所选邮件服务决定，不能承诺无限免费邮件。

## 5. GitHub

在 GitHub Settings → Developer settings → OAuth Apps 创建应用。
- Homepage URL 可填项目 GitHub 仓库。
- GitHub Authorization callback URL：`https://YOUR_PROJECT.supabase.co/auth/v1/callback`。
- Client ID / Client Secret 只填入 Supabase 的 GitHub Provider；Client Secret 不能放客户端。
- Supabase Redirect URLs 添加 `com.changanhe.kexinglu://login-callback` 和 `http://127.0.0.1:43821/callback**`（桌面仅回环监听，随机 state + PKCE）。
- 完成真实授权测试后把 githubEnabled 改为 true。

GitHub 身份也归 Supabase 同一个账号系统；同一资料库禁止登录另一个账号后误上传。当前版不提供静默跨账号迁移。免费额度适合小规模使用，存储、流量和活跃用户以后台实际套餐限制为准。

## 6. QQ

尚未实现可用 QQ 登录。需要先获得 QQ 互联应用及相应配置，再设计服务器端身份验证和账号绑定，不能把 QQ 访问令牌当成 Supabase 会话，也不能在客户端保存 AppKey。未接通前仅显示状态说明。

## 7. 同步与限制

两端“账号与同步”→ 登录 →“同步当前资料库”→ 确认绑定与上传。同步旅行、票根、食光、影视和手账及图片；不会同步本机安装路径、密码、会话、桌面聊天记录或外观设置。桌面独有字段尽量保留在共同格式的扩展字段中。手账两端渲染器不同，字体、纸张及高级素材的视觉效果不保证逐像素一致。

同步是手动触发，尚未开启后台定时上传。修改冲突会保留本地与云端两个版本，当前不会自动合并，也没有完整的冲突选择界面。首次电脑同步前保留 SQLite 快照；手机请先导出本地备份。删除使用 tombstone，图片不会立即回收，以免另一台离线设备丢图。

部署前还需实测：同账号电脑与手机往返、图片/手账还原、两账号隔离、邮箱投递、GitHub 回调、登录过期和实际国内网络访问。未完成这些验证前不得对外宣称云同步已经上线。

参考：https://supabase.com/docs/guides/auth/auth-smtp 、https://supabase.com/docs/guides/auth/social-login/auth-github
