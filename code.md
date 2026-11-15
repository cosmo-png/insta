# Instagram Profile Downloader

Downloads all images, videos, and Reels from an Instagram profile URL.

## Features
- Downloads Reels, Videos, and Images.
- Handles Carousels (downloads all slides in a carousel as separate images).
- Infinite scroll to capture old posts.
- Works for Public profiles out-of-the-box.
- Supports Private profiles if you provide session cookies.

## Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. Run the script:
   ```bash
   python main.py <username>
   # OR just run python main.py and enter the username interactively
   ```

## Notes
- **Private Profiles:** If the profile is private, the script will open a browser window. Log in manually, then press Enter to continue scraping.
- **Rate Limits:** Instagram may block aggressive scraping. This script includes delays.
- **Headless Mode:** Change `headless=False` to `True` in `main.py` if you don't want to see the browser window.