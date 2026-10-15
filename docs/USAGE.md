# 使用与数据说明 / Usage and data

## 开始记录

- **旅行日志**：记录地点、日期、文字与照片；地图不会因筛选列表而删除已有地点。通过“旅行手账”自愿创建一本手账，既可选择旅行记录，也可从空白页开始。
- **旅程票根**：分别使用“新增机票”“新增铁路票根”创建新记录；点击已有票根查看或编辑。保存后对应地图自动更新。缺少坐标会提示待定位，不会改变原始站名。
- **旅行手账**：创建后进入全屏工作台；拖入素材、自行导入贴图、调整文字与页面。退出时可选择保存或放弃修改，放弃不会覆盖原稿。导出的 HTML 手账包含所选内容，分享前请检查个人信息。
- **影视收藏**：录入作品与观后感后自动轮播；编辑、搜索或查看弹窗时暂停，以免打断操作。
- **我的**：选择主题、背景和存储位置。主题会同时更新页面、卡片、文字、表单与导航。

## 备份与迁移

先在“我的”中确认实际数据目录。退出应用后，将**整个数据目录**备份到另一处；不要只复制 SQLite 数据库，因为照片等文件另行存放。旧记录可能包含绝对路径，手动将备份改到不同目录不保证图片链接自动恢复；正常更换存储位置请使用应用内功能。

应用内搬迁采用复制方式，保留旧目录。如果目标数据库无法备份或有文件复制失败，新版不会切换到不完整的新目录。请在确认新位置正常后再自行清理旧文件。

安装目录与记录目录分离。更新、卸载应用不会主动删除记录；自定义目录与旧版“影笺录”目录可能继续被使用。

## 网络与隐私

| 功能 | 联网行为 |
| --- | --- |
| 日志、票根、食物与影视记录 | 保存到本地 SQLite 和文件目录；没有云同步。 |
| 天气 | 请求 IP 定位和 Open-Meteo 天气服务；服务商会收到请求和相关位置参数。 |
| 在线旅行地图 | 请求地图瓦片，服务商会收到请求及地图区域参数。 |
| 票根轨迹示意图 | 使用内置离线底图与地点坐标。 |
| AI 截图识别 | 用户配置并发起识别后，将所选图片发送至其配置的 OpenAI 兼容服务；应先了解服务商的数据处理规则。 |

AI 配置文件 `ai_config.json` 中的 API Key 未加密。数据备份可能同时包含行程、照片、证件信息和密钥，请妥善保管，不要发到公开仓库。开发仓库的忽略规则排除了本地数据库、配置、日志与构建产物。

## 已知边界

- 首个公开发行版以 Windows x64 和中文界面为主；没有承诺 macOS/Linux 兼容或完整英文界面。
- 轨迹为起终点之间的艺术化弧线，不表示真实列车经过的线路或飞行航路。
- 地点库为离线快照，不能覆盖所有车站、机场或未来新建站点。
- 网络服务异常可能影响天气、地图瓦片与 AI 识别，但不应阻止核心应用启动。
- 安装包未做商业代码签名；SHA-256 校验只能核对文件一致性，不能代替发布者签名。

## English summary

Back up the **entire data folder with the app closed**. Images are stored separately from the database, and some records use absolute paths; use the in-app migration function when changing storage location. The original directory is retained after migration. Incomplete copies do not activate the new directory.

Core records are local. Weather/location services, online map tiles, and optional AI recognition make network requests. AI screenshots go to the user-configured service, and the API key is stored locally without encryption. Do not include personal backups or credentials in public issue reports.
