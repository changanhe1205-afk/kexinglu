# 鸿蒙发布依赖核对 · 2026-10-23

从本机已构建工程 pubspec.lock 提取。以下为依赖清单，不等于所有库都会独立向第三方发送数据；披露需结合实际调用。

| 依赖 | 锁定版本 |
|---|---|
| supabase_flutter | 2.18.3 |
| supabase | 2.16.5 |
| gotrue | 2.27.3 |
| flutter_secure_storage_ohos | 1.2.2 |
| flutter_geolocator_ohos | 1.0.1 |
| geocoding_ohos | 1.0.0 |
| image_picker_ohos | 0.8.13+7 |
| file_picker_ohos | 10.3.8 |
| sqflite | 2.4.2 |
| sqflite_ohos | 2.4.2 |
| app_links | 7.0.0 |
| url_launcher_ohos | 6.3.2 |
| path_provider_ohos | 2.2.17 |
| shared_preferences_ohos | 2.5.4 |

已发现需处理的实际问题：
- main.dart 在首次界面之前初始化 CloudAccount，初始化会访问服务商设置；尚未设置首次隐私确认流程。
- 当前账号注销依赖联系邮箱申请，未发现应用内自助注销入口；需要对照后台检测要求完善实际流程。
- Supabase 部署区域未能从项目核实，待项目设置确认。
- 平板镜像仅下载约 157 MB，未完成，不能视为平板系统验证通过。

网络服务：Supabase 账号和同步；Open-Meteo 天气和城市搜索；百度百科、维基百科、TVmaze 及结果图片地址用于海报。原生系统插件与云端服务需分别披露。
