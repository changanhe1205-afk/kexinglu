# 客行录 · Android 1.0.1 交互体验版

使用 Flutter / Dart 原生绘制界面，免费本地编译 APK，无需购买 HBuilder X 云打包服务。手机端项目独立放在 mobile 中，Windows 版保持不变。

## 当前功能

- 五个手机导航页面：主页、旅途、票夹、收藏、我的；浮动毛玻璃导航、12 种主题和减少动效选项。
- 旅行日志、离线地图、地点记录与照片；飞机/铁路票根自动坐标匹配、弧线轨迹、滑动票夹与点击翻面。
- 六种手账款式，空白/单次旅行/全部旅行任选建册；全屏编辑、文字、42 种符号贴纸、导入图片、素材拖放、双指缩放旋转、左右翻页和 HTML 分享。
- 食光小记、影视收藏；影视卡片轮播、触摸暂停、后台暂停。
- 应用私有目录中的 SQLite 和照片；JSON 备份导入/导出，备份包含图片。

## 使用与数据

这是首个 Android 体验版，不代表 Windows 全部细节已逐项移植。手机版数据独立保存，不支持直接导入桌面 SQLite。1.0.1 已加入邮箱密码、验证码、GitHub 登录与手动云同步代码，但默认云配置为空，尚未上线；配置与联调步骤见 ../cloud/SETUP.zh-CN.md。QQ 登录尚未接通。离线站点库并非全球所有站点；无法匹配的起终点会显示未匹配提示。票根图形与条码用于记录，不作为乘车、登机凭证。

卸载前请在“我的”导出备份，并确认文件已保存到应用外的文件夹。Android 默认系统备份关闭；重新安装后的恢复使用应用备份。未开启同步时图片与位置保存在本地；登录并确认同步后会上传至该账号的私有云端空间。

## 免费开发工具

本机 Flutter：D:/Tools/flutter；Android SDK：D:/Tools/android-sdk；JDK：D:/Java/jdk-21.0.10。可使用 VS Code 打开本目录；无需安装付费插件。首次构建需联网下载依赖，构建后应用的现有核心功能可离线使用。

PowerShell 在 mobile 目录：

```powershell
$env:PUB_CACHE='D:/Tools/pub-cache'
$env:TEMP='D:/Tools/tmp'
$env:TMP='D:/Tools/tmp'
$env:JAVA_HOME='D:/Java/jdk-21.0.10'
$env:ANDROID_HOME='D:/Tools/android-sdk'
& D:/Tools/flutter/bin/flutter.bat pub get
& D:/Tools/flutter/bin/flutter.bat analyze
& D:/Tools/flutter/bin/flutter.bat test
& D:/Tools/flutter/bin/flutter.bat build apk --release --target-platform android-arm64
```

发布签名配置位于被 Git 忽略的 android/key.properties，私钥在项目目录之外保管。后续覆盖安装必须使用同一私钥与包名，并递增 pubspec.yaml 的 build number。不要上传签名文件和密码。

## 验证范围

自动化测试覆盖离线站点、编辑草稿隔离、票根日期与航班号保存、退出编辑、手账拖动、备份合并和损坏文件拒绝。测试使用独立内存数据，不读取桌面用户数据库。

本项目尚未在用户的红米 K90 至尊版上实测；真机性能、系统照片选择器和分享目标需以实际手机测试为准。

1.0.1 导航修复：主页面导航独立悬浮、安全区留白、半透明渐变毛玻璃、阴影与深色适配。11 项 Flutter 测试通过；同步适配层 10 项离线测试通过。真实云端邮箱投递、OAuth 授权、RLS 与两端同步仍待配置项目后验证。
