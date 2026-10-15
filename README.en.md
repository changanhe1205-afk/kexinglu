<div align="center">

<img src="assets/app.png" width="88" alt="Kexinglu logo" />

# Kexinglu · 客行录

**Keep the places you visit, the meals you enjoy, and the stories that stay with you.**

A personal Windows journal for travel, ticket keepsakes, creative scrapbooks, food memories, and films. Designed around local storage, gentle motion, and a floating frosted-glass navigation bar.

[Download v1.0.0](https://github.com/changanhe1205-afk/kexinglu/releases/tag/v1.0.0) · [简体中文](README.md)

</div>

## Preview

Screenshots use synthetic demo records, not personal data.

![Travel tickets and automatic routes](docs/images/release-tickets.png)

![Travel journal](docs/images/release-travel.png)

## Features

- **Travel journal:** collect notes and photos by place; revisit trips on a map with trackpad panning and zooming.
- **Ticket keepsakes:** save flight and railway tickets, choose designs, view both sides, and automatically draw curved routes from saved tickets.
- **Creative scrapbooks:** create a blank book or arrange selected travel memories. Edit full screen, drag text and stickers onto pages, import your own images, choose covers, turn pages, and export a standalone HTML book.
- **Food memories:** keep restaurants, dishes, photos, and personal impressions together.
- **Film collection:** record films and series, posters, ratings, and reviews, with an animated display and automatic rotation.
- **Personal appearance:** 12 themes, 9 built-in backgrounds, and custom background imports.

The bundled ticket data offers 41 airline choices, coordinates for 140 airports and 2,917 railway stations. Routes are commemorative diagrams, not actual flight paths, railway alignments, or navigation instructions. Some locations fall back to an approximate city position or remain unresolved.

## Install

Download `客行录-安装程序-1.0.0.exe` from [Releases](https://github.com/changanhe1205-afk/kexinglu/releases). Close the app before installing. A desktop shortcut is selected by default and can be disabled in the installer.

The package targets **Windows 10 / 11 x64** and includes Python and the desktop runtime. No app account or separate Python installation is required. Core journaling works offline. The application interface is primarily Simplified Chinese; this English introduction does not imply full English UI localization.

This release is not commercially code-signed, so Windows may show an unknown-publisher prompt. Download checksums are provided in `SHA256SUMS.txt`.

Earlier `2.x` numbers were internal development iterations. **1.0.0 is the first public release**, retains those improvements, and keeps the existing installer identity and data format. Existing users can install over their previous version. Uninstalling the application does not intentionally delete personal records.

## Data and network access

Records and images are stored locally, with no application account or cloud sync. The default data directory is `%LOCALAPPDATA%\客行录`; existing installations may use a legacy or custom folder. Settings are in `%APPDATA%\客行录\settings.json`.

Weather, IP-based city lookup, and online map tiles contact external services. Optional AI ticket recognition sends the selected screenshot to the provider configured by the user. Its API key is stored locally without encryption. Keep personal data and credentials out of public backups and issue reports. See [data and usage notes](docs/USAGE.md).

## Development

Verified with **Python 3.14 x64 and Flet 1.0.1** on Windows.

```powershell
git clone https://github.com/changanhe1205-afk/kexinglu.git
cd kexinglu
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Initial dependency and desktop-runtime setup requires internet access. Development settings are separate from installed-app settings; the default development data folder is `data/`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe build.py
# Install Inno Setup 6 with ChineseSimplified.isl, then:
.\.venv\Scripts\python.exe build_installer.py
```

Set `INNO_SETUP_DIR` if the compiler is not in a standard location. Runtime dependencies are pinned to the versions tested for this release. Native UI tests need an interactive Windows desktop.

## Feedback

Please open an [issue](https://github.com/changanhe1205-afk/kexinglu/issues) with the app version, Windows version, and steps to reproduce. Redact personal details from screenshots; do not upload databases or API keys. Data provenance is documented in [third-party notices](THIRD_PARTY_NOTICES.md).
