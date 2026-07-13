# YT Downloader by Panes & Pixels 🎬🚀

A premium, standalone Windows desktop application designed to scrape and download **YouTube Shorts** and **Instagram Reels** in high quality. Built with a stunning **Catppuccin Mocha** dark aesthetic, fluid page animations, a local encrypted credentials manager, and custom installer packaging.

---

## ✨ Features

- **Dual-Platform Dashboard:** Unified launcher cards to toggle between the YouTube Shorts Downloader (Crimson Red) and Instagram Reels Downloader (Pink/Magenta).
- **YouTube Shorts Scraper:** Input a channel handle, retrieve and sort the top 100 Shorts by view count, and batch-download the best performing videos.
- **Instagram Reels Downloader:** Seamlessly fetch and download public Reels by URL.
- **Interactive Instagram Login & 2FA:** Supports logging in to Instagram accounts directly inside the app to bypass rate limits. Fully supports Two-Factor Authentication (2FA) prompts.
- **Local Credentials Encryption:** User credentials are encrypted at the OS-level using **Windows Data Protection API (DPAPI)** and stored locally in `~/.yt_shorts_downloader_insta`, ensuring only the active Windows user can access them.
- **Multi-layered Cookie Fallback:** 
  1. Utilizes active Instaloader session.
  2. Falls back to a local `cookies.txt` file.
  3. Extracts active session cookies directly from local browsers (Chrome, Edge, Firefox, Brave, Vivaldi, Opera).
- **Control Panel Integration:** A complete custom GUI installer and uninstaller registered directly in the Windows Control Panel ("Programs and Features").

---

## 🛠️ Technology Stack

- **GUI Framework:** Python + [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Downloader Engine:** [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [Instaloader](https://github.com/instaloader/instaloader)
- **Encryption:** Native Windows Data Protection API (`crypt32.dll` via `ctypes`)
- **Compilation:** PyInstaller (compiled under folder-mode `--onedir` for instant startup)

---

## 🚀 Getting Started

### Method 1: Using the Standalone Installer (Easiest)

1. Download the latest installer `YT_Downloader_Setup.exe` from the [Releases](https://github.com/YOUR_USERNAME/YOUR_REPO/releases) page.
2. Double-click the installer and follow the GUI wizard to select an installation folder and create shortcuts.
3. Launch the app from the Desktop or Start Menu!
4. *To uninstall, simply go to your Windows Settings -> Apps & Features -> Search "YT Downloader by Panes & Pixels" and click Uninstall.*

### Method 2: Running from Source

If you want to run or modify the application locally:

#### Prerequisites
Ensure you have Python 3.10+ installed on your Windows machine.

#### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

#### Compiling to Executable
To build the standalone executable and the setup wizard yourself, run:
```bash
python build.py
```
The compiled output will be generated inside the `dist/` directory as `YT_Downloader_Setup.exe`.

---

## 🔒 Security & Privacy

This application values user privacy:
- Your Instagram credentials are **never** transmitted to any third-party servers.
- Encryption keys are managed by Windows (DPAPI) and tied directly to your active Windows user profile. Other users on the same computer cannot decrypt or read your saved login session.

---

## ⚖️ Legal Disclaimer

This tool is created for educational and archival purposes. Users are solely responsible for ensuring they comply with YouTube's and Instagram's Terms of Service and respect copyrighted material.

*Copyright © 2026 Panes & Pixels. All rights reserved.*
