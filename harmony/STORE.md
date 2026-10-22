# 客行录 · 鸿蒙 1.0.0 上架材料草稿

当前交付为原生 HarmonyOS 手机/平板工程与 AppGallery 商店包。尚未提交审核，以下介绍不得表述为已经上架。包名：`com.changanhe.kexinglu`，公开版本：`1.0.0`，内部版本：`1`。

公开用户支持/隐私联系邮箱：`kexinglu@yeah.net`。隐私政策：<https://waylore-kexinglu.fonddill9.chatgpt.site/privacy.html>。

## 中文简介

把走过的路、尝过的味道、看过的故事，留给以后的自己。

客行录是一款本地优先的旅行与生活记录应用。用照片和文字留下旅途，把机票与铁路票根收藏成地图上的轨迹，亲手排版一本可以翻页的旅行手账，也为喜欢的餐食、电影与剧集留下一页。

- 旅行日志：按地点整理故事与照片，在地图上回看走过的地方。
- 旅程票根：收藏机票与铁路票根，根据已识别的机场、车站坐标生成纪念轨迹。
- 自由手账：组合照片、文字和素材，自由排版、翻页浏览。
- 食光与影视：记录餐食、评分和观看感悟。
- 个性外观：选择主题与背景，保留轻盈的浮动导航。
- 可选账号：本机记录无需登录；需要跨设备同步时再登录自己的账号。

轨迹地图用于回忆与展示，不提供实际交通路线或导航。

## English description

Keep the places, flavors and stories that make a life.

Kexinglu is a local-first travel and lifestyle journal for HarmonyOS phones and tablets. Save journeys with photos and notes, collect flight and railway tickets, arrange a personal scrapbook, and remember favorite meals, films and shows. Optional account sign-in connects your records across devices. Core local recording works without an account.

Ticket routes are illustrative keepsakes, not transport schedules or navigation guidance.

## 审核操作说明草稿

1. 无需注册账号，打开应用后可直接进入“旅途”，点击右上角加号新增地点与文字并保存。
2. “票夹”提供机票与铁路票根创建入口。轨迹需要可定位的起终点；未识别地点不应被描述为精确航路。
3. 地图右下角进入全屏，可拖动、缩放并切换方向。
4. “我的”可调整主题、资料与背景；账号登录及同步是可选功能。
5. 位置权限用于当地天气，拒绝后可手动选择城市。照片通过系统选择器导入，网络用于天气、海报与可选同步。

提交前需以最终安装包核对所有描述，补充手机/平板真实截图、公开隐私政策与有效联系渠道，并在后台完成实际要求的应用分类和开发者资料。现有网站隐私文本仍需与最终联网功能逐项核对。

## 交付边界

- `.app` 是 AppGallery 上传包，不是普通用户点击安装的文件。
- Release Profile、私钥、签名密码和本机签名配置不进入仓库或公开附件。
- 只有完成审核后才添加真实应用市场安装链接；此前网站展示开发状态。
- 升级保留资料；不得要求用户通过卸载或清除数据完成升级。
