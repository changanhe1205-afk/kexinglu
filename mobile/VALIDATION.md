# Android 体验版验证记录

日期：2026-10-16。版本 1.0.0+1，包名 com.changanhe.kexinglu，最低 API 24，target API 36。

- Flutter analyze：No issues found。
- Flutter test：9 项通过；视觉截屏专用测试默认跳过，另行开启后通过。
- APK：Release 构建，固定 RSA 3072 私钥，APK v2 签名验证通过。签名证书 SHA256：64393e3dc8ada8a02bbfe69b50408de9c59651488efc21273541fed72fd15f21。
- Android 16 / API 36 x86_64 模拟器：实际安装成功；冷启动成功；无 E/flutter 或 FATAL EXCEPTION 记录（所检日志窗口）。
- 手动 UI 自动操作：新增 PEK → XUZ 机票，航班 CA1234、CNY 580；保存后显示 1 张票根、1 条轨迹；前后翻面正常。
- 强制停止应用后重新启动，航班、票价和轨迹均保留。
- 真实安卓页面截屏保存在 design/verification/mobile-native-*.png。所有测试记录只存在 QA 模拟器，与桌面真实数据库隔离。

限制：尚未连接红米 K90 至尊版，未实测其刷新率/帧率、系统相册和分享目标；这不是完整的桌面功能一致性认证。手机与桌面尚无数据同步。发布文件是已安装验证的同一份多架构 APK，适用于 ARM64 手机及 x86_64 模拟器。

## 1.0.1 / 2026-10-17

- 独立悬浮导航、半透明渐变毛玻璃与阴影；五个页面、深色主题和底部 48 px 安全区测试通过。
- Flutter analyze 无问题；11 项功能测试通过，截图专用测试默认跳过。
- Python 同步适配层 10 项隔离测试通过（模拟传输，非线上服务）。
- 安卓 API 36 模拟器上从 1.0.0 覆盖安装到 1.0.1 成功，原 CA1234 / CNY 580 票根与轨迹保留。实际截图：design/verification/mobile-101-tickets.png。
- 空云配置时，账号页明确显示未启用并禁用登录；无假会话、无上传。邮箱、GitHub、线上 RLS 和跨设备同步仍待真实项目联调。QQ 未接通。电脑端只更新源码，尚未重发 Windows 安装包。
- APK 包名保持 com.changanhe.kexinglu，versionCode 2，同一 RSA 签名验证通过。
- 交付 APK SHA256：472b97268251c902150d8f874a2e87521dffac366d0636dd993ee9b3d87efa5a。
