# 客行录 macOS 1.0.0 · 发布准备

目标仅为 Mac 电脑，iPhone/iPad 不在此次范围。macOS 允许从官网获取应用。当前没有完成构建、测试或签名的 macOS 安装包，不得增加有效下载按钮或宣称已经发布。

现有桌面工程为 Python/Flet，Windows spec 含绝对 Windows 路径，不能直接用于 Mac。需在 macOS 上重新收集 Flet 原生客户端、打包 .app，验证本地数据路径、证书、窗口行为、登录回调、地图及导入导出。分别核对 Apple Silicon 和 Intel 架构，避免把单架构包标为通用包。

正常公开分发路径：Mac 构建与测试 → Developer ID 签名 → Apple 公证与票据附加 → 校验最终归档 → GitHub 与官网。会员/证书尚待用户确认。不能公开私钥或要求用户关闭系统安全保护。

官方依据：
https://support.apple.com/zh-cn/102445
https://developer.apple.com/help/glossary/developer-id-certificate/
https://pyinstaller.org/en/latest/
