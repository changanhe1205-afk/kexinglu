# 第三方登录 / Social sign-in

两端支持邮箱验证码、邮箱密码，以及后台启用的 GitHub、Google、Microsoft、Discord、GitLab OAuth 登录。客户端启动或打开账号页时读取 Supabase 的公开 `/auth/v1/settings`，只显示已启用的服务。无需把 Client Secret 放进客户端。

GitHub 在本次发布时已启用。其他服务的客户端流程已实现，但需要项目所有者各自注册 OAuth 应用并在 Supabase 启用；它们不是“无需配置即可使用”。服务商的配额和政策以其官方说明为准。

## 项目配置

各服务商的回调 URL：`https://czyuhzytkmgolncvfrbm.supabase.co/auth/v1/callback`。

Supabase → Authentication → URL Configuration → Redirect URLs：

- `com.changanhe.kexinglu://login-callback`
- `http://127.0.0.1:43821/callback**`

桌面回调仅监听本机 `127.0.0.1`，使用 PKCE 和独立随机 state；手机使用 PKCE 与应用深链接。Microsoft 请求 `email` scope。不同服务登录后应检查账号邮箱与同步结果，不要把不同身份误认为同一个资料库。

## 官方配置指南

- [GitHub](https://supabase.com/docs/guides/auth/social-login/auth-github)
- [Google](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Microsoft](https://supabase.com/docs/guides/auth/social-login/auth-azure)

## English

Both clients discover enabled providers from Supabase. GitHub is enabled for this release; Google, Microsoft, Discord and GitLab require separate provider setup by the project owner. OAuth client secrets belong only in the provider configuration, never in the app or repository. Email sign-in remains available. An authorization redirect check does not replace an end-to-end login with a real account.
