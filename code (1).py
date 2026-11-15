import asyncio
import os
import time
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

class InstaDownloader:
    def __init__(self, username, output_dir="downloads"):
        self.username = username
        self.base_url = f"https://www.instagram.com/{username}/"
        self.output_dir = Path(output_dir) / username
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_ids = set()
        self.session_cookies = None

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Set to True if you want no UI
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        
        # Optional: Load cookies if you have them for private profiles
        if self.session_cookies:
            await self.context.add_cookies(self.session_cookies)

    async def stop_browser(self):
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def login_if_needed(self):
        """If private, you might need to log in manually or pass cookies."""
        print(f"[+] Navigating to {self.base_url}")
        await self.page.goto(self.base_url, wait_until="networkidle")
        
        # Check if we are on a login page or blocked
        if "login" in self.page.url:
            print("[!] Login required. Please log in manually in the browser window.")
            print("[!] Press Enter when ready...")
            input()
        
        # Wait for grid to load
        try:
            await self.page.wait_for_selector('div[role="grid"]', timeout=15000)
        except PlaywrightTimeout:
            print("[-] Could not find post grid. Profile might be private or URL invalid.")
            return False
        return True

    async def extract_post_data(self):
        """Extract media URLs from the current DOM state."""
        # We look for image/video tags within the grid items
        posts = await self.page.query_selector_all('article')
        data = []
        
        for post in posts:
            try:
                # Get shortcode (unique ID)
                href = await post.get_attribute('href')
                if not href: continue
                
                shortcode_match = re.search(r'/p/([A-Za-z0-9_-]+)/', href)
                if not shortcode_match: continue
                
                shortcode = shortcode_match.group(1)
                
                if shortcode in self.downloaded_ids:
                    continue

                # Try to find video src first, then image src
                video_src = await post.locator('video').get_attribute('src') if await post.locator('video').count() > 0 else None
                
                # For images/carousels, we often need to click to see all assets, 
                # but for bulk download, we can try to grab the direct link from the initial load
                # Instagram embeds JSON in <script> tags. Let's try that first for accuracy.
                
                # Fallback: Direct locator search
                img_src = await post.locator('img').first.get_attribute('src') if await post.locator('img').count() > 0 else None
                
                if video_src:
                    data.append({'type': 'reel', 'url': video_src, 'id': shortcode})
                elif img_src:
                    data.append({'type': 'image', 'url': img_src, 'id': shortcode})
                    
                self.downloaded_ids.add(shortcode)
                
            except Exception as e:
                continue
                
        return data

    async def scroll_and_download(self):
        """Infinite scroll until no new content loads, then download."""
        last_height = 0
        scroll_count = 0
        max_scrolls = 50 # Safety break
        
        print("[+] Starting infinite scroll...")
        
        while scroll_count < max_scrolls:
            await self.page.mouse.move(100, 100) # Move mouse to avoid hover triggers
            await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
            
            # Wait for new content to load
            await asyncio.sleep(2)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                # No new content loaded
                break
            
            last_height = new_height
            scroll_count += 1
            print(f"[+] Scrolled {scroll_count} times...")

        print("[+] Scroll finished. Extracting links...")
        posts_data = await self.extract_post_data()
        print(f"[+] Found {len(posts_data)} unique posts.")
        
        return posts_data

    async def download_file(self, url, filename):
        """Download a single file using requests (faster than playwright for pure download)."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: __import__('requests').get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
            )
            if response.status_code == 200:
                filepath = self.output_dir / filename
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[+] Downloaded: {filename}")
                return True
            else:
                print(f"[-] Failed to download {filename}: {response.status_code}")
                return False
        except Exception as e:
            print(f"[-] Error downloading {filename}: {e}")
            return False

    async def run(self):
        await self.start_browser()
        try:
            if await self.login_if_needed():
                posts = await self.scroll_and_download()
                
                if not posts:
                    print("[-] No posts found.")
                    return

                print(f"[+] Starting download of {len(posts)} items...")
                for i, post in enumerate(posts):
                    ext = "mp4" if post['type'] == 'reel' else "jpg"
                    filename = f"{post['id']}.{ext}"
                    await self.download_file(post['url'], filename)
                    
                    # Rate limit: 1-2 seconds between downloads
                    if i < len(posts) - 1:
                        await asyncio.sleep(1.5)
                        
                print(f"[+] Done! Files saved to: {self.output_dir.absolute()}")
            else:
                print("[-] Could not access profile.")
        finally:
            await self.stop_browser()

async def main():
    if len(__import__('sys').argv) < 2:
        username = input("Enter Instagram Username: ")
    else:
        username = __import__('sys').argv[1]
        
    downloader = InstaDownloader(username)
    await downloader.run()

if __name__ == "__main__":
    asyncio.run(main())