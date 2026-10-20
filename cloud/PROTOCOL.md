# 客行录同步协议 v1

认证采用 Supabase Email OTP（邮箱验证码）。两端使用相同项目 URL 和 publishable/anon key，绝不嵌入 service_role 或 secret key。启用邮箱注册、邮件模板使用 `{{ .Token }}`，配置自有 SMTP；默认邮件服务不能向任意用户发信。

记录拥有全局 UUID、kind、data、revision、deleted。owner_id 来自经过验证的登录令牌，由数据库函数填入。客户端不能指定账号、修改服务端时间或绕过版本检查。每条记录以 expected_revision 做原子比较更新；删除是永久保留的 tombstone。客户端只有读取表和调用 RPC 的权限。

同步元数据按账号绑定本地资料库。首次同步明确确认上传本地资料；已有绑定不允许换账号混入。退出登录不删除本地资料，也不会把它传给下一个账号。账号切换需要独立资料库，当前版本不静默迁移。

每轮同步先枚举本地快照，与上次确认的哈希比较，再上传变更，最后下载远端变化。远端冲突不覆盖：保留待处理本地版本并报告冲突，用户明确选择后再同步。应用过程中如果本地已再次变化，跳过该记录，下轮重试。失败不推进版本、不删除本地记录。下载完整且媒体通过哈希校验后再提交本地事务。

所有媒体放入私有 journal-media bucket，以 `<auth.uid>/<sha256>.<extension>` 命名。文档只存 `{"$asset":"<sha256>.<extension>"}`；上传、下载均需登录，禁止公开 URL 和任意路径。单图限制 10 MiB，记录 JSON 限制 5 MiB。第一次上传可能较慢，之后相同图片按哈希去重。

共同字段：movie(title,category,date,rating,note,image)，food(title,place,date,price,rating,note,image)，travel(title,city,date,rating,note,image,photos,lon,lat)，ticket(mode,from,to,date,code,seat,passenger,price,note,image)。桌面独有字段置于 `_desktop`，手机修改时保留。手账必须保留桌面原始文档及手机表示，不能直接用另一端的 JSON 覆盖原文档。

部署前必须以两个测试账号验证 RLS、私有图片隔离、令牌过期、离线修改、并发更新、删除重试和两端真实数据往返。未配置云项目时只显示“云端尚未启用”，保留所有本地功能。
