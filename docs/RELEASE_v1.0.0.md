# 客行录 1.0.0 · 首个公开发行版

把走过的路、尝过的味道、看过的故事，留给以后的自己。

客行录是一款面向 Windows 的本地生活记录应用，将旅行日志、旅程票根、自由手账、食光小记与影视收藏放在一起。你可以用地图回看足迹，把票根变成弧形旅途轨迹，也可以打开全屏工作台，亲手排出一本可以翻页的电子手账。

**本版包含**

- 旅行日志与照片地图；飞机、高铁及火车票根自动生成轨迹。
- 自由编辑手账、素材拖放、自行导入图片、立体翻页与 HTML 导出。
- 食光小记和带自动轮播的影视收藏。
- 12 套主题、9 张内置背景和浮动毛玻璃导航。
- 本地数据保存；修复搬迁失败时仍切换目录的问题。

**下载与安装**

下载附件 `客行录-安装程序-1.0.0.exe`，退出旧版后安装。适用于 Windows 10 / 11 x64，内置 Python 和桌面运行组件；无需注册应用账号。桌面快捷方式默认勾选，可自行取消。

此前 2.x 是开发编号，本次 1.0.0 为首次公开发行，包含原有改进。旧用户可直接覆盖安装，数据目录保持兼容。安装包尚未做商业代码签名；附件 `SHA256SUMS.txt` 可用于核对文件。

记录保存在本机。天气、在线地图及可选 AI 识别会使用网络；AI 识别将所选截图发送给用户配置的服务。轨迹图用于纪念展示，不代表实际铁路线路或航路。完整说明见仓库 README 与数据使用说明。

---

# Kexinglu 1.0.0 · First public release

Keep the places you visit, the meals you enjoy, and the stories that stay with you.

Kexinglu is a Windows personal journal combining travel maps, flight and railway ticket keepsakes, freely editable scrapbooks, food memories, and an animated film collection. Create a book in a full-screen workspace, arrange text and imported images, turn its pages, and export it as a standalone HTML keepsake.

This release includes 12 themes, 9 built-in backgrounds, floating frosted-glass navigation, automatic ticket route diagrams, bundled desktop components, and safer data migration.

Download the `.exe` installer below for Windows 10 / 11 x64. No separate Python installation or app account is needed. The UI is primarily Simplified Chinese. Previous 2.x builds were internal development versions; 1.0.0 is the first public release and preserves their features and existing data compatibility.

The installer is not commercially code-signed. A SHA-256 checksum file is attached. Core records remain local; weather, online map tiles, and optional AI recognition use external services. Route diagrams are illustrative and must not be used for navigation.


## 发布前验证 / Validation

- 40 项自动测试通过 / 40 automated tests passed.
- 原生交互验证：票根、旅行地图、手账退出、影视自动轮播。
- 空配置与模拟证书失败条件下打包程序可正常启动。
- 隔离安装验证：文件占用时阻止覆盖、安装完整性、默认桌面快捷方式与卸载保留用户文件。

这些检查覆盖本机测试环境，不代表已经验证所有 Windows 设备配置。 / Validation covers the tested environment, not every Windows configuration.
