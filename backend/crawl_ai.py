import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode, BrowserConfig
import json, sys
# from base64 import b64decode

async def main():
    base_browser = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        accept_downloads=True,
    )

    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler(config=base_browser) as crawler:
        # Run the crawler on a URL
        result = await crawler.arun(url=sys.argv[1], screenshot=False, cache_mode=CacheMode.BYPASS)
        # Print the extracted content
        hr = lambda: print(("-" * 80) * 2)
        hr()
        print(result.markdown)
        hr()
        print(json.dumps(result.media, indent=2))
        hr()
        print(json.dumps(result.links, indent=2))
        hr()
        print(json.dumps(result.downloaded_files, indent=2))
        hr()

        # if result.success:
        #     # Save screenshot
        #     if result.screenshot:
        #         with open("screenshot.png", "wb") as f:
        #             f.write(b64decode(result.screenshot))
        #
        #     # Save PDF
        #     if result.pdf:
        #         with open("download.pdf", "wb") as f:
        #             f.write(result.pdf)
        #
        #     print("[OK] PDF & screenshot captured.")
        # else:
        #     print("[ERROR]", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
