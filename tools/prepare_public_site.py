"""Prepare an allowlisted public download site, never copy tools or credentials."""
from pathlib import Path
import shutil
import re

ROOT=Path(__file__).resolve().parents[1]
site=ROOT/'website'
support=site/'assets/support-wechat.png'
shutil.copyfile(Path('D:/Users/chang/Downloads/微信图片_20261019224858_101_8.png'), support)
(ROOT/'docs/support').mkdir(parents=True,exist_ok=True)
shutil.copyfile(support,ROOT/'docs/support/wechat.png')
page=(site/'index.html').read_text('utf-8')
base='https://github.com/changanhe1205-afk/kexinglu/releases/latest/download/'
page=page.replace('downloads/Waylore-Windows-1.0.1.exe',base+'Kexinglu-Setup-1.0.0.exe')
page=page.replace('downloads/Waylore-Android-1.0.0.apk',base+'Kexinglu-Android-1.0.0.apk')
page=page.replace('1.0.1','1.0.0').replace(' · 82.2 MB','').replace(' · 23.4 MB','')
page=page.replace('数据只在你手里。','本地保存，同步由你决定。').replace('本地优先 · 数据只在你手里','本地优先 · 自由记录')
page=page.replace('一键导出包含照片的 JSON 备份，换设备或重装都能导回。','支持本地备份与恢复。换设备前先导出备份，并确认照片与记录完整。')
page=page.replace('覆盖安装会保留原有资料；安装包固定同名，重新生成时直接覆盖。','两端版本均为 1.0.0。已有用户直接覆盖安装，无需卸载；更新前建议保留一份备份。')
# Download cards now contain platform-specific links; preserve their contents.
page=page.replace('      <a href="#privacy">隐私</a>', '      <a href="#privacy">隐私</a>\n      <a href="#support">支持</a>')
page=page.replace('    <a class="btn btn-small"', '    <a class="language-link" href="en.html" lang="en">EN</a>\n    <a class="btn btn-small"',1)
if 'id="support"' not in page:
    page=page.replace('  </main>', '''    <section id="support" class="section support-section">
      <div><p class="eyebrow">MADE WITH CARE</p><h2>如果它陪你记住了<br>一些美好的日子。</h2>
      <p class="section-sub">客行录免费提供使用。你的反馈、一个 Star，或一份随心的赞赏，都是继续打磨它的动力。</p>
      <p>赞赏完全自愿，不解锁功能，也不影响任何人的正常使用。谢谢你，让这个小作品走得更远。</p>
      <a class="btn btn-ghost" href="https://github.com/changanhe1205-afk/kexinglu" target="_blank" rel="noopener">在 GitHub 留下一个 Star ↗</a></div>
      <figure class="support-code"><a href="assets/support-wechat.png" target="_blank" rel="noopener"><img src="assets/support-wechat.png" alt="开发者的微信赞赏码，点击查看原图" loading="lazy" width="1229" height="1229"></a><figcaption>微信扫一扫 · 随心支持开发者</figcaption></figure>
    </section>
  </main>''')
page=re.sub(r'(\s*<a href="#support">支持</a>)+', '\n      <a href="#support">支持</a>', page)
page=re.sub(r'(\s*<a class="language-link" href="en.html" lang="en">EN</a>)+', '\n    <a class="language-link" href="en.html" lang="en">EN</a>', page)
(site/'index.html').write_text(page,encoding='utf-8')
privacy=(site/'privacy.html').read_text('utf-8').replace('和风天气（QWeather）','Open-Meteo').replace('和风天气','Open-Meteo')
privacy=privacy.replace('两者仅接收','服务仅接收')
(site/'privacy.html').write_text(privacy,encoding='utf-8')
css=(site/'styles.css').read_text('utf-8')
if '.support-section' not in css:
    css+='''\n.support-section{display:grid;grid-template-columns:1.4fr 1fr;gap:70px;align-items:center;border-top:1px solid var(--line)}
.support-section h2{font-family:var(--serif);font-size:clamp(30px,4vw,48px);font-weight:500;line-height:1.5}
.support-section p{max-width:560px;color:var(--muted)}
.support-code{margin:0;max-width:320px;justify-self:center;text-align:center}
.support-code img{width:100%;height:auto;border-radius:18px;box-shadow:var(--shadow)}
.support-code figcaption{font-size:12px;color:var(--muted);margin-top:14px}
.language-link{font-size:13px;padding:8px}
@media(max-width:700px){.support-section{grid-template-columns:1fr;gap:32px}.support-code{max-width:250px}.hero-art{order:0}.hero-copy{order:-1}}
'''
(site/'styles.css').write_text(css,encoding='utf-8')
out=ROOT/'site-public/dist';out.mkdir(parents=True,exist_ok=True)
for name in ('index.html','en.html','privacy.html','styles.css','app.js'):
    if (site/name).exists():shutil.copyfile(site/name,out/name)
shutil.copytree(site/'assets',out/'assets',dirs_exist_ok=True)
print('Public static files prepared; installation files are served by GitHub Releases.')
