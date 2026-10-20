# Linux 1.0.0

首批发布面向 **Ubuntu 22.04 及更新版本，x86_64 / amd64**。不是 ARM 包；其他 Linux 发行版尚未逐一验证。

## 安装

下载 `Kexinglu-Linux-1.0.0-amd64.deb`，在下载目录运行：

```bash
sudo apt install ./Kexinglu-Linux-1.0.0-amd64.deb
```

安装后在应用菜单搜索「客行录」或「Waylore」。首次安装系统依赖需要联网，核心记录功能离线可用；天气、登录与同步需要联网。

不想安装时，可解压 `Kexinglu-Linux-1.0.0-x86_64.tar.gz`，进入目录执行 `./kexinglu`。便携包同样需要 GTK 3、libsecret、libayatana-appindicator3、OpenGL 和 xdg-utils 系统库。

## 数据与升级

- 资料默认保存于 `~/.local/share/kexinglu`，设置在 `~/.config/kexinglu`，遵循对应 XDG 环境变量。
- Linux 使用电脑版的资料结构、邮箱/GitHub 登录和同步。既有账号可登录后同步，迁移前请保留原设备备份。
- 更新 DEB 或替换便携程序目录不会主动删除个人数据。不应使用 root 启动应用。
- 界面跟随桌面缩放；文件/图片导出通过系统默认应用打开。

## 构建与验证

GitHub Actions `Linux desktop build` 在 Ubuntu 22.04 上构建 PyInstaller 与 Flet 本地运行组件，产出 DEB、TAR.GZ，并用独立 HOME 和 Xvfb 检查成品能打开原生窗口。发布前需通过该检查。

Waylore for Linux targets Ubuntu 22.04+ x64. Personal data stays outside the installation directory. ARM and other distributions are not yet verified.
