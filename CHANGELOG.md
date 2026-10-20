# 更新记录 / Changelog

## 1.0.0 · 平板与 Linux — 2026-10-20

- 安卓手机和平板共用一个 APK：大屏首页双栏，旅途/票夹左侧记录、右侧地图。
- 适配横竖屏、分屏窗口、手势安全区；浮动毛玻璃导航居中，编辑框及候选栏限制宽度。
- 修复公开天气接口湿度被重复乘以 100 的显示问题。
- 新增 Ubuntu 22.04+ x64 的 DEB 与便携 TAR.GZ，内置 Python/Flet 运行时，采用 XDG 资料目录。
- Linux 图片和导出文件使用系统默认应用打开；官网新增中英文 Linux 下载入口。

## 1.0.0 · build 25 — 2026-10-20

- 发布 Android 客户端，保留浮动导航、手账、地图、个人资料和生日祝福。
- 修复手机旅途与票夹地图缩放时轨迹、图标和文字比例不协调。
- 两端接入 GitHub OAuth；其他第三方入口仅在服务端启用后显示。
- 增加英文、日文和繁体中文常用界面翻译；高级编辑文案仍在逐步补齐。
- 发布中英文下载网站及自愿赞赏说明。
- 移除移动端内嵌天气私钥，改用公开天气接口。

Android build 25 joins Windows 1.0.0 with map zoom fixes, GitHub sign-in, UI language options, birthday greetings and a bilingual download website. Some advanced editor text remains in Chinese.

## 1.0.0 — 2026-10-15

首个公开发行版。此前 2.x 为开发迭代编号；本次统一为 1.0.0，保留现有功能、安装标识和用户数据格式。

- 旅行日志与地图、机票及铁路票根、自动弧形轨迹。
- 全屏自由手账工作台、素材拖放、自定义图片、翻页阅读与 HTML 导出。
- 食光小记、影视收藏与自动轮播。
- 12 套完整主题、9 张内置背景与浮动毛玻璃导航。
- 内置机场、铁路站点坐标及 HTTPS 根证书，打包完整桌面运行组件。
- 修复数据搬迁部分文件复制失败后仍切换目录，以及目标数据库备份失败后继续覆盖的问题。
- 补齐 pypinyin 依赖，固定已验证的运行与构建版本，加入源码发布忽略规则、中英文说明和数据使用说明。

First public release. Previous 2.x identifiers were development builds. This release brings the existing journaling, tickets, route maps, scrapbook editor, food memories, film collection, and appearance options together under version 1.0.0. It also prevents incomplete data migrations from switching the active folder and pins the verified dependency set.
