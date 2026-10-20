# Waylore download website

Public website: https://waylore-kexinglu.fonddill9.chatgpt.site

Chinese and English static pages. Both clients use version 1.0.0. Downloads point to GitHub Releases: Kexinglu-Setup-1.0.0.exe, Kexinglu-Android-1.0.0.apk and SHA256SUMS.txt.

Run tools/prepare_public_site.py to prepare the allowlisted static files for Sites hosting. Never publish private keys, databases or local configuration.

Local preview: python -m http.server 8788 --bind 127.0.0.1
